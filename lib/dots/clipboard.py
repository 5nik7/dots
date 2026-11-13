"""System clipboard adapters and the standalone cpy/pst text interface."""
import json
import os
import shutil
import subprocess
import sys

from platform_info import detect


TIMEOUT = 8


def _provider(operation):
    platform = detect()['platform']
    writing = operation == 'write'
    if platform == 'termux':
        choices = [('termux-clipboard-set' if writing else 'termux-clipboard-get', [])]
        hint = 'install termux-api and the compatible Termux:API Android app'
    elif platform in ('windows', 'wsl'):
        script = ("$ErrorActionPreference = 'Stop'; "
                  '[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false); '
                  '[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); ')
        script += ('Set-Clipboard -Value ([Console]::In.ReadToEnd())' if writing else
                   '[Console]::Write([string](Get-Clipboard -Raw))')
        shells = ('pwsh.exe', 'powershell.exe') if platform == 'wsl' else ('pwsh', 'powershell')
        choices = [(shell, ['-NoLogo', '-NoProfile', '-NonInteractive', '-STA', '-Command', script])
                   for shell in shells]
        # No --crlf/--lf: preserve the text's existing line endings.
        choices.append(('win32yank.exe', ['-i' if writing else '-o']))
        hint = 'make Windows PowerShell or win32yank.exe available on PATH'
        if platform == 'wsl':
            hint += ' with Windows interop enabled'
    else:
        choices = []
        if os.environ.get('WAYLAND_DISPLAY'):
            choices.append(('wl-copy', ['--type', 'text/plain;charset=utf-8']) if writing else
                           ('wl-paste', ['--no-newline', '--type', 'text']))
        if os.environ.get('DISPLAY'):
            choices += [('xclip', ['-selection', 'clipboard', '-in' if writing else '-out']),
                        ('xsel', ['--clipboard', '--input' if writing else '--output'])]
        hint = 'use a Wayland session with wl-clipboard or an X11 session with xclip/xsel'
    for tool, arguments in choices:
        executable = shutil.which(tool)
        if executable:
            return [executable, *arguments]
    raise ValueError('Clipboard unavailable; ' + hint)


def _run(operation, data=None):
    command = _provider(operation)
    tool = os.path.basename(command[0])
    try:
        result = subprocess.run(command, input=data,
                                stdin=subprocess.DEVNULL if data is None else None,
                                stdout=subprocess.PIPE if operation == 'read' else subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ValueError(f'Clipboard {operation} timed out ({tool})') from None
    except (OSError, subprocess.SubprocessError):
        raise ValueError(f'Clipboard {operation} failed ({tool}); check the clipboard service') from None
    if result.returncode:
        raise ValueError(f'Clipboard {operation} failed ({tool}, exit {result.returncode}); '
                         'check the clipboard service')
    return result.stdout if operation == 'read' else None


def copy(text):
    """Copy literal UTF-8 text; retained API for Todo and Fonts."""
    _run('write', text.encode('utf-8'))
    _record_copy(text, 'dots')


def _record_copy(text, source):
    try:
        from clipboard_history import record_copy
    except ImportError:
        return  # Standalone copies of the adapter need no history subsystem.
    record_copy(text, source)


def paste():
    """Read clipboard text as bytes, without newline conversion."""
    return _run('read')


class UsageError(ValueError):
    pass


def _help(command):
    if command == 'cpy':
        return ('Usage: cpy [--] [TEXT...]\n\n'
                'Copy text to the system clipboard.\n'
                'With no text, read stdin until EOF.\n'
                'Join arguments with spaces.\n'
                'No newline is added.\n\n'
                '  printf hello | cpy\n'
                '  cpy "some text"\n'
                '  cpy < file.txt\n'
                '  cpy -- -literal\n\n'
                '  -h, --help  Show this help.\n')
    return ('Usage: pst\n\n'
            'Print system clipboard text unchanged.\n'
            'Output can be piped or redirected.\n\n'
            '  pst > file.txt\n\n'
            '  -h, --help  Show this help.\n')


def _execute(command, arguments, read_input):
    operands = []
    literal = False
    for argument in arguments:
        if not literal and argument == '--':
            literal = True
        elif not literal and argument in ('-h', '--help'):
            from help_presentation import colorize_help
            return colorize_help(_help(command), prog=command).encode('utf-8')
        elif not literal and argument.startswith('-'):
            raise UsageError('unknown option; use --help or -- before literal text')
        else:
            operands.append(argument)
    if command == 'pst':
        if operands:
            raise UsageError('expected no text arguments; use pst --help')
        return paste()
    data = ' '.join(operands).encode('utf-8') if operands else read_input()
    _run('write', data)
    try:
        _record_copy(data.decode('utf-8'), 'cpy')
    except UnicodeError:
        pass  # Retain the existing provider byte contract.
    return b''


def main(arguments=None):
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    command = 'clipboard'
    try:
        if arguments == ['--powershell']:
            # A UTF-8 stdin request avoids native argv quoting/length differences.
            try:
                request = json.loads(sys.stdin.buffer.read().decode('utf-8'))
            except (UnicodeError, ValueError):
                raise UsageError('invalid PowerShell clipboard request') from None
            if (not isinstance(request, dict) or request.get('command') not in ('cpy', 'pst')
                    or not isinstance(request.get('arguments'), list)
                    or not all(isinstance(value, str) for value in request['arguments'])
                    or not isinstance(request.get('input'), str)):
                raise UsageError('invalid PowerShell clipboard request')
            command, arguments = request['command'], request['arguments']
            read_input = lambda: request['input'].encode('utf-8')
        else:
            if not arguments or arguments[0] not in ('cpy', 'pst'):
                raise UsageError('invoke cpy or pst')
            command = arguments.pop(0)
            read_input = sys.stdin.buffer.read
        output = _execute(command, arguments, read_input)
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
        return 0
    except UsageError as error:
        print(f'{command}: {error}', file=sys.stderr)
        return 2
    except (ValueError, OSError) as error:
        if isinstance(error, BrokenPipeError):
            return 1
        # Provider output and clipboard contents never enter diagnostics.
        message = str(error) if isinstance(error, ValueError) else 'could not read or write the text stream'
        print(f'{command}: {message}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
