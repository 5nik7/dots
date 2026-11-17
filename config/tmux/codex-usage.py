#!/usr/bin/env python3
"""Optional weekly Codex quota; rendering never waits for provider acquisition."""
import math
from pathlib import Path
import shutil
import sys
import json
import subprocess

from status_styles import preferences, style, span, glyph, format_for
from widget_cache import Cache, age, command

DEFAULTS = dict(enabled=True, refresh_seconds=90, timeout_seconds=15,
                max_stale_seconds=300, green_at=50, yellow_at=25, orange_at=10)


def file_identity(path):
    try:
        info = path.stat()
        return [str(path.resolve()), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]
    except OSError:
        return [str(path), None]


def identity(tool):
    # Metadata invalidates account changes without reading or retaining secrets.
    return [str(Path.home()), file_identity(Path(tool)),
            file_identity(Path.home()/'.codex/auth.json')]


def parse(raw):
    doc = json.loads(raw)
    provider = doc['providers']['codex']
    accounts = provider.get('accounts', [])
    if not isinstance(accounts, list) or provider.get('error'):
        raise ValueError('quota unavailable')
    active = [row for row in accounts if isinstance(row, dict) and row.get('active') is True]
    if len(active) != 1 or active[0].get('error'):
        raise ValueError('active quota unavailable')
    value = active[0]['limits']['seven_day']['remaining_percent']
    if type(value) not in (int, float) or not 0 <= value <= 100 or not math.isfinite(value):
        raise ValueError('invalid quota')
    return {'remaining_percent': value}


def render(value, prefs, stale=False):
    options = dict(DEFAULTS, **prefs.get('options', {}).get('codex_usage', {}))
    state = 'unknown'
    text = '?%'
    if type(value) in (int, float) and 0 <= value <= 100 and math.isfinite(value):
        state = next((name for name, key in (('good', 'green_at'), ('medium', 'yellow_at'),
                    ('low', 'orange_at')) if value >= options[key]), 'critical')
        text = str(math.floor(value))+'%'
    base = style('codex_usage', '#[bold]', prefs)
    fallback = {'good':'green', 'medium':'yellow', 'low':'colour208',
                'critical':'red', 'unknown':'brightblack'}[state]
    base = style('codex_usage.'+state, base+'#[fg='+fallback+']', prefs)
    fmt = format_for('codex_usage', prefs)
    width = fmt.get('width', 0)
    align = fmt.get('alignment', 'right')
    text = (text.ljust(width) if align == 'left' else text.center(width) if align == 'center'
            else text.rjust(width)) + ('~' if stale and state != 'unknown' else '')
    icon = glyph('codex_usage', glyph('applications.codex', '', prefs), prefs)
    result = span('codex_usage.surround', fmt.get('before', ' '), base, prefs)
    if icon:
        result += span('codex_usage.icon', icon, base, prefs)
        result += span('codex_usage.spacer', fmt.get('spacer', ' '), base, prefs)
    result += span('codex_usage.text', text, base, prefs)
    return result+span('codex_usage.surround', fmt.get('after', ''), base, prefs)+'#[default]'


def main(argv):
    token = argv[1] if len(argv) == 2 and argv[0] == '--_worker' else None
    if argv and token is None:
        return ''
    prefs = preferences()
    options = dict(DEFAULTS, **prefs.get('options', {}).get('codex_usage', {}))
    if not options['enabled']:
        return ''
    tool = shutil.which('aistat')
    if not tool:
        return ''
    initial = identity(tool)
    cache = Cache('codex-usage', initial)

    def acquire(previous):
        try:
            value = parse(command([tool, 'usage', 'codex'], options['timeout_seconds'], 1024*1024))
        except (KeyError, TypeError, AttributeError, RecursionError, OverflowError) as error:
            raise ValueError('invalid quota response') from error
        if identity(tool) != initial:
            raise ValueError('quota identity changed')
        return value, options['refresh_seconds']

    if token:
        cache.work(token, acquire, options['refresh_seconds'], retry=options['refresh_seconds'])
        return ''
    row = cache.read()
    elapsed = age(row.get('updated'))
    value = row.get('value', {}).get('remaining_percent')
    if elapsed > options['max_stale_seconds']:
        value = None
    cache.schedule(__file__, timeout=options['timeout_seconds'],
                   due=not row.get('failed') and elapsed >= options['refresh_seconds'])
    return render(value, prefs, stale=bool(row.get('failed')))


if __name__ == '__main__':
    try:
        print(main(sys.argv[1:]))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
        print('')
