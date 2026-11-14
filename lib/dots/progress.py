"""Transient progress for human CLI work; never owns operations or approval."""
from contextlib import ContextDecorator, contextmanager
from functools import wraps
from fractions import Fraction
from cli_preferences import progress_mode
import os
import re
import shutil
import signal
import sys
import threading
import time
import unicodedata

_enabled = False
_current = None
_active_step = None
DELAY = 0.5
INTERVAL = 0.1


def configure(human=True):
    """Controllers must opt in only after excluding data and dry-run modes."""
    global _enabled
    _enabled = bool(human)


def eligible(mode_override=None):
    return (_enabled and os.environ.get('TERM', 'dumb') != 'dumb'
            and sys.stdout.isatty() and sys.stderr.isatty()
            and (mode_override or progress_mode()) in ('spinner','bar','both'))


def terminal_columns(stream=None):
    """Prefer the actual terminal over an inherited, possibly stale COLUMNS."""
    try:
        return max(1, os.get_terminal_size((stream or sys.stderr).fileno()).columns)
    except (AttributeError, OSError, ValueError):
        return max(1, shutil.get_terminal_size((80, 24)).columns)


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
    def __init__(self, label, *, marker_style=None, label_style=None, mode_override=None):
        if mode_override not in (None, 'none', 'spinner', 'bar', 'both'):
            raise ValueError('invalid progress preview mode')
        self.label = label
        self.marker_style, self.label_style = marker_style, label_style
        self.mode_override = mode_override
        self.appearance = None
        self.owner = False
        self.worker = None
        self.done = threading.Event()
        self.state = (clean(label), 0, 0)
        self.stream = sys.stderr
        self.drawn = 0
        self.drawn_lines = ()
        self.overall = (Fraction(0), 'step', 1, 1)
        self.step_hint = None
        self.cancelled = False
        self.previous_term = None
        self.term_handler = None
        self.parent = None
        self.previous_state = None
        self.started = 0.0
        self.mode = 'none'

    def __enter__(self):
        global _current
        if not (eligible(self.mode_override) if self.mode_override is not None else eligible()):
            return self
        if _current is not None:
            self.parent = _current
            self.previous_state = _current.state
            return _current
        self.resolve_styles()
        self.owner = True
        self.mode = self.mode_override or progress_mode()
        self.started = time.monotonic()
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

    def resolve_styles(self):
        """Resolve once before the worker, or explicitly for a static preview."""
        if self.appearance is not None: return
        from progress_preferences import Appearance
        try:
            from style_config import current
            styles = current()
            if styles is not None:
                if self.marker_style is None: self.marker_style = styles.code('96')
                if self.label_style is None: self.label_style = styles.code('94')
            self.appearance = Appearance(styles)
        except (ImportError, OSError, ValueError, KeyError, TypeError):
            self.appearance = Appearance()
        if not isinstance(self.marker_style, str) or not re.fullmatch(r'[0-9;]{1,80}', self.marker_style): self.marker_style = '96'
        if not isinstance(self.label_style, str) or not re.fullmatch(r'[0-9;]{1,80}', self.label_style): self.label_style = '94'

    def update(self, label, completed=0, total=0):
        # Reporting is optional: malformed observer data cannot break a mutation.
        try:
            state = (clean(label), max(0, int(completed)), max(0, int(total)))
            # Publish a single immutable snapshot. The worker never needs a lock
            # that a signal handler could interrupt while the main thread owns it.
            self.state = state
        except (ValueError, TypeError, OSError):
            pass

    def update_spans(self, spans, completed=0, total=0):
        """Accept inert text and resolved SGR styles; clip before adding escapes.

        None inherits the ordinary label color. Resolve theme styles in the caller,
        once per operation, rather than querying configuration in the worker.
        """
        try:
            spans = tuple((clean(text), code if isinstance(code, str) and
                           re.fullmatch(r'[0-9]{1,3}(?:;[0-9]{1,3}){0,15}', code) else None)
                          for text, code in spans)
            self.state = (spans, max(0, int(completed)), max(0, int(total)))
        except (ValueError, TypeError, OSError):
            pass

    def credit(self, fraction):
        """Publish monotonic sequence progress; activity counters never call this."""
        if self.cancelled: return
        previous, unit, index, total = self.overall
        self.overall = (max(previous, min(Fraction(1), fraction)), unit, index, total)

    def cancel(self):
        """Freeze the operation when cancellation is returned as ordinary data."""
        self.cancelled = True

    def _clear(self):
        if self.drawn_lines:
            # Account for a terminal reflow after a width reduction. Never hide
            # the cursor or use an alternate screen owned by another workflow.
            columns = terminal_columns(self.stream)
            rows = sum(max(1, (cells + columns - 1) // columns) for cells in self.drawn_lines)
            # Reflow keeps the cursor with the current row; saved absolute
            # cursor coordinates do not follow that row when the terminal shrinks.
            self.stream.write('\r\033[2K' + '\033[1A\r\033[2K' * (rows - 1) + '\r')
            self.stream.flush()
            self.drawn_lines = ()
            self.drawn = 0

    def lines(self, frame, width, color, icons):
        """Two inert, cell-bounded rows, then optional SGR; no operation logic."""
        self.resolve_styles()
        width = max(1, width)
        fraction = self.overall[0]
        label, completed, total = self.state
        completed = min(completed, total) if total else 0
        glyphs, styles = self.appearance.glyphs(icons), self.appearance.colors
        surrounds = len(glyphs['left'] + glyphs['right'])
        spinner = ('⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' if icons else '|/-\\')[frame % (10 if icons else 4)]

        def bar(value, size):
            if value is None:
                point = frame % (2 * (size - 1)) if size > 1 else 0
                point = min(point, 2 * (size - 1) - point)
                before, filled, after = point, 1, size-point-1
            else:
                before, filled = 0, int(size * value)
                after = size-filled
            return [(glyphs['left'], styles['surround']),
                    (glyphs['empty'] * before, styles['empty']),
                    (glyphs['filled'] * filled, styles['filled']),
                    (glyphs['empty'] * after, styles['empty']),
                    (glyphs['right'], styles['surround'])]

        def bounded(parts, limit):
            result, used = [], 0
            for text, style in parts:
                piece, cells = clip(text, max(0, limit-used))
                if piece: result.append((piece, style))
                used += cells
                if len(piece) < len(text): break
            return result, used

        def paint(parts):
            parts, used = bounded(parts, width)
            text = '\033[0m' if color else ''
            for piece, style in parts:
                code = self.label_style if style is None else style
                text += ('\033['+code+'m'+piece+'\033[0m') if color and code else piece
            return text, used

        percent = str(int(100 * fraction))+'%'
        size = width-surrounds-1-len(percent)
        overall = bar(fraction, size)+[(' ', '')] if self.mode in ('bar','both') and size > 0 else []
        overall.append((percent, styles['percentage']))

        prefix = spinner if self.mode in ('spinner','both') else ''
        hint = self.step_hint
        if hint and hint[2]: prefix += (' ' if prefix else '')+f'{hint[1]}/{hint[2]}'
        prefix, prefix_cells = clip(prefix, width)
        suffix = ' '+str(100*completed//total)+'%' if total else ''
        spans = ((label, None),) if isinstance(label, str) else label
        separator = ' · ' if hint and hint[2] else ' ' if prefix else ''
        wants_bar = self.mode == 'bar' or self.mode == 'both' and total
        # Reserve an eight-cell interior before truncating activity. A short
        # activity gives its spare cells to the bar; very narrow rows shrink it.
        reserve = 8+surrounds+1 if wants_bar else 0
        activity, activity_cells = bounded(spans, width-prefix_cells-len(separator)-len(suffix)-reserve)
        current = [(prefix, self.marker_style)]
        if activity_cells:
            current += [(separator, self.marker_style), *activity]
            prefix_cells += len(separator)+activity_cells
        if wants_bar:
            gap = 1 if prefix_cells else 0
            size = width-prefix_cells-gap-len(suffix)-surrounds
            if size > 0:
                if gap: current.append((' ', ''))
                current += bar(Fraction(completed,total) if total else None, size)
        current.append((suffix, styles['percentage']))
        return paint(overall), paint(current)

    def _run(self):
        try:
            if self.done.wait(max(0, DELAY - (time.monotonic() - self.started))):
                return
            frame = 0
            while not self.done.is_set():
                width = max(1, terminal_columns(self.stream) - 1)
                mode = os.environ.get('DOTS_COLOR', 'auto')
                color = mode == 'always' or (mode == 'auto' and not os.environ.get('NO_COLOR'))
                icons = os.environ.get('DOTS_ICONS', 'auto') in ('auto', 'always')
                rows = self.lines(frame, width, color, icons)
                self._clear()
                # Reserve both rows before painting, including when the initial
                # cursor sits on the bottom terminal row.
                self.stream.write('\n\r\033[1A\r' + rows[0][0] + '\n\r' + rows[1][0])
                self.stream.flush()
                self.drawn_lines = tuple(row[1] for row in rows)
                self.drawn = max(self.drawn_lines)
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
            if not exc or exc[0] is None: self.credit(Fraction(1))
            self._stop()
            if self.term_handler is not None and signal.getsignal(signal.SIGTERM) == self.term_handler:
                signal.signal(signal.SIGTERM, self.previous_term)
            _current = None
        elif self.parent is not None and _current is self.parent:
            self.parent.state = self.previous_state
        return False


class sequence:
    """Equal sibling work within the currently reserved step, without discovery.

    Callers freeze a child count before entering. Only explicit step completion
    or Work.update credits overall progress; report/update are local activity.
    Python indexes are zero based; omitted indexes advance through the sequence.
    """
    def __init__(self, label, total, unit='step', *, recovery=False):
        self.label, self.total, self.unit = clean(label), max(0,int(total)), clean(unit)
        self.recovery = recovery
        self.next = 0
        self.context = None

    def __enter__(self):
        self.parent = _active_step
        if self.parent is not None:
            self.meter = self.parent.sequence.meter
            self.base, self.span = self.parent.base, self.parent.span
            self.tracking = self.parent.sequence.tracking and not self.recovery
        else:
            if _current is None:
                self.context = Progress(self.label)
                self.meter = self.context.__enter__()
            else: self.meter = _current
            self.base, self.span = Fraction(0), Fraction(1)
            self.tracking = not self.recovery
        self.previous_hint = self.meter.step_hint
        self.root = self.parent is None and not self.recovery
        if self.root:
            self.meter.overall = (self.meter.overall[0], self.unit, min(1,self.total), self.total)
        self.meter.update(self.label)
        return self

    def step(self, label, index=None):
        index = self.next if index is None else index
        self.next = index + 1
        return Work(self, label, index)

    def cancel(self):
        self.meter.cancel()

    def __exit__(self, *exc):
        if (not exc or exc[0] is None) and self.tracking: self.meter.credit(self.base+self.span)
        self.meter.step_hint = self.previous_hint
        if self.context is not None: self.context.__exit__(*exc)
        return False


class Work:
    def __init__(self, parent, label, index):
        self.sequence, self.label, self.index = parent, clean(label), index
        count = max(1,parent.total)
        self.base = parent.base + parent.span * Fraction(min(max(0,index),count),count)
        self.span = parent.span / count

    def __enter__(self):
        global _active_step
        self.previous = _active_step
        self.previous_hint = self.sequence.meter.step_hint
        _active_step = self
        meter = self.sequence.meter
        if self.sequence.root:
            meter.overall = (meter.overall[0],self.sequence.unit,min(self.index+1,self.sequence.total),self.sequence.total)
        meter.step_hint = ('recovery' if self.sequence.recovery else self.sequence.unit,
                           self.index+1,self.sequence.total)
        if self.sequence.tracking: meter.credit(self.base)
        meter.update(self.label)
        return self

    def update(self, label, completed=0, total=0):
        """Measure this entire step, not an opaque command's individual download."""
        self.sequence.meter.update(label,completed,total)
        try:
            if int(total)>0 and self.sequence.tracking:
                fraction = Fraction(min(max(0,int(completed)),int(total)),int(total))
                self.sequence.meter.credit(self.base+self.span*fraction)
        except (ValueError,TypeError,ZeroDivisionError): pass

    def __exit__(self, *exc):
        global _active_step
        if (not exc or exc[0] is None) and self.sequence.tracking:
            self.sequence.meter.credit(self.base+self.span)
        self.sequence.meter.step_hint = self.previous_hint
        _active_step = self.previous
        return False


def report(label, completed=0, total=0):
    if _current is not None:
        _current.update(label, completed, total)


@contextmanager
def permanent_output():
    """Join the renderer before printing; resume the same phase without a delay reset."""
    current = _current
    running = current is not None and current.worker is not None and current.worker.is_alive()
    if running:
        current._stop()
    try:
        yield
    except BaseException:
        # In particular, do not restart a worker while unwinding an interruption.
        raise
    else:
        if running and _current is current:
            current.done = threading.Event()
            try:
                current.worker = threading.Thread(target=current._run, name='dots-progress', daemon=True)
                current.worker.start()
            except (RuntimeError, OSError):
                current.worker = None


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
