"""Inert keybrowser labels and content-sized category menus."""
import os
import re
import shutil
import subprocess

from resources import cells
from picker_style import styles, fit, picker_colors


CATEGORIES = (
    ('all', 'All', '󰌌'),
    ('bash', 'Bash', ''), ('codex', 'Codex CLI', '󰚩'), ('fzf', 'FZF', '󰍉'),
    ('kitty', 'Kitty', '󰄛'), ('nvim', 'Neovim', ''),
    ('powershell', 'PowerShell', ''), ('television', 'Television', '󰔂'),
    ('tmux', 'tmux', ''), ('yazi', 'Yazi', '󰉋'), ('zsh', 'Zsh', ''),
)
MENU_HEADER = 'Enter: open  Esc: cancel'


def column_widths(ui, rows, width, show_app=True, show_mode=True):
    limits = ([('app', 12)] if show_app else []) + ([('mode', 18)] if show_mode else []) + [('display', 16)]
    widths = {field: max(1, min(cap, max((cells(ui.clean(row[field])) for row in rows), default=0)))
              for field, cap in limits}
    # Reserve separators and twelve cells of description. On small screens,
    # shrink the widest column first (keys, then mode, then app on ties).
    budget = max(len(widths), width - 12 - 3 * len(widths))
    order = list(widths)
    while sum(widths.values()) > budget:
        field = max(order, key=lambda name: (widths[name], order.index(name)))
        widths[field] -= 1
    return widths


def binding_label(ui, row, codes, show_app=True, show_mode=True, widths=None):
    muted, key, mode = codes
    def field(name, code):
        text = ui.clean(row[name])
        return ui.paint(fit(text, widths[name]) if widths is not None else text, code)
    separator = ui.paint(' · ', muted)
    fields = [field('app', muted)] if show_app else []
    if show_mode:
        fields.append(field('mode', mode))
    fields.extend((field('display', key), ui.clean(row['description']),
                   ui.paint(row['evidence'], muted)))
    return separator.join(fields)


def binding_prompt(ui, app=None, mode=None):
    return ('󰌆 ' if ui.icons else '') + ui.clean((app or 'all') + '·' + mode if mode is not None else app or '')


def menu_rows(ui, coverage, *, include_all=True):
    """Render nonempty categories from the same filtered snapshot as the browser."""
    rows = []
    counts = {item['app']: item['count'] for item in coverage}
    muted = styles(ui)[0]
    for identity, title, icon in CATEGORIES:
        if identity == 'all' and not include_all:
            continue
        count = sum(counts.values()) if identity == 'all' else counts.get(identity, 0)
        if not count:
            continue
        label = ui.clean((icon + ' ' if ui.icons else '') + title)
        rows.append((identity, label + ui.paint(f' · [{count}]', muted)))
    return rows


def terminal_dimensions():
    """Use the attached client rather than run-shell's nonexistent terminal."""
    columns, lines = shutil.get_terminal_size((80, 24))
    if os.environ.get('TMUX') and shutil.which('tmux'):
        try:
            command = ['tmux', 'display-message', '-p']
            if os.environ.get('TMUX_PANE'):
                command += ['-t', os.environ['TMUX_PANE']]
            result = subprocess.run(command + ['#{client_width} #{client_height}'],
                                    capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                width, height = map(int, result.stdout.split())
                if width > 0 and height > 0:
                    columns, lines = width, height
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    return columns, lines


def menu_dimensions(labels, *, size=None, header=MENU_HEADER):
    """Fit chrome and rows within the caller's terminal."""
    columns, lines = size or terminal_dimensions()
    width = max(32, max((cells(re.sub(r'\x1b\[[0-9;]*m', '', label)) for label in labels), default=0) + 6,
                max((cells(line) for line in header.splitlines()), default=0) + 4)
    return min(width, max(1, columns - 2)), min(len(labels) + len(header.splitlines()) + 5, max(1, lines - 2))
