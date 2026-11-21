"""Transient Anodize drafts and token-only FZF previews; no publication here."""
import base64
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SHARED = HERE.parents[1] / 'lib/dots'
sys.path[:0] = [str(HERE), str(SHARED), str(SHARED / 'files'), str(SHARED / 'themes')]
from authoring import regular_bytes, encode
from catalog import Presentation
from interaction import RichSelector, SelectionEnded, SelectionEvent, terminal
from picker import fzf_colors
from presentation import ColorView, escape, render_preview
from transactions import parents_safe
from progress import Progress, sequence, permanent_output

ACTIONS = ['show', 'preview', 'create', 'extract', 'patina', 'edit', 'apply', 'import', 'export', 'promote']
ADJUSTMENTS = ['vibrance', 'saturation', 'contrast', 'brightness', 'shadows', 'highlights',
               'temperature', 'tint', 'blackPoint', 'whitePoint', 'hueShift', 'gamma']


def choose(title, choices, rows=None, *, state=None, comparison=None, swatches=False):
    if not choices:
        raise ValueError('No available choices for ' + title)
    ui = Presentation()
    labels = [ui.clean(value) for value in choices]
    selector = RichSelector()
    if callable(rows):
        rows = rows() if selector.backend == 'fzf' else None
    if swatches and ui.color:
        for index, row in enumerate(rows):
            strip = ''.join(escape(row['colors'][name], True) + '  ' for name in
                            ('background', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'foreground'))
            labels[index] += '  ' + strip + '\033[0m'
    with tempfile.TemporaryDirectory(prefix='anodize-picker-') as directory:
        preview = None
        if rows is not None:
            snapshot = Path(directory) / 'items.json'
            snapshot.write_bytes(encode(dict(rows=rows, color=ui.color, comparison=comparison)))
            snapshot.chmod(0o600)
            command = '"$DOTS_ANODIZE_PYTHON" -B "$DOTS_ANODIZE_PREVIEW" "$DOTS_ANODIZE_SNAPSHOT" {1}'
            if os.name == 'nt':
                command = '& $env:DOTS_ANODIZE_PYTHON -B $env:DOTS_ANODIZE_PREVIEW $env:DOTS_ANODIZE_SNAPSHOT {1}'
            preview = (command, None, dict(DOTS_ANODIZE_PYTHON=sys.executable,
                        DOTS_ANODIZE_PREVIEW=str(Path(__file__)), DOTS_ANODIZE_SNAPSHOT=str(snapshot),
                        DOTS_ICONS='always' if ui.icons else 'never',
                        DOTS_PROGRESS='never'))
        if state is not None and selector.backend == 'fzf':
            with permanent_output():
                try:
                    index = selector.fzf(title, labels, False, preview, ui.color, ui.icons, fzf_colors(ui),
                                         navigation=state, navigation_keys={'esc': 'cancel'},
                                         query=state.get('query', ''), focus_index=state.get('index'))[0]
                except SelectionEvent:
                    raise SelectionEnded(130) from None
            state['index'] = index
        else:
            index = selector.pick(title, labels, preview=preview, color=ui.color,
                                  icons=ui.icons, colors=fzf_colors(ui))[0]
    return index


def choice(title, choices):
    return choices[choose(title, choices)]


@permanent_output()
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
    if args.action == 'patina' and args.all_themes and args.yes:
        args.interactive = False  # The batch has its own single approval, including from guided wrappers.
        if not args.file:
            parser.error('patina --all-themes --yes requires an input image')
        if not args.dry_run and (args.json or not terminal()):
            parser.error('saving all themes requires a terminal confirmation; use --dry-run --json to list outputs')
    elif any(getattr(args, flag, False) for flag in ('all_modes', 'all_styles', 'all_themes')):
        args.interactive = True
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
    if action == 'extract' and args.mode and args.all_modes:
        parser.error('choose --mode or --all-modes')
    if hasattr(args, 'id'):
        args.id = missing(args.id, 'Theme ID', lambda: entry('New theme ID') if action == 'create' else theme(author, action))
    if action in ('extract', 'import', 'patina'):
        args.file = missing(args.file, 'Source file', lambda: browse(action != 'import'))
    if action == 'patina':
        if args.all_styles and '--style' in args._provided:
            parser.error('choose --style or --all-styles')
        if (args.all_styles or args.all_themes) and (args.compare or args.compare_modes):
            parser.error('choose --all-themes or --all-styles for individual images, or use a comparison sheet')
        if not (args.theme or args.palette_image or args.all_themes):
            if not can_pick:
                parser.error('patina requires --theme or --palette-image')
            sources = ['Theme', 'Reference image']
            if guided and not (args.compare or args.compare_modes):
                if '--style' not in args._provided and not args.all_styles:
                    sources.append('All styles')
                sources.append('All themes')
                if '--style' not in args._provided and not args.all_styles:
                    sources.append('All themes and styles')
            source = choice('Palette source', sources)
            if source == 'All styles':
                args.all_styles = True
                source = choice('Palette source', ['Theme', 'Reference image'])
            if source.startswith('All themes'):
                args.all_themes = True
                args.all_styles |= source == 'All themes and styles'
            elif source == 'Theme':
                args.theme = theme(author, 'show')
            else:
                args.palette_image = browse(True)
        if (args.theme or args.all_themes) and not (args.mode or args.compare_modes) and (args.light or args.dark):
            parser.error('--light and --dark with a theme require --mode or --compare-modes')
        if args.compare_modes and args.mode:
            parser.error('--compare-modes includes all modes; omit --mode')
        if args.compare and ({'--style', '--stops', '--strength', '--harmony'} & args._provided):
            parser.error('--compare uses each style at its defaults')
        if guided and args.palette_image:
            if not (args.light or args.dark):
                args.light = choice('Lightness', ['Dark', 'Light']) == 'Light'
        from patina import available_styles
        if not available_styles(args):
            parser.error('incompatible Patina settings: harmony requires alloy, harmonize or natural, stops require gradient (2+) or duotone (2), and exact/shaded use fixed strength')
        if guided and args.theme and not args.all_styles and not (args.output or args.compare or args.compare_modes):
            if choice('Destination', ['Personal theme backgrounds', 'Choose an output path']) == 'Choose an output path':
                args.output = entry('New image file')
        if args.palette_image and not (args.output or args.compare or args.compare_modes):
            if not guided:
                parser.error('--output is required with --palette-image; use --interactive to choose a path')
            args.output = entry('New image file')
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
    if guided and action in ('create', 'extract', 'import') and not getattr(args, 'all_modes', False) and not (args.light or args.dark):
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
    generated, rendered = {}, {}
    if payload or doc.get('seed'):
        source = dict(image=payload) if payload else dict(color=doc['seed'])
        batch = author.call('generate-modes', modes=modes, options=doc['options'], rendered=True,
                            include_baselines=True, document=dict(adjustments=doc['adjustments'],
                            overrides=doc['overrides']), **source)
        if 'baselines' not in batch:
            raise ValueError('Mode previews require an updated engine; run python3 -B tools/verify_anodize.py build')
        generated, rendered = batch['baselines'], batch['palettes']
    with sequence('Generating mode previews', len(modes), unit='mode') as previews:
        for mode in modes:
            with previews.step(mode):
                draft = copy.deepcopy(doc)
                draft['options']['mode'] = mode
                if generated:
                    draft['baseline'] = generated[mode]
                else:
                    draft['baseline'] = author.call('variant', document={k: v for k, v in draft.items() if k != 'generated'})['colors']
                colors = rendered[mode] if generated else author.render(draft)['colors']
                result.append(dict(document=draft, id=mode, mode='light' if draft['options']['light'] else 'dark',
                                   colors=colors))
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
        colors = author.render(doc)['colors']
        view = ColorView(colors, preview=True)
        with permanent_output():
            render_logo(Presentation(), colors=colors, view=view)
            render_preview(doc['id'], colors, 'light' if doc['options']['light'] else 'dark', view=view)
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
    from logo import dimensions, text_banner, utf8_output
    utf8_output(sys.stdout)
    view = ColorView(preview=True)
    rows = view.pane_height or dimensions(sys.stdout)[1]
    return text_banner(view.available, rows)


def preview(snapshot, token):
    if not token.isdecimal():
        raise ValueError('invalid preview token')
    doc = json.loads(regular_bytes(snapshot, 16 << 20))
    row = doc['rows'][int(token)]
    os.environ['DOTS_COLOR'] = 'always' if doc['color'] else 'never'
    if doc.get('comparison'):
        from authoring import Author
        from patina import comparison_thumbnail
        row = comparison_thumbnail(Author(), Path(doc['comparison']), int(token), row)
    if 'thumbnail' in row:
        from patina import thumbnail_lines
        view = ColorView(row['colors'], preview=True)
        view.title(row['id'])
        if row.get('target'):
            view.line(view.resource(row['target']))
        for line in thumbnail_lines(row['thumbnail'], doc['color'], view.available, max(1, view.pane_height - 2) if view.pane_height else None):
            view.line(line)
    elif row.get('error'):
        Presentation().detail('Unavailable', row['error'])
    else:
        render_preview(row['id'], row['colors'], row.get('mode', ''), logo=preview_logo())


if __name__ == '__main__':
    try:
        preview(*sys.argv[1:])
    except (ValueError, OSError, IndexError, TypeError, KeyError) as error:
        print('Preview unavailable: ' + str(error))
        sys.exit(1)
