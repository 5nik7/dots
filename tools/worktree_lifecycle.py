#!/usr/bin/env python3
"""Explicitly managed development worktrees only; preview by default."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


class Refusal(Exception):
    """A fixed diagnostic; never include arbitrary Git output or file contents."""


def inside(path, root):
    return path == root or root in path.parents


def process_use(root):
    """Inspect this account's processes, without dumping argv/environment data."""
    proc = Path('/proc')
    if os.name != 'posix' or not (proc / 'self' / 'fd').is_dir():
        return 'process inspection unavailable on this host'
    uncertain = False
    try:
        for process in proc.iterdir():
            if not process.name.isdigit():
                continue
            try:
                if process.stat().st_uid != os.getuid():
                    continue
                for field in ('cwd', 'exe', 'fd', 'maps', 'cmdline'):
                    try:
                        if field in ('cwd', 'exe'):
                            targets = [os.readlink(process / field)]
                        elif field == 'fd':
                            targets = []
                            for fd in (process / field).iterdir():
                                try:
                                    targets.append(os.readlink(fd))
                                except FileNotFoundError:
                                    pass
                        elif field == 'maps':
                            targets = [line.split(maxsplit=5)[-1] for line in
                                       (process / field).read_text().splitlines()
                                       if len(line.split(maxsplit=5)) == 6]
                        else:
                            # Match only path arguments; never display their contents.
                            targets = (process / field).read_bytes().decode(errors='replace').split('\0')
                        if any(t == str(root) or t.startswith(str(root) + os.sep) for t in targets):
                            return 'active process reference'
                    except FileNotFoundError:
                        continue
                    except PermissionError:
                        try:
                            status = (process / 'status').read_text()
                            if any(line.startswith('State:') and ('Z (' in line or 'X (' in line)
                                   for line in status.splitlines()):
                                continue
                        except FileNotFoundError:
                            continue
                        # Keep scanning so a definite live reference is reported
                        # even when an earlier process was inaccessible. Either
                        # outcome still refuses removal.
                        uncertain = True
            except FileNotFoundError:
                continue
    except (OSError, UnicodeError):
        return 'process inspection uncertainty'
    return 'process inspection permission uncertainty' if uncertain else None


class Lifecycle:
    def __init__(self, original, session=None, helper=None):
        self.original = Path(original).resolve(strict=True)
        self.cwd = Path.cwd().resolve()
        self.helper = Path(helper or __file__).resolve(strict=True)
        self.session = Path(session).resolve(strict=True) if session else None
        # Ignore inherited Git routing/injected config; allow transport credentials
        # through their normal Git/SSH configuration without printing them.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
        self.common = Path(self.git(self.original, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip())
        if self.common != self.original / '.git' or not self.common.is_dir():
            raise Refusal('original must be the main non-bare checkout')
        if self.worktrees()[0].get('worktree') != str(self.original):
            raise Refusal('original checkout registration mismatch')
        self.registry = self.common / 'dots-managed-worktrees.json'
        self.lock = self.common / 'dots-managed-worktrees.lock'

    def git(self, cwd, *args):
        try:
            result = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, '-c', 'core.fsmonitor=false',
                                     '-c', 'submodule.recurse=false', '-c', 'gc.auto=0',
                                     '-c', 'maintenance.auto=false', '-C', str(cwd), *args],
                                    env=self.env, capture_output=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired):
            raise Refusal('Git unavailable or timed out') from None
        if result.returncode:
            raise Refusal('Git refused ' + args[0])
        return result.stdout.decode('utf-8', errors='strict')

    def worktrees(self):
        blocks = self.git(self.original, 'worktree', 'list', '--porcelain', '-z').split('\0\0')
        records = [dict(part.split(' ', 1) if ' ' in part else (part, '')
                        for part in block.split('\0') if part) for block in blocks if block]
        for record in records:
            if 'worktree' in record:
                # Git prints forward slashes on Windows; compare native paths.
                record['worktree'] = str(Path(record['worktree']).resolve())
        return records

    def load(self):
        if self.registry.is_symlink():
            raise Refusal('invalid managed registry')
        if not self.registry.exists():
            return []
        if self.registry.stat().st_size > 65536:
            raise Refusal('invalid managed registry')
        try:
            data = json.loads(self.registry.read_text())
            if set(data) != {'schema_version', 'worktrees'} or data['schema_version'] != 1:
                raise ValueError()
            records = data['worktrees']
            if not isinstance(records, list) or len(records) > 64:
                raise ValueError()
            for r in records:
                if not isinstance(r, dict) or set(r) != {'path', 'git_dir', 'token'} or not all(isinstance(v, str) for v in r.values()):
                    raise ValueError()
            if len({r['path'] for r in records}) != len(records):
                raise ValueError()
            return records
        except (ValueError, TypeError, OSError):
            raise Refusal('invalid managed registry') from None

    def save(self, records):
        payload = json.dumps({'schema_version': 1, 'worktrees': records}, indent=2) + '\n'
        if len(records) > 64 or len(payload.encode('utf-8')) > 65536:
            raise Refusal('managed registry limit exceeded')
        temporary = self.registry.with_name(self.registry.name + '.' + uuid.uuid4().hex)
        try:
            with temporary.open('x', encoding='utf-8') as f:
                f.write(payload)
            os.replace(temporary, self.registry)
        finally:
            temporary.unlink(missing_ok=True)

    def registration(self, path):
        root = Path(path)
        if not root.is_absolute() or root.resolve(strict=True) != root or root.parent != self.original.parent:
            raise Refusal('candidate must be a canonical immediate sibling of original')
        if root == self.original or not (root / '.git').is_file() or (root / '.git').is_symlink():
            raise Refusal('original or non-linked worktree')
        entries = [w for w in self.worktrees() if w.get('worktree') == str(root)]
        if len(entries) != 1 or 'locked' in entries[0] or 'prunable' in entries[0]:
            raise Refusal('unregistered, locked or prunable worktree')
        if Path(self.git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip()) != self.common:
            raise Refusal('different repository')
        admin = Path(self.git(root, 'rev-parse', '--path-format=absolute', '--git-dir').strip())
        if admin.parent != self.common / 'worktrees' or admin.resolve() != admin:
            raise Refusal('unexpected worktree administrative path')
        return root, admin

    def register(self, path):
        root, admin = self.registration(path)
        if len(self.worktrees()) > 2:
            raise Refusal('more than one development worktree; inspect and resolve capacity first')
        records = self.load()
        if any(r['path'] == str(root) for r in records):
            raise Refusal('already recorded; do not silently renew authorization')
        token = uuid.uuid4().hex
        marker = admin / 'dots-managed-token'
        with marker.open('x', encoding='ascii') as f:
            f.write(token)
        records.append({'path': str(root), 'git_dir': str(admin), 'token': token})
        self.save(records)
        return {'path': str(root), 'status': 'registered'}

    def local_work(self, root):
        if self.git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all',
                    '--ignored=matching', '--ignore-submodules=none'):
            return 'staged, modified, untracked or ignored content'
        if any(line and line[0] != 'H' for line in self.git(root, 'ls-files', '-v').splitlines()):
            return 'index flags require review'
        allowed = {'.'}
        submodules = set()
        for item in self.git(root, 'ls-files', '--stage', '-z').split('\0'):
            if not item:
                continue
            meta, name = item.split('\t', 1)
            allowed.update(str(p) for p in Path(name).parents)
            if meta.startswith('160000 '):
                allowed.add(name)
                submodules.add(name)
        def uncertain(error):
            raise Refusal('directory inspection uncertainty')
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=uncertain):
            rel = str(Path(directory).relative_to(root))
            if rel in submodules:
                if dirs or files:
                    return 'populated submodule requires review'
                dirs[:] = []
            elif not dirs and not files and rel not in allowed:
                return 'unique empty directory'
        return None

    def live_use(self, root, protects):
        references = [self.original, self.cwd, self.helper, *protects]
        if self.session:
            references.append(self.session)
        # Only known paths, never shell/configuration contents.
        for key in ('HOME', 'DOTS', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME',
                    'XDG_CACHE_HOME', 'ZDOTDIR', 'ENV', 'BASH_ENV', 'INPUTRC'):
            if os.environ.get(key):
                references.append(Path(os.environ[key]).expanduser().resolve())
        references.extend(Path(p).resolve() for p in os.environ.get('PATH', '').split(os.pathsep) if p)
        home = Path.home()
        references.extend(home / p for p in ('dots-review-evidence', '.config', '.local/share', '.local/state', '.cache',
                                            '.bashrc', '.bash_profile', '.profile', '.zshrc', '.zprofile'))
        if any(inside(Path(p).resolve(), root) for p in references):
            return 'protected original/session/helper or known live path'
        # Original-checkout symlinks can feed live dotfiles. Do not follow them
        # while walking or read target contents.
        def uncertain(error):
            raise Refusal('live symlink inspection uncertainty')
        for directory, dirs, files in os.walk(self.original, followlinks=False, onerror=uncertain):
            if Path(directory) == self.original:
                dirs[:] = [d for d in dirs if d != '.git']
            for name in dirs + files:
                p = Path(directory) / name
                if p.is_symlink() and inside(p.resolve(), root):
                    return 'original checkout symlink uses candidate'
        return process_use(root)

    def eligible(self, record, protects, merged=True):
        root, admin = self.registration(record['path'])
        marker = admin / 'dots-managed-token'
        if str(admin) != record['git_dir'] or marker.is_symlink() or not marker.is_file() or marker.stat().st_size != 32 or marker.read_text() != record['token']:
            raise Refusal('managed identity mismatch')
        reason = self.live_use(root, protects) or self.local_work(root)
        if reason:
            raise Refusal(reason)
        head = self.git(root, 'rev-parse', 'HEAD').strip()
        if not merged:
            return root, head
        main = self.git(self.original, 'rev-parse', 'refs/remotes/origin/main').strip()
        try:
            self.git(self.original, 'merge-base', '--is-ancestor', head, main)
        except Refusal:
            raise Refusal('HEAD not contained in origin/main') from None
        return root, head

    def run(self, apply=False, reviewed=False, protects=()):
        records = self.load()
        results = []
        for record in records:
            result = {'path': record['path'], 'status': 'skipped'}
            attempted = False
            try:
                if apply:
                    if not reviewed or not self.session:
                        raise Refusal('apply requires --usage-reviewed and --session-worktree')
                    if str(self.session) not in [w.get('worktree') for w in self.worktrees()]:
                        raise Refusal('session worktree is not registered here')
                root, head = self.eligible(record, protects, merged=not apply)
                if apply:
                    # Restrict fetch destination: no pruning, tags, submodules,
                    # user refspecs, branch deletion or automatic maintenance.
                    self.git(self.original, 'fetch', '--no-recurse-submodules', '--no-prune',
                             '--no-tags', '--no-auto-maintenance', 'origin',
                             'refs/heads/main:refs/remotes/origin/main')
                    root, refreshed_head = self.eligible(record, protects)
                    if refreshed_head != head:
                        raise Refusal('candidate HEAD changed during checks')
                    attempted = True
                    self.git(self.original, 'worktree', 'remove', str(root))
                    records = [r for r in records if r != record]
                    self.save(records)
                    result['status'] = 'removed'
                else:
                    result.update(status='candidate', reason='cached merge check only; fresh fetch and usage review required for apply')
            except (Refusal, OSError, ValueError, RuntimeError) as e:
                result['reason'] = str(e) if isinstance(e, Refusal) else 'filesystem or metadata uncertainty'
                if attempted:
                    result.update(status='removal_failed', action='inspect directory and registration; no force or automatic retry')
            results.append(result)
        recorded = {r['path'] for r in self.load()}
        results.extend({'path': w['worktree'], 'status': 'skipped', 'reason': 'not explicitly managed'}
                       for w in self.worktrees() if w.get('worktree') not in recorded)
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='absolute original checkout')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--apply', action='store_true')
    modes.add_argument('--register', metavar='PATH')
    parser.add_argument('--session-worktree', help='actual current agent/session worktree, even after cd')
    parser.add_argument('--usage-reviewed', action='store_true', help='caller verified no other idle session or text-based live configuration uses candidates')
    parser.add_argument('--protect', action='append', default=[], metavar='PATH', help='additional known live reference; repeatable')
    args = parser.parse_args()
    try:
        lifecycle = Lifecycle(args.repo, args.session_worktree)
        if lifecycle.lock.exists():
            raise Refusal('another helper operation or stale lock requires review')
        locked = False
        try:
            if args.apply or args.register:
                with lifecycle.lock.open('x'):
                    pass
                locked = True
            if args.register:
                result = lifecycle.register(args.register)
            else:
                result = lifecycle.run(args.apply, args.usage_reviewed, [Path(p).resolve() for p in args.protect])
        finally:
            if locked:
                lifecycle.lock.unlink()
        print(json.dumps(result, indent=2))
        return 0
    except (Refusal, OSError, ValueError, RuntimeError):
        print('worktree lifecycle: repository or registry validation failed; nothing further attempted', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
