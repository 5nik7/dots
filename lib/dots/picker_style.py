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

    from style_config import current
    preferences = current()
    if preferences:
        import copy
        preferences = copy.copy(preferences)
        preferences._palette = colors
    semantic = dict(muted='ui.muted', accent='ui.accent', foreground='ui.foreground', green='status.success', yellow='status.warning', red='status.error', blue='ui.label', hint='ui.heading', warning='status.warning')

    def sgr(name, fallback, bold=False):
        if preferences and name in semantic:
            return preferences.sgr(semantic[name], dict(fg=name, bold=bold))
        value = colors.get(name)
        if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            return fallback
        rgb = ';'.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))
        return ('1;' if bold else '') + '38;2;' + rgb

    foreground = sgr('foreground', '39')
    return dict(muted=sgr('muted', '2;37'), emphasis=sgr('bright_magenta', '1;95', True),
                orange=sgr('orange', '38;5;208'), accent=sgr('accent', '1;35', True),
                green=sgr('green', '32'), yellow=sgr('yellow', '33'), blue=sgr('blue', '34'),
                bright_green=sgr('bright_green', '92'), bright_red=sgr('bright_red', '91'),
                bold_hint=sgr('hint', '1;36', True), bold_muted=sgr('muted', '1;37', True),
                bold_bright_red=sgr('bright_red', '1;91', True),
                bold_bright_green=sgr('bright_green', '1;92', True),
                bold_warning=sgr('warning', '1;33', True),
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
