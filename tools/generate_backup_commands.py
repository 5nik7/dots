#!/usr/bin/env python3
"""Generate backup command adapters from the shared static grammar."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from bak_commands import COMMANDS, header


def main():
    if sys.argv[1:] not in ([], ['--check']): return 2
    stale = []
    outputs = {ROOT / 'bin' / ('dots-bak' + ('-' + action if action else '')): header(action) for action in COMMANDS}
    bash = '''#!/usr/bin/env bash
# Resolve the selected launcher, not an inherited checkout variable.
_bak_source=${BASH_SOURCE[0]}
[[ $_bak_source == /* ]] || _bak_source=$PWD/$_bak_source
_bak_links=0
while [[ -L $_bak_source ]]; do
  (( ++_bak_links <= 40 )) || { printf 'bak: executable symlink loop\\n' >&2; exit 1; }
  _bak_target=$(readlink -- "$_bak_source") || exit 1
  if [[ $_bak_target == /* ]]; then _bak_source=$_bak_target
  else _bak_source=${_bak_source%/*}/$_bak_target; fi
done
DOTS=$(cd -- "${_bak_source%/*}/.." && pwd -P) || exit 1
export DOTS
exec python3 -B "$DOTS/lib/dots/bak_cli.py" "$@"
'''
    outputs[ROOT/'bin/bak'] = bash
    outputs[ROOT/'scripts/bak'] = bash
    native = '''# Native backup bridge; literal arguments and shared transactions.
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'lib/dots/ui.ps1')
try {
    . (Join-Path $root 'lib/dots/files/entry.ps1')
    Invoke-DotsFiles $root 'bak' @($args | ForEach-Object { [string] $_ })
    exit $script:DotsFilesExitCode
} catch {
    Write-DotsMessage ('bak: ' + $_.Exception.Message) error @{}
    exit 1
}
'''
    outputs[ROOT/'bin/bak.ps1'] = native
    outputs[ROOT/'scripts/bak.ps1'] = native
    outputs[ROOT/'shells/powershell/Scripts/bak.ps1'] = native.replace(
        '$root = Split-Path -Parent $PSScriptRoot',
        '$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))')
    for path, text in outputs.items():
        if sys.argv[1:]:
            if not path.is_file() or path.read_text() != text: stale.append(path.name)
        else:
            path.write_text(text, newline='\r\n' if path.suffix=='.ps1' else '\n');path.chmod(0o755)
    if stale: print('Stale backup adapters: ' + ', '.join(stale), file=sys.stderr)
    return int(bool(stale))


if __name__ == '__main__': sys.exit(main())
