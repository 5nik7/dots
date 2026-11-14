"""Native Windows invocation for portable managers, without a command shell.

Batch launchers are not argv-safe. Recognize the installed npm/RubyGems layout
and invoke its native interpreter directly; unknown shell shims fail closed.
"""
import os
from pathlib import Path


def windows():
    return os.name == 'nt'


def executable(name, env=None):
    """Resolve an explicit path or PATH entry, never implicit current directory."""
    env = os.environ if env is None else env
    path = Path(name)
    suffixes = ('',) if path.suffix else ('.exe', '.com', '.cmd', '.bat', '.ps1', '')
    roots = (Path(),) if path.is_absolute() or path.parent != Path('.') else tuple(
        Path(part.strip('"')) for part in env.get('PATH', '').split(os.pathsep)
        if part.strip('"') and Path(part.strip('"')).is_absolute())
    for root in roots:
        for suffix in suffixes:
            candidate = root / (str(path) + suffix)
            if candidate.is_file():
                return candidate.resolve()
    return None


def argv(args, env=None):
    args = [str(arg) for arg in args]
    if not windows():
        return args
    from .common import Error
    if not args:
        raise Error('Empty native command')
    command = executable(args[0], env)
    if command is None:
        raise Error('Native executable is unavailable: ' + args[0])
    if command.suffix.lower() in ('.exe', '.com'):
        return [str(command), *args[1:]]
    name = command.stem.lower() if command.suffix else command.name.lower()
    if name == 'npm':
        script = command.parent / 'node_modules/npm/bin/npm-cli.js'
        interpreter = command.parent / 'node.exe'
        if not interpreter.is_file(): interpreter = executable('node.exe', env)
    elif name == 'gem':
        script = next((p for p in (command.parent / 'gem', command.parent / 'gem.rb')
                       if p.is_file()), None)
        interpreter = command.parent / 'ruby.exe'
        if not interpreter.is_file(): interpreter = executable('ruby.exe', env)
    else:
        raise Error('Native invocation refuses an unsupported shell launcher: ' + str(command))
    if script is None or not script.is_file() or interpreter is None:
        raise Error('Native ' + name + ' requires its installed script and native interpreter')
    return [str(interpreter), str(script), *args[1:]]


def available(name):
    from .common import Error
    try:
        argv([name])
        return True
    except (Error, OSError):
        return False
