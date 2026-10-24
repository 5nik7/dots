#!/usr/bin/env python3
"""Literal settings and paths shared by native command controllers."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB / 'files'))
from file_platform import config_root, state_root


def settings(root):
    schema = [line.split('\t', 3) for line in (LIB / 'shell/settings.tsv').read_text().splitlines()]
    values = {key: dict(value=default, source='default') for key, _, default, _ in schema}
    kinds = {key: kind for key, kind, _, _ in schema}
    config = Path(os.environ.get('DOTS_CONFIG_FILE') or config_root() / 'dots/config.env')
    if not config.is_absolute():
        raise ValueError('DOTS_CONFIG_FILE must be absolute')
    patterns = dict(bool='[01]', style='auto|always|never', suggestions='deja|autosuggestions|none', id='[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*')
    def valid(key, value):
        if key not in kinds or not re.fullmatch(patterns[kinds[key]], value):
            raise ValueError('invalid Dots setting: ' + key)
    if config.exists():
        seen = set()
        for line in config.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'): continue
            key, sep, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if not sep or key in seen: raise ValueError('invalid or repeated Dots setting')
            if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]: value = value[1:-1]
            valid(key, value)
            values[key] = dict(value=value, source='config')
            seen.add(key)
    for key in kinds:
        value = os.environ.get(key)
        if value:
            valid(key, value)
            values[key] = dict(value=value, source='environment')
    for line in (LIB / 'shell/paths.tsv').read_text().splitlines():
        key, _, relative = line.split('\t')
        if key != '-': values[key] = dict(value=str(root / relative), source='checkout')
    if os.name == 'nt': values['THEMESCMD'] = dict(value=str(root / 'bin/theme.ps1'), source='checkout')
    state = state_root()
    values['DOTS_CONFIG_FILE'] = dict(value=str(config), source='resolved')
    values['DOTS_STATE_DIR'] = dict(value=str(state), source='resolved')
    selection = os.environ.get('DOTS_THEME_SELECTION')
    identity = dict(value=selection or values['DOTS_THEME_DEFAULT']['value'], source='environment' if selection else 'default')
    if not selection:
        token = state / 'themes/current'
        if token.is_file() and not token.is_symlink():
            generation = token.read_text().strip()
            if re.fullmatch(r'g\.[a-zA-Z0-9]+', generation):
                path = state / 'themes/generations' / generation / 'id'
                if path.is_file(): identity = dict(value=path.read_text().strip(), source='published')
    values['DOTS_THEME_ID'] = identity
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', nargs='?')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    root = Path(os.environ.get('DOTS') or LIB.parents[1]).resolve()
    values = settings(root)
    if args.name:
        if args.name not in values: parser.error('unknown setting')
        values = {args.name: values[args.name]}
    if args.json: print(json.dumps(dict(version=1, values=values), ensure_ascii=True))
    elif args.name: print(values[args.name]['value'])
    elif not sys.stdout.isatty():
        for key, item in values.items(): print(f"{key}={item['value']} [{item['source']}]")
    else:
        from catalog import Presentation
        ui = Presentation()
        ui.heading('Dots environment')
        path_names = {line.split('\t', 1)[0] for line in (LIB / 'shell/paths.tsv').read_text().splitlines()}
        path_names.update(('DOTS_CONFIG_FILE', 'DOTS_STATE_DIR'))
        for key, item in values.items():
            value = ui.path(item['value']) if key in path_names else item['value']
            ui.detail(key, value + ' [' + item['source'] + ']')


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError) as error:
        print('dots env: ' + str(error), file=sys.stderr)
        sys.exit(2)
