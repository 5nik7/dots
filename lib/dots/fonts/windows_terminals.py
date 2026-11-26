"""Resolve native terminal editions only when a font target requests them."""
import os
from pathlib import Path
import shutil
import subprocess
from app_paths import WT_EDITIONS


MINTTY = ('msys2-mintty', 'git-bash-mintty')
GROUP = 'all-terminals'


def output(command):
    try:
        result = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=5,
                                env=dict(os.environ, LC_ALL='C.UTF-8'))
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def mintty_home(library, target):
    if target == 'git-bash-mintty':
        git = shutil.which('git.exe')
        exec_path = Path(output([git, '--exec-path'])) if git else None
        if exec_path and exec_path.is_absolute() and any(
                (parent / 'usr/bin/mintty.exe').is_file() for parent in exec_path.parents):
            home = Path(os.environ.get('HOME') or library.home)
            if home.is_absolute() and home.is_dir():
                return home
    else:
        launcher = shutil.which('msys2.exe') or shutil.which('msys2_shell.cmd')
        roots = [Path(launcher).parent] if launcher else []
        mintty = shutil.which('mintty.exe')
        if mintty:
            roots.append(Path(mintty).parent.parent.parent)
        for root in roots:
            binary = root / 'usr/bin'
            if not (root / 'msys2_shell.cmd').is_file() or not (binary / 'mintty.exe').is_file():
                continue
            account = output([str(binary / 'getent.exe'), 'passwd', os.environ.get('USERNAME', '')])
            fields = account.split(':')
            if len(fields) == 7:
                home = Path(output([str(binary / 'cygpath.exe'), '-aw', fields[5]]))
                if home.is_absolute() and home.is_dir():
                    return home
    raise FileNotFoundError('installed ' + target + ' and its user home could not be located')


def host_path(library, target):
    if target in WT_EDITIONS:
        path = Path(os.environ['LOCALAPPDATA']) / WT_EDITIONS[target] / 'settings.json'
        if not path.is_file():
            raise FileNotFoundError(target + ' settings.json is absent')
        return path
    home = mintty_home(library, target)
    # Mintty reads later files with higher precedence, saving to ~/.minttyrc
    # when there is no per-user file. Never edit /etc/minttyrc.
    candidates = (home / '.minttyrc', home / '.config/mintty/config',
                  Path(os.environ['APPDATA']) / 'mintty/config')
    return next((path for path in candidates if path.exists() or path.is_symlink()), candidates[0])
