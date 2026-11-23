"""Declarative built-in plugin installation assets; no plugin code is loaded."""
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


def relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or any(ord(char) < 32 for char in value)):
        raise ValueError('invalid plugin asset path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('plugin assets must stay within their plugin')
    return value


def git_environment(*, local=False):
    env = {key: value for key, value in os.environ.items()
           if key not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE')}
    if local:
        env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    return env


def local_git(directory, *args):
    return subprocess.run(['git', '-C', str(directory), *args], check=True, capture_output=True,
                          env=git_environment(local=True)).stdout


def recorded_submodule(root, path):
    """Identify the single registered stage-zero gitlink an update would use."""
    modules = root/'.gitmodules'
    source = root/path
    if (modules.is_symlink() or not modules.is_file() or source.resolve() != source
            or not source.is_relative_to(root)):
        raise ValueError('invalid optional source registration: ' + path)
    try:
        entry = local_git(root, 'ls-files', '--full-name', '--stage', '-z', '--', ':(literal)' + path)
        match = re.fullmatch(rb'160000 ([0-9a-f]{40}|[0-9a-f]{64}) 0\t' + re.escape(os.fsencode(path)) + b'\0', entry)
        if not match:
            raise ValueError('expected a single recorded gitlink: ' + path)
        keys = local_git(root, 'config', '--no-includes', '--file', '.gitmodules', '--null',
                         '--name-only', '--fixed-value', '--get-regexp', r'^submodule\..*\.path$', path)
        if keys.count(b'\0') != 1:
            raise ValueError('ambiguous optional source registration: ' + path)
        values = local_git(root, 'config', '--no-includes', '--file', '.gitmodules', '--null',
                           '--get-all', os.fsdecode(keys[:-1]))
        if values != os.fsencode(path) + b'\0':
            raise ValueError('ambiguous optional source registration: ' + path)
        return match[1].decode('ascii')
    except subprocess.CalledProcessError as error:
        raise ValueError('cannot verify optional source registration: ' + path) from error


def submodule_worktree(root, source, pin):
    """Accept a checkout of the recorded source or its initialized Git module."""
    marker = source / '.git'
    if source.is_symlink() or marker.is_symlink() or not (marker.is_file() or marker.is_dir()):
        return False
    try:
        top = local_git(source, 'rev-parse', '--show-toplevel').removesuffix(b'\n')
        if Path(os.fsdecode(top)).resolve() != source:
            return False
        # An independent offline clone can supply the recorded object. A
        # normal absorbed submodule can predate a newly recorded parent pin.
        try:
            local_git(source, 'cat-file', '-e', pin + '^{commit}')
        except subprocess.CalledProcessError:
            if not marker.is_file():
                return False
            gitdir = local_git(source, 'rev-parse', '--absolute-git-dir').removesuffix(b'\n')
            common = local_git(root, 'rev-parse', '--git-common-dir').removesuffix(b'\n')
            return Path(os.fsdecode(gitdir)).is_relative_to((root/os.fsdecode(common)).resolve()/'modules')
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def submodule_initialized(source):
    if not (source/'.git').exists():
        return False
    root = source.parent.parent
    try:
        pin = recorded_submodule(root, source.relative_to(root).as_posix())
        return submodule_worktree(root, source, pin)
    except (ValueError, OSError):
        return False


def definitions(root):
    manifest = Path(root) / 'plugins/manifest.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not isinstance(data.get('plugins'), dict):
        raise ValueError('unsupported plugin manifest')
    for name, row in data['plugins'].items():
        if not re.fullmatch('[a-z][a-z0-9-]*', name) or not isinstance(row, dict):
            raise ValueError('invalid plugin definition')
        source = row.get('source', {})
        if 'submodule' in source:
            if relative(source['submodule']) != 'plugins/' + name:
                raise ValueError('plugin submodule must match its checkout path')
            if not isinstance(row.get('platforms'), list) or not row['platforms']:
                raise ValueError('submodule plugin requires platform declarations')
        for key in ('runtime', 'manual'):
            relative(row[key])
        if set(row['completions']) != {'bash', 'zsh', 'fish'}:
            raise ValueError('plugin completion assets are incomplete')
        for value in row['completions'].values():
            relative(value)
    return data['plugins']
