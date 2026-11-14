"""Read-only standalone bridge to the static Dots completion protocol."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from logo import MODES, LAYOUTS


def complete(argv, parser):
    display_types = len(argv) > 2 and argv[0] == 'zsh' and argv[2] == '--display-types'
    if display_types:
        argv = [*argv[:2], *argv[3:]]
    if len(argv) < 4 or argv[0] not in ('bash', 'zsh', 'fish') or argv[2] != '--':
        raise ValueError('invalid completion request')
    shell, cursor = argv[0], int(argv[1])
    words = argv[3:]
    if not 1 <= cursor < len(words):
        raise ValueError('invalid completion cursor')
    def emit(value, description='', role='value'):
        fields = ['candidate', value, description]
        if display_types:
            fields.append(role)
        print(*fields, sep='\t')
    # Drop words after the cursor. Strip root presentation options here;
    # create --color is a seed and leaf logo options use static metadata below.
    words = words[1:cursor+1]
    prefixes = {'--color': ('auto', 'always', 'never'), '--icons': ('auto', 'always', 'never'),
                '--logo': MODES, '--logo-layout': LAYOUTS}
    while len(words) > 1:
        if words[0] == '--interactive':
            words.pop(0)
            continue
        flag, equals, value = words[0].partition('=')
        if flag not in prefixes:
            break
        if not equals:
            if flag in ('--color', '--icons'):
                return
            if len(words) == 2:
                for value in prefixes[flag]:
                    if value.startswith(words[1]):
                        emit(value)
                return
            value = words.pop(1)
        words.pop(0)
        if value not in prefixes[flag]:
            return
    current = words[-1]
    if len(words) == 1:
        candidates = [('--help', 'Show help', 'option'), ('-h', 'Show help', 'option'),
                      ('--interactive', 'Open guided authoring and selection', 'option'),
                      ('--color=', 'Color mode (DOTS_COLOR)', 'option'),
                      ('--icons=', 'Icon mode (DOTS_ICONS)', 'option'),
                      ('--logo=', 'Logo renderer (ANODIZE_LOGO)', 'option'),
                      ('--logo-layout=', 'Logo layout (ANODIZE_LOGO_LAYOUT)', 'option')]
        actions = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        candidates += [(name, child.description, 'command') for name, child in actions.choices.items()]
        if '=' in current and current.split('=', 1)[0] in prefixes:
            flag = current.split('=', 1)[0]
            candidates = [(flag + '=' + mode, '', 'value') for mode in prefixes[flag]]
        for value, description, role in candidates:
            if value.startswith(current):
                emit(value, description, role)
        return
    code = Path(__file__).resolve().parents[2]
    root = Path(os.environ.get('DOTS') or code)
    env = dict(os.environ, DOTS=str(code), DOTHEMES=str(root/'themes'), THEMES=str(root/'themes'))
    # Read bundled headers via the existing provider; never execute leaf commands
    # or the Go engine. The adapter handles shell escaping and filesystem matches.
    result = subprocess.run([str(code/'bin/dots'), '__complete', shell, str(len(words)+1),
                             *(['--display-types'] if display_types else []),
                             '--', 'dots', 'anodize', *words], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    if result.returncode == 0:
        sys.stdout.buffer.write(result.stdout)
