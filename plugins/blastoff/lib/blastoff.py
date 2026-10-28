#!/usr/bin/env python3
"""Blastoff's shared command contract. No shell execution or network operations."""
from __future__ import annotations
import sys
# Shipped UI helpers must not create bytecode during read-only commands.
sys.dont_write_bytecode = True
VERSION = '0.1.12'
# Shared human-output accents; source text is sanitized before these are added.
PURPLE = '38;2;138;12;233'
PINK = '38;2;255;67;191'
HUMAN_STYLES = {'id':'97', 'label':PURPLE, 'value':PINK, 'separator':'2',
                'prefix':'2;'+PURPLE, 'selected':'1;'+PINK,
                'list_heading':'1;38;2;235;10;101'}
_UI_MODULES = {}

def ui_module(module):
    # Resolve shipped siblings once per invocation, including isolated (-I) mode.
    if module in _UI_MODULES:
        return _UI_MODULES[module]
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('blastoff_' + module, Path(__file__).with_name(module + '.py'))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    _UI_MODULES[module] = loaded
    return loaded
if sys.version_info < (3, 11):
    print('blastoff: Python 3.11+ is required', file=sys.stderr)
    raise SystemExit(3)
# Decode only the private frontend boundary; ordinary Bash startup stays unchanged.
if __name__ == '__main__' and sys.argv[1:2] == ['--_powershell-argv-v1']:
    try:
        arguments, shell = ui_module('argv_transport').decode(sys.argv[1:])
        sys.argv[1:] = arguments
        if shell:
            import os
            os.environ['BLASTOFF_NATIVE_PWSH'] = shell
    except ValueError as error:
        print('blastoff: '+str(error), file=sys.stderr)
        raise SystemExit(3)
# Keep version cheap and independent of files, Starship and optional tools.
if __name__ == '__main__' and sys.argv[1:] == ['--version']:
    print('blastoff ' + VERSION)
    raise SystemExit(0)
_CLI = None
def cli_module():
    global _CLI
    if _CLI is None:
        _CLI = ui_module('cli')
    return _CLI

_STARTUP_ARGS = None
if __name__ == '__main__':
    try:
        # Parse once before application imports. Explicit and implicit help use
        # the same parser; literal '--' and invalid options retain their meaning.
        _STARTUP_ARGS = cli_module().parse(sys.argv[1:], VERSION)
    except cli_module().Failure as e:
        if '--json' in sys.argv:
            import json
            print(json.dumps({'error':str(e), 'code':e.code}), file=sys.stderr)
        else:
            print('blastoff: ' + str(e), file=sys.stderr)
        raise SystemExit(e.code)
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
import tomllib
import uuid

MAX_FILE = 4 * 1024 * 1024
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z')
MODULE = re.compile(r'[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\Z')

Failure = cli_module().Failure

def name(value):
    if not NAME.fullmatch(value) or value.upper() in {'CON','PRN','AUX','NUL'} or re.fullmatch(r'(COM|LPT)[1-9]', value.upper()):
        raise Failure('Names must use 1–96 ASCII letters, digits, underscores or hyphens; start with a letter/digit and avoid Windows device names.', 2)
    return value

def module_path(value):
    if not MODULE.fullmatch(value):
        raise Failure('Module paths use letters, digits, underscores, hyphens and dots (example: custom.clock).', 2)
    return tuple(value.split('.'))

def path(value):
    p = Path(value).expanduser()
    if not p.is_absolute():
        raise Failure('Configured paths must be absolute: ' + str(p), 2)
    return p

def exists(p):
    return os.path.lexists(p)

def regular(p, links=False):
    try:
        s = p.stat() if links else p.lstat()
    except FileNotFoundError:
        raise Failure('File not found: ' + str(p))
    if not stat.S_ISREG(s.st_mode) or (not links and getattr(s, 'st_file_attributes', 0) & 0x400):
        raise Failure('Refusing non-regular file: ' + str(p))
    return s

def read(p, links=False):
    # O_NONBLOCK makes a raced-in FIFO fail rather than hang; fstat verifies it.
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0)
    if not links:
        flags |= getattr(os, 'O_NOFOLLOW', 0)
        regular(p)
    fd = os.open(p, flags)
    with os.fdopen(fd, 'rb') as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode):
            raise Failure('Refusing non-regular file: ' + str(p))
        data = f.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise Failure('File exceeds 4 MiB limit: ' + str(p))
    return data

def parsed(data):
    try:
        return tomllib.loads(data.decode('utf-8-sig'))
    except (ValueError, UnicodeError) as e:
        raise Failure('Invalid UTF-8 TOML: ' + str(e))

def storage_root(p):
    """Pin storage aliases, never child paths or the active-config pathname.

    Missing ordinary directories are allowed, but every link must resolve to an
    existing directory. Walking components preserves that distinction and rejects
    unsupported Windows reparse points rather than silently normalizing them.
    """
    redirects = 0

    def resolve(directory, strict=False):
        nonlocal redirects
        current = Path(directory.anchor)
        # A Windows junction can target just a drive/UNC root. There may be no
        # components below the anchor, but that target must still exist.
        if strict and not stat.S_ISDIR(current.lstat().st_mode):
            raise Failure('Not a storage directory link target: ' + str(current))
        for part in directory.parts[1:]:
            if part == '..':
                current = current.parent
                continue
            candidate = current / part
            try:
                info = candidate.lstat()
            except FileNotFoundError:
                if strict:
                    raise Failure('Storage directory link target does not exist: ' + str(candidate))
                current = candidate
                continue
            reparse = getattr(info, 'st_file_attributes', 0) & 0x400
            if stat.S_ISLNK(info.st_mode) or reparse:
                if reparse and getattr(info, 'st_reparse_tag', None) not in (
                    0xA000000C, 0xA0000003,  # symlink / mount-point (junction)
                ):
                    raise Failure('Unsupported storage directory reparse point: ' + str(candidate))
                redirects += 1
                if redirects > 40:
                    raise Failure('Storage directory link loop or too many links: ' + str(p))
                target = Path(os.readlink(candidate))
                if not target.is_absolute():
                    target = current / target
                current = resolve(target, strict=True)
            elif not stat.S_ISDIR(info.st_mode):
                raise Failure('Not a storage directory: ' + str(candidate))
            else:
                current = candidate
        return current

    return resolve(p)


def inspect_parents(p):
    # Storage-root aliases are resolved separately; all remaining parents must
    # still be real directories, including children inside the storage root.
    for parent in [p, *p.parents]:
        if exists(parent):
            s = parent.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                raise Failure('Refusing symlink/reparse directory for a write: ' + str(parent))
            if not stat.S_ISDIR(s.st_mode):
                raise Failure('Not a directory: ' + str(parent))
def safe_parents(p):
    inspect_parents(p)
    p.mkdir(parents=True, exist_ok=True, mode=0o700)

def fingerprint(p):
    if not exists(p):
        return None
    s = p.lstat()
    content = read(p, links=True)
    return (s.st_dev, s.st_ino, s.st_mtime_ns, s.st_mode, hashlib.sha256(content).digest(), os.readlink(p) if p.is_symlink() else None)

def atomic(p, data, expected=None, *, check=None):
    safe_parents(p.parent)
    fd, temporary = tempfile.mkstemp(prefix='.' + p.name + '.', dir=p.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if expected is not None and exists(p) and not p.is_symlink():
            os.chmod(temporary, stat.S_IMODE(p.stat().st_mode))
        if check is not None:
            check()
        if fingerprint(p) != expected:
            raise Failure('Destination changed during operation; refusing to overwrite: ' + str(p))
        os.replace(temporary, p)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

@contextlib.contextmanager
def locks(paths):
    acquired = []
    try:
        for p in sorted(set(paths), key=str):
            safe_parents(p.parent)
            try:
                p.mkdir(mode=0o700)
            except FileExistsError:
                raise Failure('Another operation or a stale lock exists: ' + str(p) + '; inspect before removing it.')
            acquired.append(p)
        yield
    finally:
        for p in reversed(acquired):
            p.rmdir()

def table_sections(text):
    """Locate TOML table declarations outside strings/comments, then parse headers."""
    headers = []
    i = 0
    line_start = True
    depth = 0
    while i < len(text):
        c = text[i]
        if c == '\n':
            line_start = True
            i += 1
        elif c in ' \t\r' and line_start:
            i += 1
        elif c == '#':
            end = text.find('\n', i)
            i = len(text) if end < 0 else end
        elif c in "\"'":
            line_start = False
            quote = c
            triple = text.startswith(c * 3, i)
            size = 3 if triple else 1
            i += size
            while i < len(text):
                if quote == '"' and text[i] == '\\':
                    i += 2
                elif text.startswith(quote * size, i):
                    i += size
                    # TOML allows 4/5 quote characters at the end of multiline strings.
                    if triple:
                        while i < len(text) and text[i] == quote:
                            i += 1
                    break
                else:
                    i += 1
        elif c == '[' and line_start and depth == 0:
            start = i
            end = text.find('\n', i)
            end = len(text) if end < 0 else end
            declaration = text[i:end]
            try:
                header = tomllib.loads(declaration + '\n__blastoff_header_marker__ = true\n')
            except ValueError as e:
                raise Failure('Unsupported table declaration: ' + str(e))
            def locate(obj, route=()):
                if isinstance(obj, dict):
                    if obj.get('__blastoff_header_marker__') is True:
                        return route
                    for k, v in obj.items():
                        result = locate(v, route + (k,))
                        if result is not None:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = locate(item, route)
                        if result is not None:
                            return result
                return None
            route = locate(header)
            if route is None:
                raise Failure('Cannot locate table declaration')
            headers.append((start, route))
            i = end
            line_start = False
        else:
            if c in '[{':
                depth += 1
            elif c in ']}':
                depth -= 1
            line_start = False
            i += 1
    return [(start, headers[j+1][0] if j+1 < len(headers) else len(text), route) for j, (start, route) in enumerate(headers)]

def subtree(obj, route):
    for k in route:
        if not isinstance(obj, dict) or k not in obj:
            raise Failure('Module table not found: ' + '.'.join(route))
        obj = obj[k]
    if not isinstance(obj, dict):
        raise Failure('A module must be a TOML table: ' + '.'.join(route))
    return obj

def extract_module(data, route):
    doc = parsed(data)
    original = subtree(doc, route)
    text = data.decode('utf-8-sig')
    spans = [(a,b) for a,b,r in table_sections(text) if r[:len(route)] == route]
    if not spans:
        raise Failure('Module uses root dotted keys/inline tables. Convert it to an explicit [module] table first; no files changed.')
    snippet = ''.join(text[a:b] for a,b in spans)
    result = parsed(snippet.encode())
    if subtree(result, route) != original:
        raise Failure('Cannot losslessly extract this module layout; no files changed.')
    return snippet.encode()

def snippet_route(data):
    obj = parsed(data)
    text = data.decode('utf-8-sig')
    sections = table_sections(text)
    if not sections:
        raise Failure('Stored module must contain an explicit table')
    route = sections[0][2]
    # First header identifies the module. All later tables must be descendants.
    if any(r[:len(route)] != route for _,_,r in sections):
        raise Failure('Stored module contains unrelated tables')
    expected = {}
    target = expected
    for part in route[:-1]:
        target = target.setdefault(part, {})
    target[route[-1]] = subtree(obj, route)
    if obj != expected:
        raise Failure('Stored module contains unrelated root values')
    return route

def merge_module(active, snippet):
    route = snippet_route(snippet)
    doc = parsed(active)
    replacement = subtree(parsed(snippet), route)
    text = active.decode('utf-8-sig')
    spans = [(a,b) for a,b,r in table_sections(text) if r[:len(route)] == route]
    # Remove only the selected table and descendants. Validate the whole result.
    for a,b in reversed(spans):
        text = text[:a] + text[b:]
    text = text.rstrip('\r\n') + '\n\n' + snippet.decode('utf-8-sig')
    data = text.encode()
    result = parsed(data)
    # Work on a deep copy, preserving dates and nested arrays.
    import copy
    expected = copy.deepcopy(doc)
    target = expected
    for part in route[:-1]:
        value = target.setdefault(part, {})
        if not isinstance(value, dict):
            raise Failure('Module parent is not a table')
        target = value
    target[route[-1]] = replacement
    if result != expected:
        raise Failure('Module merge would change unrelated values; no files changed.')
    return data

class App:
    def __init__(self, args):
        self.args = args
        self.root = storage_root(path(os.environ.get('BLASTOFF_HOME') or str(Path.home() / '.config/blastoff')))
        self.themes = self.root / 'themes'
        self.modules = self.root / 'modules'
        self.backups = self.root / 'backups'
        self.configured_config = path(os.environ.get('STARSHIP_CONFIG') or str(Path.home() / '.config/starship.toml'))
        self._active = None
        self._report_views = {}
        self._dots_report = (args.command in ('current', 'doctor', 'list') or
                             (args.command, getattr(args, 'action', None)) in
                             (('theme', 'list'), ('theme', 'save'), ('backup', 'list')))
        self.color = not args.json and args.color != 'never' and 'NO_COLOR' not in os.environ and (args.color == 'always' or (sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'))
    def report(self, stream=None):
        if self.args.json or not self._dots_report:
            return None
        stream = sys.stdout if stream is None else stream
        if stream not in self._report_views:
            self._report_views[stream] = ui_module('reports').report(
                getattr(self.args, 'report_color', None), stream=stream)
        return self._report_views[stream]
    @property
    def config(self):
        if self._active is None:
            self._active = ui_module('active_config').ActiveConfig(core_api(), self.configured_config, self.args.replace_link)
        return self._active.target
    def check_active(self):
        target = self.config
        self._active.check(write=True)
        for directory in (self.themes, self.modules):
            if target.is_relative_to(directory):
                raise Failure('Active configuration is a stored library path; use a separate active config')
        return target
    def atomic_active(self, data, expected):
        self.check_active()
        atomic(self.config, data, expected, check=self.check_active)
    def diagnostic(self, message, level='debug'):
        if level == 'debug' and not self.args.verbose:
            return
        safe = ''.join(c if c.isprintable() else ascii(c)[1:-1] for c in str(message))
        if self.args.json:
            print(json.dumps({'level':level, 'message':safe}), file=sys.stderr)
        else:
            ui = self.report(sys.stderr)
            if ui:
                ui.text('blastoff: '+level+': '+safe,
                        level if level in ('warning', 'error') else 'muted')
            else:
                print('blastoff: '+level+': '+safe, file=sys.stderr)
    def accent(self, text, style):
        return '\x1b['+style+'m'+text+'\x1b[0m' if self.color else text
    def emit(self, result, message=None, *, styled_lines=None):
        if self.args.json:
            print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        elif styled_lines is not None:
            rows = []
            for tokens in styled_lines:
                pieces = []
                for text, role in tokens:
                    safe = ''.join(c if c.isprintable() else ascii(c)[1:-1] for c in text)
                    pieces.append(self.accent(safe, HUMAN_STYLES[role]) if role else safe)
                rows.append(''.join(pieces))
            print('\n'.join(rows))
        elif message is not None:
            message = ''.join(c if c.isprintable() or c == '\n' else ascii(c)[1:-1] for c in message)
            print(self.accent(message, PURPLE))
        else:
            raise RuntimeError('Missing human output renderer')
    def status(self, title, fields):
        print(self.accent(title, '1;'+PURPLE))
        width = max(len(label) for label, _ in fields)+2
        for label, value in fields:
            # Do not replay controls/bidi from configured paths or tool names.
            safe_value = ''.join(c if c.isprintable() else ascii(c)[1:-1] for c in value)
            print('  '+self.accent(label.ljust(width), PINK)+safe_value)
    def files(self, directory):
        if not directory.exists():
            return []
        candidates = []
        for p in directory.glob('*.toml'):
            try:
                name(p.stem)
            except Failure:
                continue
            if p.is_file() and not p.is_symlink():
                candidates.append(p)
        return sorted(candidates, key=lambda p:p.stem)
    def presets(self):
        if not shutil.which('starship'):
            raise Failure('starship is required for preset commands', 3)
        output = self.starship(['preset', '--list'])
        values = [line.strip() for line in output.splitlines() if line.strip()]
        try:
            for value in values:
                name(value)
        except Failure:
            raise Failure('starship returned an unusable preset list', 3)
        return sorted(set(values))
    def optional_presets(self):
        # Only optional discovery is softened; source reads, validation and
        # mutation failures must retain their normal failure behavior.
        try:
            return self.presets(), {'status':'ok', 'error':None}
        except Failure as e:
            return [], {'status':'unavailable', 'error':str(e)}
    def discovery_warning(self, discovery):
        if discovery['status'] == 'unavailable' and not self.args.json:
            self.diagnostic('presets unavailable: ' + discovery['error'], 'warning')
    def starship(self, args):
        try:
            proc = subprocess.run(['starship', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
        except FileNotFoundError:
            raise Failure('starship is required for preset commands', 3)
        except subprocess.TimeoutExpired:
            raise Failure('starship preset command timed out', 3)
        except OSError:
            raise Failure('starship could not be started', 3)
        if proc.returncode:
            raise Failure('starship preset failed (exit ' + str(proc.returncode) + ')', 3)
        if len(proc.stdout) > MAX_FILE:
            raise Failure('starship output exceeds 4 MiB', 3)
        try:
            return proc.stdout.decode('utf-8')
        except UnicodeError:
            raise Failure('starship output is not valid UTF-8', 3)
    def backup(self, source, kind):
        data = read(source, links=True)
        safe_parents(self.backups)
        ident = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:12]
        metadata = {'id':ident, 'kind':kind, 'source':str(source), 'sha256':hashlib.sha256(data).hexdigest(), 'symlink_target':os.readlink(source) if source.is_symlink() else None}
        if kind == 'config':
            metadata['configured_config'] = str(self.configured_config)
            metadata['resolved_config'] = str(self.config)
            metadata['active_links'] = [{'path': str(p), 'target': fp[-1]} for p, fp in self._active.links]
            metadata['provenance'] = self._backup_origin if hasattr(self, '_backup_origin') else ui_module('provenance').read_record(core_api(), self)[0]
        atomic(self.backups / (ident + '.toml'), data)
        atomic(self.backups / (ident + '.json'), (json.dumps(metadata, sort_keys=True)+'\n').encode())
        self.diagnostic('Created '+kind+' backup '+ident)
        return ident
    def active_write(self, data, *, expected=...):
        parsed(data)
        self.check_active()
        before = fingerprint(self.config)
        if expected is not ... and before != expected:
            raise Failure('Active config changed during operation; refusing overwrite')
        if exists(self.config):
            old = read(self.config, links=True)
            if not self.config.is_symlink() and old == data:
                return None
            backup = self.backup(self.config, 'config')
        else:
            backup = None
        self.atomic_active(data, before)
        return backup
    def stored_write(self, target, data, *, expected=...):
        parsed(data)
        if target.is_symlink():
            raise Failure('Refusing symlink destination: ' + str(target))
        before = fingerprint(target)
        if expected is not ... and before != expected:
            raise Failure('Destination changed during operation; refusing overwrite: '+str(target))
        if before is not None and not self.args.force:
            raise Failure('Destination exists; use --force to back it up and replace it: ' + str(target))
        backup = self.backup(target, 'stored') if before is not None else None
        atomic(target, data, before)
        return backup
    def source(self, value):
        if value.startswith('preset:'):
            n = name(value[7:])
            if n not in self.presets():
                raise Failure('Unknown preset: ' + n)
            data = self.starship(['preset', n]).encode()
            self.loaded_source = {'kind':'preset', 'name':n}
        else:
            n = name(value[6:] if value.startswith('local:') else value)
            p = self.themes / (n + '.toml')
            if not exists(p) and not value.startswith('local:'):
                return self.source('preset:' + n)
            before = fingerprint(p)
            data = read(p)
            if fingerprint(p) != before:
                raise Failure('Source changed during read')
            self.loaded_source = {'kind':'local', 'name':n, 'path':str(p), 'fingerprint':ui_module('provenance').serial(before)}
        self.loaded_source['sha256'] = hashlib.sha256(data).hexdigest()
        parsed(data)
        self.diagnostic('Validated source '+self.loaded_source['kind']+':'+n)
        return data
    def list(self):
        themes = [p.stem for p in self.files(self.themes)]
        presets, discovery = self.optional_presets()
        result = {'themes':themes, 'presets':presets, 'starship_available':bool(shutil.which('starship')), 'preset_discovery':discovery}
        self.discovery_warning(discovery)
        if self.args.json:
            self.emit(result)
        else:
            identity = ui_module('provenance').list_identity(core_api(), self)
            ui = self.report()
            if ui:
                ui_module('reports').themes(ui, result, identity)
                return result
            rows = []
            identified = False
            for title, values, kind in [('THEMES', themes, 'local'),('PRESETS', presets, 'preset')]:
                rows.append([(title, 'list_heading')])
                for n in values:
                    selected = identity['identity'] == (kind, n)
                    row = [('  ', None), (kind+':', 'prefix'), (n, 'selected' if selected else 'id')]
                    if selected:
                        row.append(('  ['+identity['marker']+']', 'selected'))
                        identified = True
                    rows.append(row)
                if not values:
                    rows.append([('  (unavailable)' if title == 'PRESETS' and discovery['status'] == 'unavailable' else '  (none)', None)])
            if identity['identity'] and not identified:
                kind, n = identity['identity']
                rows.append([('Origin: ', 'label'), (kind+':', 'prefix'), (n, 'selected'),
                             ('  ['+identity['marker']+'; not listed]', 'selected')])
            if identity['note']:
                rows.append([(identity['note'], None)])
            self.emit(result, styled_lines=rows)
        return result
    def current(self):
        data = read(self.config, links=True) if exists(self.config) else None
        matches = [p.stem for p in self.files(self.themes) if data is not None and read(p) == data]
        result = {'config':str(self.configured_config), 'resolved_config':str(self.config), 'exists':data is not None,
                  'matching_themes':matches, 'symlink':self.configured_config.is_symlink()}
        result['provenance'] = ui_module('provenance').status(core_api(), self, data)
        if self.args.json:
            self.emit(result)
            return
        ui = self.report()
        if ui:
            ui_module('reports').current(ui, result)
            return
        match_text = ', '.join(matches) if matches else '(no local match)' if data is not None else '(no active config)'
        file_type = 'symlink' if result['symlink'] else 'regular file' if data is not None else 'not found'
        self.status('Current configuration', [('MATCHES', match_text), ('CONFIG', str(self.configured_config)), ('TARGET', str(self.config)), ('FILE', file_type), ('LAST LOADED', result['provenance']['origin']), ('TRACKING', result['provenance']['status'])])
    def doctor(self):
        try:
            resolved = str(self.config)
        except (Failure, OSError):
            resolved = None
        result = {'version':VERSION, 'python':sys.version.split()[0], 'config':str(self.configured_config), 'resolved_config':resolved,
                  'blastoff_home':str(self.root), 'themes':str(self.themes), 'modules':str(self.modules),
                  'starship':shutil.which('starship'), 'fzf':shutil.which('fzf'), 'gum':shutil.which('gum'),
                  'config_exists':exists(self.configured_config), 'config_symlink':self.configured_config.is_symlink()}
        if self.args.json:
            self.emit(result)
            return
        ui = self.report()
        if ui:
            ui_module('reports').doctor(ui, result)
            return
        state = 'present' if result['config_exists'] else 'not found'
        if result['config_symlink']:
            state += ' (symlink)'
        self.status('Blastoff doctor', [
            ('VERSION', VERSION), ('PYTHON', result['python']),
            ('CONFIG', result['config']), ('TARGET', resolved or 'unavailable'), ('STATUS', state),
            ('STORAGE', result['blastoff_home']), ('THEMES', result['themes']), ('MODULES', result['modules']),
            ('STARSHIP', result['starship'] or 'not found (needed for presets)'),
            ('FZF', result['fzf'] or 'not found (optional)'), ('GUM', result['gum'] or 'not found (optional)'),
        ])
    def pick(self):
        if self.args.json or not sys.stdin.isatty() or not sys.stdout.isatty():
            raise Failure('Picker requires an interactive terminal and human output', 2)
        fzf = shutil.which('fzf')
        if self.args.fzf and not fzf:
            raise Failure('fzf is required for --fzf; install fzf or use ordinary pick for a fallback', 3)
        values = ['local:' + p.stem for p in self.files(self.themes)]
        presets, discovery = self.optional_presets()
        self.discovery_warning(discovery)
        values += ['preset:' + n for n in presets]
        if not values:
            raise Failure('No themes or presets available')
        # Ambient picker options can auto-accept, run previews/bindings, or start
        # a listener. This picker is deliberately names-only and user-confirmed.
        picker_env = {k:v for k,v in os.environ.items() if not k.startswith(('FZF_', 'GUM_'))}
        if fzf:
            selected = ui_module('picker_ui').choose_fzf(values, self.themes, self.color, os.environ, fancy=self.args.fancy, diagnostic=self.diagnostic, executable=fzf)
            if selected is None:
                raise Failure('Selection cancelled', 130)
            return selected
        elif shutil.which('gum'):
            self.diagnostic('fzf unavailable; using Gum fallback', 'warning')
            if not self.color:
                picker_env['NO_COLOR'] = '1'
            proc = subprocess.run(['gum', 'choose', '--header=BLASTOFF | Enter apply / Esc cancel\nlocal: stored | preset: Starship', '--cursor=> ', '--cursor-prefix=> ', '--selected-prefix=* ', '--unselected-prefix=  ', '--cursor.foreground=141', '--header.foreground=213', *values], text=True, stdout=subprocess.PIPE, env=picker_env)
        else:
            self.diagnostic('fzf unavailable; using numbered fallback', 'warning')
            self.emit({}, 'BLASTOFF | local: stored / preset: Starship')
            print('Number + Enter applies; empty cancels.')
            for i, value in enumerate(values, 1):
                print(f'{i:3}  {value}')
            # input()'s libc terminal path can defer SIGINT until another line
            # on native Termux. TextIO readline keeps cancellation responsive.
            print('Theme number (empty cancels): ', end='', flush=True)
            choice = sys.stdin.readline().strip()
            if not choice or '\x1b' in choice:
                raise Failure('Selection cancelled', 130)
            if not choice.isdigit() or not 1 <= int(choice) <= len(values):
                raise Failure('Invalid selection', 2)
            return values[int(choice)-1]
        selected = proc.stdout.strip()
        if proc.returncode or selected not in values:
            raise Failure('Selection cancelled', 130)
        return selected
    @contextlib.contextmanager
    def mutate(self):
        paths = [self.root / '.operation.lock']
        if self.args.command in {'apply','pick','restore','module-load','edit','active-save'}:
            paths.append(self.config.parent / ('.' + self.config.name + '.blastoff.lock'))
        with locks(paths):
            if self._active is not None:
                self._active.check()
                if self.args.command in {'apply','pick','restore','module-load','edit'}:
                    self.check_active()
            yield

def parser():
    return cli_module().parser(VERSION)

def backup_metadata(p):
    meta = json.loads(read(p))
    if not isinstance(meta, dict):
        raise Failure('Invalid backup metadata: expected a JSON object')
    return meta

normalize = cli_module().normalize

def run(argv, *, parsed_args=None):
    args = parsed_args if parsed_args is not None else cli_module().parse(argv, VERSION)
    if args.command is None:
        ui_module('welcome').render(VERSION, args.color, args.json); return 0
    cmd = args.command
    if cmd == 'completion':
        print((Path(__file__).resolve().parent.parent / 'completions' / ('blastoff.' + args.shell)).read_text(), end=''); return 0
    app = App(args)
    app.diagnostic('Storage: '+str(app.root)+'; active config: '+str(app.configured_config))
    if cmd == 'doctor':
        app.doctor(); return 0
    if cmd == 'list' or (cmd == 'theme' and args.action == 'list'):
        app.list(); return 0
    if cmd == 'current':
        app.current(); return 0
    if cmd == 'preset' and args.action == 'list':
        values = app.presets(); app.emit({'presets':values}, '\n'.join(values) or 'No presets available'); return 0
    if cmd == 'module' and args.action == 'list':
        values = [p.stem for p in app.files(app.modules)]; app.emit({'modules':values}, '\n'.join(values) or 'No saved modules'); return 0
    if cmd == 'backup' and args.action == 'list':
        return ui_module('backups').listing(core_api(), app)
    if cmd == 'module' and args.action == 'show':
        return ui_module('operations').show_module(core_api(), app)
    return ui_module('operations').run(core_api(), app)

def core_api():
    from types import SimpleNamespace
    return SimpleNamespace(**globals())

def human_error(message, code):
    args = _STARTUP_ARGS
    supported = args is not None and (args.command in ('current', 'doctor', 'list') or
        (args.command, getattr(args, 'action', None)) in
        (('theme', 'list'), ('theme', 'save'), ('active-save', 'save'), ('backup', 'list')))
    ui = ui_module('reports').report(getattr(args, 'report_color', None), stream=sys.stderr) if supported else None
    if ui:
        ui.text('blastoff: ' + str(message), 'muted' if code == 130 else 'error')
    else:
        print('blastoff: ' + str(message), file=sys.stderr)

def main():
    try:
        return run(sys.argv[1:], parsed_args=_STARTUP_ARGS)
    except Failure as e:
        if '--json' in sys.argv:
            print(json.dumps({'error':str(e), 'code':e.code}), file=sys.stderr)
        else:
            human_error(e, e.code)
        return e.code
    except BrokenPipeError:
        return 0
    except RuntimeError as e:
        if '--json' in sys.argv:
            print(json.dumps({'error':str(e), 'code':3}), file=sys.stderr)
        else:
            human_error(e, 3)
        return 3
    except (OSError, ValueError, UnicodeError) as e:
        if '--json' in sys.argv:
            print(json.dumps({'error':str(e), 'code':1}), file=sys.stderr)
        else:
            human_error(e, 1)
        return 1
    except (KeyboardInterrupt, EOFError):
        return 130
if __name__ == '__main__':
    raise SystemExit(main())
