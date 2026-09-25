#!/usr/bin/env python3
"""Anodize CLI: presentation and journal adapter around the pure Go engine."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files'))
from catalog import Presentation
from transactions import digest, exists, parents_safe
from authoring import Author, encode, new_document, regular_bytes, toml_colors


class Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Python 3.14 colors argparse help by default. Presentation owns ANSI;
        # feeding argparse's escapes through its sanitizer prints literal \\x1b.
        self.color = False

    def error(self, message):
        raise UsageError(message)

    def print_help(self, file=None):
        ui = Presentation(file)

        def paragraph(text, indent=2, color=None):
            for line in textwrap.wrap(ui.clean(text), width=ui.width-indent,
                                      break_on_hyphens=False):
                ui.emit(' ' * indent + (ui.paint(line, color) if color else line))

        def rows(title, entries):
            ui.emit()
            ui.heading(title)
            column = min(26, max(len(label) for label, _ in entries) + 2)
            for label, description in entries:
                if ui.width < 60 or len(label) >= column:
                    paragraph(label, color='94')
                    paragraph(description, indent=4)
                else:
                    lines = textwrap.wrap(ui.clean(description), width=ui.width-column-2,
                                          break_on_hyphens=False) or ['']
                    ui.emit('  ' + ui.paint(label.ljust(column), '94') + lines[0])
                    for line in lines[1:]:
                        ui.emit(' ' * (column+2) + line)

        commands = next((a for a in self._actions if isinstance(a, argparse._SubParsersAction)), None)
        ui.heading('Anodize' if commands else self.prog)
        paragraph(self.description)
        ui.emit()
        ui.heading('Usage')
        positional = [a for a in self._actions if not a.option_strings and a is not commands]
        suffix = 'COMMAND [OPTIONS]' if commands else ' '.join([a.dest.upper() for a in positional] + ['[OPTIONS]'])
        paragraph(f'{self.prog} {suffix}', color='95')
        if commands:
            rows('Commands', [(name, child.description) for name, child in commands.choices.items()])
        if positional:
            rows('Arguments', [(a.dest.upper(), a.help) for a in positional])
        options = []
        for action in self._actions:
            if not action.option_strings or action.help == argparse.SUPPRESS:
                continue
            label = ', '.join(action.option_strings)
            if action.nargs != 0:
                label += ' ' + (action.metavar or action.dest.upper())
            description = action.help or ''
            if action.required:
                description += ' (required)'
            if action.choices:
                description += ': ' + ', '.join(action.choices)
            options.append((label, description))
        rows('Options', options)
        if commands:
            ui.emit()
            ui.heading('Examples')
            for example in ("anodize create dusk --color '#725ac1' --dry-run",
                            "anodize create dusk --color '#725ac1' --yes",
                            'anodize preview dusk', 'anodize apply dusk --dry-run'):
                paragraph(example, color='92')
            ui.emit()
            paragraph('Use anodize COMMAND --help for command options.')
            paragraph('Saving a theme does not activate it. Review changes, then use --yes to save or apply.')
            ui.emit()
            paragraph('Before COMMAND: --color=auto|always|never and --icons=auto|always|never control presentation.', color='90')
        elif self.prog.endswith(' create'):
            ui.emit()
            paragraph('Choose exactly one source: --image, --color or --from.', color='93')


class UsageError(ValueError):
    pass


def parser():
    p = Parser(prog='anodize', description='Author palettes and save recoverable Dots themes.')
    sub = p.add_subparsers(dest='action', required=True, parser_class=Parser)
    descriptions = {'modes': 'List extraction modes', 'extract': 'Inspect an image palette', 'create': 'Create an authored theme',
                    'import': 'Import a local blueprint or palette', 'list': 'List authored themes', 'show': 'Inspect an authored theme',
                    'edit': 'Edit an authored theme', 'preview': 'Preview colors or app configuration', 'export': 'Export a theme',
                    'apply': 'Publish through Dots'}
    descriptions['completion'] = 'Print shell completion source'
    for action, description in descriptions.items():
        q = sub.add_parser(action, help=description, description=description)
        if action == 'completion':
            q.add_argument('shell', choices=['bash', 'zsh', 'fish'], help='Shell adapter to print')
            continue
        q.add_argument('--json', action='store_true', help='Emit versioned JSON')
        if action in ('extract', 'import'):
            q.add_argument('file', help='Local image file' if action == 'extract' else 'Local blueprint or palette file')
        elif action not in ('modes', 'list'):
            q.add_argument('id', help='Theme identifier')
        if action in ('create', 'extract', 'edit', 'import'):
            q.add_argument('--mode', help='Extraction mode (default: normal)')
            mode = q.add_mutually_exclusive_group()
            mode.add_argument('--light', action='store_true', help='Use a light palette (exclusive with --dark)')
            mode.add_argument('--dark', action='store_true', help='Use a dark palette (exclusive with --light)')
        if action in ('create', 'edit'):
            q.add_argument('--adjust', action='append', default=[], metavar='NAME=VALUE', help='Set an absolute adjustment; repeat for multiple values')
            q.add_argument('--set', action='append', default=[], metavar='COLOR=HEX', help='Override a named color; repeat for multiple colors')
        if action == 'create':
            src = q.add_mutually_exclusive_group(required=True)
            src.add_argument('--image', metavar='FILE', help='Extract colors from a local image')
            src.add_argument('--color', metavar='HEX', help='Generate from a seed color, such as #725ac1')
            src.add_argument('--from', dest='from_theme', metavar='THEME', help='Derive from an existing Dots theme')
        if action == 'edit':
            q.add_argument('--reset-adjustments', action='store_true', help='Clear adjustments while retaining color overrides')
            q.add_argument('--reextract', action='store_true', help='Regenerate from the saved wallpaper or seed')
        if action in ('create', 'import', 'edit'):
            q.add_argument('--reference-wallpaper', action='store_true', help='Keep an absolute external wallpaper reference')
        if action in ('create', 'import', 'edit', 'export', 'apply'):
            q.add_argument('--dry-run', action='store_true', help='Preview without changes; takes precedence over --yes')
            q.add_argument('--yes', action='store_true', help='Apply the preview without prompting')
        if action == 'import':
            q.add_argument('--name', required=True, metavar='ID', help='Save under this new theme identifier')
            q.add_argument('--format', choices=['anodize', 'aether', 'base16', 'colors'], required=True, help='Input format')
        if action == 'export':
            q.add_argument('--format', choices=['anodize', 'aether', 'colors'], default='anodize', help='Output format (default: anodize)')
            q.add_argument('--output', metavar='FILE', help='Save to a new file; otherwise emit raw stdout')
        if action == 'preview':
            q.add_argument('--app', choices=['kitty', 'tmux', 'btop', 'termux', 'bat', 'yazi'], help='Emit raw app configuration instead of colors')
        if action == 'apply':
            q.add_argument('--background', action='store_true', help='Also activate the wallpaper after publishing the theme')
    return p


def present(result, use_json=False):
    if use_json:
        sys.stdout.buffer.write(encode(result))
        return
    ui = Presentation()
    ui.heading('Anodize')
    if 'modes' in result:
        for mode in result['modes']:
            ui.emit('  ' + ui.paint(mode, '94'))
    if 'items' in result:
        ui.emit('  ' + ui.paint(str(len(result['items'])), '96') + ' authored themes')
        for row in result['items']:
            ui.emit('  ' + ui.paint(row['id'], '94') + '  ' + ui.paint(row['mode'], '90'))
        if not result['items']:
            ui.emit('  No authored themes. Use anodize create to make one.')
    if 'id' in result:
        ui.detail('Theme', result['id'])
    if 'status' in result:
        code = '93' if result['status'] == 'preview' else '92'
        ui.emit('  ' + ui.paint(result['status'], code))
    if 'target' in result:
        ui.detail('Target', ui.path(result['target']))
    for target in result.get('connectors', []):
        ui.detail('Connector', ui.path(target))
    for name in result.get('files', []):
        ui.detail('File', name)
    if result.get('transaction'):
        ui.detail('Transaction', result['transaction'])
        ui.detail('Undo', 'dots files undo ' + result['transaction'])
    if result.get('wallpaper'):
        ui.detail('Wallpaper', ui.path(result['wallpaper']))
    if 'contrast' in result:
        ui.detail('Contrast', f'{result["contrast"]:.2f}:1 foreground/background')
    if 'colors' in result:
        for key, value in sorted(result['colors'].items()):
            if key.startswith('color') and key[5:].isdigit():
                continue
            if ui.color:
                rgb = ';'.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))
                swatch = f'\033[48;2;{rgb}m  \033[0m '
            else:
                swatch = ''
            ui.emit('  ' + swatch + ui.paint(f'{key:<22}', '94') + ' ' + value)
    for note in result.get('notes', []):
        ui.detail('Note', note)
    if result.get('status') == 'preview':
        ui.emit('  Preview only; no changes made. Use --yes to apply.')


def confirm(args, view):
    if args.dry_run:
        present(view, args.json)
        return False
    if args.yes:
        return True
    if args.json or not sys.stdin.isatty():
        present(view, args.json)
        return False
    present(view)
    return input('Apply this plan? [y/N] ').strip().lower() in ('y', 'yes')


def pairs(values, numeric=False):
    result = {}
    for value in values:
        key, sep, item = value.partition('=')
        if not sep or not key or not item:
            raise UsageError('expected NAME=VALUE')
        result[key] = float(item) if numeric else item
    return result


def main(argv=None):
    p = parser()
    values = list(sys.argv[1:] if argv is None else argv)
    if values and values[0] == '__complete':
        from integration import complete
        return complete(values[1:], p)
    # Match Dots prefix presentation flags for the standalone entry point.
    while values and (values[0].startswith('--color=') or values[0].startswith('--icons=')):
        key, value = values.pop(0)[2:].split('=', 1)
        if value not in ('auto', 'always', 'never'):
            raise UsageError('presentation mode must be auto, always, or never')
        os.environ['DOTS_' + key.upper()] = value
    if not values:
        p.print_help()
        return
    args = p.parse_args(values)
    if args.action == 'completion':
        source = Path(__file__).with_name('completion') / args.shell
        sys.stdout.write(source.read_text())
        return
    author = Author()
    action = args.action
    if action == 'modes':
        present(author.call('modes'), args.json)
        return
    if action == 'list':
        rows = []
        for path in sorted(author.themes.glob('*/anodize.json')):
            doc = author.load(path.parent.name, owned=True)
            rows.append(dict(id=doc['id'], mode='light' if doc['options']['light'] else 'dark'))
        present(dict(schema=1, items=rows), args.json)
        return
    if action == 'extract':
        opts = dict(mode=args.mode or 'normal', light=args.light)
        doc = new_document('preview', author.generate(args.file, options=opts), **dict(light=opts['light'], mode=opts['mode']))
        present(dict(author.render(doc), id='preview'), args.json)
        return
    if action in ('create', 'import', 'edit'):
        notes = []
        wallpaper = None
        if action == 'import':
            doc, notes = author.imported(args.file, args.name, args.format)
        elif action == 'edit':
            doc = copy.deepcopy(author.load(args.id, owned=True))
            if args.reset_adjustments:
                doc['adjustments'] = {}
        elif args.from_theme:
            original = author.load(args.from_theme)
            doc = new_document(args.id, author.render(original)['colors'], original['options']['light'], original['options']['mode'])
            if original.get('wallpaper'):
                wallpaper = Path(original['wallpaper'])
                if not wallpaper.is_absolute():
                    wallpaper = author.target(args.from_theme) / wallpaper
                wallpaper = str(wallpaper)
        else:
            opts = dict(mode=args.mode or 'normal', light=args.light)
            doc = new_document(args.id, author.generate(args.image, args.color, opts), **dict(light=opts['light'], mode=opts['mode']))
            if args.image:
                wallpaper = str(Path(args.image).absolute())
            if args.color:
                doc['seed'] = args.color
        changed_generation = bool(args.mode and args.mode != doc['options']['mode']) or (args.light and not doc['options']['light']) or (args.dark and doc['options']['light'])
        doc['options']['mode'] = args.mode or doc['options']['mode']
        if args.light or args.dark:
            doc['options']['light'] = args.light
        if changed_generation or (action == 'edit' and args.reextract):
            wall = doc.get('wallpaper')
            if wall and not Path(wall).is_absolute():
                wall = str(author.target(doc['id']) / wall)
            if wallpaper:
                wall = wallpaper
            if wall or doc.get('seed'):
                doc['baseline'] = author.generate(wall, None if wall else doc.get('seed'), doc['options'])
            elif action == 'edit' and args.reextract:
                raise ValueError('re-extraction requires a saved wallpaper or seed')
            else:
                doc['baseline'] = author.call('variant', document={k: v for k, v in doc.items() if k != 'generated'})['colors']
        if action != 'import':
            doc['adjustments'].update(pairs(args.adjust, numeric=True))
            doc['overrides'].update(pairs(args.set))
        plan = author.prepare(doc, edit=action == 'edit', reference=args.reference_wallpaper, wallpaper=wallpaper)
        view = dict(schema=1, id=doc['id'], target=plan['target'], status=plan['status'], notes=notes,
                    files=sorted(plan['files']))
        if doc.get('wallpaper'):
            view['wallpaper'] = doc['wallpaper']
            if Path(doc['wallpaper']).is_absolute():
                view['notes'].append('External wallpaper dependency; keep this file available.')
        if plan['status'] == 'unchanged':
            present(view, args.json)
        elif confirm(args, view):
            result = author.save(plan)
            present(dict(view, status=result['status'], transaction=result.get('id')), args.json)
        return
    if action in ('show', 'preview', 'export'):
        doc = author.load(args.id)
        rendered = author.render(doc)
        if action == 'preview' and args.app:
            if args.json:
                raise UsageError('--app returns raw configuration; omit --json')
            names = dict(kitty='kitty.conf', tmux='tmux.conf', btop='btop.theme', termux='termux.properties', bat='bat.tmTheme', yazi='yazi.toml')
            with tempfile.TemporaryDirectory(prefix='anodize-preview-') as tmp:
                author.theme_bridge('render', args.id, tmp)
                sys.stdout.buffer.write(regular_bytes(Path(tmp) / names[args.app]))
            return
        if action in ('show', 'preview'):
            present(dict(rendered, id=doc['id'], wallpaper=doc.get('wallpaper')), args.json)
            return
        if args.format == 'colors':
            content = toml_colors(rendered['colors'], doc['options']['light'])
        elif args.format == 'aether':
            from authoring import NAMES
            content = encode(dict(name=doc['id'], palette=dict(colors=[rendered['colors'][k] for k in NAMES],
                                   mode='light' if doc['options']['light'] else 'dark',
                                   lightMode=doc['options']['light'], extendedColors=rendered['colors'])))
        else:
            exported = {k: v for k, v in doc.items() if k != 'generated'}
            if exported.get('wallpaper') and not Path(exported['wallpaper']).is_absolute():
                exported['wallpaper'] = str(author.target(args.id) / exported['wallpaper'])
            content = encode(exported)
        if not args.output:
            if args.dry_run:
                raise UsageError('--dry-run requires --output; stdout export is already read-only')
            if args.json and args.format != 'anodize':
                raise UsageError('raw export has its own format; omit --json')
            sys.stdout.buffer.write(content)
            return
        path = Path(args.output).absolute()
        parents_safe(path)
        if exists(path):
            raise ValueError('export destination already exists')
        view = dict(schema=1, status='preview', target=str(path))
        if confirm(args, view):
            with tempfile.TemporaryDirectory(prefix='anodize-export-') as tmp:
                src = Path(tmp) / 'export'
                src.write_bytes(content)
                result = author.store().apply('anodize-export', [{'path': str(path), 'source': str(src)}], {str(path): None}, retain=True)
            present(dict(view, status=result['status'], transaction=result.get('id')), args.json)
        return
    if action == 'apply':
        # Always obtain the publisher's real preflight before approval.
        wallpaper = None
        if args.background:
            doc = author.load(args.id)
            wallpaper = doc.get('wallpaper')
            if wallpaper and not Path(wallpaper).is_absolute():
                wallpaper = str(author.target(args.id) / wallpaper)
            if wallpaper:
                regular_bytes(wallpaper, 32 << 20)
                if Path(wallpaper).suffix.lower() == '.gif':
                    raise ValueError('wallpaper activation requires PNG or JPEG; GIF palettes can still be applied without --background')
        raw, _ = author.theme_bridge('plan', args.id, *(['background', wallpaper or ''] if args.background else []))
        view = json.loads(raw)
        view.update(id=args.id, target=view['publish'], notes=['Apply wallpaper too.'] if args.background else [])
        if wallpaper:
            view['wallpaper'] = wallpaper
        if confirm(args, view):
            raw, diagnostics = author.theme_bridge('apply', args.id, *(['background', wallpaper or ''] if args.background else []))
            if diagnostics:
                sys.stderr.buffer.write(diagnostics)
            present(dict(json.loads(raw), id=args.id), args.json)
        return


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('anodize: ' + str(exc), '91'))
        sys.exit(2 if isinstance(exc, UsageError) else 1)
