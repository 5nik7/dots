#!/usr/bin/env python3
"""Config discovery, adoption and reversible catalog-backed file operations."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import sys
import textwrap

from catalog import Catalog, Presentation, read_json, platform, relative, ID
from transactions import Store, digest, exists, parents_safe


class Manager:
    def __init__(self):
        self.root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[3]).resolve()
        self.catalog = Catalog(self.root, platform())
        home = Path(os.environ['HOME'])
        state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state')
        if not state.is_absolute():
            raise ValueError('state root must be absolute')
        self.store = Store(state / 'dots')
        self.config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config') / 'dots/files.json'

    def backup_default(self):
        if not exists(self.config):
            return False
        data = read_json(self.config)
        if set(data) != {'schema', 'backup'} or type(data['backup']) is not bool:
            raise ValueError('files preferences require schema: 1 and boolean backup')
        return data['backup']

    def locations(self):
        rows = []
        for owner in self.catalog.sources:
            if owner['status'] != 'available' or self.catalog.platform not in owner['platforms']:
                continue
            path = Path(owner['root']) / '.dots/file-locations.json'
            if not exists(path):
                continue
            doc = read_json(path)
            if doc.get('repository') != owner['id'] or not isinstance(doc.get('locations'), list):
                raise ValueError('invalid location registry')
            identities = set()
            for item in doc['locations']:
                if item['id'] in identities:
                    raise ValueError('duplicate location ID')
                identities.add(item['id'])
                if not isinstance(item.get('exclusions', []), list) or not all(isinstance(x, str) for x in item.get('exclusions', [])):
                    raise ValueError('location exclusions must be a list of relative globs')
                if not ID.fullmatch(item['id']) or item['kind'] not in ('root', 'file'):
                    raise ValueError('invalid location definition')
                if not self.catalog.applicable(item['platforms']):
                    continue
                source = relative(item['source'])
                if not any(source.is_relative_to(relative(r)) for r in owner['roots']):
                    raise ValueError('location source is outside owning repository roots')
                target = self.catalog.target(item['target'])
                if target:
                    rows.append(dict(item, repository=owner['id'], root=owner['root'], path=target,
                                     exclusions=item.get('exclusions', [])))
        return rows

    def mapping(self, path, repo=None):
        matches = []
        for loc in self.locations():
            if repo and loc['repository'] != repo:
                continue
            base = Path(loc['path'])
            if path == base or (loc['kind'] == 'root' and path.is_relative_to(base)):
                matches.append(loc)
        if not matches:
            raise ValueError('path is not in an eligible registered location: ' + str(path))
        specificity = max(len(Path(x['path']).parts) for x in matches)
        matches = [x for x in matches if len(Path(x['path']).parts) == specificity]
        if len(matches) != 1:
            raise ValueError('ambiguous location ownership; select --repo')
        loc = matches[0]
        suffix = path.relative_to(loc['path'])
        if any(suffix.match(pattern) for pattern in loc['exclusions']):
            raise ValueError('path is excluded by the location registry')
        source = Path(loc['root']) / loc['source']
        if loc['kind'] == 'root':
            source /= suffix
        target = loc['target'].rstrip('/')
        if suffix != Path('.'):
            target += '/' + suffix.as_posix()
        return loc, source, target

    @staticmethod
    def allowed(path):
        # Deliberately conservative; never claim exhaustive secret detection.
        lower = {x.lower() for x in path.parts}
        blocked = {'.git', '.ssh', '.gnupg', '.aws', '.azure', '.bakstore', '__pycache__',
                   'cache', 'caches', 'logs', 'sessions', 'keyrings', 'chromium', 'google-chrome',
                   'firefox', 'chromium-browser', 'dots', 'node_modules',
                   'cacheddata', 'cachedextensionvsixs', 'cachedprofilesdata', 'code cache',
                   'gpucache', 'dawngraphitecache', 'dawnwebgpucache', 'shadercache',
                   'crashpad', 'local storage', 'session storage', 'shared dictionary',
                   'globalstorage', 'workspacestorage'}
        name = path.name.lower()
        parts = [x.lower() for x in path.parts]
        # These app-owned preview/database trees are generated assets, not themes.
        previews = any(a == 'xfcethememanager' and b in
                       {'controls', 'cursors', 'frames', 'icons', 'meta', 'wallpapers'}
                       for a, b in zip(parts, parts[1:]))
        return not (lower & blocked or any(x in name for x in ('credential', 'token', 'secret', '.bak.', '.dots-'))
                    or previews
                    or name in ('hosts.yml', '.env', 'id_rsa', 'id_ed25519', 'history',
                                'cookie', 'cookies', 'cookies-journal', 'globhist',
                                'network persistent state', 'transportsecurity', 'sharedstorage',
                                'dips', 'dips-wal', 'dips-shm', 'machineid')
                    or name.endswith(('.key', '.pem', '.sqlite', '.db', '.log', '.lock', '.swp',
                                      '.bak', '.backup', '.cache', '.boltdb', '.vscdb',
                                      '-database.simple', '-volumes.simple', '-default-sink', '-default-source')))

    def inspect_content(self, path):
        if path.is_symlink():
            raise ValueError('symlink adoption requires manual review: ' + str(path))
        if path.is_dir():
            for child in path.iterdir():
                self.inspect_content(child)
            return
        if not stat.S_ISREG(path.lstat().st_mode) or not self.allowed(path):
            raise ValueError('excluded or unsupported import: ' + str(path))
        # Inspect bounded regular-file chunks without logging their contents.
        with path.open('rb') as stream:
            tail = b''
            for chunk in iter(lambda: stream.read(65536), b''):
                text = tail + chunk
                if re.search(rb'(?i)(BEGIN [A-Z ]*PRIVATE KEY|(?:password|api[_-]?key|access[_-]?token)\s*[=:]\s*["\']?[^\s"\']{4,})', text):
                    raise ValueError('possible credential material; import refused: ' + str(path))
                tail = text[-256:]

    def system(self, repo=None):
        claims = {r['target']: r for r in self.catalog.records() if r['target']}
        rows, seen = [], set()
        for loc in self.locations():
            if repo and loc['repository'] != repo:
                continue
            base = Path(loc['path'])
            pending = [base]
            while pending:
                path = pending.pop()
                if str(path) in seen or not exists(path):
                    continue
                seen.add(str(path))
                if str(path) in claims:
                    rows.append({'path': str(path), 'status': 'managed', 'repository': claims[str(path)]['repository']})
                    continue
                try:
                    self.mapping(path, repo)
                except ValueError:
                    rows.append({'path': str(path), 'status': 'excluded', 'repository': loc['repository']})
                    continue
                if not self.allowed(path) or path.is_symlink():
                    rows.append({'path': str(path), 'status': 'excluded', 'repository': loc['repository']})
                    continue
                if path.is_dir():
                    try:
                        pending.extend(reversed(sorted(path.iterdir())))
                    except OSError:
                        rows.append({'path': str(path), 'status': 'unavailable', 'repository': loc['repository']})
                else:
                    try:
                        owner, source, target = self.mapping(path, repo)
                        status = 'existing-source' if exists(source) else 'candidate'
                        if not stat.S_ISREG(path.lstat().st_mode):
                            status = 'excluded'
                        rows.append({'path': str(path), 'source': str(source), 'target': target,
                                     'repository': owner['repository'], 'status': status})
                    except ValueError:
                        rows.append({'path': str(path), 'status': 'excluded', 'repository': loc['repository']})
        return sorted(rows, key=lambda x: x['path'])

    def plan(self, args):
        ops, guards, docs, views = [], {}, {}, []
        records = self.catalog.records()
        owners = {x['id']: x for x in self.catalog.sources if x['status'] == 'available'}
        def guard(path):
            parents_safe(path)
            guards[str(path)] = digest(path)
        def document(owner):
            path = Path(owner['root']) / '.dots/files.json'
            if str(path) not in docs:
                guard(path)
                docs[str(path)] = self.catalog.manifest(owner)
            return docs[str(path)]
        def operation(path, **kwargs):
            path = Path(path)
            if path.is_relative_to(self.store.state) or self.store.state.is_relative_to(path):
                raise ValueError('operation overlaps the state store')
            if any(x['path'] == str(path) for x in ops):
                raise ValueError('overlapping operation paths')
            guard(path)
            ops.append(dict(path=str(path), **kwargs))
        if args.action == 'add':
            paths = list(args.values)
            if args.scan:
                if paths:
                    raise ValueError('choose paths or --scan')
                paths = [x['path'] for x in self.system(args.repo) if x['status'] in ('candidate', 'existing-source')]
            expanded = []
            for value in paths:
                path = Path(os.path.abspath(value))
                parents_safe(path)
                if path.is_symlink():
                    match = next((r for r in records if r['target'] == str(path) and r['status'] == 'linked'), None)
                    if match:
                        views.append({'path': str(path), 'status': 'unchanged'})
                        continue
                    raise ValueError('refusing adoption of an unrelated symlink')
                if path.is_dir() and not args.directory_link:
                    for current, directories, files in os.walk(path, followlinks=False):
                        if any((Path(current) / d).is_symlink() for d in directories):
                            raise ValueError('directory contains symlinks; review individual files')
                        expanded.extend(Path(current) / name for name in sorted(files))
                else:
                    expanded.append(path)
            for path in sorted(set(expanded)):
                self.inspect_content(path)
                loc, source, target = self.mapping(path, args.repo)
                self.catalog.target(target)  # Validate generated target before any mutation.
                owner = owners[loc['repository']]
                # Never adopt into a nested repository through its parent owner.
                for other in self.catalog.sources:
                    child = Path(other['root'])
                    if child != Path(owner['root']) and child.is_relative_to(owner['root']) and source.is_relative_to(child):
                        raise ValueError('select the owning submodule for this source')
                for row in records:
                    target_path = Path(row['target']) if row['target'] else None
                    if target_path and (path == target_path or (row['strategy'] == 'directory-link' and path.is_relative_to(target_path)) or (path.is_dir() and target_path.is_relative_to(path))):
                        raise ValueError('target is already claimed: ' + row['id'])
                if path == source or source.is_relative_to(path) or path.is_relative_to(source):
                    raise ValueError('source and target overlap')
                guard(path)
                guard(source)
                if exists(source):
                    if digest(source) != digest(path):
                        raise ValueError('different repository source already exists: ' + str(source))
                else:
                    operation(source, source=str(path))
                operation(path, link=str(source))
                doc = document(owner)
                rel = source.relative_to(owner['root']).as_posix()
                slug = re.sub('[^a-z0-9_-]+', '-', rel.lower()).strip('-')
                identity = 'file-' + slug
                if any(x['id'] == identity or x['source'] == rel for x in doc['resources']):
                    raise ValueError('resource ID or source already tracked')
                doc['resources'].append({'id': identity, 'source': rel, 'target': target,
                    'app': 'config', 'category': 'config', 'platforms': loc['platforms'],
                    'strategy': 'directory-link' if path.is_dir() else 'link'})
                views.append({'path': str(path), 'source': str(source), 'id': owner['id'] + ':' + identity, 'status': 'import-and-link'})
        else:
            for identity in dict.fromkeys(args.values):
                row = next((r for r in records if r['id'] == identity), None)
                if not row or not row['applicable'] or not row['target'] or row['status'] in ('conflict', 'replaced', 'replacement-unavailable'):
                    raise ValueError('select an applicable, unambiguous resource: ' + identity)
                source, target = Path(row['source']), Path(row['target'])
                if (args.action == 'link' or target.is_symlink()) and (not source.exists() or source.is_symlink()):
                    raise ValueError('source must be an existing regular file or owned directory')
                guard(source)
                if target == source or source.is_relative_to(target) or target.is_relative_to(source):
                    raise ValueError('source and target overlap')
                if target.is_symlink() and target.resolve() != source.resolve():
                    raise ValueError('unrelated or theme-generated link is protected: ' + str(target))
                if args.action == 'link':
                    if row['strategy'] == 'copy':
                        raise ValueError('resource requests copy; change metadata explicitly before linking')
                    if target.is_symlink():
                        views.append({'path': str(target), 'status': 'unchanged'})
                        continue
                    if exists(target) and not args.backup:
                        raise ValueError('existing target requires --backup: ' + str(target))
                    operation(target, link=str(source))
                else:
                    if target.is_symlink():
                        if source.is_dir():
                            for node in source.rglob('*'):
                                if node.is_symlink() or node.name == '.git':
                                    raise ValueError('directory contains links or Git metadata; materialize it manually')
                        operation(target, source=str(source))
                    doc = document(owners[row['repository']])
                    doc['resources'] = [x for x in doc['resources'] if x['id'] != identity.split(':', 1)[1]]
                views.append({'path': str(target), 'source': str(source), 'id': identity, 'status': args.action})
        for path, doc in docs.items():
            doc['resources'].sort(key=lambda x: x['id'])
            operation(path, data=doc)
        # Reject batch ancestor/descendant replacements, including directory imports.
        for i, left in enumerate(ops):
            for right in ops[i+1:]:
                a, b = Path(left['path']), Path(right['path'])
                if a.is_relative_to(b) or b.is_relative_to(a):
                    raise ValueError('overlapping batch operations')
        return ops, guards, list(docs), views


def show(title, rows, stream=None):
    ui = Presentation(stream)
    ui.heading(title)
    for row in rows:
        ui.emit('  ' + ui.paint(row.get('id') or ui.path(row.get('path', '')), '1;94') + '  ' + ui.status(row.get('status', 'available')))
        if row.get('created'):
            ui.detail('Created', row['created'])
        if row.get('action'):
            ui.detail('Operation', row['action'])
        if row.get('source'):
            ui.detail('Source', ui.path(row['source']))
        if row.get('path'):
            ui.detail('Target', ui.path(row['path']))
    if not rows:
        ui.emit('  No matching items.')


def show_system(rows, locations, verbose=False, include_all=False):
    """Compact human projection only; discovery records stay complete for JSON."""
    ui = Presentation()
    counts = Counter(row['status'] for row in rows)
    visible = [r for r in rows if include_all or r['status'] not in ('managed', 'excluded')]

    def line(value, code='90', indent='  '):
        for part in textwrap.wrap(ui.clean(value), width=ui.width-len(indent),
                                  break_on_hyphens=False, replace_whitespace=False) or ['']:
            ui.emit(indent + ui.paint(part, code))

    def statuses(items):
        for status, count in sorted(Counter(x['status'] for x in items).items()):
            ui.emit('    ' + ui.paint(str(count), '96') + ' ' + ui.status(status))

    ui.heading('System configs')
    line(' / '.join(f'{counts[s]} {s.replace("-", " ")}' for s in
                   ('candidate', 'existing-source', 'managed', 'excluded', 'unavailable') if counts[s]), '96')
    if verbose:
        for row in visible:
            line(ui.path(row['path']), '95')
            ui.emit('    ' + ui.paint(row['repository'], '94') + '  ' + ui.status(row['status']))
            if row.get('source'):
                ui.detail('Source', ui.path(row['source']))
    else:
        groups = {}
        for row in visible:
            path = Path(row['path'])
            matches = [loc for loc in locations if loc['repository'] == row['repository']
                       and (path == Path(loc['path']) or
                            (loc['kind'] == 'root' and path.is_relative_to(loc['path'])))]
            if matches:
                loc = max(matches, key=lambda x: len(Path(x['path']).parts))
                suffix = path.relative_to(loc['path'])
                if loc['kind'] == 'root' and len(suffix.parts) > 1:
                    path = Path(loc['path']) / suffix.parts[0]
            groups.setdefault((str(path), row['repository']), []).append(row)
        for (path, repository), items in sorted(groups.items()):
            label = ui.clean(ui.path(path))
            badges = ', '.join(ui.paint(str(n), '96') + ' ' + ui.status(s)
                               for s, n in sorted(Counter(x['status'] for x in items).items()))
            rendered = ('  ' + ui.paint(label, '95') + '  ' +
                        ui.paint(repository, '94') + ' / ' + badges)
            if len(re.sub(r'\x1b\[[0-9;]*m', '', rendered)) <= ui.width:
                ui.emit(rendered)
                continue
            line(label, '95')
            line(repository, '94', '    ')
            statuses(items)
    if not visible:
        line('No config candidates found.' if not include_all else 'No matching items.', '94')
    hidden = sum(counts[s] for s in ('managed', 'excluded')) if not include_all else 0
    if hidden:
        line('Managed/excluded entries hidden; use --all to include them.')
    if not verbose and visible:
        line('Use --verbose for individual files and source mappings.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['locations', 'system', 'add', 'link', 'remove', 'history', 'undo', 'recover', 'backups-list', 'backups-show', 'backups-restore'])
    parser.add_argument('values', nargs='*')
    parser.add_argument('--repo')
    parser.add_argument('--scan', action='store_true')
    parser.add_argument('--directory-link', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--all', dest='include_all', action='store_true')
    backups = parser.add_mutually_exclusive_group()
    backups.add_argument('--backup', action='store_true', default=None)
    backups.add_argument('--no-backup', dest='backup', action='store_false')
    args = parser.parse_args()
    if args.action != 'system' and (args.verbose or args.include_all):
        parser.error('--verbose and --all require discover --system')
    if args.action != 'add' and (args.scan or args.directory_link):
        parser.error('--scan and --directory-link require add')
    if args.scan and args.directory_link:
        parser.error('--directory-link requires explicit directory paths')
    if args.action in ('locations', 'system', 'history', 'backups-list') and args.values:
        parser.error('this inspection command takes no positional arguments')
    manager = Manager()
    if manager.catalog.platform == 'windows':
        raise ValueError('native Windows managed operations are not implemented')
    if args.action in ('locations', 'system', 'history', 'backups-list', 'backups-show'):
        if args.action == 'locations':
            rows = [dict(x, status='available' if exists(x['path']) else 'missing') for x in manager.locations()]
        elif args.action == 'system':
            rows = manager.system(args.repo)
        elif args.action == 'history':
            rows = manager.store.records()
        else:
            rows = [read_json(p) for p in sorted(manager.store.backups.glob('*.json'))] if manager.store.backups.exists() else []
            if args.action == 'backups-show':
                if len(args.values) != 1:
                    parser.error('show requires one backup ID')
                rows = [x for x in rows if x['id'] == args.values[0]]
                if not rows:
                    raise ValueError('backup not found')
        if args.json:
            print(json.dumps({'schema': 1, 'items': rows}, ensure_ascii=True))
        elif args.action == 'system':
            show_system(rows, manager.locations(), args.verbose, args.include_all)
        else:
            show(args.action.replace('-', ' ').title(), rows)
            if args.action == 'backups-show':
                show('Protected objects', [dict(x, status='backed-up') for x in rows[0]['objects']])
        return
    if args.backup is None:
        args.backup = manager.backup_default()
    if args.action in ('undo', 'recover', 'backups-restore'):
        if len(args.values) != 1:
            parser.error('one transaction or backup ID is required')
        identity = args.values[0]
        if args.action == 'recover':
            doc = manager.store.load(identity)
            if doc['status'] not in ('preparing', 'applying', 'rolling-back', 'recovery-required'):
                raise ValueError('transaction does not need recovery')
            ops, guards, catalogs = [], {}, doc['catalogs']
            views = [dict(x, status='recover') for x in doc['operations']]
        elif args.action == 'undo':
            ops, guards, catalogs = manager.store.inverse(identity)
            views = [dict(x, status='undo') for x in ops]
        else:
            record = read_json(manager.store.backups / (identity + '.json')) if re.fullmatch('[a-f0-9]{32}', identity) else None
            if not record:
                raise ValueError('invalid backup ID')
            doc = manager.store.load(identity)
            if doc['status'] != 'complete':
                raise ValueError('backup transaction is not complete')
            ops, guards, catalogs, views = [], {}, [], []
            for i, entry in enumerate(doc['operations']):
                # Restore data objects; catalog changes belong to undo, not restore.
                if entry['before'] is None or entry['path'] in doc['catalogs']:
                    continue
                path = entry['path']
                current = digest(path)
                if current == entry['before']:
                    continue
                if current != entry['after'] and current is not None and not args.backup:
                    raise ValueError('changed restore target requires --backup')
                source = manager.store.root / identity / f'{i}-before'
                if digest(source) != entry['before']:
                    raise ValueError('backup failed verification')
                ops.append({'path': path, 'source': str(source)})
                guards[path] = current
                guards[str(source)] = entry['before']
                views.append({'path': path, 'status': 'restore'})
    else:
        if not args.values and not (args.action == 'add' and args.scan):
            parser.error('select paths or qualified resource IDs')
        ops, guards, catalogs, views = manager.plan(args)
    preview = {'schema': 1, 'action': args.action, 'dry_run': args.dry_run, 'backup': args.backup, 'items': views}
    if args.dry_run:
        if args.json:
            print(json.dumps(preview))
        else:
            show('File operation preview', views)
            print('  Preview only; no changes made. Retained backups: ' + ('enabled' if args.backup else 'disabled'))
        return
    stream = sys.stderr if args.json else sys.stdout
    show('File operation preview', views, stream)
    print('  Retained backups: ' + ('enabled' if args.backup else 'disabled'), file=stream)
    if not args.yes:
        if not sys.stdin.isatty():
            parser.error('use --dry-run to inspect or --yes to apply without a terminal')
        print('Apply these changes? [y/N] ', end='', file=sys.stderr, flush=True)
        if input().lower() != 'y':
            if args.json:
                print(json.dumps(dict(preview, status='cancelled')))
            else:
                print('Cancelled; no changes made.')
            return
    if args.action == 'recover':
        result = manager.store.recover(args.values[0])
    else:
        result = manager.store.apply(args.action, ops, guards, args.backup, catalogs)
    if args.json:
        print(json.dumps(result))
    else:
        ui = Presentation()
        ui.heading('File operation ' + result['status'])
        if result.get('id'):
            ui.detail('Transaction', result['id'])
            if args.backup:
                ui.detail('Backup', result['id'])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('Interrupted; inspect dots files history for recovery status.', '93'))
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots files: ' + str(error), '91'))
        sys.exit(1)
