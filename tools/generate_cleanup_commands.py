#!/usr/bin/env python3
"""Generate cleanup command adapters from their static grammar."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from cleanup_commands import COMMANDS, header


def main():
    if sys.argv[1:] not in ([], ['--check']): return 2
    stale = []
    for action in COMMANDS:
        path = ROOT / 'bin' / ('dots-cleanup'+('-'+action if action else ''))
        text = header(action)
        if sys.argv[1:]:
            if not path.is_file() or path.read_text() != text: stale.append(path.name)
        else:
            path.write_text(text); path.chmod(0o755)
    if stale: print('Stale cleanup adapters: '+', '.join(stale), file=sys.stderr)
    return bool(stale)


if __name__ == '__main__': sys.exit(main())
