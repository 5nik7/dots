"""Bounded Anodize branding. No engine, terminal queries, or persistent state."""
import argparse
import base64
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ASSETS = Path(__file__).with_name('assets')
MODES = ('text', 'auto', 'kitty', 'chafa')
LAYOUTS = ('auto', 'horizontal', 'stacked', 'icon')
TIMEOUT = 1.0


class LogoOption(argparse.Action):
    """Apply while parsing so options preceding --help affect its header too."""
    def __call__(self, parser, namespace, values, option_string=None):
        os.environ['ANODIZE_' + self.dest.upper()] = values
        setattr(namespace, self.dest, values)


def add_options(parser):
    parser.add_argument('--logo', choices=MODES, action=LogoOption,
                        help='Logo renderer (default: text; ANODIZE_LOGO)')
    parser.add_argument('--logo-layout', choices=LAYOUTS, action=LogoOption,
                        help='Logo layout, bounded to fit (ANODIZE_LOGO_LAYOUT)')


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


def text_lines(layout, width, height):
    if layout == 'compact':
        if width >= 16 and height >= 3:
            return ['  /\\', ' /_ \\   ANODIZE', '/_/\\_\\']
        return [(' /\\ ANODIZE' if width >= 11 else '/\\' if width >= 2 else 'A')]
    try:
        lines = (ASSETS / (layout + '.txt')).read_text(encoding='ascii').splitlines()
        if lines and len(lines) <= height and max(map(len, lines)) <= width:
            return lines
    except (OSError, UnicodeError):
        pass
    return text_lines('compact', width, height)


def kitty_supported():
    # Be conservative. TERM propagated through an unknown multiplexer is not
    # evidence of passthrough support. No queries may consume the user's input.
    return (not any(os.environ.get(k) for k in ('TMUX', 'STY', 'ZELLIJ'))
            and (os.environ.get('TERM') == 'xterm-kitty'
                 or (os.environ.get('KITTY_WINDOW_ID') and os.environ.get('TERM', '').startswith('xterm'))))


def asset(layout, color):
    layout = 'icon' if layout == 'compact' else layout
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


def chafa_image(path, width, height, color, icons):
    executable = shutil.which('chafa')
    if not executable:
        return None
    result = subprocess.run([
        executable, '--probe=off', '--polite=on', '--format=symbols', '--animate=off',
        '--relative=off', '--optimize=0', '--fg-only', '--threads=1',
        '--symbols=block' if icons else '--symbols=ascii',
        '--colors=full' if color else '--colors=none',
        f'--size={width}x{height}', str(path),
    ], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
       timeout=TIMEOUT, check=False)
    if result.returncode or not result.stdout.strip():
        return None
    return result.stdout.decode('utf-8').rstrip('\n') + '\n'


def render(ui, full=False):
    columns, rows = dimensions(ui.stream)
    terminal = ui.stream.isatty() and os.environ.get('TERM', 'dumb') != 'dumb'
    requested = os.environ.get('ANODIZE_LOGO_LAYOUT', 'auto')
    layout, width, height = layout_for(columns, rows, full and terminal, requested)
    mode = os.environ.get('ANODIZE_LOGO', 'text')
    # Undecorated and redirected output always uses the portable text path.
    if terminal and ui.color and width >= 16 and height >= 3 and mode in ('auto', 'kitty', 'chafa'):
        try:
            path = asset(layout, True)
            if mode in ('auto', 'kitty') and ui.icons and kitty_supported():
                output = kitty_image(path, min(width, 64), height)
            elif mode in ('auto', 'chafa') and path.is_file():
                output = chafa_image(path, min(width, 64), height, ui.color, ui.icons)
            else:
                output = None
            if output:
                ui.stream.write(output)
                return
        except (OSError, ValueError, struct.error, subprocess.SubprocessError):
            pass
    for line in text_lines(layout, width, height):
        ui.emit(ui.paint(line, '95'))


if __name__ == '__main__':
    # Core-owned static-help adapter, never imports or executes an extension.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files'))
    from catalog import Presentation
    try:
        render(Presentation(), full=True)
    except KeyboardInterrupt:
        sys.exit(130)
