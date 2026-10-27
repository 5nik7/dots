"""Bounded Anodize branding. No engine, terminal queries, or persistent state."""
import argparse
import base64
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ASSETS = Path(__file__).with_name('assets')
MODES = ('text', 'auto', 'kitty', 'chafa')
LAYOUTS = ('auto', 'base', 'horizontal', 'stacked', 'icon')
TIMEOUT = 1.0
# Exact owner-supplied LOGO1, also used when assets are missing or invalid.
BASE_LOGO = (
    '⠀⠀⠀⠀⠀⠀⠀⣰⡄⠀⠀⠀⠀⠀⠀',
    '⠀⠀⠀⠀⠀⢀⣼⣿⣿⣄⠀⠀⠀⠀⠀',
    '⠀⠀⠀⠀⠠⢾⡿⠃⠘⣿⣆⠀⠀⠀⠀',
    '⠀⠀⠀⣰⣷⣦⣤⣀⠀⠘⣿⣦⠀⠀⠀',
    '⠀⠀⣴⣿⡟⠙⠻⢿⣿⣶⣾⣿⣧⡀⠀',
    '⢀⣾⣿⠏⠀⠀⠀⠀⠀⠉⠛⠿⣿⣷⡀',
)


class TextLogo(list):
    """Plain artwork with region identity retained through layout fallback."""
    def __init__(self, lines, layout='base'):
        super().__init__(lines)
        width, height = max(map(len, self), default=0), len(self)
        self.regions = ()
        if layout == 'horizontal':
            self.regions = ((0, 0, 16, height), (16, 0, width, height))
        elif layout == 'stacked':
            self.regions = ((0, 0, width, 8), (0, 9, width, height))


class LogoOption(argparse.Action):
    """Apply while parsing so options preceding --help affect its header too."""
    def __call__(self, parser, namespace, values, option_string=None):
        os.environ['ANODIZE_' + self.dest.upper()] = values
        setattr(namespace, self.dest, values)


def add_options(parser):
    parser.add_argument('--logo', choices=MODES, action=LogoOption,
                        help='Logo renderer (default: text; ANODIZE_LOGO)')
    parser.add_argument('--logo-layout', choices=LAYOUTS, action=LogoOption,
                        help='Logo layout; base selects LOGO1 (ANODIZE_LOGO_LAYOUT)')


def configure_options(values):
    """Core-owned native help/dispatch options; never load the extension."""
    remaining = []
    values = iter(values)
    for token in values:
        if token == '--':
            remaining.extend([token, *values])
            break
        key, separator, value = token.partition('=')
        if key not in ('--logo', '--logo-layout'):
            remaining.append(token)
            continue
        if not separator:
            value = next(values, '')
        choices = MODES if key == '--logo' else LAYOUTS
        if value not in choices:
            raise ValueError('Expected ' + key + '=' + '|'.join(choices))
        os.environ['ANODIZE_' + key[2:].replace('-', '_').upper()] = value
    return remaining


def dimensions(stream):
    try:
        size = os.get_terminal_size(stream.fileno())
        if size.columns > 0 and size.lines > 0:
            return size.columns, size.lines
    except (OSError, ValueError, AttributeError):
        pass
    def positive(name, default):
        try:
            value = int(os.environ.get(name, ''))
            return value if value > 0 else default
        except ValueError:
            return default
    return positive('COLUMNS', 80), positive('LINES', 24)


def layout_for(columns, rows, full, requested):
    width = max(1, columns - 1)
    height = max(1, min(8 if full else 3, rows // 3))
    if not full or height < 6 or width < 19:
        return 'compact', width, height
    layout = requested if requested in LAYOUTS else 'auto'
    if layout == 'auto':
        layout = 'horizontal' if columns >= 80 else 'stacked'
    if layout == 'horizontal' and width < 39:
        layout = 'stacked'
    if layout == 'stacked' and height < 8:
        layout = 'icon'
    return layout, width, height


def read_text_asset(path, width, height):
    """ASCII and braille cells are one column each, including blank braille.

    Reject controls and other character sets rather than guessing their width
    or passing terminal escapes through. Keep the Bash reader equivalent.
    """
    try:
        lines = path.read_text(encoding='utf-8').split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        if (lines and len(lines) <= height and max(map(len, lines)) <= width
                and all(32 <= ord(c) <= 126 or 0x2800 <= ord(c) <= 0x28ff for line in lines for c in line)
                and any(c not in (' ', '\u2800') for line in lines for c in line)):
            return lines
    except (OSError, UnicodeError):
        pass
    return None


def text_lines(layout, width, height):
    if layout in ('auto', 'horizontal'):
        candidates = ['horizontal.txt']
    elif layout == 'stacked':
        candidates = ['stacked.txt']
    else:
        candidates = []
    for name in candidates:
        lines = read_text_asset(ASSETS / name, width, height)
        if lines:
            return TextLogo(lines, Path(name).stem)
    if layout in ('icon', 'stacked'):
        # Compare actual widths, not lexicographic filenames or claimed sizes.
        best, best_width = None, -1
        for path in sorted(ASSETS.glob('logo-*.txt')):
            number = path.stem[5:]
            if not number.isascii() or not number.isdecimal() or not number.strip('0'):
                continue
            lines = read_text_asset(path, width, height)
            if lines and max(map(len, lines)) > best_width:
                best, best_width = lines, max(map(len, lines))
        if best:
            return TextLogo(best, 'icon')
    return TextLogo(BASE_LOGO)


def unicode_output(stream):
    try:
        '\u2800\u28ff'.encode(getattr(stream, 'encoding', None) or 'utf-8')
        return True
    except (UnicodeError, LookupError):
        return False


def text_banner(width, rows, *, requested=None, full=False):
    """Exact default artwork; viewport height never substitutes another mark."""
    width = max(1, width)
    requested = requested or os.environ.get('ANODIZE_LOGO_LAYOUT', 'auto')
    if requested not in LAYOUTS or requested == 'auto':
        requested = 'horizontal' if full else 'base'
    return text_lines(requested, width, 16)


def utf8_output(stream):
    """Human branding must survive legacy Python output encodings intact."""
    if not unicode_output(stream) and hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')


def kitty_supported():
    # Be conservative. TERM propagated through an unknown multiplexer is not
    # evidence of passthrough support. No queries may consume the user's input.
    return (not any(os.environ.get(k) for k in ('TMUX', 'STY', 'ZELLIJ'))
            and (os.environ.get('TERM') == 'xterm-kitty'
                 or (os.environ.get('KITTY_WINDOW_ID') and os.environ.get('TERM', '').startswith('xterm'))))


def asset(layout, color):
    layout = 'icon' if layout in ('compact', 'base') else layout
    variant = 'white'
    if color:
        variant = 'color'
        if layout != 'icon':
            try:
                light = int(os.environ.get('COLORFGBG', '').split(';')[-1]) in range(7, 16)
            except ValueError:
                light = False
            variant += '-black' if light else '-white'
    return ASSETS / f'{layout}-{variant}.png'


def image_box(path, width, height):
    data = path.read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) > 256 * 1024:
        raise ValueError('invalid bundled PNG')
    pixels_w, pixels_h = struct.unpack('>II', data[16:24])
    if not pixels_w or not pixels_h:
        raise ValueError('empty PNG')
    # Standard terminal cell aspect (1:2), without querying pixel geometry.
    ratio = 2 * pixels_w / pixels_h
    cols = min(width, max(1, round(height * ratio)))
    lines = min(height, max(1, math.ceil(cols / ratio)))
    return data, cols, lines


def kitty_image(path, width, height):
    data, cols, rows = image_box(path, width, height)
    encoded = base64.b64encode(data).decode('ascii')
    # Reserve rows first so rendering near the bottom can scroll normally.
    output = '\n' * rows + f'\033[{rows}A\r'
    for offset in range(0, len(encoded), 4096):
        chunk = encoded[offset:offset+4096]
        more = int(offset + 4096 < len(encoded))
        control = f'a=T,f=100,t=d,q=2,C=1,c={cols},r={rows},' if offset == 0 else ''
        output += f'\033_G{control}m={more};{chunk}\033\\'
    return output + f'\033[{rows}B\r'


def chafa_image(path, width, height, color):
    executable = shutil.which('chafa')
    if not executable:
        return None
    result = subprocess.run([
        executable, '--probe=off', '--polite=on', '--format=symbols', '--animate=off',
        '--relative=off', '--optimize=0', '--fg-only', '--threads=1',
        '--symbols=braille',
        '--colors=full' if color else '--colors=none',
        f'--size={width}x{height}', str(path),
    ], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
       timeout=TIMEOUT, check=False)
    if result.returncode or not result.stdout.strip():
        return None
    return result.stdout.decode('utf-8').rstrip('\n') + '\n'


def published_colors(root):
    from resources import read_data
    try:
        colors = json.loads(read_data(root / 'palette.json')).get('colors', {})
        return colors if isinstance(colors, dict) else {}
    except (ValueError, AttributeError):
        return {}


def render(ui, full=False, colors=None, *, view=None):
    utf8_output(ui.stream)
    columns, rows = dimensions(ui.stream)
    terminal = ui.stream.isatty() and os.environ.get('TERM', 'dumb') != 'dumb'
    requested = os.environ.get('ANODIZE_LOGO_LAYOUT', 'auto')
    unicode_text = terminal and ui.icons and unicode_output(ui.stream)
    # Preserve the existing graphics layout/size policy independently of text.
    layout, width, height = layout_for(columns, rows, full and terminal, requested)
    mode = os.environ.get('ANODIZE_LOGO', 'text')
    # Undecorated and redirected output always uses the portable text path.
    if unicode_text and ui.color and width >= 16 and height >= 3 and mode in ('auto', 'kitty', 'chafa'):
        try:
            path = asset(layout, True)
            if mode in ('auto', 'kitty') and ui.icons and kitty_supported():
                output = kitty_image(path, min(width, 64), height)
            elif mode in ('auto', 'chafa') and path.is_file():
                output = chafa_image(path, min(width, 64), height, ui.color)
            else:
                output = None
            if output:
                ui.stream.write((view.base if view else '') + output + (view.reset if view else ''))
                return
        except (OSError, ValueError, struct.error, subprocess.SubprocessError):
            pass
    lines = text_banner(view.available if view else width, rows, requested=requested, full=full)
    if view is not None:
        view.artwork(lines)
        return
    if ui.color:
        from text_gradient import endpoints, gradient
        if colors is None:
            colors = published_colors(ui.resources.root)
        if endpoints(colors):
            for line in gradient(lines, colors, regions=lines.regions, restore='\x1b[0m'):
                ui.emit(line)
            return
    for line in lines:
        ui.emit(ui.paint(line, '95'))


if __name__ == '__main__':
    # Core-owned static-help adapter, never imports or executes an extension.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files'))
    from catalog import Presentation
    try:
        render(Presentation(), full=True)
    except KeyboardInterrupt:
        sys.exit(130)
