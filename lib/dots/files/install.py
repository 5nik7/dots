#!/usr/bin/env python3
"""Checkout installation: catalog plans, retained baselines and native adapters."""
import argparse
from contextlib import ExitStack, contextmanager
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from collections import Counter

if sys.version_info < (3, 9):
    raise SystemExit('dots setup requires Python 3.9 or newer')

from catalog import Catalog, Presentation, platform, read_json
from events import OperationOutput
from file_platform import lock, open_nofollow, state_root, prepare_text
from transactions import Store, digest, exists, parents_safe, private_directory, copy_object

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from interaction import gum_confirm
from progress import Progress, configure

from identities import canonical, current_source
from setup_components import DEFAULTS, component
from managed_destination import physical

PUBLIC_SOURCES = ('termux', 'windows', 'nvim')


@contextmanager
def locked_file(path):
    parents_safe(path)
    private_directory(path.parent)
    with os.fdopen(open_nofollow(path, os.O_RDWR | os.O_CREAT), 'a') as handle:
        lock(handle)
        yield


def approve(args, label='Apply this plan?'):
    if args.yes:
        return True
    if args.json or getattr(args, 'non_interactive', False) or not sys.stdin.isatty():
        raise ValueError('noninteractive installation requires --yes or --dry-run')
    choice = None if args.json else gum_confirm(label)
    if choice is not None:
        return choice
    print(label + ' [y/N] ', end='', file=sys.stderr, flush=True)
    return sys.stdin.readline().strip().lower() in ('y', 'yes')


def display(doc, args, final=False):
    if args.json:
        if final or args.dry_run:
            print(json.dumps(doc, ensure_ascii=True))
        return
    ui = Presentation()
    ui.heading('Dots ' + doc['action'] + ' — ' + doc['status'])
    counts = Counter(row['status'] for row in doc.get('items', []))
    ui.emit('  ' + ui.paint(', '.join(str(count) + ' ' + status.replace('-', ' ') for status, count in sorted(counts.items())) or 'No matching changes.', '96'))
    for row in doc.get('items', []):
        if final:
            continue
        ui.emit()
        ui.emit('  ' + ui.paint(row['id'], '1;94') + '  ' + ui.status(row['status']))
        for field in ('source', 'target', 'root', 'ref', 'reason'):
            if row.get(field):
                is_path = field in ('source', 'target', 'root')
                if is_path:
                    intended = 'dir' if field == 'root' else None
                    if field == 'target' and row['status'] == 'create' and not os.path.lexists(row[field]):
                        intended = 'symlink' if row.get('source') and row.get('strategy') != 'copy' else 'file'
                    ui.resource_detail(field.title(), row[field], kind=intended)
                else:
                    ui.detail(field.title(), row[field])
    if doc.get('transaction'):
        ui.detail('Transaction', doc['transaction'])
    ui.emit('\n  ' + ('No changes made.' if args.dry_run else doc.get('message', 'Retained backups protect replaced configurations.')))


class Installation:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.platform = platform()
        from platform_info import detect
        context = detect()
        if context['platform'] == 'windows' and context['runtime'] != 'native':
            raise ValueError('Windows setup requires native Windows Python; MSYS/Cygwin supports inspection only')
        self.state = state_root()
        self.store = Store(self.state)
        self.receipt_path = self.state / 'installation.json'
        parents_safe(self.receipt_path)
        receipt_before = digest(self.receipt_path)
        self.receipt = read_json(self.receipt_path) if exists(self.receipt_path) else {
            'schema': 1, 'root': str(self.root), 'platform': self.platform,
            'entries': {}, 'transactions': []}
        if self.receipt.get('root') != str(self.root) or self.receipt.get('platform') != self.platform:
            raise ValueError('another checkout owns this installation; uninstall it before changing checkouts')
        if not isinstance(self.receipt.get('entries'), dict) or not isinstance(self.receipt.get('transactions'), list):
            raise ValueError('invalid installation record')
        if digest(self.receipt_path) != receipt_before:
            raise ValueError('installation record changed while reading; retry the preview')
        self.guards = {str(self.receipt_path): receipt_before}
        self.operations = []
        self.items = []
        self.theme_notice = ''
        self.entries = copy.deepcopy(self.receipt['entries'])
        from identities import registry
        registry_path = self.root / '.dots/files.json'
        registry_before = digest(registry_path)
        identities = registry(self.root)
        if identities:
            if digest(registry_path) != registry_before:
                raise ValueError('registry changed while reading installation identities; retry the preview')
            self.guards[str(registry_path)] = registry_before
        for entry in self.entries.values():
            entry['id'] = identities.resolve(entry['id']) if identities else canonical(entry['id'])
        self.theme = None
        self.theme_environment = {}
        self.theme_prepared = False
        self.components = None
        self.resources = None
        self.catalog_records = []
        self.receipt_changed = False
        self.blocked = False
        self.transaction = uuid.uuid4().hex
        for record in self.store.records():
            if record['status'] in ('preparing', 'applying', 'rolling-back', 'recovery-required'):
                raise ValueError('unfinished transaction: run dots files recover ' + record['id'])

    def item(self, identity, status, target=None, source=None, reason=None, strategy=None):
        row = dict(id=identity, status=status)
        row.update({k: str(v) for k, v in dict(target=target, source=source, reason=reason, strategy=strategy).items() if v is not None})
        self.items.append(row)
        if status == 'conflict':
            self.blocked = True

    def guard(self, path):
        path = str(path)
        parents_safe(path)
        self.guards.setdefault(path, digest(path))

    def merge_plan(self, operations, guards, *, label):
        """Compose owner-produced operations without weakening their guards."""
        for path, expected in guards.items():
            if path in self.guards and self.guards[path] != expected:
                raise ValueError('conflicting preview guards: ' + path)
            self.guards[path] = expected
        for operation in operations:
            previous = next((op for op in self.operations if op['path'] == operation['path']), None)
            if previous is not None:
                if previous != operation:
                    raise ValueError('conflicting setup writes: ' + operation['path'])
                continue
            if 'data' in operation:
                path = Path(operation['path'])
                if path.is_file() and not path.is_symlink() and read_json(path) == operation['data']:
                    continue
            self.operations.append(operation)
            self.item(label, 'create' if guards.get(operation['path']) is None else 'replace-with-backup', operation['path'])

    def add(self, identity, path, *, link=None, text=None, source=None, directory=False, managed=False):
        path = Path(path)
        self.guard(path)
        key = str(path)
        if any(op['path'] == key for op in self.operations):
            raise ValueError('duplicate installation target: ' + key)
        owned = self.entries.get(key)
        if not owned and key in getattr(self, 'legacy_verified', set()):
            managed = True
        current = self.guards[key]
        same = (link is not None and path.is_symlink() and os.readlink(path) == str(link))
        if source is not None:
            source = Path(source)
            if source.is_symlink() or not source.is_file():
                raise ValueError('copy strategy requires a regular file source')
            self.guard(source)
            same = not path.is_symlink() and current == self.guards[str(source)]
        if text is not None:
            same = path.is_file() and not path.is_symlink() and path.read_text(encoding='utf-8') == text
        if owned and current != owned['after'] and not managed:
            self.item(identity, 'conflict', path, reason='installer-owned target changed; preserve and review it')
            return
        if same:
            self.item(identity, 'unchanged', path, link or source, strategy='copy' if source is not None else None)
            return
        if path.is_symlink() and not owned and not managed:
            # A matching relative link predating setup is observed, never owned.
            if link is not None and path.resolve() == Path(link).resolve():
                self.item(identity, 'unchanged', path, link)
                return
            self.item(identity, 'conflict', path, reason='unrelated link is protected; inspect dots files migrate-apps for a legacy application installation')
            return
        if link is not None and path.is_dir() and path.resolve() == Path(link).resolve():
            raise ValueError('source and target overlap: ' + key)
        op = dict(path=key)
        if link is not None:
            op.update(link=str(link), directory=directory)
        elif source is not None:
            op['source'] = str(source)
        else:
            op['text'] = text
        self.operations.append(op)
        if not owned:
            owned = dict(id=identity, before=current, backup=self.transaction,
                         index=len(self.operations)-1)
            self.entries[key] = owned
        owned['desired'] = {k: v for k, v in op.items() if k != 'path'}
        self.item(identity, 'replace-with-backup' if current is not None else 'create', path, link or source,
                  reason='copy regular file' if source is not None else None,
                  strategy='copy' if source is not None else None)

    def retire(self, identity, path):
        """Retire a caller-verified legacy object, retaining its original baseline."""
        path = Path(path)
        key = str(path)
        self.guard(path)
        if not exists(path):
            return
        if key in self.entries:
            self.item(identity, 'conflict', path, reason='legacy artifact already has Dots ownership')
            return
        self.entries[key] = dict(id=identity, before=self.guards[key], backup=self.transaction,
                                 index=len(self.operations))
        self.operations.append(dict(path=key, delete=True))
        self.item(identity, 'remove', path, reason='verified legacy artifact; retain recovery copy')

    def plan_core_manual(self, home):
        if 'core' not in self.components or self.platform == 'windows':
            return
        source = self.root / 'man/dots.1'
        # Older/minimal source fixtures need not contain the new manual directory.
        if not source.parent.exists():
            return
        if not source.is_file() or source.is_symlink():
            self.item('dots:manual', 'conflict', source, reason='generated dots manual is missing or nonregular')
            return
        self.guard(source)
        if self.platform == 'termux':
            value = os.environ.get('TERMUX__PREFIX') or os.environ.get('PREFIX', '')
            prefix = Path(value)
            if not value or not prefix.is_absolute() or '..' in prefix.parts or prefix == Path(prefix.anchor):
                raise ValueError('Termux manual requires an absolute native prefix')
            destination = prefix / 'share/man/man1/dots.1'
        else:
            destination = home / '.local/share/man/man1/dots.1'
        self.add('dots:manual', destination, link=source)

    def plan_bundled_apps(self, home):
        # Minimal controller fixtures may omit bundled apps. A declared bundle
        # must be complete; missing runtime assets block the whole transaction.
        manifest = self.root / 'plugins/manifest.json'
        if not manifest.is_file():
            if (self.root / 'plugins').exists():
                raise ValueError('application plugin manifest is missing')
            return
        self.guard(manifest)
        data = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share')
        from plugin_paths import definitions
        for name, definition in definitions(self.root).items():
            if self.components is not None and name not in self.components:
                continue
            source = self.root / 'plugins' / name
            manual = definition['manual']
            required = [source / definition['runtime'], source / manual,
                        *(source / value for value in definition['completions'].values()),
                        self.root / 'bin' / name, self.root / 'bin' / (name + '.ps1')]
            missing = next((path for path in required if not path.is_file()), None)
            if missing:
                self.item('dots:' + name, 'conflict', missing, reason='bundled application is incomplete')
                continue
            for path in required:
                self.guard(path)
            if self.platform == 'windows':
                quoted = str(self.root / 'bin' / (name + '.ps1')).replace("'", "''")
                self.add('dots:' + name + ':command', home / '.local/bin' / (name + '.ps1'),
                         text="& '" + quoted + "' @args\nexit $LASTEXITCODE\n")
            else:
                self.add('dots:' + name + ':command', home / '.local/bin' / name,
                         link=self.root / 'bin' / name)
                for shell, relative in (
                    ('bash', 'bash-completion/completions/' + name),
                    ('zsh', 'zsh/site-functions/_' + name),
                ):
                    self.add('dots:' + name + ':completion:' + shell, data / relative,
                             link=source / definition['completions'][shell])
                self.add('dots:' + name + ':manual', home / '.local/share/man/man1' / (name + '.1'),
                         link=source / manual)

    def theme_bridge(self, mode, fingerprint=None):
        cmd = ([sys.executable, '-B', str(self.root / 'lib/dots/themes/setup.py'), mode]
               if self.platform == 'windows' else ['bash', str(self.root / 'lib/dots/themes/setup.bash'), mode])
        if fingerprint:
            cmd.append(fingerprint)
        result = subprocess.run(cmd, env=dict(os.environ, DOTS=str(self.root), DOTS_PROGRESS='never',
                                             DOTS_COLOR='never', DOTS_ICONS='never', **self.theme_environment),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise ValueError('theme preparation failed: ' + result.stderr.decode(errors='replace').strip())
        return result.stdout.decode().split('\0')[:-1]

    def reconcile_destinations(self, records, planned=()):
        """Retain original recovery pointers when a directory mapping moved a child."""
        for key, entry in list(self.entries.items()):
            path = physical(key, records, self.guards, planned=planned)
            if str(path) == key:
                continue
            if str(path) in self.entries:
                raise ValueError('duplicate logical/physical installation ownership: ' + key)
            if digest(path) != entry['after']:
                raise ValueError('mapped installer-owned target changed; preserve and review: ' + key)
            entry['logical_path'] = key
            self.entries[str(path)] = self.entries.pop(key)
            self.receipt_changed = True

    def plan_install(self, components=None, resources=None, *, defer_theme=False):
        self.components = set(DEFAULTS if components is None else components)
        self.resources = None if resources is None else set(resources)
        catalog = Catalog(self.root, self.platform)
        for path in catalog.input_paths():
            self.guard(path)
        for source in catalog.sources:
            if source['status'] == 'excluded':
                continue
            if self.platform in source['platforms'] and source['status'] != 'available':
                self.item(source['id'], 'skipped', reason='optional source unavailable; select --with-source ' + source['id'])
        observed = catalog.records()
        self.catalog_records = observed
        for row in observed:
            if row['applicable'] and not row['enabled']:
                self.item(row['id'], 'skipped', row['target'], reason='stashed')
        records = [r for r in observed if r['enabled'] and r['applicable'] and r['status'] != 'replaced']
        selected = [r for r in records if 'files' in self.components
                    and (self.resources is None or r['id'] in self.resources)]
        if self.resources is not None:
            missing = self.resources - {r['id'] for r in selected}
            if missing:
                raise ValueError('setup resource is not enabled/applicable: ' + ', '.join(sorted(missing)))
        planned = {r['target'] for r in selected if r['strategy'] == 'directory-link'}
        self.reconcile_destinations(observed, planned)
        # Render against the selected source even before its destination link
        # exists. This keeps compiled syntax inputs stable across first/repeat
        # setup and includes the real custom syntaxes on the first build.
        bat = next((r for r in records if r['app'] == 'bat' and r['strategy'] == 'directory-link'
                    and r['target'] and (r in selected or Path(r['target']).resolve() == Path(r['source']))), None)
        if bat and not os.environ.get('BAT_CONFIG_DIR'):
            self.theme_environment['BAT_CONFIG_DIR'] = bat['source']
        connectors = []
        if not defer_theme and 'themes' in self.components and (self.root / 'lib/dots/themes' / ('setup.py' if self.platform == 'windows' else 'setup.bash')).is_file():
            with Progress('Inspecting theme inputs'):
                identity, fingerprint, current, incomplete = self.theme_bridge('inspect')
            self.theme = dict(id=identity, fingerprint=fingerprint, generation=current,
                              incomplete=incomplete)
            themes = self.state / 'themes'
            for p in (themes / 'current', self.state / 'current/theme', themes / 'commands/current'):
                self.guard(p)
            for folder in (themes / 'generations', themes / 'commands/generations'):
                if folder.exists():
                    for status in folder.glob('*/status'):
                        if status.read_text().strip() == 'prepared':
                            raise ValueError('unfinished theme publication; recover with dots theme refresh first')
            for line in (self.root / 'lib/dots/themes/connectors.tsv').read_text().splitlines():
                app, suffix, artifact = line.split('\t')
                if self.platform == 'windows' and app not in ('yazi', 'git', 'vivid', 'eza', 'leaf'):
                    continue
                owner = next((r for r in records if r['app'] == app and r['strategy'] == 'directory-link' and r['target']), None)
                if app in ('eza', 'leaf'):
                    from app_paths import eza_config_directory, leaf_config_directory
                    resolver = leaf_config_directory if app == 'leaf' else eza_config_directory
                    base = resolver(windows=self.platform == 'windows')
                    if not owner or Path(owner['target']) != base:
                        continue
                if owner and Path(owner['source']).is_dir():
                    connectors.append((app, Path(owner['source']) / suffix, artifact))
            if self.platform == 'termux':
                target = Path(os.environ['HOME']) / '.termux/colors.properties'
                selected = [r for r in selected if r['target'] != str(target)]
                if not any(not r['enabled'] and r['target'] == str(target) for r in observed):
                    connectors.append(('termux', physical(target, observed, self.guards, planned=planned), 'termux.properties'))
            # Preserve the publisher's opt-in-by-existing-directory boundaries.
            for app, parent, filename, artifact in (
                ('codex', Path(os.environ.get('CODEX_HOME') or Path.home()/'.codex')/'themes', 'dots.tmTheme', 'bat.tmTheme'),
                ('pi', Path(os.environ.get('PI_CODING_AGENT_DIR') or Path.home()/'.pi/agent').expanduser()/'themes', 'dots.json', 'pi.json')):
                if parent.is_dir():
                    connectors.append((app, parent / filename, artifact))
        for row in selected:
            if row['status'] in ('unmapped', 'unsupported-platform', 'source-missing', 'source-broken-link'):
                self.item(row['id'], 'skipped', row['target'], reason=row['status'])
                continue
            if row['status'] == 'conflict':
                self.item(row['id'], 'conflict', row['target'], reason='catalog ownership conflict')
                continue
            source, target = Path(row['source']), Path(row['target'])
            if source.is_symlink():
                self.item(row['id'], 'conflict', target, reason='source must be a regular file or owned directory')
                continue
            if target == source or target in source.parents or source in target.parents:
                raise ValueError('overlapping source and target: ' + str(target))
            self.guard(source)
            if row['strategy'] == 'copy':
                if not source.is_file():
                    self.item(row['id'], 'conflict', target, reason='copy strategy requires a regular file source')
                    continue
                self.add(row['id'], target, source=source)
                continue
            from git_platform import plan as plan_git_platform
            plan_git_platform(self, row)
            # Link identity is the installed object; later source edits remain
            # editable. During this apply, sources are bound to the preview.
            self.add(row['id'], target, link=source, directory=source.is_dir())
        home = Path(os.environ.get('HOME') or Path.home())
        launcher = 'dots.ps1' if self.platform == 'windows' else 'dots'
        if 'core' not in self.components:
            pass
        elif self.platform == 'windows':
            quoted = str(self.root / 'bin/dots.ps1').replace("'", "''")
            self.add('dots:command', home / '.local/bin' / launcher,
                     text="& '" + quoted + "' @args\nexit $LASTEXITCODE\n")
        else:
            self.add('dots:command', home / '.local/bin' / launcher, link=self.root / 'bin' / launcher)
        self.plan_core_manual(home)
        self.plan_bundled_apps(home)
        todo = self.root / 'bin' / ('todo.ps1' if self.platform == 'windows' else 'todo')
        if 'core' in self.components and todo.is_file():
            self.guard(todo)
            if self.platform == 'windows':
                quoted = str(todo).replace("'", "''")
                self.add('dots:todo:command', home / '.local/bin/todo.ps1',
                         text="& '" + quoted + "' @args\nexit $LASTEXITCODE\n")
            else:
                self.add('dots:todo:command', home / '.local/bin/todo', link=todo)
        fonts = self.root / 'bin' / ('fonts.ps1' if self.platform == 'windows' else 'fonts')
        if 'core' in self.components and fonts.is_file():
            self.guard(fonts)
            if self.platform == 'windows':
                quoted = str(fonts).replace("'", "''")
                self.add('dots:fonts:command', home / '.local/bin/fonts.ps1',
                         text="& '" + quoted + "' @args\nexit $LASTEXITCODE\n")
            else:
                self.add('dots:fonts:command', home / '.local/bin/fonts', link=fonts)
        for app, path, artifact in connectors:
            desired = self.state / 'current/theme' / artifact
            old = os.readlink(path) if path.is_symlink() else ''
            # A fixed connector may repair a relocated generated-state link,
            # but an arbitrary link is never treated as installer ownership.
            managed = old.endswith('/dots/current/theme/' + artifact)
            self.add('theme:' + app + (':' + artifact if app == 'leaf' else ''), path, link=desired, directory=artifact == 'yazi', managed=managed)
        if self.theme:
            generation = self.state / 'themes/generations' / self.theme['generation']
            stored = generation / 'fingerprint'
            self.theme['refresh'] = (bool(self.theme['incomplete']) or not stored.is_file()
                                     or stored.read_text().strip() != self.theme['fingerprint'])
            self.theme['refresh'] |= not (self.state / 'themes/commands/current').is_symlink()
            self.item('theme:' + self.theme['id'], 'prepare' if self.theme['refresh'] else 'unchanged',
                      target=self.theme['incomplete'] or None,
                      reason='rebuild incomplete theme data or restore its publication pointer' if self.theme['incomplete'] else
                             'publish generated theme data without app reloads or hooks')
            if self.theme['refresh']:
                for identity, path in (('selection', self.state/'themes/current'),
                                       ('active', self.state/'current/theme'),
                                       ('commands', self.state/'themes/commands/current')):
                    owned = self.entries.get(str(path))
                    drift = owned and self.guards[str(path)] != owned['after']
                    self.item('theme:' + identity, 'prepare', path,
                              reason='reconcile the validated current theme selection; retain original baseline' if drift else 'publish prepared generation; retain previous pointer for restoration')
        elif 'themes' in self.components:
            self.item('themes', 'prepare' if defer_theme else 'skipped', reason='prepare after prerequisites' if defer_theme else 'theme preparation adapter is unavailable')

    def plan_uninstall(self, components=None, resources=None):
        self.components = None if components is None else set(components)
        self.resources = None if resources is None else set(resources)
        # Old receipts can name a child through a subsequently installed
        # catalog directory link. Only load catalog inputs for this bounded case.
        if any(any(p.is_symlink() for p in Path(key).parents) for key in self.entries):
            catalog = Catalog(self.root, self.platform)
            for path in catalog.input_paths():
                self.guard(path)
            self.reconcile_destinations(catalog.records())
        retained_files = any(component(e['id']) == 'files' and
                             (self.components is not None and 'files' not in self.components
                              or self.resources is not None and e['id'] not in self.resources)
                             for e in self.entries.values())
        if self.components is not None and 'themes' in self.components and retained_files:
            raise ValueError('theme removal would break retained managed files; include those files or retain themes')
        for path, entry in list(self.entries.items())[::-1]:
            owner = entry.get('component', component(entry['id']))
            if self.components is not None and owner not in self.components:
                continue
            if owner == 'files' and self.resources is not None and entry['id'] not in self.resources:
                continue
            self.guard(path)
            if self.guards[path] != entry['after']:
                self.item(entry['id'], 'preserved', path, reason='target changed after installation')
                continue
            op = dict(path=path)
            if entry['before'] is None:
                op['delete'] = True
            else:
                payload = self.store.root / entry['backup'] / (str(entry['index']) + '-before')
                self.guard(payload)
                if self.guards[str(payload)] != entry['before']:
                    raise ValueError('original backup failed verification: ' + path)
                op['source'] = str(payload)
            self.operations.append(op)
            del self.entries[path]
            self.item(entry['id'], 'restore' if entry['before'] else 'remove', path)

    def prepare_theme(self):
        if self.theme_prepared or not self.theme or not self.theme['refresh']:
            return
        self.store.notify('Preparing', reason='theme rendering and cache generation')
        with Progress('Preparing theme generation'):
            values = self.theme_bridge('prepare', self.theme['fingerprint'])
        self.theme_prepared = True
        self.theme_notice = values[2] if len(values) > 2 else ''
        generation = Path(values[0])
        base = self.state / 'themes'
        if generation.parent != base / 'generations' or not generation.name.startswith('g.'):
            raise ValueError('invalid prepared theme generation')
        self.store.notify('Prepared', generation, reason='inactive theme generation', kind='dir')
        displayed = len(self.items)
        self.add('theme:selection', base / 'current', text=generation.name + '\n', managed=True)
        self.add('theme:active', self.state / 'current/theme', link=generation, directory=True, managed=True)
        if len(values) > 1 and values[1]:
            self.add('theme:commands', base / 'commands/current', link=values[1], directory=True, managed=True)
        else:
            for row in self.items:
                if row['id'] == 'theme:commands' and row['status'] == 'prepare':
                    row['status'] = 'unchanged'
        self.items[displayed:] = [row for row in self.items[displayed:] if row['status'] == 'conflict']
        # Inactive immutable payloads are retained. The Store owns publication;
        # the theme publisher must not try to recover this independent journal.

    def prepare(self):
        if not self.theme: return
        with ExitStack() as stack:
            for path in (self.state/'themes/commands/lock', self.state/'themes/lock'):
                stack.enter_context(locked_file(path))
            from setup_stages import verify
            verify(self.guards)
            self.prepare_theme()

    def apply(self, action, catalogs=(), write_receipt=True, retain=True):
        with ExitStack() as stack:
            if self.theme or any(e['id'].startswith('theme:') for e in self.receipt['entries'].values()):
                for path in (self.state/'themes/commands/lock', self.state/'themes/lock'):
                    stack.enter_context(locked_file(path))
            for path, expected in self.guards.items():
                if digest(path) != expected:
                    raise ValueError('changed after preview: ' + path)
            if action == 'install':
                self.prepare_theme()
            if self.blocked:
                raise ValueError('installation plan contains conflicts')
            if not self.operations and not self.receipt_changed:
                return {'status': 'unchanged'}
            # Compute link identity using temporary payloads in owned state only,
            # after approval. No live target is touched during preparation.
            private_directory(self.state / 'setup-staging')
            import tempfile
            with tempfile.TemporaryDirectory(dir=self.state / 'setup-staging') as tmp:
                for index, op in enumerate(self.operations):
                    if op['path'] not in self.entries:
                        continue
                    prepared = Path(tmp) / str(index)
                    if 'link' in op:
                        try:
                            prepared.symlink_to(op['link'], target_is_directory=op.get('directory', False))
                        except OSError as error:
                            raise ValueError('symbolic links unavailable; enable link capability explicitly before retrying') from error
                    elif 'text' in op:
                        prepare_text(prepared, op['text'], op['path'])
                    elif 'source' in op:
                        copy_object(op['source'], prepared)
                    self.entries[op['path']]['after'] = digest(prepared)
                    self.entries[op['path']].pop('desired', None)
            receipt = dict(self.receipt, entries=self.entries,
                           transactions=self.receipt['transactions'] + [self.transaction])
            if write_receipt:
                self.operations.append(dict(path=str(self.receipt_path), data=receipt))
            with Progress('Applying ' + action):
                result = self.store.apply(action, self.operations, self.guards, retain=retain,
                                          catalogs=catalogs, identity=self.transaction,
                                          publication_locked=bool(self.theme or any(e['id'].startswith('theme:') for e in self.receipt['entries'].values())))
            return result

    def prune_empty_parents(self):
        candidates = set()
        for identity in self.receipt['transactions']:
            for row in self.store.load(identity).get('created_parents', []):
                path = Path(row['path'])
                if row['created'] and path != self.state and self.state not in path.parents:
                    candidates.add(path)
        for path in sorted(candidates, key=lambda p: len(p.parts), reverse=True):
            parents_safe(path)
            if path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
                self.store.apply('uninstall-empty-directory', [dict(path=str(path), delete=True)],
                                 {str(path): digest(path)}, retain=True)


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, env=git_environment())
    if result.returncode:
        raise ValueError('Git operation failed: ' + result.stderr.strip())
    return result.stdout.rstrip('\r\n')


def git_environment():
    return {key: value for key, value in os.environ.items()
            if key not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE')}


def protect_ignored(root, target):
    ignored = git(root, 'ls-files', '--others', '--ignored', '--exclude-standard', '-z').split('\0')
    incoming = set(git(root, 'ls-tree', '-r', '--name-only', '-z', target).split('\0'))
    claimed = incoming | {p.as_posix() for name in incoming if name for p in Path(name).parents}
    for name in filter(None, ignored):
        path = Path(name)
        if name in claimed or any(p.as_posix() in incoming for p in path.parents):
            raise ValueError('update would replace ignored local content: ' + name)


def source_plan(root, args):
    if not args.update and not args.with_source:
        return []
    catalog = Catalog(root, platform())
    bundled = {row['id'] for row in catalog.sources if row.get('bundled')}
    if (args.update or set(args.with_source) - bundled) and not shutil.which('git'):
        raise ValueError('Git is required to update or acquire sources')
    result = []
    if args.update:
        if git(root, 'status', '--porcelain', '--untracked-files=normal'):
            raise ValueError('update requires a clean checkout; preserve local changes before retrying')
        branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
        remote = git(root, 'config', 'branch.' + branch + '.remote')
        ref = git(root, 'config', 'branch.' + branch + '.merge')
        if not ref.startswith('refs/heads/') or remote.startswith('-'):
            raise ValueError('update requires an explicit branch upstream')
        result.append(dict(id='dots', root=str(root), status='fast-forward', remote=remote, ref=ref,
                           head=git(root, 'rev-parse', 'HEAD')))
    for source in catalog.sources:
        if source['id'] not in PUBLIC_SOURCES or platform() not in source['platforms']:
            continue
        if source.get('bundled'):
            if source['id'] in args.with_source:
                result.append(dict(id=source['id'], root=source['root'], status='bundled'))
            continue
        path = Path(source['root'])
        initialized = (path / '.git').exists()
        if source['id'] not in args.with_source and not (args.update and initialized):
            continue
        if not initialized and path.exists() and any(path.iterdir()):
            raise ValueError('optional source destination is occupied: ' + source['id'])
        if initialized and git(path, 'status', '--porcelain', '--untracked-files=normal'):
            raise ValueError('optional source has local changes: ' + source['id'])
        result.append(dict(id=source['id'], root=str(path), path=source['path'],
                           status='recorded-commit', initialized=initialized))
    selected = {r['id'] for r in result}
    if set(args.with_source) - selected:
        raise ValueError('requested source is unavailable or not applicable to this platform')
    return result


def update_sources(root, rows):
    for row in rows:
        if row.get('status') == 'bundled': continue
        path = Path(row['root'])
        if row['id'] == 'dots':
            gitdir = Path(git(root, 'rev-parse', '--absolute-git-dir'))
            with locked_file(gitdir / 'dots-setup.lock'):
                if git(root, 'rev-parse', 'HEAD') != row['head'] or git(root, 'status', '--porcelain'):
                    raise ValueError('repository changed after preview')
                fetch = ['git', '-C', str(root), '-c', 'submodule.recurse=false', 'fetch',
                         '--no-recurse-submodules', '--no-tags', '--refmap=', row['remote'], row['ref']]
                if subprocess.run(fetch, stdout=sys.stderr, env=git_environment()).returncode:
                    raise ValueError('fetch failed; setup was not applied')
                target = git(root, 'rev-parse', 'FETCH_HEAD')
                git(root, 'merge-base', '--is-ancestor', 'HEAD', target)
                if git(root, 'diff', '--name-only', 'HEAD', target, '--', '.gitmodules'):
                    raise ValueError('submodule topology changed; review and update manually')
                if git(root, 'rev-parse', 'HEAD') != row['head'] or git(root, 'status', '--porcelain'):
                    raise ValueError('repository changed during fetch')
                protect_ignored(root, target)
                git(root, '-c', 'submodule.recurse=false', 'merge', '--ff-only', '--no-overwrite-ignore', target)
        else:
            if row['initialized']:
                if git(path, 'status', '--porcelain'):
                    raise ValueError('optional source changed after preview')
                # Never abandon local commits when moving to the parent's pin.
                pin = git(root, 'ls-tree', 'HEAD', '--', row['path']).split()[2]
                known = subprocess.run(['git','-C',str(path),'cat-file','-e',pin+'^{commit}'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=git_environment()).returncode == 0
                if not known:
                    if subprocess.run(['git','-C',str(path),'fetch','--no-recurse-submodules','--no-tags','origin',pin], stdout=sys.stderr, env=git_environment()).returncode:
                        raise ValueError('cannot fetch recorded source commit: ' + row['id'])
                git(path, 'merge-base', '--is-ancestor', 'HEAD', pin)
                protect_ignored(path, pin)
            command = ['git', '-C', str(root), '-c', 'submodule.recurse=false',
                       'submodule', 'update', '--init', '--checkout', '--', row['path']]
            if subprocess.run(command, stdout=sys.stderr, env=git_environment()).returncode:
                raise ValueError('optional source update failed: ' + row['id'])


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dots files', add_help=False,
                                    description='Install or restore catalogued Dots configurations with retained backups.',
                                    epilog='Setup is also available through dots init --setup and the root install/uninstall shell and PowerShell scripts.')
    parser.add_argument('-h', '--help', action='store_true', help='show setup help')
    parser.add_argument('action', choices=('install', 'uninstall', 'migrate-apps'))
    parser.add_argument('--dry-run', action='store_true', help='preview without writes or network access')
    parser.add_argument('-v', '--verbose', action='store_true', help='show actions, backups and unchanged/skipped reasons')
    parser.add_argument('--yes', action='store_true', help='approve the displayed plan without prompting')
    parser.add_argument('--json', action='store_true', help='emit a schema-1 result')
    parser.add_argument('--update', action='store_true', help='fast-forward the clean checkout before planning setup')
    parser.add_argument('--with-source', action='append', default=[], type=current_source, choices=PUBLIC_SOURCES)
    parser.add_argument('--packages', metavar='FILE', help='restore declared packages before configuration setup')
    parser.add_argument('--color', choices=('auto', 'always', 'never'))
    parser.add_argument('--icons', choices=('auto', 'always', 'never'))
    import setup_wizard
    setup_wizard.arguments(parser)
    raw = list(sys.argv[1:] if argv is None else argv)
    if '--help' in raw or '-h' in raw:
        for key in ('color', 'icons'):
            option = next((s.split('=', 1)[1] for s in raw if s.startswith('--' + key + '=')), None)
            if option in ('auto', 'always', 'never'):
                os.environ['DOTS_' + key.upper()] = option
        ui = Presentation()
        ui.heading('Dots setup')
        ui.emit(parser.format_help())
        return 0
    args = parser.parse_args(raw)
    if args.action != 'install' and (args.update or args.with_source or args.packages or args.fonts
                                    or args.font_target or args.with_dependencies or args.save_choices):
        parser.error('source, package, font, dependency and saved-choice options require install')
    if args.action == 'migrate-apps' and any((args.interactive,args.non_interactive,args.component is not None,args.resource is not None,args.no_clear,args.no_logo)):
        parser.error('wizard and component selection options require install or uninstall')
    if args.interactive and (args.yes or args.json or args.dry_run):
        parser.error('--interactive cannot be combined with --yes, --json or --dry-run')
    if args.interactive and not setup_wizard.terminal():
        parser.error('--interactive requires terminal input and output')
    for key in ('color', 'icons'):
        if getattr(args, key):
            os.environ['DOTS_' + key.upper()] = getattr(args, key)
    configure(not args.json and not args.dry_run)
    root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[3]).resolve()
    rows = source_plan(root, args)
    if rows:
        source_doc = dict(schema=1, action='source update', status='preview', items=rows,
                          message='Configuration setup is planned after source changes; Git updates are retained if setup fails.')
        display(source_doc, args)
        if args.dry_run:
            return 0
        if not approve(args, 'Update these sources, then plan configuration setup?'):
            display(dict(source_doc, status='cancelled', items=[]), args, True)
            return 0
        update_sources(root, rows)
        # Load the newly checked-out implementation before planning file writes.
        forwarded = []
        skip = False
        for word in raw:
            if skip:
                skip = False
                continue
            if word == '--with-source':
                skip = True
            elif word != '--update' and not word.startswith('--with-source='):
                forwarded.append(word)
        os.execv(sys.executable, [sys.executable, '-B', str(root / 'lib/dots/files/install.py'), *forwarded])
    installation = Installation(root)
    if args.action != 'migrate-apps':
        setup_wizard.defaults(root, installation, args)
        interactive = (args.interactive or not any((args.non_interactive, args.yes, args.json, args.dry_run))
                       and setup_wizard.terminal())
        if interactive:
            try:
                setup_wizard.run(root, installation, args)
            except setup_wizard.SelectionEnded as error:
                if error.status not in (0, 130):
                    raise ValueError('setup selector failed; no approval received') from error
                display(dict(action=args.action, status='cancelled', items=[], message='No changes made.'), args, True)
                return error.status
        setup_wizard.selected_inputs(installation, args)
    with ExitStack() as cleanup:
        return process_selection(root, installation, args, cleanup)


def process_selection(root, installation, args, cleanup):
    import setup_wizard
    preparation = None
    if args.action == 'install':
        from setup_stages import Preparation
        preparation = Preparation(installation, args)
        cleanup.callback(preparation.close)
    output = OperationOutput.for_args(args)
    installation.store.observer = output
    with Progress('Planning ' + args.action):
        if args.action == 'install':
            installation.plan_install(args.component, args.resource, defer_theme=preparation.deferred_theme)
            setup_wizard.save_plan(root, installation, args)
        elif args.action == 'migrate-apps':
            from app_migration import plan
            plan(installation)
        else:
            installation.plan_uninstall(args.component, args.resource)
            from setup_fonts import uninstall as uninstall_fonts
            uninstall_fonts(installation)
    doc = dict(schema=1, action=args.action, status='blocked' if installation.blocked else 'preview',
               platform=installation.platform, items=installation.items)
    if args.action != 'migrate-apps':
        doc['components'] = args.component
    if preparation:
        doc['preparation'] = preparation.preview()
        if 'packages' in args.component:
            doc['packages'] = dict(schema=1,status='preview',groups=[dict(manager=g['manager'],scope=g['scope'],
                status='deferred',reason='manager inspection follows preparation approval',plan=None,
                desired=g['packages']) for g in preparation.packages['groups']])
        if not args.json:
            ui = Presentation()
            for row in doc['preparation']:
                ui.detail('Preparation', row['stage'])
                for requirement in row.get('requirements', []):
                    ui.detail('Missing', requirement['tool']+' — '+(requirement['package'] or requirement['reason']))
                if row['stage'] == 'packages':
                    for group in row['manifest']['groups']:
                        targets = [p['name']+('='+p['pin'] if p['pin'] else '') for p in group['packages'] if p['enabled']]
                        ui.detail(group['manager']+' / '+group['scope'], ', '.join(targets) or 'no enabled packages')
    display(doc, args, final=args.action == 'migrate-apps' and not args.yes)
    output.plan(installation.items, args.dry_run)
    if args.dry_run or (args.action == 'migrate-apps' and not args.yes):
        return int(installation.blocked)
    if installation.blocked:
        raise ValueError('resolve the displayed conflicts before applying setup')
    if preparation and doc['preparation']:
        if not approve(args, 'Prepare these components before the final managed-change review?'):
            display(dict(doc, status='cancelled', items=[], message='No changes made.'), args, True)
            return 0
        try:
            preparation.run()
        except Exception as error:
            doc.update(preparation.results)
            Presentation(sys.stderr).emit('dots setup: '+Presentation.clean(str(error)))
            display(dict(doc,status='incomplete',stages=preparation.outcomes,
                preparation_record=str(preparation.record) if preparation.record.exists() else None,
                message='Preparation stopped; configuration was not applied. Completed preparation effects remain.'),args,True)
            return 1
        doc.update(preparation.results)
        try:
            if preparation.deferred_theme:
                previous_guards = installation.guards
                installation = Installation(root)
                installation.guards.update(previous_guards)
                installation.store.observer = output
                installation.plan_install(args.component, args.resource)
                setup_wizard.save_plan(root, installation, args)
                preparation.installation = installation
            installation.prepare()
            # Optional planners attach their verified payloads to this one final plan.
            preparation.finish(installation)
        except Exception as error:
            preparation.save_outcome('managed-payloads','failed',reason=str(error))
            Presentation(sys.stderr).emit('dots setup: '+Presentation.clean(str(error)))
            display(dict(doc,status='incomplete',stages=preparation.outcomes,
                preparation_record=str(preparation.record),
                message='Payload preparation stopped; configuration was not applied. Completed preparation effects remain.'),args,True)
            return 1
        doc['items'] = installation.items
        doc['stages'] = preparation.outcomes
        doc['preparation_record'] = str(preparation.record) if preparation.record.exists() else None
        display(dict(doc, message='Final managed changes; completed preparation effects remain if cancelled.'), args)
        if installation.blocked: raise ValueError('resolve conflicts in the final managed plan')
    if not approve(args, 'Apply these managed changes?'):
        display(dict(doc, status='cancelled', items=[], message='Managed changes cancelled; completed preparation effects remain.'), args, True)
        return 0
    try:
        result = installation.apply(args.action)
    except (OSError, ValueError) as error:
        if preparation and preparation.outcomes:
            preparation.save_outcome('publication', 'failed', reason=str(error))
            raise ValueError('Managed setup failed; completed preparation effects remain: '+str(error)) from error
        raise
    if installation.theme_notice:
        ui = Presentation(sys.stderr)
        if args.json:
            ui.color = ui.icons = False
        ui.emit(ui.paint('Vivid compatibility mode', '93'))
        ui.detail('Detail', installation.theme_notice)
    if args.action == 'uninstall':
        installation.prune_empty_parents()
    incomplete = any(x['status'] == 'preserved' for x in installation.items)
    completed = {'create':'linked', 'replace-with-backup':'linked', 'restore':'restored', 'remove':'removed', 'prepare':'published'}
    final_items = [dict(row, status=completed.get(row['status'], row['status'])) for row in installation.items]
    display(dict(doc, status='incomplete' if incomplete else result['status'],
                 transaction=result.get('id'), items=final_items,
                 message='Changed targets were preserved.' if incomplete else 'Completed. Recovery records and retained backups remain available.'), args, True)
    return int(incomplete)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('Interrupted; inspect dots files history before retrying.', file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots setup: ' + str(error), '91'))
        sys.exit(1)
