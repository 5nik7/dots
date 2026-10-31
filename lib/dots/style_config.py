"""Literal visual preferences. Reads only selected inputs; never publishes state."""
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import stat

from profile_config import checkout, context
from style_catalog import canonical, split, ALIASES as ICON_ALIASES

APPS = ('cli', 'tmux', 'yazi', 'fzf', 'gum', 'starship', 'gitmux', 'nvim')
LIMIT = 2 * 1024 * 1024
NAME = re.compile(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\Z')
ATTRS = dict(bold=1, dim=2, italic=3, underline=4, reverse=7, strikethrough=9)
ANSI = dict(black=30, red=31, green=32, yellow=33, blue=34, magenta=35, cyan=36,
            foreground=39, background=49, muted=90, bright_black=90, bright_red=91,
            bright_green=92, bright_yellow=93, bright_blue=94, bright_magenta=95,
            bright_cyan=96, bright_foreground=97, white=37)
ALIASES = dict(accent='blue', info='blue', success='green', warning='yellow', error='red',
               hint='cyan', orange='yellow', brown='yellow', selection='blue',
               selection_background='blue', selection_foreground='foreground', cursor='foreground',
               dark_background='background', darker_background='background', light_background='background',
               lighter_background='background', bright_background='background', dark_foreground='foreground', light_foreground='foreground')
ROLES = {'90':'ui.muted', '91':'status.error', '92':'status.success', '93':'status.warning',
         '94':'ui.label', '95':'ui.accent', '96':'ui.heading', '97':'ui.foreground',
         '31':'status.error', '32':'status.success', '33':'status.warning', '34':'ui.label',
         '35':'ui.accent', '36':'ui.heading', '37':'ui.foreground'}


def flatten(data, prefix=''):
    result = {}
    for key, value in data.items():
        name = prefix + '.' + key if prefix else key
        if isinstance(value, dict): result.update(flatten(value, name))
        else: result[name] = value
    return result


def nested(values):
    result = {}
    for name, value in values.items():
        parts = name.split('.'); node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node,dict): raise ValueError('overlapping style keys')
        if isinstance(node.get(parts[-1]), dict): raise ValueError('overlapping style keys')
        node[parts[-1]] = value
    return result


def read(path):
    """Portable TOML subset: named tables, quoted strings, booleans and comments."""
    if not path.exists() and not path.is_symlink(): return {}
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > LIMIT:
        raise ValueError('style configuration must be a bounded regular file: ' + str(path))
    values, section = {}, ''
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        table = re.fullmatch(r'\[([a-z][a-z0-9_.]*)\]\s*(?:#.*)?', line)
        if table:
            section = table[1]
            if not NAME.fullmatch(section): raise ValueError('invalid style table: ' + str(path))
            continue
        pair = re.fullmatch(r'([a-z][a-z0-9_]*)\s*=\s*("(?:[^"\\]|\\.)*"|\x27[^\x27]*\x27|true|false)\s*(?:#.*)?', line)
        if not pair: raise ValueError('expected a literal style option: ' + str(path))
        name = section + '.' + pair[1] if section else pair[1]
        if name in values: raise ValueError('duplicate style option: ' + name)
        raw = pair[2]
        values[name] = raw[1:-1] if raw.startswith("'") else json.loads(raw)
    return values


def encode(values):
    tables = {}
    for key, value in sorted(values.items()):
        table, _, name = key.rpartition('.')
        tables.setdefault(table, []).append(name + ' = ' + json.dumps(value, ensure_ascii=False))
    return '\n\n'.join(('['+table+']\n' if table else '') + '\n'.join(rows)
                       for table, rows in tables.items()) + '\n'


def validate(group, values):
    for key, value in values.items():
        if not NAME.fullmatch(key): raise ValueError('invalid style option name')
        if key.startswith('apps.') and (len(key.split('.')) < 4 or key.split('.')[1] not in APPS):
            raise ValueError('unknown visual consumer: ' + key)
        if group == 'icons':
            if not isinstance(value, str) or len(value) > 64 or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
                raise ValueError('icons require short printable literal strings: ' + key)
        elif group == 'colors':
            field = key.rsplit('.', 1)[-1]
            if field in ATTRS:
                if type(value) is not bool: raise ValueError('style attributes require booleans: ' + key)
            elif field not in ('fg','bg') or not isinstance(value, str) or not (
                    value in ANSI or value in ALIASES or value in ('reset','default') or re.fullmatch('#[a-fA-F0-9]{6}', value)):
                raise ValueError('colors require a palette role or #RRGGBB: ' + key)
        else: raise ValueError('unknown style group')


class Styles:
    def __init__(self, root=None, selected=None, *, defaults=False, replacements=None, palette=None):
        self.root = checkout(root)
        self.selected = selected if selected is not None else context(self.root)
        self.defaults = defaults
        self.values, self.sources, self.paths, self.layers = {}, {}, [], {}
        self._palette = palette
        self._codes = {}
        replacements = replacements or {}
        for group in ('icons','colors'):
            paths = [self.root/'default'/(group+'.toml')]
            if not defaults: paths += [Path(layer['root'])/(group+'.toml') for layer in self.selected['layers']]
            values, sources, layers = {}, {}, []
            for path in paths:
                self.paths.append(path)
                doc = replacements.get(path)
                if doc is None: doc = read(path)
                validate(group, doc)
                values.update(doc); sources.update({key:str(path) for key in doc})
                layers.append((str(path), doc))
            nested(values)
            self.values[group], self.sources[group] = values, sources
            self.layers[group] = layers

    def path(self, group):
        if group not in ('icons','colors'): raise ValueError('unknown style group')
        if self.defaults: return self.root/'default'/(group+'.toml')
        if not self.selected['layers']: raise ValueError('no profile definition in this checkout')
        return Path(self.selected['layers'][-1]['root'])/(group+'.toml')

    def resolve(self, group, name, app=None):
        """Fold general then app-specific values inside each inheritance layer."""
        embedded, name = split(name)
        app = embedded or app
        canonical_name = canonical(name) if group == 'icons' else name
        names = [k for k, v in ICON_ALIASES.items() if v == canonical_name] if group == 'icons' else []
        names.append(canonical_name)
        declarations = []
        for path, values in self.layers[group]:
            for prefix in ('', 'apps.'+app+'.') if app else ('',):
                for key in names:
                    if prefix+key in values:
                        declarations.append(dict(key=group+'.'+prefix+key, value=values[prefix+key], source=path))
        winner = declarations[-1] if declarations else {}
        return dict(value=winner.get('value'), source=winner.get('source'), declarations=declarations)

    def icon(self, name, fallback='', app=None):
        result = self.resolve('icons', name, app)
        return result['value'] if result['source'] else fallback

    @property
    def palette(self):
        if self._palette is None:
            from files.file_platform import state_root
            path = state_root()/'current/theme/palette.json'
            self._palette = {}
            try:
                if stat.S_ISREG(path.lstat().st_mode) and path.stat().st_size <= LIMIT:
                    self._palette = json.loads(path.read_text()).get('colors', {})
            except (OSError, ValueError, AttributeError): pass
        return self._palette

    def color(self, value):
        resolved = self.palette.get(value, self.palette.get(ALIASES.get(value), value))
        return resolved if isinstance(resolved, str) and re.fullmatch('#[a-fA-F0-9]{6}', resolved) else value

    def sgr_color(self, value, background=False):
        value = self.color(value)
        if value.startswith('#'):
            return ('48' if background else '38')+';2;'+';'.join(str(int(value[i:i+2],16)) for i in (1,3,5))
        if value in ('reset','default'): return '49' if background else '39'
        code = ANSI.get(ALIASES.get(value, value), 39)
        if background: code = code+10 if code != 49 else 49
        elif code == 49: code = 39
        return str(code)

    def style(self, name, fallback=None, app=None):
        result = dict(fallback or {})
        for field in ('fg', 'bg', *ATTRS):
            resolved = self.resolve('colors', name+'.'+field, app)
            if resolved['source']: result[field] = resolved['value']
        return result

    def sgr(self, name, fallback=None, app=None):
        doc = self.style(name, fallback, app)
        return self.sgr_fields(doc)

    def sgr_fields(self,doc):
        result = [str(code) for key,code in ATTRS.items() if doc.get(key)]
        for key in ('fg','bg'):
            if key in doc: result.append(self.sgr_color(doc[key], key=='bg'))
        return ';'.join(result) or '0'

    def code(self, code):
        """Adapt legacy semantic ANSI tokens; leave exact palette swatches alone."""
        if code in self._codes: return self._codes[code]
        parts = str(code).split(';')
        roles = [p for p in parts if p in ROLES]
        if len(roles) != 1 or any(p not in ROLES and p not in ('1','2','3','4','7','9') for p in parts): return code
        fallback = {key: True for key,value in ATTRS.items() if str(value) in parts}
        result = self.sgr(ROLES[roles[0]], dict(fallback, fg=next((k for k,v in ANSI.items() if str(v)==roles[0]), 'foreground')), app='cli')
        self._codes[code] = result
        return result

    def rows(self):
        for key in self.values['icons']:
            if not key.startswith('apps.'): yield '__icon.'+key, self.icon(key, app='cli'), 'style'
        for code in ROLES: yield '__color.'+code, self.code(code), 'style'

    def startup_inputs(self):
        from files.file_platform import state_root
        paths = {Path(__file__), Path(__file__).with_name('style_catalog.py')}
        palette = state_root()/'current/theme/palette.json'
        if palette.is_file(): paths.add(palette)
        for path in self.paths:
            if path.exists(): paths.add(path)
            if path.parent.is_dir(): paths.add(path.parent)
        return paths


@lru_cache(maxsize=1)
def _current(root,identity,state):
    try: return Styles(root,context(root,identity or None))
    except (OSError, ValueError, KeyError, TypeError): return None


def current():
    from files.file_platform import state_root
    return _current(str(checkout()),os.environ.get('DOTS_PROFILE',''),str(state_root()))


current.cache_clear=_current.cache_clear


def icon(name, fallback='', app=None):
    style = current()
    return style.icon(name, fallback, app or 'cli') if style else fallback


def code(value):
    style = current()
    return style.code(value) if style else value
