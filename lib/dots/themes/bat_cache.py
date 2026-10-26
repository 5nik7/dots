#!/usr/bin/env python3
"""Snapshot custom Bat syntaxes for explicit, generation-local cache builds."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

FILE_LIMIT = 2 * 1024 * 1024
TOTAL_LIMIT = 64 * 1024 * 1024
ENTRY_LIMIT = 16384
DEPTH_LIMIT = 64


def resolve(path, strict=False):
    try:
        return path.resolve(strict=strict)
    except RuntimeError as error:
        raise ValueError('Cycle in Bat input links: ' + str(path)) from error


def regular_bytes(path):
    # NONBLOCK prevents a changed input from hanging on a FIFO before fstat.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Bat syntax input is not a regular file: ' + str(path))
        if info.st_size > FILE_LIMIT:
            raise ValueError('Bat syntax input exceeds 2 MiB: ' + str(path))
        data = stream.read(FILE_LIMIT + 1)
    if len(data) > FILE_LIMIT:
        raise ValueError('Bat syntax input exceeds 2 MiB: ' + str(path))
    return data


def syntax_files(root):
    files = []
    entries = total = 0

    def walk(directory, relative, ancestors):
        nonlocal entries, total
        resolved = resolve(directory, strict=True)
        if resolved in ancestors:
            raise ValueError('Cycle in Bat syntax directories: ' + str(directory))
        if len(ancestors) >= DEPTH_LIMIT:
            raise ValueError('Bat syntax directory depth exceeds limit')
        ancestors = ancestors | {resolved}
        # Ignore VCS internals when a syntax package is a checkout.
        with os.scandir(resolved) as listing:
            children = []
            for item in listing:
                entries += 1
                if entries > ENTRY_LIMIT:
                    raise ValueError('Bat syntax directory exceeds entry limit')
                if item.name != '.git':
                    children.append(item.name)
        for name in sorted(children):
            child, destination = resolved / name, relative / name
            info = child.stat()  # Broken links fail rather than silently losing syntax.
            if stat.S_ISDIR(info.st_mode):
                walk(child, destination, ancestors)
            elif child.suffix == '.sublime-syntax':
                data = regular_bytes(child)
                total += len(data)
                if total > TOTAL_LIMIT:
                    raise ValueError('Bat syntax inputs exceed 64 MiB')
                files.append((destination.as_posix(), data))

    if root.exists() or root.is_symlink():
        walk(root, Path(), set())
    return tuple(files)


@dataclass(frozen=True)
class Inputs:
    executable: str | None
    compiler: tuple = ()
    source: str = ''
    resolved_source: str = ''
    files: tuple = ()

    def fingerprint(self):
        payload = dict(executable=self.executable, compiler=self.compiler,
                       source=self.source, resolved_source=self.resolved_source,
                       files=[(name, hashlib.sha256(data).hexdigest()) for name, data in self.files])
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def inputs():
    executable = shutil.which('bat')
    if not executable:
        return Inputs(None)
    executable = str(resolve(Path(executable), strict=True))
    info = Path(executable).stat()
    # Resolve the real source before build() replaces BAT_CONFIG_DIR. A config
    # file override does not select Bat's asset directory, including on Windows.
    env = dict(os.environ, BAT_CONFIG_PATH=os.devnull, BAT_THEME='ansi')

    def query(option):
        result = subprocess.run([executable, option], env=env, capture_output=True, timeout=8)
        if result.returncode or not result.stdout or len(result.stdout) > 65536:
            raise ValueError('Could not query Bat ' + option)
        return result.stdout.decode('utf-8').removesuffix('\n').removesuffix('\r')

    version = query('--version')
    source = query('--config-dir')
    if not source or any(ord(c) < 32 for c in source):
        raise ValueError('Invalid Bat configuration directory')
    directory = Path(source).absolute()
    resolved = resolve(directory)
    if directory.exists() and not directory.is_dir():
        raise ValueError('Bat configuration path is not a directory: ' + str(directory))
    if directory.is_symlink() and not directory.exists():
        raise ValueError('Broken Bat configuration directory link: ' + str(directory))
    compiler = (version, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    return Inputs(executable, compiler, str(directory), str(resolved), syntax_files(directory / 'syntaxes'))


def build(directory, snapshot=None, expected=None):
    snapshot = inputs() if snapshot is None else snapshot
    if expected is not None and snapshot.fingerprint() != expected:
        raise ValueError('Bat syntax inputs changed during preparation; retry')
    if snapshot.executable is None:
        return False
    directory = Path(directory).absolute()
    theme = regular_bytes(directory / 'bat.tmTheme')
    source, cache = directory / 'bat-source', directory / 'bat-cache'
    (source / 'themes').mkdir(parents=True)
    cache.mkdir()
    (source / 'themes/Dots.tmTheme').write_bytes(theme)
    for name, data in snapshot.files:
        target = source / 'syntaxes' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    env = dict(os.environ, BAT_CONFIG_PATH=os.devnull, BAT_THEME='ansi',
               BAT_CONFIG_DIR=str(source), BAT_CACHE_PATH=str(cache))
    result = subprocess.run([snapshot.executable, 'cache', '--build', '--source', str(source), '--target', str(cache)],
                            cwd=source, env=env, capture_output=True, timeout=120)
    if result.returncode:
        # Bat errors may include source text. Keep diagnostics to the source path.
        raise ValueError('Bat cache build failed; check syntax definitions in ' + snapshot.source)
    if not all((cache / name).is_file() and (cache / name).stat().st_size
               for name in ('syntaxes.bin', 'themes.bin')):
        raise ValueError('Bat cache build did not produce complete assets')
    return True


def main(args):
    if args == ['fingerprint']:
        print(inputs().fingerprint())
    elif len(args) == 3 and args[0] == 'build':
        if not build(Path(args[1]), expected=args[2]):
            raise ValueError('Bat became unavailable during preparation')
    else:
        raise ValueError('Invalid Bat cache preparation operation')


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print('dots theme: ' + str(error), file=sys.stderr)
        sys.exit(1)
