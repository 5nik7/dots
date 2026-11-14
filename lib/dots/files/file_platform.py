"""Native filesystem primitives shared by catalog and transaction controllers."""
import os
from pathlib import Path
import stat
import re
import shutil
from pathlib import PureWindowsPath


def validate_windows_path(path):
    value = PureWindowsPath(path)
    if not value.is_absolute() or str(value).lower().startswith(('\\\\wsl$', '\\\\wsl.localhost', '\\\\?\\', '\\\\.\\')):
        raise ValueError('managed Windows paths must be absolute native paths, not WSL or device paths')
    for part in value.parts[1:]:
        if part in ('.', '..') or part.rstrip(' .') != part or any(c in ':*?"<>|' or ord(c) < 32 for c in part) or re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?', part, re.I):
            raise ValueError('unsupported Windows path component')


def native_link_text(value, windows=None):
    """Normalize Windows readlink substitution paths for source lookup only.

    Keep the actual link untouched. Device namespaces other than ordinary drive
    and UNC substitutions stay intact so validate_windows_path refuses them.
    """
    if windows is None:
        windows = os.name == 'nt'
    if windows:
        if value.startswith('\\\\?\\UNC\\'):
            return '\\\\' + value[8:]
        if re.match(r'^\\\\\?\\[A-Za-z]:\\', value):
            return value[4:]
    return value


def link_target_matches(path, target):
    """Compare link text without rewriting guards or following its destination.

    Windows readlink exposes drive/UNC substitution prefixes even when the link
    was created with an ordinary path. Only normalize that observed spelling;
    arbitrary device namespaces and the desired target remain untouched.
    """
    return Path(path).is_symlink() and native_link_text(os.readlink(path)) == str(target)


WINDOWS_EXECUTABLE_SUFFIXES = ('.exe', '.com', '.bat', '.cmd')


def native_staging_suffix(path):
    """Retain Windows filename-derived mode bits without changing digests."""
    suffix = Path(path).suffix.lower()
    return suffix if os.name == 'nt' and suffix in WINDOWS_EXECUTABLE_SUFFIXES else ''


def termux_prefix(platform):
    """Resolve only the explicitly supplied Termux installation prefix."""
    if platform != 'termux':
        return None
    value = os.environ.get('PREFIX', '')
    if not value:
        return None
    root = Path(value)
    if (not root.is_absolute() or root == Path(root.anchor) or
            '..' in root.parts or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('PREFIX must be an absolute non-root directory without traversal or controls')
    return root


def config_root(env=None):
    env = os.environ if env is None else env
    home = Path(env.get('HOME') or env.get('USERPROFILE') or Path.home())
    base = Path(env.get('XDG_CONFIG_HOME') or
                (env.get('APPDATA', home / 'AppData/Roaming') if os.name == 'nt' else home / '.config'))
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


def sync_file(path):
    """Flush an owned regular file; Windows requires a writable handle."""
    flags = os.O_RDWR if os.name == 'nt' else os.O_RDONLY
    with os.fdopen(open_nofollow(path, flags), 'r+b' if os.name == 'nt' else 'rb') as stream:
        os.fsync(stream.fileno())


def copy_file(source, dest):
    """Copy and flush a new payload without changing the source's metadata."""
    shutil.copyfile(source, dest, follow_symlinks=False)
    # Acquire write access before copystat restores a read-only attribute. Keep
    # that handle through the flush instead of reopening a read-only copy.
    with os.fdopen(open_nofollow(dest, os.O_RDWR), 'r+b') as stream:
        shutil.copystat(source, dest, follow_symlinks=False)
        os.fsync(stream.fileno())
    return dest


def prepare_text(dest, text, previous):
    """Prepare the same text object for receipt prediction and publication."""
    previous = Path(previous)
    with Path(dest).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
        stream.flush()
        if previous.exists() and not previous.is_symlink():
            os.chmod(dest, stat.S_IMODE(previous.stat().st_mode))
        os.fsync(stream.fileno())


def permissions(fd, path=None):
    if os.name != 'nt':
        os.fchmod(fd, stat.S_IMODE(path.stat().st_mode) if path and path.exists() else 0o644)


def state_root(env=None):
    env = os.environ if env is None else env
    home = Path(env.get('HOME') or env.get('USERPROFILE') or Path.home())
    if env.get('XDG_STATE_HOME'):
        base = Path(env['XDG_STATE_HOME'])
    elif os.name == 'nt':
        base = Path(env.get('LOCALAPPDATA', home / 'AppData/Local'))
    else:
        base = home / '.local/state'
    if not base.is_absolute():
        raise ValueError('state root must be absolute')
    return base / 'dots'
