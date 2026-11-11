"""Separated preference files and portable typed appearance declarations.

The small literal TOML dialect also works on Python 3.9. The reserved [controls]
section stores canonical Config keys; { inherit = true } declares a nullable
control, and {} declares an extensible empty map. No expressions are evaluated.
"""
import copy
import json
from pathlib import Path
import re

GROUPS = ('settings', 'apps', 'formatting', 'colors')
FILES = ('config.json', 'colors.toml', 'icons.toml')
LIMIT = 2 * 1024 * 1024


def text(path):
    path = Path(path)
    if not path.exists() and not path.is_symlink(): return ''
    if path.is_symlink() or not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('preferences require a bounded regular file: ' + str(path))
    return path.read_text(encoding='utf-8-sig')


def json_document(path):
    raw = text(path)
    data = json.loads(raw) if raw else {'schema': 1}
    if not isinstance(data, dict) or data.get('schema') != 1 or set(data)-{'schema', *GROUPS}:
        raise ValueError('invalid preference document: ' + str(path))
    if any(not isinstance(data.get(g, {}), dict) for g in GROUPS):
        raise ValueError('preference groups must be objects')
    return data


def style_sections(raw):
    ordinary = []; rows = []; inside = False; seen = False
    for line in raw.splitlines(keepends=True):
        if re.fullmatch(r'\s*\[controls\]\s*(?:#.*)?\n?', line):
            if seen: raise ValueError('duplicate controls table')
            seen = inside = True
            continue
        if line.lstrip().startswith('['): inside = False
        (rows if inside else ordinary).append(line)
    return ''.join(ordinary), ''.join(rows)


def controls(path):
    from config_values import parts
    result = {}
    _, raw = style_sections(text(path))
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        try: key, end = json.JSONDecoder().raw_decode(line)
        except ValueError: raise ValueError('typed style keys must be quoted: ' + str(path)) from None
        if not isinstance(key, str) or not line[end:].lstrip().startswith('='):
            raise ValueError('invalid typed style declaration: ' + str(path))
        parts(key)
        raw_value = line[end:].lstrip()[1:].strip()
        if raw_value == '{ inherit = true }': value = None
        else:
            try: value, end = json.JSONDecoder().raw_decode(raw_value)
            except ValueError: raise ValueError('expected a literal typed style value: ' + str(path)) from None
            if raw_value[end:].strip() and not raw_value[end:].lstrip().startswith('#'):
                raise ValueError('unexpected typed style value suffix')
            if type(value) not in (str, bool, int, dict) or isinstance(value, dict) and value:
                raise ValueError('typed style declarations must be scalar or empty maps')
        if key in result: raise ValueError('duplicate typed style key: ' + key)
        if appearance_file(key) != Path(path).name:
            raise ValueError('typed appearance key belongs in another preference file: ' + key)
        result[key] = value
    return result


def appearance_file(key):
    from config_keys import canonical
    from config_values import parts
    path=parts(canonical(key)) if key else ()
    if path[:3]==('apps','nvim','icons'):return 'icons.toml'
    if path[:1]==('colors',) or path[:3] in (('apps','fzf','colors'),('apps','nvim','highlights'),('apps','nvim','icon_styles')):
        return 'colors.toml'
    return 'config.json'


def put(doc, key, value):
    from config_values import parts
    node = doc
    for part in parts(key)[:-1]:
        if part in node and not isinstance(node[part], dict): raise ValueError('overlapping preference keys')
        node = node.setdefault(part, {})
    node[parts(key)[-1]] = copy.deepcopy(value)


def overlay(base, other):
    """Declaration merge retaining nulls (unlike effective-value inheritance)."""
    result = copy.deepcopy(base)
    for key, value in other.items():
        result[key] = overlay(result.get(key, {}) if isinstance(result.get(key), dict) else {}, value) if isinstance(value, dict) else copy.deepcopy(value)
    return result


def layers(directory, legacy=None, replacements=None):
    from config_keys import document
    directory = Path(directory); replacements = replacements or {}
    result = []
    if legacy is not None:
        path = directory/'profile.json'
        data = replacements.get(path, legacy)
        result.append((path, document({g: data[g] for g in GROUPS if g in data}, public=False)))
    path = directory/'config.json'
    data = replacements.get(path)
    if data is None: data = json_document(path)
    data = document(data, public=False)
    if data.get('colors'): raise ValueError('unrecognized typed colors in configuration')
    result.append((path, data))
    for filename in ('colors.toml','icons.toml'):
        path = directory/filename
        values = replacements.get(path)
        # Replacements are complete typed preference documents; Styles uses its
        # own flat replacement map independently.
        if values is None:
            values = {}
            for key, value in controls(path).items(): put(values, key, value)
        result.append((path, document(values, public=False)))
    return result


def combined(directory, legacy=None, replacements=None):
    result = {'schema': 1}
    for _, layer in layers(directory, legacy, replacements):
        result = overlay(result, {g: layer[g] for g in GROUPS if g in layer})
    return result


def partition(data):
    from config_keys import document
    from config_values import leaves, name
    result = {'config.json': {'schema': 1}, 'colors.toml': {}, 'icons.toml': {}}
    public = document({g: data[g] for g in GROUPS if g in data})
    for path, value in leaves(public):
        if not path: continue
        key = name(path); filename = appearance_file(key)
        if filename == 'config.json': put(result[filename], key, value)
        else: result[filename][key] = value
    return result


def encode_controls(values):
    if not values: return ''
    return '\n[controls]\n' + ''.join(json.dumps(k, ensure_ascii=False) + ' = ' +
        ('{ inherit = true }' if v is None else json.dumps(v, ensure_ascii=False)) + '\n' for k, v in sorted(values.items()))


def encode_style(path, values, ordinary=None):
    if ordinary is None: ordinary = style_sections(text(path))[0]
    return ordinary.rstrip() + '\n' + encode_controls(values)


def compact(value):
    if not isinstance(value,dict):return value
    result={}
    for key,child in value.items():
        cleaned=compact(child)
        if cleaned!={} or not isinstance(child,dict):result[key]=cleaned
    return result


class PreferencePlan:
    """One retained Store transaction for a scope's preference files."""
    def __init__(self, root, selected, defaults=False):
        from files.transactions import digest, parents_safe
        from config_values import Controls
        self.root = Path(root); self.selected = selected; self.defaults = defaults
        self.directory = self.root/'default' if defaults else Path(selected['layers'][-1]['root'])
        self.path = self.directory/'config.json'
        self.controls = Controls(root, selected, defaults=defaults)
        self.guards = {}
        for path in self.controls.paths:
            parents_safe(path); self.guards[str(path)] = digest(path)
        self.legacy = None if defaults else json.loads(text(self.directory/'profile.json'))
        self.before = combined(self.directory, self.legacy)
        self.data = copy.deepcopy(self.before)
        self.items = []; self.operations = []; self.replacements = {}

    def check(self):
        from files.transactions import digest
        for path,before in self.guards.items():
            if digest(Path(path))!=before:raise ValueError('configuration changed during preview')

    def finish(self):
        self.check()
        from config_keys import document
        if not self.defaults:
            self.data=compact(self.data)
        pieces = partition(self.data)
        self.operations = []; self.replacements = {}
        # Publish separated declarations before removing their legacy copies.
        for filename in ('colors.toml','icons.toml','config.json'):
            data=pieces[filename]
            path = self.directory/filename
            if filename.endswith('.json'):
                self.replacements[path] = document(data, public=False)
                if data != json_document(path): self.operations.append(dict(path=str(path), data=data))
            else:
                typed = {}
                for key, value in data.items(): put(typed, key, value)
                self.replacements[path] = document(typed, public=False)
                if data != controls(path): self.operations.append(dict(path=str(path), text=encode_style(path,data)))
        if self.legacy is not None:
            clean = {k:v for k,v in self.legacy.items() if k not in GROUPS}
            self.replacements[self.directory/'profile.json'] = clean
            if clean != self.legacy: self.operations.append(dict(path=str(self.directory/'profile.json'),data=clean))

    def apply(self, action):
        from files.transactions import Store
        from files.file_platform import state_root
        return Store(state_root()).apply('config-'+action, self.operations, self.guards,
                                         retain=True, catalogs=list(self.replacements))


class SettingsPlan(PreferencePlan):
    def edit(self, key, value=None, unset=False, json_value=False):
        from profile_config import validate_settings
        self.check()
        name = key[9:] if key.startswith('settings.') else key
        if not unset:
            if json_value: value = json.loads(value)
            elif name=='files.backup' and isinstance(value,str):
                if value not in ('true','false'):raise ValueError('files.backup requires true or false')
                value=value=='true'
            validate_settings({name:value})
        values = self.data.setdefault('settings', {})
        if unset: values.pop(name,None)
        else: values[name] = value
        self.items.append(dict(action='unset' if unset else 'set',key='settings.'+name))
        if compact(self.data)==compact(self.before):return
        self.finish()
