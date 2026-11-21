"""Weekly quota data and literal spans shared by the status line and shell."""
import json
import math
import os
from pathlib import Path
import shutil
import time

from status_styles import format_for, glyph
from widget_cache import Cache, age, command

DEFAULTS = dict(enabled=True, refresh_seconds=90, timeout_seconds=15,
                max_stale_seconds=300, green_at=50, yellow_at=25, orange_at=10)
COLORS = dict(good='green', medium='yellow', low='colour208', critical='red', unknown='brightblack')
WORKER = Path(__file__).with_name('codex-usage.py')


def options_for(prefs):
    options = {**DEFAULTS, **prefs.get('options', {}).get('codex_usage', {})}
    if type(options['timeout_seconds']) is not int or not 1 <= options['timeout_seconds'] <= 60:
        raise ValueError('invalid worker timeout')
    return options


def provider(explicit=False):
    name = 'aistat.exe' if os.name == 'nt' else 'aistat'
    tool = shutil.which(name)
    if tool or not explicit:
        return tool
    # Go installs commands in GOBIN or the first GOPATH's bin directory.
    gopath = (os.environ.get('GOPATH') or str(Path.home() / 'go')).split(os.pathsep)[0]
    directory = Path(os.environ.get('GOBIN') or Path(gopath) / 'bin')
    if directory.is_absolute():
        return shutil.which(str(directory / name))
    return None


def file_identity(path):
    try:
        info = path.stat()
        return [str(path.resolve()), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]
    except OSError:
        return [str(path), None]


def identity(tool):
    return [str(Path.home()), file_identity(Path(tool)), file_identity(Path.home()/'.codex/auth.json')]


def valid_percent(value):
    return type(value) in (int, float) and 0 <= value <= 100 and math.isfinite(value)


def parse(raw):
    provider = json.loads(raw)['providers']['codex']
    accounts = provider.get('accounts', [])
    if not isinstance(accounts, list) or provider.get('error'):
        raise ValueError('quota unavailable')
    active = [row for row in accounts if isinstance(row, dict) and row.get('active') is True]
    if len(active) != 1 or active[0].get('error'):
        raise ValueError('active quota unavailable')
    value = active[0]['limits']['seven_day']['remaining_percent']
    if not valid_percent(value):
        raise ValueError('invalid quota')
    return {'remaining_percent': value}


def layout(value, prefs, stale=False, icons=True):
    options = options_for(prefs)
    state, text = 'unknown', '?%'
    if valid_percent(value):
        state = next((name for name, key in (('good', 'green_at'), ('medium', 'yellow_at'),
                     ('low', 'orange_at')) if value >= options[key]), 'critical')
        text = str(math.floor(value)) + '%'
    fmt = format_for('codex_usage', prefs)
    width = fmt.get('width', 0)
    if type(width) is not int or not 0 <= width <= 20:
        raise ValueError('invalid quota width')
    align = fmt.get('alignment', 'right')
    text = (text.ljust(width) if align == 'left' else text.center(width) if align == 'center'
            else text.rjust(width)) + ('~' if stale and state != 'unknown' else '')
    icon = glyph('codex_usage', glyph('applications.codex', '', prefs), prefs)
    parts = [('surround', fmt.get('before', ' '))]
    if icons and icon:
        parts.extend([('icon', icon), ('spacer', fmt.get('spacer', ' '))])
    parts.extend([('text', text), ('surround', fmt.get('after', ''))])
    return state, parts


def observation(row, options):
    value = row.get('value', {}).get('remaining_percent')
    if not valid_percent(value) or age(row.get('updated')) > options['max_stale_seconds']:
        value = None
    return value, bool(row.get('failed'))


def refresh_due(row, options):
    if row.get('failed'):
        return time.time() >= row.get('next_at', 0)
    return age(row.get('updated')) >= options['refresh_seconds'] or not valid_percent(
        row.get('value', {}).get('remaining_percent'))


def schedule(cache, options, explicit=False):
    return cache.schedule(WORKER, ['--explicit'] if explicit else [],
                          timeout=options['timeout_seconds'], due=lambda row: refresh_due(row, options))


def work(token, tool, options):
    initial = identity(tool)

    def acquire(_previous):
        try:
            value = parse(command([tool, 'usage', 'codex'], options['timeout_seconds'], 1024*1024))
        except (KeyError, TypeError, AttributeError, RecursionError, OverflowError) as error:
            raise ValueError('invalid quota response') from error
        if identity(tool) != initial:
            raise ValueError('quota identity changed')
        return value, options['refresh_seconds']
    Cache('codex-usage', initial).work(token, acquire, options['refresh_seconds'],
                                       retry=options['refresh_seconds'])
