#!/usr/bin/env python3
"""Generate the clipboard family adapters from static metadata."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots'))
from clipboard_commands import COMMANDS, header

if sys.argv[1:] not in ([], ['--check']):
    raise SystemExit(2)
stale = []
for action in COMMANDS:
    path = ROOT/'bin'/('dots-clipboard' + ('-' + action.replace(' ', '-') if action else ''))
    text = header(action)
    if sys.argv[1:]:
        if not path.exists() or path.read_text() != text:
            stale.append(path.name)
    else:
        path.write_text(text); path.chmod(0o755)
if stale:
    print('Stale clipboard adapters: ' + ', '.join(stale), file=sys.stderr)
raise SystemExit(bool(stale))
