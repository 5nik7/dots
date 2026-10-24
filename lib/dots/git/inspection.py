#!/usr/bin/env python3
"""Local repository facts and registered-submodule selection shared by both shells."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit

# This directory is also prepended by the native controller bridge.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli as core
from resources import cells
from git_identity import host_icon


def context(directory):
    if not shutil.which('git'):
        raise core.GitError('Git is required')
    if any(key in os.environ for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR')):
        raise core.GitError('unset Git repository/index redirection variables')
    base = core.root(Path(directory).resolve())
    if base is None:
        raise core.GitError('not inside a Git worktree')
    return base


def edges(parent, base, depth):
    """Read registration once per parent; never follow unsafe children."""
    links = core.children(parent)
    registered = {}
    if links:
        keys = core.records(parent, 'config', '--no-includes', '--null', '--name-only', '--file', '.gitmodules',
                            '--get-regexp', r'^submodule\..*\.path$', required=False)
        for key in keys:
            values = core.records(parent, 'config', '--no-includes', '--null', '--file', '.gitmodules', '--get-all', key, required=False)
            if len(values) == 1:
                registered[values[0]] = registered.get(values[0], 0) + 1
    result = []
    for relative, oid in links:
        child = parent / relative
        row = dict(path=str(child), parent=str(parent), relative_path=os.path.relpath(child, base).replace(os.sep, '/'),
                   depth=depth, recorded_commit=oid, availability='available', reason='')
        try:
            if (not relative or Path(relative).is_absolute() or '\\' in relative and os.name == 'nt'
                    or any(part in ('', '.', '..') for part in relative.split('/')) or registered.get(relative) != 1):
                raise core.GitError('unsafe or unregistered submodule')
            cursor = parent
            for part in relative.split('/'):
                cursor /= part
                core.check_object(cursor)
                if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
                    raise core.GitError('unsafe submodule path')
            if (child / '.git').is_symlink():
                raise core.GitError('unsafe submodule Git directory')
            if core.root(child) != child:
                row.update(availability='missing', reason='not initialized; descendants are unknown')
        except (OSError, ValueError):
            row.update(availability='blocked', reason='unsafe or unregistered submodule')
        result.append(row)
    return result


def discover(base, depth=None):
    rows, errors, limited = [], [], []
    visited = {base}
    def visit(parent, level):
        try:
            children = edges(parent, base, level)
        except (OSError, ValueError):
            errors.append(dict(path=str(parent), reason='cannot inspect submodule index or registration'))
            return
        for row in children:
            rows.append(row)
            if row['availability'] != 'available':
                continue
            child = Path(row['path'])
            if child in visited:
                row.update(availability='blocked', reason='repeated repository')
                continue
            visited.add(child)
            if depth is not None and level >= depth:
                # The limit deliberately avoids reading the child's descendants.
                limited.append(str(child))
            else:
                visit(child, level + 1)
    visit(base, 1)
    return rows, errors, limited


def selection(base, operand=None, all_submodules=False):
    if bool(operand is not None) == bool(all_submodules):
        raise core.UsageError('select one registered PATH or --all-submodules')
    if all_submodules:
        return edges(base, base, 1)
    relative = operand
    if relative.startswith('./'):
        relative = relative[2:]
    if (not relative or Path(relative).is_absolute() or any(p in ('', '.', '..') for p in relative.split('/'))
            or os.name == 'nt' and '\\' in relative):
        raise core.UsageError('PATH must name a registered submodule relative to the selected repository')
    parent, level = base, 1
    while True:
        candidates = edges(parent, base, level)
        match = next((row for row in candidates if relative == row['relative_path'] or relative.startswith(row['relative_path'] + '/')), None)
        if match is None:
            raise core.UsageError('PATH is not a registered submodule')
        if relative == match['relative_path']:
            return [match]
        if match['availability'] != 'available':
            raise core.UsageError('cannot select an undiscovered descendant of an unavailable submodule')
        parent, level = Path(match['path']), level + 1


def selection_hash(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


class Inspection:
    def __init__(self, base):
        self.base = base
        self.ui = core.Presentation()
        self.owners, self.aliases = set(), {}
        self.ownership = 'unconfigured'
        config = core.config_root() / 'dots/git.conf'
        try:
            if config.exists():
                if config.is_symlink() or not config.is_file():
                    raise ValueError('invalid ownership configuration')
                self.ownership = 'configured'
                for entry in core.records(base, 'config', '--no-includes', '--null', '--file', str(config), '--list'):
                    key, _, value = entry.partition('\n')
                    if key == 'dots-git.owner' and '/' in value and '\n' not in value:
                        self.owners.add(value)
                    elif key == 'dots-git.hostalias' and '=' in value:
                        alias, host = value.split('=', 1)
                        self.aliases[alias.lower()] = host.lower()
                    else:
                        raise ValueError('invalid ownership configuration')
        except (OSError, ValueError):
            self.ownership = 'unavailable'
            self.owners, self.aliases = set(), {}

    def remote(self, path, branch):
        remote = core.text(path, 'config', '--get', 'branch.' + branch + '.remote', required=False) if branch else ''
        if not remote or remote == '.':
            remote = 'origin'
        url = core.text(path, 'remote', 'get-url', '--', remote, required=False)
        if not url:
            return dict(name=None, url=None, host=None, owner=None, owned=None, ownership=self.ownership)
        safe, host, repo = url.split('?')[0].split('#')[0], '', ''
        try:
            if '://' in url:
                parsed = urlsplit(url)
                host, repo = parsed.hostname or '', parsed.path
                authority = parsed.netloc.rsplit('@', 1)[-1]
                safe = parsed.scheme + '://' + authority + parsed.path
            elif re.match(r'^(?:[^/@:]+@)?[^/:]+:', url):
                authority, repo = url.split(':', 1)
                host = authority.rsplit('@', 1)[-1]
                safe = host + ':' + repo.split('?')[0].split('#')[0]
        except ValueError:
            return dict(name=remote, url=None, host=None, owner=None, owned=None, ownership='unavailable')
        host = self.aliases.get(host.lower(), host.lower())
        owner = repo.split('?')[0].split('#')[0].strip('/').rpartition('/')[0] if host else ''
        if url.lower().startswith('file://'):
            owner = ''
        owned = host + '/' + owner in self.owners if host and owner and self.ownership == 'configured' else None
        return dict(name=remote, url=safe, host=host or None, owner=owner or None, owned=owned, ownership=self.ownership)

    def inspect(self, edge):
        row = dict(edge, branch=None, head=None, detached=False, status=edge['availability'],
                   ahead=None, behind=None, upstream=None, files=[], pointer_changed=False, remote=None)
        if row['availability'] != 'available':
            return row
        path = Path(row['path'])
        try:
            row['branch'] = core.text(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', required=False) or None
            row['head'] = core.text(path, 'rev-parse', '--verify', 'HEAD', required=False) or None
            row['detached'] = not row['branch'] and bool(row['head'])
            row['files'] = core.status_files(path)
            row['status'] = 'modified' if row['files'] else 'clean'
            if any('U' in f['xy'] or f['xy'] in ('AA', 'DD') for f in row['files']):
                row['status'] = 'conflict'
            if core.in_progress(path):
                row.update(status='blocked', reason='Git operation in progress')
            row['pointer_changed'] = bool(row['recorded_commit'] and row['head'] != row['recorded_commit'])
            row['remote'] = self.remote(path, row['branch'])
            try:
                tracking = core.upstream(path)[3]
                row['upstream'] = tracking.removeprefix('refs/remotes/')
                row['ahead'], row['behind'] = map(int, core.text(path, 'rev-list', '--left-right', '--count', 'HEAD...' + tracking).split())
            except (ValueError, OSError):
                pass
        except (ValueError, OSError):
            row.update(status='blocked', reason='cannot inspect repository')
        return row

    def role(self, name):
        return self.ui.resources.git_style(name)

    def branch(self, row):
        return 'detached ' + row['head'][:8] if row['detached'] else self.ui.branch_label(row['branch'])

    def repository_label(self, row, label):
        return self.ui.repository_label(row['path'], label, (row['remote'] or {}).get('host'))

    def info(self, row, full_paths=False):
        ui = self.ui
        path = Path(row['path'])
        ui.repository_detail('Repository', path, path.name, self.role('repo_owned' if row['remote'] and row['remote']['owned'] else 'repo'), (row['remote'] or {}).get('host'))
        if 'selector' in row:
            ui.detail('Selector', row['selector'] or 'ambiguous; use the exact path')
        if ui.human:
            ui.resource_detail('Path', path, display=str(path) if full_paths else ui.path(path), kind='dir')
        else:
            ui.repository_detail('Path', path, str(path) if full_paths else ui.path(path), self.role('repo_owned' if row['remote'] and row['remote']['owned'] else 'repo'), (row['remote'] or {}).get('host'))
        self.remote_details(row)
        ui.detail('Branch', self.branch(row), self.role('detached' if row['detached'] else 'branch'))
        ui.detail('HEAD', row['head'] or ('unborn' if row['availability'] == 'available' else 'unavailable'))
        ui.detail('Upstream', ui.branch_label(row['upstream']), self.role('branch'))
        ui.detail('Status', row['status'], self.role(row['status']))
        ui.detail('Changes', f"{sum(f['xy'][0] not in (' ', '?') for f in row['files'])} staged / "
                  f"{sum(f['xy'][1] != ' ' and f['xy'] != '??' for f in row['files'])} unstaged / "
                  f"{sum(f['xy'] == '??' for f in row['files'])} untracked")
        if row['ahead'] is None:
            ui.detail('Tracking', 'unknown (cached)', '2')
        else:
            ui.detail_spans('Tracking', [(str(row['ahead']) + ' ahead', self.role('ahead')), (' / ', None),
                                        (str(row['behind']) + ' behind', self.role('behind')), (' (cached)', '2')])
        if row['reason']:
            ui.detail('Reason', row['reason'], '93')
        if 'submodules' in row:
            counts = row['submodules']
            ui.detail('Submodules', f"{counts['total']} discovered / {counts['available']} available / {counts['missing']} missing / {counts['blocked']} blocked")
            if row['depth_limited']:
                ui.detail('Depth', 'Descendant counts cover the requested depth only.')

    def remote_details(self, row, ui=None):
        ui = self.ui if ui is None else ui
        remote = row['remote']
        if not remote:
            return
        icon = host_icon(remote['host'])
        ui.detail('Remote', remote['name'] or 'none')
        ui.detail_spans('URL', [((icon + ' ' if ui.icons and remote['url'] else '') + (remote['url'] or 'unavailable'), None)])
        ui.detail('Owner', remote['owner'] or 'unavailable')
        owned = remote['owned']
        ui.detail('Owned', ('yes' if owned else 'no') if owned is not None else remote['ownership'] if remote['ownership'] != 'configured' else 'unavailable')

    def status_details(self, row, full_paths):
        self.ui.detail('Branch', self.branch(row), self.role('detached' if row['detached'] else 'branch'))
        self.ui.detail('Status', row['status'], self.role(row['status']))
        if row['pointer_changed']:
            self.ui.detail('Pointer', 'differs from parent index', self.role('modified'))
        if row['reason']:
            self.ui.detail('Reason', row['reason'], '93')
        if row['ahead'] is not None:
            self.ui.detail_spans('Tracking', [(str(row['ahead']) + ' ahead', self.role('ahead')), (' / ', None),
                                           (str(row['behind']) + ' behind', self.role('behind')), (' (cached)', '2')])
        for file in row['files']:
            path = Path(row['path']) / file['path']
            self.ui.resource_detail(core.Workflow.file_label(file['xy']), path,
                                    display=str(path) if full_paths else file['path'],
                                    label_code=self.role(core.Workflow.file_role(file['xy'])))
            if file['old_path']:
                old = Path(row['path']) / file['old_path']
                self.ui.resource_detail('From', old, display=str(old) if full_paths else file['old_path'])


class Tree:
    """Human-only tree gutters; discovery and redirected output stay independent."""
    def __init__(self, view, rows):
        self.view, self.ui = view, view.ui
        self.by_path = {row['path']: row for row in rows}
        self.last = {row['parent']: row['path'] for row in rows}
        self.vertical = '│' if self.ui.icons else '|'

    def clip(self, prefix):
        # Leave enough room for the shared detail renderer on narrow terminals.
        limit = max(4, min(self.ui.width // 2, self.ui.width - 24) // 4 * 4)
        if len(prefix) > limit:
            return '... ' + (prefix[-(limit - 4):] if limit > 4 else '')
        return prefix

    def header(self, base, full_paths):
        label = self.ui.repository_label(base, str(base) if full_paths else base.name)
        self.ui._spans([('Repository ', '94'), (label, self.view.role('repo'))],
                       self.vertical + '   ', '2', continuation_prefix=self.vertical + '   ')

    def row(self, row, full_paths, details):
        ui, view = self.ui, self.view
        columns, parent = [], row['parent']
        while parent in self.by_path:
            ancestor = self.by_path[parent]
            columns.append('    ' if self.last[ancestor['parent']] == parent else self.vertical + '   ')
            parent = ancestor['parent']
        ancestors = ''.join(reversed(columns))
        final = self.last[row['parent']] == row['path']
        branch = ('└── ' if final else '├── ') if ui.icons else ('`-- ' if final else '|-- ')
        first = self.clip(ancestors + branch)
        continuation = ancestors + ('    ' if final else self.vertical + '   ')
        if row['path'] in self.last:
            continuation += self.vertical + '   '
        continuation = self.clip(continuation)
        ui.emit(ui.paint(self.clip(ancestors + self.vertical + '   ').rstrip(), '2'))
        label = view.repository_label(row, row['path'] if full_paths else row['relative_path'])
        identity = (label, view.role('repo_owned' if row['remote'] and row['remote']['owned'] else 'repo'))
        metadata = [(view.branch(row), view.role('detached' if row['detached'] else 'branch')),
                    ('  ' + row['status'], view.role(row['status']))]
        if row['pointer_changed']:
            metadata.append(('  pointer changed', view.role('modified')))
        if cells(ui.clean(first + label + '  ' + ''.join(text for text, _ in metadata))) > ui.width:
            ui._spans([identity], first, '2', continuation_prefix=continuation)
            ui._spans(metadata, continuation, '2', continuation_prefix=continuation)
        else:
            ui._spans([identity, ('  ', None), *metadata], first, '2', continuation_prefix=continuation)
        # Compose a gutter with ordinary detail rows, reserving its width before
        # wrapping. No ANSI parsing or modification of already-rendered content.
        detail_ui = copy.copy(ui)
        detail_ui.width = ui.width - cells(continuation)
        detail_ui.emit = lambda value='': ui.emit(ui.paint(continuation, '2') + value)
        if row['reason']:
            detail_ui.detail('Reason', row['reason'], '93')
        if details:
            view.remote_details(row, detail_ui)
            detail_ui.detail('Recorded', row['recorded_commit'])
            detail_ui.detail('Current', row['head'] or 'unavailable')


def describe_collection(rows, base, limited):
    by_path = {row['path']: row for row in rows}
    siblings = {}
    for row in rows:
        key = (row['parent'], Path(row['path']).name)
        siblings[key] = siblings.get(key, 0) + 1
    for row in rows:
        name = Path(row['path']).name
        parent = by_path.get(row['parent'])
        prefix = parent.get('selector') if parent else ''
        valid = siblings[row['parent'], name] == 1 and name not in ('.', '..') and not any(c in name for c in ':\\/')
        row['selector'] = (prefix + ':' if prefix else '') + name if valid and prefix is not None else None
        row['submodules'] = dict(total=0, available=0, missing=0, blocked=0)
        row['depth_limited'] = row['path'] in limited
    for row in reversed(rows):
        parent = by_path.get(row['parent'])
        if parent:
            for key, count in row['submodules'].items():
                parent['submodules'][key] += count
            parent['submodules']['total'] += 1
            parent['submodules'][row['availability']] += 1
            parent['depth_limited'] |= row['depth_limited']


def positive(value):
    if not value.isdecimal() or int(value) < 1:
        raise argparse.ArgumentTypeError('depth must be a positive integer')
    return int(value)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise core.UsageError(message)


def main(argv=None, info_edge=None):
    parser = Parser(description=__doc__)
    parser.add_argument('command', choices=('info', 'submodules', 'submodules-info', 'status', '_select', '_complete'))
    parser.add_argument('-C', '--directory', default=os.environ.get('DOTS') or str(core.LIB.parents[1]))
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--full-paths', action='store_true')
    parser.add_argument('--depth', type=positive)
    parser.add_argument('--details', action='store_true')
    parser.add_argument('--dirty', action='store_true')
    parser.add_argument('--all-submodules', action='store_true')
    parser.add_argument('--no-wiki', action='store_true')
    parser.add_argument('path', nargs='?')
    args = parser.parse_intermixed_args(argv)
    if args.command not in ('submodules', 'submodules-info') and args.depth is not None:
        parser.error('--depth requires git submodules or git submodules info')
    if args.command != 'submodules' and args.details:
        parser.error('--details requires git submodules')
    if args.command != 'status' and args.dirty:
        parser.error('--dirty requires git submodules status')
    if args.command not in ('status', '_select') and args.path is not None:
        parser.error('this command does not accept a PATH')
    if args.command != '_select' and args.all_submodules:
        parser.error('--all-submodules requires git submodules publish')
    base = context(args.directory)
    if info_edge is not None:
        base = Path(info_edge['path'])
        args.directory = str(base)
    if args.command == '_select':
        rows = selection(base, args.path, args.all_submodules)
        fields = [selection_hash(rows)]
        for row in rows:
            fields.extend(row[key] for key in ('path', 'parent', 'recorded_commit', 'availability', 'reason'))
        sys.stdout.buffer.write(b''.join(os.fsencode(field) + b'\0' for field in fields))
        return 0
    if args.command == '_complete':
        rows, _, _ = discover(base)
        for row in rows:
            value = row['relative_path']
            if row['availability'] != 'blocked' and not any(ord(c) < 32 or ord(c) == 127 for c in value):
                print('./' + value if value.startswith('-') else value)
        return 0
    core.configure(not args.json)
    view = Inspection(base)
    selected = selection(base, args.path)[0] if args.path is not None else None
    with core.Progress('Discovering submodules'):
        if info_edge is not None and info_edge['availability'] != 'available':
            rows, errors, limited = [], [], []
        elif selected and selected['availability'] == 'available':
            rows, errors, limited = discover(Path(selected['path']))
            for row in rows:
                row['relative_path'] = os.path.relpath(row['path'], base).replace(os.sep, '/')
                row['depth'] += selected['depth']
            rows.insert(0, selected)
        elif selected:
            rows, errors, limited = [selected], [], []
        else:
            rows, errors, limited = discover(base, args.depth)
    counts = {state: sum(row['availability'] == state for row in rows) for state in ('available', 'missing', 'blocked')}
    counts['total'] = len(rows)
    root_row = dict(path=str(base), parent=None, relative_path='.', depth=0, recorded_commit=None, availability='available', reason='')
    if info_edge is not None:
        root_row.update(availability=info_edge['availability'], reason=info_edge['reason'])
    with core.Progress('Inspecting repositories') as progress:
        inspected = []
        inputs = [root_row] if args.command == 'info' else rows
        for i, row in enumerate(inputs):
            inspected.append(view.inspect(row))
            progress.update('Inspecting repositories', i + 1, len(inputs))
    complete = not errors and not counts['missing'] and not counts['blocked'] and all(r['status'] not in ('blocked', 'missing') for r in inspected)
    if args.command == 'submodules-info':
        describe_collection(inspected, base, limited)
    if args.dirty:
        inspected = [row for row in inspected if row['files'] or row['pointer_changed'] or row['status'] in ('missing', 'blocked', 'conflict')]
    data = dict(schema=1, command='submodules status' if args.command == 'status' else args.command.replace('-', ' '),
                base=str(base), selection=selected['path'] if selected else None, remote_state='cached', complete=complete,
                depth_limit=args.depth, depth_limited=bool(limited), submodules=counts, errors=errors, repositories=inspected)
    companion_rows=[]
    if args.command=='info' and info_edge is None and not args.no_wiki:
        from wiki_git import association
        companion=association(base)
        if companion:
            companion_rows.append(companion)
            if companion['availability']=='available':
                companion['repository']=view.inspect(dict(path=companion['path'],parent=None,relative_path='wiki',depth=0,recorded_commit=None,availability='available',reason=''))
        data['companions']=companion_rows
    if args.json:
        print(json.dumps(data, ensure_ascii=True))
        return int(not complete)
    ui = view.ui
    ui.heading('Git info' if args.command == 'info' else 'Git submodule info' if args.command == 'submodules-info' else 'Git submodule status' if args.command == 'status' else 'Git submodules')
    if args.command == 'info':
        view.info(inspected[0], args.full_paths)
        for companion in companion_rows:
            ui.emit();ui.detail('Companion','wiki ('+companion['availability']+')')
            ui.resource_detail('Path',companion['path'],kind='dir')
            if companion.get('repository'): view.info(companion['repository'],args.full_paths)
            else: ui.detail('Hint',companion['reason'])
    else:
        tree = Tree(view, inspected) if args.command == 'submodules' and ui.human and inspected else None
        if tree:
            tree.header(base, args.full_paths)
        else:
            ui.repository_detail('Repository', base, str(base) if args.full_paths else base.name, view.role('repo'))
        last = {}
        for row in inspected:
            last[row['parent']] = row['path']
        by_path = {row['path']: row for row in inspected}
        for row in inspected:
            if tree:
                tree.row(row, args.full_paths, args.details)
                continue
            ui.emit()
            label = view.repository_label(row, row['path'] if args.full_paths else row['relative_path'])
            if args.command == 'submodules-info':
                view.info(row, args.full_paths)
            elif args.command == 'submodules':
                chain, parent = [], row['parent']
                while parent in by_path:
                    ancestor = by_path[parent]
                    chain.append(('    ' if last[ancestor['parent']] == parent else '│   ' if ui.icons else '|   '))
                    parent = ancestor['parent']
                connector = ''.join(reversed(chain)) + (('└── ' if ui.icons else '`-- ') if last[row['parent']] == row['path'] else ('├── ' if ui.icons else '|-- '))
                if len(connector) > ui.width // 2:
                    connector = '... ' + connector[-(ui.width // 2 - 4):]
                spans = [(connector, '2'), (label, view.role('repo_owned' if row['remote'] and row['remote']['owned'] else 'repo')),
                         ('  ' + view.branch(row), view.role('detached' if row['detached'] else 'branch')),
                         ('  ' + row['status'], view.role(row['status']))]
                if row['pointer_changed']:
                    spans.append(('  pointer changed', view.role('modified')))
                if cells(ui.clean(''.join(text for text, _ in spans))) > ui.width:
                    ui._spans([spans[1]], connector, '2')
                    metadata = [(text.lstrip() if i == 0 else text, code) for i, (text, code) in enumerate(spans[2:])]
                    ui._spans(metadata, ' ' * len(connector))
                else:
                    ui.heading_spans(spans)
                if row['reason']:
                    ui.detail('Reason', row['reason'], '93')
                if args.details:
                    view.remote_details(row)
                    ui.detail('Recorded', row['recorded_commit'])
                    ui.detail('Current', row['head'] or 'unavailable')
            else:
                ui.detail_spans('Repository', [(label, view.role('repo_owned' if row['remote'] and row['remote']['owned'] else 'repo'))])
                view.status_details(row, args.full_paths)
        if not inspected:
            ui.detail('Result', 'No matching submodule changes.' if args.dirty else 'No registered submodules.')
    ui.emit()
    ui.detail('Submodules', f"{counts['total']} discovered / {counts['available']} available / {counts['missing']} missing / {counts['blocked']} blocked")
    if args.depth:
        ui.detail('Depth', f'{args.depth} levels; counts cover this traversal only')
    for error in errors:
        ui.detail('Blocked', error['path'] + ': ' + error['reason'], '91')
    if not complete:
        ui.detail('Result', 'Incomplete; unavailable descendants remain unknown.', '93')
    if args.command == 'info':
        ui.detail('Tree', 'dots git submodules' + (' -C DIR (same repository)' if args.directory != os.environ.get('DOTS', str(core.LIB.parents[1])) else ''))
    ui.detail('Remote', 'Cached tracking refs; no fetch performed.', '2')
    return int(not complete)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except core.UsageError as error:
        core.Presentation(sys.stderr).detail('Error', str(error), '91')
        sys.exit(2)
    except (OSError, ValueError) as error:
        core.Presentation(sys.stderr).detail('Error', str(error), '91')
        sys.exit(3)
    except KeyboardInterrupt:
        sys.exit(130)
