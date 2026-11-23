"""Bundled application boundary and inert completion; no backend discovery."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ('blastoff', 'pkgs')


def run(root, family, arguments):
    if family not in FAMILIES:
        raise ValueError('unknown bundled application')
    entry = Path(root) / 'plugins' / ('blastoff/lib/blastoff.py' if family == 'blastoff' else 'pkgs/main.py')
    runtime = (os.environ.get('BLASTOFF_PYTHON') or sys.executable) if family == 'blastoff' else sys.executable
    if not shutil.which(runtime):
        print(f'{family}: Python runtime unavailable: {runtime}', file=sys.stderr)
        return 3
    if os.name == 'nt' and Path(runtime).suffix.lower() in ('.cmd', '.bat', '.ps1'):
        print(f'{family}: Python runtime must be a native executable: {runtime}', file=sys.stderr)
        return 3
    if family == 'blastoff' and os.environ.get('DOTS_POWERSHELL'):
        # Preserve Blastoff's native aliases, host check and picker-shell context.
        envelope = dict(version=1, host=os.name, shell=os.environ['DOTS_POWERSHELL'], argv=list(arguments))
        arguments = ['--_powershell-argv-v1', base64.b64encode(json.dumps(envelope).encode()).decode('ascii')]
    command = [runtime, '-B', *(['-I'] if family == 'blastoff' else []), str(entry), *arguments]
    status = subprocess.call(command)
    return status if status >= 0 else 128 - status


def run_git_it(root, args, directories=None):
    """Use the registered checkout while preserving the caller's directory and streams."""
    from plugin_paths import submodule_initialized
    source = Path(root) / 'plugins/git-it'
    app = source / 'git-it'
    if os.name != 'nt' and submodule_initialized(source) and not app.is_symlink() and app.is_file() and os.access(app, os.X_OK):
        os.execve(app, [str(app), *args], dict(os.environ, DOTS=str(root)))
    options = args[:args.index('--')] if '--' in args else args
    if any(arg in ('--help', '-h') for arg in options):
        from cli import help_view
        from command_metadata import resolve, roots
        directories = directories or roots(root, [])
        stem, _, _ = resolve(directories, ['git', 'it', *args])
        return help_view(directories, stem.split('-'))
    if os.name == 'nt':
        print('dots git it requires Bash 5 on Termux, Linux or WSL.', file=sys.stderr)
    else:
        print('dots git it requires the registered git-it plugin. Run dots files install --with-source git-it to initialize it.', file=sys.stderr)
    return 3


def complete(root, words, *, display_types=False):
    """Use generated metadata only; completion never launches an application."""
    from completion_records import candidate_record
    if not words:
        return 0
    family, *tail = words
    if family == 'git-it':
        from command_metadata import read
        directory = Path(root)/'bin'
        paths = [directory/'dots-git-it', *directory.glob('dots-git-it-*')]
        rows = {path.name[5:]: read(path) for path in paths if path.is_file()}
    elif family in FAMILIES:
        rows = json.loads((Path(root)/'lib/dots/metadata/bundled-apps.json').read_text())
    else:
        return 0
    current = tail.pop() if tail else ''
    stem = family
    positionals = []
    expected = None
    literal = False
    directory = '.'
    previous_option = ''
    for index, word in enumerate(tail):
        if expected:
            if previous_option in ('-C', '--directory'):
                directory = word
            expected = None
            continue
        if word == '--':
            literal = True
            continue
        if not literal and stem == 'git-it' and word in ('-s', '--status', '--sync'):
            stem += '-sync' if word == '--sync' else '-status'
            continue
        flag, separator, value = word.partition('=')
        option = next((r for r in rows[stem]['option'] if flag in r[:2]), None)
        if not literal and option:
            previous_option = flag
            if flag in ('-C', '--directory') and separator: directory = value
            if option[2] != 'flag' and not separator: expected = option[2]
        elif not literal and word.startswith('-'):
            continue
        elif not literal and not positionals and stem+'-'+word in rows:
            stem += '-'+word
            if stem == 'git-it-submodule':
                command = [sys.executable, '-B', str(Path(root)/'lib/dots/git/submodule.py'), '--complete',
                           '-C', directory, *tail[index+1:], current]
                env = dict(os.environ, _DOTS_COMPLETION_DISPLAY_TYPES='1' if display_types else '0')
                result = subprocess.run(command, env=env, stdout=subprocess.PIPE, text=True)
                sys.stdout.write(result.stdout)
                return result.returncode
        else:
            positionals.append(word)
    suggestions = []
    def add(value, description='', role='value'):
        if value.startswith(current) and not any(c in value+description for c in '\t\r\n'):
            suggestions.append(candidate_record(value, description, role, display_types=display_types))
    def values(kind, prefix=''):
        if kind.startswith('choice:'):
            for value in kind[7:].split(','): add(prefix+value)
        elif kind in ('file', 'directory'): suggestions.append((kind, prefix, ''))
        elif kind == 'git-submodule':
            result = subprocess.run([sys.executable, '-B', str(Path(root)/'lib/dots/git/inspection.py'),
                                     '_complete', '-C', directory], capture_output=True, text=True)
            if result.returncode == 0:
                for path in result.stdout.splitlines(): add(path, 'Registered submodule')
    row = rows[stem]
    if expected:
        values(expected)
    elif not literal and current.startswith('-'):
        flag, sep, _ = current.partition('=')
        if sep:
            for long, short, kind, _ in row['option']:
                if flag == long: values(kind, flag+'=')
        else:
            for long, short, _, description in row['option']:
                add(long, description, 'option')
                if short: add(short, description, 'option')
    else:
        if not positionals and not literal:
            for key, child in rows.items():
                if key.startswith(stem+'-') and '-' not in key[len(stem)+1:]:
                    add(key[len(stem)+1:], child['summary'], 'command')
        for number, kind, description in row['argument']:
            if int(number) == len(positionals)+1: values(kind)
    for record in dict.fromkeys(suggestions):
        print('\t'.join(record))
    return 0


if __name__ == '__main__':
    if sys.argv[1:2] == ['--run-git-it']:
        sys.exit(run_git_it(ROOT, sys.argv[2:]))
    from completion_records import requested
    sys.exit(complete(ROOT, sys.argv[1:], display_types=requested()))
