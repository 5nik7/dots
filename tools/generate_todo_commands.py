#!/usr/bin/env python3
"""Generate/check static first-party todo adapters from shared definitions."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from todo_commands import COMMANDS, header

def main():
    check = sys.argv[1:] == ['--check']
    if sys.argv[1:] not in ([], ['--check']):
        return 2
    failures = []
    for action in COMMANDS:
        path = ROOT / 'bin' / ('dots-todo' + ('-' + action if action else ''))
        desired = header(action)
        if check:
            if not path.is_file() or path.read_text() != desired:
                failures.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(desired)
            path.chmod(0o755)
    if failures:
        print('Stale todo adapters: ' + ', '.join(failures), file=sys.stderr)
    return int(bool(failures))

if __name__ == '__main__':
    sys.exit(main())
