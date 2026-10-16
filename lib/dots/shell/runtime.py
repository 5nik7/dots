"""Data-only settings and palette readers for the native Xonsh adapter."""
from pathlib import Path
import re


def valid(kind, value):
    if kind == 'id':
        return bool(re.fullmatch(r'[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*', value))
    return value in {'bool': ('0', '1'), 'style': ('auto', 'always', 'never'),
                    'suggestions': ('deja', 'autosuggestions', 'none')}[kind]


def settings(root, env):
    config = Path(env.get("DOTS_CONFIG_FILE") or
                  Path(env.get("XDG_CONFIG_HOME") or Path(env['HOME']) / '.config') / 'dots/config.env')
    schema = {}
    for line in (Path(root) / 'lib/dots/shell/settings.tsv').read_text().splitlines():
        key, kind, default, _ = line.split('\t')
        schema[key] = (kind, default)
    values = {key: default for key, (_, default) in schema.items()}
    origins = dict.fromkeys(schema, 'default')
    seen = set()
    if config.exists():
        for number, line in enumerate(config.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if not sep or key not in schema or key in seen:
                raise ValueError(f'dots: invalid setting on line {number}')
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if not valid(schema[key][0], value):
                raise ValueError(f'dots: invalid {key}')
            values[key], origins[key] = value, 'config'
            seen.add(key)
    for key, (kind, _) in schema.items():
        if env.get(key):
            values[key], origins[key] = str(env[key]), 'environment'
        value = values[key]
        if not valid(kind, value):
            raise ValueError(f'dots: invalid {key}')
    return values, origins, str(config)


def palette(state):
    marker = Path(state) / 'themes/current'
    if not marker.exists():
        return None
    generation = marker.read_text().strip()
    if not re.fullmatch(r'g\.[a-zA-Z0-9]+', generation):
        raise ValueError('dots: invalid theme generation')
    data = {'@theme': {}, '@palette': {}, '@role': {}}
    for line in (Path(state) / 'themes/generations' / generation / 'shell.tsv').read_text().splitlines():
        name, key, value = line.split('\t')
        if not re.fullmatch(r'(?:@theme|@palette|@role|[a-z_][a-zA-Z0-9_]*)', name) or not re.fullmatch(r'[a-zA-Z0-9_-]+', key):
            raise ValueError('dots: invalid palette data')
        data.setdefault(name, {})[key] = value
    if not data['@theme'].get('id'):
        raise ValueError('dots: missing theme identity')
    return generation, data
