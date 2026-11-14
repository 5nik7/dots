"""Native standalone FZF workflows with inert rows and post-selection actions."""
from contextlib import contextmanager
import base64
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from interaction import RichSelector, SelectionEnded, SelectionEvent, rich_fzf_available
from resources import clean
from utility_runtime import ToolExit, capture, execute, require, words


def text(value):
    if 'text' in value: return value['text']
    return os.fsdecode(base64.b64decode(value['bytes']))


def executable_rows():
    names = set()
    suffixes = {value.casefold() for value in os.environ.get('PATHEXT', '.EXE;.COM;.CMD;.BAT').split(';')} | {'.ps1'}
    for directory in os.get_exec_path():
        try:
            for path in Path(directory).iterdir():
                if path.is_file() and (path.suffix.casefold() in suffixes if os.name == 'nt' else os.access(path, os.X_OK)):
                    names.add(path.name)
        except OSError:
            continue
    return [dict(label=name, value=name, kind='text', preview=name) for name in sorted(names, key=str.casefold)]


def environment_rows():
    from profiles import SENSITIVE
    rows = []
    for name, value in sorted(os.environ.items()):
        shown = '<redacted>' if value and SENSITIVE.search(name) else value
        rows.append(dict(label=name, value=name+'='+shown, kind='text', preview=name+'\n'+shown))
    return rows


def file_rows(directories=False):
    output = capture('fd', ['--type', 'directory' if directories else 'file', '--print0'])
    return [dict(label=os.fsdecode(value), value=os.fsdecode(value), kind='file', path=os.path.abspath(os.fsdecode(value)))
            for value in output.split(b'\0') if value]


def search_rows(pattern):
    if not pattern: return []
    output = capture('rg', ['--json', '--smart-case', '-e', pattern, '--', '.'], allowed=(0, 1))
    rows = []
    for line in output.splitlines():
        record = json.loads(line)
        if record.get('type') != 'match': continue
        data = record['data']; path = text(data['path']); number = data['line_number']
        content = text(data['lines']).rstrip('\r\n')
        rows.append(dict(label=path+':'+str(number)+':'+content, value=path, path=os.path.abspath(path),
                         line=number, kind='file'))
    return rows


def font_rows(kind, content):
    if kind == 'fzpyfig':
        fonts = capture('pyfiglet', ['-l']).decode('utf-8').split()
    else:
        directory = capture('figlet', ['-I2']).decode('utf-8').strip()
        fonts = [path.stem for path in Path(directory).glob('*.flf') if path.is_file()]
    return [dict(label=font, value=font, kind='font', renderer='pyfiglet' if kind == 'fzpyfig' else 'figlet', text=content)
            for font in sorted(set(fonts))]


def render_font(row):
    # Neither the selected font nor the supplied text enters shell code.
    return capture(row['renderer'], ['-f', row['value']], data=row['text'].encode('utf-8'))


def preview_text(row):
    if row['kind'] == 'text': return row['preview']
    if row['kind'] == 'font': return render_font(row).decode('utf-8', errors='replace')
    path = Path(row['path'])
    if path.is_dir():
        return '\n'.join(sorted(child.name + (os.sep if child.is_dir() else '') for child in path.iterdir())[:200])
    with path.open('rb') as stream: data = stream.read(65536)
    if b'\0' in data: return 'Binary file; preview unavailable.'
    lines = data.decode('utf-8', errors='replace').splitlines()
    focus = max(1, int(row.get('line', 1))); start = max(0, focus-20)
    return '\n'.join(('> ' if index == focus else '  ') + str(index) + '  ' + line
                     for index, line in enumerate(lines[start:start+200], start+1))


@contextmanager
def preview_snapshot(rows):
    with tempfile.TemporaryDirectory(prefix='dots-utility-picker-') as directory:
        snapshot = Path(directory)/'items.json'
        snapshot.write_text(json.dumps(rows, ensure_ascii=True), encoding='utf-8')
        snapshot.chmod(0o600)
        prefix = ('& $env:DOTS_UTILITY_PYTHON -B $env:DOTS_UTILITY_PREVIEW preview $env:DOTS_UTILITY_SNAPSHOT {1}'
                  if os.name == 'nt' else '"$DOTS_UTILITY_PYTHON" -B "$DOTS_UTILITY_PREVIEW" preview "$DOTS_UTILITY_SNAPSHOT" {1}')
        yield (prefix, '', dict(DOTS_UTILITY_PYTHON=sys.executable, DOTS_UTILITY_PREVIEW=str(Path(__file__).resolve()),
                              DOTS_UTILITY_SNAPSHOT=str(snapshot), DOTS_PROGRESS='never'))


def pick(name, rows, *, query='', navigation=None, events=None, disabled=False, header=None):
    require('fzf')
    if not rich_fzf_available(): raise ToolExit(3, 'native FZF preview support is unavailable')
    from files.catalog import Presentation
    from files.picker import fzf_colors
    ui = Presentation()
    if header is None:
        header = ('Enter: print/copy  Esc: cancel' if name == 'fzfig' else
                  'Enter: print  Esc: cancel' if name == 'fzpyfig' else 'Enter: select  Esc: cancel')
    with preview_snapshot(rows) as preview:
        selected = RichSelector(backend='fzf').fzf(name, [clean(row['label']) for row in rows], False,
            preview, ui.color, ui.icons, fzf_colors(ui), query=query, navigation=navigation,
            navigation_keys=events, disabled=disabled, header=header)
    if not selected: raise SelectionEnded(130)
    return rows[selected[0]]


def edit_match(row):
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'vim'
    command = words(editor)
    basename = Path(command[0]).stem.casefold()
    if basename in ('vi', 'vim', 'nvim', 'gvim', 'nano'):
        command += ['+' + str(row['line']), '--', row['path']]
    elif basename in ('code', 'code-insiders'):
        command += ['--goto', row['path']+':'+str(row['line'])]
    else:
        command += [row['path']]
    return execute(command)


def search(name, arguments):
    query = ' '.join(arguments); fuzzy = False
    while True:
        pattern, separator, filter_query = query.partition(' ') if name == 'fzg' else (query, '', '')
        rows = search_rows(pattern)
        navigation = {'query': filter_query if name == 'fzg' else query}
        events = {'ctrl-r': 'refresh'}
        if name == 'fzrg': events['alt-enter'] = 'fuzzy'
        try:
            row = pick(name, rows, query=navigation['query'], navigation=navigation, events=events,
                       disabled=not (fuzzy or name == 'fzg'),
                       header='Enter: open  Esc: cancel\n' +
                              ('Ctrl-R: search PATTERN [FILTER]' if name == 'fzg' else 'Ctrl-R: refresh search') +
                              ('\nAlt-Enter: fuzzy filter' if name == 'fzrg' else ''))
            return edit_match(row)
        except SelectionEvent as event:
            if event.action == 'fuzzy':
                fuzzy = True
                # Keep the current ripgrep snapshot while changing only its
                # fuzzy query; return to a new ripgrep scan with Ctrl-R.
                navigation = {'query': ''}
                try:
                    row = pick(name, rows, navigation=navigation, events={'ctrl-r': 'refresh'},
                               header='Enter: open  Esc: cancel\nCtrl-R: new search')
                    return edit_match(row)
                except SelectionEvent:
                    query = navigation['query']; fuzzy = False
            else:
                query = navigation['query']


def main(name, arguments):
    try:
        if name in ('fzg', 'fzrg', 'fzrg3'): return search(name, arguments)
        if name == 'fzfd':
            directories = False; navigation = {'query': ''}
            while True:
                try:
                    selected = pick('Directories' if directories else 'Files', file_rows(directories),
                                    query=navigation['query'], navigation=navigation, events={'ctrl-t': 'toggle'},
                                    header='Enter: select  Esc: cancel\nCtrl-T: files/directories')
                    print(selected['value']); return 0
                except SelectionEvent:
                    directories = not directories
        if name in ('fzfig', 'fzpyfig'):
            arguments = list(arguments); pipe = None
            while arguments and arguments[0] in ('-p', '--pipe') and name == 'fzfig':
                if len(arguments) < 2: raise ValueError('--pipe requires an executable and literal arguments')
                pipe = words(arguments[1]); del arguments[:2]
                if any(value in ('|', '||', '&&', ';', '>', '<') for value in pipe):
                    raise ValueError('--pipe accepts one executable and literal argv, not a shell program')
            if arguments and arguments[0] == '--': arguments.pop(0)
            content = (' '.join(arguments) or 'test') if name == 'fzfig' else (arguments[0] if arguments else '')
            row = pick(name, font_rows(name, content))
            output = render_font(row)
            if pipe: output = capture(pipe[0], pipe[1:], data=output)
            if name == 'fzfig' and output:
                from clipboard import copy
                copy(output.decode('utf-8'))
            sys.stdout.buffer.write(output); sys.stdout.buffer.flush()
            return 0
        rows = executable_rows() if name == 'fzcmd' else environment_rows()
        if not rows: raise ToolExit(1, 'no choices available')
        selected = pick(name, rows, query=arguments[0] if name == 'fzenv' and arguments else '')
        print(selected['value'])
        return 0
    except SelectionEnded as error:
        return error.status


def preview_main(arguments):
    if len(arguments) != 3 or arguments[0] != 'preview' or not re.fullmatch(r'0|[1-9][0-9]*', arguments[2]):
        raise ValueError('invalid private utility preview')
    rows = json.loads(Path(arguments[1]).read_text(encoding='utf-8'))
    index = int(arguments[2])
    if index >= len(rows): raise ValueError('invalid preview identity')
    # Preserve line breaks while neutralizing terminal controls in inspected data.
    print('\n'.join(clean(line) for line in preview_text(rows[index]).splitlines()))


if __name__ == '__main__':
    try: preview_main(sys.argv[1:])
    except (ValueError, OSError, ToolExit) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
