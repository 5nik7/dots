"""Project selection and explicit native shell handoff; no tmux/WSL bridge."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

from help_adapters import HelpArgumentParser
from interaction import SelectionEnded
from menu_projects import discover
from menus import Entry, Menu, add_arguments, choose
from resources import clean


def shell_command(*, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        executable = os.environ.get('DOTS_POWERSHELL') or shutil.which('pwsh.exe') or shutil.which('powershell.exe')
        if not executable or Path(executable).name.lower() not in ('pwsh.exe', 'powershell.exe'):
            raise ValueError('a native PowerShell executable is required')
        args = ['-NoLogo']
    else:
        executable = os.environ.get('SHELL') or shutil.which('bash')
        if not executable or Path(executable).name not in ('bash', 'zsh', 'fish', 'nu', 'xonsh', 'sh'):
            raise ValueError('a supported native interactive shell is required')
        args = ['-i']
    if not Path(executable).is_absolute() or not Path(executable).is_file():
        raise ValueError('native shell must resolve to an existing absolute executable')
    return [executable, *args]


def handoff(project):
    # The directory is a CreateProcess/POSIX cwd, never command source or an
    # argument to a shell parser. Returning from the child restores this menu.
    root = project.root
    if not root.is_absolute() or not root.is_dir() or root.resolve() != root:
        raise ValueError('selected project changed or is unavailable')
    return subprocess.run(shell_command(), cwd=root).returncode


def main(argv=None):
    parser = HelpArgumentParser(prog='dots menu projects', description='Choose a project and open its native shell')
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        projects = discover()
        rows = {str(index): project for index, project in enumerate(projects, 1)}
        menu = Menu('projects', 'Projects', tuple(Entry(key, p.label, str(p.root)) for key, p in rows.items()))
        selected = choose(menu, mode=args.menu_mode, query=args.query,
                          header='Enter: open native shell  Esc: cancel')
        return handoff(rows[selected.id]) if selected else 0
    except SelectionEnded as error:
        return error.status
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError) as error:
        print('dots menu projects: ' + clean(str(error)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
