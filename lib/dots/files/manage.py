#!/usr/bin/env python3
"""Config discovery, adoption and reversible catalog-backed file operations."""
from identities import canonical, validate_cli
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import sys
import textwrap

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from interaction import gum_confirm, SelectionEnded
from progress import Progress, configure, tracked, sequence, permanent_output

from catalog import Catalog, Presentation, read_json, platform, relative, ID
from events import OperationOutput
from transactions import Store, digest, exists, parents_safe
from file_platform import state_root, config_root
from path_operands import SourceRequired, UnknownLocation, adoption, link_operands, operand


class Manager:
    def __init__(self, catalog=None):
        self.root = (catalog.root if catalog is not None else Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[3])).resolve()
        self.catalog = catalog or Catalog(self.root, platform())
        home = Path(os.environ.get('HOME') or Path.home())
        state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state')
        if not state.is_absolute():
            raise ValueError('state root must be absolute')
        self.store = Store(state_root())
        from profile_config import config_path
        self.config = config_path('files.json', self.root)

    def backup_default(self):
        from profile_config import settings
        value = settings(self.root).get('files.backup')
        if value is not None: return value['value']
        if not exists(self.config):
            return False
        data = read_json(self.config)
        if set(data) != {'schema', 'backup'} or type(data['backup']) is not bool:
            raise ValueError('files preferences require schema: 1 and boolean backup')
        return data['backup']

    def locations(self):
        rows = []
        for owner in self.catalog.sources:
            if owner['id'] == 'theme' or owner['status'] != 'available' or self.catalog.platform not in owner['platforms']:
                continue
            path = Path(owner['root']) / '.dots/file-locations.json'
            if not exists(path):
                continue
            doc = read_json(path)
            if canonical(doc.get('repository')) != owner['id'] or not isinstance(doc.get('locations'), list):
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
            raise UnknownLocation('path is not in an eligible registered location: ' + str(path))
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
        if not self.allowed(path):
            raise ValueError('excluded or unsupported import: ' + str(path))
        if path.is_symlink():
            raise ValueError('symlink adoption requires manual review: ' + str(path))
        if path.is_dir():
            for child in path.iterdir():
                self.inspect_content(child)
            return
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('excluded or unsupported import: ' + str(path))
        # Inspect bounded regular-file chunks without logging their contents.
        with path.open('rb') as stream:
            tail = b''
            for chunk in iter(lambda: stream.read(65536), b''):
                text = tail + chunk
                if re.search(rb'(?i)(BEGIN [A-Z ]*PRIVATE KEY|(?:password|api[_-]?key|access[_-]?token)\s*[=:]\s*["\']?[^\s"\']{4,})', text):
                    raise ValueError('possible credential material; import refused: ' + str(path))
                tail = text[-256:]

    @tracked('Discovering system configs')
    def system(self, repo=None):
        from registration import Registration
        registration = Registration(self)
        claims = {r['target']: r for r in self.catalog.records() if r['target'] and r['enabled'] and r['applicable'] and r['status'] != 'replaced'}
        rows, seen = [], set()
        for loc in self.locations():
            imports_in_scope = not repo or loc['repository'] == repo
            base = Path(loc['path'])
            pending = [base]
            while pending:
                path = pending.pop()
                if str(path) in seen or not exists(path):
                    continue
                seen.add(str(path))
                if str(path) in claims:
                    if not repo or claims[str(path)]['repository'] == repo:
                        rows.append({'path': str(path), 'status': 'managed', 'repository': claims[str(path)]['repository']})
                    continue
                try:
                    self.mapping(path, loc['repository'])
                except ValueError:
                    if imports_in_scope:
                        rows.append({'path': str(path), 'status': 'excluded', 'repository': loc['repository']})
                    continue
                if path.is_symlink():
                    try:
                        rows.append(registration.candidate(path, repo))
                    except (OSError, ValueError) as error:
                        if imports_in_scope:
                            rows.append({'path': str(path), 'status': 'excluded', 'repository': loc['repository'],
                                         'reason': str(error)})
                    continue
                if not self.allowed(path):
                    if imports_in_scope:
                        rows.append({'path': str(path), 'status': 'excluded', 'repository': loc['repository']})
                    continue
                if path.is_dir():
                    try:
                        pending.extend(reversed(sorted(path.iterdir())))
                    except OSError:
                        rows.append({'path': str(path), 'status': 'unavailable', 'repository': loc['repository']})
                else:
                    if not imports_in_scope:
                        continue
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

    @tracked('Planning file operations')
    def plan(self, args):
        self.link_installation = None
        self.registration_receipt = False
        ops, guards, docs, views = [], {}, {}, []
        records = self.catalog.records()
        owners = {x['id']: x for x in self.catalog.sources if x['status'] == 'available'}
        def guard(path):
            parents_safe(path)
            observed = digest(path)
            if guards.setdefault(str(path), observed) != observed:
                raise ValueError('changed during file planning: ' + str(path))
        for path in self.catalog.input_paths():
            guard(path)
        def document(owner):
            if owner['id'] not in docs:
                docs[owner['id']] = self.catalog.manifest(owner)
            return docs[owner['id']]
        def operation(path, **kwargs):
            path = Path(path)
            if path.is_relative_to(self.store.state) or self.store.state.is_relative_to(path):
                raise ValueError('operation overlaps the state store')
            if any(x['path'] == str(path) for x in ops):
                raise ValueError('overlapping operation paths')
            guard(path)
            ops.append(dict(path=str(path), **kwargs))
        registering = args.action in ('add', 'find') or getattr(args, 'link_paths', False)
        if registering:
            from registration import Registration, candidates, global_scope_conflict
            from managed_destination import physical, points_to, theme_artifact, yazi_migration_reason
            registration = Registration(self)
            for owner in self.catalog.sources:
                if owner['id'] != 'theme' and owner['status'] == 'available':
                    guard(Path(owner['root']) / '.dots/file-locations.json')
            paths = list(args.values)
            if args.scan:
                if paths:
                    raise ValueError('choose paths or --scan')
                inventory = candidates(self, args.repo)
                if getattr(args, 'global_files', False):
                    for row in inventory:
                        if reason := global_scope_conflict(row):
                            row.update(status='excluded', reason=reason)
                paths = [x['candidate'] for x in inventory if x['status'] not in ('needs-target', 'excluded')]
                views.extend(dict(x, status='skipped', reason=x.get('reason', x['status']))
                             for x in inventory if x['status'] in ('needs-target', 'excluded'))
            expanded = {}
            registrations = []
            observed = None
            for value in paths:
                path = operand(self.catalog, value)
                target = getattr(args, 'target', None) or getattr(args, 'target_map', {}).get(str(path))
                if not target and not path.is_symlink() and registration.owner(path, args.repo) is not None and observed is None:
                    observed = self.system(args.repo)
                row = registration.candidate(path, args.repo, target, observed or ())
                if row:
                    if getattr(args, 'global_files', False) and (reason := global_scope_conflict(row)):
                        raise ValueError(reason)
                    if args.action == 'add' and getattr(args, 'source', None):
                        expected = adoption(registration, path, args, args.source)[1] if path.is_symlink() else None
                        if str(expected) != row['source'] or row['status'] != 'register-existing-link':
                            raise ValueError('--source differs from the source this path already owns or links to')
                    if getattr(args, 'link_paths', False):
                        if not row['target']:
                            raise ValueError('link target is unavailable on this platform')
                        if not Path(row['target']).parent.is_dir():
                            raise ValueError('link target parent must be an existing directory')
                    if args.action == 'find':
                        expected = args.found[str(path)]
                        if row['status'] != 'register-existing-link' or any(row[key] != expected[key]
                                for key in ('source', 'target', 'strategy')):
                            raise ValueError('link changed after discovery: ' + str(path))
                        row['id'] = expected['id']
                    if not row['target']:
                        if not args.dry_run:
                            raise ValueError(row['reason'] + ' Source: ' + row['source'])
                        views.append(row)
                    else:
                        registrations.append(row)
                    continue
                if args.action != 'add':
                    raise ValueError('link source must be an existing managed source')
                from mappings import target_spec
                target_spec(self.catalog, str(path))
                parents_safe(path)
                if not self.allowed(path):
                    raise ValueError('excluded or unsupported import: ' + str(path))
                if not exists(path):
                    raise ValueError('import path does not exist: ' + str(path))
                chosen = getattr(args, 'source', None) or getattr(args, 'source_map', {}).get(str(path))
                if path.is_dir() and not args.directory_link:
                    for current, directories, files in os.walk(path, followlinks=False):
                        if any((Path(current) / d).is_symlink() for d in directories):
                            raise ValueError('directory contains symlinks; review individual files')
                        for name in sorted(files):
                            child = Path(current) / name
                            relative_child = child.relative_to(path)
                            if chosen and str(chosen).startswith('${'):
                                expanded[child] = str(chosen).rstrip('/') + '/' + relative_child.as_posix()
                            else:
                                expanded[child] = str(Path(chosen) / relative_child) if chosen else None
                else:
                    expanded[path] = chosen
            assigned = {}
            for path, chosen in sorted(expanded.items()):
                try:
                    owner, source, target, eligibility = adoption(registration, path, args, chosen)
                except SourceRequired as error:
                    if not args.dry_run:
                        raise
                    views.append(dict(path=str(path), status='needs-source', reason=str(error)))
                    continue
                self.inspect_content(path)
                self.catalog.target(target)  # Validate generated target before any mutation.
                # Never adopt into a nested repository through its parent owner.
                for other in self.catalog.sources:
                    child = Path(other['root'])
                    if child != Path(owner['root']) and child.is_relative_to(owner['root']) and source.is_relative_to(child):
                        raise ValueError('select the owning submodule for this source')
                for row in records:
                    if not row['enabled']:
                        continue
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
                operation(path, link=str(source), directory=path.is_dir())
                doc = document(owner)
                rel = source.relative_to(owner['root']).as_posix()
                qualified = registration.names.choose(owner['id'], source, target, assigned)
                assigned[qualified] = source, target
                identity = qualified.split(':', 1)[1]
                if any(x['id'] == identity or x['source'] == rel for x in doc['resources']):
                    raise ValueError('resource ID or source already tracked')
                if self.catalog.registry:
                    eligibility = self.catalog.registry.entries.get(qualified, eligibility)
                if not self.catalog.applicable(eligibility):
                    raise ValueError('resource is not eligible for the active platform: ' + qualified)
                doc['resources'].append({'id': identity, 'source': rel, 'target': target,
                    'app': 'config', 'category': 'config', 'platforms': eligibility,
                    'strategy': 'directory-link' if path.is_dir() else 'link'})
                view = dict(path=str(path), source=str(source), id=owner['id'] + ':' + identity, status='import-and-link')
                if self.catalog.flat:
                    view.update(source_spec=self.catalog.source_spec(source), target_spec=target,
                                profile=self.catalog.profile['current'], strategy=doc['resources'][-1]['strategy'])
                views.append(view)
            if registrations:
                registrations = list({(r['source'], r['target']): r for r in registrations}.values())
                registration.assign_ids(registrations, assigned, approved=args.action == 'find')
                from install import Installation
                installation = Installation(self.root)
                installation.operations = ops
                installation.guards.update(guards)
                for row in registrations:
                    source = Path(row['source'])
                    target = physical(Path(row['target']), records, guards)
                    registration.validate_directory(source, row['repository'])
                    if row['repository'] == 'theme':
                        theme_artifact(source, self.catalog.theme_root, guards)
                        if reason := yazi_migration_reason(row, target, installation.entries, guards):
                            raise ValueError(reason)
                        if target.is_symlink() and not points_to(target, source):
                            raise ValueError('theme connector points elsewhere: ' + str(target))
                    else:
                        guard(source)
                    guard(target)
                    previous = next((r for r in records if r['id'] == row['id']), None)
                    if previous:
                        if (not previous['enabled'] or not previous['applicable']
                                or previous['source'] != row['source'] or previous['target'] != row['target']
                                or previous['strategy'] != row['strategy']):
                            raise ValueError('existing mapping differs or is stashed; use files edit/restore: ' + row['id'])
                    else:
                        document_row = document(owners[row['repository']])
                        if any(r['id'] == row['id'].split(':', 1)[1] for r in document_row['resources']):
                            raise ValueError('resource ID already tracked: ' + row['id'])
                        document_row['resources'].append(dict(id=row['id'].split(':', 1)[1],
                            source=source.relative_to(owners[row['repository']]['root']).as_posix(),
                            target=row['target_spec'], strategy=row['strategy'], app=row['app'],
                            category=row['category'], platforms=row['platforms']))
                    if exists(target) and not target.is_symlink() and not args.backup:
                        raise ValueError('existing target requires --backup: ' + str(target))
                    before = len(ops)
                    installation.add(row['id'], target, link=source, directory=source.is_dir())
                    if installation.blocked:
                        raise ValueError('unrelated link or drifted installation target is protected: ' + str(target))
                    self.registration_receipt |= len(ops) != before
                    views.append(dict(row, status='unchanged' if previous and len(ops) == before else row['status']))
                proposed = {r['id']: r for r in Catalog(self.root, self.catalog.platform, docs).records()}
                for row in registrations:
                    current = proposed[row['id']]
                    if current['status'] in ('conflict', 'replaced', 'replacement-unavailable') or not current['applicable']:
                        raise ValueError('resource has conflicting or inactive ownership: ' + row['id'])
                installation.guards.update(guards)
                self.link_installation = installation
            for key, value in registration.guards.items():
                if key in guards and guards[key] != value:
                    raise ValueError('changed during registration: ' + key)
                guards[key] = value
        else:
            for identity in dict.fromkeys(args.values):
                row = next((r for r in records if r['id'] == identity), None)
                if not row and self.catalog.registry and identity in self.catalog.registry.entries:
                    raise ValueError('resource needs a mapping in the selected profile: '+identity)
                if not row or not row['applicable']:
                    raise ValueError('select an applicable, unambiguous resource: ' + identity)
                source = Path(row['source'])
                if args.action == 'remove':
                    doc = document(owners[row['repository']])
                    doc['resources'] = [entry for entry in doc['resources'] if entry['id'] != identity.split(':', 1)[1]]
                    reason = None
                    if row['status'] == 'replaced':
                        reason = 'Destination managed by ' + row['replaced_by']
                    elif row['repository'] != 'theme' and not exists(source):
                        guard(source)
                        if guards[str(source)] is not None:
                            raise ValueError('source changed during removal preview: ' + str(source))
                        reason = 'Repository source is absent'
                    if reason:
                        views.append(dict(id=identity, path=row['target'], source=str(source),
                                          status='remove-mapping', reason=reason))
                        continue
                if args.action == 'link' and not row['enabled']:
                    raise ValueError('resource is stashed; use dots files stash --restore ' + identity)
                if not row['target'] or row['status'] in ('conflict', 'replaced', 'replacement-unavailable'):
                    raise ValueError('select an applicable, unambiguous resource: ' + identity)
                from managed_destination import physical, points_to, theme_artifact, yazi_flavor_directory, yazi_migration_reason
                target = physical(Path(row['target']), records, guards)
                needs_source = args.action == 'link' or target.is_symlink()
                if needs_source and (not source.exists() or source.is_symlink()):
                    raise ValueError('source must be an existing regular file or owned directory')
                if row['repository'] == 'theme':
                    guarded_source = theme_artifact(source, self.catalog.theme_root, guards) if needs_source else None
                    if guarded_source is not None and guarded_source.is_dir() != (row['strategy'] == 'directory-link'):
                        raise ValueError('generated artifact does not match its link strategy: ' + identity)
                else:
                    guarded_source = source
                    guard(source)
                if target == source or source.is_relative_to(target) or target.is_relative_to(source):
                    raise ValueError('source and target overlap')
                if args.action == 'link' and yazi_flavor_directory(row):
                    from install import Installation
                    receipt = Installation(self.root)
                    guards[str(receipt.receipt_path)] = receipt.guards[str(receipt.receipt_path)]
                    if reason := yazi_migration_reason(row, target, receipt.entries, guards):
                        raise ValueError(reason)
                if target.is_symlink() and not points_to(target, source):
                    raise ValueError('unrelated or theme-generated link is protected: ' + str(target))
                if args.action == 'link':
                    if row['strategy'] == 'copy':
                        raise ValueError('resource requests copy; change metadata explicitly before linking')
                    if row['id'] == 'dots:git':
                        from install import Installation
                        from git_platform import plan as plan_git_platform
                        installation = Installation(self.root)
                        if plan_git_platform(installation, row):
                            self.link_installation = installation
                            ops.extend(installation.operations)
                            guards.update(installation.guards)
                            views.extend(dict(item, path=item.get('target')) for item in installation.items)
                    if target.is_symlink():
                        views.append({'path': str(target), 'status': 'unchanged'})
                        continue
                    if exists(target) and not args.backup:
                        raise ValueError('existing target requires --backup: ' + str(target))
                    operation(target, link=str(source), directory=row['strategy'] == 'directory-link')
                else:
                    if target.is_symlink():
                        if source.is_dir():
                            for node in source.rglob('*'):
                                if node.is_symlink() or node.name == '.git':
                                    raise ValueError('directory contains links or Git metadata; materialize it manually')
                        operation(target, source=str(guarded_source))
                views.append({'path': str(target), 'source': str(source), 'id': identity, 'status': args.action})
        for doc in docs.values():
            doc['resources'].sort(key=lambda x: x['id'])
        catalog_ops = self.catalog.updates(docs, update_registry=args.action != 'remove')
        for op in catalog_ops:
            operation(op['path'], data=op['data'])
        # Reject batch ancestor/descendant replacements, including directory imports.
        for i, left in enumerate(ops):
            for right in ops[i+1:]:
                a, b = Path(left['path']), Path(right['path'])
                if a.is_relative_to(b) or b.is_relative_to(a):
                    raise ValueError('overlapping batch operations')
        if getattr(self, 'link_installation', None):
            self.link_installation.operations = ops
            self.link_installation.guards.update(guards)
        return ops, guards, [*self.catalog.lock_paths(), *[op['path'] for op in catalog_ops]], views


def show(title, rows, stream=None):
    from resources import cells
    ui = Presentation(stream)
    ui.heading(title)
    for row in rows:
        identity = ui.paint(row['id'], '1;94') + '  ' if row.get('id') else ''
        status = ui.status(row.get('status', 'available'))
        line = '  ' + identity + status
        if identity and ui.human and cells(re.sub(r'\x1b\[[0-9;]*m', '', line)) > ui.width:
            ui._spans([(row['id'], '1;94')], prefix='  ')
            ui.emit('  ' + status)
        else:
            ui.emit(line)
        if row.get('created'):
            ui.detail('Created', row['created'])
        if row.get('action'):
            ui.detail('Operation', row['action'])
        if row.get('source'):
            ui.resource_detail('Source', row['source'], display=row.get('source_spec') if ui.human else None)
        if row.get('path'):
            ui.resource_detail('Target', row['path'])
        if row.get('reason'):
            ui.detail('Reason', row['reason'])
        if row.get('strategy'):
            ui.detail('Strategy', row['strategy'])
        if row.get('profile'):
            ui.detail('Profile', row['profile'])
    if not rows:
        ui.emit('  No matching items.')


def show_system(rows, locations, verbose=False, include_all=False):
    """Compact human projection only; discovery records stay complete for JSON."""
    ui = Presentation()
    ui.repository_roots([dict(id=loc['repository'], root=loc.get('root')) for loc in locations])
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
                   ('candidate', 'existing-source', 'register-existing-link', 'managed', 'excluded', 'unavailable') if counts[s]), '96')
    if verbose:
        for row in visible:
            ui.resource_detail('Path', row['path'])
            ui.emit('    ' + ui.paint(ui.owner_label(row['repository']), '94') + '  ' + ui.status(row['status']))
            if row.get('source'):
                ui.resource_detail('Source', row['source'])
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
            badges = ', '.join(ui.paint(str(n), '96') + ' ' + ui.status(s)
                               for s, n in sorted(Counter(x['status'] for x in items).items()))
            rendered = ('  ' + ui.resource(path) + '  ' +
                        ui.paint(ui.owner_label(repository), '94') + ' / ' + badges)
            if len(re.sub(r'\x1b\[[0-9;]*m', '', rendered)) <= ui.width:
                ui.emit(rendered)
                continue
            ui.resource_detail('Path', path)
            line(ui.owner_label(repository), '94', '    ')
            statuses(items)
    if not visible:
        line('No config candidates found.' if not include_all else 'No matching items.', '94')
    hidden = sum(counts[s] for s in ('managed', 'excluded')) if not include_all else 0
    if hidden:
        line('Managed/excluded entries hidden; use --all to include them.')
    if not verbose and visible:
        line('Use --verbose for individual files and source mappings.')


def main():
    from help_adapters import HelpArgumentParser
    parser = HelpArgumentParser()
    parser.add_argument('action', choices=['locations', 'system', 'add', 'link', 'find', 'remove', 'history', 'undo', 'recover', 'backups-list', 'backups-show', 'backups-restore'])
    parser.add_argument('values', nargs='*')
    parser.add_argument('--path', dest='search_paths', metavar='DIR', action='append', default=[])
    parser.add_argument('--repo')
    parser.add_argument('-s', '--source', action='append')
    parser.add_argument('-t', '--target', action='append')
    parser.add_argument('-g', '--global', dest='global_files', action='store_true')
    parser.add_argument('--scan', action='store_true')
    parser.add_argument('--pick', action='store_true')
    parser.add_argument('--directory-link', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--all', dest='include_all', action='store_true')
    backups = parser.add_mutually_exclusive_group()
    backups.add_argument('--backup', action='store_true', default=None)
    backups.add_argument('--no-backup', dest='backup', action='store_false')
    args = parser.parse_intermixed_args()
    if args.search_paths and args.action != 'find':
        parser.error('--path is supported by files find and files fd')
    for field in ('source', 'target'):
        values = getattr(args, field) or []
        if len(values) > 1:
            parser.error('--' + field + ' may be supplied only once')
        setattr(args, field, next(iter(values), None))
    args.link_paths = link_operands(parser, args)
    if not args.link_paths:
        validate_cli(args, parser)
    from interaction import selection_requested as requested
    picking = requested(parser, args, args.values, args.action in ('add', 'link', 'remove'))
    configure(not args.json and not args.dry_run)
    if args.include_all and args.action != 'system':
        parser.error('--all requires discover --system')
    if args.verbose and args.action not in ('system', 'add', 'find', 'link', 'remove', 'undo', 'recover', 'backups-restore'):
        parser.error('--verbose requires discover --system or a file-changing operation')
    if args.action != 'add' and (args.scan or args.directory_link):
        parser.error('--scan and --directory-link require add')
    if (args.target or args.source) and not args.link_paths:
        if args.action != 'add' or len(args.values) != 1 or args.scan or args.pick or (args.source and args.target):
            parser.error('--source or --target requires one explicit add path, or link source and target')
    if args.global_files and (args.action != 'add' or args.repo):
        parser.error('--global selects storage for add; use either --global or --repo')
    if args.action == 'find' and (args.repo or args.backup is not None):
        parser.error('find registers existing links; supply search roots as operands or with --path')
    if args.scan and args.directory_link:
        parser.error('--directory-link requires explicit directory paths')
    if args.pick and args.scan and args.values:
        parser.error('choose paths or --scan')
    if args.action in ('locations', 'system', 'history', 'backups-list') and args.values:
        parser.error('this inspection command takes no positional arguments')
    manager = Manager()
    output = OperationOutput.for_args(args)
    manager.store.observer = output
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
    if args.action == 'find':
        from file_platform import check_object
        from find_links import discover, review
        roots = list(args.values)
        for value in args.search_paths:
            if not value:
                parser.error('--path requires a directory')
            directory = operand(manager.catalog, value)
            check_object(directory)
            if not directory.is_dir():
                raise ValueError('--path requires an existing directory: ' + str(directory))
            roots.append(directory)
        # Guard catalog inputs before discovery so approvals cannot be reused
        # with a subsequently changed mapping or root.
        inputs = {str(path): digest(path) for path in manager.catalog.input_paths()}
        with Progress('Finding existing Dots links'):
            found, discovery_guards = discover(manager, roots)
        preview = dict(schema=1, action='find', dry_run=args.dry_run, items=found)
        if args.dry_run or (args.json and not args.yes):
            if args.json: print(json.dumps(preview))
            else: show('Existing links', found)
            return
        args.find_conflicts = [r for r in found if r['status'] == 'conflict']
        if args.find_conflicts and not args.json:
            show('Conflicting links', args.find_conflicts)
        accepted = review(found, args.yes, args.json) if found else []
        if not accepted:
            if args.json: print(json.dumps(dict(schema=1, status='unchanged', operations=[], skipped=args.find_conflicts)))
            elif not args.find_conflicts: show('Existing links', [])
            return
        args.found = {r['candidate']: r for r in accepted}
        args.find_guards = dict(inputs, **discovery_guards)
        args.values = list(args.found)
        args.yes = True  # Each selected item has already been approved.
    if picking:
        from picker import candidates, select
        with Progress('Loading file choices'):
            rows = candidates(manager, args.action, args.values, args.repo, global_files=args.global_files)
            if args.global_files:
                from registration import global_scope_conflict
                if args.values:
                    for row in rows:
                        if reason := global_scope_conflict(row): raise ValueError(reason)
                rows = [row for row in rows if not global_scope_conflict(row)]
        chosen = select(rows, args.action, multi=True, owners=manager.catalog.sources)
        if not chosen:
            return
        args.values = [r['candidate'] if args.action == 'add' else r['id'] for r in chosen]
        args.scan = False
    if args.action == 'add' and not args.scan and not args.yes and not args.json and not args.dry_run and sys.stdin.isatty():
        from registration import Registration, global_scope_conflict
        from mappings import prompt, target_spec
        resolver = Registration(manager)
        args.target_map = {}
        args.source_map = {}
        observed = None
        for value in args.values:
            path = operand(manager.catalog, value)
            if not args.target and not path.is_symlink() and resolver.owner(path, args.repo) and observed is None:
                observed = manager.system(args.repo)
            row = resolver.candidate(path, args.repo, args.target, observed or ())
            if args.global_files and row and (reason := global_scope_conflict(row)):
                raise ValueError(reason)
            if row and not row['target']:
                destination = prompt('Destination for ' + row['source'])
                if not destination:
                    raise SelectionEnded(130)
                args.target_map[str(path)] = destination
            elif not row and not args.source:
                target_spec(manager.catalog, str(path))
                try:
                    manager.mapping(path, args.repo)
                except UnknownLocation:
                    source = prompt('Storage path for ' + str(path))
                    if not source: raise SelectionEnded(130)
                    args.source_map[str(path)] = source
    with sequence('File operations', 2) as phases:
        with phases.step('Plan file operations'):
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
                        source = manager.store.payload(identity, i, 'before', entry)
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
                for path, expected in getattr(args, 'find_guards', {}).items():
                    if expected != guards.get(path, expected) or digest(path) != expected:
                        raise ValueError('changed after discovery: ' + path)
                    guards[path] = expected
                receipt = (args.action not in ('add', 'find') and not args.link_paths) or manager.registration_receipt
                if getattr(manager, 'link_installation', None) and receipt:
                    # Installation baselines must survive for a later uninstall.
                    args.backup = True
        with permanent_output():
            if getattr(manager, 'link_installation', None):
                manager.link_installation.store.observer = output
            output.plan(views, args.dry_run)
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
                approved = None if args.json else gum_confirm('Apply these changes?')
                if approved is None:
                    print('Apply these changes? [y/N] ', end='', file=sys.stderr, flush=True)
                    approved = input().lower() == 'y'
                if not approved:
                    phases.cancel()
                    if args.json:
                        print(json.dumps(dict(preview, status='cancelled')))
                    else:
                        print('Cancelled; no changes made.')
                    return
        with phases.step('Apply file operations'):
            if args.action == 'recover':
                result = manager.store.recover(args.values[0])
            elif getattr(manager, 'link_installation', None) and receipt:
                result = manager.link_installation.apply(args.action, catalogs=catalogs, retain=args.backup,
                            write_receipt=receipt)
                if result['status'] == 'unchanged':
                    result = dict(schema=1, status='unchanged', operations=[])
            else:
                result = manager.store.apply(args.action, ops, guards, args.backup, catalogs)
        with permanent_output():
            if args.json:
                if args.action == 'find' and args.find_conflicts:
                    result['skipped'] = args.find_conflicts
                print(json.dumps(result))
            else:
                ui = Presentation()
                ui.heading('File operation ' + result['status'])
                if result.get('id'):
                    ui.detail('Transaction', result['id'])
                    ui.detail('Undo', 'dots files undo ' + result['id'])
                    if args.backup:
                        ui.detail('Backup', result['id'])


if __name__ == '__main__':
    try:
        main()
    except SelectionEnded as end:
        sys.exit(end.status)
    except (KeyboardInterrupt, EOFError):
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('Interrupted; inspect dots files history for recovery status.', '93'))
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots files: ' + str(error), '91'))
        sys.exit(1)
