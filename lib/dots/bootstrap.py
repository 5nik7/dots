"""Standalone missing-checkout acquisition used by generated startup snippets."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def publish_checkout(checkout, destination):
    """Atomically expose a staged checkout without replacing an occupied path."""
    if os.name == 'nt':
        os.rename(checkout, destination)
    elif sys.platform.startswith(('linux', 'android')):
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, 'renameat2', None)
        if rename is None: raise ValueError('atomic no-replace checkout publication is unavailable')
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(checkout), -100, os.fsencode(destination), 1):
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
    else:
        raise ValueError('automatic checkout publication is unsupported on this platform')


def acquire(destination, source, ref='main'):
    """Use the same native acquisition code as an installed shell."""
    target = Path(destination).expanduser().absolute()
    helpers = Path(__file__).resolve().parent / 'shell/bootstrap'
    if os.name == 'nt':
        engine = shutil.which('powershell.exe') or shutil.which('pwsh')
        if not engine:
            raise ValueError('native PowerShell is required for checkout acquisition')
        args = [engine, '-NoProfile', '-NonInteractive', '-File', str(helpers/'locate.ps1'), 'interactive', '-Utf8']
    else:
        args = ['sh', str(helpers/'locate.sh'), 'interactive']
    env = dict(os.environ, DOTS_BOOTSTRAP_DIR=str(target), DOTS_BOOTSTRAP_SOURCE=source,
               DOTS_BOOTSTRAP_REF=ref)
    result = subprocess.run(args, env=env, capture_output=True, text=True, encoding='utf-8' if os.name == 'nt' else None, timeout=200)
    if result.returncode or not result.stdout.strip() or not (target / 'lib/dots/shell/startup.bash').is_file():
        raise ValueError(result.stderr.strip() or 'checkout acquisition failed')
    return target

def main():
    destination=os.environ.get('DOTS_BOOTSTRAP_DIR') or str(Path.home()/'dots')
    source=os.environ.get('DOTS_BOOTSTRAP_SOURCE','https://github.com/5nik7/dots.git')
    ref=os.environ.get('DOTS_BOOTSTRAP_REF','main')
    acquire(destination,source,ref)


if __name__ == '__main__':
    try: main()
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('dots bootstrap: '+str(error),file=sys.stderr);sys.exit(1)
