"""Bounded Codex app-server adapter; imported only for an explicit Todo launch."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import re
import shutil
import stat
import subprocess
import threading

from platform_info import detect


class RPC:
    def __init__(self, send, receive, close):
        self.send, self.receive, self.shutdown = send, receive, close
        self.responses = queue.Queue()
        self.sequence = 0
        self.closed = False
        self.reader = threading.Thread(target=self.drain, daemon=True)
        self.reader.start()
        self.call('initialize', dict(clientInfo=dict(name='dots_todo', title='Dots Todo', version='1'),
                                    capabilities=dict(experimentalApi=True)))
        self.send(json.dumps(dict(method='initialized')))

    def drain(self):
        try:
            while not self.closed:
                raw = self.receive()
                if not raw or len(raw) > 16 * 1024 * 1024:
                    break
                message = json.loads(raw)
                # The attached Codex TUI owns server requests/approval decisions.
                # Drain notifications continuously rather than retaining transcript data.
                if isinstance(message, dict) and 'id' in message and 'method' not in message:
                    self.responses.put(message)
        except Exception:
            pass  # Transport errors can contain authentication headers: never expose them.
        finally:
            self.responses.put(None)

    def call(self, method, params=None):
        self.sequence += 1
        ident = self.sequence
        try:
            self.send(json.dumps(dict(id=ident, method=method, params=params or {})))
        except Exception:
            raise ValueError('Codex request could not be sent; resume the linked thread to recover') from None
        try:
            while True:
                response = self.responses.get(timeout=15)
                if response is None:
                    raise ValueError('Codex connection closed; resume the linked thread to recover')
                if response.get('id') == ident:
                    break
        except (OSError, queue.Empty):
            raise ValueError('Codex request timed out or disconnected; resume the linked thread to recover') from None
        if 'error' in response:
            raise ValueError('Codex rejected ' + method + '; check server capabilities and the linked thread')
        if not isinstance(response.get('result'), dict):
            raise ValueError('Codex returned an invalid ' + method + ' response')
        return response['result']

    def close(self):
        self.closed = True
        self.shutdown()
        self.reader.join(timeout=2)


def private_token(directory):
    from transactions import parents_safe
    parents_safe(directory / 'token')
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ValueError('Codex runit token directory must be private and owned by this user')
    fd = os.open(directory / 'token', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'r', encoding='ascii') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                info.st_mode & 0o077 or info.st_size not in (64, 65)):
            raise ValueError('Codex runit token must be a private regular file')
        token = stream.read(66).strip()
    if not re.fullmatch('[a-f0-9]{64}', token):
        raise ValueError('Codex runit token is invalid')
    return token


class Backend:
    def __init__(self):
        self.termux = detect()['platform'] == 'termux'
        self.environment = dict(os.environ)
        for key in ('CODEX_HOME', 'CODEX_TERMUX_CONFIG'):
            if self.environment.get(key):
                self.environment[key] = str(Path(self.environment[key]).expanduser().resolve())
        self.executable = shutil.which('codex-termux' if self.termux else 'codex')
        if not self.executable:
            raise ValueError(('codex-termux' if self.termux else 'Codex') + ' is unavailable')
        self.port = None
        if self.termux:
            result = subprocess.run([self.executable, '--wrapper-no-update', '--wrapper-output', 'raw',
                'manage', 'config', 'show'], capture_output=True, timeout=5, env=self.environment)
            if result.returncode or len(result.stdout) > 16384:
                raise ValueError('Cannot read codex-termux connection settings')
            settings = dict(line.split('=', 1) for line in result.stdout.decode().splitlines()
                            if '=' in line and not line.startswith('#'))
            value = settings.get('runit_port', '')
            if not value.isdecimal() or not 1 <= int(value) <= 65535:
                raise ValueError('codex-termux returned an invalid runit port')
            self.port = int(value)
            self.environment['CODEX_TERMUX_RUNIT_PORT'] = str(self.port)
        home = Path(self.environment.get('CODEX_HOME') or Path.home() / '.codex').resolve()
        self.identity = ('termux-runit:' + str(self.port) if self.termux else 'local-daemon') + ':' + str(home)

    def argv(self, thread, cwd):
        prefix = ([self.executable, '--wrapper-no-update', 'connect', '--chatgpt', '--backend', 'runit', '--']
                  if self.termux else [self.executable])
        return [*prefix, '--cd', cwd, 'resume', thread]

    @contextmanager
    def connect(self):
        if self.termux:
            try:
                from websockets.sync.client import connect
            except ImportError:
                raise ValueError('Todo planning requires Python websockets; see docs/todo.md') from None
            try:
                token = private_token(Path.home() / '.local/share/codex-remote')
                connector = connect('ws://127.0.0.1:' + str(self.port), proxy=None,
                    additional_headers={'Authorization': 'Bearer ' + token},
                    open_timeout=5, close_timeout=2, max_size=16 * 1024 * 1024)
                connection = connector.__enter__()
            except Exception:
                raise ValueError('Codex runit connection failed; check codex-termux manage server status --backend runit') from None
            close = lambda: connector.__exit__(None, None, None)
            send, receive = connection.send, connection.recv
        else:
            result = subprocess.run([self.executable, 'app-server', 'daemon', 'start'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
                                    env=self.environment)
            if result.returncode:
                raise ValueError('Codex local daemon unavailable; check the native Codex installation')
            process = subprocess.Popen([self.executable, 'app-server', 'proxy'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                env=self.environment)
            def send(value):
                process.stdin.write(value + '\n')
                process.stdin.flush()
            receive = lambda: process.stdout.readline(16 * 1024 * 1024 + 1)
            def close():
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait()
                process.stdin.close(); process.stdout.close()
        rpc = None
        try:
            rpc = RPC(send, receive, close)
            yield rpc
        finally:
            rpc.close() if rpc else close()
