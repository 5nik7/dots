#!/usr/bin/env python3
"""Portable cleanup frontend; destructive rules are currently Termux-only."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cleanup_commands import COMMANDS, OPTIONS
from cleanup.termux import GROUPS, ORDINARY, CHECKPOINTS, Termux
from cleanup.core import public
from cleanup.receipts import Receipts, totals
from cleanup.presentation import render, confirm
from cleanup.engine import run, available
from platform_info import detect
from progress import configure, Progress


def parser(action):
    result = argparse.ArgumentParser(prog='dots cleanup'+(' '+action if action else ''),
                                     description=COMMANDS[action][0])
    if hasattr(result, 'color'): result.color = False
    for flag, short, kind, help_text in OPTIONS[action]:
        kwargs = dict(help=help_text)
        if flag in ('--group','--exclude'): kwargs.update(action='append', default=[])
        if kind == 'flag': kwargs['action'] = 'store_true'
        elif kind.startswith('choice:'): kwargs['choices'] = kind[7:].split(',')
        elif flag in ('--older-than','--limit'): kwargs['type'] = int
        if flag == '--limit': kwargs['default'] = 20
        result.add_argument(*([flag, short] if short else [flag]), **kwargs)
    if action == 'report': result.add_argument('run_id', nargs='?')
    result.epilog = 'Commands: '+', '.join(a for a in COMMANDS if a) if not action else None
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    action = argv.pop(0) if argv and argv[0] in COMMANDS and argv[0] else ''
    p = parser(action)
    args = p.parse_args(argv)
    for field, variable in (('color','DOTS_COLOR'),('icons','DOTS_ICONS'),('progress','DOTS_PROGRESS')):
        if getattr(args, field, None): os.environ[variable] = getattr(args, field)
    info = detect()
    store = Receipts()
    if action in ('history','report'):
        rows = store.rows()
        if action == 'history':
            if args.limit < 0: p.error('--limit must be nonnegative')
            data = dict(schema=1, status='observed', runs=rows[:args.limit] if args.limit else rows,
                        cumulative=totals(row['totals'] for row in rows))
        else:
            data = next((r for r in rows if r['id'] == args.run_id), None) if args.run_id else (rows[0] if rows else None)
            if data is None:
                if args.run_id: raise ValueError('cleanup run not found')
                data = dict(schema=1, status='empty', runs=[])
            data = dict(data, cumulative=store.cumulative())
        render(data, args); return 0
    if action == 'groups':
        render(dict(schema=1, platform=info['platform'], catalog=[dict(id=k, label=v[0], risk=v[1],
                    description=v[2], supported=info['platform']=='termux', default=k in ORDINARY) for k,v in GROUPS.items()]), args)
        return 0
    groups = list(dict.fromkeys(args.group or ORDINARY))
    if args.include_checkpoints: groups = list(dict.fromkeys([*groups, *CHECKPOINTS]))
    groups = [g for g in GROUPS if g in groups and g not in args.exclude]
    if args.older_than is not None and (not 0 <= args.older_than <= 36500 or not set(groups) & set(CHECKPOINTS)):
        p.error('--older-than requires checkpoint groups and 0..36500 days')
    yes = getattr(args, 'yes', False)
    if yes and set(groups) & set(CHECKPOINTS): p.error('--yes is only allowed for ordinary groups')
    tty = all(s.isatty() for s in (sys.stdin, sys.stdout, sys.stderr))
    if not action and yes and not tty: p.error('unattended deletion requires explicit run --yes')
    preview = action == 'scan' or args.dry_run or (not action and (args.json or not tty))
    if not preview and not yes and (not tty or args.json): p.error('noninteractive run requires --yes; use scan for inspection')
    if info['platform'] != 'termux':
        render(dict(schema=1, platform=info['platform'], status='unsupported', issues=[dict(reason='Cleanup rules are not implemented for this platform.')]), args)
        return 3
    from config_values import value
    age = args.older_than if args.older_than is not None else value('apps.cleanup.checkpoint_min_age_days', 30)
    adapter = Termux()
    configure(tty and not args.json and not args.dry_run and not args.quiet)
    previous = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        with Progress('Scanning cleanup candidates') as progress:
            targets, issues = adapter.candidates(groups, age, progress.update)
        if preview:
            data = dict(schema=1, platform='termux', status='planned', selected_groups=groups,
                        candidates=[public(t) for t in targets], issues=issues, available_after=available(adapter.boundary))
            render(data, args); return 1 if issues else 0
        with Progress('Cleaning approved groups') as progress:
            data = run(adapter, targets, groups, issues, store,
                       (lambda *_: 'delete') if yes else confirm, progress.update)
        render(data, args)
        return 130 if data['status']=='stopped' else 1 if data['status']=='partial' else 0
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('cleanup: interrupted; inspect cleanup history for any recorded removals', file=sys.stderr); sys.exit(130)
    except (ValueError, OSError) as error:
        from files.catalog import Presentation
        ui = Presentation(sys.stderr); ui.detail('Cleanup', str(error), '91'); sys.exit(1)
