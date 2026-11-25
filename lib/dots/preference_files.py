"""Unified application preferences and compatible split preference files.

The small literal TOML dialect also works on Python 3.9. The reserved [controls]
section stores canonical Config keys; { inherit = true } declares a nullable
control, and {} declares an extensible empty map. No expressions are evaluated.
"""
import copy
from functools import lru_cache
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
    return copy.deepcopy(_parsed(text(path)))


@lru_cache(maxsize=16)
def _parsed(raw):
    # A content key notices same-size edits, atomic replacements and newly created
    # inputs. Cached documents stay private so plans can freely edit their copies.
    def unique_fields(pairs):
        values = {}
        for key, value in pairs:
            if key in values and (type(values[key]) is not type(value) or values[key] != value):
                raise ValueError('conflicting duplicate preference field: ' + key)
            values[key] = value
        return values

    data = json.loads(raw, object_pairs_hook=unique_fields) if raw else {'schema': 1}
    schema = data.get('schema') if isinstance(data, dict) else None
    groups = GROUPS if schema == 1 else ('settings', 'apps', 'colors', 'icons')
    if type(schema) is not int or schema not in (1, 2) or set(data)-{'schema', *groups}:
        raise ValueError('invalid preference document')
    if any(not isinstance(data.get(g, {}), dict) for g in groups):
        raise ValueError('preference groups must be objects')
    return data


def unified_document(typed, styles):
    """Encode one layer. Reject conflicting owners before returning a document."""
    from config_keys import document, public_styles
    from config_namespace import app_field
    from config_values import leaves, name, parts
    from style_catalog import canonical as icon_role, split
    result = {'schema': 2}

    def place(path, value):
        node = result
        for part in path[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise ValueError('overlapping preference keys: ' + name(path))
        key = path[-1]
        if key in node and (type(node[key]) is not type(value) or node[key] != value):
            raise ValueError('conflicting configuration aliases: ' + name(path))
        node[key] = copy.deepcopy(value)

    public = document({g: typed[g] for g in GROUPS if typed.get(g)}, strict=True)
    for path, value in leaves(public):
        if not path:
            continue
        if path[0] == 'settings':
            place(path, value)
        else:
            field = app_field(name(path))
            if not field:
                if value == {} and path[0] in ('apps', 'formatting'):
                    continue
                raise ValueError('unknown typed preference owner: ' + name(path))
            app, kind, tail = field
            place(('apps', app, kind, *tail), value)
    for group in ('colors', 'icons'):
        for key, value in public_styles(group, styles.get(group, {}), strict=True).items():
            app, role = split(key)
            relative = parts(icon_role(role) if group == 'icons' else role)
            if app and typed_style(app, group, relative):
                raise ValueError('semantic style overlaps a native control: ' + group + '.' + key)
            place(('apps', app, group, *relative) if app else (group, *relative), value)
    return result


def typed_style(app, group, tail):
    """Native map fields and semantic roles can share an app's colors or icons."""
    if app == 'nvim':
        return group == 'icons' or group == 'colors' and tail[:1] in (('highlights',), ('icon_styles',))
    if group != 'colors':
        return False
    if app == 'fzf':
        return len(tail) <= 1
    if app == 'menu':
        from config_keys import MOVES
        from config_values import name
        return tail[:1] == ('entries',) or (tail[:1] == ('popup',) and
            any(public == name(('colors', 'apps', app, *tail)) for _, public in MOVES))
    return False


def unified_values(document):
    """Decode schema 2 into existing typed values and literal flat style maps."""
    from config_keys import document as translate, MOVES
    from config_namespace import NATIVE_GROUPS
    from config_values import leaves, name, parts, lookup, MISSING
    typed = {'schema': 1}
    styles = {'colors': {}, 'icons': {}}
    if not isinstance(document, dict) or type(document.get('schema')) is not int or document.get('schema') != 2:
        raise ValueError('expected preference schema 2')
    if set(document) - {'schema', 'settings', 'apps', *styles}:
        raise ValueError('unknown unified preference group')
    if any(not isinstance(value, dict) for key,value in document.items() if key != 'schema'):
        raise ValueError('preference groups must be objects')
    if document.get('settings'):
        typed['settings'] = copy.deepcopy(document['settings'])
    for group in styles:
        if 'apps' in document.get(group, {}):
            raise ValueError('application preferences belong under apps: ' + group)
        for path, value in leaves(document.get(group, {})):
            if path:
                styles[group][name(path)] = value
    for app, groups in document.get('apps', {}).items():
        if not isinstance(groups, dict) or set(groups) - {'settings', 'formatting', *styles}:
            raise ValueError('unknown application preference group: ' + app)
        for group, values in groups.items():
            if not isinstance(values, dict):
                raise ValueError('application preference groups must be objects: ' + app)
            if group in ('settings', 'formatting'):
                if values:
                    if group == 'settings':
                        reserved = {'settings','formatting','colors','icons'} | {k for a,k in NATIVE_GROUPS if a == app}
                        if reserved & values.keys():
                            raise ValueError('preference belongs to another application group: ' + app)
                    prefix = ('apps', app) if group == 'settings' else ('formatting', 'apps', app)
                    for old, _ in MOVES:
                        path = parts(old)
                        if path[:len(prefix)] == prefix and lookup(values, path[len(prefix):], MISSING) is not MISSING:
                            raise ValueError('preference belongs to another application group: ' + old)
                    node = typed
                    for part in prefix:
                        node = node.setdefault(part, {})
                    node.update(copy.deepcopy(values))
                continue
            for tail, value in leaves(values):
                if typed_style(app, group, tail):
                    if app == 'menu':
                        path = ('colors', 'apps', app, *tail)
                    elif app == 'nvim' and group == 'colors':
                        path = ('apps', app, *tail)
                    else:
                        path = ('apps', app, group, *tail)
                    put(typed, name(path), value)
                elif tail:
                    styles[group][name(('apps', app, *tail))] = value
    return translate(typed, public=False, strict=True), styles


@lru_cache(maxsize=16)
def _decoded(raw):
    return unified_values(_parsed(raw))


def _layer(directory, replacements):
    path = directory/'config.json'
    if path in replacements:
        data = replacements[path]
        return (data, unified_values(data) if data.get('schema') == 2 else None)
    raw = text(path)
    data = _parsed(raw)
    return data, _decoded(raw) if data['schema'] == 2 else None


def legacy_inputs(directory):
    if any((directory/f).exists() or (directory/f).is_symlink() for f in FILES[1:]):
        return True
    manifest = text(directory/'profile.json')
    profile = json.loads(manifest) if manifest else {}
    return any(profile.get(group) for group in GROUPS)


def uses_unified(directory, root):
    directory = Path(directory)
    path = directory/'config.json'
    if path.exists() or path.is_symlink():
        return _parsed(text(path))['schema'] == 2
    if directory == Path(root)/'default' or legacy_inputs(directory):
        return False
    return _parsed(text(Path(root)/'default'/'config.json'))['schema'] == 2


def preference_path(directory, key, root):
    directory = Path(directory)
    if uses_unified(directory, root):
        return directory/'config.json'
    if key == 'icons' or key.startswith('icons.'):
        return directory/'icons.toml'
    return directory/appearance_file(key)


def style_layers(directory, group, replacements=None):
    from style_config import read
    directory = Path(directory)
    replacements = replacements or {}
    path = directory/'config.json'
    _, decoded = _layer(directory, replacements)
    if decoded is not None:
        return [(path, dict(decoded[1][group]))]
    path = directory/(group+'.toml')
    return [(path, replacements[path] if path in replacements else read(path))]


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


def setting_layers(directory, legacy=None):
    """Shell settings live only in the manifest and JSON owner at each layer."""
    directory = Path(directory)
    path = directory/'config.json'
    data = _parsed(text(path))
    if data['schema'] == 1 and legacy is not None:
        yield directory/'profile.json', legacy.get('settings', {})
    yield path, data.get('settings', {})


def layers(directory, legacy=None, replacements=None):
    from config_keys import document
    directory = Path(directory); replacements = replacements or {}
    result = []
    if legacy is not None:
        path = directory/'profile.json'
        data = replacements.get(path, legacy)
        result.append((path, document({g: data[g] for g in GROUPS if g in data}, public=False)))
    path = directory/'config.json'
    data, decoded = _layer(directory, replacements)
    if decoded is not None:
        inputs = [(directory/'profile.json', {})] if legacy is not None else []
        return [*inputs, (path, copy.deepcopy(decoded[0]))]
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


def unified_operation(path, data, *, sparse=False):
    # Store's literal text operation selects UTF-8 on every platform.
    # Keep the schema marker when deleting it would reactivate legacy overrides.
    if sparse and data == {'schema': 2} and not legacy_inputs(Path(path).parent):
        return dict(path=str(path), delete=True)
    return dict(path=str(path), text=json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def clear_current():
    from config_values import current as controls
    from style_config import current as styles
    styles.cache_clear()
    controls.cache_clear()


def preference_guards(root, selected, defaults=False):
    from files.transactions import digest, parents_safe
    paths = [Path(root)/'default'/name for name in FILES]
    if not defaults:
        for layer in selected['layers']:
            paths.extend(Path(layer['root'])/name for name in (*FILES, 'profile.json'))
    guards = {}
    for path in paths:
        parents_safe(path)
        guards[str(path)] = digest(path)
    return guards


class PreferencePlan:
    """One retained Store transaction for a scope's preference files."""
    def __init__(self, root, selected, defaults=False):
        from config_values import Controls
        self.root = Path(root); self.selected = selected; self.defaults = defaults
        self.directory = self.root/'default' if defaults else Path(selected['layers'][-1]['root'])
        self.path = self.directory/'config.json'
        self.guards = preference_guards(root, selected, defaults)
        self.controls = Controls(root, selected, defaults=defaults)
        self.legacy = None if defaults else json.loads(text(self.directory/'profile.json'))
        self.unified = uses_unified(self.directory, root)
        self.style_values = {group: {} for group in ('icons', 'colors')}
        if self.unified and self.path.is_file():
            self.style_values = unified_values(json_document(self.path))[1]
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
        if self.unified:
            path = self.directory/'config.json'
            data = unified_document(self.data, self.style_values)
            self.replacements = {path: data}
            self.operations = []
            previous = json_document(path) if path.exists() else {'schema': 2}
            if data != previous:
                self.operations.append(unified_operation(path, data, sparse=not self.defaults))
            return
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
        result = Store(state_root()).apply('config-'+action, self.operations, self.guards,
                                           retain=True, catalogs=list(self.replacements))
        if self.operations:
            clear_current()
        return result


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
        if compact(self.data)==compact(self.before):
            self.operations, self.replacements = [], {}
            return
        self.finish()
