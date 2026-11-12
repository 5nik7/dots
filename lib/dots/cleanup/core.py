"""Read-only inventories and guarded POSIX removal, shared by cleanup rules."""
from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter
import os
import stat


@dataclass
class Target:
    rule: str
    group: str
    path: Path
    mode: str = 'contents'
    entries: dict = field(default_factory=dict)
    reason: str = ''


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            getattr(info, 'st_blocks', 0) * 512)


def inside(path, root):
    return path == root or root in path.parents


def safe_path(path, boundary, *, leaf_link=False):
    path, boundary = Path(path), Path(boundary)
    if not path.is_absolute() or '..' in path.parts or not inside(path, boundary) or path == boundary:
        raise ValueError('cleanup target escapes its application boundary: ' + str(path))
    for parent in [*reversed(path.parents), path]:
        if not os.path.lexists(parent):
            continue
        info = parent.lstat()
        if parent.is_symlink() and not (leaf_link and parent == path):
            raise ValueError('linked cleanup path: ' + str(parent))
        if inside(parent, boundary):
            if info.st_dev != boundary.stat().st_dev or (parent != boundary and os.path.ismount(parent)):
                raise ValueError('mounted cleanup path: ' + str(parent))
            if info.st_uid != os.getuid():
                raise ValueError('cleanup path has another owner: ' + str(parent))


def inventory(target, boundary):
    safe_path(target.path, boundary)
    if not os.path.lexists(target.path):
        return {}
    root = target.path
    out = {}
    pending = []
    device = boundary.stat().st_dev

    def record(path, info):
        if info.st_dev != device or info.st_uid != os.getuid():
            raise ValueError('foreign filesystem or owner: ' + str(path))
        if not any(test(info.st_mode) for test in (stat.S_ISREG, stat.S_ISDIR, stat.S_ISLNK)):
            raise ValueError('special file in cleanup target: ' + str(path))
        out[str(path.relative_to(root))] = fingerprint(info)
        if stat.S_ISDIR(info.st_mode):
            if os.path.ismount(path):
                raise ValueError('mounted cleanup directory: ' + str(path))
            pending.append((path, fingerprint(info)))

    record(root, root.lstat())
    while pending:
        path, expected = pending.pop()
        ancestor = directory_fd(path)
        try:
            fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=ancestor)
        finally:
            os.close(ancestor)
        try:
            if fingerprint(os.fstat(fd)) != expected:
                raise ValueError('directory changed during scan: ' + str(path))
            with os.scandir(fd) as children:
                for child in children:
                    record(path / child.name, child.stat(follow_symlinks=False))
            if fingerprint(os.fstat(fd)) != expected:
                raise ValueError('directory changed during scan: ' + str(path))
        finally:
            os.close(fd)
    if target.mode == 'file' and not stat.S_ISREG(out['.'][2]):
        raise ValueError('expected a regular cleanup file: ' + str(root))
    if target.mode != 'file' and not stat.S_ISDIR(out['.'][2]):
        raise ValueError('expected a cleanup directory: ' + str(root))
    return out


def measure(entries):
    counts = Counter(info[:2] for info in entries.values())
    seen = set()
    result = dict(files=0, directories=0, symlinks=0, logical_bytes=0, allocated_bytes=0)
    for info in entries.values():
        kind = 'files' if stat.S_ISREG(info[2]) else 'directories' if stat.S_ISDIR(info[2]) else 'symlinks'
        result[kind] += 1
        if info[:2] in seen:
            continue
        seen.add(info[:2])
        if kind == 'files':
            result['logical_bytes'] += info[5]
        # Removing a name whose other hardlinks survive does not reclaim its blocks.
        if kind != 'files' or counts[info[:2]] >= info[4]:
            result['allocated_bytes'] += info[8]
    return result


def removed(before, after):
    # Replacement names are drift, not proof that this run removed their data.
    gone = {name: info for name, info in before.items() if name not in after}
    return measure(gone)


def public(target):
    entries = {name: info for name, info in target.entries.items()
               if target.mode != 'contents' or name != '.'}
    return dict(rule=target.rule, group=target.group, path=str(target.path),
                mode=target.mode, reason=target.reason, **measure(entries))


def references(paths, proc=Path('/proc')):
    """Observe own-user cwd, executables, descriptors and maps; never read secrets."""
    paths = [str(p) for p in paths]
    hits, failures = [], []
    if not proc.is_dir():
        return [], ['process inspection is unavailable']
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            refs = []
            for part in ('cwd', 'exe'):
                try:
                    refs.append(os.readlink(entry / part))
                except FileNotFoundError:
                    pass
            for fd in (entry / 'fd').iterdir():
                try:
                    refs.append(os.readlink(fd))
                except FileNotFoundError:
                    pass
            try:
                for line in (entry / 'maps').read_text(errors='replace').splitlines():
                    parts = line.split(None, 5)
                    if len(parts) == 6:
                        refs.append(parts[5])
            except FileNotFoundError:
                continue
            for path in paths:
                if any(ref == path or ref.startswith(path + '/') for ref in refs):
                    hits.append(path)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError:
            failures.append('cannot inspect process ' + entry.name)
    return sorted(set(hits)), failures


def directory_fd(path):
    """Open every ancestor without following links, including during races."""
    # Android permits searching ancestors such as / without listing them.
    flags = getattr(os, 'O_PATH', os.O_RDONLY) | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def delete_entries(target, boundary, progress=lambda *args: None, confirmed=None):
    """Remove only inventoried names; never recursively consume newly arrived files."""
    if inventory(target, boundary) != target.entries:
        raise ValueError('target changed since review: ' + str(target.path))
    names = sorted(target.entries, key=lambda name: len(Path(name).parts), reverse=True)
    for count, name in enumerate(names, 1):
        info = target.entries[name]
        if name == '.' and target.mode == 'contents':
            continue
        path = target.path if name == '.' else target.path / name
        safe_path(path, boundary, leaf_link=True)
        fd = directory_fd(path.parent)
        try:
            current = fingerprint(os.stat(path.name, dir_fd=fd, follow_symlinks=False))
            # Directory mtime/size and hardlink counts change as approved children are removed.
            same = current[:4] == info[:4]
            if not stat.S_ISDIR(info[2]):
                same = same and current[5:7] == info[5:7]
            if not same:
                raise ValueError('entry changed before deletion: ' + str(path))
            if stat.S_ISDIR(info[2]):
                os.rmdir(path.name, dir_fd=fd)
            else:
                os.unlink(path.name, dir_fd=fd)
            if confirmed is not None:
                confirmed[name] = info
        finally:
            os.close(fd)
        progress('Removing ' + target.rule, count, len(names))
