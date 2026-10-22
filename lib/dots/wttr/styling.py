"""Weather colors and inert widget spans; read published palette data only."""
from datetime import datetime
from dataclasses import dataclass
import math
import os
import re

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
ATTRIBUTES = dict(bold=('1', 'bold'), dim=('2', 'dim'), italic=('3', 'italics'),
                  underline=('4', 'underscore'), reverse=('7', 'reverse'))
SHORT_ATTRIBUTES = dict(b='bold', i='italic', u='underline', d='dim')
DETAIL_COLORS = dict(location='magenta', sunrise='yellow', sunset='orange', humidity='cyan', precip='blue', wind='cyan')
DETAIL_DIRECTIVES = {name + '_color': name for name in DETAIL_COLORS}
HELP_ART = ('█ █ █ ▀█▀ ▀█▀ █▀█', '▀▄▀▄▀  █   █  █▀▄')


def help_banner(ui):
    """Authored help artwork, with one shared horizontal palette gradient."""
    if not ui.color:
        for line in HELP_ART:
            ui.emit(line)
        return
    from resources import cells
    colors = Colors()
    endpoints = []
    for name, fallback in (('blue', '#3B82F6'), ('cyan', '#06B6D4')):
        shade = colors.resolve(name)
        if not isinstance(shade, str) or not HEX.fullmatch(shade):
            shade = fallback
        endpoints.append(tuple(int(shade[i:i+2], 16) for i in (1,3,5)))
    width = max(cells(line) for line in HELP_ART)
    for line in HELP_ART:
        pieces, column = [], 0
        for char in line:
            ratio = column / max(1, width - 1)
            rgb = [round(start + (end - start) * ratio) for start, end in zip(*endpoints)]
            pieces.append(ui.paint(char, '38;2;' + ';'.join(map(str, rgb))))
            column += cells(char)
        ui.emit(''.join(pieces))


@dataclass(frozen=True)
class Style:
    foreground: str | int | None = None
    attributes: frozenset = frozenset()

    def merge(self, other):
        return Style(other.foreground if other.foreground is not None else self.foreground,
                     self.attributes | other.attributes)


def parse_style(value):
    """Parse inert, unordered attributes and at most one foreground."""
    if type(value) is int:
        return Style(color(value))
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('weather style requires attributes and/or one color')
    foreground, attributes, bright = None, set(), False
    for token in value.split():
        token = SHORT_ATTRIBUTES.get(token, token)
        if token in ATTRIBUTES:
            attributes.add(token)
        elif token == 'bright':
            bright = True
        else:
            if foreground is not None:
                raise ValueError('weather style accepts only one foreground color')
            foreground = color(token)
    if bright:
        if foreground not in ANSI_NAMES:
            raise ValueError('bright requires a standard color name: ' + ', '.join(ANSI_NAMES))
        foreground = 'bright_' + foreground
    return Style(foreground, frozenset(attributes))


def parse_widget(template):
    """Literal tokens only: no Python formatting, evaluation or recursive expansion."""
    from core import FIELDS, clean
    if not isinstance(template, str) or len(template) > 1024 or clean(template) != template:
        raise ValueError('template must be one line of at most 1024 characters')
    tokens, end = [], 0
    for match in re.finditer(r'\{\{|\}\}|\{([^{}]*)\}|[^{}]+', template):
        if match.start() != end:
            raise ValueError('unmatched braces in widget template')
        end = match.end()
        field = match[1]
        if field is None:
            literal = match[0]
            tokens.append(('literal', literal[0] if literal in ('{{', '}}') else literal))
        elif field in FIELDS:
            tokens.append(('field', field))
        elif field in ('reset', 'icon_color', 'temp_color', 'feel_color'):
            tokens.append((field, None))
        elif field in DETAIL_DIRECTIVES:
            tokens.append(('detail_color', DETAIL_DIRECTIVES[field]))
        else:
            try:
                tokens.append(('style', parse_style(field)))
            except ValueError as error:
                raise ValueError('invalid widget placeholder; use a field, style, supported icon/temperature color directive or reset') from error
    if end != len(template):
        raise ValueError('unmatched braces in widget template')
    return tokens


def plain_widget(tokens, values):
    return ''.join(value if kind == 'literal' else values[value]
                   for kind, value in tokens if kind in ('literal', 'field'))


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
        return style_sgr(self.style(parse_style(value)))

    def style(self, value):
        if not self.enabled:
            return Style()
        return Style(self.resolve(value.foreground) if value.foreground is not None else None,
                     value.attributes)


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def validate_config(cfg):
    gap = cfg.setdefault('label_gap', 3)
    if type(gap) is not int or not 1 <= gap <= 8:
        raise ValueError('label_gap must be an integer from 1 to 8')
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
    if (not isinstance(thresholds, list) or
            any(not finite_number(v) for v in thresholds) or
            any(a >= b for a, b in zip(thresholds, thresholds[1:]))):
        raise ValueError('temperature_scale.thresholds requires finite, strictly increasing numbers')
    colors = scale.setdefault('colors', list(COLORS))
    if not isinstance(colors, list) or len(colors) != len(thresholds) + 1:
        raise ValueError('temperature_scale.colors requires one more style than thresholds')
    for value in colors:
        parse_style(value)
    for group in ('icon_colors', 'night_icon_colors'):
        mapping = cfg.setdefault(group, {})
        if not isinstance(mapping, dict):
            raise ValueError(group + ' must be a table')
        for key, value in mapping.items():
            if key != 'unknown' and not re.fullmatch(r'\d{3}', key) and not (group == 'icon_colors' and key in DETAIL_COLORS):
                raise ValueError('invalid condition color code')
            parse_style(value)


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
    if not thresholds or value <= thresholds[0]:
        return palette[0]
    for index, boundary in enumerate(thresholds[1:], 1):
        if value < boundary:
            return palette[index]
    return palette[-1]


def sgr(value):
    if value is None or value == 'default':
        return None
    if type(value) is int:
        return '38;5;' + str(value)
    return '38;2;' + ';'.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))


def style_sgr(style):
    codes = [code for name, (code, _) in ATTRIBUTES.items() if name in style.attributes]
    shade = sgr(style.foreground)
    if shade:
        codes.append(shade)
    return ';'.join(codes) or None


def tmux_style(style):
    codes = []
    if style.foreground not in (None, 'default'):
        shade = 'colour' + str(style.foreground) if type(style.foreground) is int else style.foreground
        codes.append('fg=' + shade)
    codes.extend(code for name, (_, code) in ATTRIBUTES.items() if name in style.attributes)
    # Reset each span to the incoming style before adding this span's attributes.
    return '#[default]' + ('#[' + ','.join(codes) + ']' if codes else '')


def condition(code, cfg, night=False):
    code = str(code)
    glyph = cfg['icons'].get(code, cfg['icons'].get('unknown', '?'))
    shade = cfg['icon_colors'].get(code, cfg['icon_colors'].get('unknown', 'default'))
    if night:
        glyph = cfg['night_icons'].get(code, glyph)
        shade = cfg['night_icon_colors'].get(code, shade)
    return glyph, shade


def detail_color(name, cfg):
    return cfg['icon_colors'].get(name, DETAIL_COLORS[name])


def forecast_night(data, day, hour):
    from core import astronomy
    try:
        when = datetime.fromisoformat(day['date']).replace(hour=int(hour)//100, minute=int(hour)%100)
        return astronomy(data, when)[2] == 'night'
    except (KeyError, ValueError, TypeError):
        return False


def widget(template, values, cfg, ui, *, tokens=None):
    tokens = parse_widget(template) if tokens is None else tokens
    mode = os.environ.get('DOTS_COLOR', cfg['widget_color'])
    output = cfg['widget_color_format']
    enabled = mode == 'always' or (mode == 'auto' and not os.environ.get('NO_COLOR') and
               (output == 'tmux' or (ui.stream.isatty() and os.environ.get('TERM', 'dumb') != 'dumb')))
    enabled = enabled and output != 'plain'
    ui.color = enabled
    if not enabled:
        text = plain_widget(tokens, values).strip()
        return text.replace('#', '##') if output == 'tmux' else text
    manual = any(kind not in ('literal', 'field') for kind, _ in tokens)
    spans, previous = [], None
    active = Style()
    for kind, value in tokens:
        if kind == 'reset':
            active = Style()
            continue
        if kind in ('style', 'temp_color', 'feel_color', 'icon_color', 'detail_color'):
            addition = value if kind == 'style' else parse_style(
                detail_color(value, cfg) if kind == 'detail_color' else
                temperature_color(values['temperature' if kind == 'temp_color' else 'feels_like'], cfg)
                if kind in ('temp_color', 'feel_color') else
                condition(values['code'], cfg, values['daylight'] == 'night')[1])
            active = active.merge(addition)
            continue
        style = active
        if not manual:
            shade = 'default'
            if kind == 'field':
                if value in ('temperature', 'feels_like'):
                    shade = temperature_color(values[value], cfg)
                elif value == 'unit' and previous in ('temperature', 'feels_like'):
                    shade = temperature_color(values[previous], cfg)
                elif value == 'icon':
                    shade = condition(values['code'], cfg, values['daylight'] == 'night')[1]
                elif value.endswith('_icon') and value[:-5] in DETAIL_COLORS:
                    shade = detail_color(value[:-5], cfg)
            style = parse_style(shade)
        spans.append((value if kind == 'literal' else values[value], style))
        previous = value if kind == 'field' else None
    colors = Colors()
    spans = [(value, colors.style(style)) for value, style in spans if value]
    if output == 'tmux':
        # Save once for the whole widget; individual spans never nest defaults.
        text = ''.join(tmux_style(style) + value.replace('#', '##') for value, style in spans)
        return '#[push-default]' + text + '#[default]#[pop-default]'
    return ''.join(ui.paint(value, code) if (code := style_sgr(style)) else value
                   for value, style in spans).strip()
