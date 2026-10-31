"""Explicit tmux context for menu selection and workflow terminal handoff."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile


HELPER = Path(__file__).with_name('menu_host.py')


def tmux_arg(value):
    # tmux's command parser treats a trailing semicolon as a command separator.
    return value[:-1] + r'\;' if value.endswith(';') else value


def status(code):
    return 128 - code if code < 0 else code


def terminal_result(path, code):
    receipt = Path(path).with_suffix('.status')
    if receipt.is_file():
        value = receipt.read_text(encoding='ascii')
        if value.isdecimal() and 0 <= int(value) <= 255:
            return int(value)
        raise ValueError('invalid menu terminal result')
    return 130 if code in (0, -1, 129) else status(code)


@contextmanager
def request_file(payload):
    """Private, short-lived transport; never emit its contents or retain a journal."""
    with tempfile.TemporaryDirectory(prefix='dots-menu-') as directory:
        path = Path(directory) / 'request.json'
        with path.open('x', encoding='utf-8') as stream:
            if os.name != 'nt':
                os.fchmod(stream.fileno(), 0o600)
            json.dump(payload, stream, ensure_ascii=True)
        yield path


def read_request(path):
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'r', encoding='utf-8') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4 * 1024 * 1024:
            raise ValueError('invalid private menu request')
        if os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('private menu request has unsafe permissions')
        try:
            data = json.load(stream)
        except (ValueError, UnicodeError):
            raise ValueError('invalid private menu request') from None
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('invalid private menu request')
    return data


@dataclass(frozen=True)
class TmuxContext:
    executable: str
    socket: str
    client: str
    client_pid: int
    pane: str
    session: str
    cwd: str

    def __post_init__(self):
        if (not all(isinstance(v, str) and v and '\0' not in v for v in
                    (self.executable, self.socket, self.client, self.pane, self.session, self.cwd))
                or not all(os.path.isabs(v) for v in (self.executable, self.socket, self.cwd))
                or not re.fullmatch(r'%[0-9]+', self.pane)
                or not re.fullmatch(r'\$[0-9]+', self.session)
                or type(self.client_pid) is not int or self.client_pid <= 0):
            raise ValueError('invalid menu tmux context')

    def command(self, *args):
        return [self.executable, '-N', '-S', self.socket, *map(tmux_arg, args)]

    def observe(self, *args):
        result = subprocess.run(self.command(*args), capture_output=True, text=True, timeout=5)
        if result.returncode:
            raise ValueError('menu tmux context is no longer available')
        return result.stdout

    @classmethod
    def from_environment(cls):
        """Consume an inherited menu context, or capture an unambiguous caller."""
        if os.name == 'nt':
            raise ValueError('tmux menus are unavailable on native Windows')
        request = os.environ.get('DOTS_MENU_CONTEXT')
        if request:
            context = cls(**read_request(request)['context'])
            context.verify()
            return context
        return cls.capture()

    @classmethod
    def capture(cls, *, client=None, pane=None, cwd=None):
        if os.name == 'nt':
            raise ValueError('tmux menus are unavailable on native Windows')
        executable = shutil.which('tmux')
        parts = os.environ.get('TMUX', '').rsplit(',', 2)
        pane = pane or os.environ.get('TMUX_PANE', '')
        if not executable or len(parts) != 3 or not os.path.isabs(parts[0]) or not re.fullmatch(r'%[0-9]+', pane):
            raise ValueError('menu requires an explicit tmux server and originating pane')
        cwd = os.path.abspath(cwd or os.getcwd())
        # A temporary identity enables only read-only observation during capture.
        probe = cls(os.path.abspath(executable), parts[0], client or 'unresolved', 1, pane, '$0', cwd)
        session = probe.observe('display-message', '-p', '-t', pane, '#{session_id}').strip()
        clients = probe.observe('list-clients', '-F', '#{client_name}\t#{client_pid}\t#{session_id}').splitlines()
        candidates = [row.split('\t') for row in clients]
        candidates = [row for row in candidates if len(row) == 3 and row[2] == session and (client is None or row[0] == client)]
        if len(candidates) != 1:
            raise ValueError('menu client is unavailable or ambiguous; supply the invoking client explicitly')
        name, pid, _ = candidates[0]
        context = cls(probe.executable, probe.socket, name, int(pid), pane, session, cwd)
        context.verify()
        return context

    def verify(self):
        rows = self.observe('list-clients', '-F', '#{client_name}\t#{client_pid}\t#{session_id}\t#{client_width}\t#{client_height}').splitlines()
        found = [row.split('\t') for row in rows if row.split('\t')[0] == self.client]
        if (len(found) != 1 or len(found[0]) != 5 or found[0][1:3] != [str(self.client_pid), self.session]
                or self.observe('display-message', '-p', '-t', self.pane, '#{session_id}').strip() != self.session):
            raise ValueError('originating menu client or pane changed; reopen the menu')
        try:
            width, height = map(int, found[0][3:])
        except ValueError:
            raise ValueError('invalid tmux client dimensions') from None
        if min(width, height) < 3:
            raise ValueError('tmux client is too small for a menu')
        return width, height

    @contextmanager
    def selector_environment(self):
        """Scope FZF's tmux invocation to this client without changing server state."""
        columns, lines = self.verify()
        shell = shutil.which('bash')
        if not shell or any(c.isspace() for c in shell):
            raise ValueError('menu popup needs a usable Bash adapter')
        with request_file(dict(schema=1, context=asdict(self))) as path:
            proxy = path.parent / 'tmux'
            proxy.write_text('#!' + shell + '\nexec ' + shlex.join(
                [sys.executable, '-B', str(HELPER), 'proxy', str(path)]) + ' "$@"\n', encoding='utf-8')
            proxy.chmod(0o700)
            # An unset pane makes FZF use a client popup, not a shared floating
            # pane on newer tmux. The proxy supplies -c for exact client routing.
            yield dict(PATH=str(path.parent) + os.pathsep + os.environ.get('PATH', ''),
                       TMUX_PANE='', TMUX=self.socket + ',0,0',
                       DOTS_MENU_COLUMNS=str(columns), DOTS_MENU_LINES=str(lines))

    def popup(self, argv, *, size=None):
        columns, lines = self.verify()
        width, height = size or (max(1, columns * 9 // 10), max(1, lines * 9 // 10))
        width, height = min(width, columns), min(height, lines)
        from menu_popup import preferences, tmux_flags, dimensions
        from files.catalog import Presentation
        ui = Presentation(terminal=True)
        options = preferences()
        width, height = dimensions(options, (width, height), (columns, lines), size)
        appearance = tmux_flags(options, height, lines, color=ui.color, icons=ui.icons)
        return subprocess.run(self.command('display-popup', '-E', '-c', self.client,
            *appearance, '-w' + str(width), '-h' + str(height), *argv)).returncode

    def output(self, argv, *, title='Dots output'):
        from menu_pager import OutputResult, popup_bounds, show_report
        width, maximum = popup_bounds(self.verify())
        payload = dict(schema=1, argv=list(argv), cwd=self.cwd,
                       environment=dict(os.environ), hold=True, title=title,
                       render_size=[max(1, width - 2), max(1, maximum - 2)])
        with request_file(payload) as path:
            result = self.popup([sys.executable, '-B', str(HELPER), 'host', str(path)],
                                size=(width, min(6, maximum)))
            code = terminal_result(path, result)
            report = path.parent / 'view.txt'
            if not path.with_suffix('.status').exists() or not report.is_file():
                return OutputResult(code, False)
            return OutputResult(code, show_report(report, self))

    def host(self, argv, *, hold=False, title=None, document=False):
        if hold:
            return self.output(argv, title=title or 'Dots output').code
        self.verify()
        # Preserve the caller environment in private transport, not command-line
        # arguments, logs, public JSON or persistent state.
        payload = dict(schema=1, argv=list(argv), cwd=self.cwd, environment=dict(os.environ), hold=hold)
        if title is not None:
            payload['title'] = title
        if document:
            payload['defer_reader'] = True
        with request_file(payload) as path:
            result = self.popup([sys.executable, '-B', str(HELPER), 'host', str(path)])
            code = terminal_result(path, result)
            if document and code == 0 and (path.parent / 'document.ready').exists():
                from menu_pager import show_report
                read_request(path.parent / 'document.ready')
                show_report(path.parent / 'view.txt', self)
            return code
