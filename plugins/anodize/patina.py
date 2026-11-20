"""Patina's staged image export and personal background naming."""
import argparse
import base64
from pathlib import Path
import shutil
import stat
import sys
import tempfile

from authoring import regular_bytes
from file_platform import config_root
from progress import tracked
from transactions import DestinationOccupied, digest, exists, parents_safe

IMAGE_LIMIT = 32 << 20


DEFAULT_STYLE = 'alloy'
# Comparison-sheet numbers follow this order. The picker leads with the default.
STYLES = ('harmonize', 'gradient', 'duotone', 'exact', 'shaded', 'natural', 'palette-blend',
          'color-transfer', 'split-tone', 'muted', 'vivid', 'pastel', 'night', 'accent',
          'posterize', 'dither', 'ink', DEFAULT_STYLE)
PICKER_STYLES = (DEFAULT_STYLE, *(style for style in STYLES if style != DEFAULT_STYLE))
FORMATS = ('png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp', 'tif', 'tiff', 'avif')
OPTIONAL_CODECS = {'webp': 'WEBP', 'tiff': 'TIFF', 'bmp': 'BMP', 'avif': 'AVIF'}
HARMONIES = ('auto', 'analogous', 'complementary', 'source', 'palette')


def percent(value):
    try:
        number = int(value)
    except ValueError:
        number = -1
    if not 0 <= number <= 100:
        raise argparse.ArgumentTypeError('strength must be an integer from 0 to 100')
    return number


def stop_names(value):
    names = [name.strip() for name in value.split(',')]
    if len(names) < 2 or any(not name for name in names):
        raise argparse.ArgumentTypeError('supply at least two comma-separated palette names')
    return names


def available_styles(args):
    guided = args.interactive and '--style' not in getattr(args, '_provided', ())
    styles = PICKER_STYLES if guided else (args.style,)
    return [style for style in styles
            if (args.harmony is None or style in (DEFAULT_STYLE, 'harmonize', 'natural'))
            and (args.strength is None or style not in ('exact', 'shaded'))
            and (args.stops is None or style == 'gradient' or style == 'duotone' and len(args.stops) == 2)]


def settings(args, style):
    values = dict(style=style, harmony=args.harmony, strength=args.strength, stops=args.stops)
    return {key: value for key, value in values.items() if value is not None}


def image_guard(path):
    parents_safe(path)
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > IMAGE_LIMIT:
        raise ValueError('expected a regular image of at most 32 MiB: ' + str(path))
    return digest(path)


def destination(base, automatic):
    parents_safe(base)
    candidate = base
    number = 0
    while exists(candidate):
        if not automatic:
            raise ValueError('output already exists: ' + str(candidate))
        number += 1
        candidate = base.with_name(f'{base.stem}_{number}{base.suffix}')
    return candidate


@tracked('Rendering Patina image')
def render(author, request, options, stage, preview):
    payload = dict(request, **options)
    if not preview:
        payload['columns'] = 0
    with stage.open('xb') as stream:
        return author.call('patina', image_stream=stream, **payload)


@tracked('Previewing Patina styles')
def style_previews(author, request, candidates):
    return author.call('patina-previews', **request, candidates=candidates)['thumbnails']


def select_style(author, request, args):
    from interactive import choose
    styles = available_styles(args)
    def preview_rows():
        previews = style_previews(author, request, [settings(args, style) for style in styles])
        return [dict(id=style, thumbnail=thumbnail, colors=request['colors'])
                for style, thumbnail in zip(styles, previews, strict=True)]

    return styles[choose('Recoloring style', styles, preview_rows)]


def thumbnail_lines(thumbnail, colored, max_width=None, max_lines=None):
    width = thumbnail['width']
    pixels = base64.b64decode(thumbnail['pixels'], validate=True)
    rows = len(pixels) // (width * 4)
    scale = min(1, (max_width or width) / width, 2 * (max_lines or rows) / rows)
    cols, height = max(1, round(width * scale)), max(1, round(rows * scale))
    shades = ' .:-=+*#%@'
    def sample(x, y):
        sx, sy = (2*x + 1)*width//(2*cols), (2*y + 1)*rows//(2*height)
        i = (sy * width + sx) * 4
        return tuple(value * pixels[i+3] // 255 for value in pixels[i:i+3])
    for y in range(0, height, 2):
        line = []
        for x in range(cols):
            top, bottom = sample(x, y), sample(x, min(y+1, height-1))
            if colored:
                line.append('\033[38;2;%d;%d;%d;48;2;%d;%d;%dm▀' % (*top, *bottom))
            else:
                brightness = sum(w*(a+b)/2 for a,b,w in zip(top,bottom,(0.2126,0.7152,0.0722)))
                line.append(shades[round(brightness*(len(shades)-1)/255)])
        yield ''.join(line) + ('\033[0m' if colored else '')


def output_settings(args, source):
    sheet = args.compare or args.compare_modes
    extension = args.format or 'png'
    if args.output:
        base = Path(args.output).absolute()
        if base.suffix:
            extension = base.suffix[1:].lower()
            if extension not in FORMATS:
                raise ValueError('unsupported output extension: ' + base.suffix)
        else:
            base = base.with_name(base.name + '.' + extension)
    elif sheet:
        label = 'styles' if args.compare else 'modes'
        base = source.with_name(f'{source.stem}_{label}.{extension}')
    elif args.theme:
        filename = source.name if source.suffix.lower() == '.' + extension else source.stem + '.' + extension
        base = config_root() / 'dots/backgrounds' / args.theme / filename
    else:
        raise ValueError('--output is required with --palette-image')
    fmt = {'jpg': 'jpeg', 'tif': 'tiff'}.get(extension, extension)
    opts = dict(format=fmt)
    if args.lossless:
        if fmt != 'webp' or args.quality is not None:
            raise ValueError('--lossless requires WebP output and cannot be combined with --quality')
        opts['lossless'] = True
    elif args.quality is not None or fmt in ('jpeg', 'webp', 'avif'):
        if fmt not in ('jpeg', 'webp', 'avif'):
            raise ValueError('--quality requires JPEG, WebP or AVIF output')
        opts['quality'] = args.quality if args.quality is not None else (80 if fmt == 'avif' else 90)
        if not 1 <= opts['quality'] <= 100:
            raise ValueError('--quality must be between 1 and 100')
    if fmt in OPTIONAL_CODECS:
        try:
            from PIL import Image
            Image.init()
            if OPTIONAL_CODECS[fmt] not in Image.SAVE:
                raise ImportError()
        except ImportError:
            raise ValueError(f'{fmt.upper()} output requires Pillow with its {fmt.upper()} encoder') from None
    return base, opts


def mode_palettes(author, ids, light, **source):
    return author.call('generate-modes', modes=ids, options=dict(light=light),
                       rendered=True, **source)['palettes']


def run(author, args, confirm, present):
    source = Path(args.file).absolute()
    guards = {str(source): image_guard(source)}
    automatic = args.output is None
    theme_dir = author.target(args.theme) if args.theme else None
    base, encoding = output_settings(args, source)
    target = destination(base, automatic)
    pick_mode = args.interactive and args.palette_image and not (args.mode or args.compare_modes)
    mode_ids = author.call('modes')['modes'] if args.compare_modes or pick_mode else []
    if args.theme:
        for name in ('anodize.json', 'theme.toml', 'colors.toml', 'palette.toml'):
            path = theme_dir / name
            guards[str(path)] = digest(path)
        doc = author.load(args.theme)
        authored = author.render(doc)['colors']
        light = args.light or (doc['options']['light'] and not args.dark)
        ids = mode_ids or ([args.mode] if args.mode else [])
        palettes = mode_palettes(author, ids, light, colors=authored) if ids else {}
        colors = palettes[args.mode] if args.mode else authored
        selection = dict(id=args.theme)
        if ids:
            selection['light'] = light
        if args.mode:
            selection['mode'] = args.mode
    else:
        reference = Path(args.palette_image).absolute()
        guards[str(reference)] = image_guard(reference)
        mode = args.mode or 'normal'
        palettes = mode_palettes(author, mode_ids or [mode], args.light,
                                  image=base64.b64encode(regular_bytes(reference, IMAGE_LIMIT)).decode())
        colors = palettes[mode]
        selection = dict(palette_image=str(reference), mode=mode, light=args.light)

    for name in args.stops or ():
        if name not in colors:
            raise ValueError('unknown palette stop: ' + name)
    preview = not args.json and sys.stdout.isatty() and (args.dry_run or not args.yes)
    columns, lines = shutil.get_terminal_size()
    request = dict(image=base64.b64encode(regular_bytes(source, IMAGE_LIMIT)).decode(),
                   colors=colors, palette=sorted(set(colors.values())),
                   columns=max(1, min(columns, 120)-4), rows=max(1, min(30, lines//2)))
    if pick_mode:
        from interactive import choose
        def preview_modes():
            preview_style = available_styles(args)[0]
            candidates = [dict(settings(args, preview_style), colors=palettes[mode]) for mode in mode_ids]
            previews = style_previews(author, request, candidates)
            return [dict(id=mode, colors=palettes[mode], thumbnail=thumb)
                    for mode, thumb in zip(mode_ids, previews, strict=True)]
        mode = mode_ids[choose('Extraction mode', mode_ids, preview_modes)]
        colors = palettes[mode]
        selection['mode'] = mode
        request.update(colors=colors, palette=sorted(set(colors.values())))
    if args.interactive and '--style' not in args._provided and not args.compare:
        args.style = select_style(author, request, args)
    options = settings(args, args.style)
    if args.compare:
        request.update(sheet=True, candidates=[dict(style=style, label=style) for style in STYLES])
        selection['comparison'] = 'styles'
    elif args.compare_modes:
        candidates = [dict(options, colors=palettes[mode], label=mode) for mode in mode_ids]
        if args.theme:
            candidates.insert(0, dict(options, colors=authored, label='as-authored'))
        request.update(sheet=True, candidates=candidates)
        selection['comparison'] = 'modes'
    with tempfile.TemporaryDirectory(prefix='anodize-patina-') as tmp:
        fmt = encoding['format']
        request.update(format='png' if fmt in ('webp', 'tiff', 'avif') else fmt,
                       quality=encoding.get('quality', 0))
        stage = Path(tmp) / 'render'
        meta = render(author, request, options, stage, preview)
        del request
        if meta.pop('patina_version', None) != 2:
            raise ValueError('Patina requires an updated engine; run python3 -B tools/verify_anodize.py build in Dots')
        if fmt in OPTIONAL_CODECS:
            from PIL import Image
            final = Path(tmp) / ('image.' + fmt)
            with Image.open(stage) as img:
                img.save(final, format=OPTIONAL_CODECS[fmt], **{k: v for k, v in encoding.items() if k != 'format'})
            stage = final
        if any(digest(path) != expected for path, expected in guards.items()):
            raise ValueError('Patina input changed during render')
        effective = meta.pop('settings')
        view = dict(meta, status='preview', source=str(source), **effective, **selection, **encoding)
        while True:
            view['target'] = str(target)
            if not confirm(args, view, colors):
                return
            if args.theme and author.render(author.load(args.theme))['colors'] != authored:
                raise ValueError('theme colors changed after preview')
            try:
                result = author.store().apply('anodize-patina',
                    [dict(path=str(target), source=str(stage), create_only=True)],
                    {**guards, str(target): None}, retain=True)
            except DestinationOccupied:
                if not automatic:
                    raise
                target = destination(base, True)
                continue
            view.pop('thumbnail', None)
            present(dict(view, status=result['status'], transaction=result['id']), args.json, colors)
            return
