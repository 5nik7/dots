#!/usr/bin/env python3
"""Native recursive Git workflow. Adapted from git-it; see LICENSE."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import signal
import subprocess
import sys
from urllib.parse import urlsplit

LIB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / 'files'))
from catalog import Presentation
from file_platform import config_root, check_object
from interaction import gum_confirm
from progress import Progress, configure, eligible, permanent_output

from profile_config import config_path


class GitError(ValueError):
    pass


class UsageError(GitError):
    pass


def git(path, *args, required=True):
    result = subprocess.run(['git', '-C', str(path), *map(str, args)], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    if required and result.returncode:
        # Credentials and remote URLs can appear in Git stderr. Never echo it.
        raise GitError('Git operation failed: ' + args[0])
    return result


def text(path, *args, required=True):
    return git(path, *args, required=required).stdout.decode('utf-8', 'surrogateescape').rstrip('\n')


def records(path, *args, required=True):
    return [r.decode('utf-8', 'surrogateescape') for r in git(path, *args, required=required).stdout.split(b'\0') if r]


def root(path):
    value = text(path, 'rev-parse', '--show-toplevel', required=False)
    return Path(value).resolve() if value else None


def children(path):
    result = []
    for row in records(path, 'ls-files', '--stage', '-z'):
        meta, name = row.split('\t', 1)
        mode, oid, stage = meta.split()
        if stage != '0': raise GitError('conflicted submodule index')
        if mode == '160000': result.append((name, oid))
    return result


def child_name(path, relative):
    if not relative or Path(relative).is_absolute() or any(p in ('', '.', '..') for p in relative.split('/')):
        raise GitError('unsafe submodule path')
    cursor = path
    for part in relative.split('/'):
        cursor /= part
        check_object(cursor)
        if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()): raise GitError('unsafe submodule path')
    if (cursor / '.git').is_symlink(): raise GitError('unsafe submodule Git directory')
    names = []
    for key in records(path, 'config', '--no-includes', '--null', '--name-only', '--file', '.gitmodules', '--get-regexp', r'^submodule\..*\.path$', required=False):
        values = records(path, 'config', '--no-includes', '--null', '--file', '.gitmodules', '--get-all', key)
        if len(values) != 1: raise GitError('ambiguous submodule registration')
        if values[0] == relative: names.append(key[len('submodule.'):-len('.path')])
    if len(names) != 1: raise GitError('missing or ambiguous submodule registration')
    return names[0]


def upstream(path):
    branch = text(path, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    remote = text(path, 'config', '--get', 'branch.' + branch + '.remote')
    ref = text(path, 'config', '--get-all', 'branch.' + branch + '.merge')
    if remote == '.' or '\n' in ref or not ref.startswith('refs/heads/'): raise GitError('requires one attached upstream')
    tracking = 'refs/remotes/' + remote + '/' + ref[len('refs/heads/'):]
    git(path, 'check-ref-format', ref)
    git(path, 'check-ref-format', tracking)
    return branch, remote, ref, tracking


def in_progress(path):
    for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'sequencer'):
        value = Path(text(path, 'rev-parse', '--git-path', name))
        if (value if value.is_absolute() else path / value).exists(): return True
    return False


def clean(path):
    return (not in_progress(path) and git(path, 'diff', '--cached', '--quiet', '--ignore-submodules=none', '--', required=False).returncode == 0
            and not records(path, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=all'))


def status_files(path, ignore='none'):
    rows = iter(records(path, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=' + ignore))
    files = []
    for row in rows:
        xy, name = row[:2], row[3:]
        old = next(rows) if 'R' in xy or 'C' in xy else ''
        files.append(dict(path=name, xy=xy, old_path=old))
    return files


class Workflow:
    def __init__(self, args):
        self.args = args
        self.root = root(Path(args.directory).resolve())
        if self.root is None: raise GitError('not inside a Git worktree')
        self.ui = Presentation()
        self.events, self.locks, self.order = [], [], []
        self.visited, self.blocked = set(), set()
        self.parents, self.snapshots, self.destinations = {}, {}, {}
        self.owners, self.aliases = set(), {}
        self.failed = False
        self.scope_rows = None
        self.wiki = None
        if getattr(args, 'scoped_publish', False):
            from inspection import selection, selection_hash
            try:
                self.scope_rows = selection(self.root, args.path, args.all_submodules)
            except ValueError as error:
                raise UsageError(str(error)) from None
            self.scope_hash = selection_hash(self.scope_rows)
        if not args.no_config and (args.command == 'publish' or self.ui.color or self.ui.icons):
            try:
                config = Path(args.config or config_path('git.conf'))
                if config.exists():
                    if config.is_symlink() or not config.is_file(): raise GitError('configuration must be a regular file')
                    for row in records(self.root, 'config', '--no-includes', '--null', '--file', str(config), '--list'):
                        key, _, value = row.partition('\n')
                        if key == 'dots-git.owner' and '/' in value and '\n' not in value: self.owners.add(value)
                        elif key == 'dots-git.hostalias' and '=' in value:
                            alias, host = value.split('=', 1); self.aliases[alias.lower()] = host.lower()
                        else: raise GitError('invalid publication configuration')
                elif args.config: raise GitError('configuration does not exist')
            except (GitError, OSError, ValueError):
                self.owners, self.aliases = set(), {}
                if args.command == 'publish': raise
        if self.ui.icons:
            from git_identity import Identities
            self.ui._git_identities = Identities()
            self.ui._git_identities.aliases = self.aliases

    def role(self, role):
        return self.ui.resources.git_style(role)

    def owned(self, path):
        if not self.owners: return False
        branch = text(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', required=False)
        remote = text(path, 'config', '--get', 'branch.' + branch + '.remote', required=False) or 'origin'
        url = text(path, 'remote', 'get-url', '--', remote, required=False)
        if '://' in url:
            parsed = urlsplit(url); host, repo = parsed.hostname or '', parsed.path
        elif re.match(r'^(?:[^/@:]+@)?[^/:]+:', url):
            host, repo = url.split(':', 1); host = host.split('@')[-1]
        else: return False
        host = self.aliases.get(host.lower(), host.lower())
        return host + '/' + repo.strip('/').rpartition('/')[0] in self.owners

    @staticmethod
    def file_role(xy):
        if 'U' in xy or xy in ('AA','DD'): return 'conflict'
        if xy == '??': return 'untracked'
        if xy == '!!': return 'ignored'
        for marker, role in (('D','deleted'),('R','renamed'),('C','copied'),('A','added')):
            if marker in xy: return role
        return 'modified' if len(xy)>1 and xy[1] != ' ' else 'staged'

    @staticmethod
    def file_label(xy):
        if xy == '??': return 'untracked'
        if 'U' in xy or xy in ('AA', 'DD'): return 'conflict'
        label = 'staged' if xy[0] != ' ' else ''
        if xy[1] != ' ': label += (' + ' if label else '') + 'modified'
        if 'D' in xy: label += ' deleted'
        if 'R' in xy: label += ' renamed'
        return label

    @permanent_output()
    def event(self, path, state, detail, file='', xy=''):
        row = dict(path=str(path), status=state, detail=detail, file=file, xy=xy)
        self.events.append(row)
        if state in ('blocked', 'failed'): self.failed = True
        if not self.args.json:
            self.render_event(path, state, detail, file, xy)

    @permanent_output()
    def render_event(self, path, state, detail, file='', xy='', stream=None):
        ui = Presentation(stream) if stream is not None else Presentation(sys.stderr) if state in ('blocked', 'failed') else self.ui
        if ui.icons and not hasattr(self.ui, '_git_identities'):
            from git_identity import Identities
            self.ui._git_identities = Identities()
            self.ui._git_identities.aliases = self.aliases
        if hasattr(self.ui, '_git_identities'):
            ui._git_identities = self.ui._git_identities
        role = 'blocked' if state in ('blocked', 'failed') else 'clean' if state in ('published', 'updated', 'clean', 'unchanged') else 'modified' if state == 'pending' else state
        marker = ('\uf00d' if ui.icons else '[x]') if role == 'blocked' else ('\uf00c' if ui.icons else '[+]') if role == 'clean' else ('\uf071' if ui.icons else '[!]')
        ui.repository_detail('Repository', path, str(path) if self.args.full_paths else path.name, self.role('repo_owned' if self.owned(path) else 'repo'))
        ui.detail('Status', marker + ' ' + state, self.role(role))
        if file: ui.resource_detail(self.file_label(xy) if xy else 'File', path / file,
                                    display=str(path / file) if self.args.full_paths else file,
                                    label_code=self.role(self.file_role(xy)) if xy else None)
        elif state == 'planned' and self.args.command == 'publish' and path in self.destinations:
            destination = self.destinations[path]
            ui.detail_spans('Details', [('branch ', None), (ui.branch_label(destination[0]), self.role('branch')),
                                      (': publish to ' + destination[5] + ' → ', None),
                                      (ui.branch_label(destination[2]), self.role('branch')),
                                      ('; message: ' + self.args.message, None)])
        elif state == 'planned' and self.args.command == 'sync' and detail.startswith('fetch '):
            prefix = 'fetch and fast-forward/check out '
            suffix = '; remote state not checked'
            tracking = detail.removeprefix(prefix).removesuffix(suffix)
            ui.detail_spans('Details', [(prefix, None), (ui.branch_label(tracking), self.role('branch')), (suffix, None)])
        elif state == 'pending' and detail.startswith('Submodule '):
            suffix = ' differs from the parent index; record its pointer separately. Parent index was not changed by this command.'
            relative = detail.removeprefix('Submodule ').removesuffix(suffix)
            child = path / relative
            ui.detail_spans('Details', [('Submodule ', None),
                (ui.repository_label(child, relative), self.role('repo_owned' if self.owned(child) else 'repo')), (suffix, None)])
        elif state != 'unchanged': ui.detail('Details', detail)

    def lock(self, path):
        if self.args.dry_run: return
        common = Path(text(path, 'rev-parse', '--git-common-dir'))
        common = (common if common.is_absolute() else path / common).resolve() / 'git-it.lock'
        if common in self.locks: return
        try: common.mkdir()
        except OSError: raise GitError('another dots git or git-it operation holds the lock (or a stale lock needs manual inspection)') from None
        self.locks.append(common)

    def status(self):
        rows, reasons = [], {}
        def visit(path):
            row = dict(path=str(path), branch='', status='clean', ahead=None, behind=None, files=[])
            rows.append(row)
            if root(path) != path:
                row['status'] = 'missing'; self.failed = True; return
            row['branch'] = text(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', required=False)
            if not row['branch']:
                commit = text(path, 'rev-parse', '--short', 'HEAD', required=False)
                if commit: row['branch'] = 'detached ' + commit
            row['files'] = status_files(path)
            if row['files']: row['status'] = 'modified'
            if any('U' in f['xy'] or f['xy'] in ('AA', 'DD') for f in row['files']): row['status'] = 'conflict'
            try:
                tracking = upstream(path)[3]
                row['ahead'], row['behind'] = map(int, text(path, 'rev-list', '--left-right', '--count', 'HEAD...' + tracking).split())
            except (GitError, ValueError): pass
            try: links = children(path)
            except GitError as error:
                reasons[str(path)] = str(error)
                row['status'] = 'blocked'; self.failed = True; return
            for relative, _ in links:
                child = path / relative
                try: child_name(path, relative)
                except (GitError, ValueError):
                    rows.append(dict(path=str(child), branch='', status='blocked', ahead=None, behind=None, files=[])); self.failed = True; continue
                visit(child)
        with Progress('Inspecting repositories'):
            visit(self.root)
            if self.wiki and self.wiki.only:
                rows[0]['kind']='wiki'
            if self.wiki and self.wiki.row and not self.wiki.only:
                if self.wiki.row['availability']=='available': visit(self.wiki.path)
                else: rows.append(dict(path=str(self.wiki.path),branch='',status='missing',ahead=None,behind=None,files=[]))
                next(row for row in rows if row['path']==str(self.wiki.path))['kind']='wiki'
                reasons[str(self.wiki.path)]='Associated wiki repository' if self.wiki.row['availability']=='available' else 'Wiki unavailable; skipped. Use dots wiki init.'
        if self.args.json:
            print(json.dumps(dict(schema=1, remote_state='cached', repositories=rows, complete=not self.failed), ensure_ascii=True))
        else:
            self.ui.heading('Git status')
            for row in rows:
                path = Path(row['path'])
                label = str(path) if self.args.full_paths else path.name
                if not self.args.full_paths and sum(Path(r['path']).name == path.name for r in rows) > 1:
                    label = (str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path)) if path != self.root else path.name + ' (root)'
                self.ui.emit()
                self.ui.repository_detail('Repository', path, label, self.role('repo_owned' if self.owned(path) else 'repo'))
                self.ui.detail('Branch', self.ui.branch_label(row['branch']), self.role('detached' if row['branch'].startswith('detached ') else 'branch'))
                self.ui.detail('Status', row['status'], self.role(row['status']))
                if str(path) in reasons: self.ui.detail('Reason', reasons[str(path)])
                if row['ahead'] is not None:
                    self.ui.detail('Tracking', str(row['ahead']) + ' ahead', self.role('ahead'))
                    self.ui.detail('', str(row['behind']) + ' behind (cached)', self.role('behind'))
                for file in row['files']:
                    self.ui.resource_detail(self.file_label(file['xy']), path / file['path'],
                                            display=str(path / file['path']) if self.args.full_paths else file['path'],
                                            label_code=self.role(self.file_role(file['xy'])))
                    if file['old_path']:
                        self.ui.resource_detail('From', path / file['old_path'],
                                                display=str(path / file['old_path']) if self.args.full_paths else file['old_path'])
            changed = sum(r['status'] != 'clean' for r in rows)
            self.ui.emit(f'  {len(rows)} repositories / {changed} changed or unavailable / {len(rows)-changed} clean')
            self.ui.emit('  Remote state uses local tracking refs; no fetch performed.')

    def external_phase(self, label):
        if self.scope_rows is not None and eligible():
            Presentation(sys.stderr).detail('Phase', label)

    def fetch(self, path, remote, ref, tracking):
        if self.scope_rows is not None:
            self.external_phase('Fetching upstream')
            git(path, '-c', 'fetch.recurseSubmodules=false', 'fetch', '--quiet', '--no-tags', '--no-recurse-submodules', '--refmap=', '--', remote, ref + ':' + tracking)
            return
        with Progress('Fetching upstream'):
            git(path, '-c', 'fetch.recurseSubmodules=false', 'fetch', '--quiet', '--no-tags', '--no-recurse-submodules', '--refmap=', '--', remote, ref + ':' + tracking)

    def topology(self, path, target):
        old = {name for name, _ in children(path)}
        new = set()
        for row in records(path, 'ls-tree', '-r', '-z', target):
            meta, name = row.split('\t', 1)
            if meta.startswith('160000 '):
                new.add(name)
                # Validate components without requiring the future .gitmodules.
                cursor = path
                if Path(name).is_absolute() or any(p in ('', '.', '..') for p in name.split('/')): raise GitError('unsafe new submodule path')
                for part in name.split('/'):
                    cursor /= part; check_object(cursor)
                    if cursor.is_symlink(): raise GitError('unsafe new submodule path')
                if name not in old and cursor.exists(): raise GitError('occupied new submodule path')
        if not old <= new: raise GitError('submodule removal or replacement needs manual review')

    def sync(self, path, pinned=None, parent=None, relative=None):
        try:
            if path in self.visited: raise GitError('repeated repository in traversal')
            self.visited.add(path); self.lock(path)
            if not clean(path): raise GitError('local edits, staged changes, untracked files, or an operation in progress')
            before = text(path, 'rev-parse', '--verify', 'HEAD')
            remote = ref = tracking = ''
            if pinned is None: _, remote, ref, tracking = upstream(path)
            elif self.args.remote:
                name = child_name(parent, relative)
                branch = text(parent, 'config', '--get', 'submodule.' + name + '.branch', required=False) or text(parent, 'config', '--file', '.gitmodules', '--get', 'submodule.' + name + '.branch', required=False)
                if branch == '.': branch = text(parent, 'symbolic-ref', '--quiet', '--short', 'HEAD')
                if branch:
                    attached = text(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', required=False)
                    remote = text(path, 'config', '--get', 'branch.' + attached + '.remote', required=False) or 'origin'
                    if remote == '.': remote = 'origin'
                    ref, tracking = 'refs/heads/' + branch, 'refs/remotes/' + remote + '/' + branch
                    git(path, 'check-ref-format', ref); git(path, 'check-ref-format', tracking)
                else: _, remote, ref, tracking = upstream(path)
            if self.args.dry_run:
                detail = f'fetch and fast-forward/check out {remote}/{ref}; remote state not checked' if remote else f'check out parent-recorded commit {pinned}; missing objects may need download'
                self.event(path, 'planned', detail)
            else:
                if remote:
                    self.fetch(path, remote, ref, tracking)
                    target = text(path, 'rev-parse', '--verify', tracking + '^{commit}')
                else:
                    target = pinned
                    if git(path, 'cat-file', '-e', target + '^{commit}', required=False).returncode:
                        branch = text(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', required=False)
                        source = text(path, 'config', '--get', 'branch.' + branch + '.remote', required=False) or 'origin'
                        git(path, 'fetch', '--quiet', '--no-tags', '--no-recurse-submodules', '--', source, target)
                if not clean(path) or text(path, 'rev-parse', 'HEAD') != before: raise GitError('repository changed during fetch')
                if pinned is None:
                    if git(path, 'merge-base', '--is-ancestor', target, 'HEAD', required=False).returncode == 0:
                        self.event(path, 'unchanged', 'already current or locally ahead; local commits retained')
                    else:
                        if git(path, 'merge-base', '--is-ancestor', 'HEAD', target, required=False).returncode: raise GitError('local and upstream histories diverged')
                        self.topology(path, target)
                        git(path, '-c', 'submodule.recurse=false', 'merge', '--ff-only', '--no-edit', '--no-overwrite-ignore', target)
                        self.event(path, 'updated', 'fast-forwarded upstream')
                elif before == target: self.event(path, 'unchanged', 'at selected submodule commit')
                else:
                    if not text(path, 'for-each-ref', '--format=%(refname)', '--contains', before, 'refs/remotes/'):
                        raise GitError('refusing to leave a submodule commit without remote reachability evidence')
                    self.topology(path, target)
                    git(path, '-c', 'submodule.recurse=false', 'checkout', '--quiet', '--detach', '--no-overwrite-ignore', target, '--')
                    self.event(path, 'updated', 'checked out selected commit; parent pointer is not staged')
            for relative, oid in children(path):
                child = path / relative
                try:
                    child_name(path, relative)
                    if root(child) != child:
                        if not self.args.init: raise GitError('not initialized; use sync --init to permit downloading this submodule')
                        if self.args.dry_run:
                            self.event(child, 'planned', 'initialize at recorded commit; deeper structure requires download'); continue
                        if child.exists() and any(child.iterdir()): raise GitError('uninitialized submodule directory is not empty')
                        git(path, '-c', 'submodule.recurse=false', '--literal-pathspecs', 'submodule', 'update', '--init', '--checkout', '--', relative)
                    self.sync(child, oid, path, relative)
                except (GitError, OSError, ValueError) as error: self.event(child, 'blocked', str(error))
        except (GitError, OSError, ValueError) as error: self.event(path, 'blocked', str(error))

    def fingerprint(self, path):
        digest = hashlib.sha256()
        for args in [('rev-parse', 'HEAD'), ('status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=all'),
                     ('diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv')]: digest.update(git(path, *args).stdout)
        if self.args.all:
            digest.update(git(path, 'diff', '--binary', '--no-ext-diff', '--no-textconv', '--ignore-submodules=all').stdout)
            for name in records(path, 'ls-files', '--others', '--exclude-standard', '-z'):
                file = path / name
                if file.is_symlink(): digest.update(os.fsencode(os.readlink(file)))
                elif file.is_file(): digest.update(git(path, 'hash-object', '--no-filters', '--', str(file)).stdout)
                else: raise GitError('unsupported untracked object')
        return digest.hexdigest()

    def collect(self, path, parent=None):
        self.parents[path] = parent
        try:
            if path in self.visited: raise GitError('repeated repository')
            self.visited.add(path); self.lock(path)
            for relative, _ in children(path):
                child = path / relative
                try:
                    child_name(path, relative)
                    if root(child) != child: raise GitError('initialize the submodule before recursive publication')
                    self.collect(child, path)
                    if child in self.blocked: self.blocked.add(path)
                except (ValueError, OSError) as error:
                    self.blocked.add(path); self.event(child, 'blocked', str(error))
            self.snapshots[path] = self.fingerprint(path)
            self.order.append(path)
        except (ValueError, OSError) as error:
            self.blocked.add(path); self.event(path, 'blocked', str(error))

    def needed(self, path):
        if git(path, 'diff', '--cached', '--quiet', '--ignore-submodules=none', '--', required=False).returncode: return True
        if self.args.all and status_files(path, 'all'): return True
        parent = self.parents[path]
        if parent:
            relative = path.relative_to(parent).as_posix()
            rows = records(parent, 'ls-files', '--stage', '-z', '--', ':(literal)' + relative)
            if len(rows) != 1 or rows[0].split('\t')[0].split()[1] != text(path, 'rev-parse', 'HEAD'): return True
        try: tracking = upstream(path)[3]
        except GitError: return False
        return git(path, 'merge-base', '--is-ancestor', 'HEAD', tracking, required=False).returncode != 0

    def destination(self, path):
        branch, remote, ref, tracking = upstream(path)
        for key in ('remote.' + remote + '.push', 'branch.' + branch + '.pushRemote', 'remote.pushDefault'):
            if git(path, 'config', '--get-all', key, required=False).returncode == 0: raise GitError('ambiguous push configuration')
        if text(path, 'config', '--bool', '--get', 'remote.' + remote + '.mirror', required=False) == 'true': raise GitError('mirror push is not supported')
        url = text(path, 'remote', 'get-url', '--push', '--all', '--', remote)
        if not url or '\n' in url: raise GitError('requires one push URL')
        if '://' in url:
            parsed = urlsplit(url); host, repo = parsed.hostname or '', parsed.path
            safe = parsed.scheme + '://' + (parsed.hostname or '') + parsed.path
        elif re.match(r'^(?:[^/@:]+@)?[^/:]+:', url):
            host, repo = url.split(':', 1); host = host.split('@')[-1]; safe = host + ':' + repo
        else: host, repo, safe = '', url, url
        repo = repo.split('?')[0].split('#')[0].strip('/')
        host = self.aliases.get(host.lower(), host.lower())
        if not host or host + '/' + repo.rpartition('/')[0] not in self.owners: raise GitError('push URL is not owned by a configured host/namespace')
        return branch, remote, ref, tracking, url, safe.split('?')[0].split('#')[0]

    def recheck_scope(self):
        if self.scope_rows is not None:
            from inspection import selection, selection_hash
            if selection_hash(selection(self.root, self.args.path, self.args.all_submodules)) != self.scope_hash:
                raise GitError('submodule selection changed after preview')

    def report_parent_pointers(self):
        if self.scope_rows is None or self.args.dry_run:
            return
        for row in self.scope_rows:
            if row['availability'] != 'available':
                continue
            head = text(Path(row['path']), 'rev-parse', '--verify', 'HEAD', required=False)
            if head and head != row['recorded_commit']:
                self.event(Path(row['parent']), 'pending', 'Submodule ' + str(Path(row['path']).relative_to(row['parent']))
                           + ' differs from the parent index; record its pointer separately. Parent index was not changed by this command.')

    def publish(self):
        if self.scope_rows is None:
            self.collect(self.root)
        else:
            with Progress('Collecting publish inputs'):
                for row in self.scope_rows:
                    if row['availability'] != 'available':
                        self.event(Path(row['path']), 'blocked', row['reason'])
                    else:
                        self.collect(Path(row['path']))
            if not self.args.json:
                self.ui.detail('Scope', 'Only selected subtrees will publish; excluded parent indexes remain unchanged.')
                if not self.scope_rows:
                    self.ui.detail('Result', 'No registered submodules.')
        if self.wiki: self.wiki.collect()
        expected = set()
        for path in self.order:
            parent = self.parents[path]
            try:
                if path in self.blocked: raise GitError('required child or preflight check failed')
                if not self.needed(path) and path not in expected:
                    self.event(path, 'unchanged', 'no selected changes or known ahead commits (remote state not fetched)'); continue
                if in_progress(path): raise GitError('Git operation in progress')
                destination = self.destination(path)
                self.destinations[path] = destination
                self.event(path, 'planned', f'branch {destination[0]}: publish to {destination[5]} → {destination[2]}; message: {self.args.message}')
                if parent: expected.add(parent)
                for row in status_files(path):
                    if self.args.all or row['xy'][0] not in (' ', '?'): self.event(path, 'selected', row['xy'] + ' ' + row['path'], row['path'], row['xy'])
            except (ValueError, OSError) as error:
                self.blocked.add(path)
                if parent: self.blocked.add(parent)
                self.event(path, 'blocked', str(error))
        if self.args.dry_run or not self.destinations:
            self.report_parent_pointers()
            return
        if not self.args.yes:
            if not sys.stdin.isatty(): raise UsageError('publish requires a terminal confirmation or --yes')
            if self.args.json:
                for row in self.events:
                    self.render_event(Path(row['path']), row['status'], row['detail'], row['file'], row['xy'], sys.stderr)
            approved = None if self.args.json else gum_confirm('Publish the selected changes?', 'Publish')
            if approved is None:
                print('Publish the selected changes? [y/N] ', end='', file=sys.stderr, flush=True)
                approved = input().lower() == 'y'
            if not approved:
                self.event(self.root, 'cancelled', 'nothing committed or pushed'); return
        for path in self.order:
            parent = self.parents[path]
            try:
                self.recheck_scope()
                if path in self.blocked: raise GitError('a required child or preflight check failed')
                if self.fingerprint(path) != self.snapshots[path] or (parent and self.fingerprint(parent) != self.snapshots[parent]): raise GitError('publish inputs changed after preview')
                if in_progress(path): raise GitError('Git operation in progress')
                if not self.needed(path):
                    self.event(path, 'unchanged', 'no selected changes or known ahead commits'); continue
                if self.wiki and path==self.wiki.path: self.wiki.validate(True)
                dest = self.destination(path)
                if dest != self.destinations.get(path): raise GitError('branch or destination changed after preview')
                branch, remote, ref, tracking, url, _ = dest
                self.fetch(path, remote, ref, tracking)
                if git(path, 'merge-base', '--is-ancestor', tracking, 'HEAD', required=False).returncode: raise GitError('remote is ahead or diverged; sync or resolve manually before publishing')
                if self.fingerprint(path) != self.snapshots[path] or self.destination(path) != dest: raise GitError('inputs or destination changed during preflight')
                self.recheck_scope()
                if self.args.all: git(path, 'add', '--all', '--', '.', *[':(top,exclude,literal)' + name for name, _ in children(path)])
                if git(path, 'diff', '--cached', '--quiet', '--ignore-submodules=none', '--', required=False).returncode:
                    self.external_phase('Committing selected changes')
                    git(path, 'commit', '-m', self.args.message)
                self.external_phase('Pushing selected changes')
                git(path, '-c', 'push.followTags=false', 'push', '--porcelain', '--recurse-submodules=check', '--', url, 'HEAD:' + ref)
                self.event(path, 'published', 'selected changes and ahead commits pushed')
                self.fetch(path, url, ref, tracking)
                if parent:
                    relative = path.relative_to(parent).as_posix()
                    index = records(parent, 'ls-files', '--stage', '-z', '--', ':(literal)' + relative)[0].split('\t')[0].split()[1]
                    old_rows = records(parent, 'ls-tree', '-z', 'HEAD', '--', ':(literal)' + relative)
                    old = old_rows[0].split('\t')[0].split()[2] if old_rows else ''
                    head = text(path, 'rev-parse', 'HEAD')
                    if index not in (old, head): raise GitError('pre-existing staged child pointer differs; preserved for manual review')
                    if self.fingerprint(parent) != self.snapshots[parent]: raise GitError('parent changed during child publication')
                    git(parent, 'add', '--', ':(literal)' + relative)
                    self.snapshots[parent] = self.fingerprint(parent)
            except (ValueError, OSError) as error:
                self.event(path, 'blocked', str(error))
                if parent: self.blocked.add(parent)
        self.report_parent_pointers()

    def run(self):
        configure(not self.args.json and not self.args.dry_run)
        try:
            if self.args.command == 'status': self.status()
            else:
                command = 'submodules publish' if getattr(self.args, 'scoped_publish', False) else self.args.command
                if not self.args.json: self.ui.heading('Git ' + command)
                if self.args.command == 'sync':
                    self.sync(self.root)
                    if self.wiki and self.wiki.row and not self.wiki.only:
                        if self.wiki.row['availability']=='available':
                            if any(e['path']==str(self.root) and e['status'] in ('blocked','failed') for e in self.events):
                                self.event(self.wiki.path,'blocked','Source synchronization failed; wiki skipped')
                            else:
                                try:self.wiki.recheck()
                                except (ValueError,OSError) as error:self.event(self.wiki.path,'blocked',str(error))
                                else:self.sync(self.wiki.path)
                        else: self.event(self.wiki.path,'skipped','Wiki unavailable; use dots wiki init')
                else: self.publish()
                if self.args.json:
                    data = dict(schema=1, command=command, complete=not self.failed, dry_run=self.args.dry_run, events=self.events)
                    if self.scope_rows is not None:
                        data.update(base=str(self.root), selection=[row['path'] for row in self.scope_rows])
                    print(json.dumps(data, ensure_ascii=True))
                elif self.failed: self.ui.emit('  Incomplete; completed work is retained. Resolve blockers and rerun.')
                elif self.args.dry_run: self.ui.emit('  Preview only; no changes made. Remote state was not fetched.')
                else: self.ui.emit('  Complete')
            return int(self.failed)
        finally:
            for path in reversed(self.locks): path.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'sync', 'publish', 'submodules-publish'])
    parser.add_argument('path', nargs='?')
    parser.add_argument('--all-submodules', action='store_true')
    parser.add_argument('-C', '--directory', default=os.environ.get('DOTS') or str(LIB.parents[1]))
    parser.add_argument('--config')
    parser.add_argument('--no-config', action='store_true')
    parser.add_argument('--no-wiki', action='store_true')
    parser.add_argument('--wiki-only', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('-m', '--message')
    for flag in ('json', 'full-paths', 'dry-run', 'all', 'yes', 'remote', 'init'): parser.add_argument('--' + flag, action='store_true')
    args = parser.parse_intermixed_args()
    args.scoped_publish = args.command == 'submodules-publish'
    if args.scoped_publish:
        args.command = 'publish'
        if bool(args.path is not None) == bool(args.all_submodules): parser.error('select one registered PATH or --all-submodules')
    elif args.path is not None or args.all_submodules:
        parser.error('PATH and --all-submodules require git submodules publish')
    if args.command != 'publish' and (args.all or args.yes or args.config or args.no_config or args.message): parser.error('publish options require publish')
    if args.command != 'sync' and (args.remote or args.init): parser.error('sync options require sync')
    if args.command == 'status' and args.dry_run: parser.error('status is already read-only')
    if not shutil.which('git'): raise GitError('Git is required')
    if any(name in os.environ for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR')): raise GitError('unset Git repository/index redirection variables')
    if not args.message: args.message = 'Sync via ' + (os.environ.get('HOSTNAME') or socket.gethostname()) + ' on ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    def interrupted(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    if hasattr(signal, 'SIGBREAK'): signal.signal(signal.SIGBREAK, interrupted)
    workflow=Workflow(args)
    if args.wiki_only and (args.no_wiki or args.scoped_publish): parser.error('wiki-only scope conflicts with submodule/exclusion scope')
    if not args.no_wiki and not args.scoped_publish and (args.wiki_only or (workflow.root/'.dots/wiki.json').is_file()):
        from wiki_git import Companion
        workflow.wiki=Companion(workflow)
    return workflow.run()


if __name__ == '__main__':
    try: sys.exit(main())
    except UsageError as error:
        print('dots git: ' + str(error), file=sys.stderr); sys.exit(2)
    except (OSError, ValueError) as error:
        print('dots git: ' + str(error), file=sys.stderr); sys.exit(3)
    except KeyboardInterrupt: sys.exit(130)
