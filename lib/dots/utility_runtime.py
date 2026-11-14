"""Small native process boundaries shared by standalone utility adapters."""
import os
import shlex
import shutil
import subprocess


class ToolExit(Exception):
    def __init__(self, code, message=''):
        super().__init__(message)
        self.code = code


def require(name):
    path = shutil.which(name + '.exe') if os.name == 'nt' else None
    if os.name == 'nt' and not path: path = shutil.which(name + '.com')
    path = path or shutil.which(name)
    if not path:
        raise ToolExit(127, name + ' is unavailable')
    if os.name == 'nt' and os.path.splitext(path)[1].casefold() not in ('.exe', '.com'):
        raise ToolExit(3, name + ' resolves to a shell script; select its native executable to preserve literal arguments')
    return path


def words(value):
    result = shlex.split(value, posix=os.name != 'nt')
    if os.name == 'nt':
        result = [part[1:-1] if len(part) > 1 and part[0] == part[-1] and part[0] in ('"', "'") else part for part in result]
    if not result: raise ValueError('expected an executable and literal arguments')
    return result


def capture(name, arguments=(), *, data=None, allowed=(0,)):
    try:
        result = subprocess.run([require(name), *arguments], input=data, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise ToolExit(124, name + ' timed out') from None
    if result.returncode not in allowed:
        raise ToolExit(result.returncode, name + ' failed (exit ' + str(result.returncode) + ')')
    return result.stdout


def execute(arguments, *, data=None):
    command = [require(arguments[0]), *arguments[1:]]
    return subprocess.run(command, input=data).returncode
