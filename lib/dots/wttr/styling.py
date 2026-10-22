"""Weather colors and inert widget spans; read published palette data only."""
from datetime import datetime
import math
import os
import re
import string

COLORS = ['cyan', 'blue', 'green', 'yellow', 'orange', 'red']
THRESHOLDS = [32, 60, 75, 85, 95]
HEX = re.compile(r'#[0-9a-fA-F]{6}\Z')
PALETTE_LIMIT = 2 * 1024 * 1024
ANSI_NAMES = 'black red green yellow blue magenta cyan white'.split()
FALLBACKS = {name: i for i, name in enumerate(ANSI_NAMES)}
FALLBACKS.update({'bright_' + name: i + 8 for i, name in enumerate(ANSI_NAMES)})
FALLBACKS.update(orange=208, foreground='default', background=0, muted=8, accent=4)
ALIASES = dict(gray='muted', grey='muted', purple='magenta', indigo='blue')
THEME_KEYS = dict(black='color0', white='color7', bright_black='color8',
                  bright_white='color15')


def color(value):
    if type(value) is int and 0 <= value <= 255:
        return value
    if isinstance(value, str):
        if re.fullmatch(r'[0-9]{1,3}', value) and int(value) <= 255:
            return int(value)
        if value == 'default' or HEX.fullmatch(value) or value in FALLBACKS or value in ALIASES:
            return value
    raise ValueError('weather colors must be a supported theme color name, #RRGGBB, 0–255 or default')


class Colors:
    """One lazy snapshot per render, never a theme command or a persistent cache."""
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.palette = None

    def resolve(self, value):
        if not self.enabled:
            return 'default'
        value = color(value)
        if type(value) is int or value == 'default' or HEX.fullmatch(value):
            return value
        name = ALIASES.get(value, value)
        if self.palette is None:
            from core import read_regular, load_json
            from file_platform import state_root
            self.palette = {}
            try:
                doc = load_json(read_regular(state_root() / 'current/theme/palette.json', PALETTE_LIMIT))
                colors = doc.get('colors') if isinstance(doc, dict) else None
                if isinstance(colors, dict):
                    self.palette = {key: shade for key, shade in colors.items()
                                    if isinstance(shade, str) and HEX.fullmatch(shade)}
            except (OSError, ValueError, RecursionError):
                pass
        return self.palette.get(THEME_KEYS.get(name, name), FALLBACKS[name])

    def sgr(self, value):
        return sgr(self.resolve(value))


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def validate_config(cfg):
    cfg.setdefault('show_location_attribution', True)
    if type(cfg['show_location_attribution']) is not bool:
        raise ValueError('show_location_attribution must be true or false')
    for key, default, choices in [('widget_color', 'auto', ('auto', 'always', 'never')),
                                  ('widget_color_format', 'ansi', ('ansi', 'plain', 'tmux'))]:
        if cfg.setdefault(key, default) not in choices:
            raise ValueError('invalid ' + key)
    scale = cfg.setdefault('temperature_scale', {})
    if not isinstance(scale, dict):
        raise ValueError('temperature_scale must be a table')
    if scale.setdefault('unit', 'F') not in ('F', 'C'):
        raise ValueError('temperature_scale.unit must be F or C')
    default = THRESHOLDS if scale['unit'] == 'F' else [(v-32)*5/9 for v in THRESHOLDS]
    thresholds = scale.setdefault('thresholds', list(default))
    if (not isinstance(thresholds, list) or len(thresholds) != 5 or
            any(not finite_number(v) for v in thresholds) or
            any(a >= b for a, b in zip(thresholds, thresholds[1:]))):
        raise ValueError('temperature_scale.thresholds requires five finite, increasing numbers')
    colors = scale.setdefault('colors', list(COLORS))
    if not isinstance(colors, list) or len(colors) != 6:
        raise ValueError('temperature_scale.colors requires six colors')
    for value in colors:
        color(value)
    for group in ('icon_colors', 'night_icon_colors'):
        mapping = cfg.setdefault(group, {})
        if not isinstance(mapping, dict):
            raise ValueError(group + ' must be a table')
        for key, value in mapping.items():
            if key != 'unknown' and not re.fullmatch(r'\d{3}', key):
                raise ValueError('invalid condition color code')
            color(value)


def temperature_color(value, cfg):
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        return 'default'
    if not math.isfinite(value):
        return 'default'
    scale = cfg['temperature_scale']
    source = 'F' if cfg['units'] == 'us' else 'C'
    if source != scale['unit']:
        value = value * 9/5 + 32 if source == 'C' else (value-32)*5/9
    thresholds, palette = scale['thresholds'], scale['colors']
    if value <= thresholds[0]:
        return palette[0]
    for index, boundary in enumerate(thresholds[1:], 1):
        if value < boundary:
            return palette[index]
    return palette[-1]


def sgr(value):
    if value == 'default':
        return None
    if type(value) is int:
        return '38;5;' + str(value)
    return '38;2;' + ';'.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))


def condition(code, cfg, night=False):
    code = str(code)
    glyph = cfg['icons'].get(code, cfg['icons'].get('unknown', '?'))
    shade = cfg['icon_colors'].get(code, cfg['icon_colors'].get('unknown', 'default'))
    if night:
        glyph = cfg['night_icons'].get(code, glyph)
        shade = cfg['night_icon_colors'].get(code, shade)
    return glyph, shade


def forecast_night(data, day, hour):
    from core import astronomy
    try:
        when = datetime.fromisoformat(day['date']).replace(hour=int(hour)//100, minute=int(hour)%100)
        return astronomy(data, when)[2] == 'night'
    except (KeyError, ValueError, TypeError):
        return False


def widget(template, values, cfg, ui):
    from core import format_widget
    # Keep the existing strict field grammar and control-free values.
    format_widget(template, values)
    mode = os.environ.get('DOTS_COLOR', cfg['widget_color'])
    output = cfg['widget_color_format']
    enabled = mode == 'always' or (mode == 'auto' and not os.environ.get('NO_COLOR') and
               (output == 'tmux' or (ui.stream.isatty() and os.environ.get('TERM', 'dumb') != 'dumb')))
    enabled = enabled and output != 'plain'
    ui.color = enabled
    spans, previous = [], None
    for literal, field, _, _ in string.Formatter().parse(template):
        if literal:
            spans.append((literal, 'default'))
            previous = None
        if field is None:
            continue
        shade = 'default'
        if field in ('temperature', 'feels_like'):
            shade = temperature_color(values[field], cfg)
        elif field == 'unit' and previous in ('temperature', 'feels_like'):
            shade = temperature_color(values[previous], cfg)
        elif field == 'icon':
            shade = condition(values['code'], cfg, values['daylight'] == 'night')[1]
        spans.append((values[field], shade))
        previous = field
    if not enabled:
        text = format_widget(template, values).strip()
        return text.replace('#', '##') if output == 'tmux' else text
    colors = Colors()
    spans = [(value, colors.resolve(shade)) for value, shade in spans]
    if output == 'tmux':
        # Save once for the whole widget; individual spans never nest defaults.
        text = ''.join(('#[fg=' + ('colour' + str(shade) if type(shade) is int else shade) + ']'
                        if shade != 'default' else '#[default]') +
                       value.replace('#', '##') for value, shade in spans)
        return '#[push-default]' + text + '#[default]#[pop-default]'
    return ''.join(ui.paint(value, sgr(shade)) if shade != 'default' else value for value, shade in spans).strip()
