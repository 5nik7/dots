"""Read-only Todo preview sizing; the event path imports no goal or UI modules."""
import os
import sys


def preview_rows(lines, matches, *, popup, notice):
    # FZF_LINES excludes the tmux popup's two border rows. The remaining chrome
    # is prompt/separator (2), header (3 + notice) and preview borders (2).
    compact = min(4, max(1, lines - (8 if popup else 10) - notice))
    return compact if not matches else max(compact, lines - 7 - notice - matches)


def number(environment, key, maximum):
    value = environment.get(key, '')
    if not value or len(value) > 7 or not value.isascii() or not value.isdecimal():
        raise ValueError('invalid layout number')
    result = int(value)
    if result > maximum:
        raise ValueError('layout number exceeds bounds')
    return result


def action(mode, environment):
    """Emit only a fixed FZF action and bounded integers, never display text."""
    if mode not in ('update', 'toggle'):
        return ''
    try:
        lines = number(environment, 'FZF_LINES', 10000)
        matches = number(environment, 'FZF_MATCH_COUNT', 1000000)
        notice = number(environment, 'DOTS_TODO_LAYOUT_NOTICE', 2)
        popup = number(environment, 'DOTS_TODO_LAYOUT_POPUP', 1)
        current = (number(environment, 'FZF_PREVIEW_LINES', 10000)
                   if environment.get('FZF_PREVIEW_LINES') else 0)
        if not lines:
            raise ValueError('empty selector')
    except ValueError:
        # Older/malformed environments keep sizing and native toggle behavior.
        return 'toggle-preview' if mode == 'toggle' else ''
    if mode == 'toggle' and current:
        return 'change-preview-window(hidden)'
    if mode == 'update' and not current:
        return ''  # A search must never undo the user's Alt-P choice.
    target = preview_rows(lines, matches, popup=bool(popup), notice=notice)
    if mode == 'update' and current == target:
        return ''
    return f'change-preview-window(down,{target},wrap)'


def bindings(*, popup, notice):
    """Probe only at browser entry; filter mode parses but never runs bindings."""
    import subprocess
    environment = dict(os.environ, FZF_DEFAULT_OPTS='', FZF_DEFAULT_OPTS_FILE='',
                       FZF_DEFAULT_COMMAND='', BASH_ENV='', ENV='')
    try:
        probe = subprocess.run(['fzf', '--filter=',
            '--bind=result:transform(echo),resize:transform(echo),alt-p:transform(echo)'],
            input=b'', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=environment, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return [], {}
    if probe.returncode not in (0, 1):
        return [], {}
    command = ('& $env:DOTS_TODO_PYTHON -B $env:DOTS_TODO_LAYOUT'
               if os.name == 'nt' else '"$DOTS_TODO_PYTHON" -B "$DOTS_TODO_LAYOUT"')
    return [event + ':transform:' + command + ' update' for event in ('result', 'resize')] + [
        'alt-p:transform:' + command + ' toggle'], dict(
            DOTS_TODO_LAYOUT=os.path.abspath(__file__),
            DOTS_TODO_LAYOUT_POPUP=str(int(popup)), DOTS_TODO_LAYOUT_NOTICE=str(int(notice)))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        sys.stdout.write(action(sys.argv[1], os.environ))
