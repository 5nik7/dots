#!/usr/bin/env python3
"""Render the nonblocking tmux quota widget or run a reserved refresh."""
import subprocess
import sys

from codex_quota import COLORS, identity, layout, observation, options_for, provider, schedule, work
from status_styles import preferences, span, style
from widget_cache import Cache


def render(value, prefs, stale=False):
    state, parts = layout(value, prefs, stale)
    base = style('codex_usage', '#[bold]', prefs)
    base = style('codex_usage.' + state, base + '#[fg=' + COLORS[state] + ']', prefs)
    return ''.join(span('codex_usage.' + role, text, base, prefs) for role, text in parts) + '#[default]'


def main(argv):
    worker = len(argv) in (2, 3) and argv[0] == '--_worker' and argv[2:] in ([], ['--explicit'])
    if argv and not worker:
        return ''
    explicit = worker and argv[2:] == ['--explicit']
    prefs = preferences()
    options = options_for(prefs)
    if not explicit and not options['enabled']:
        return ''
    tool = provider(explicit)
    if not tool:
        return ''
    if worker:
        work(argv[1], tool, options)
        return ''
    cache = Cache('codex-usage', identity(tool))
    value, stale = observation(cache.read(), options)
    schedule(cache, options)
    return render(value, prefs, stale)


if __name__ == '__main__':
    try:
        print(main(sys.argv[1:]))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
        print('')
