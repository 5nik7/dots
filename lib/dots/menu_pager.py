"""Transient read-only output reader; never a public command or shell pipeline."""
import os
from dataclasses import dataclass
import re
import stat
import unicodedata
from contextlib import contextmanager, nullcontext
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading

from menu_tmux import read_request, request_file, status, terminal_result
from resources import clean


@contextmanager
def output_directory(parent=None):
    # A popup can disappear while a reader is open. Unwind the private spool on
    # normal terminal hangup/termination as well as explicit reader dismissal.
    handlers = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    try:
        if os.name != 'nt' and threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGHUP, signal.SIGTERM):
                handlers[signum] = signal.signal(signum, interrupted)
        # Hosted readers live under the caller-owned request directory, so the
        # caller also cleans them if tmux kills the terminal process outright.
        parent = parent or os.environ.get('DOTS_MENU_SPOOL_DIR') or None
        with tempfile.TemporaryDirectory(prefix='dots-output-', dir=parent) as directory:
            yield Path(directory)
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)


@dataclass(frozen=True)
class OutputResult:
    code: int
    reviewed: bool = False


def action_page(text, *, title, actions, frame, context=None, notice=''):
    """Opt-in FZF document actions; return an action, never a selected text line.

    Existing read-only less/FZF readers retain their own keys and return contract.
    Query/focused line survive an action such as copying and reopening this page.
    """
    from interaction import RichSelector, SelectionEvent, rich_fzf_available
    from files.catalog import Presentation
    from files.picker import fzf_colors
    from progress import permanent_output
    if not rich_fzf_available():
        raise ValueError('Brief actions require FZF; use todo brief ID to print the brief')
    labels = text.splitlines() or ['']
    ui = Presentation(terminal=True, detail_indent=2)
    wrapped = 'fzf-wrap' in tuple(backends())
    with output_directory() as directory:
        path = directory / 'document.txt'
        with private_file(path) as stream: stream.write(text.encode())
        size = context.verify() if context else shutil.get_terminal_size((80, 24))
        width, height = report_size(path, size, 'fzf-wrap' if wrapped else 'fzf')
        chunks = ['Enter: actions', 'Esc: back', *[key.replace('alt-', 'Alt-').upper().replace('ALT-', 'Alt-') + ': ' + label
                  for key, (_, label) in actions.items()], 'Ctrl-C: cancel']
        lines, row = [], ''
        for chunk in chunks:
            if row and len(row) + len(chunk) + 2 > max(18, width - 8):
                lines.append(row); row = ''
            row += ('  ' if row else '') + chunk
        if row: lines.append(row)
        if notice: lines.append(notice)
        header = '\n'.join(lines)
        with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
            try:
                selected = RichSelector(backend='fzf').fzf(title, labels, False, None,
                    ui.color, ui.icons, fzf_colors(ui), popup=f'center,{width},{height}' if context else False,
                    height=height, header=header, environment=environment, query=frame.get('query', ''),
                    navigation=frame, navigation_keys={'esc': 'back', **{k: v[0] for k, v in actions.items()}},
                    event_selection=True, focus_index=frame.get('line'), wrap=wrapped)
                frame['line'] = selected[0]
                return 'actions'
            except SelectionEvent as event:
                if event.index is not None: frame['line'] = event.index
                return event.action


def popup_bounds(size):
    columns, lines = size
    return max(1, min(columns, columns * 9 // 10)), max(1, min(lines, lines * 9 // 10))


# Count presentation only; never rewrite the captured report.
ANSI = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))')


def display_rows(path, width, *, limit, wrap=True):
    rows = 0
    with path.open('r', encoding='utf-8', errors='replace', newline=None) as stream:
        for line in stream:
            rows += 1
            if rows >= limit:
                return limit
            if not wrap:
                continue
            column = logical = 0
            for char in ANSI.sub('', line.rstrip('\n')):
                if char == '\b':
                    column = max(0, column - 1)
                    logical = max(0, logical - 1)
                    continue
                widths = ([1] * (8 - logical % 8) if char == '\t' else
                          [1, 1] if ord(char) < 32 or ord(char) == 127 else
                          [0 if unicodedata.combining(char) else
                           2 if unicodedata.east_asian_width(char) in 'WF' else 1])
                for cells in widths:
                    if cells and column + cells > width:
                        rows += 1
                        column = 0
                        if rows >= limit:
                            return limit
                    column += cells
                    logical += cells
    return rows


def report_size(path, size, backend='less'):
    width, maximum = popup_bounds(size)
    chrome = 3 if backend == 'less' else 6  # borders plus prompt/header/info
    # FZF reserves list gutters in addition to the popup border. Its wrap
    # indicator is disabled below so continuation lines use the same budget.
    text_width = width - (2 if backend == 'less' else 6)
    rows = display_rows(path, max(1, text_width), limit=maximum,
                        wrap=backend != 'fzf')
    return width, min(maximum, max(6, rows + chrome))


def backends():
    if shutil.which('less'):
        yield 'less'
    fzf = shutil.which('fzf')
    if fzf:
        try:
            probe = subprocess.run([fzf, '--help'], capture_output=True, timeout=5)
            wrapped = probe.returncode == 0 and b'--wrap' in (probe.stdout or b'')
        except (OSError, subprocess.SubprocessError):
            wrapped = False
        yield 'fzf-wrap' if wrapped else 'fzf'


def reader(path, *, backend=None, environment=None):
    if backend is None:
        for candidate in backends():
            try:
                return reader(path, backend=candidate, environment=environment)
            except (OSError, ValueError):
                continue
        raise ValueError('output reader unavailable or failed; install less or FZF')
    # less otherwise displays Nerd Font private-use glyphs as <U+...> text.
    environment = dict(os.environ if environment is None else environment)
    environment.update(LESS='', LESSOPEN='', LESSCLOSE='', LESSSECURE='1',
                       LESSSECURE_ALLOW='', LESSHISTFILE='-', LESSKEYIN=os.devnull,
                       LESSKEYIN_SYSTEM=os.devnull, LESSKEY='', LESSKEY_SYSTEM='',
                       LESSCHARSET='utf-8',
                       LESSUTFCHARDEF='E000-F8FF:p,F0000-FFFFD:p,100000-10FFFD:p')
    if backend == 'less':
        from less_style import published_environment
        environment = published_environment(environment)
        less = shutil.which('less', path=environment.get('PATH'))
        if not less:
            raise ValueError('less unavailable')
        # An open input file keeps private filenames out of less's status view.
        with path.open('rb') as content:
            result = subprocess.call([less, '-R', '--mouse', '-P',
                'PgUp/Dn scroll | / find | Back q'], stdin=content, env=environment)
        if result not in (0, 130, -2):
            raise ValueError('less failed')
        return result == 0
    if backend not in ('fzf', 'fzf-wrap'):
        raise ValueError('invalid output reader')
    fzf = shutil.which('fzf', path=environment.get('PATH'))
    if not fzf:
        raise ValueError('FZF unavailable')
    # The selected line is discarded. Report content never becomes a command.
    environment.update(FZF_DEFAULT_OPTS='', FZF_DEFAULT_OPTS_FILE='', FZF_DEFAULT_COMMAND='',
                       BASH_ENV='', ENV='')
    data = path.read_bytes().replace(b'\0', b'\\0').replace(b'\n', b'\0')
    result = subprocess.run([fzf, '--read0', '--print0', '--ansi', '--no-sort', '--no-multi',
        '--layout=reverse', '--no-height', '--prompt=Search output: ',
        '--header=Arrows/PgUp/PgDn: scroll  Home/End: first/last\nType: search  Enter/Esc: back',
        '--bind=esc:abort,ctrl-c:abort,home:first,end:last,pgup:page-up,pgdn:page-down',
        *(['--wrap', '--wrap-sign='] if backend == 'fzf-wrap' else [])],
        input=data, stdout=subprocess.DEVNULL, env=environment)
    if result.returncode not in (0, 1, 130, -2):
        raise ValueError('output reader failed')
    return result.returncode == 0


def show_report(path, context):
    for backend in backends():
        with request_file(dict(schema=1, file=str(path), backend=backend,
                               environment=dict(os.environ))) as request:
            result = context.popup([sys.executable, '-B', str(Path(__file__)), 'view', str(request)],
                                   size=report_size(path, context.verify(), backend))
            code = terminal_result(request, result)
            if code in (0, 130):
                return code == 0
    raise ValueError('output reader unavailable or failed; install less or FZF')


def private_file(path):
    stream = path.open('xb')
    if os.name != 'nt':
        os.fchmod(stream.fileno(), 0o600)
    return stream


def prepare(source, directory, *, title, code=0):
    path = directory / 'view.txt'
    with private_file(path) as stream:
        stream.write((clean(title) + '\n' + (f'Exit status: {code}\n' if code else '') + '\n').encode())
        with source.open('rb') as content:
            shutil.copyfileobj(content, stream)
        if source.stat().st_size == 0:
            stream.write(b'(No output.)\n')
    return path


def view(source, directory, *, title, code=0):
    return reader(prepare(source, directory, title=title, code=code))


def page_text(text, *, title='Dots output', code=0, context=None, defer=False):
    request = os.environ.get('DOTS_MENU_READER_HANDOFF') if defer else None
    if request:
        data = read_request(request)
        if data.get('defer_reader') is not True:
            raise ValueError('invalid document handoff')
        directory = Path(request).parent
        source = directory / 'document.txt'
        with private_file(source) as stream:
            stream.write(text.encode('utf-8') if isinstance(text, str) else text)
        prepare(source, directory, title=title, code=code)
        with private_file(directory / 'document.ready') as stream:
            stream.write(b'{"schema":1}')
        return
    with output_directory() as directory:
        source = directory / 'output.txt'
        with private_file(source) as stream:
            stream.write(text.encode('utf-8') if isinstance(text, str) else text)
        path = prepare(source, directory, title=title, code=code)
        return show_report(path, context) if context else reader(path)


def capture(argv, spool, *, cwd=None, environment=None, render_size=None):
    from menu_host import literal_argv
    columns, lines = render_size or shutil.get_terminal_size((80, 24))
    environment = dict(os.environ if environment is None else environment)
    terminal = sys.stdout.isatty() and environment.get('TERM', 'dumb') != 'dumb'
    color, icons = environment.get('DOTS_COLOR', 'auto'), environment.get('DOTS_ICONS', 'auto')
    environment.update(DOTS_COLOR='always' if color == 'always' or color == 'auto' and terminal and not environment.get('NO_COLOR') else 'never',
                       DOTS_ICONS='always' if icons == 'always' or icons == 'auto' and terminal else 'never',
                       DOTS_PROGRESS='never', DOTS_MENU_CAPTURE='1',
                       COLUMNS=str(columns), LINES=str(lines))
    source = spool / 'output.txt'
    with private_file(source) as stream:
        try:
            code = status(subprocess.call(literal_argv(argv), cwd=cwd, env=environment,
                          stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT))
        except OSError:
            stream.write(b'The selected command could not be started.\n')
            code = 2
    return code, source


def run_report(argv, *, title='Dots output', cwd=None, environment=None, completed=None, directory=None):
    with output_directory(directory) as spool:
        code, source = capture(argv, spool, cwd=cwd, environment=environment)
        if completed:
            completed(code)
        try:
            reviewed = bool(view(source, spool, title=title, code=code))
        except KeyboardInterrupt:
            reviewed = False
        return OutputResult(code, reviewed)


def run_output(argv, **kwargs):
    return run_report(argv, **kwargs).code


def main():
    if len(sys.argv) == 3 and sys.argv[1] == 'view':
        request = Path(sys.argv[2])
        data = read_request(request)
        path = Path(data['file'])
        info = path.lstat()
        if (not path.is_absolute() or not stat.S_ISREG(info.st_mode)
                or os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)
                or data.get('backend') not in ('less', 'fzf', 'fzf-wrap')
                or not isinstance(data.get('environment'), dict)
                or not all(isinstance(k, str) and isinstance(v, str) and k and '=' not in k
                           and '\0' not in k + v for k, v in data['environment'].items())):
            raise ValueError('invalid report request')
        try:
            code = 0 if reader(path, backend=data['backend'], environment=data['environment']) else 130
        except KeyboardInterrupt:
            code = 130
        except (OSError, ValueError):
            code = 2
        with private_file(request.with_suffix('.status')) as stream:
            stream.write(str(code).encode('ascii'))
        return code
    if len(sys.argv) != 2:
        raise ValueError('invalid private output request')
    data = read_request(sys.argv[1])
    if (not isinstance(data.get('text'), str) or not isinstance(data.get('title'), str)
            or type(data.get('code')) is not int or not 0 <= data['code'] <= 255):
        raise ValueError('invalid private output request')
    return 0 if page_text(data['text'], title=data['title'], code=data['code']) else 130


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError):
        print('dots menu: output reader failed', file=sys.stderr)
        sys.exit(2)
