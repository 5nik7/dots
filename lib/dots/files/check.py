#!/usr/bin/env python3
"""Review absent sources and transactionally prune catalog metadata only."""
import argparse
import copy
import json
from pathlib import Path
import stat
import sys

from catalog import Catalog, PLATFORMS, Presentation, platform
from events import OperationOutput
from manage import Manager
from transactions import digest, parents_safe
from interaction import gum_confirm
from progress import Progress, configure


def source_state(path):
    """Only ENOENT is absence; permission and ancestor errors must propagate."""
    path = Path(path)
    parents_safe(path)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return 'absent'
    if stat.S_ISLNK(mode):
        try:
            path.stat()
        except FileNotFoundError:
            return 'broken-source-link'
    return 'present'


class Check:
    def __init__(self, args):
        self.args = args
        self.manager = Manager()
        self.catalog = Catalog(self.manager.root, args.platform)
        self.guards = {}
        self.documents = {}
        self.items = []

    def guard(self, path):
        path = str(path)
        parents_safe(path)
        self.guards[path] = digest(path)

    def inspect(self):
        self.guard(self.manager.root / '.dots/sources.json')
        self.catalog = Catalog(self.manager.root, self.args.platform)
        if self.args.repo and not any(s['id'] == self.args.repo for s in self.catalog.sources):
            raise ValueError('unknown repository: ' + self.args.repo)
        for owner in self.catalog.sources:
            if owner['status'] != 'excluded':
                self.guard(Path(owner['root']) / '.dots/files.json')
            if owner['status'] == 'available':
                path = Path(owner['root']) / '.dots/files.json'
                self.documents[owner['id']] = (str(path), self.catalog.manifest(owner))
        rows = self.catalog.records()
        rows = [r for r in rows if (self.args.all_platforms or r['applicable']) and all(
            getattr(self.args, option) is None or r[field] == getattr(self.args, option)
            for option, field in (('repo', 'repository'), ('app', 'app'),
                                  ('category', 'category'), ('status', 'status')))]
        rows.sort(key=lambda r: (str(r.get(self.args.sort, '')), r['id']))
        with Progress('Checking file sources') as progress:
            for index, row in enumerate(rows):
                state = source_state(row['source'])
                self.items.append(dict(row, source_state=state, eligible=state == 'absent',
                                       outcome='candidate' if state == 'absent' else 'kept',
                                       reason={'absent': 'Source path is absent',
                                               'present': 'Source exists',
                                               'broken-source-link': 'Broken source symlink; repair or review manually'}[state]))
                progress.update('Checking file sources', index + 1, len(rows))
        self.verify_metadata()
        return self.items

    def verify_metadata(self):
        for path, expected in self.guards.items():
            parents_safe(path)
            if digest(path) != expected:
                raise ValueError('changed after preview: ' + path)

    def plan(self, selected):
        selected = set(selected)
        eligible = {r['id'] for r in self.items if r['eligible']}
        if not selected <= eligible:
            raise ValueError('selection contains an ineligible resource')
        self.verify_metadata()
        guards = dict(self.guards)
        documents = {}
        for row in self.items:
            if row['id'] not in selected:
                continue
            if source_state(row['source']) != 'absent':
                raise ValueError('source changed after preview: ' + row['source'])
            guards[row['source']] = None
            path, original = self.documents[row['repository']]
            if path not in documents:
                documents[path] = copy.deepcopy(original)
            documents[path]['resources'] = [r for r in documents[path]['resources']
                                            if row['repository'] + ':' + r['id'] not in selected]
        operations = [dict(path=p, data=doc) for p, doc in sorted(documents.items())]
        for operation in operations:
            path = Path(operation['path'])
            state = self.manager.store.state
            if path.is_relative_to(state) or state.is_relative_to(path):
                raise ValueError('catalog overlaps the state store')
        return operations, guards, sorted(documents)

    def apply(self, selected):
        operations, guards, catalogs = self.plan(selected)
        with Progress('Updating file catalogs'):
            return self.manager.store.apply('check', operations, guards, catalogs=catalogs)


def confirm(question, action='Apply'):
    approved = gum_confirm(question, action, cancel='Skip' if action == 'Remove entry' else 'Cancel')
    if approved is not None:
        return approved
    ui = Presentation(sys.stderr)
    ui.emit(ui.paint(question + ' [y/N] ', '94'))
    answer = sys.stdin.readline()
    if not answer:
        raise KeyboardInterrupt
    return answer.strip().lower() in ('y', 'yes')


def show_item(ui, row):
    ui.emit()
    ui.detail('Resource', row['id'], '1;94')
    ui.detail('Status', row['reason'], '93')
    ui.resource_detail('Source', row['source'])
    ui.resource_detail('Target', row['target'])
    ui.detail('Action', 'Remove catalog entry only' if row['eligible'] else 'Keep catalog entry')


def summary(ui, result):
    counts = result['counts']
    for label in ('checked', 'eligible', 'selected', 'removed', 'skipped'):
        ui.detail(label.title(), counts[label], '96')
    if result.get('transaction', {}).get('id'):
        identity = result['transaction']['id']
        ui.detail('Transaction', identity)
        ui.detail('Undo', 'dots files undo ' + identity)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('-v', '--verbose', action='store_true')
    for flag in ('yes', 'dry-run', 'json', 'all-platforms'):
        p.add_argument('--' + flag, action='store_true')
    for flag in ('repo', 'app', 'category', 'status'):
        p.add_argument('--' + flag)
    p.add_argument('--platform', choices=sorted(PLATFORMS), default=platform())
    p.add_argument('--sort', choices=['id', 'app', 'repository', 'source', 'status'], default='id')
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.json and not (args.yes or args.dry_run):
        p.error('--json requires --dry-run or --yes')
    configure(not args.json and not args.dry_run)
    check = Check(args)
    output = OperationOutput.for_args(args)
    check.manager.store.observer = output
    with Progress('Inspecting file catalog'):
        items = check.inspect()
    candidates = [r for r in items if r['eligible']]
    sources = [s for s in check.catalog.sources if not args.repo or s['id'] == args.repo]
    result = dict(schema=1, action='check', platform=args.platform, dry_run=args.dry_run,
                  status='preview' if args.dry_run else 'unchanged', items=items, sources=sources,
                  counts=dict(checked=len(items), eligible=len(candidates), selected=0, removed=0, skipped=0))
    ui = Presentation()
    if not args.json:
        ui.heading('Check tracked files')
        for source in sources:
            if source['status'] != 'available':
                ui.repository_detail('Repository', source['root'], source['id'] + ': ' + source['status'], '93')
        for row in items:
            if row['source_state'] == 'broken-source-link':
                show_item(ui, row)
    selected = []
    if args.dry_run:
        check.plan([row['id'] for row in candidates])
        for row in candidates:
            row['outcome'] = 'would-remove'
            if not args.json:
                show_item(ui, row)
    elif candidates:
        if not args.yes and not all(s.isatty() for s in (sys.stdin, sys.stdout, sys.stderr)):
            p.error('use --dry-run to inspect or --yes to apply without terminal input and output')
        for row in candidates:
            if not args.json and not args.yes:
                show_item(ui, row)
            if args.yes or confirm('Remove this catalog entry?', 'Remove entry'):
                selected.append(row['id'])
                row['outcome'] = 'selected'
            else:
                row['outcome'] = 'skipped'
        result['counts']['selected'] = len(selected)
        if selected:
            # Validate the selected plan before offering final approval.
            check.plan(selected)
            if not args.json:
                ui.heading('Selected catalog removals')
                for row in candidates:
                    if row['id'] in selected:
                        show_item(ui, row)
            if args.yes or confirm('Apply these catalog removals?'):
                result['transaction'] = check.apply(selected)
                result['status'] = 'complete'
                result['counts']['removed'] = len(selected)
                for row in candidates:
                    if row['id'] in selected:
                        row['outcome'] = 'removed'
            else:
                result['status'] = 'cancelled'
                for row in candidates:
                    if row['id'] in selected:
                        row['outcome'] = 'cancelled'
        result['counts']['skipped'] = len(candidates) - result['counts']['removed']
    for row in items:
        outcome = row.get('outcome', '')
        if args.dry_run or outcome in ('skipped', 'removed') or not row['eligible']:
            output('Would remove catalog entry' if outcome == 'would-remove' else 'Removed catalog entry' if outcome == 'removed' else 'Skipped',
                   row.get('source'), reason=row['id'] + ': ' + row['reason'])
    if args.json:
        print(json.dumps(result, ensure_ascii=True))
    else:
        ui.heading('File check ' + result['status'])
        summary(ui, result)
        if not candidates:
            ui.detail('Result', 'No absent-source catalog entries match this check.')
        if args.dry_run:
            ui.emit('  Preview only; no changes made.')
        elif not result['counts']['removed']:
            ui.emit('  No changes made.')
        else:
            ui.detail('Result', 'Catalog entries removed; source and target objects were preserved.', '92')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('Interrupted; if apply started, inspect dots files history for recovery status.', '93'))
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots files check: ' + str(error), '91'))
        sys.exit(1)
