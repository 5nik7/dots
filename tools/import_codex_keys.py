#!/usr/bin/env python3
"""Import the audited Codex 0.164.0 action inventory from a local source checkout.

No network or application execution. Supplemental UI bindings are maintained
separately in codex-contexts.json. See keys/data/SOURCES.md for the audit scope.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

REVISION = '6aaac694803004a63c6f393d153c96d22521a6b9'
FILES = ('tui/src/keymap.rs', 'tui/src/keymap/bindings.rs',
         'config/src/tui_keymap.rs', 'tui/src/keymap/vim_search.rs',
         'tui/src/keymap/chords.rs', 'tui/src/keymap/leader.rs',
         'tui/src/keymap/chords/quick_dial_defaults.rs')


def extract(root):
    sources = {name: (root / 'codex-rs' / name).read_text() for name in FILES}
    text = sources[FILES[0]]
    defaults = text[text.index('    fn built_in_defaults()'):text.index('    /// Reject ambiguous bindings')]
    registry = sources[FILES[1]].split('define_runtime_action_bindings! {', 1)[1]
    config = sources[FILES[2]]
    descriptions = {}
    for group in re.finditer(r'pub struct Tui(\w+)Keymap \{(.*?)\n\}', config, re.S):
        mode = re.sub(r'(?<!^)([A-Z])', r'_\1', group[1]).lower()
        for field in re.finditer(r'((?:    ///[^\n]*\n)+)    pub (\w+):', group[2]):
            descriptions[mode, field[2]] = ' '.join(re.sub(r'^    /// ?', '', field[1], flags=re.M).split())
    groups = list(re.finditer(r'^            (\w+): (?:Arc::new\()?\w+Keymap \{', defaults, re.M))
    values = {}
    code = r"KeyCode::(?:Char\(('(?:\\.|[^'\\])*')\)|F\((\d+)\)|(\w+))"
    binding = re.compile(r'(plain|ctrl|alt|shift)\(' + code + r'\)|raw\(KeyBinding::new\(\s*' + code + r',\s*([\w: |]+),?\s*\)\)', re.S)
    names = {'Esc': 'esc', 'PageUp': 'page-up', 'PageDown': 'page-down', 'BackTab': 'shift-tab'}

    def keys(body):
        result = []
        for match in binding.finditer(body):
            kind, char, fn, name, rchar, rfn, rname, mods = match.groups()
            char, fn, name = (char, fn, name) if kind else (rchar, rfn, rname)
            key = ast.literal_eval(char) if char else 'f' + fn if fn else names.get(name, name.lower())
            key = {' ': 'space', '-': 'minus'}.get(key, key)
            prefix = [] if kind == 'plain' else [kind] if kind else [m.lower().replace('control', 'ctrl') for m in re.findall(r'KeyModifiers::(\w+)', mods)]
            result.append('-'.join([*prefix, key]))
        remainder = binding.sub('', body).replace(',', '').strip()
        if remainder:
            raise ValueError('Unrecognized default binding: ' + remainder)
        return result

    for index, group in enumerate(groups):
        mode = 'global' if group[1] == 'app' else group[1]
        section = defaults[group.end():groups[index+1].start() if index+1 < len(groups) else len(defaults)]
        for match in re.finditer(r'(\w+): default_bindings!\[(.*?)\],', section, re.S):
            values[mode, match[1]] = keys(match[2])
    search = sources[FILES[3]]
    for match in re.finditer(r'(\w+): vec!\[(.*?)\],', search):
        values['vim_search', match[1]] = keys(match[2])
    values['vim_normal', 'jump_top'] = ['g g']
    values['vim_operator', 'motion_jump_top'] = ['g g']
    values['chat', 'open_presets'] = ['leader p']
    actions = []
    for group in re.finditer(r'"(\w+)" => \w+, \w+, \w+ \[([^]]+)\]', registry):
        for action in group[2].split(','):
            action = action.strip()
            if not action:
                continue
            configurable = 'runtime_only' not in action
            action = action.split(' =>')[0]
            mode = group[1]
            description = descriptions.get((mode, action))
            if not description:
                if (mode, action) != ('global', 'open_warnings'):
                    raise ValueError('Missing description: ' + mode + '.' + action)
                description = 'Open retained warnings without replacing the composer.'
            actions.append(dict(mode=mode, action=action, keys=values[mode, action],
                                description=description, configurable=configurable))
    actions.append(dict(mode='global', action='leader', keys=['ctrl-x'],
                        description='Prefix for shared shortcut chords.', configurable=True))
    return dict(version='0.164.0', revision=REVISION,
                sources={name: hashlib.sha256(value.encode()).hexdigest() for name, value in sources.items()},
                actions=actions)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = extract(args.source)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
