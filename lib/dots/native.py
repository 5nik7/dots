#!/usr/bin/env python3
"""Literal argument bridge for native shell adapters; never evaluate shell text."""
import base64
import json
from pathlib import Path
import runpy
import sys


def main(argv=None):
    if sys.version_info < (3, 9):
        raise ValueError('Dots requires Python 3.9 or newer')
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise ValueError('native bridge requires a controller and encoded argument array')
    controller, encoded = argv
    allowed = {'cli': 'cli.py', 'usage-logo': 'usage_logo.py', 'wttr': 'wttr/cli.py', 'todo': 'todo_standalone.py', **{name: 'files/' + name + '.py' for name in
               ('catalog', 'check', 'repair', 'manage', 'mappings', 'install', 'browser')}}
    if controller not in allowed:
        raise ValueError('unknown native controller')
    args = json.loads(base64.b64decode(encoded, validate=True).decode('utf-8'))
    if not isinstance(args, list) or not all(isinstance(a, str) and '\0' not in a for a in args):
        raise ValueError('native arguments must be an array of strings without NUL')
    path = Path(__file__).resolve().parent / allowed[controller]
    sys.path.insert(0, str(path.parent))
    sys.argv = [str(path), *args]
    runpy.run_path(str(path), run_name='__main__')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print('dots: ' + str(error), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
