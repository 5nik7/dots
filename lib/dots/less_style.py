"""Optional less standout colors; inert palette data and process environment only."""
import json
import os
from pathlib import Path
import re

RESET = '\x1b[0m'
MARKER = '_DOTS_LESS_STYLE'
START, END = 'LESS_TERMCAP_so', 'LESS_TERMCAP_se'
HEX = re.compile(r'#[0-9a-fA-F]{6}\Z')


def apply(environment, colors, *, mode='auto', enabled=True, windows=None):
    """Refresh our inherited pair, retaining explicit (including empty) overrides."""
    owned = bool(environment.get(MARKER)) and (
        environment.get(START) == environment[MARKER] and environment.get(END) == RESET)
    if (START in environment or END in environment) and not owned:
        environment.pop(MARKER, None)
        return
    if 'LESS_TERMINFO_smso' in environment or 'LESS_TERMINFO_rmso' in environment:
        if owned:
            environment.pop(START, None)
            environment.pop(END, None)
        environment.pop(MARKER, None)
        return
    windows = os.name == 'nt' if windows is None else windows
    color = mode == 'always' or (mode == 'auto' and (environment.get('TERM') or 'dumb') != 'dumb'
                                and not environment.get('NO_COLOR'))
    if windows or not enabled or not color:
        if owned:
            environment.pop(START, None)
            environment.pop(END, None)
        environment.pop(MARKER, None)
        return
    fg = colors.get('foreground')
    bg = colors.get('lighter_background', colors.get('background'))
    if not all(isinstance(value, str) and HEX.fullmatch(value) for value in (fg, bg)):
        return
    rgb = lambda value: ';'.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))
    start = '\x1b[0;38;2;' + rgb(fg) + ';48;2;' + rgb(bg) + 'm'
    environment.update({START: start, END: RESET, MARKER: start})


def published_environment(environment):
    """Selected popup boundary: read the current snapshot even in an old tmux server."""
    from resources import read_data
    from shell.runtime import settings
    result = dict(environment)
    try:
        options, _, _ = settings(Path(__file__).resolve().parents[2],
                                 dict(result, HOME=result.get('HOME') or str(Path.home())))
        state = result.get('XDG_STATE_HOME') or (result.get('LOCALAPPDATA') if os.name == 'nt' else None)
        root = Path(state or Path(result.get('HOME') or str(Path.home())) / '.local/state')
        document = json.loads(read_data(root / 'dots/current/theme/palette.json') or '{}')
        colors = document.get('colors', {})
        if not isinstance(colors, dict):
            colors = {}
    except (OSError, ValueError, AttributeError, KeyError):
        return result
    apply(result, colors, mode=options['DOTS_COLOR'], enabled=options['DOTS_INIT_THEME'] == '1')
    return result
