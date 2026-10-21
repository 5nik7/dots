#!/usr/bin/env python3
"""Opt-in FZF-tab preview worker. Arguments are literal completion words."""
import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / 'files'), str(HERE.parent / 'themes')]
from authoring import Author, encode, regular_bytes
spec = importlib.util.spec_from_file_location('anodize_preview_cli', HERE / 'cli.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
parser, build_document = cli.parser, cli.build_document
from interactive import candidates, preview_logo
from presentation import render_preview
from progress import configure
from logo import LAYOUTS


def preview_options(words):
    """Read complete presentation options without parsing a partial command."""
    words = iter(words)
    for word in words:
        if word == '--':
            break
        if word == '--logo-layout':
            value = next(words, '')
        elif word.startswith('--logo-layout='):
            value = word.split('=', 1)[1]
        else:
            if word.startswith('--icons=') and word.split('=', 1)[1] in ('auto', 'always', 'never'):
                os.environ['DOTS_ICONS'] = word.split('=', 1)[1]
            continue
        if value in LAYOUTS:
            os.environ['ANODIZE_LOGO_LAYOUT'] = value


def request(words, selected):
    words = list(words)
    if not words:
        return None
    command = Path(words.pop(0)).name
    if command == 'dots':
        while words and words[0].startswith(('--color=', '--icons=')):
            words.pop(0)
        if not words:
            return None
        command = words.pop(0)
        if command not in ('anodize', 'theme', 'themes'): return None
    elif command not in ('anodize', 'theme'):
        return None
    while words and words[0].startswith(('--color=', '--icons=')):
        words.pop(0)
    mode = selected.removeprefix('--mode=')
    is_mode = bool(words and (words[-1].startswith('--mode=') or len(words) > 1 and words[-2] == '--mode'))
    if not is_mode:
        if words and words[-1].startswith(('--from=', '--theme=')):
            selected = selected.split('=', 1)[-1]
        return ('theme', (selected, command == 'anodize')) if selected and not selected.startswith('-') else None
    # Completion only previews complete literal sources; never fill inputs or prompt.
    if words[-1].startswith('--mode='):
        words[-1] = '--mode=normal'
    else:
        words[-1] = 'normal'
    return 'mode', (words, mode)


def main(cache, selected, *words):
    configure(False)
    preview_options(words)
    operation = request(words, selected)
    if operation is None:
        return 3
    kind, value = operation
    author = Author()
    if kind == 'theme':
        value, branded = value
        # Discovery is engine-free; do not mistake an ordinary file argument for a theme.
        if value not in author.identities():
            return 3
        raw, _ = author.theme_bridge('resolve', value)
        palette = json.loads(raw)
        colors = {**palette.get('colors', palette['palette']), **palette['roles']}
        render_preview(value, colors, palette['mode'], logo=preview_logo() if branded else ())
        return 0
    values, mode = value
    args = parser().parse_args(values)
    if args.action not in ('create', 'extract', 'edit', 'import'):
        return 3
    sources = []
    for name in ('file', 'image'):
        if getattr(args, name, None): sources.append(Path(getattr(args, name)).absolute())
    identity = getattr(args, 'from_theme', None) or (args.id if args.action == 'edit' else None)
    if identity:
        directory = author.target(identity)
        sources.extend(directory / name for name in ('anodize.json', 'colors.toml', 'palette.toml', 'theme.toml') if (directory / name).exists())
        if (directory / 'anodize.json').exists():
            recipe = json.loads(regular_bytes(directory / 'anodize.json'))
            if recipe.get('wallpaper'):
                sources.append(directory / recipe['wallpaper'])
    stamps = [(str(path), path.stat().st_size, path.stat().st_mtime_ns, path.stat().st_ino) for path in sources]
    key = hashlib.sha256(encode([values, stamps])).hexdigest()
    path = Path(cache) / (key + '.json')
    if path.exists():
        rows = json.loads(regular_bytes(path, 16 << 20))
    else:
        if args.action == 'extract':
            from authoring import new_document
            options = dict(mode='normal', light=args.light)
            doc = new_document('preview', author.generate(args.file, options=options), **options)
            wallpaper = args.file
        else:
            if args.action == 'create' and not any((args.image, args.color, args.from_theme)):
                raise ValueError('Supply --image, --color or --from before previewing modes')
            if args.action == 'create' and not args.id: args.id = 'preview'
            if args.action == 'import' and not args.name: args.name = 'preview'
            doc, _, wallpaper = build_document(author, args)
        if args.action == 'extract' or args.action == 'create' and (args.image or args.color):
            rows = candidates(author, doc, wallpaper)
        else:
            # A palette's unchanged mode keeps its baseline. Each other mode
            # must derive from the original recipe, not a normal-mode variant.
            # Reuse the command builder so imports, edits and --from agree with
            # the command that completion will eventually insert.
            rows = []
            for candidate in author.call('modes')['modes']:
                candidate_args = copy.copy(args)
                candidate_args.mode = candidate
                draft, _, _ = build_document(author, candidate_args)
                rows.append(dict(document=draft, id=candidate,
                                 mode='light' if draft['options']['light'] else 'dark',
                                 colors=author.render(draft)['colors']))
        staged = path.with_suffix('.' + str(os.getpid()) + '.tmp')
        staged.write_bytes(encode(rows))
        staged.chmod(0o600)
        staged.replace(path)
    row = next((r for r in rows if r['id'] == mode), None)
    if row is None:
        return 3
    render_preview(mode, row['colors'], row['mode'], logo=preview_logo())
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(*sys.argv[1:]))
    except (ValueError, OSError, TypeError, KeyError) as error:
        from catalog import Presentation
        Presentation().detail('Preview unavailable', str(error))
        sys.exit(0)
