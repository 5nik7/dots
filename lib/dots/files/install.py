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
from file_platform import lock, open_nofollow, state_root
from transactions import Store, digest, exists, parents_safe, private_directory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from interaction import gum_confirm
from progress import Progress, configure

PUBLIC_SOURCES = ('androidots', 'windots', 'nvim')


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
    if not sys.stdin.isatty():
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
                        intended = 'symlink' if row.get('source') else 'file'
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
        self.theme = None
        self.blocked = False
        self.transaction = uuid.uuid4().hex
        for record in self.store.records():
            if record['status'] in ('preparing', 'applying', 'rolling-back', 'recovery-required'):
                raise ValueError('unfinished transaction: run dots files recover ' + record['id'])

    def item(self, identity, status, target=None, source=None, reason=None):
        row = dict(id=identity, status=status)
        row.update({k: str(v) for k, v in dict(target=target, source=source, reason=reason).items() if v is not None})
        self.items.append(row)
        if status == 'conflict':
            self.blocked = True

    def guard(self, path):
        path = str(path)
        parents_safe(path)
        self.guards.setdefault(path, digest(path))

    def add(self, identity, path, *, link=None, text=None, directory=False, managed=False):
        path = Path(path)
        self.guard(path)
        key = str(path)
        if any(op['path'] == key for op in self.operations):
            raise ValueError('duplicate installation target: ' + key)
        owned = self.entries.get(key)
        current = self.guards[key]
        same = (link is not None and path.is_symlink() and os.readlink(path) == str(link))
        if text is not None:
            same = path.is_file() and not path.is_symlink() and path.read_text(encoding='utf-8') == text
        if owned and current != owned['after'] and not managed:
            self.item(identity, 'conflict', path, reason='installer-owned target changed; preserve and review it')
            return
        if same:
            self.item(identity, 'unchanged', path, link)
            return
        if path.is_symlink() and not owned and not managed:
            # A matching relative link predating setup is observed, never owned.
            if link is not None and path.resolve() == Path(link).resolve():
                self.item(identity, 'unchanged', path, link)
                return
            self.item(identity, 'conflict', path, reason='unrelated link is protected')
            return
        if link is not None and path.is_dir() and path.resolve() == Path(link).resolve():
            raise ValueError('source and target overlap: ' + key)
        op = dict(path=key)
        if link is not None:
            op.update(link=str(link), directory=directory)
        else:
            op['text'] = text
        self.operations.append(op)
        if not owned:
            owned = dict(id=identity, before=current, backup=self.transaction,
                         index=len(self.operations)-1)
            self.entries[key] = owned
        owned['desired'] = {k: v for k, v in op.items() if k != 'path'}
        self.item(identity, 'replace-with-backup' if current is not None else 'create', path, link)

    def theme_bridge(self, mode, fingerprint=None):
        cmd = ([sys.executable, '-B', str(self.root / 'lib/dots/themes/setup.py'), mode]
               if self.platform == 'windows' else ['bash', str(self.root / 'lib/dots/themes/setup.bash'), mode])
        if fingerprint:
            cmd.append(fingerprint)
        result = subprocess.run(cmd, env=dict(os.environ, DOTS=str(self.root), DOTS_PROGRESS='never',
                                             DOTS_COLOR='never', DOTS_ICONS='never'),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise ValueError('theme preparation failed: ' + result.stderr.decode(errors='replace').strip())
        return result.stdout.decode().split('\0')[:-1]

    def plan_install(self):
        catalog = Catalog(self.root, self.platform)
        self.guard(self.root / '.dots/sources.json')
        for source in catalog.sources:
            if source['status'] == 'excluded':
                continue
            self.guard(Path(source['root']) / '.dots/files.json')
            if self.platform in source['platforms'] and source['status'] != 'available':
                self.item(source['id'], 'skipped', reason='optional source unavailable; select --with-source ' + source['id'])
        observed = catalog.records()
        for row in observed:
            if row['applicable'] and not row['enabled']:
                self.item(row['id'], 'skipped', row['target'], reason='stashed')
        records = [r for r in observed if r['enabled'] and r['applicable'] and r['status'] != 'replaced']
        connectors = []
        if (self.root / 'lib/dots/themes' / ('setup.py' if self.platform == 'windows' else 'setup.bash')).is_file():
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
                if self.platform == 'windows' and app not in ('yazi', 'git', 'vivid', 'eza'):
                    continue
                owner = next((r for r in records if r['app'] == app and r['strategy'] == 'directory-link' and r['target']), None)
                if app == 'eza':
                    from app_paths import eza_config_directory
                    base = eza_config_directory(windows=self.platform == 'windows')
                    if not owner or Path(owner['target']) != base:
                        continue
                if owner and Path(owner['source']).is_dir():
                    connectors.append((app, Path(owner['source']) / suffix, artifact))
            if self.platform == 'termux':
                target = Path(os.environ['HOME']) / '.termux/colors.properties'
                records = [r for r in records if r['target'] != str(target)]
                if not any(not r['enabled'] and r['target'] == str(target) for r in observed):
                    connectors.append(('termux', target, 'termux.properties'))
            # Preserve the publisher's opt-in-by-existing-directory boundaries.
            for app, parent, filename, artifact in (
                ('codex', Path(os.environ.get('CODEX_HOME') or Path.home()/'.codex')/'themes', 'dots.tmTheme', 'bat.tmTheme'),
                ('pi', Path(os.environ.get('PI_CODING_AGENT_DIR') or Path.home()/'.pi/agent').expanduser()/'themes', 'dots.json', 'pi.json')):
                if parent.is_dir():
                    connectors.append((app, parent / filename, artifact))
        for row in records:
            if row['status'] in ('unmapped', 'unsupported-platform', 'source-missing', 'source-broken-link'):
                self.item(row['id'], 'skipped', row['target'], reason=row['status'])
                continue
            if row['status'] == 'conflict' or row['strategy'] == 'copy':
                self.item(row['id'], 'conflict', row['target'], reason='catalog ownership conflict or unsupported copy preference')
                continue
            source, target = Path(row['source']), Path(row['target'])
            if source.is_symlink():
                self.item(row['id'], 'conflict', target, reason='source must be a regular file or owned directory')
                continue
            if target == source or target in source.parents or source in target.parents:
                raise ValueError('overlapping source and target: ' + str(target))
            self.guard(source)
            from git_platform import plan as plan_git_platform
            plan_git_platform(self, row)
            # Link identity is the installed object; later source edits remain
            # editable. During this apply, sources are bound to the preview.
            self.add(row['id'], target, link=source, directory=source.is_dir())
        home = Path(os.environ.get('HOME') or Path.home())
        launcher = 'dots.ps1' if self.platform == 'windows' else 'dots'
        if self.platform == 'windows':
            quoted = str(self.root / 'bin/dots.ps1').replace("'", "''")
            self.add('dots:command', home / '.local/bin' / launcher,
                     text="& '" + quoted + "' @args\nexit $LASTEXITCODE\n")
        else:
            self.add('dots:command', home / '.local/bin' / launcher, link=self.root / 'bin' / launcher)
        for app, path, artifact in connectors:
            desired = self.state / 'current/theme' / artifact
            old = os.readlink(path) if path.is_symlink() else ''
            # A fixed connector may repair a relocated generated-state link,
            # but an arbitrary link is never treated as installer ownership.
            managed = old.endswith('/dots/current/theme/' + artifact)
            self.add('theme:' + app, path, link=desired, directory=artifact == 'yazi', managed=managed)
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
        else:
            self.item('themes', 'skipped', reason='theme preparation adapter is unavailable')

    def plan_uninstall(self):
        for path, entry in list(self.entries.items())[::-1]:
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
        if not self.theme or not self.theme['refresh']:
            return
        self.store.notify('Preparing', reason='theme rendering and cache generation')
        with Progress('Preparing theme generation'):
            values = self.theme_bridge('prepare', self.theme['fingerprint'])
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
            if not self.operations:
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
                        with prepared.open('w', encoding='utf-8', newline='\n') as stream:
                            stream.write(op['text'])
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
    if not shutil.which('git'):
        raise ValueError('Git is required for --update and --with-source')
    catalog = Catalog(root, platform())
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
    parser.add_argument('action', choices=('install', 'uninstall'))
    parser.add_argument('--dry-run', action='store_true', help='preview without writes or network access')
    parser.add_argument('-v', '--verbose', action='store_true', help='show actions, backups and unchanged/skipped reasons')
    parser.add_argument('--yes', action='store_true', help='approve the displayed plan without prompting')
    parser.add_argument('--json', action='store_true', help='emit a schema-1 result')
    parser.add_argument('--update', action='store_true', help='fast-forward the clean checkout before planning setup')
    parser.add_argument('--with-source', action='append', default=[], choices=PUBLIC_SOURCES)
    parser.add_argument('--color', choices=('auto', 'always', 'never'))
    parser.add_argument('--icons', choices=('auto', 'always', 'never'))
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
    if args.action == 'uninstall' and (args.update or args.with_source):
        parser.error('--update and --with-source require install')
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
        forwarded = [args.action]
        for flag in ('yes', 'json', 'verbose'):
            if getattr(args, flag):
                forwarded.append('--' + flag)
        os.execv(sys.executable, [sys.executable, '-B', str(root / 'lib/dots/files/install.py'), *forwarded])
    installation = Installation(root)
    output = OperationOutput.for_args(args)
    installation.store.observer = output
    with Progress('Planning ' + args.action):
        if args.action == 'install':
            installation.plan_install()
        else:
            installation.plan_uninstall()
    doc = dict(schema=1, action=args.action, status='blocked' if installation.blocked else 'preview',
               platform=installation.platform, items=installation.items)
    display(doc, args)
    output.plan(installation.items, args.dry_run)
    if args.dry_run:
        return int(installation.blocked)
    if installation.blocked:
        raise ValueError('resolve the displayed conflicts before applying setup')
    if not approve(args):
        display(dict(doc, status='cancelled', items=[], message='No changes made.'), args, True)
        return 0
    result = installation.apply(args.action)
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
