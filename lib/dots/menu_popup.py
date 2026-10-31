"""Dedicated appearance for Dots selectors and their owned terminal popups."""
import re
import shutil

POSITIONS = ('center', 'top', 'bottom', 'left', 'right')
BORDERS = ('rounded', 'sharp', 'double', 'bold', 'none')
SIZES = ('auto', 'fit', 'fill')
SIZE_PRESETS = ('50%', '75%', '90%', '100%')


def valid_size(value):
    return (type(value) is int and 1 <= value <= 10000 or isinstance(value, str) and
            (value in SIZES or re.fullmatch(r'(?:[1-9][0-9]?|100)%', value) is not None))


def viewport(environment=None):
    """The addressed client can differ from the process's stdout terminal."""
    env = environment or {}
    try:
        size = tuple(int(env[key]) for key in ('DOTS_MENU_COLUMNS', 'DOTS_MENU_LINES'))
        if all(0 < n <= 100000 for n in size): return size
    except (KeyError, TypeError, ValueError): pass
    return shutil.get_terminal_size((80, 24))


def extent(value, available):
    return max(1, available * int(value[:-1]) // 100) if isinstance(value, str) and value.endswith('%') else int(value)


def dimensions(options, automatic, size, content=None):
    result = []
    for index, key in enumerate(('width', 'height')):
        available = max(1, size[index])
        choice = options.get(key, 'auto')
        baseline = extent(automatic[index], available)
        if choice == 'auto': target = baseline
        elif choice == 'fill': target = available
        elif choice == 'fit': target = min(content[index] if content else baseline, max(1, available * 9 // 10))
        else: target = extent(choice, available)
        minimum = 1 if choice == 'auto' else (32 if index == 0 else 6)
        result.append(min(available, max(minimum, target)))
    return tuple(result)


def automatic_size(spec):
    values = spec.split(',') if isinstance(spec,str) else ['90%', '90%']
    if values[0] in POSITIONS: values = values[1:]
    values = values[:2] or ['90%', '90%']
    return tuple(values if len(values)==2 else values*2)


def content_size(labels, title, header, size, options, wrap=False, automatic=None):
    """Measure inert display cells, never run a preview to discover its content."""
    from resources import cells
    ansi = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))')
    # NUL-delimited FZF records may contain trusted display line breaks.
    lengths = [cells(line) for text in labels for line in ansi.sub('', str(text)).split('\n')]
    chrome = [cells(ansi.sub('', text)) for text in [title + ': ', *header.splitlines()]]
    width = max([0, *lengths, *chrome]) + 6
    fitted_width = dimensions(options, automatic or size, size, (width, size[1]))[0]
    rows = sum(max(1, (n + max(1, fitted_width-6)-1) // max(1, fitted_width-6)) for n in lengths) if wrap else len(lengths)
    return width, rows + len(header.splitlines()) + 5


def preferences():
    from config_values import value
    return value('apps.menu.popup', {})


def geometry(spec, options, *, size=None, content=None):
    """Auto preserves controller geometry; explicit controls use client bounds."""
    parts = spec.split(',') if isinstance(spec, str) else ['center', '90%']
    position = options.get('position', 'center')
    if parts[0] in POSITIONS:
        parts[0] = position
    else:
        parts.insert(0, position)
    if any(options.get(key, 'auto') != 'auto' for key in ('width', 'height')):
        width, height = dimensions(options, automatic_size(spec), size or viewport(), content)
        parts = [position, str(width), str(height), *parts[3:]]
    return ','.join(parts)


def border(options):
    return options.get('border', 'rounded')


def colors(options):
    from fzf_config import colors as native_colors
    from style_config import current
    return native_colors({'colors': options.get('colors', {'border': 'accent'})}, current())


def tmux_flags(options, height, lines, *, color=True, icons=True):
    """Native host styles are per-popup arguments, never server option writes."""
    position = options.get('position', 'center')
    x = '0' if position == 'left' else 'R' if position == 'right' else 'C'
    # tmux's Y coordinate is the bottom edge of the popup.
    y = str(height) if position == 'top' else str(lines) if position == 'bottom' else 'C'
    frame = border(options)
    flags = ['-x' + x, '-y' + y]
    if frame == 'none':
        flags += ['-B']
    else:
        flags += ['-b', {'sharp': 'single', 'bold': 'heavy'}.get(frame, frame) if icons else 'simple']
    if not color:
        return flags + ['-s', 'fg=default,bg=default', '-S', 'fg=default,bg=default']
    values = dict(part.split(':', 1) for part in colors(options).split(',') if part)
    def shade(value):
        return 'default' if value == '-1' else 'colour' + value if value.isdigit() else value
    body = ','.join(key + '=' + shade(values[key]) for key in ('fg', 'bg') if key in values)
    outline = ','.join(key + '=' + shade(values[source]) for key, source in (('fg','border'), ('bg','bg')) if source in values)
    if body: flags += ['-s', body]
    if outline: flags += ['-S', outline]
    return flags
