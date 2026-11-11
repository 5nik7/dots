"""Small, lazy adapter from application reports to the shared Dots renderer."""
import os
import sys


STYLES = dict(heading='1;96', label='94', identity='94', count='96',
              success='92', warning='93', error='91', muted='2', value=None)


def color_mode(explicit=None, fallback='auto'):
    mode = explicit if explicit is not None else os.environ.get('DOTS_COLOR', fallback)
    return mode if mode in ('auto', 'always', 'never') else 'never'


def report(explicit=None, *, fallback='auto', stream=None, data=False, presentation=None, styles=None):
    """Data and ordinary redirected text never load the human renderer."""
    if data:
        return None
    stream = sys.stdout if stream is None else stream
    mode = color_mode(explicit, fallback)
    capture = os.environ.get('DOTS_MENU_CAPTURE') == '1'
    if not (stream.isatty() or capture or mode == 'always'
            or os.environ.get('DOTS_ICONS') == 'always'):
        return None
    return Report(stream, mode, capture, presentation=presentation, styles=styles)


class Report:
    def __init__(self, stream, mode, capture, *, presentation=None, styles=None):
        from files.catalog import Presentation
        self.styles = STYLES if styles is None else styles
        self.ui = (presentation or Presentation)(stream, terminal=stream.isatty() or capture)
        terminal = (stream.isatty() or capture) and os.environ.get('TERM', 'dumb') != 'dumb'
        self.ui.color = mode == 'always' or (mode == 'auto' and terminal and not os.environ.get('NO_COLOR'))
        self.ui.human = True

    def heading(self, title, count=None):
        if count is None:
            self.ui.heading(title)
        else:
            self.ui.heading_spans([(title, self.styles['heading']),
                                   (' (', self.styles['muted']), (str(count), self.styles['count']),
                                   (')', self.styles['muted'])])

    def gap(self):
        self.ui.emit()

    def row(self, spans, *, indent=2):
        self.ui._spans([(str(value), self.styles[role]) for value, role in spans],
                       prefix=' ' * indent)

    def text(self, value, role='value'):
        self.row([(value, role)])

    def field(self, label, value, role='value'):
        value = 'yes' if value is True else 'no' if value is False else 'unavailable' if value is None else str(value)
        self.ui.detail_spans(label, [(value, self.styles[role])], label_width=11)

    def resource(self, label, path, *, kind=None):
        self.ui.resource_detail(label.ljust(11), path, kind=kind)

    def prompt(self, value):
        from resources import wrap
        lines = list(wrap(self.ui.clean(value), max(1, self.ui.width - 1)))
        for line in lines[:-1]:
            self.ui.emit(self.ui.paint(line, self.styles['label']))
        print(self.ui.paint(lines[-1], self.styles['label']), end=' ',
              file=self.ui.stream, flush=True)
