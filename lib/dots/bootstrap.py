"""Standalone missing-checkout acquisition used by generated startup snippets."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


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
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        if (destination / 'bin/dots').is_file() and (destination / 'lib/dots/shell/startup.bash').is_file(): return destination
        raise ValueError('bootstrap destination exists and is not a Dots checkout')
    if not shutil.which('git'): raise ValueError('Git is required to fetch the missing checkout')
    if not ref or ref.startswith('-') or any(c.isspace() for c in ref): raise ValueError('invalid bootstrap ref')
    url = urlsplit(source)
    if source.startswith('-') or url.username or url.password or url.query or url.fragment:
        raise ValueError('bootstrap source must not contain credentials or URL parameters')
    if not Path(source).is_absolute() and url.scheme not in ('', 'https', 'file'): raise ValueError('bootstrap source must be HTTPS or a local repository')
    destination.parent.mkdir(parents=True,exist_ok=True)
    lockpath = destination.parent / ('.' + destination.name + '.bootstrap.lock')
    fd = os.open(lockpath, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
        if destination.exists() or destination.is_symlink():
            if (destination/'bin/dots').is_file(): return destination
            raise ValueError('bootstrap destination became occupied')
        work = Path(tempfile.mkdtemp(prefix='.'+destination.name+'.bootstrap-',dir=destination.parent))
        journal = work/'journal.json'
        def record(status):
            with journal.open('w') as out:
                json.dump(dict(version=1,status=status,destination=str(destination),ref=ref),out)
                out.flush();os.fsync(out.fileno())
        record('preparing')
        try:
            env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',GIT_CONFIG_NOSYSTEM='1')
            result=subprocess.run(['git','-c','submodule.recurse=false','-c','protocol.ext.allow=never','clone','--no-recurse-submodules','--single-branch','--branch',ref,'--',source,str(work/'checkout')],env=env,capture_output=True,timeout=90)
            if result.returncode: raise ValueError('checkout fetch failed; existing paths were preserved')
            checkout=work/'checkout'
            for relative in ('bin/dots','bin/dots.ps1','lib/dots/shell/startup.bash'):
                if not (checkout/relative).is_file(): raise ValueError('fetched repository lacks the Dots startup layout')
            record('prepared')
            publish_checkout(checkout, destination)
            record('committed')
            # Retain a small acquisition journal; payload staging is now empty.
            return destination
        except BaseException:
            record('failed')
            raise


def main():
    destination=os.environ.get('DOTS_BOOTSTRAP_DIR') or str(Path.home()/'dots')
    source=os.environ.get('DOTS_BOOTSTRAP_SOURCE','https://github.com/5nik7/dots.git')
    ref=os.environ.get('DOTS_BOOTSTRAP_REF','main')
    acquire(destination,source,ref)


if __name__ == '__main__':
    try: main()
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('dots bootstrap: '+str(error),file=sys.stderr);sys.exit(1)
