"""One approval for create-only Patina exports across the theme catalog."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile

from authoring import ID, regular_bytes
from file_platform import config_root
from interaction import gum_confirm
from patina import (IMAGE_LIMIT, available_styles, destination, image_guard, output_settings,
                    save_image, settings, staged_image, theme_guards, theme_palettes)
from progress import sequence
from transactions import DestinationOccupied


def confirm_batch():
    approved = gum_confirm('Save images for all themes?', action='Save images')
    if approved is not None:
        return approved
    return input('Save images? [y/N] (Enter to cancel) ').strip().lower() in ('y', 'yes', 'save images')


def save_variant(author, args, row, base, request, encoding, guards):
    with tempfile.TemporaryDirectory(prefix='anodize-patina-') as tmp:
        stage, _ = staged_image(author, Path(tmp), request, settings(args, row['style']), encoding)
        while True:
            target = destination(base, True)
            try:
                receipt = save_image(author, stage, target, guards)
            except DestinationOccupied:
                continue
            row.update(status='saved', target=str(target), transaction=receipt['id'])
            return


def require_source(source, expected):
    try:
        if image_guard(source) == expected:
            return
    except (ValueError, OSError) as exc:
        raise ValueError(f'input is no longer available: {source} ({exc})') from exc
    raise ValueError(f'input changed during batch: {source}')


def theme_request(author, args, theme, image):
    guards = theme_guards(author, theme)
    authored, variants, _ = theme_palettes(author, theme, [args.mode] if args.mode else [], args.light, args.dark)
    colors = variants[args.mode] if args.mode else authored
    for stop in args.stops or ():
        if stop not in colors:
            raise ValueError('unknown palette stop: ' + stop)
    return dict(image=image, colors=colors, palette=sorted(set(colors.values()))), guards


def render_batch(author, args, source, expected, groups, encoding, total):
    image = base64.b64encode(regular_bytes(source, IMAGE_LIMIT)).decode()
    require_source(source, expected)
    item_errors = (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError)
    with sequence('Saving Patina images', total, unit='image') as progress:
        for theme, entries in groups.items():
            planned = [row for row, _ in entries if row['status'] == 'planned']
            if planned:
                try:
                    request, guards = theme_request(author, args, theme, image)
                    guards[str(source)] = expected
                except item_errors as exc:
                    require_source(source, expected)
                    for row in planned:
                        row.update(status='failed', error=str(exc))
            for row, base in entries:
                with progress.step(f"{theme} / {row['style']}"):
                    if row['status'] != 'planned':
                        continue
                    require_source(source, expected)
                    try:
                        save_variant(author, args, row, base, request, encoding, guards)
                    except item_errors as exc:
                        require_source(source, expected)
                        row.update(status='failed', error=str(exc))


def plan_destinations(themes, root, relative, styles, all_styles):
    groups = {}
    for theme in themes:
        if not ID.fullmatch(theme):
            raise ValueError('invalid theme ID in catalog')
        entries = groups[theme] = []
        for style in styles:
            name = relative.with_stem(f'{relative.stem}_{style}') if all_styles else relative
            base = root / theme / name
            row = dict(id=theme, style=style, target=str(base), status='planned')
            try:
                row['target'] = str(destination(base, True))
            except (ValueError, OSError) as exc:
                row.update(status='failed', error=str(exc))
            entries.append((row, base))
    return groups


def save_all_themes(author, args, present):
    source = Path(args.file).absolute()
    expected = image_guard(source)
    relative, encoding = output_settings(args, source, batch=True)
    if args.mode:
        modes = json.loads((Path(__file__).parent / 'engine/modes.json').read_bytes())
        if args.mode not in {mode['id'] for mode in modes}:
            raise ValueError('unknown palette mode: ' + args.mode)
    styles = available_styles(args)
    root = config_root() / 'dots/backgrounds'
    groups = plan_destinations(author.identities(), root, relative, styles, args.all_styles)
    outputs = [row for entries in groups.values() for row, _ in entries]
    if not outputs:
        raise ValueError('no themes or compatible styles available for export')
    pattern = relative.with_stem(relative.stem + '_<style>') if args.all_styles else relative
    summary = dict(schema=1, source=str(source), theme_count=len(groups), styles=styles,
                   total=len(outputs), destination=str(root / '<theme>' / pattern), **encoding)
    if args.dry_run:
        present(dict(summary, status='preview', outputs=outputs), args.json)
        if any(row['status'] == 'failed' for row in outputs):
            raise SystemExit(1)
        return
    present(dict(summary, status='ready'))
    if not confirm_batch():
        return
    exit_code = 1
    try:
        render_batch(author, args, source, expected, groups, encoding, len(outputs))
    except KeyboardInterrupt:
        summary['stopped'] = 'interrupted'
        exit_code = 130
    except (OSError, ValueError) as exc:
        summary['stopped'] = str(exc)
    saved = sum(row['status'] == 'saved' for row in outputs)
    failed = sum(row['status'] == 'failed' for row in outputs)
    remaining = len(outputs) - saved - failed
    present(dict(summary, status='complete' if saved == len(outputs) else 'incomplete',
                 saved=saved, failed=failed, remaining=remaining, outputs=outputs))
    if 'stopped' in summary or saved != len(outputs):
        raise SystemExit(exit_code)
