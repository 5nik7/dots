"""Inert, themed project/session rows and previews; action input lives elsewhere."""
from contextlib import nullcontext
import os
from pathlib import Path
import shutil
import sys

from interaction import RichSelector, SelectionEvent, rich_fzf_available, terminal
from menu_tmux import read_request, request_file
from picker_style import fit, picker_colors, styles, named_styles
from resources import clean, cells
from menu_pager import ANSI


def short_path(path):
    try:
        relative = path.relative_to(Path.home())
        return '~' if relative == Path('.') else '~/' + str(relative)
    except ValueError:
        return str(path)


# The browser's event map and its reference share these descriptions. Enter,
# Ctrl-C and preview controls are provided by the shared selector.
CONTROLS = (
    ('enter', 'Enter', 'Open / switch / create', None),
    ('f1', 'F1', 'Actions', 'actions'),
    ('alt-h', 'Alt-H', 'Keybindings', 'keys'),
    ('alt-n', 'Alt-N', 'New session', 'new'),
    ('alt-r', 'Alt-R', 'Rename session', 'rename'),
    ('alt-d', 'Alt-D', 'Delete (confirmation)', 'delete'),
    ('alt-t', 'Alt-T', 'New Termux tab', 'termux'),
    ('esc', 'Esc', 'Back / close', 'back'),
    ('ctrl-c', 'Ctrl-C', 'Quit the browser', None),
    ('alt-p', 'Alt-P', 'Toggle preview', None),
    ('alt-j', 'Alt-J', 'Scroll preview down', None),
    ('alt-k', 'Alt-K', 'Scroll preview up', None),
)
KEY_HINT = 'Alt-H: keys'


def controls(termux=False, intent=None):
    return tuple((key, label, ('Choose to ' + intent if intent and key == 'enter' else description), action)
                 for key, label, description, action in CONTROLS if termux or key != 'alt-t')


def show_keys(*, context=None, termux=False, intent=None):
    from files.catalog import Presentation
    from files.picker import fzf_colors
    from menus import dimensions
    from progress import permanent_output
    ui = Presentation(terminal=True) if context else Presentation()
    muted, emphasis, _ = styles(ui)
    labels = [ui.paint(fit(label, 7), emphasis) + ui.paint(' · ', muted) + description
              for _, label, description, _ in controls(termux, intent)]
    header = 'Esc / Alt-H: back  Ctrl-C: quit'
    size = context.verify() if context else shutil.get_terminal_size((80, 24))
    width, height = dimensions([ANSI.sub('', label) for label in labels], 'dots·tmux·keys', header, size=size)
    with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
        try:
            RichSelector(backend='fzf').fzf('dots·tmux·keys', labels, False, None,
                ui.color, ui.icons, picker_colors(fzf_colors(ui)),
                popup=f'center,{width},{height}' if context else False, height=height,
                header=header, environment=environment, navigation={},
                navigation_keys={'esc': 'back', 'alt-h': 'back'}, bindings=['enter:ignore'])
        except SelectionEvent as event:
            if event.action != 'back':
                raise


def plural(count, noun):
    return f'{count} {noun}' + ('' if count == 1 else 's')


def preview_text(row, ui, codes):
    muted, emphasis = codes['muted'], codes['emphasis']
    current_project = any(s.current for s in row.sessions)
    noncurrent_style = codes['accent'] if row.project else '1;' + codes['blue']
    title_style = '1;' + codes['light_foreground'] if not row.sessions else emphasis if current_project else noncurrent_style
    title = ui.paint(clean(row.label), title_style)
    if row.project:
        count_style = codes['orange'] if row.sessions else codes['red']
        title += ui.paint(' · ', muted) + ui.paint('[' + plural(len(row.sessions), 'session') + ']', count_style)
    lines = [title]
    if row.project:
        _, _, path_style = ui.resources.describe(row.project.root, 'dir')
        path = ('󰉋 ' if ui.icons else '') + clean(short_path(row.project.root))
        lines.append(ui.paint('Project: ', muted) + ui.paint(path, path_style))
    for session in row.sessions:
        name_style = emphasis if session.current else noncurrent_style
        name = ui.paint(clean(session.name) + ': ', name_style) if len(row.sessions) > 1 or session.name != row.label else ''
        windows = ui.paint(plural(session.windows, 'window'), codes['green'])
        clients = ui.paint(f'{session.attached_clients} attached', codes['yellow'] if session.attached_clients >= 1 else muted)
        current = ui.paint(' · current', '1;' + codes['bright_green']) if session.current else ''
        lines.append('  ' + name + windows + ui.paint(' · ', muted) + clients + current)
    return '\n'.join(lines) + '\n'


def preview_height(previews, lines):
    """Stable per-view height for clipped lines and two preview borders."""
    maximum = min(8, max(1, lines - 11))  # Leave room for chrome and choices.
    largest = max((len(ANSI.sub('', text).splitlines()) for text in previews), default=0)
    return min(maximum, max(3, largest + 2))


def render(rows, ui, width):
    codes = named_styles(ui)
    muted, emphasis = codes['muted'], codes['emphasis']
    name_width = max(8, min(26, width // 2 - 3, max((cells(clean(row.label)) for row in rows), default=8)))
    labels, previews = [], []
    duplicates = {r.label for r in rows if sum(s.label == r.label for s in rows) > 1}
    for row in rows:
        count = len(row.sessions)
        current = any(s.current for s in row.sessions)
        icon = ('' if row.project else '') + ' ' if ui.icons else ''
        noncurrent_style = codes['accent'] if row.project else '1;' + codes['blue']
        name_style = emphasis if current else noncurrent_style if count else codes['light_foreground']
        name = ui.paint(icon + fit(clean(row.label), name_width), name_style)
        detail = f'{count} session' + ('s' if count != 1 else '') if row.project else f'{row.sessions[0].windows} win'
        if width < 52 and count:
            detail = f'[{count}]' if row.project else f'{row.sessions[0].windows}w'
        count_text = detail
        current_text = ' · ' + (' ' if ui.icons else '') + 'current' if current else ''
        if current:
            detail += current_text
        elif not count:
            detail = 'no session'
        if row.project and row.label in duplicates:
            detail += ' · ' + short_path(row.project.root)
        detail = fit(clean(detail), max(1, width - cells(icon) - name_width - 3)).rstrip()
        if count and (row.project or current):
            # Clip first, then keep count, current marker and path styles separate.
            count_end = min(len(count_text), len(detail))
            marker_end = min(len(count_text) + len(current_text), len(detail))
            styled_detail = ui.paint(detail[:count_end], codes['orange'])
            if detail[count_end:marker_end]:
                styled_detail += ui.paint(detail[count_end:marker_end], '1;' + codes['bright_green'])
            if detail[marker_end:]:
                styled_detail += ui.paint(detail[marker_end:], muted)
        else:
            styled_detail = ui.paint(detail, muted)
        labels.append(name + ui.paint(' · ', muted) + styled_detail)
        previews.append(preview_text(row, ui, codes))
    return labels, previews


def pick(rows, *, context=None, frame=None, termux=False, prompt='dots·tmux·sessions', intent=None):
    from files.catalog import Presentation
    from files.picker import fzf_colors
    from progress import permanent_output
    frame = frame if frame is not None else {}
    ui = Presentation(terminal=True) if context else Presentation()
    if context is None and not terminal():
        raise ValueError('menu browsing requires a terminal or explicit tmux context')
    reason = ''
    if not rich_fzf_available():
        reason = 'FZF unavailable or preview shell unavailable'
    elif context:
        import subprocess
        result = subprocess.run(['fzf', '--help'], capture_output=True, timeout=5)
        if result.returncode or b'--popup' not in result.stdout:
            reason = 'FZF popup support unavailable'
    size = context.verify() if context else shutil.get_terminal_size((80, 24))
    columns, lines = size
    width = max(1, columns - 2)
    list_width = width - 4
    labels, previews = render(rows, ui, list_width)
    if reason:
        print('dots menu: ' + reason + '; listing choices without selecting.', file=sys.stderr)
        ui.heading('Tmux sessions')
        for label in labels:
            ui.emit('  ' + label)
        return None
    keys = {key: action for key, _, _, action in controls(termux, intent) if action is not None}
    header = KEY_HINT
    preview_lines = preview_height(previews, lines)
    height = min(max(10, len(rows) + 6 + preview_lines), max(1, lines - 2))
    focus = next((i for i, row in enumerate(rows) if row.id == frame.get('selected')), None)
    with request_file(dict(schema=1, previews=previews)) as path:
        preview = ('"$DOTS_SESSION_PYTHON" -B "$DOTS_SESSION_UI" preview "$DOTS_SESSION_PREVIEW" {1}', '',
                   dict(DOTS_SESSION_PYTHON=sys.executable, DOTS_SESSION_UI=str(Path(__file__).resolve()),
                        DOTS_SESSION_PREVIEW=str(path)))
        with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
            try:
                selection = RichSelector(backend='fzf').fzf(clean(prompt), labels, False, preview,
                    ui.color, ui.icons, picker_colors(fzf_colors(ui)),
                    popup=f'center,{width},{height}' if context else False, height=height,
                    preview_position='down', preview_lines=preview_lines, preview_wrap=False, query=frame.get('query', ''),
                    header=header, environment=environment, info='inline-right', hscroll=False,
                    navigation=frame, navigation_keys=keys, event_selection=True,
                    focus_index=focus)
            except SelectionEvent as event:
                if event.index is not None:
                    frame['selected'] = rows[event.index].id
                raise
    frame['selected'] = rows[selection[0]].id
    return rows[selection[0]]


def preview(path, token):
    import re
    data = read_request(path)['previews']
    if not re.fullmatch(r'0|[1-9][0-9]*', token) or int(token) >= len(data):
        raise ValueError('unknown session preview token')
    print(data[int(token)], end='')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'preview':
        preview(sys.argv[2], sys.argv[3])
    else:
        sys.exit(2)
