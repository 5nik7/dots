"""In-memory views and compact mode selection over one inert binding snapshot."""
import os
import json
from contextlib import nullcontext

from keys.presentation import binding_label, column_widths, menu_layout, picker_colors, styles, terminal_dimensions
from menus import Entry, Menu, styled_labels


def view(ui, rows, app, mode, columns):
    """Keep original indices while fitting columns to the visible list pane."""
    indices = [i for i, row in enumerate(rows) if mode is None or row['mode'] == mode]
    position = 'down' if columns < 100 else 'right'
    width = max(1, (int(columns * .99) if os.environ.get('TMUX') else columns) - 4)
    if position == 'right':
        width = max(1, width - int(width * .45) - 2)
    widths = column_widths(ui, [rows[i] for i in indices], width, app is None, mode is None)
    codes = styles(ui)
    labels = [binding_label(ui, row, codes, app is None, mode is None, widths) for row in rows]
    return labels, indices, position


def choose_mode(ui, rows, current):
    from interaction import RichSelector, SelectionEvent
    from files.picker import fzf_colors
    modes = [None, *sorted({row['mode'] for row in rows}, key=lambda value: (value.casefold(), value))]
    def entry(mode):
        if mode is None:
            return Entry('all', 'all')
        identity = 'mode:'+mode if mode.isprintable() else 'mode-json:'+json.dumps(mode, ensure_ascii=True)
        return Entry(identity, ui.clean(mode) or '(empty)')
    menu = Menu('keys:modes', 'Modes', tuple(entry(mode) for mode in modes))
    header = 'Enter: select  Esc: back\nCtrl-C: cancel'
    context = getattr(ui, 'menu_context', None)
    size = context.verify() if context else terminal_dimensions()
    popup = bool(os.environ.get('TMUX'))
    labels, width, height = menu_layout(ui, lambda view: styled_labels(menu, view, compact=True),
                                      size=size, header=header, popup=popup)
    focus = modes.index(current) + 1 if current in modes else 1
    with context.selector_environment() if context else nullcontext(None) as environment:
        try:
            selected = RichSelector().fzf(((ui.icon('navigation.keys', '󰌆') + ' ') if ui.icons else '') + 'modes',
                labels, False, None, ui.color, ui.icons, picker_colors(fzf_colors(ui)),
                popup=f'center,{width},{height}' if popup else False, popup_resolved=popup,
                height=height, header=header, info='inline-right', environment=environment,
                navigation={}, navigation_keys={'esc': 'back'}, bindings=[f'load:pos({focus})'])
        except SelectionEvent as event:
            if event.action != 'back':
                raise
            return current
    return modes[selected[0]]
