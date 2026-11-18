"""Shared bounded Markdown rendering; Dots retains terminal and reader ownership."""
import os
import re
import shutil
import sys

PRIORITY = ('leaf', 'mdcat', 'glow', 'rich-cli', 'mdterm', 'bat', 'builtin')
CHOICES = ('auto', *PRIORITY[:-1], 'cat', 'builtin')
EXECUTABLES = {'rich-cli': ('rich',), 'bat': ('bat', 'batcat')}
SGR = re.compile(r'(\x1b\[[0-9;:]*m)')
ESCAPE = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))')


def executable(viewer):
    return next((path for name in EXECUTABLES.get(viewer, (viewer,))
                 if (path := shutil.which(name))), None)


def availability():
    """Human Config details only; completion choices never depend on PATH."""
    return ', '.join(name for name in CHOICES if name in ('auto', 'builtin') or executable(name))


def plain(data):
    from resources import clean
    text = data.decode('utf-8', errors='replace') if isinstance(data, bytes) else data
    return '\n'.join(clean(line) for line in text.replace('\r\n', '\n').split('\n')).encode()


def rendered_bytes(data, color):
    # Only renderer-owned SGR is allowed through the read-only reader. Source
    # controls are escaped before execution; OSC, cursor and clipboard commands
    # from external output must never become terminal actions.
    text = data.decode('utf-8', errors='replace')
    return b''.join(part.encode() if color and SGR.fullmatch(part) else plain(ESCAPE.sub('', part))
                    for part in SGR.split(text))


def arguments(viewer, binary, width, color):
    if viewer == 'leaf':
        return [binary, '--inline', ('ansi' if color else 'plain') + ':' + str(max(20, width))]
    if viewer == 'mdcat':
        return [binary, '--ansi' if color else '--no-colour', '--local', '--columns', str(width), '--no-pager', '-']
    if viewer == 'glow':
        return [binary, '--width', str(width), '--pager=false', '--style', 'auto' if color else 'notty', '-']
    if viewer == 'rich-cli':
        return [binary, '--markdown', '--width', str(width), *(['--force-terminal'] if color else []), '-']
    if viewer == 'mdterm':
        return [binary, '--width', str(width), *([] if color else ['--no-color'])]
    if viewer == 'bat':
        return [binary, '--no-config', '--paging=never', '--style=plain', '--language=markdown',
                '--terminal-width=' + str(width), '--color=' + ('always' if color else 'never'), '-']
    return [binary]  # cat consumes stdin, including on native Windows.


def render(data, ui, *, viewer=None, inline_notice=False):
    from config_values import value
    from themes.file_preview import run_renderer
    selected = viewer or value('apps.cli.markdown_viewer', 'auto')
    if selected not in CHOICES:
        raise ValueError('invalid Markdown viewer')
    source = plain(data)
    if not source.strip():
        return source
    candidates = PRIORITY if selected == 'auto' else (selected, *(v for v in PRIORITY if v != selected))
    environment = dict(os.environ)
    environment.update(COLUMNS=str(max(1, ui.width)))
    if not ui.color:
        environment.update(NO_COLOR='1', FORCE_COLOR='0', CLICOLOR_FORCE='0')
    notice = b''
    for candidate in candidates:
        if candidate == 'builtin':
            return notice + source
        binary = executable(candidate)
        output = None
        if binary:
            try:
                output = run_renderer(arguments(candidate, binary, max(1, ui.width), ui.color), source, environment)
            except (OSError, ValueError, RuntimeError):
                pass
        if output is not None and output.strip():
            return notice + rendered_bytes(output, ui.color)
        if candidate == selected:
            message = 'dots: Markdown viewer ' + selected + ' unavailable or failed; using automatic fallback.'
            if inline_notice:
                notice = (message + '\n\n').encode()
            else:
                print(message, file=sys.stderr)
    return notice + source


def reader_ui(context=None, *, gutters=2):
    from files.catalog import Presentation
    from menu_pager import popup_bounds
    from menu_popup import viewport
    ui = Presentation(terminal=True)
    ui.width = max(1, (popup_bounds(context.verify())[0] if context else viewport()[0]) - gutters)
    return ui


def page(data, *, title, context=None):
    from menu_pager import page_text
    return page_text(render(data, reader_ui(context), inline_notice=True), title=title, context=context)
