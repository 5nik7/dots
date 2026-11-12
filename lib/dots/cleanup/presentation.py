"""Dots-owned human views; machine records bypass this module's renderer."""
import os
import shutil
import sys

from files.catalog import Presentation
from interaction import Selector, SelectionEnded
from progress import permanent_output
from .core import public
from .receipts import totals
from .termux import GROUPS


def size(value):
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if abs(value) < 1024 or unit == 'TiB':
            return (str(int(value)) if unit == 'B' else f'{value:.2f}')+' '+unit
        value /= 1024


def group_view(ui, group, rows, details=False):
    label, risk, consequence = GROUPS[group]
    summary = totals(rows)
    ui.heading(label)
    ui.detail('Group', group)
    ui.detail('Risk', risk, '93' if risk != 'low' else '94')
    ui.detail('Size', size(summary['allocated_bytes']))
    ui.detail('Files', str(summary['files']))
    ui.detail('Effect', consequence)
    if details:
        for row in rows:
            ui.resource_detail('Target', row['path'])


def render(data, args, stream=None):
    if args.json and stream is None:
        import json
        print(json.dumps(data, ensure_ascii=True)); return
    ui = Presentation(stream)
    if args.quiet and stream is None:
        ui = Presentation(sys.stderr)
        for issue in data.get('issues', []): ui.detail('Cleanup', issue['reason'], '93')
        for row in data.get('groups', []):
            if row.get('reason') and row['status'] != 'skipped': ui.detail('Cleanup', row['reason'], '93')
            for item in row.get('targets', []):
                if item.get('reason'): ui.detail('Cleanup', item['reason'], '93')
                if item.get('uncertainty'): ui.detail('Uncertain', item['uncertainty'], '93')
        return
    ui.heading('Cleanup')
    if data.get('platform'): ui.detail('Platform', data['platform'])
    if data.get('status'): ui.detail('Result', data['status'], '93' if data['status'] in ('partial','incomplete','stopped') else None)
    if 'candidates' in data:
        if not data['candidates']: ui.emit('  No eligible cleanup files.')
        for group in data['selected_groups']:
            rows = [r for r in data['candidates'] if r['group'] == group]
            if rows:
                ui.emit(); group_view(ui, group, rows, args.verbose)
        ui.emit('\n  No changes made.')
    if 'catalog' in data:
        for row in data['catalog']:
            ui.emit(); ui.detail('Group', row['id']); ui.detail('Risk', row['risk'])
            ui.detail('Scope', row['description']); ui.detail('Support', 'available' if row['supported'] else 'not implemented')
    for row in data.get('runs', []):
        ui.emit(); ui.detail('Run', row['id']); ui.detail('Started', row['started'])
        ui.detail('Result', row['status']); ui.detail('Removed', size(row['totals']['allocated_bytes']))
    if 'runs' in data and not data['runs']: ui.emit('  No recorded cleanup runs.')
    for row in data.get('groups', []):
        ui.emit(); ui.detail('Group', row['group']); ui.detail('Result', row['status'])
        if row.get('reason'): ui.detail('Reason', row['reason'], '93')
        for item in row.get('targets', []):
            if args.verbose or item['status'] != 'completed':
                ui.resource_detail('Target', item['path']); ui.detail('Result', item['status'])
            if item.get('reason'): ui.detail('Reason', item['reason'], '93')
            if item.get('uncertainty'): ui.detail('Uncertain', item['uncertainty'], '93')
    for issue in data.get('issues', []):
        ui.detail('Skipped', issue['reason'], '93')
        if args.verbose and issue.get('path'): ui.resource_detail('Target', issue['path'])
    if data.get('totals') is not None:
        ui.emit(); ui.detail('Removed', size(data['totals']['allocated_bytes']), '92')
        ui.detail('Files', str(data['totals']['files']))
        ui.detail('Folders', str(data['totals']['directories']))
        ui.detail('Links', str(data['totals']['symlinks']))
    if data.get('cumulative') is not None: ui.detail('Combined', size(data['cumulative']['allocated_bytes']), '96')
    if 'available_after' in data: ui.detail('Available', size(data['available_after']))
    if 'available_change' in data: ui.detail('Disk change', size(data['available_change']))
    if 'duration_seconds' in data: ui.detail('Duration', str(data['duration_seconds'])+' s')
    if data.get('id'): ui.detail('Run', data['id'])
    if data.get('uncertainty'): ui.detail('Uncertain', data['uncertainty'], '93')


def confirm(group, targets):
    with permanent_output():
        ui = Presentation(sys.stderr)
        ui.emit(); group_view(ui, group, [public(t) for t in targets], True)
        ui.detail('Deletion', 'Permanent; no retained copy or undo', '93')
        if shutil.which('gum') and shutil.which('bash') and os.environ.get('TERM', 'dumb') != 'dumb':
            try:
                return Selector('gum', sys.stderr).pick('choose', 'Clean this group?', ['Skip','Delete','Stop'], 'Skip').lower()
            except SelectionEnded as error:
                if error.status == 130: raise KeyboardInterrupt from None
                raise ValueError('confirmation failed; no approval received') from None
        while True:
            print('Delete / Skip / Stop [Skip]: ', end='', file=sys.stderr, flush=True)
            value = sys.stdin.readline()
            if not value: return 'stop'
            answer = value.strip().lower()
            if answer in ('', 'n', 'no', 'skip'): return 'skip'
            if answer in ('y', 'yes', 'delete'): return 'delete'
            if answer in ('s', 'stop', '\x1b'): return 'stop'
            print('Enter yes, no, or stop.', file=sys.stderr)
