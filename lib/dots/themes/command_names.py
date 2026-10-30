"""Data-only shortcut allocation shared by the Bash and native publishers."""
import os
from pathlib import Path
import re
import sys

ID = re.compile(r'[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*')
RESERVED = set('themes env theme dots anodize current_theme help list current dir show color colors init set refresh switcher install update remove bg plugin plugins files summary'.split())


def allocate(names, owned_bin, *, search_path=None, windows=None, pathext=None):
    """Return {executable: target}, skipped targets; never execute PATH entries.

    The caller must verify the current generation before excluding owned_bin.
    Canonical names are reserved even when their own shortcut cannot be emitted.
    """
    names = sorted(set(names))
    if any(not ID.fullmatch(name) for name in names):
        raise ValueError('unsafe generated command name')
    windows = os.name == 'nt' if windows is None else windows
    search_path = os.environ.get('PATH', os.defpath) if search_path is None else search_path
    normalize = str.casefold if windows else str
    owned = normalize(str(Path(owned_bin).resolve()))
    candidates = set(names) | {name + '-theme' for name in names}
    occupied = set()
    extensions = {''}
    if windows:
        extensions.update(ext.casefold() for ext in (pathext if pathext is not None else os.environ.get('PATHEXT', '.COM;.EXE;.BAT;.CMD')).split(';') if ext.startswith('.'))
        extensions.add('.ps1')
    for entry in search_path.split(';' if windows else os.pathsep):
        directory = Path(entry or os.curdir)
        if normalize(str(directory.resolve())) == owned:
            continue
        if windows:
            try:
                entries = {p.name.casefold(): p for p in directory.iterdir()}
            except (FileNotFoundError, NotADirectoryError):
                continue
            for name in candidates:
                if any((path := entries.get(name + ext)) is not None and path.is_file() for ext in extensions):
                    occupied.add(name)
        else:
            for name in candidates:
                path = directory / name
                if path.is_file() and os.access(path, os.X_OK):
                    occupied.add(name)
    mapping, skipped = {}, []
    for name in names:
        if name in RESERVED:
            continue
        command = name
        if name in occupied:
            command += '-theme'
            if command in occupied or command in names or command in RESERVED:
                skipped.append(name)
                continue
        mapping[command] = name
    return dict(sorted(mapping.items())), skipped


if __name__ == '__main__':
    try:
        mapping, skipped = allocate(filter(None, sys.stdin.read().splitlines()), sys.argv[1])
        for command, target in mapping.items():
            print('generated', command, target, sep='\t')
        for target in skipped:
            print('skipped', target, target + '-theme', sep='\t')
    except (OSError, ValueError) as error:
        print('dots theme: cannot allocate commands: ' + str(error), file=sys.stderr)
        sys.exit(1)
