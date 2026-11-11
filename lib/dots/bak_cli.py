#!/usr/bin/env python3
"""Native backup frontend; all file writes are planned by backup_catalog."""
import argparse
from copy import copy
import json
import os
from pathlib import Path
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / 'files'))
from backup_catalog import BackupPlan
from bak_commands import COMMANDS
from catalog import Presentation
from interaction import SelectionEnded, gum_confirm, terminal


def parser():
    result = argparse.ArgumentParser(prog='bak', description='Move files into recoverable backups. Restore retains saved versions.',
        epilog='Commands: ' + ', '.join(k for k in COMMANDS if k) + '. Use bak -- NAME for a filename matching a command.')
    result.add_argument('values', nargs='*', metavar='COMMAND_OR_PATH')
    for name in ('json','dry-run','no-backup'):
        result.add_argument('--' + name, action='store_true')
    result.add_argument('-q','--quiet', action='store_true')
    result.add_argument('-v','--verbose', action='store_true')
    result.add_argument('-y','--yes', action='store_true')
    location = result.add_mutually_exclusive_group()
    location.add_argument('-s','--store', action='store_true')
    location.add_argument('--in-place', action='store_true')
    mode = result.add_mutually_exclusive_group()
    mode.add_argument('--copy', action='store_true')
    mode.add_argument('--move', action='store_true')
    for name in ('store-dir','to','original'):
        result.add_argument('--' + name)
    for name in ('keep','older-than'):
        result.add_argument('--' + name, type=int)
    for name in ('color','icons'):
        result.add_argument('--' + name, choices=('auto','always','never'))
    return result


def preferences(args):
    from config_values import Controls
    from profile_config import checkout
    controls = Controls(checkout())
    values = controls.values.get('apps', {}).get('bak', {})
    location = 'adjacent' if args.in_place else 'store' if args.store else values.get('location','store')
    directory = args.store_dir or values.get('store', '~/.bakstore')
    if args.store_dir:
        location = 'store'
    plan = BackupPlan(directory=directory, location=location)
    for path in controls.paths:
        plan.guard(path)
    mode = 'copy' if args.copy else 'move' if args.move else values.get('mode', 'move')
    return plan, mode


def render(data, args, stream=None):
    if args.json and stream is None:
        print(json.dumps(data, ensure_ascii=True)); return
    if args.quiet and stream is None:
        return
    ui = Presentation(stream)
    ui.heading('Backups')
    if data.get('status'):
        ui.detail('Result', data['status'])
    rows = data.get('items', [])
    if not rows:
        ui.emit('  No matching backups.')
    for row in rows:
        ui.emit()
        for key in ('id','action','created','kind','mode','origin','status'):
            if row.get(key) is not None:
                ui.detail(key.title(), row[key], '94' if key == 'id' else None)
        for key in ('original','path','source','target'):
            if row.get(key):
                ui.resource_detail(key.title(), row[key], kind='symlink' if row.get('kind') == 'link' else row.get('kind'))
        if row.get('protected'):
            ui.detail('Retention', 'Required for uninstall', '33')
        if row.get('original') is None and row.get('origin') == 'import':
            ui.detail('Restore', 'Original path unknown; supply --to', '33')
    if data.get('transaction'):
        ui.detail('Transaction', data['transaction'])
    if args.dry_run:
        ui.emit('\n  No changes made.')


def confirm(plan, args):
    if not plan.finish() or args.yes:
        return
    if args.json or not terminal():
        raise ValueError('delete/prune requires --yes when noninteractive; use --dry-run to inspect')
    render(plan.report(), args, sys.stderr)
    accepted = gum_confirm('Apply these backup changes?', 'Apply')
    if accepted is None:
        print('Apply these backup changes? [y/N] ', end='', file=sys.stderr, flush=True)
        accepted = sys.stdin.readline().strip().lower() in ('y','yes')
    if not accepted:
        raise SelectionEnded(130)


def browse(args):
    from menus import Menu, Entry, choose
    from menu_pager import page_text
    import io
    if args.json or args.dry_run or not terminal():
        plan, _ = preferences(args)
        render(dict(schema=1, status='observed', items=plan.records()), args)
        return
    while True:
        plan, _ = preferences(args)
        rows = plan.records()
        entries = tuple(Entry(row['id'], Path(row['original'] or row['path']).name,
                              row['created'] + (' · protected' if row['protected'] else '')) for row in rows)
        selected = choose(Menu('bak:entries','Backups',entries), mode='browse')
        if selected is None:
            return
        row = next(row for row in rows if row['id'] == selected.id)
        actions = [Entry('show','Inspect'), Entry('restore','Restore')]
        if not row['protected']:
            actions.append(Entry('delete','Delete'))
        action = choose(Menu('bak:actions','Backup actions',tuple(actions)), mode='browse',compact=True)
        if action is None:
            continue
        if action.id == 'show':
            output = io.StringIO(); render(dict(items=[row]), args, output)
            page_text(output.getvalue(), title='bak·inspect')
            continue
        draft, _ = preferences(args)
        if action.id == 'restore':
            draft.restore(row['id'])
        else:
            draft.delete([row['id']])
        approval = copy(args); approval.yes = False
        confirm(draft, approval)
        render(draft.apply('bak-' + action.id), args)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    grammar = parser()
    args = grammar.parse_intermixed_args(argv)
    for key in ('color','icons'):
        if getattr(args, key):
            os.environ['DOTS_' + key.upper()] = getattr(args, key)
    if args.json or args.quiet or args.dry_run:
        os.environ['DOTS_PROGRESS'] = 'never'
    before_marker = grammar.parse_intermixed_args(argv[:argv.index('--')]).values if '--' in argv else args.values
    action = args.values.pop(0) if before_marker and args.values[0] and args.values[0] in COMMANDS else 'create' if args.values else 'browse'
    allowed = {'copy': {'create'}, 'move': {'create'}, 'to': {'restore'},
               'no_backup': {'restore'}, 'original': {'import'}, 'keep': {'prune'},
               'older_than': {'prune'}, 'store': {'create','restore'},
               'in_place': {'create','restore'}, 'store_dir': {'create','restore'}}
    for key, actions in allowed.items():
        supplied = getattr(args,key) is not None if key in ('keep','older_than') else bool(getattr(args,key))
        if supplied and action not in actions:
            raise ValueError('--' + key.replace('_','-') + ' is not valid for ' + action)
    if not argv and not terminal():
        grammar.print_help(); return 0
    if action == 'browse':
        if args.values: raise ValueError('browse takes no operands')
        browse(args); return 0
    plan, mode = preferences(args)
    values = args.values
    if action in ('show','restore') and len(values) != 1:
        raise ValueError(action + ' requires one backup ID')
    if action in ('create','import','delete') and not values:
        raise ValueError(action + ' requires at least one operand')
    if action in ('list','prune') and values:
        raise ValueError(action + ' takes no operands')
    if action == 'list':
        render(dict(schema=1,status='observed',items=plan.records()),args); return 0
    if action == 'show':
        plan.entry(values[0])
        render(dict(schema=1,status='observed',items=[r for r in plan.records() if r['id']==values[0]]),args); return 0
    if action == 'create': plan.create(values, copy=mode=='copy')
    elif action == 'import': plan.import_backup(values, original=args.original)
    elif action == 'restore': plan.restore(values[0], destination=args.to, backup=not args.no_backup)
    elif action == 'delete': plan.delete(values)
    elif action == 'prune': plan.prune(keep=args.keep, older_than=args.older_than)
    if args.dry_run:
        render(plan.report(), args)
    else:
        if action in ('delete','prune'): confirm(plan,args)
        from events import OperationOutput
        observer = OperationOutput(args.verbose and not args.quiet and not args.json)
        render(plan.apply('bak-' + action, observer=observer),args)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SelectionEnded as error:
        sys.exit(error.status)
    except (OSError, ValueError) as error:
        print('bak: ' + Presentation.clean(str(error)), file=sys.stderr); sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
