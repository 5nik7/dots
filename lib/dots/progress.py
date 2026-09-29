"""Transient progress for human CLI work; never owns operations or approval."""
from contextlib import ContextDecorator
from functools import wraps
import os
import shutil
import signal
import sys
import threading
import unicodedata

_enabled = False
_current = None
DELAY = 0.5
INTERVAL = 0.1


def configure(human=True):
    """Controllers must opt in only after excluding data and dry-run modes."""
    global _enabled
    _enabled = bool(human)


def eligible():
    return (_enabled and os.environ.get('DOTS_PROGRESS', 'auto') == 'auto'
            and os.environ.get('TERM', 'dumb') != 'dumb'
            and sys.stdout.isatty() and sys.stderr.isatty())


def clean(value):
    return ''.join(c if c.isprintable() else repr(c)[1:-1] for c in str(value))


def clip(text, width):
    """Bound terminal cells, including combining and wide filename characters."""
    result, used = '', 0
    for char in text:
        cells = 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if used + cells > width:
            break
        result += char
        used += cells
    return result, used


class Progress(ContextDecorator):
    def __init__(self, label):
        self.label = label
        self.owner = False
        self.worker = None
        self.done = threading.Event()
        self.state = (clean(label), 0, 0)
        self.stream = sys.stderr
        self.drawn = 0
        self.previous_term = None
        self.term_handler = None
        self.parent = None
        self.previous_state = None

    def __enter__(self):
        global _current
        if not eligible():
            return self
        if _current is not None:
            self.parent = _current
            self.previous_state = _current.state
            return _current
        self.owner = True
        _current = self
        try:
            self.worker = threading.Thread(target=self._run, name='dots-progress', daemon=True)
            self.worker.start()
        except (RuntimeError, OSError):
            self.worker = None
        if threading.current_thread() is threading.main_thread():
            self.previous_term = signal.getsignal(signal.SIGTERM)
            if self.previous_term != signal.SIG_IGN:
                self.term_handler = self._terminate
                signal.signal(signal.SIGTERM, self.term_handler)
        return self

    def update(self, label, completed=0, total=0):
        # Reporting is optional: malformed observer data cannot break a mutation.
        try:
            state = (clean(label), max(0, int(completed)), max(0, int(total)))
            # Publish a single immutable snapshot. The worker never needs a lock
            # that a signal handler could interrupt while the main thread owns it.
            self.state = state
        except (ValueError, TypeError, OSError):
            pass

    def _clear(self):
        if self.drawn:
            self.stream.write('\r' + ' ' * self.drawn + '\r')
            self.stream.flush()
            self.drawn = 0

    def _run(self):
        try:
            if self.done.wait(DELAY):
                return
            frame = 0
            while not self.done.is_set():
                label, completed, total = self.state
                width = max(1, shutil.get_terminal_size((80, 24)).columns - 1)
                mode = os.environ.get('DOTS_COLOR', 'auto')
                color = mode == 'always' or (mode == 'auto' and not os.environ.get('NO_COLOR'))
                icons = os.environ.get('DOTS_ICONS', 'auto') in ('auto', 'always')
                if total:
                    completed = min(completed, total)
                    size = min(16, max(3, width // 5))
                    filled = size * completed // total
                    marker = '[' + ('━' if icons else '#') * filled + '-' * (size - filled) + ']'
                    suffix = f' {completed}/{total}'
                else:
                    marker = ('⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' if icons else '|/-\\')[frame % (10 if icons else 4)]
                    suffix = ''
                prefix = marker + suffix + ' '
                text, cells = clip(prefix + label, width)
                if color and len(prefix) < len(text):
                    text = '\033[96m' + text[:len(prefix)] + '\033[94m' + text[len(prefix):] + '\033[0m'
                self.stream.write('\r' + text + ' ' * max(0, self.drawn - cells))
                self.stream.flush()
                self.drawn = cells
                frame += 1
                self.done.wait(INTERVAL)
        except (OSError, ValueError):
            pass
        finally:
            try:
                self._clear()
            except (OSError, ValueError):
                pass

    def _stop(self):
        self.done.set()
        if self.worker is not None:
            self.worker.join()

    def _terminate(self, signum, frame):
        self._stop()
        if callable(self.previous_term):
            self.previous_term(signum, frame)
        else:
            signal.signal(signum, self.previous_term)
            os.kill(os.getpid(), signum)

    def __exit__(self, *exc):
        global _current
        if self.owner:
            self._stop()
            if self.term_handler is not None and signal.getsignal(signal.SIGTERM) == self.term_handler:
                signal.signal(signal.SIGTERM, self.previous_term)
            _current = None
        elif self.parent is not None and _current is self.parent:
            self.parent.state = self.previous_state
        return False


def report(label, completed=0, total=0):
    if _current is not None:
        _current.update(label, completed, total)


def tracked(label):
    """Keep the work in the caller; only the renderer runs in a worker."""
    def decorate(function):
        @wraps(function)
        def run(*args, **kwargs):
            if not eligible():
                return function(*args, **kwargs)
            with Progress(label):
                report(label)
                return function(*args, **kwargs)
        return run
    return decorate
