"""Read-only resource presentation. No theme resolution, content reads or subprocesses."""
import fnmatch
import os
from pathlib import Path
import re
import stat
import unicodedata

LIMIT = 2 * 1024 * 1024
SGR = re.compile(r'[0-9;]{1,128}\Z')
CORE = dict(fi='file', di='dir', ln='symlink', or_='broken_symlink', mi='missing',
            ex='executable', pi='fifo', so='socket', bd='block_device', cd='character_device')
CORE['or'] = CORE.pop('or_')
DEFAULTS = dict(file='95', dir='1;94', symlink='96', broken_symlink='91',
                missing='95', executable='92', fifo='93', socket='95',
                block_device='93', character_device='93')


def clean(value):
    return ''.join(c if c.isprintable() or unicodedata.category(c) == 'Co'
                   else repr(c)[1:-1] for c in str(value))


def cells(value):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in value)


def wrap(value, width):
    """Wrap inert text, preserving every character, including spaces in paths."""
    part, used = '', 0
    for c in value:
        size = cells(c)
        if used + size > width and part:
            boundary = max(part.rfind('/'), part.rfind(' ')) + 1
            if boundary and cells(part[:boundary]) >= width // 2:
                yield part[:boundary]
                part = part[boundary:]
                used = cells(part)
            else:
                yield part
                part, used = '', 0
        part += c
        used += size
    yield part


def read_data(path):
    try:
        # Refuse FIFOs/devices and symlinked payloads; generation directories may be links.
        if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > LIMIT:
            return ''
        with path.open(encoding='utf-8') as stream:
            return stream.read(LIMIT + 1)
    except (OSError, UnicodeError):
        return ''


def suffix_rows(entries, group):
    """GNU suffix case-collision rules, shared with file-colors.py's matcher."""
    groups, ordered = {}, []
    for key, code in reversed(entries):
        entry = dict(key=key, code=code)
        groups.setdefault(key.lower(), []).append(entry)
        ordered.append(entry)
    for items in groups.values():
        for i, item in enumerate(items):
            if item.get('shadowed'):
                continue
            folded = False
            for older in items[i+1:]:
                if older.get('shadowed'):
                    continue
                if item['key'] == older['key'] or folded:
                    older['shadowed'] = True
                elif item['code'] == older['code']:
                    older['shadowed'], folded = True, True
                else:
                    item['exact'] = older['exact'] = True
    return [(group, e['key'], e['code'] or '0', 'exact' if e.get('exact') else 'fold')
            for e in ordered if not e.get('shadowed')]


def legacy_rows(text):
    types, suffixes = {}, []
    # Escaped legacy entries have no portable Bash fallback; ignore them safely.
    for item in text.strip().split(':'):
        key, sep, code = item.partition('=')
        if not sep or '\\' in key or '^' in key or not SGR.fullmatch(code):
            continue
        if key in CORE:
            types[CORE[key]] = code
        elif key.startswith('*'):
            suffixes.append((key[1:], code))
    return [('type', k, v, '-') for k, v in types.items()] + suffix_rows(suffixes, 'suffix')


class Resources:
    def __init__(self, root=None):
        state = os.environ.get('XDG_STATE_HOME')
        if not state and os.name == 'nt':
            state = os.environ.get('LOCALAPPDATA')
        self.root = Path(root or Path(state or Path.home() / '.local/state') / 'dots/current/theme')
        self._rows = None
        self._icons = None

    @property
    def rows(self):
        if self._rows is None:
            data = read_data(self.root / 'file-styles.tsv').splitlines()
            rows = []
            if data and data[0] == 'dots-file-styles\t1':
                for line in data[1:]:
                    parts = line.split('\t')
                    if (len(parts) != 4 or parts[0] not in ('type', 'extension', 'mime', 'suffix', 'default_mime')
                            or not parts[1] or not SGR.fullmatch(parts[2])
                            or parts[3] not in ('-', 'exact', 'fold')
                            or any(ord(c) < 32 or ord(c) == 127 for c in parts[1])):
                        rows = []
                        break
                    if parts[0] == 'type' and not re.fullmatch(r'[a-z][a-z0-9_]*', parts[1]):
                        rows = []
                        break
                    rows.append(tuple(parts))
            self._rows = rows or legacy_rows(read_data(self.root / 'ls_colors'))
        return self._rows

    @property
    def icons(self):
        if self._icons is None:
            self._icons = [tuple(line.split('\t')) for line in
                           read_data(Path(__file__).with_suffix('.tsv')).splitlines()
                           if not line.startswith('#') and len(line.split('\t')) == 4]
        return self._icons

    def describe(self, path, kind=None, mime=None, styled=True):
        p = Path(path)
        inferred_kind = not kind
        if not kind:
            try:
                mode = p.lstat().st_mode
                kind = ('broken_symlink' if not p.exists() else 'symlink') if stat.S_ISLNK(mode) else (
                    'dir' if stat.S_ISDIR(mode) else 'fifo' if stat.S_ISFIFO(mode) else
                    'socket' if stat.S_ISSOCK(mode) else 'block_device' if stat.S_ISBLK(mode) else
                    'character_device' if stat.S_ISCHR(mode) else 'executable' if mode & 0o111 else 'file')
            except OSError:
                kind = 'missing'
        rows = self.rows if styled else []
        types = {row[1]: row[2] for row in rows if row[0] == 'type'}
        if inferred_kind and types.get(kind) in ('0', '00'):
            if kind == 'executable':
                kind = 'file'
            elif kind == 'broken_symlink':
                kind = 'symlink'
        icon, guessed = '', ''
        for group, key, value, inferred in self.icons:
            if group == 'kind' and key == kind:
                icon = value
        # Missing/planned files can still be identified by their name.
        if kind in ('file', 'missing'):
            for group, key, value, inferred in self.icons:
                if group == 'name' and p.name == key or group == 'suffix' and p.name.lower().endswith(key.lower()):
                    icon, guessed = value, inferred
                    break
            mime = mime or guessed
            if mime and not guessed:
                for group, key, value, _ in self.icons:
                    if group == 'mime' and fnmatch.fnmatchcase(mime, key):
                        icon = value
                        break
        code = types.get(kind, DEFAULTS.get(kind, '95'))
        if kind in ('file', 'missing'):
            for group, key, value, case in rows:
                if group in ('extension', 'suffix'):
                    if (p.name if case == 'exact' else p.name.lower()).endswith(key if case == 'exact' else key.lower()):
                        code = value
                        break
                elif group in ('mime', 'default_mime') and mime and fnmatch.fnmatchcase(mime, key):
                    code = value
                    break
        return kind, icon or '󰈔', code
