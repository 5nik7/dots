"""Goal text input with shared palette policy and private terminal handoff."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from interaction import SelectionEnded, terminal
from menu_tmux import request_file, read_request, terminal_result
from resources import clean


def input_text(initial, title, multiline=False):
    if not terminal():
        raise ValueError('goal input requires a terminal')
    # Existing goal text is data. Never inject controls into Gum/readline; keep
    # the exact original when the displayed editable value is accepted as-is.
    editable = '\n'.join(clean(line) for line in initial.split('\n')) if multiline else clean(initial)
    def accepted(value):
        return initial if value == editable else value
    if shutil.which('gum') and os.environ.get('TERM') != 'dumb':
        from files.catalog import Presentation
        from resources import Resources, read_data
        env = dict(os.environ)
        ui = Presentation(detail_indent=2)
        if ui.color:
            env.pop('NO_COLOR', None)
            for line in read_data(Resources().root / 'gum_env.sh').splitlines():
                match = re.fullmatch(r"export (GUM_[A-Z_]+)='(#[a-fA-F0-9]{6})'", line)
                if match: env[match[1]] = match[2]
        else:
            env['NO_COLOR'] = '1'
        flags = ['gum', 'write' if multiline else 'input', '--char-limit=0']
        if not ui.icons: flags += ['--no-show-help', '--prompt=> ']
        result = subprocess.run([*flags, '--header=' + clean(title), '--value=' + editable],
                                stdout=subprocess.PIPE, text=True, env=env)
        if result.returncode:
            if result.returncode in (130, -2): raise SelectionEnded(130)
            raise ValueError('goal input cancelled or failed; nothing was changed')
        return accepted(result.stdout.removesuffix('\n'))
    print(clean(title) + '\nCtrl-C: cancel')
    if multiline:
        print('Current value:\n' + '\n'.join(clean(line) for line in initial.splitlines()))
        print('Enter replacement lines; a single dot finishes, /keep keeps the current value.')
        lines = []
        while True:
            value = input('> ')
            if value == '/keep' and not lines: return initial
            if value == '.': return accepted('\n'.join(lines))
            if value == '\x1b': raise SelectionEnded(130)
            lines.append(value)
    try:
        import readline
    except ImportError:
        print('Current: ' + clean(initial))
        value = input('Value (/keep keeps current): ')
        return initial if value == '/keep' else accepted(value)
    readline.set_startup_hook(lambda: readline.insert_text(editable))
    try:
        value = input('Value: ')
        if '\x1b' in value: raise SelectionEnded(130)
        return accepted(value)
    finally:
        readline.set_startup_hook(None)


def prompt(initial, title, context=None, multiline=False):
    if context is None:
        return input_text(initial, title, multiline)
    with request_file(dict(schema=1, initial=initial, title=title, multiline=multiline)) as path:
        columns, lines = context.verify()
        code = context.popup([sys.executable, '-B', str(Path(__file__).resolve()), str(path)],
                             size=(max(1, min(80, columns - 2)), max(1, min(18 if multiline else 9, lines - 2))))
        code = terminal_result(path, code)
        if code:
            if code == 130: raise SelectionEnded(130)
            raise ValueError('goal input failed; nothing was changed')
        data = read_request(path.with_suffix('.answer'))
        if not isinstance(data.get('value'), str): raise ValueError('invalid goal input response')
        return data['value']


if __name__ == '__main__':
    path = Path(sys.argv[1])
    code = 0
    try:
        data = read_request(path)
        value = input_text(data['initial'], data['title'], data['multiline'])
        answer = path.with_suffix('.answer')
        with answer.open('x', encoding='utf-8') as stream:
            if os.name != 'nt': os.fchmod(stream.fileno(), 0o600)
            json.dump(dict(schema=1, value=value), stream)
    except (SelectionEnded, KeyboardInterrupt, EOFError):
        code = 130
    except (ValueError, OSError) as error:
        print(clean(str(error)), file=sys.stderr)
        code = 1
    path.with_suffix('.status').write_text(str(code), encoding='ascii')
    sys.exit(code)
