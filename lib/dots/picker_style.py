"""Shared semantic field styles and display-cell fitting for inert pickers."""
import json
import re
from resources import cells, read_data


def named_styles(ui):
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

    foreground = sgr('foreground', '39')
    return dict(muted=sgr('muted', '2;37'), emphasis=sgr('bright_magenta', '1;95', True),
                orange=sgr('orange', '38;5;208'), accent=sgr('accent', '1;35', True),
                green=sgr('green', '32'), yellow=sgr('yellow', '33'), blue=sgr('blue', '34'),
                bright_green=sgr('bright_green', '92'),
                foreground=foreground, light_foreground=sgr('light_foreground', foreground),
                red=sgr('red', '31'))


def styles(ui):
    # Preserve the original key-picker tuple; its third field is orange.
    codes = named_styles(ui)
    return codes['muted'], codes['emphasis'], codes['orange']


def fit(value, width):
    """Pad or shorten already sanitized text by terminal cells, before styling."""
    if cells(value) > width:
        prefix, used = '', 0
        for char in value:
            size = cells(char)
            if used + size > width - 1:
                break
            prefix += char
            used += size
        value = prefix + '…'
    return value + ' ' * max(0, width - cells(value))


def picker_colors(colors):
    # The shared theme's fg+:strip discards row ANSI. Keep field styling when selected.
    entries = [entry for entry in colors.split(',') if entry and not entry.startswith('fg+:')]
    return ','.join([*entries, 'fg+:-1:regular'])
