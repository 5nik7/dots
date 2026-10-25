"""Inert keybrowser labels and content-sized category menus."""
import json
import os
import re
import shutil
import subprocess

from resources import cells, read_data


CATEGORIES = (
    ('all', 'All', '󰌌'), ('apps', 'Apps', '󰀻'),
    ('bash', 'Bash', ''), ('fzf', 'FZF', '󰍉'),
    ('kitty', 'Kitty', '󰄛'), ('nvim', 'Neovim', ''),
    ('powershell', 'PowerShell', ''), ('television', 'Television', '󰔂'),
    ('tmux', 'tmux', ''), ('yazi', 'Yazi', '󰉋'), ('zsh', 'Zsh', ''),
)
MENU_HEADER = 'Enter: open  Esc: cancel'


def styles(ui):
    """Use only the published snapshot, with terminal-palette fallbacks."""
    try:
        palette = json.loads(read_data(ui.resources.root / 'palette.json'))
        colors = palette.get('colors', {})
        if not isinstance(colors, dict):
            colors = {}
    except (ValueError, AttributeError):
        colors = {}

    def sgr(name, fallback, bold=False):
        value = colors.get(name)
        if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            return fallback
        rgb = ';'.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))
        return ('1;' if bold else '') + '38;2;' + rgb

    return sgr('muted', '2;37'), sgr('bright_magenta', '1;95', True)


def binding_label(ui, row, codes):
    muted, key = codes
    separator = ui.paint(' · ', muted)
    return separator.join((ui.paint(row['app'], muted), ui.paint(row['mode'], muted),
                           ui.paint(row['display'], key), ui.clean(row['description']),
                           ui.paint(row['evidence'], muted)))


def menu_rows(ui, coverage=None):
    """Keep identity separate from labels, including unavailable providers."""
    rows = []
    for identity, title, icon in CATEGORIES:
        if coverage is not None and identity in ('all', 'apps'):
            continue
        label = (icon + ' ' if ui.icons else '') + title
        if coverage is not None:
            item = next((c for c in coverage if c['app'] == identity), {})
            count = item.get('count', 0)
            status = 'live' if item.get('live') else 'configured' if count else 'unavailable'
            label += f' · {count} bindings · {status}'
        rows.append((identity, ui.clean(label)))
    return rows


def menu_dimensions(labels):
    """Fit chrome and rows, clamped to the attached client rather than run-shell's TTY."""
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
    width = max(32, max((cells(label) for label in labels), default=0) + 6,
                cells(MENU_HEADER) + 4)
    return min(width, max(1, columns - 2)), min(len(labels) + 6, max(1, lines - 2))


def picker_colors(colors):
    # The shared theme's fg+:strip discards row ANSI. Keep field styling when selected.
    entries = [entry for entry in colors.split(',') if entry and not entry.startswith('fg+:')]
    return ','.join([*entries, 'fg+:-1:regular'])
