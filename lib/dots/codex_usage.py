"""Print the Codex weekly quota widget on a terminal."""
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'config/tmux'))
from codex_quota import (COLORS, identity, layout, observation, options_for, provider,
                         refresh_due, schedule)
from status_styles import plain_text, preferences, style_fields
from widget_cache import Cache


def reading(options):
    """Join the shared worker within the caller’s deadline."""
    tool = provider(explicit=True)
    if not tool:
        return None, False, 'aistat is unavailable'
    initial = identity(tool)
    cache = Cache('codex-usage', initial)
    deadline = time.monotonic() + options['timeout_seconds']
    while True:
        row = cache.read()
        if identity(tool) != initial:
            return None, False, 'the quota account or provider changed'
        value, stale = observation(row, options)
        if not refresh_due(row, options):
            return value, stale, '' if value is not None else 'weekly quota is unavailable'
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return value, True, 'quota refresh timed out'
        if row.get('lease', 0) <= time.time() and not schedule(cache, options, explicit=True):
            return value, True, 'quota cache is unavailable'
        time.sleep(min(.05, remaining))


def color_code(value, background):
    from style_config import ANSI
    side = '48' if background else '38'
    if value == 'colour208':
        return side + ';5;208'
    if value is None:
        return ''
    if value.startswith('#'):
        return side + ';2;' + ';'.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))
    if value in ('foreground', 'background', 'default'):
        return '49' if background else '39'
    if value.startswith('bright'):
        value = 'bright_' + value[6:].lstrip('_')
    code = 97 if value == 'bright_white' else ANSI[value]
    return str(code + (10 if background else 0))


def render(value, prefs, stale):
    from plugin_presentation import color_mode
    mode = color_mode()
    colored = mode == 'always' or (mode == 'auto' and sys.stdout.isatty() and
              os.environ.get('TERM', 'dumb') != 'dumb' and not os.environ.get('NO_COLOR'))
    state, parts = layout(value, prefs, stale, icons=os.environ.get('DOTS_ICONS') != 'never')
    if not colored:
        return ''.join(plain_text(text) for _, text in parts)
    from style_config import ATTRS
    base = {'bold': True, **style_fields('codex_usage', prefs), 'fg': COLORS[state],
            **style_fields('codex_usage.' + state, prefs)}
    spans = []
    for role, text in parts:
        if not text:
            continue
        fields = {**base, **style_fields('codex_usage.' + role, prefs)}
        codes = [str(code) for attr, code in ATTRS.items() if fields.get(attr) is True]
        codes += [color_code(fields.get('fg'), False), color_code(fields.get('bg'), True)]
        spans.append('\033[' + ';'.join(['0', *filter(None, codes)]) + 'm' + plain_text(text))
    return ''.join(spans) + '\033[0m'


def main(argv):
    if argv:
        print('Usage: codex-usage [--help]', file=sys.stderr)
        return 2
    prefs = preferences()
    try:
        value, stale, reason = reading(options_for(prefs))
    except (AttributeError, KeyError, TypeError, ValueError):
        value, stale, reason = None, False, 'invalid widget settings or cache'
    except OSError:
        value, stale, reason = None, False, 'quota cache is unavailable'
    try:
        widget = render(value, prefs, stale)
    except (AttributeError, KeyError, TypeError, ValueError):
        widget = render(value, {}, stale)
    print(widget)
    if value is None:
        print('codex-usage: ' + reason, file=sys.stderr)
        return 1
    return 0
