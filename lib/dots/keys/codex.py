"""Offline Codex CLI reference and bounded, inert user keymap inspection."""
import json
import os
from pathlib import Path
import re
import tomllib

from .model import record, readable
from .providers import read_file

DATA = Path(__file__).parent / 'data'
FALLBACKS = {'submit', 'queue', 'toggle_shortcuts'}
MODIFIERS = {'ctrl': 'ctrl', 'control': 'ctrl', 'alt': 'alt', 'option': 'alt',
             'shift': 'shift', 'super': 'super', 'cmd': 'super', 'command': 'super'}
ALIASES = {'escape': 'esc', 'return': 'enter', 'spacebar': 'space', 'pgup': 'page-up',
           'pageup': 'page-up', 'pgdn': 'page-down', 'pagedown': 'page-down', 'del': 'delete'}
KEYS = {'enter', 'tab', 'backspace', 'esc', 'delete', 'up', 'down', 'left', 'right',
        'home', 'end', 'page-up', 'page-down', 'space', 'minus'}


def config_path():
    # Codex uses the native user home on Windows too, not APPDATA or XDG.
    return Path(os.environ['CODEX_HOME']).expanduser() / 'config.toml' if os.environ.get('CODEX_HOME') else Path.home() / '.codex/config.toml'


def normalize(spec):
    """Codex's ASCII key aliases; preserve the original separately in row.key."""
    if not isinstance(spec, str) or not spec or len(spec) > 256 or not spec.isascii() or any(ord(c) < 32 for c in spec):
        raise ValueError('Invalid Codex key notation')
    strokes = spec.lower().split()
    if not 1 <= len(strokes) <= 2:
        raise ValueError('Codex bindings have one or two strokes')
    result = []
    for index, stroke in enumerate(strokes):
        if stroke == 'leader' and index == 0 and len(strokes) == 2:
            result.append('leader')
            continue
        parts = [p for p in stroke.split('-') if p]
        mods = set()
        while parts and parts[0] in MODIFIERS:
            mod = MODIFIERS[parts.pop(0)]
            if mod in mods:
                raise ValueError('Duplicate Codex modifier')
            mods.add(mod)
        key = '-'.join(parts)
        key = ALIASES.get(key, key)
        if not (key in KEYS or len(key) == 1 and key.isprintable() or re.fullmatch(r'f(?:[1-9]|1[0-9]|2[0-4])', key)):
            raise ValueError('Unknown Codex key name')
        result.append('-'.join([*[m for m in ('ctrl', 'alt', 'shift', 'super') if m in mods], key]))
    return ' '.join(result)


def display(spec, leaders):
    def stroke(key):
        # Keep key names distinct from the '-' modifier separator.
        key = key.replace('page-up', 'PageUp').replace('page-down', 'PageDown')
        if key == 'minus':return '-'
        if key.endswith('-minus'):key = key[:-5] + '-'
        key = re.sub(r'(^|-)f(\d+)$', lambda m: m[1] + 'F' + m[2], key)
        return readable(key)
    if spec.startswith('leader '):
        prefix = ' / '.join(stroke(k) for k in leaders) or 'Leader (unbound)'
        return prefix + ' → ' + stroke(spec[7:])
    return ' → '.join(stroke(k) for k in spec.split())


def overrides(path, known, notes):
    if not path.is_file():
        notes.append('No readable Codex user keymap at ' + str(path))
        return {}
    try:
        data = tomllib.loads(read_file(path))
        tui = data.get('tui', {})
        if not isinstance(tui, dict) or not isinstance(tui.get('keymap', {}), dict):
            raise ValueError('Invalid keymap table')
        keymap = tui.get('keymap', {})
    except (ValueError, OSError, UnicodeError):
        # Never include TOML values, credentials, or parser snippets in diagnostics.
        notes.append('Codex user configuration could not be read; bundled defaults remain available.')
        return {}
    result = {}; unsupported = False; invalid = False
    for mode, actions in keymap.items():
        if not isinstance(actions, dict):
            invalid = True
            continue
        for action, value in actions.items():
            if (mode, action) not in known:
                unsupported = True
                continue
            values = [value] if isinstance(value, str) else value
            try:
                if not isinstance(values, list) or len(values) > 128:
                    raise ValueError('Invalid binding alternatives')
                parsed = [(raw, normalize(raw)) for raw in values]
                if (mode, action) == ('global', 'leader') and any(' ' in key for _, key in parsed):
                    raise ValueError('Leader must be a single stroke')
                result[mode, action] = parsed
            except ValueError:
                invalid = True
    if unsupported:notes.append('Unsupported Codex context/action entries were omitted; reference targets CLI 0.164.0.')
    if invalid:notes.append('Invalid Codex keymap entries were omitted; runtime validation may reject this configuration.')
    return result


def codex_rows(notes, defaults=True):
    path = DATA / 'codex-defaults.json'
    catalog = json.loads(read_file(path))
    actions = catalog['actions']
    known = {(a['mode'], a['action']) for a in actions if a['configurable']}
    known.update(('global', action) for action in FALLBACKS)
    config = config_path()
    custom = overrides(config, known, notes)
    leaders = [key for _, key in custom.get(('global', 'leader'), [('ctrl-x', 'ctrl-x')])]
    # The implicit leader yields to an explicit binding/chord that uses Ctrl-X.
    if ('global', 'leader') not in custom and any(key.split()[0] == 'ctrl-x' for values in custom.values() for _, key in values):
        leaders = []
    rows = []

    def add(mode, action, raw, spec, description, source, default, status=None, layer=None):
        row = record('codex', mode, raw, action, description, source=source,
                     default=default, layer=layer or ('bundled' if default else 'tui.keymap.' + mode))
        row['display'] = display(spec, leaders) if spec else 'Unbound'
        row['status'] = status or 'configured; activation unverified'
        rows.append(row)
        return row

    for entry in actions:
        mode, action = entry['mode'], entry['action']
        identity = (mode, action)
        setting = identity if identity in custom else ('global', action) if mode == 'composer' and action in FALLBACKS and ('global', action) in custom else None
        description = entry['description']
        if mode.startswith('vim_'):description += ' Requires Vim mode and this editing context.'
        elif mode == 'editor':description += ' Text-area editing; composer submission and popups can intercept this key.'
        elif action.startswith('toggle_voice'):description += ' Requires voice support; mute applies during a voice conversation.'
        elif action == 'toggle_shortcuts':description += ' With an empty composer.'
        elif action == 'submit':description += ' While working, steer the active turn.'
        elif action == 'open_presets':description += ' Uses the shared leader when its chord is available.'
        for key in entry['keys']:
            status = 'shadowed' if setting or key.startswith('leader ') and not leaders or identity == ('global', 'leader') and not leaders else None
            add(mode, action, key, key, description, path, True, status)
        if setting:
            values = custom[setting]
            layer = 'tui.keymap.' + '.'.join(setting)
            if not values:
                add(mode, action, [], '', description, config, False, 'disabled', layer)
            for raw, spec in values:
                add(mode, action, raw, spec, description, config, False,
                    'disabled' if spec.startswith('leader ') and not leaders else None, layer)
        # Retain a global fallback declaration when a context-specific value wins.
        fallback = ('global', action)
        if mode == 'composer' and action in FALLBACKS and setting == identity and fallback in custom:
            if not custom[fallback]:
                add(mode, action, [], '', description, config, False, 'shadowed', 'tui.keymap.global.' + action)
            for raw, spec in custom[fallback]:
                add(mode, action, raw, spec, description, config, False, 'shadowed', 'tui.keymap.global.' + action)

    supplements = DATA / 'codex-contexts.json'
    primary = list(rows)
    for entry in json.loads(read_file(supplements))['bindings']:
        if 'binding_from' in entry:
            mode, action = entry['binding_from']
            for origin in primary:
                if (origin['mode'], origin['action']) != (mode, action):continue
                row = dict(origin, mode=entry['mode'], action=entry['action'], description=entry['description'])
                rows.append(row)
        else:
            for key in entry['keys']:
                row = add(entry['mode'], entry['action'], key, key, entry['description'], supplements, True)
                if entry['action']=='side_terminal_alias':
                    current=[r for r in primary if r['mode']=='global' and r['action']=='toggle_side_conversation' and r['status'] not in ('shadowed','disabled')]
                    if not any(r['display']=='Ctrl+/' for r in current):row['status']='shadowed'
    notes.extend([
        'Bundled Codex CLI ' + catalog['version'] + ' defaults (' + catalog['revision'] + '); installed-version compatibility is unverified.',
        'User tui.keymap overrides, two-stroke/leader chords, supported global fallbacks and explicit unbinding are read without starting Codex.',
        'Project/profile/command-line layers, runtime conflict validation, feature gates and in-session changes are not observed; activation is unverified.',
        'Contexts can intercept shared keys; terminal support affects Shift/Super/function keys. Unix suspension is unavailable on native Windows.',
    ])
    return rows if defaults else [r for r in rows if not r['default']]
