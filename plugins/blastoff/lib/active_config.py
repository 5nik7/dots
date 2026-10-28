"""Pinned active-file aliases; parent-directory write policy stays strict."""
import os
from pathlib import Path


def link_target(value, windows=False):
    # readlink() on Windows returns extended-length substitution paths. Match
    # ordinary drive/UNC spellings used by overrides, locks and provenance.
    if windows and value.startswith('\\\\?\\'):
        value = value[4:]
        if value.startswith('UNC\\'):
            value = '\\\\' + value[4:]
    return Path(value)


def stamp(path):
    value = path.lstat()
    return (value.st_dev, value.st_ino, value.st_mode, value.st_mtime_ns,
            value.st_ctime_ns, os.readlink(path))


class ActiveConfig:
    def __init__(self, core, configured, replace=False):
        self.core, self.configured, self.replace = core, configured, replace
        self.links = []
        current = configured
        if not replace:
            seen = set()
            while current.is_symlink():
                if current in seen or len(self.links) >= 40:
                    raise core.Failure('Active config symlink loop or excessive chain')
                seen.add(current)
                before = stamp(current)
                # Windows file symlinks are supported; other reparse types are not.
                tag = getattr(current.lstat(), 'st_reparse_tag', 0)
                if tag and tag != 0xA000000C:
                    raise core.Failure('Unsupported active config reparse point: '+str(current))
                self.links.append((current, before))
                target = link_target(before[-1], windows=os.name == 'nt')
                current = Path(os.path.abspath(target if target.is_absolute() else current.parent / target))
            if self.links:
                core.regular(current)
        self.target = current
        self.check()

    def check(self, write=False):
        core = self.core
        for alias, expected in self.links:
            try:
                unchanged = alias.is_symlink() and stamp(alias) == expected
            except OSError:
                unchanged = False
            if not unchanged:
                raise core.Failure('Active config link changed during operation: '+str(alias))
            if write:
                core.inspect_parents(alias.parent)
        if write:
            core.inspect_parents(self.target.parent)
            if core.exists(self.target):
                core.regular(self.target, links=self.replace and self.target.is_symlink())
            elif self.links:
                raise core.Failure('Active config symlink target disappeared')
        return self.target
