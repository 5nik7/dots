#!/usr/bin/env python3
"""Token-only native theme picker previews; no shell-evaluated filenames."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

from palette_native import LIB, Themes, regular
from catalog import Presentation
from interaction import RichSelector
from picker import fzf_colors


def choose(themes, identities=None, files=None):
    ui = Presentation()
    rows = []
    for identity in identities or []:
        try: rows.append(dict(id=identity, palette=themes.load(identity)))
        except (ValueError, OSError) as error: rows.append(dict(id=identity, error=str(error)))
    if files is not None: rows = [dict(path=str(p), name=p.name) for p in files]
    labels = [ui.paint(r['id'], '94') if 'id' in r else ui.resource(r['path']) for r in rows]
    with tempfile.TemporaryDirectory(prefix='dots-theme-picker-') as directory:
        snapshot = Path(directory) / 'items.json'
        snapshot.write_text(json.dumps(dict(rows=rows, color=ui.color, icons=ui.icons)), encoding='utf-8')
        snapshot.chmod(0o600)
        if os.name == 'nt':
            prefix = '& $env:DOTS_PICKER_PYTHON -B $env:DOTS_PICKER_HELPER'
            argument = '$env:DOTS_PICKER_SNAPSHOT'
        else:
            prefix = '"$DOTS_PICKER_PYTHON" -B "$DOTS_PICKER_HELPER"'
            argument = '"$DOTS_PICKER_SNAPSHOT"'
        preview = (prefix + ' preview ' + argument + ' {1}', prefix + ' cycle ' + argument,
                   dict(DOTS_PICKER_PYTHON=sys.executable, DOTS_PICKER_HELPER=str(Path(__file__).resolve()),
                        DOTS_PICKER_SNAPSHOT=str(snapshot), DOTS_PROGRESS='never'))
        return RichSelector().pick('Theme' if identities is not None else 'Background', labels,
                                   preview=preview, color=ui.color, icons=ui.icons, colors=fzf_colors(ui))[0]


def main(args):
    action, snapshot, *tokens = args
    path = Path(snapshot)
    doc = json.loads(regular(path))
    mode_path = path.with_suffix('.mode')
    mode = int(regular(mode_path)) if mode_path.exists() else 0
    if action == 'cycle':
        mode_path.write_text(str((mode + 1) % 2)); return
    if action != 'preview' or len(tokens) != 1 or not tokens[0].isdecimal(): raise ValueError('invalid preview token')
    row = doc['rows'][int(tokens[0])]
    os.environ['DOTS_COLOR'] = 'always' if doc['color'] else 'never'
    os.environ['DOTS_ICONS'] = 'always' if doc['icons'] else 'never'
    ui = Presentation()
    if 'error' in row:
        ui.detail('Unavailable', row['error'])
    elif 'palette' in row:
        palette = row['palette']
        from presentation import render_preview
        render_preview(row['id'], palette['colors'], palette['mode'], palette=mode == 0)
    else:
        image = Path(row['path'])
        ui.resource_detail('Background', image)
        if image.is_file() and not image.is_symlink():
            ui.detail('Size', str(image.stat().st_size) + ' bytes')
            if mode == 0 and shutil.which('chafa'):
                subprocess.run(['chafa', '--format=symbols', '--size=60x20', '--', str(image)], timeout=5)
    ui.emit('  Alt-C: switch preview view. Enter reviews the selection.')


if __name__ == '__main__':
    try: main(sys.argv[1:])
    except (ValueError, OSError, IndexError, subprocess.TimeoutExpired) as error:
        print('Preview unavailable: ' + str(error)); sys.exit(1)
