"""Literal profile configuration shared by commands, catalogs and native adapters."""
import json
import os
from pathlib import Path
import re
import sys

LIB = Path(__file__).resolve().parent
SETTING_PATTERNS = {'bool': r'[01]', 'style': r'auto|always|never',
                    'suggestions': r'deja|autosuggestions|none',
                    'id': r'[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*'}


def checkout(root=None):
    return Path(root or os.environ.get('DOTS') or LIB.parents[1]).resolve()


def schema():
    return {key: (kind, default, description) for key, kind, default, description in
            (line.split('\t', 3) for line in (LIB / 'shell/settings.tsv').read_text().splitlines())}


def validate_settings(values):
    if not isinstance(values, dict):
        raise ValueError('profile settings must be an object')
    kinds = schema()
    for key, value in values.items():
        if key == 'files.backup':
            if type(value) is not bool: raise ValueError('files.backup must be a boolean')
        elif key not in kinds or not isinstance(value, str) or not re.fullmatch(SETTING_PATTERNS[kinds[key][0]], value):
            raise ValueError('invalid Dots setting: ' + key)


def context(root=None, identity=None):
    from profiles import resolve
    if identity is not None:
        from profile_views import selected
        return selected(checkout(root), identity)
    return resolve(checkout(root))


def legacy_directory():
    from files.file_platform import config_root
    return config_root() / 'dots'


def directory(root=None, identity=None):
    selected = context(root, identity)
    return Path(selected['layers'][-1]['root']) if selected['layers'] else legacy_directory()


def config_path(name, root=None, *, write=False):
    """Resolve the most specific existing input; never relocate themes or state."""
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('invalid configuration name')
    if relative.parts[0] == 'themes':
        return legacy_directory() / relative
    selected = context(root)
    if write and selected['layers']:
        return Path(selected['layers'][-1]['root']) / relative
    for layer in reversed(selected['layers']):
        path = Path(layer['root']) / relative
        if path.exists() or path.is_symlink(): return path
    return legacy_directory() / relative


def settings(root=None, selected=None):
    result = {}
    for layer in (selected or context(root))['layers']:
        result.update({key: dict(value=value, source='profile:' + layer['id'])
                       for key, value in layer.get('settings', {}).items()})
    return result


def read_env(path):
    """Compatibility settings input; no shell evaluation and no value diagnostics."""
    values = {}
    if not path.exists(): return values
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        key, sep, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not sep or key in values: raise ValueError('invalid or repeated Dots setting')
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]: value = value[1:-1]
        values[key] = value
    validate_settings(values)
    return values


def keys(root=None, identity=None):
    result = set(schema()) | {'settings.files.backup', 'profile.alias'}
    selected = context(root, identity or None)
    for layer in selected['layers']:
        for group in ('settings', 'environment', 'files'):
            result.update(group + '.' + key for key in layer.get(group, {}))
    from style_config import Styles, APPS
    for group, values in Styles(root, selected).values.items():
        result.add(group)
        for key in [*values, *['apps.'+app+'.'+key for app in APPS for key in values if not key.startswith('apps.')]]:
            parts = key.split(".")
            result.update(group + "." + ".".join(parts[:i]) for i in range(1,len(parts)+1))
    return sorted(result)


def main(args):
    if args and args[0] == '__keys':
        for key in keys(identity=args[1] if len(args) > 1 else None): print(key)
        return
    if args == ['__settings']:
        selected = context()
        print('__path\t' + str(directory()) + '\tprofile')
        for key, row in settings(selected=selected).items():
            if key != 'files.backup': print(key + '\t' + row['value'] + '\t' + row['source'])
        from style_config import Styles
        for row in Styles(selected=selected).rows(): print('\t'.join(row))
    elif args == ['__style-inputs']:
        from style_config import Styles
        for path in [*Styles().paths, LIB/'style_config.py', LIB/'theme_styles.py', LIB/'resources.tsv', checkout()/'config/gitmux/gitmux.conf']:
            if path.is_file(): print(path)
    elif len(args) >= 2 and args[0] == '__paths':
        for name in args[1:]: print(config_path(name))
    elif len(args) == 2 and args[0] == '__path':
        print(config_path(args[1]))
    elif args == ['__settings-json']:
        selected = context()
        path = Path(selected['layers'][-1]['root']) / 'profile.json' if selected['layers'] else legacy_directory() / 'config.env'
        print(json.dumps(dict(settings=settings(selected=selected), path=str(path)), ensure_ascii=True))
    else:
        raise ValueError('invalid internal configuration query')


if __name__ == '__main__':
    try: main(sys.argv[1:])
    except (OSError, ValueError) as error:
        print('dots config: ' + str(error), file=sys.stderr); sys.exit(1)
