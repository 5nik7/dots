"""Transient Anodize drafts and token-only FZF previews; no publication here."""
import base64
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / 'files'), str(HERE.parent / 'themes')]
from authoring import regular_bytes, encode
from catalog import Presentation
from interaction import RichSelector, SelectionEnded, terminal
from picker import fzf_colors
from presentation import ColorView, render_preview
from transactions import parents_safe
from progress import Progress

ACTIONS = ['show', 'preview', 'create', 'extract', 'edit', 'apply', 'import', 'export', 'promote']
ADJUSTMENTS = ['vibrance', 'saturation', 'contrast', 'brightness', 'shadows', 'highlights',
               'temperature', 'tint', 'blackPoint', 'whitePoint', 'hueShift', 'gamma']


def choose(title, choices, rows=None):
    if not choices:
        raise ValueError('No available choices for ' + title)
    ui = Presentation()
    labels = [ui.clean(value) for value in choices]
    with tempfile.TemporaryDirectory(prefix='anodize-picker-') as directory:
        preview = None
        if rows is not None:
            snapshot = Path(directory) / 'items.json'
            snapshot.write_bytes(encode(dict(rows=rows, color=ui.color)))
            snapshot.chmod(0o600)
            command = '"$DOTS_ANODIZE_PYTHON" -B "$DOTS_ANODIZE_PREVIEW" "$DOTS_ANODIZE_SNAPSHOT" {1}'
            if os.name == 'nt':
                command = '& $env:DOTS_ANODIZE_PYTHON -B $env:DOTS_ANODIZE_PREVIEW $env:DOTS_ANODIZE_SNAPSHOT {1}'
            preview = (command, None, dict(DOTS_ANODIZE_PYTHON=sys.executable,
                        DOTS_ANODIZE_PREVIEW=str(Path(__file__)), DOTS_ANODIZE_SNAPSHOT=str(snapshot),
                        DOTS_ICONS='always' if ui.icons else 'never',
                        DOTS_PROGRESS='never'))
        index = RichSelector().pick(title, labels, preview=preview, color=ui.color,
                                    icons=ui.icons, colors=fzf_colors(ui))[0]
    return index


def choice(title, choices):
    return choices[choose(title, choices)]


def entry(title, default=''):
    value = input(title + (f' [{default}]' if default else '') + ': ').strip()
    if value == '\x1b':
        raise SelectionEnded(130)
    value = value or default
    if not value:
        raise ValueError(title + ' is required')
    return value


def action_menu():
    if not terminal():
        raise ValueError('--interactive requires terminal input and output')
    return choice('Anodize', ACTIONS)


def browse(image=False):
    directory = Path.cwd()
    while True:
        parents_safe(directory / 'placeholder')
        entries = sorted((p for p in directory.iterdir() if not p.is_symlink()
                          and (p.is_dir() or p.is_file() and (not image or p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif')))),
                         key=lambda p: (not p.is_dir(), p.name.lower()))
        labels = ['Enter a path', '../'] + [p.name + ('/' if p.is_dir() else '') for p in entries]
        selected = choose(str(directory), labels)
        if selected == 0:
            path = Path(entry('Image path' if image else 'File path')).expanduser().absolute()
        elif selected == 1:
            directory = directory.parent
            continue
        else:
            path = entries[selected - 2]
        parents_safe(path)
        if path.is_symlink():
            raise ValueError('picker source must not be a symlink')
        if path.is_dir():
            directory = path
            continue
        regular_bytes(path, 32 << 20 if image else 1 << 20)
        return str(path)


def theme(author, action):
    identities = author.authored(user_only=True) if action == 'promote' else author.authored() if action == 'edit' else author.identities()
    rows = []
    for identity in identities:
        try:
            doc = author.load(identity, owned=action in ('edit', 'promote'))
            rows.append(dict(id=identity, mode=doc['options']['mode'], colors=author.render(doc)['colors']))
        except (ValueError, OSError) as error:
            rows.append(dict(id=identity, error=str(error)))
    selected = choose('Theme', identities, rows)
    if rows[selected].get('error'):
        raise ValueError(rows[selected]['error'])
    return identities[selected]


def fill_inputs(parser, args, author):
    guided = args.interactive
    if guided and (getattr(args, 'json', False) or getattr(args, 'yes', False) or not terminal()):
        parser.error('--interactive requires terminal streams and cannot combine with --json or --yes')
    can_pick = guided or terminal() and not any(getattr(args, key, False) for key in ('json', 'yes', 'dry_run'))
    def missing(value, title, get):
        if value:
            return value
        if not can_pick:
            parser.error(title + ' is required; supply it explicitly or use --interactive in a terminal')
        return get()
    action = args.action
    if hasattr(args, 'id'):
        args.id = missing(args.id, 'Theme ID', lambda: entry('New theme ID') if action == 'create' else theme(author, action))
    if action in ('extract', 'import'):
        args.file = missing(args.file, 'Source file', lambda: browse(action == 'extract'))
    if action == 'create' and not any((args.image, args.color, args.from_theme)):
        if not can_pick:
            parser.error('create requires exactly one of --image, --color or --from')
        source = choice('Source', ['Image', 'Seed color', 'Existing theme'])
        if source == 'Image': args.image = browse(True)
        elif source == 'Seed color': args.color = entry('Seed #RRGGBB')
        else: args.from_theme = theme(author, 'show')
    if action == 'import':
        args.name = missing(args.name, '--name', lambda: entry('New theme ID'))
        args.format = missing(args.format, '--format', lambda: choice('Input format', ['anodize', 'aether', 'base16', 'colors']))
    if action == 'promote':
        if guided and not args.copy:
            args.copy = choice('Promotion', ['Move', 'Copy with a new ID']) != 'Move'
        if args.copy:
            args.name = missing(args.name, '--name for copy', lambda: entry('New built-in theme ID'))
    if guided and action in ('create', 'import') and not args.builtin:
        args.builtin = choice('Save location', ['User themes', 'Built-in themes']) == 'Built-in themes'
    if guided and action in ('create', 'extract', 'import') and not (args.light or args.dark):
        args.light = choice('Lightness', ['Dark', 'Light']) == 'Light'
        args.dark = not args.light
    if guided and action == 'export':
        if '--format' not in getattr(args, '_provided', set()):
            args.format = choice('Output format', ['anodize', 'aether', 'colors'])
        if not args.output:
            args.output = entry('New export file')
    if guided and action == 'preview' and not args.app:
        selected = choice('Preview', ['Theme', 'kitty', 'tmux', 'btop', 'termux', 'bat', 'yazi'])
        if selected != 'Theme': args.app = selected
    if guided and action == 'apply' and not args.background:
        args.background = choice('Apply', ['Theme only', 'Theme and wallpaper']) != 'Theme only'


def candidates(author, doc, wallpaper=None, modes=None):
    """Read an image once, then derive complete drafts with identical edit settings."""
    image = wallpaper or doc.get('wallpaper')
    if image and not Path(image).is_absolute():
        image = str(author.target(doc['id']) / image)
    payload = base64.b64encode(regular_bytes(image, 32 << 20)).decode() if image else None
    result = []
    modes = modes or author.call('modes')['modes']
    with Progress('Generating mode previews'):
        for mode in modes:
            draft = copy.deepcopy(doc)
            draft['options']['mode'] = mode
            if payload or draft.get('seed'):
                kwargs = dict(options=draft['options'])
                kwargs.update(image=payload) if payload else kwargs.update(color=draft['seed'])
                draft['baseline'] = author.call('generate', **kwargs)['colors']
            else:
                draft['baseline'] = author.call('variant', document={k: v for k, v in draft.items() if k != 'generated'})['colors']
            result.append(dict(document=draft, id=mode, mode='light' if draft['options']['light'] else 'dark',
                               colors=author.render(draft)['colors']))
    return result


def select_mode(author, doc, wallpaper=None):
    rows = candidates(author, doc, wallpaper)
    index = choose('Extraction mode', [r['id'] for r in rows], rows)
    return rows[index]['document']


def edit_draft(author, args, doc, wallpaper=None):
    if not args.mode:
        doc = select_mode(author, doc, wallpaper)
    while True:
        from logo import render as render_logo
        render_logo(Presentation())
        render_preview(doc['id'], author.render(doc)['colors'], 'light' if doc['options']['light'] else 'dark')
        selected = choice('Draft', ['Review save', 'Mode', 'Light/dark', 'Adjustment', 'Color override',
                                    'Reset adjustments', 'Re-extract', 'Cancel'])
        if selected == 'Cancel': raise SelectionEnded(130)
        if selected == 'Review save': return doc
        changed = copy.deepcopy(doc)
        if selected == 'Mode': changed = select_mode(author, changed, wallpaper)
        elif selected == 'Light/dark':
            changed['options']['light'] = choice('Lightness', ['Dark', 'Light']) == 'Light'
            changed = candidates(author, changed, wallpaper, [changed['options']['mode']])[0]['document']
        elif selected == 'Adjustment':
            key = choice('Adjustment', ADJUSTMENTS)
            changed['adjustments'][key] = float(entry('Value', str(changed['adjustments'].get(key, 1 if key == 'gamma' else 0))))
        elif selected == 'Color override':
            colors = author.render(changed)['colors']
            key = choice('Color', sorted(k for k in colors if not (k.startswith('color') and k[5:].isdigit())))
            changed['overrides'][key] = entry('#RRGGBB', colors[key])
        elif selected == 'Reset adjustments': changed['adjustments'] = {}
        elif selected == 'Re-extract':
            if not (wallpaper or changed.get('wallpaper') or changed.get('seed')):
                raise ValueError('re-extraction requires a saved wallpaper or seed')
            changed = candidates(author, changed, wallpaper, [changed['options']['mode']])[0]['document']
        author.render(changed)  # Validate before accepting the draft.
        doc = changed


def preview_logo():
    from logo import dimensions, text_banner, unicode_output
    view = ColorView(preview=True)
    rows = view.pane_height or dimensions(sys.stdout)[1]
    unicode_text = (os.environ.get('TERM', 'dumb') != 'dumb'
                    and os.environ.get('DOTS_ICONS', 'auto') != 'never'
                    and unicode_output(sys.stdout))
    return text_banner(view.available, rows, unicode_text=unicode_text, scrollable=True)


def preview(snapshot, token):
    if not token.isdecimal():
        raise ValueError('invalid preview token')
    doc = json.loads(regular_bytes(snapshot, 16 << 20))
    row = doc['rows'][int(token)]
    os.environ['DOTS_COLOR'] = 'always' if doc['color'] else 'never'
    if row.get('error'):
        Presentation().detail('Unavailable', row['error'])
    else:
        render_preview(row['id'], row['colors'], row.get('mode', ''), logo=preview_logo())


if __name__ == '__main__':
    try:
        preview(*sys.argv[1:])
    except (ValueError, OSError, IndexError, TypeError, KeyError) as error:
        print('Preview unavailable: ' + str(error))
        sys.exit(1)
