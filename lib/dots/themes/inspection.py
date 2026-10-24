#!/usr/bin/env python3
"""Read-only inspection of one published theme generation; never publish or apply."""
import argparse
import itertools
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB.parent))
sys.path.insert(0, str(LIB.parent / 'files'))
from catalog import Presentation, platform
from file_platform import config_root, state_root, open_nofollow, check_object
from transactions import parents_safe
from interaction import Selector, SelectionEnded, terminal
from app_paths import eza_config_directory, television_config_directory, leaf_config_directory, config_directory
from picker import CREDENTIAL, LIMIT
from file_preview import directory_view, text_view, resource_span

# These are publication internals, never browsable content or completion operands.
INTERNAL = {'id', 'selection', 'fingerprint', 'previous', 'previous-active', 'status',
            'connectors', 'commands', 'commands-old', 'commands-new', 'active.new'}
CACHES = {'bat-cache', 'bat-source', 'delta-cache'}
DERIVED = {'yazi/flavor.toml': 'yazi.toml', 'yazi/tmtheme.xml': 'bat.tmTheme'}
SHARED = {'palette.json', 'shell.tsv', 'init.zsh', 'init.fish', 'init.ps1',
          'colors.json', 'colors.lua', 'ls_colors', 'file-styles.tsv', 'git-styles.tsv'}
OVERRIDES = set('kitty.conf tmux.conf btop.theme termux.properties bat.tmTheme yazi.toml '
                'fzf.sh gum_env.sh pi.json vivid.yml fsh.ini eza.yml television.toml leaf.toml'.split())
# Non-link consumers describe integration mechanisms, not live process state.
CONSUMERS = {
    'bat.tmTheme': [('bat', 'environment', 'BAT_THEME=Dots; generation-local BAT_CACHE_PATH')],
    'bat-cache': [('bat', 'environment', 'BAT_CACHE_PATH'), ('delta', 'environment', 'generation syntax cache')],
    'delta-cache': [('delta', 'environment', 'generation syntax cache')],
    'kitty.conf': [('kitty', 'include', 'Stable theme file or local connector include')],
    'fzf.sh': [('fzf', 'environment', 'Dots shell initialization')],
    'gum_env.sh': [('gum', 'include', 'Optional explicit sourcing / Dots interaction adapter')],
    'fsh.ini': [('fsh', 'include', 'Dots Zsh syntax-highlighting adapter')],
    'vivid.yml': [('vivid', 'environment', 'Dots shell LS_COLORS generation')],
    'ls_colors': [('shell', 'environment', 'LS_COLORS through Dots shell initialization')],
    'palette.json': [('nvim', 'include', 'Dots palette reader')],
    'colors.json': [('yazi', 'include', 'Dots Yazi plugin'), ('dots', 'include', 'Shared semantic colors')],
    'colors.lua': [('lua', 'include', 'Optional Lua palette consumers')],
    'file-styles.tsv': [('dots', 'include', 'Shared resource presentation')],
    'git-styles.tsv': [('dots', 'include', 'Git presentation')],
    'shell.tsv': [('shell', 'include', 'Dots shell palette data')],
    'init.zsh': [('shell', 'include', 'Bash/Zsh initialization')],
    'init.fish': [('shell', 'include', 'Fish initialization')],
    'init.ps1': [('shell', 'include', 'PowerShell initialization')],
    'gtk.css': [('gtk', 'plugin', 'Optional GTK plugin')],
    'qt6ct.conf': [('qt6ct', 'plugin', 'Optional Qt plugin')],
    'blastoff.toml': [('starship', 'plugin', 'Optional Starship/Blastoff palette merge')],
}
BAD = {'missing', 'broken', 'points-elsewhere', 'regular-file', 'unavailable', 'pinned'}


def bounded(path, limit=2 * 1024 * 1024):
    """No symlink parents, special-file opens, unbounded reads or evaluation."""
    path = Path(path)
    parents_safe(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('expected a regular data file')
    fd = open_nofollow(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('file type changed')
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('data exceeds size limit')
    return data


def identifier(value):
    p = PurePosixPath(value)
    if (not value or '\\' in value or p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/'))
            or p.parts[0] in INTERNAL or p.parts[0].startswith('.') or len(p.parts) > 2):
        raise ValueError('expected a listed generation-relative file identifier')
    return value


def lexical(path):
    return Path(os.path.abspath(path))


def registry():
    return [line.split('\t') for line in (LIB / 'connectors.tsv').read_text().splitlines() if line]


class Inspection:
    def __init__(self):
        self.state, self.config = state_root(), config_root()
        self.home = Path(os.environ.get('HOME') or Path.home())
        self.checkout = Path(os.environ.get('DOTS') or LIB.parents[2]).resolve()
        self.theme_root = Path(os.environ.get('DOTHEMES') or os.environ.get('THEMES') or self.checkout / 'themes')
        self.templates = Path(os.environ.get('DOTS_THEME_TEMPLATES') or self.checkout / 'default/themed')
        self.personal = self.config / 'dots/themed'
        self.active = self.state / 'current/theme'
        self.generation = None
        self.identity = None
        self.findings = []
        self.rows = {}
        self.connections = []
        self.publication = 'absent'
        self._inventoried = False
        self._snapshot()

    def finding(self, message, artifact=None):
        self.findings.append(dict(artifact=artifact, message=message))

    def _snapshot(self):
        try:
            parents_safe(self.active)
            if not os.path.lexists(self.active):
                return
            if not self.active.is_symlink():
                raise ValueError('active theme is not a managed link')
            target = lexical(self.active.parent / os.readlink(self.active))
            if target.parent != self.state / 'themes/generations' or not re.fullmatch(r'g\.[a-zA-Z0-9]+', target.name):
                raise ValueError('active theme points outside managed generations')
            parents_safe(target / 'id')
            if not target.is_dir():
                raise ValueError('active generation is missing')
            identity = bounded(target / 'id', 256).decode('utf-8').strip()
            if not re.fullmatch(r'[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*', identity):
                raise ValueError('invalid published theme identity')
            self.generation, self.identity = target, identity
            self.publication = 'available'
        except (OSError, ValueError, RuntimeError, UnicodeError):
            self.publication = 'unavailable'
            self.finding('Active theme pointer or generation is missing, unreadable or unsafe.')

    def source(self, name):
        if name in DERIVED:
            return dict(kind='derived', path=None, artifact=DERIVED[name], basis='current-resolution')
        if name in SHARED or name in CACHES:
            return dict(kind='generated', path=None, artifact=None, basis='current-resolution')
        bundled = self.theme_root / self.identity
        user = self.config / 'dots/themes' / self.identity
        candidates = []
        bundled_palette = any((bundled / f).is_file() for f in ('colors.toml', 'palette.toml'))
        if bundled_palette and user.is_dir():
            return dict(kind='unknown', path=None, artifact=None, basis='current-resolution')
        if name in OVERRIDES and bundled_palette:
            candidates.append(('bundled-override', bundled / name))
        candidates += [('personal-template', self.personal / (name + '.tpl')),
                       ('default-template', self.templates / (name + '.tpl'))]
        for kind, path in candidates:
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                return dict(kind=kind, path=str(path.absolute()), artifact=None, basis='current-resolution')
            except OSError:
                continue
        return dict(kind='unknown', path=None, artifact=None, basis='current-resolution')

    def add(self, name, required=False):
        identifier(name)
        if name in self.rows:
            self.rows[name]['required'] |= required
            return
        path = self.generation / name
        status, kind = 'available', 'cache' if name in CACHES else 'file'
        try:
            parents_safe(path)
            check_object(path)
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) if kind == 'cache' else stat.S_ISREG(mode)):
                status = 'unavailable'
            elif not os.access(path, os.R_OK):
                status = 'unavailable'
        except FileNotFoundError:
            status = 'missing'
        except (OSError, ValueError):
            status = 'unavailable'
        try:
            source = self.source(name)
        except (OSError, ValueError, RuntimeError):
            source = dict(kind='unknown', path=None, artifact=None, basis='current-resolution')
        self.rows[name] = dict(id=name, kind=kind, status=status, required=required,
                               path=str(self.active / name), resolved_path=str(path),
                               source=source, consumers=[], connections=[])

    def fixed_connections(self, *, windows=None):
        """Mirror publisher eligibility, including app-specific native destinations."""
        windows = os.name == 'nt' if windows is None else windows
        connector_config = Path(os.environ.get('XDG_CONFIG_HOME') or self.home / '.config')
        for app, suffix, artifact in registry():
            base = connector_config / app
            supported = not windows or app in ('yazi', 'git', 'vivid', 'eza', 'television', 'leaf')
            error = None
            try:
                if app == 'eza': base = eza_config_directory(windows=windows)
                elif app == 'television': base = television_config_directory(windows=windows)
                elif app == 'leaf': base = leaf_config_directory(windows=windows)
                elif windows and app == 'yazi': base = config_directory('yazi')
                target = base / suffix if base else None
                eligible = supported and target is not None and (
                    base.is_dir() if app in ('television', 'leaf') else target.parent.is_dir())
            except (OSError, ValueError, RuntimeError):
                target, eligible, error = None, False, 'Invalid or unreadable application directory.'
            self.connect(app, artifact, target, eligible, supported, error=error)
        if not windows:
            target = self.home / '.termux/colors.properties'
            self.connect('termux', 'termux.properties', target, target.parent.is_dir())
        for app, value, suffix, artifact in (
            ('codex', os.environ.get('CODEX_HOME') or str(self.home / '.codex'), 'themes/dots.tmTheme', 'bat.tmTheme'),
            ('pi', os.environ.get('PI_CODING_AGENT_DIR') or str(self.home / '.pi/agent'), 'themes/dots.json', 'pi.json')):
            base = Path(value).expanduser()
            safe = base.is_absolute() and not any(p in ('.', '..') for p in value.replace('\\', '/').split('/')) and not any(ord(c) < 32 for c in value)
            self.connect(app, artifact, base / suffix if safe else None,
                         safe and (base / suffix).parent.is_dir(), error=None if safe else 'Invalid application directory.')

    def connect(self, app, artifact, target, eligible, supported=True, origin='fixed', error=None):
        row = dict(app=app, artifact=artifact, target=str(target) if target else None,
                   resolved_target=None, link_target=None, expected=str(self.active / artifact),
                   status='not-configured', eligible=bool(eligible), origin=origin, reason=error)
        if error or not supported or target is None:
            row['status'] = 'unavailable'
            row['reason'] = error or 'No connector on this platform.'
        else:
            try:
                for parent in target.parents: check_object(parent)
                row['resolved_target'] = str(target.parent.resolve(strict=False) / target.name)
                check_object(target)
                mode = target.lstat().st_mode
                if stat.S_ISLNK(mode):
                    raw = os.readlink(target)
                    row['link_target'] = raw
                    dest = lexical(target.parent.resolve(strict=False) / raw)
                    expected = self.active / artifact
                    row['status'] = ('linked' if dest == expected else
                                     'pinned' if target.resolve(strict=False) == self.generation / artifact else 'points-elsewhere')
                    if dest == expected:
                        if not (self.generation / artifact).exists(): row['status'] = 'broken'
                    elif not target.exists(): row['status'] = 'broken'
                else:
                    row['status'] = 'regular-file' if stat.S_ISREG(mode) else 'unavailable'
            except FileNotFoundError:
                row['status'] = 'missing' if eligible else 'not-configured'
            except (OSError, ValueError, RuntimeError):
                row['status'], row['reason'] = 'unavailable', 'Cannot safely inspect destination.'
        self.connections.append(row)

    def supplementary(self):
        """Bounded journal metadata only; never read retained before/after contents."""
        root = self.state / 'files/transactions'
        try:
            parents_safe(root / 'entry')
            if not root.is_dir(): return
            with os.scandir(root) as entries:
                paths = list(itertools.islice(entries, 513))
            if len(paths) > 512:
                self.finding('Supplementary connection inspection limited to 512 transaction records.')
            known = {c['resolved_target'] for c in self.connections}
            for item in sorted(paths[:512], key=lambda e: e.name):
                if not re.fullmatch('[a-f0-9]{32}', item.name) or item.is_symlink(): continue
                directory = Path(item.path)
                try:
                    doc = json.loads(bounded(directory / 'journal.json'))
                    if doc.get('schema') != 1 or doc.get('status') != 'complete': continue
                    operations = doc.get('operations', [])
                    if not isinstance(operations, list) or len(operations) > 4096:
                        raise ValueError('invalid operations')
                    for op in operations:
                        target = Path(op['path'])
                        if not target.is_absolute(): continue
                        for parent in target.parents: check_object(parent)
                        # Finalized journals discard prepared objects. Observe the
                        # recorded destination link; never read its file contents.
                        if not target.is_symlink(): continue
                        source = lexical(target.parent.resolve(strict=False) / os.readlink(target))
                        if not source.is_absolute() or not source.is_relative_to(self.active): continue
                        artifact = source.relative_to(self.active).as_posix()
                        if artifact not in self.rows and artifact != 'yazi': continue
                        actual = str(target.parent.resolve(strict=False) / target.name)
                        if actual in known: continue
                        known.add(actual)
                        app = 'bat' if target.name == 'Dots.tmTheme' else 'managed'
                        self.connect(app, artifact, target, True, origin='transaction')
                except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
                    self.finding('A retained transaction could not be inspected for supplementary connections.')
        except (OSError, ValueError, RuntimeError):
            self.finding('Retained transaction metadata is unavailable for supplementary connections.')

    def inventory(self, app=None, connections=True):
        if self.generation is not None and not self._inventoried:
            self._inventoried = True
            try:
                with os.scandir(self.generation) as entries:
                    names = [e.name for e in itertools.islice(entries, 1025)]
                if len(names) > 1024: raise ValueError('too many generated entries')
                for name in sorted(names):
                    if name in INTERNAL or name.startswith('.'): continue
                    if name == 'yazi': continue
                    self.add(name)
                for base in (self.personal, self.templates):
                    templates = list(itertools.islice(base.glob('*.tpl'), 1025))
                    if len(templates) > 1024: raise ValueError('too many templates')
                    for template in templates:
                        if template.is_file() and not template.is_symlink() and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]*', template.stem) and template.stem not in INTERNAL:
                            self.add(template.stem, required=True)
                # Only fixed derived children are traversed; never recurse caches/journals.
                for name in DERIVED: self.add(name, required=True)
                for name in (('init.ps1', 'init.zsh', 'init.fish') if os.name == 'nt' else ('init.zsh', 'init.fish')):
                    self.add(name, required=True)
                for name in ('palette.json', 'colors.json', 'colors.lua', 'shell.tsv', 'ls_colors', 'file-styles.tsv', 'git-styles.tsv'):
                    self.add(name, required=True)
                for _, _, name in registry():
                    if name != 'yazi': self.add(name, required=True)
                if connections:
                    self.fixed_connections()
                    self.supplementary()
                for row in self.rows.values():
                    row['consumers'] = [dict(app=a, kind=k, description=d, activation='unverified')
                                        for a, k, d in CONSUMERS.get(row['id'], [])]
                    row['connections'] = [c for c in self.connections if c['artifact'] == row['id'] or
                                          (c['artifact'] == 'yazi' and row['id'].startswith('yazi/'))]
                    if row['status'] != 'available':
                        self.finding('Generated artifact is ' + row['status'] + '.', row['id'])
            except (OSError, ValueError, RuntimeError):
                self.finding('Generation inventory is unreadable, unsafe or exceeds its entry limit.')
        rows = sorted(self.rows.values(), key=lambda r: r['id'])
        if app:
            rows = [r for r in rows if any(c['app'] == app for c in r['connections'] + r['consumers'])]
        ids = {r['id'] for r in rows}
        findings = [f for f in self.findings if not app or f['artifact'] is None or f['artifact'] in ids]
        failures = [c for r in rows for c in r['connections'] if c['status'] in BAD and (c['eligible'] or c['reason'] not in (None, 'No connector on this platform.') or c['link_target'] is not None) and (not app or c['app'] == app)]
        return dict(schema=1, platform=platform(), generation=dict(status=self.publication, id=self.generation.name if self.generation else None,
                    theme=self.identity, path=str(self.active), resolved_path=str(self.generation) if self.generation else None),
                    artifacts=rows, findings=findings, healthy=self.publication == 'available' and (not app or bool(rows)) and not findings and not failures)

    def record(self, name):
        identifier(name)
        if name not in self.rows: raise ValueError('unknown generated file; use dots theme files list')
        return self.rows[name]


def text_content(row, source=False):
    value = row['source']['path'] if source else row['resolved_path']
    if value is None: raise ValueError('no template or override source for this artifact')
    path = Path(value)
    # Source roots may be managed directory links; leaf links remain refused.
    if source:
        for parent in path.parents: check_object(parent)
        if path.is_symlink(): raise ValueError('source leaf is a symlink')
        path = path.parent.resolve(strict=True) / path.name
    data = bounded(path, LIMIT)
    if b'\0' in data or CREDENTIAL.search(data):
        raise ValueError('binary or possible credential content cannot be displayed')
    data.decode('utf-8')
    return data


def ui_for_output():
    ui = Presentation()
    # Inspection listings are plain when redirected, even with forced decoration.
    if not sys.stdout.isatty(): ui.color = ui.icons = ui.human = False
    return ui


def verification_code(evidence):
    status = evidence.get('status', 'unknown')
    return '92' if status in ('matches', 'configured') else '93' if status in ('different', 'stale') else '90'


def info_view(ui, row):
    ui.heading_spans([('Theme file: ' + row['id'], '1;96')])
    ui.detail('Status', row['status'])
    ui.resource_detail('Active', row['path'])
    ui.resource_detail('Generation', row['resolved_path'])
    source = row['source']
    ui.emit()
    ui.detail('Source basis', 'Source for next refresh; historical provenance is unrecorded')
    ui.detail('Source kind', source['kind'])
    if source['path']: ui.resource_detail('Source', source['path'])
    if source['artifact']: ui.detail('Derived from', source['artifact'])
    for app, group in application_groups(row).items():
        ui.emit()
        ui.detail('Application', app)
        for c in group['connections']:
            ui.detail('Connection', c['status'], '92' if c['status'] == 'linked' else '93')
            if c['target']: ui.resource_detail('Target', c['target'])
            if c['resolved_target'] and c['resolved_target'] != c['target']:
                ui.resource_detail('Location', c['resolved_target'])
            if c['link_target']: ui.resource_detail('Link value', c['link_target'])
            ui.resource_detail('Expected', c['expected'])
            if c['reason']: ui.detail('Reason', c['reason'])
        for c in group['consumers']: ui.detail('Usage', c['kind'] + ': ' + c['description'])
        for evidence in group['evidence']:
            ui.detail('Evidence', evidence['summary'], verification_code(evidence))
            ui.detail('Basis', evidence['basis'])
            ui.detail('Reason', evidence['reason'])
            if evidence['automation']: ui.detail('Auto-update', evidence['automation'])
            for path in evidence['paths']: ui.resource_detail('Checked', path)
    ui.emit()
    ui.detail('Scope', 'Configuration and inherited values only; running applications are not queried.')


def application_groups(row):
    groups = {}
    for field in ('connections', 'consumers'):
        for item in row[field]:
            group = groups.setdefault(item['app'], dict(connections=[], consumers=[], evidence=[]))
            group[field].append(item)
            evidence = item.get('verification')
            if evidence and evidence not in group['evidence']: group['evidence'].append(evidence)
    return groups


def list_view(ui, doc, check=False):
    ui.heading('Theme file check' if check else 'Theme files')
    ui._spans([(doc['generation']['theme'] or doc['generation']['status'], '94'),
               ('  |  ' + str(len(doc['artifacts'])) + ' artifacts', '90')], '  ')
    if not doc['artifacts']:
        ui.detail('Files', 'No generated files match; publish a theme or review the app filter.')
    for row in doc['artifacts']:
        ui.emit()
        kind = 'dir' if row['kind'] == 'cache' else 'file'
        ui._spans([resource_span(ui, row['resolved_path'], row['id'] + ('/' if kind == 'dir' else ''), kind),
                   ('  ' + row['status'], '90' if row['status'] == 'available' else '93')],
                  '  ', continuation_prefix='    ')
        for app, group in application_groups(row).items():
            spans = [(app + '  ', '94')]
            statuses = list(dict.fromkeys(c['status'] for c in group['connections']))
            for status in statuses:
                spans += [(status + '  ', '92' if status == 'linked' else '93')]
            evidence = [e for e in group['evidence'] if e['status'] != 'unknown']
            if evidence:
                for e in evidence:
                    label = e['summary']
                    if e['automation']: label += '; auto-update ' + e['automation']
                    spans.append((label + '  ', verification_code(e)))
            elif not statuses:
                kinds = ', '.join(dict.fromkeys(c['kind'] for c in group['consumers']))
                spans.append((kinds, '90'))
            spans[-1] = (spans[-1][0].rstrip(), spans[-1][1])
            ui._spans(spans, '    ', continuation_prefix='      ')
            for c in group['connections']:
                if c['target']: ui._spans([resource_span(ui, c['target'])], '      ')
    ui.emit()
    for finding in doc['findings']: ui.detail('Attention', finding['message'], '93')
    if check and doc.get('consumer_checks'):
        for finding in doc.get('consumer_findings', []):
            ui.detail('Consumer', finding['app'] + ': ' + finding['reason'], '93')
    ui.detail('Result', f"{len(doc['artifacts'])} generated artifacts" + ('; checks passed' if check and doc['healthy'] else '; attention required' if check else ''))
    ui.detail('Scope', 'Checks cover configuration and inherited values. Running apps are not queried; use info FILE for evidence.')


def show_content(ui, row, source=False, raw=False):
    path = Path(row['resolved_path'])
    directory = row['kind'] == 'cache' and (not source or row['source']['path'] is None)
    if directory:
        if raw: raise ValueError('--raw requires a regular text file; omit it to list directory contents')
        directory_view(ui, path, fallback=source)
        return
    data = text_content(row, source)
    if raw or not ui.stream.isatty():
        ui.stream.buffer.write(data)
    else:
        generation = path.parents[len(PurePosixPath(row['id']).parts) - 1]
        filename = row['source']['path'] if source else row['id']
        text_view(ui, data, filename, generation)


def observed(inspect, app=None, include_failures=False):
    from consumer_checks import annotate
    return annotate(inspect, inspect.inventory(app), bounded, include_failures, app)


def browse(app=None, selector=None):
    selector = selector or Selector()
    ui = ui_for_output()
    while True:
        inspect = Inspection()
        doc = observed(inspect, app)
        if not doc['artifacts']:
            list_view(ui, doc)
            return 0
        # Numeric prefixes keep display escaping and duplicate labels out of operands.
        choices = {f"{n + 1}. {ui.clean(r['id'])}": r['id'] for n, r in enumerate(doc['artifacts'])}
        choice = selector.pick('filter', 'Generated theme files', [*choices, 'Exit'])
        if choice == 'Exit': return 0
        if choice not in choices: raise ValueError('unknown selection')
        name = choices[choice]
        while True:
            # Refresh after every interaction, including a theme switch while browsing.
            current = Inspection(); current_doc = observed(current, app)
            if not any(r['id'] == name for r in current_doc['artifacts']): break
            row = current.record(name)
            info_view(ui, row)
            contents = 'Directory contents' if row['kind'] == 'cache' else 'Generated contents'
            actions = ['Back', contents] + (['Source contents'] if row['source']['path'] else []) + ['Exit']
            action = selector.pick('choose', 'Inspect file', actions, 'Back')
            if action == 'Back': break
            if action == 'Exit': return 0
            if action not in actions: raise ValueError('unknown action')
            try:
                fresh = Inspection(); fresh.inventory(app)
                row = fresh.record(name)
                if row['kind'] == 'cache':
                    directory_view(ui, row['resolved_path'])
                else:
                    data = text_content(row, action == 'Source contents')
                    filename = row['source']['path'] if action == 'Source contents' else row['id']
                    text_view(ui, data, filename, fresh.generation)
            except (OSError, ValueError, RuntimeError):
                ui.detail('Content', 'Unavailable, unsafe, binary or exceeds 64 KiB.')


def parser():
    p = argparse.ArgumentParser(prog='dots theme files', description=__doc__)
    subs = p.add_subparsers(dest='action')
    for action in ('list', 'info', 'show', 'path', 'check', 'browse'):
        sub = subs.add_parser(action)
        if action in ('info', 'show'): sub.add_argument('file')
        if action == 'path': sub.add_argument('file', nargs='?')
        if action in ('list', 'check', 'browse'): sub.add_argument('--app')
        if action in ('list', 'info', 'check'): sub.add_argument('--json', action='store_true')
        if action in ('show', 'path'): sub.add_argument('--source', action='store_true')
        if action == 'show': sub.add_argument('--raw', action='store_true')
        if action == 'check': sub.add_argument('--consumers', action='store_true')
        if action == 'path': sub.add_argument('--resolved', action='store_true')
    return p


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ('__files', '__apps'):
        if len(args) != 1: raise ValueError('unexpected completion arguments')
        if args[0] == '__apps':
            names = {r[0] for r in registry()} | {'codex', 'pi', 'termux', 'managed'}
            names.update(a for consumers in CONSUMERS.values() for a, _, _ in consumers)
        else:
            names = {r['id'] for r in Inspection().inventory(connections=False)['artifacts']}
        for name in sorted(names):
            if not any(ord(c) < 32 or ord(c) == 127 for c in name): print(name)
        return 0
    if not args or args[0].startswith('-') and args[0] not in ('-h', '--help'): args.insert(0, 'list')
    p = parser(); opts = p.parse_args(args)
    if opts.action == 'path' and (opts.source and (opts.resolved or not opts.file)):
        p.error('--source requires FILE and cannot be combined with --resolved')
    if opts.action == 'browse':
        if not terminal(): p.error('browse requires terminal input and output; use dots theme files list')
        return browse(opts.app)
    inspect = Inspection(); doc = inspect.inventory(getattr(opts, 'app', None))
    row = inspect.record(opts.file) if getattr(opts, 'file', None) else None
    if opts.action in ('list', 'info', 'check'):
        if row is not None: doc['artifacts'] = [row]
        from consumer_checks import annotate
        annotate(inspect, doc, bounded, getattr(opts, 'consumers', False), getattr(opts, 'app', None))
    if opts.action == 'path':
        if inspect.generation is None: raise ValueError('no available active theme generation')
        value = (row['source']['path'] if opts.source else row['resolved_path'] if opts.resolved else row['path']) if row else (str(inspect.generation) if opts.resolved else str(inspect.active))
        if value is None: raise ValueError('no template or override source for this artifact')
        print(value)
    elif opts.action == 'show':
        show_content(ui_for_output(), row, opts.source, opts.raw)
    elif getattr(opts, 'json', False):
        if row is not None: doc['artifacts'] = [row]
        print(json.dumps(doc, ensure_ascii=True, sort_keys=True))
    elif opts.action == 'info': info_view(ui_for_output(), row)
    else: list_view(ui_for_output(), doc, opts.action == 'check')
    return 1 if opts.action == 'check' and not doc['healthy'] else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SelectionEnded as end:
        sys.exit(end.status)
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError, RuntimeError) as error:
        if sys.stderr.isatty():
            ui = Presentation(sys.stderr)
            ui.heading('Theme file inspection failed')
            ui.detail('Error', str(error), '91')
        else:
            print('dots theme files: ' + Presentation.clean(error), file=sys.stderr)
        sys.exit(1)
