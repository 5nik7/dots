#!/usr/bin/env python3
"""Generate/check weather adapters and completion source artifacts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/wttr'))
from commands import COMMANDS, header
from completion import generate, FILES


def main():
    if sys.argv[1:] not in ([], ['--check']):
        return 2
    check = sys.argv[1:] == ['--check']
    outputs = {ROOT / 'bin' / ('dots-wttr' + ('-' + action if action else '')): header(action)
               for action in COMMANDS}
    outputs.update({ROOT / 'shells' / shell / 'completions' / name: generate(shell)
                    for shell, name in FILES.items()})
    failures = []
    for path, desired in outputs.items():
        if not path.is_file() or path.read_text(encoding='utf-8') != desired:
            if check:
                failures.append(str(path.relative_to(ROOT)))
            else:
                path.write_text(desired, encoding='utf-8')
        if not check and path.parent == ROOT / 'bin':
            path.chmod(0o755)
    if failures:
        print('Stale weather artifacts: ' + ', '.join(failures), file=sys.stderr)
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
