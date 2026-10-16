"""Native filesystem primitives shared by catalog and transaction controllers."""
import os
from pathlib import Path
import stat


def reparse(path):
    try:
        return bool(getattr(Path(path).lstat(), 'st_file_attributes', 0) & 0x400)
    except FileNotFoundError:
        return False


def check_object(path):
    if reparse(path) and not Path(path).is_symlink():
        raise ValueError('unsupported reparse point: ' + str(path))


def open_nofollow(path, flags, mode=0o600):
    check_object(path)
    if Path(path).is_symlink():
        raise ValueError('refusing symlink: ' + str(path))
    return os.open(path, flags | getattr(os, 'O_NOFOLLOW', 0), mode)


def lock(handle, blocking=False):
    handle.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))


def sync_dir(path):
    # Windows does not expose POSIX directory fsync. Payload/journal files are
    # flushed; rename recovery covers process interruption, not power loss.
    if os.name == 'nt':
        return
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def permissions(fd, path=None):
    if os.name != 'nt':
        os.fchmod(fd, stat.S_IMODE(path.stat().st_mode) if path and path.exists() else 0o644)


def state_root():
    home = Path(os.environ.get('HOME') or Path.home())
    if os.environ.get('XDG_STATE_HOME'):
        base = Path(os.environ['XDG_STATE_HOME'])
    elif os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local'))
    else:
        base = home / '.local/state'
    if not base.is_absolute():
        raise ValueError('state root must be absolute')
    return base / 'dots'
