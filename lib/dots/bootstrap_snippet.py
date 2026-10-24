"""Emit self-contained startup bootstrap code without executing it."""
import base64
from pathlib import Path
import sys


def snippet(shell):
    code=(Path(__file__).with_name('bootstrap.py')).read_text()
    payload=base64.b64encode(code.encode()).decode()
    python="import base64; exec(compile(base64.b64decode("+repr(payload)+"), 'dots-bootstrap', 'exec'))"
    if shell in ('bash','zsh'):
        import shlex
        return '''# Dots: acquire a missing checkout, then load full shell configuration.
if [[ -r ${DOTS_BOOTSTRAP_DIR:-$HOME/dots}/lib/dots/shell/startup.bash ]]; then
  export DOTS="${DOTS_BOOTSTRAP_DIR:-$HOME/dots}"
  source "$DOTS/shells/'''+shell+'/init.'+shell+'''"
elif command -v python3 >/dev/null 2>&1; then
  if command python3 -B -c '''+shlex.quote(python)+'''; then
    export DOTS="${DOTS_BOOTSTRAP_DIR:-$HOME/dots}"
    source "$DOTS/shells/'''+shell+'/init.'+shell+'''"
  fi
else
  printf 'dots: Python is needed for first-time preparation; continuing without Dots\\n' >&2
fi
'''
    if shell=='powershell':
        return '''# Dots native PowerShell bootstrap.
$dotsBootstrapRoot = if ($env:DOTS_BOOTSTRAP_DIR) { $env:DOTS_BOOTSTRAP_DIR } else { Join-Path $HOME 'dots' }
$dotsBootstrapPython = Get-Command python3, python -ErrorAction SilentlyContinue | Select-Object -First 1
if (Test-Path -LiteralPath (Join-Path $dotsBootstrapRoot 'lib/dots/shell/startup.bash') -PathType Leaf) {
    $env:DOTS = $dotsBootstrapRoot
    . (Join-Path $env:DOTS 'shells/powershell/profile.ps1')
} elseif ($dotsBootstrapPython) {
    & $dotsBootstrapPython.Source -B -c '''+"'"+python.replace("'","''")+"'"+'''
    if ($LASTEXITCODE -eq 0) {
        $env:DOTS = if ($env:DOTS_BOOTSTRAP_DIR) { $env:DOTS_BOOTSTRAP_DIR } else { Join-Path $HOME 'dots' }
        . (Join-Path $env:DOTS 'shells/powershell/profile.ps1')
    }
} else { Write-Warning 'dots: Python is needed for first-time preparation; continuing without Dots' }
'''
    raise ValueError('bootstrap supports bash, zsh and powershell')


if __name__=='__main__':
    print(snippet(sys.argv[1]),end='')
