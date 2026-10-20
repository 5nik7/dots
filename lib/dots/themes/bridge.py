#!/usr/bin/env python3
"""Private native structured bridge for Anodize; diagnostics use stderr."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile

from palette_native import Themes
from theme_cli import publication, connectors, backgrounds, validate_pointers


def main():
    action, identity, *args = sys.argv[1:]
    themes = Themes()
    palette = themes.load(identity)
    if action == 'resolve': print(json.dumps(palette))
    elif action == 'render': themes.render(identity, Path(args[0]))
    elif action == 'plan':
        validate_pointers(themes)
        if args and args[0] == 'background':
            backgrounds(themes, 'set', [args[1]], preflight=True, identity=identity) if len(args) > 1 and args[1] else backgrounds(themes, 'select', [], preflight=True, identity=identity)
        with tempfile.TemporaryDirectory(prefix='dots-anodize-preview-') as directory:
            themes.render(identity, Path(directory))
        print(json.dumps(dict(schema=1, status='preview', theme=identity,
                             publish=str(themes.state / 'current/theme'),
                             connectors=[str(p) for p, _ in connectors(themes)])))
    elif action == 'apply':
        with contextlib.redirect_stdout(sys.stderr):
            wallpaper = None
            if args and args[0] == 'background':
                wallpaper = backgrounds(themes, 'set', [args[1]], preflight=True, identity=identity) if len(args) > 1 and args[1] else backgrounds(themes, 'select', [], preflight=True, identity=identity)
            generation = publication(themes, identity)
            if wallpaper: backgrounds(themes, 'set', [wallpaper], identity=identity)
        print(json.dumps(dict(schema=1, status='complete', generation=generation)))
    else: raise ValueError('unknown theme bridge action')


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError) as error:
        print('dots theme: ' + str(error), file=sys.stderr); sys.exit(1)
