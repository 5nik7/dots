"""Nerd Fonts picker rows, literal selections and private FZF action callbacks."""
import os
from pathlib import Path
import re
import subprocess
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from menus import Entry, Menu, styled_label
from resources import clean


def literal(glyph):
    if not isinstance(glyph, str) or len(glyph) != 1 or clean(glyph) != glyph:
        raise ValueError('expected one printable glyph')
    return glyph


def labels(rows, ui, prefs, formatting, *, descriptions=True, collections=False):
    entries = []
    for row in rows:
        detail = row['codepoint'] if descriptions else ''
        if collections:
            detail += ' ' + row['collection']
        entries.append(Entry(row['name'], row['name'], detail))
    menu = Menu('fonts:icons', 'Fonts', tuple(entries))
    accent = prefs.style('ui.accent', {'fg': 'accent'}, app='cli') if prefs else {}
    code = prefs.sgr('fonts.glyph', accent, app='cli') if prefs else '96'
    # The literal glyph is content, including when decorative icons are disabled.
    return [ui.paint(literal(row['glyph']), code, preferences=prefs, icon_styles=False) + '\t' +
            styled_label(menu, entry, ui, preferences=prefs, formatting=formatting)
            for row, entry in zip(rows, entries)]


def completion_rows():
    from config_values import value
    from files.catalog import Presentation
    from fonts.browser import icon_version
    from fonts.model import Library
    from style_config import current
    library = Library()
    rows = library.catalog['glyphs'].get(icon_version(library, None), [])
    if not rows:
        raise ValueError('glyph index is not cached; run dots fonts update --source nerd')
    rendered = labels(rows, Presentation(terminal=True), current(), value('formatting.apps.menu', {}), collections=True)
    for row, label in zip(rows, rendered):
        print(f"{ord(row['glyph']):X}\t{label}")


def action_bindings(request, *, insert_available):
    # FZF substitutes the temporary filename literally. Pass it as data even
    # when the private temp directory contains quotes, spaces or shell syntax.
    if os.name == 'nt':
        worker = '& $env:DOTS_GLYPH_PYTHON -B $env:DOTS_GLYPH_ACTION'
        arguments = "$env:DOTS_GLYPH_REQUEST @'\n{+f1}\n'@"
    else:
        worker = '"$DOTS_GLYPH_PYTHON" -B "$DOTS_GLYPH_ACTION"'
        marker = 'DOTS_SELECTED_FILE'
        while marker in str(request.parent):
            marker += '_'
        arguments = f'"$DOTS_GLYPH_REQUEST" <<\'{marker}\'\n{{+f1}}\n{marker}'
    actions = [('enter', 'copy'), ('alt-y', 'copy'), ('double-click', 'copy')]
    if insert_available:
        actions.append(('alt-i', 'insert'))
    return [f'{key}:transform({worker} {action} {arguments})' for key, action in actions]


def perform(action, request, selected_file):
    from fonts.browser import copy, insert
    from menu_tmux import TmuxContext, read_request
    data = read_request(request)
    glyphs = data['glyphs']
    # FZF writes only field 1 (a numeric snapshot ID), with its output delimiter.
    tokens = Path(selected_file).read_bytes().replace(b'\0', b'\n').splitlines()
    if not tokens:
        return
    if any(not re.fullmatch(rb'0|[1-9][0-9]*', token) or int(token) >= len(glyphs) for token in tokens):
        raise ValueError('invalid selection')
    text = ''.join(literal(glyphs[int(token)]) for token in tokens)
    if action == 'copy':
        copy(text)
        print('accept')
    elif action == 'insert':
        insert(text, TmuxContext(**data['context']))
        print('clear-multi+change-prompt(fonts·icons: )')


if __name__ == '__main__':
    action, *args = sys.argv[1:]
    try:
        if action == 'completion':
            completion_rows()
        elif action in ('copy', 'insert') and len(args) in (1, 2):
            selected_file = args[1] if len(args) == 2 else sys.stdin.read().removesuffix('\n')
            perform(action, args[0], selected_file)
        else:
            sys.exit(2)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        if action == 'completion':
            print('nf: ' + clean(str(error)), file=sys.stderr)
            sys.exit(1)
        # Only fixed FZF actions reach transform, including on provider failures.
        print('change-prompt(Copy failed · retry or Alt-P: )' if action == 'copy' else
              'change-prompt(Insert failed · check origin: )')
