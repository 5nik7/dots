"""Route group shortcuts and Git presentation options through their normal commands."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
COMMANDS = ('info', 'path', 'status', 'sync', 'publish', 'submodule', 'submodules', 'wiki', 'it')
VALUES = ('-C', '--directory', '--config', '--get', '-f', '--format', '--view', '--depth', '-m', '--message')


def dispatch(args, native):
    program = [sys.executable, '-B', str(ROOT/'lib/dots/cli.py')] if native else [str(ROOT/'bin/dots')]
    os.execvpe(program[0], [*program, *args], dict(os.environ, DOTS_GIT_OPTIONS_PARSED='1'))


def main(argv):
    native = argv[0] == 'native'
    words = iter(argv[1:])
    prefix, rest, literal = [], [], []
    cmd = None
    directory = os.environ.get('DOTS') or str(ROOT)
    selected_directory = False
    outermost = False
    for word in words:
        output = rest if cmd else prefix
        if word == '--':
            literal = [word, *words]
            break
        opt, equal, attached = word.partition('=')
        if opt in ('--no-color', '--no-progress') and not equal:
            os.environ['DOTS_COLOR' if opt == '--no-color' else 'DOTS_PROGRESS'] = 'never'
        elif opt == '--color':
            value = attached if equal else next(words, None)
            if value not in ('always', 'never', 'auto'):
                raise ValueError('--color requires auto, always or never')
            os.environ['DOTS_COLOR'] = value
        elif opt == '--outermost' and not equal:
            outermost = True
        elif opt in VALUES or (opt == '--remote' and cmd in (None, 'info', 'path')):
            value = attached if equal else next(words, None)
            if value is None:
                raise ValueError(opt + ' requires a value')
            if opt in ('-C', '--directory'):
                directory = value
                selected_directory = True
            else:
                output.extend((opt, value))
        elif not cmd and word in ('-s', '--status', '--sync', *COMMANDS):
            cmd = {'-s': 'status', '--status': 'status', '--sync': 'sync'}.get(word, word)
        elif not cmd and not word.startswith('-'):
            raise ValueError('unknown git command')
        else:
            output.append(word)
    if not cmd:
        from queries import is_field_query
        if is_field_query(prefix) or '--remote' in prefix or '--json' in prefix:
            cmd = 'info'
        elif all(arg in ('-h', '--help') for arg in prefix):
            dispatch(['help', 'git'], native)
        else:
            raise ValueError('choose a git command or field')
    if outermost:
        if cmd not in ('status', 'sync', 'publish'):
            raise ValueError('--outermost requires status, sync or publish')
        from queries import ancestry, inspection
        base = inspection.context(directory)
        directory = ancestry(base, base)['outermost']
        selected_directory = True
    if selected_directory:
        prefix.extend(('-C', directory))
    args = [*rest, *prefix, *literal]
    if cmd in ('info', 'path'):
        from queries import is_field_query
        if cmd == 'path' or is_field_query(args):
            program = Path(__file__).with_name('queries.py')
            os.execv(sys.executable, [sys.executable, '-B', str(program), cmd, *args])
    dispatch(['git', cmd, *args], native)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, OSError) as error:
        print('dots git: ' + str(error), file=sys.stderr)
        sys.exit(2)
