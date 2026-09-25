"""Read-only standalone bridge to the static Dots completion protocol."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def complete(argv, parser):
    if len(argv) < 4 or argv[0] not in ('bash', 'zsh', 'fish') or argv[2] != '--':
        raise ValueError('invalid completion request')
    shell, cursor = argv[0], int(argv[1])
    words = argv[3:]
    if not 1 <= cursor < len(words):
        raise ValueError('invalid completion cursor')
    # Drop words after the cursor. Presentation prefixes are only legal before
    # the action; create --color is a seed and must retain its original meaning.
    words = words[1:cursor+1]
    while len(words) > 1 and words[0].startswith(('--color=', '--icons=')):
        if words.pop(0).split('=', 1)[1] not in ('auto', 'always', 'never'):
            return
    current = words[-1]
    if len(words) == 1:
        candidates = [('--help', 'Show help'), ('-h', 'Show help'),
                      ('--color=', 'Color mode (DOTS_COLOR)'),
                      ('--icons=', 'Icon mode (DOTS_ICONS)')]
        actions = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        candidates += [(name, child.description) for name, child in actions.choices.items()]
        if current.startswith(('--color=', '--icons=')):
            lead = current.split('=', 1)[0] + '='
            candidates = [(lead + mode, '') for mode in ('auto', 'always', 'never')]
        for value, description in candidates:
            if value.startswith(current):
                print('candidate', value, description, sep='\t')
        return
    code = Path(__file__).resolve().parents[3]
    root = Path(os.environ.get('DOTS') or code)
    env = dict(os.environ, DOTS=str(code), DOTHEMES=str(root/'themes'), THEMES=str(root/'themes'))
    # Read bundled headers via the existing provider; never execute leaf commands
    # or the Go engine. The adapter handles shell escaping and filesystem matches.
    result = subprocess.run([str(code/'bin/dots'), '__complete', shell, str(len(words)+1),
                             '--', 'dots', 'anodize', *words], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    if result.returncode == 0:
        sys.stdout.buffer.write(result.stdout)
