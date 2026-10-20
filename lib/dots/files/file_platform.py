"""Native filesystem primitives shared by catalog and transaction controllers."""
import os
from pathlib import Path
import stat
import re
from pathlib import PureWindowsPath


def validate_windows_path(path):
    value = PureWindowsPath(path)
    if not value.is_absolute() or str(value).lower().startswith(('\\\\wsl$', '\\\\wsl.localhost', '\\\\?\\', '\\\\.\\')):
        raise ValueError('managed Windows paths must be absolute native paths, not WSL or device paths')
    for part in value.parts[1:]:
        if part in ('.', '..') or part.rstrip(' .') != part or any(c in ':*?"<>|' or ord(c) < 32 for c in part) or re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?', part, re.I):
            raise ValueError('unsupported Windows path component')


def config_root():
    home = Path(os.environ.get('HOME') or Path.home())
    base = Path(os.environ.get('XDG_CONFIG_HOME') or
                (os.environ.get('APPDATA', home / 'AppData/Roaming') if os.name == 'nt' else home / '.config'))
    if not base.is_absolute():
        raise ValueError('config root must be absolute')
    return base


def reparse(path):
    try:
        return bool(getattr(Path(path).lstat(), 'st_file_attributes', 0) & 0x400)
    except FileNotFoundError:
        return False


def check_object(path):
    if os.name == 'nt':
        validate_windows_path(path)
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
