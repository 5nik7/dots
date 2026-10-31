"""Bounded streaming presentation; the runner owns status, never the formatter."""
import codecs
import os
import queue
import re
import signal
import subprocess
import sys
import threading
from .common import clean

ESCAPES = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-_])')
APT_SCRIPT_WARNING = 'WARNING: apt does not have a stable CLI interface. Use with caution in scripts.'


def styled(cfg, stream):
    return cfg.get('output') != 'raw' and (cfg.get('output') == 'styled' or stream.isatty() or
                                           os.environ.get('DOTS_MENU_CAPTURE') == '1')


class Formatter:
    def __init__(self, stream, cfg):
        self.stream, self.pending = stream, ''
        self.after_cr = False
        self.manager = cfg.get('_manager')
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.ui = None
        if styled(cfg, stream):
            try:
                from .reports import report
                self.ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'), stream=stream)
            except (ImportError, OSError, ValueError): pass

    def emit(self, text, ending=''):
        text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', ESCAPES.sub('', text)).replace('\t', '    ')
        if self.manager in (None, 'auto', 'apt') and text == APT_SCRIPT_WARNING: return
        role = ('error' if re.search(r'^(?:E:|ERR\b|error\b|fatal\b|failed\b)', text, re.I) else
                'warning' if re.search(r'^(?:W:|warn|skip)', text, re.I) else
                'success' if re.search(r'^(?:success|complete|installed\b|up.to.date)', text, re.I) else 'value')
        markers = {'apt': r'^(?:Get:|Hit:|Unpacking |Setting up )', 'pacman': r'^(?:::|\(\d+/\d+\))',
                   'paru': r'^(?:::|\(\d+/\d+\))', 'yay': r'^(?:::|\(\d+/\d+\))',
                   'npm': r'^(?:added |changed |removed |npm )', 'pip': r'^(?:Collecting |Downloading |Installing |Requirement )',
                   'uv-tool': r'^(?:Resolved |Prepared |Installed |Updated )', 'go': r'^(?:go: |Upgrading |Binary\s)',
                   'gem': r'^(?:Fetching |Building |Successfully )', 'dnf': r'^(?:Upgrading:|Installing:|Downloading )',
                   'xbps': r'^(?:Updating |Installing |Unpacking )'}
        if role == 'value' and any(re.search(pattern,text) for name,pattern in markers.items() if self.manager in (None,'auto',name)):
            role = 'identity'
        if self.ui and role != 'value': text = self.ui.ui.paint(text, __import__('plugin_presentation').STYLES[role])
        self.stream.write(text + ending)
        self.stream.flush()

    def feed(self, chunk, final=False):
        decoded = self.decoder.decode(chunk, final=final)
        if decoded:
            if self.after_cr and decoded.startswith('\n'): decoded = decoded[1:]
            self.after_cr = False
        self.pending += decoded
        while True:
            found = re.search(r'[\r\n]', self.pending)
            if not found: break
            line, self.pending = self.pending[:found.start()], self.pending[found.end():]
            if found.group() == '\r':
                if self.pending.startswith('\n'): self.pending = self.pending[1:]
                elif not self.pending: self.after_cr = True
            self.emit(line, '\n')
        if final:
            self.pending = re.sub(r'\x1b(?:\[[0-?]*[ -/]*|\][^\x07]*)?$', '', self.pending)
        if len(self.pending) > 8192 or final: self.flush_partial(final=final)

    def flush_partial(self, final=False):
        # Do not emit an incomplete terminal escape sequence.
        if not final and self.manager in (None, 'auto', 'apt') and APT_SCRIPT_WARNING.startswith(self.pending): return
        if self.pending and '\x1b' not in ESCAPES.sub('', self.pending):
            self.emit(self.pending)
            self.pending = ''
        elif len(self.pending) > 8192:
            self.emit(self.pending.replace('\x1b', ''))
            self.pending = ''


def filter_stdin(cfg):
    source = getattr(sys.stdin, 'buffer', sys.stdin)
    target = getattr(sys.stdout, 'buffer', sys.stdout)
    formatter = Formatter(sys.stdout, cfg)
    while True:
        chunk = source.read1(4096) if hasattr(source, 'read1') else source.read(4096)
        if not chunk: break
        if isinstance(chunk, str): chunk = chunk.encode()
        if cfg.get('output') == 'raw':
            try: target.write(chunk)
            except TypeError: target.write(chunk.decode('utf-8', 'replace'))
            target.flush()
        else: formatter.feed(chunk); formatter.flush_partial()
    if cfg.get('output') != 'raw': formatter.feed(b'', final=True)
    return 0


def run(command, cfg, *, unattended=False, env=None, data=False):
    command = list(command)
    try: tty = open('/dev/tty', 'r')
    except OSError: tty = None
    if command[0] == 'sudo' and tty is None and '-n' not in command:
        command.insert(1, '-n')
    stdin = tty if tty else subprocess.DEVNULL
    stdout = sys.stderr if data else sys.stdout
    environment = dict(os.environ, **(env or {}))
    capture = styled(cfg, stdout) or styled(cfg, sys.stderr)
    proc = None
    stopped = threading.Event()
    isolated = tty is None and os.name != 'nt'
    try:
        if capture: environment.update(LC_ALL='C', NO_COLOR='1')
        proc = subprocess.Popen(command, stdin=stdin, stdout=subprocess.PIPE if capture else stdout,
                                stderr=subprocess.PIPE if capture else sys.stderr, env=environment,
                                start_new_session=isolated)
        if not capture: return proc.wait()
        events = queue.Queue(maxsize=64)
        def put(event):
            while not stopped.is_set():
                try: events.put(event, timeout=0.1); return
                except queue.Full: pass
        def pump(index, pipe):
            try:
                while not stopped.is_set():
                    chunk = pipe.read1(4096)
                    if not chunk: break
                    put((index, chunk))
            finally:
                pipe.close()
                put((index, None))
        workers = [threading.Thread(target=pump, args=(i, pipe), daemon=True)
                   for i, pipe in enumerate((proc.stdout, proc.stderr))]
        for worker in workers: worker.start()
        formatters = [Formatter(stdout, cfg), Formatter(sys.stderr, cfg)]
        finished = 0
        while finished < 2:
            try: index, chunk = events.get(timeout=0.1)
            except queue.Empty:
                for formatter in formatters: formatter.flush_partial()
                continue
            if chunk is None:
                formatters[index].feed(b'', final=True)
                finished += 1
            else: formatters[index].feed(chunk)
        return proc.wait()
    except BaseException:
        stopped.set()
        if proc:
            try:
                if isolated: os.killpg(proc.pid, signal.SIGINT)
                elif proc.poll() is None: proc.send_signal(signal.SIGINT)
                try: proc.wait(timeout=2)
                except subprocess.TimeoutExpired: pass
                if isolated: os.killpg(proc.pid, signal.SIGKILL)
                elif proc.poll() is None: proc.kill()
            except ProcessLookupError: pass
            proc.wait()
        raise
    finally:
        stopped.set()
        if tty: tty.close()
