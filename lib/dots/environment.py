#!/usr/bin/env python3
"""Literal settings and paths shared by native command controllers."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import shutil
from profiles import resolve, public_report, SENSITIVE

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB / 'files'))
from file_platform import config_root, state_root


RETIRED = ('DOTRUBY', 'RUBYCOMP')


def retired_paths(root, env):
    home = env.get('HOME') or env.get('USERPROFILE') or str(Path.home())
    roots = [str(root), env.get('DOTS_PROFILE_CHECKOUT'), str(Path(home)/'dots')]
    return {os.path.normcase(os.path.normpath(str(Path(base)/'ruby/completion'))) for base in roots if base}


def clean_metadata(value):
    return ''.join(record+';' for record in value.split(';') if record and record.split(':',1)[0].split('|',1)[0] not in RETIRED)


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
    compatibility = state / 'current/theme/id'
    if not selection and identity['source'] == 'default' and compatibility.is_file():
        identity = dict(value=compatibility.read_text().strip(), source='published')
    values['DOTS_THEME_ID'] = identity
    return values


TOKEN = re.compile(r'\$\{([A-Z][A-Z0-9_]*)\}')


def declarations(root, profile=None):
    profile = resolve(root) if profile is None else profile
    rows = {key: (value, 'default') for key, value in json.loads((LIB / 'shell/environment.json').read_text())['defaults'].items()}
    if profile['facts']['platform'] == 'windows':
        rows['XDG_CONFIG_HOME'] = ('${APPDATA}', 'platform:windows')
        rows['XDG_CACHE_HOME'] = ('${LOCALAPPDATA}/cache', 'platform:windows')
        rows['XDG_DATA_HOME'] = ('${LOCALAPPDATA}', 'platform:windows')
        rows['XDG_STATE_HOME'] = ('${LOCALAPPDATA}', 'platform:windows')
    for layer in profile['layers']:
        rows.update({key: (value.replace('${PROFILE}', layer['root']), 'profile:' + layer['id']) for key, value in layer.get('environment', {}).items()})
    return rows


def inspect(root):
    profile = resolve(root)
    values = settings(root)
    context = dict(os.environ, DOTS=str(root))
    context.setdefault('HOME', str(Path.home()))
    context.setdefault('APPDATA', str(Path.home() / 'AppData/Roaming'))
    context.setdefault('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))
    for key, (template, origin) in declarations(root, profile).items():
        if template == '@editor':
            default = next((name for name in ('nvim', 'vim', 'vi', 'code', 'nano') if shutil.which(name)), 'vi')
        else: default = TOKEN.sub(lambda m: context.get(m[1], ''), template)
        value = context.get(key) or default
        values[key] = dict(value=value, source='environment' if context.get(key) else origin, group='Applications', default=default, sensitive=bool(SENSITIVE.search(key) or any(SENSITIVE.search(m[1]) for m in TOKEN.finditer(template))))
        context[key] = value
    for entry in os.environ.get('DOTS_ENV_ORIGINS', '').split(';'):
        key, separator, origin = entry.partition('|')
        if separator and key in values and values[key].get('default') == values[key]['value'] and re.fullmatch(r'(?:default|environment|platform:[a-z]+|profile:[a-z0-9_./-]+)', origin):
            values[key]['source'] = origin
    facts = profile['facts']
    for key, value in dict(DOTS_PLATFORM=facts['platform'], DOTS_DISTRO=facts['distro'], DOTS_ARCH=facts['architecture'], DOTS_RUNTIME=facts['runtime'], DOTS_PROFILE=profile['current'], DOTS_PROFILE_LAYERS=' '.join(row['id'] for row in profile['layers'])).items():
        values[key] = dict(value=value, source='detected', group='Platform')
    paths = []
    for row in reversed(profile['layers']):
        for relative in row.get('path', ['bin', 'scripts']):
            path = Path(row['root']) / relative
            if path.is_dir(): paths.append(dict(path=str(path), source='profile:' + row['id']))
    for relative in ('bin', 'scripts'):
        path = root / relative
        if path.is_dir(): paths.append(dict(path=str(path), source='checkout'))
    for key in ('GOBIN',):
        if Path(context[key]).is_dir(): paths.append(dict(path=context[key], source=key))
    for relative in ('.cargo/bin', '.local/bin', 'bin', '.fzf/bin'):
        path = Path(context['HOME']) / relative
        if path.is_dir(): paths.append(dict(path=str(path), source='user-tools'))
    if values['DOTS_INIT_COMMANDS']['value'] == '1':
        paths.append(dict(path=str(state_root() / 'themes/commands/current/bin'), source='theme-commands'))
    for row in paths: row['present'] = row['path'] in os.environ.get('PATH', '').split(os.pathsep)
    values['THEMESCMD'] = dict(value=str(root / ('bin/theme.ps1' if os.name == 'nt' else 'bin/theme')), source='checkout')
    values['THEMESBIN'] = dict(value=str(state_root() / 'themes/commands/current/bin'), source='resolved')
    values['DOTS_THEME_ID']['group'] = 'Current theme'
    values['PATH'] = dict(value=os.environ.get('PATH', ''), source='inherited', group='Paths', contributions=paths)
    for entry in os.environ.get('DOTS_ENV_HOOKS', '').split(';'):
        parts = entry.split(':')
        if len(parts) != 4: continue
        key, origin, private, operation = parts
        if not re.fullmatch(r'[A-Z_a-z][A-Z_a-z0-9]*', key) or not re.fullmatch(r'[a-z0-9_-]+', origin) or private not in ('0','1') or operation not in ('set','unset'): continue
        values[key] = dict(value=os.environ.get(key, ''), source='hook:' + origin, group='Hooks', operation=operation, sensitive=private == '1')
    # Published shell variables are data, never sourced for inspection.
    for name, owner in json.loads((LIB / 'shell/environment.json').read_text())['observed'].items():
        if name in os.environ and name not in values:
            values[name] = dict(value=os.environ[name], source='inherited', owner=owner, group='Applications')
    setting_keys = {line.split('\t')[0] for line in (LIB / 'shell/settings.tsv').read_text().splitlines()}
    for key, row in values.items():
        row.setdefault('group', 'Settings' if key in setting_keys else 'Paths')
        row['inherited'] = 'matches' if key in os.environ and os.environ[key] == row['value'] else 'different' if key in os.environ else 'unset'
        if row.get('sensitive') or SENSITIVE.search(key):
            row['value'] = '[redacted]'; row.pop('default', None); row['sensitive'] = True
    for key in RETIRED: values.pop(key, None)
    return dict(version=1, values=values, platform=facts, profile=public_report(profile), path=paths)


def main():
    if sys.argv[1:] == ['__names']:
        for key in inspect(Path(os.environ.get('DOTS') or LIB.parents[1]).resolve())['values']: print(key)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', nargs='?')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    root = Path(os.environ.get('DOTS') or LIB.parents[1]).resolve()
    result = inspect(root)
    values = result['values']
    if args.name:
        if args.name not in values: parser.error('unknown name')
        result['values'] = values = {args.name: values[args.name]}
    if args.json: print(json.dumps(dict(version=1, values=values) if args.name else result, ensure_ascii=True))
    elif args.name: print(values[args.name]['value'])
    else:
        from catalog import Presentation
        ui = Presentation()
        if not ui.human:
            for key, row in values.items(): print(f"{key}={row['value']} [{row['source']}]")
            return
        from resources import cells, wrap
        def clean(value):
            return ''.join('\\u%04x' % ord(c) if ord(c) < 32 or 127 <= ord(c) < 160 else c for c in str(value))
        kinds = {line.split('\t')[0]: line.split('\t')[1] for line in (LIB / 'shell/settings.tsv').read_text().splitlines()}
        ui.heading('Dots environment')
        for group in ('Platform', 'Current theme', 'Settings', 'Applications', 'Paths', 'Hooks'):
            rows = [(key, row) for key, row in values.items() if row['group'] == group]
            if not rows: continue
            ui.emit(); ui.heading(group)
            for key, row in rows:
                value = row['value']; style = '95' if group == 'Current theme' else None
                path = (group == 'Paths' and key != 'PATH') or (isinstance(value, str) and os.path.isabs(value))
                if path:
                    value = clean(ui.path(value))
                    _, icon, style = ui.resources.describe(row['value'], 'file' if key == 'DOTS_CONFIG_FILE' else 'dir')
                    if ui.icons: value = icon + ' ' + value
                else: value = clean(value)
                if kinds.get(key) == 'bool': value += ' (enabled)' if value == '1' else ' (disabled)'
                origin = clean(row['source'])
                inline = '  ' + key.ljust(26) + '  ' + value + '  [' + origin + ']'
                if cells(inline) <= ui.width:
                    ui.emit(ui.paint('  ' + key.ljust(26), '94') + '  ' + (ui.paint(value,style) if style else value) + '  ' + ui.paint('['+origin+']','2'))
                else:
                    for part in wrap(key,ui.width-2): ui.emit('  '+ui.paint(part,'94'))
                    for part in wrap(value,ui.width-4): ui.emit('    '+(ui.paint(part,style) if style else part))
                    for part in wrap('Source: '+origin,ui.width-4): ui.emit('    '+ui.paint(part,'2'))
                if group in ('Applications','Platform','Hooks'):
                    for part in wrap('Inherited: '+row['inherited'],ui.width-4): ui.emit('    '+ui.paint(part,'2'))



if __name__ == '__main__':
    try: main()
    except (ValueError, OSError) as error:
        print('dots env: ' + str(error), file=sys.stderr)
        sys.exit(2)
