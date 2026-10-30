"""Session-only weather browser. Selection and previews never acquire weather."""
from contextlib import nullcontext
from dataclasses import dataclass
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import Cache, clean, config, validate_location, validate_language
from metadata import BROWSE_OPTIONS, spellings
from files.catalog import Presentation
from interaction import RichSelector, SelectionEnded, SelectionEvent, rich_fzf_available, terminal
from menu_input import prompt
from menu_tmux import TmuxContext, read_request, request_file
from menus import Entry, Menu, choose, run_action, show_message
from resources import wrap
from wttr import cli as weather_cli

ENTRIES = (
    Entry('current', 'Current conditions'),
    Entry('daily', 'Daily forecast'),
    Entry('hourly', 'Hourly forecast'),
    Entry('location', 'Change location'),
    Entry('units', 'Change units'),
    Entry('refresh', 'Refresh'),
    Entry('help', 'Help'),
    Entry('back', 'Back / Close'),
)
HELP = ('Enter: open   Esc: back / close   Ctrl-C: cancel\n'
        'F1: help   Alt-P: preview   Alt-J/K: scroll preview\n\n'
        'Opening and searching this menu only read cached weather.\n'
        'Reports refresh missing or stale data when the existing cooldown permits.\n'
        'Refresh explicitly retries, overriding freshness and cooldown.\n'
        'Failed refreshes retain marked stale weather up to configured max_stale.\n'
        'Location and units apply only until this browser closes.\n'
        'Automatic location uses the configured default, then termux-geo on Termux.\n'
        'There is no IP-location fallback. Plain wttr and dots wttr print reports.')


def help_view():
    ui = Presentation()
    ui.heading('Weather browser')
    ui.detail('Usage', 'wttr browse [LOCATION] [options] | dots wttr browse')
    for flag, value, description in BROWSE_OPTIONS:
        ui.detail(', '.join(spellings(flag)) + (' ' + value if value else ''), description)
    ui.emit()
    for line in HELP.splitlines():
        for part in wrap(line, ui.width):
            ui.emit(part)
    ui.detail('Fallback', 'Without FZF or an interactive terminal, print the ordinary report.')


@dataclass
class Session:
    path: Path
    cfg: dict
    location: str | None
    verbose: bool = False

    def cache(self):
        return Cache(self.cfg, self.location)

    def arguments(self, view='daily', *, refresh=False, browser=True):
        args = ['--config', str(self.path), '--units', self.cfg['units'],
                '--days', str(self.cfg['days']), '--language', self.cfg['language'],
                '--timeout', str(self.cfg['timeout'])]
        if self.location is not None:
            args.append('--location=' + self.location)
        if self.verbose:
            args.append('--verbose')
        if view == 'current': args.append('--current')
        elif view == 'hourly': args.append('--hourly')
        if browser: args.append('--allow-stale')
        if refresh: args.append('--refresh')
        return args

    def snapshot(self, view, *, width=80, row=None):
        """Render a bounded cached snapshot; no refresh, locks, workers or geo."""
        stream = io.StringIO()
        ui = Presentation(stream, terminal=True)
        ui.width = max(1, width)
        cache = self.cache()
        row = cache.read() if row is None else row
        ui.detail('Location', self.location or self.cfg['default_location'] or 'Automatic city')
        ui.detail('Units', self.cfg['units'])
        if row.get('error'):
            ui.detail('Refresh', clean(row['error']), '93')
        if cache.usable(row, stale=True):
            args = SimpleNamespace(current=view != 'daily' and view != 'hourly',
                                   hourly=view == 'hourly', verbose=self.verbose)
            weather_cli.render(row, self.cfg, args, cache.age(row), ui=ui)
        else:
            ui.detail('Weather', 'Unavailable: open a report or choose Refresh.')
        return stream.getvalue()


def preview_transport(path):
    command = ('& $env:DOTS_WTTR_PYTHON -B $env:DOTS_WTTR_BROWSER preview $env:DOTS_WTTR_PREVIEW {1}'
               if os.name == 'nt' else '"$DOTS_WTTR_PYTHON" -B "$DOTS_WTTR_BROWSER" preview "$DOTS_WTTR_PREVIEW" {1}')
    return command, '', dict(DOTS_WTTR_PYTHON=sys.executable, DOTS_WTTR_BROWSER=str(Path(__file__).resolve()),
                            DOTS_WTTR_PREVIEW=str(path))


def preview(path, token):
    data = read_request(path)
    if not token.isdecimal(): raise ValueError('invalid weather preview selection')
    index = int(token)
    if not 0 <= index < len(data['previews']): raise ValueError('invalid weather preview selection')
    print(data['previews'][index], end='')


def pick(session, frame, context):
    from files.picker import fzf_colors
    from picker_style import picker_colors
    from progress import permanent_output
    ui = Presentation(terminal=True)
    columns, lines = context.verify() if context else shutil.get_terminal_size((80, 24))
    width = max(1, min(100, columns - 2))
    height = max(1, min(30, lines - 2))
    row = session.cache().read()
    snapshots = {view: session.snapshot(view, width=max(1, width - 6), row=row)
                 for view in ('current', 'daily', 'hourly')}
    previews = [HELP if entry.id == 'help' else snapshots.get(entry.id, snapshots['current']) for entry in ENTRIES]
    labels = [entry.label for entry in ENTRIES]
    with request_file(dict(schema=1, previews=previews)) as path:
        with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
            try:
                selected = RichSelector(backend='fzf').fzf('wttr', labels, False,
                    preview_transport(path), ui.color, ui.icons, picker_colors(fzf_colors(ui)),
                    popup=f'center,{width},{height}' if context else False, height=height,
                    preview_position='down', preview_lines=max(1, min(10, height - 14)), preview_wrap=True,
                    query=frame.get('query', ''), environment=environment, navigation=frame,
                    event_selection=True, focus_index=frame.get('focus'),
                    header='Enter: open  Esc: back\nF1: help  Ctrl-C: cancel')
            except SelectionEvent as event:
                if event.index is not None: frame['focus'] = event.index
                raise
    frame['focus'] = selected[0]
    return ENTRIES[selected[0]].id


def select(title, entries, context):
    frame = {}
    while True:
        try:
            entry = choose(Menu('wttr:' + title, title, tuple(Entry(key, label) for key, label in entries)),
                           mode='browse', context=context, navigation=frame, query=frame.get('query', ''), compact=True)
            return entry.id if entry else None
        except SelectionEvent as event:
            if event.action != 'help': return None
            show_message(HELP, context=context, title='Weather browser help')


def available(context):
    if os.environ.get('TERM') == 'dumb' or not rich_fzf_available(): return False
    if context:
        result = subprocess.run(['fzf', '--help'], capture_output=True, timeout=5)
        return result.returncode == 0 and b'--popup' in result.stdout
    return True


def browse(session, args, context):
    frame = dict(query=args.query or '')
    while True:
        try:
            try:
                action = pick(session, frame, context)
            except SelectionEvent as event:
                action = 'help' if event.action == 'help' else 'back'
            if action == 'back': return 0
            if action == 'help':
                show_message(HELP, context=context, title='Weather browser help')
            elif action == 'location':
                choice = select('Location', [('custom', 'Enter a location'),
                                             ('default', 'Use configured / automatic location'), ('back', 'Back')], context)
                if choice == 'default': session.location = None
                elif choice == 'custom':
                    try:
                        value = prompt(session.location or session.cfg['default_location'],
                                       'Weather location (city or coordinates)', context, back=True)
                    except SelectionEvent:
                        continue
                    session.location = validate_location(value)
            elif action == 'units':
                units = select('Units', [('us', 'US: Fahrenheit, mph, inches'),
                                         ('metric', 'Metric: Celsius, km/h, mm'), ('back', 'Back')], context)
                if units in ('us', 'metric'): session.cfg['units'] = units
            else:
                view = 'current' if action == 'refresh' else action
                code = run_action([sys.executable, '-B', str(Path(__file__).with_name('cli.py')), '--_browse-report',
                                   *session.arguments(view, refresh=action == 'refresh')],
                                  kind='output', context=context, title='Weather · ' + view)
                if code == 130: return 130
        except (ValueError, OSError) as error:
            # Expired context must never fall back to a different client.
            if context: context.verify()
            show_message(clean(str(error)), context=context, title='Weather unavailable', code=1)


def main(argv):
    args = weather_cli.parser(BROWSE_OPTIONS, 'wttr browse').parse_intermixed_args(argv)
    for key in ('color', 'icons'):
        if getattr(args, key): os.environ['DOTS_' + key.upper()] = getattr(args, key)
    if args.help:
        help_view()
        return 0
    if len(args.positional) > 1 or (args.positional and args.location is not None):
        raise ValueError('supply one location, positionally or with --location')
    from stock import classify
    stock, _ = classify(args.positional)
    if stock: raise ValueError('stock requests cannot be combined with browse; use wttr directly')
    location = args.location if args.location is not None else args.positional[0] if args.positional else None
    if location is not None: location = validate_location(location)
    path, cfg = config(args.config)
    for key in ('units', 'language'):
        if getattr(args, key): cfg[key] = getattr(args, key)
    validate_language(cfg['language'])
    if args.days: cfg['days'] = int(args.days)
    if args.timeout:
        try: cfg['timeout'] = int(args.timeout)
        except ValueError: raise ValueError('timeout must be an integer from 1 to 60') from None
        if not 1 <= cfg['timeout'] <= 60: raise ValueError('timeout must be an integer from 1 to 60')
    session = Session(path.resolve(), cfg, location, args.verbose)
    # A redirected invocation is a report; inherited tmux variables alone do
    # not make it interactive. The launcher's private context is explicit.
    interactive = terminal() or bool(args.client or os.environ.get('DOTS_MENU_CONTEXT'))
    context = None
    if interactive and os.name != 'nt':
        context = (TmuxContext.capture(client=args.client) if args.client else
                   TmuxContext.from_environment() if os.environ.get('TMUX') or os.environ.get('DOTS_MENU_CONTEXT') else None)
    if not interactive or not available(context):
        print('wttr: browser unavailable; printing the ordinary weather report.', file=sys.stderr)
        return weather_cli.main(session.arguments(browser=False))
    try:
        return browse(session, args, context)
    except (SelectionEnded, KeyboardInterrupt, EOFError) as error:
        return error.status if isinstance(error, SelectionEnded) else 130


if __name__ == '__main__':
    try:
        if len(sys.argv) != 4 or sys.argv[1] != 'preview': raise ValueError('invalid weather preview request')
        preview(Path(sys.argv[2]), sys.argv[3])
    except (ValueError, OSError) as error:
        print('wttr: ' + clean(str(error)), file=sys.stderr)
        sys.exit(1)
