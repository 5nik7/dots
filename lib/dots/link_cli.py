#!/usr/bin/env python3
"""Safe ln-style symlinks using native primitives inside the shared Store."""
import argparse
import json
import os
from pathlib import Path
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / 'files'))
from backup_catalog import BackupPlan, absolute, disjoint
from catalog import Presentation
from transactions import exists


def prepare(plan, sources, destination, *, exact=False, relative=False, allow_missing=False, backup=True):
    sources = [plan.path(source) for source in sources]
    destination = absolute(destination)
    container = destination.is_dir() and not exact
    if len(sources) > 1 and not container:
        raise ValueError('multiple sources require an existing target directory')
    targets = [plan.path(destination / source.name if container else destination) for source in sources]
    disjoint(targets)
    for source, target in zip(sources, targets):
        if not allow_missing and not source.exists():
            raise ValueError('source is missing or broken; use --allow-missing: ' + str(source))
        if source == target or target in source.parents or source.is_dir() and source in target.parents:
            raise ValueError('source and target overlap: ' + str(target))
        if any(target == other or target in other.parents for other in sources):
            raise ValueError('a target would replace another source')
        plan.protect_source(target)
        link = os.path.relpath(source, target.parent) if relative else str(source)
        plan.guard(target)
        if target.is_symlink() and absolute(target.parent / os.readlink(target)) == source:
            plan.items.append(dict(action='unchanged', source=str(source), target=str(target)))
            continue
        record = plan.snapshot(target, origin='link') if exists(target) and backup else None
        plan.add(dict(path=str(target), link=link, directory=source.is_dir()))
        plan.items.append(dict(action='link', source=str(source), target=str(target),
                               backup=record['id'] if record else None,
                               backup_retained=backup))
    return plan


def render(data, args):
    if args.json:
        print(json.dumps(data, ensure_ascii=True)); return
    if args.quiet:
        return
    from style_config import current
    ui = Presentation()
    prefs = current()
    for row in data['items']:
        if row.get('action') not in ('link','unchanged'):
            continue
        source, target = row['source'], row['target']
        source_style = ui.resources.describe(source)[2] if ui.color else None
        target_style = ui.resources.describe(target, 'symlink')[2] if ui.color else None
        spans = []
        if ui.icons:
            fields = prefs.style('icons.operations.link',app='cli') if prefs else {}
            style = prefs.sgr('icons.operations.link',app='cli') if fields else '94'
            spans.append((ui.icon('operations.link','󰡯') + ' ', style))
        if args.dry_run and row['action'] == 'link':
            spans.append(('Would link ', '90'))
        spans += [(ui.clean(ui.path(source)),source_style), (' -> ','90'),
                  (ui.clean(ui.path(target)),target_style)]
        if row['action'] == 'unchanged': spans.append((' (unchanged)', '90'))
        ui.heading_spans(spans)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dots link', description='Create symlinks safely; move conflicting objects into backups by default.')
    parser.add_argument('paths', nargs='+', metavar='PATH')
    parser.add_argument('-T','--no-target-directory', action='store_true')
    parser.add_argument('-r','--relative', action='store_true')
    parser.add_argument('--allow-missing', action='store_true')
    parser.add_argument('--no-backup', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('-q','--quiet', action='store_true')
    parser.add_argument('--store-dir')
    parser.add_argument('--in-place', action='store_true')
    for name in ('color','icons'):
        parser.add_argument('--' + name, choices=('auto','always','never'))
    args = parser.parse_intermixed_args(argv)
    if len(args.paths) < 2:
        parser.error('provide SOURCE TARGET or SOURCE... DIRECTORY')
    for name in ('color','icons'):
        if getattr(args,name): os.environ['DOTS_' + name.upper()] = getattr(args,name)
    if args.json or args.quiet or args.dry_run:
        os.environ['DOTS_PROGRESS'] = 'never'
    from config_values import Controls
    from profile_config import checkout
    controls = Controls(checkout())
    values = controls.values.get('apps',{}).get('bak',{})
    plan = BackupPlan(directory=args.store_dir or values.get('store','~/.bakstore'),
                      location='adjacent' if args.in_place else 'store' if args.store_dir else values.get('location','store'))
    for path in controls.paths: plan.guard(path)
    prepare(plan, args.paths[:-1], args.paths[-1], exact=args.no_target_directory,
            relative=args.relative, allow_missing=args.allow_missing, backup=not args.no_backup)
    render(plan.report() if args.dry_run else plan.apply('link'), args)
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError,ValueError) as error:
        print('dots link: ' + Presentation.clean(str(error)),file=sys.stderr); sys.exit(1)
    except KeyboardInterrupt: sys.exit(130)
