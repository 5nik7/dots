#!/usr/bin/env python3
"""Shared controllers for existing standalone utilities; no extension discovery."""
import os
from pathlib import Path
import sys

from utility_commands import NAMES, USAGE, canonical
from utility_runtime import ToolExit


def help_text(name):
    if name == 'linked':
        source = (Path(__file__).resolve().parents[2] / 'scripts/linked').read_text(encoding='utf-8')
        return source.split("cat <<'USAGE_EOF'\n", 1)[1].split('\nUSAGE_EOF', 1)[0] + '\n'
    notes = {
        'fzfd': 'Enter selects; Ctrl-T switches files/directories; Esc cancels. Requires native fd and fzf.\n',
        'fzg': 'First query word is the ripgrep pattern; remaining words filter matches. Ctrl-R refreshes the search. Enter opens the editor; Esc cancels.\n',
        'fzrg': 'Ctrl-R refreshes ripgrep; Alt-Enter filters the current results. Enter opens the editor; Esc cancels.\n',
        'fzrg3': 'Ctrl-R refreshes ripgrep. Enter opens the editor; Esc cancels.\n',
        'fzfig': 'Select a native FIGlet font, then print and copy the rendered text. --pipe runs one literal executable argv after selection; shell pipelines are unsupported.\n',
        'fzpyfig': 'Select a native pyfiglet font and print the rendered text.\n',
        'fzenv': 'Select an environment variable. Sensitive values remain redacted.\n',
        'cht': 'Native query/shell with explicit copy, mode, id and hush commands. Settings writes are journaled. Shell configuration expressions are not executed. Standalone installation, self-update and stealth monitoring need separate native adapters.\n',
        'www': 'Open HTTPS in the native browser. With no argument: Git origin, WWW, then Google.\n',
    }
    return 'Usage: ' + USAGE[name] + '\n' + notes.get(name, '')


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or not canonical(arguments[0]):
        raise ValueError('unknown standalone utility')
    name = canonical(arguments.pop(0))
    if name != 'fzopt' and arguments and arguments[0] in ('--help', '-h'):
        from help_presentation import colorize_help
        print(colorize_help(help_text(name), prog=name), end='')
        return 0
    try:
        if name == 'linked' and arguments and arguments[0].split('=')[0] == '--completion':
            shell = arguments[0].partition('=')[2] if '=' in arguments[0] else (arguments[1] if len(arguments) == 2 else '')
            if shell not in ('bash', 'zsh'): raise ValueError('completion shell must be bash or zsh')
            marker = shell.upper() + '_COMPLETION_EOF'
            source = (Path(__file__).resolve().parents[2] / 'scripts/linked').read_text(encoding='utf-8')
            print(source.split("cat <<'" + marker + "'\n", 1)[1].split('\n' + marker, 1)[0])
            return 0
        if name in ('linked', 'lnkd', 'pathout', 'dirout', 'isdir', 'isfile'):
            from utility_paths import path_command
            return path_command(name, arguments)
        if name == 'cpwd':
            from utility_paths import cwd
            from clipboard import copy
            copy(cwd())
            return 0
        if name == 'fzopt':
            from utility_options import main as options
            return options(arguments)
        if name.startswith('fz'):
            from utility_picker import main as picker
            return picker(name, arguments)
        from utility_web import main as web
        return web(name, arguments)
    except ToolExit as error:
        if str(error): print(name + ': ' + str(error), file=sys.stderr)
        return error.code
    except FileNotFoundError as error:
        print(name + ': ' + str(error), file=sys.stderr)
        return 1
    except ValueError as error:
        print(name + ': ' + str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except OSError as error:
        print('utility: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
