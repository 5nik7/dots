#!/usr/bin/env python3
"""Relink and prune the effective file mappings for the active profile."""
from collections import Counter
from dataclasses import replace
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from catalog import Catalog, Presentation, platform
from check import Check, confirm
from events import OperationOutput
from file_platform import open_nofollow
from identities import validate_cli
from interaction import SelectionEnded
from progress import configure, permanent_output, sequence
from repair import Repair, terminal
from transactions import digest


STRATEGIES = ('link', 'directory-link')
CHANGES = ('link', 'relink', 'prune')
DONE = dict(link='linked', relink='relinked', prune='pruned')


def equal_contents(left, right):
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(open_nofollow(left, flags), 'rb') as a, os.fdopen(open_nofollow(right, flags), 'rb') as b:
        if not all(stat.S_ISREG(os.fstat(stream.fileno()).st_mode) for stream in (a, b)):
            raise ValueError('file type changed during comparison')
        while True:
            chunk = a.read(1024 * 1024)
            if chunk != b.read(1024 * 1024):
                return False
            if not chunk:
                return True


class Relink(Repair):
    def classify(self, row, *, planned=(), planned_parents=()):
        finding = super().classify(row, planned=planned, planned_parents=planned_parents)
        if finding.issue != 'occupied-target' or finding.target_kind != 'file' or row['strategy'] != 'link':
            return finding
        source, target = self.endpoints[row['id']]
        edited = replace(finding, reason='File contents differ. Preserve the destination and review it with dots files repair.')
        if source.stat().st_size != target.stat().st_size:
            return edited
        source_digest, target_digest = digest(source), digest(target)
        # Store digests include permission bits. Equal contents with different
        # permissions can be linked once the original has a retained backup.
        if source_digest != target_digest:
            if stat.S_IMODE(source.stat().st_mode) == stat.S_IMODE(target.stat().st_mode) or not equal_contents(source, target):
                return edited
        for path, observed in ((source, source_digest), (target, target_digest)):
            if observed is None or self.install.guards.setdefault(str(path), observed) != observed:
                raise ValueError('source or destination changed during comparison: ' + str(path))
        return replace(finding, action='relink', resolution='relink',
                       reason='Contents are identical. Retain a backup and link the destination.')


def uninitialized(catalog):
    """Git can leave a deinitialized submodule's directory in place."""
    candidates = {}
    for owner in catalog.sources:
        if owner['status'] != 'available' or owner.get('virtual') or owner.get('bundled') or not catalog.applicable(owner['platforms']):
            continue
        root = Path(owner['root'])
        marker = root / '.git'
        if root != catalog.root and not (not marker.is_symlink() and (marker.is_dir() or marker.is_file())):
            candidates[root.relative_to(catalog.root)] = owner['id']
    modules = catalog.root / '.gitmodules'
    if not candidates or not modules.is_file():
        return set()
    if modules.is_symlink():
        raise ValueError('submodule registration must be a regular file')
    try:
        result = subprocess.run(['git', 'config', '--no-includes', '--null', '--file', str(modules),
                                 '--get-regexp', r'^submodule\..*\.path$'], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Without Git, preserve uncertain nested owners in a checkout declaring
        # submodules; the root and bundled profiles remain available.
        return set(candidates.values())
    if result.returncode not in (0, 1):
        raise ValueError('could not read submodule registrations')
    paths = {Path(os.fsdecode(record.split(b'\n', 1)[1])) for record in result.stdout.split(b'\0') if record}
    return {candidates[path] for path in paths if path in candidates}


def projected_catalog(catalog, operations):
    if not operations:
        return catalog
    profiles, manifests = {}, {}
    for op in operations:
        path = Path(op['path'])
        if path.name == 'profile.json':
            profiles[path] = op['data']
        else:
            from identities import canonical
            manifests[canonical(op['data']['repository'])] = op['data']
    return Catalog(catalog.root, catalog.platform, manifests=manifests, profile=catalog.profile, overrides=profiles)


class Maintenance:
    def __init__(self, args):
        self.args = args
        self.check = Check(args) if args.action in ('prune', 'sync') else None
        self.repair = Relink(args) if args.action in ('relink', 'sync') else None
        self.items = {}
        self.prunes = set()
        self.metadata = []
        self.guards = {}
        self.locks = []
        self.catalog = None
        self.unavailable = set()
        self.inputs = set()

    def masked(self, row):
        if row['enabled'] or not self.catalog.flat:
            return False
        owner, name = row['id'].split(':', 1)
        parent = self.catalog.parent_mappings.get(owner, {}).get(name)
        return parent is not None and self.catalog.effective[owner][name] == dict(parent, enabled=False)

    def inspect(self, choose=None):
        seed = self.check.catalog if self.check else Catalog(self.repair.root, self.repair.install.platform)
        starting_inputs = {str(path): digest(path) for path in seed.input_paths()}
        self.inputs = set(starting_inputs)
        if self.check:
            rows = self.check.inspect()
            self.catalog = self.check.catalog
            self.unavailable = uninitialized(self.catalog)
            for row in rows:
                reason = row['reason']
                if row['repository'] in self.unavailable:
                    operation, reason = 'skipped', 'Source repository is uninitialized.'
                elif self.masked(row):
                    operation, reason = 'skipped', 'Inherited declaration already disabled in this profile.'
                elif row['eligible']:
                    if choose is None or choose('prune', row):
                        self.prunes.add(row['id'])
                        operation = 'prune'
                    else:
                        operation, reason = 'skipped', 'Prune declined.'
                elif self.repair:
                    continue
                else:
                    operation = 'unchanged' if row['source_state'] == 'present' else 'skipped'
                self.add(row, operation, reason)
            self.metadata, self.guards, self.locks = self.check.plan(self.prunes)
        if self.repair:
            if self.catalog is None:
                self.catalog = Catalog(self.repair.root, self.repair.install.platform)
                self.unavailable = uninitialized(self.catalog)
            catalog = projected_catalog(self.catalog, self.metadata)
            def include(row):
                if row['id'] in self.items:
                    return False
                if row['repository'] in self.unavailable:
                    self.add(row, 'skipped', 'Source repository is uninitialized.')
                    return False
                if row['strategy'] not in STRATEGIES:
                    self.add(row, 'skipped', 'Copy mapping.')
                    return False
                return True
            def select(row, finding):
                return finding.action in ('link', 'relink') and (choose is None or choose(finding.action, dict(row, reason=finding.reason)))
            self.repair.inspect(catalog=catalog, include=include, select=select)
            self.catalog = self.repair.catalog
            for row in self.repair.items:
                skipped = row['id'] in self.repair.skipped
                self.add(row, 'skipped' if skipped else row['repair_action'], 'Relink declined.' if skipped else row['reason'])
            self.repair.install.merge_plan(self.metadata, self.guards, label='Prune profile mappings')
        current_inputs = self.repair.install.guards if self.repair else self.check.guards
        if (self.inputs != {str(path) for path in self.catalog.input_paths()} or
                any(current_inputs.get(path) != expected for path, expected in starting_inputs.items())):
            raise ValueError('catalog changed during inspection')
        return self.document('preview')

    def add(self, row, operation, reason):
        item = dict(row, operation=operation, reason=reason, outcome='would-' + operation if operation in CHANGES else operation)
        for field in ('repair_action', 'eligible'):
            item.pop(field, None)
        self.items[row['id']] = item

    def document(self, status, transaction=None):
        items = [self.items[k] for k in sorted(self.items)]
        amounts = Counter(r['operation'] for r in items)
        counts = dict(checked=len(items), eligible=sum(amounts[v] for v in CHANGES),
                      linked=0, relinked=0, pruned=0, unchanged=amounts['unchanged'],
                      skipped=amounts['skipped'], unresolved=amounts['unresolved'])
        if transaction:
            items = [dict(r, outcome=DONE[r['operation']]) if r['operation'] in CHANGES else r for r in items]
            counts.update({done: amounts[op] for op, done in DONE.items()})
        elif status == 'cancelled':
            items = [dict(r, outcome='cancelled') if r['operation'] in CHANGES else r for r in items]
        result = dict(schema=1, action=self.args.action, profile=self.catalog.profile['current'],
                      platform=self.catalog.platform, dry_run=self.args.dry_run, status=status, items=items, counts=counts)
        if transaction:
            result['transaction'] = transaction
        return result

    def apply(self):
        if self.prunes or self.repair and self.repair.choices:
            current = Catalog(self.catalog.root, self.catalog.platform)
            if (current.profile['current'] != self.catalog.profile['current'] or current.sources != self.catalog.sources
                    or {str(path) for path in current.input_paths()} != self.inputs or uninitialized(current) != self.unavailable):
                raise ValueError('profile or source repository availability changed after preview')
        if self.check:
            self.check.verify_metadata()
        transaction = None
        if self.repair:
            self.repair.verify()
            if self.repair.choices:
                transaction = self.repair.install.apply(self.args.action, catalogs=self.locks or self.catalog.lock_paths(), retain=True)
        if transaction is None and self.metadata:
            transaction = self.check.manager.store.apply(self.args.action, self.metadata, self.guards, retain=True, catalogs=self.locks)
        unresolved = any(r['operation'] == 'unresolved' for r in self.items.values())
        status = ('partial' if transaction else 'unresolved') if unresolved else ('complete' if transaction else 'unchanged')
        return self.document(status, transaction)


def parser():
    from help_adapters import HelpArgumentParser
    p = HelpArgumentParser(description=__doc__)
    p.add_argument('action', choices=['relink', 'prune', 'sync'])
    for name in ('repo', 'app', 'category'):
        p.add_argument('--' + name)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('-i', '--interactive', action='store_true')
    mode.add_argument('--yes', action='store_true')
    mode.add_argument('--dry-run', action='store_true')
    p.add_argument('--json', action='store_true')
    p.add_argument('-v', '--verbose', action='store_true')
    p.set_defaults(values=[], all_platforms=False, sort='id', status=None, platform=platform())
    return p


@permanent_output()
def render(result, verbose=False):
    ui = Presentation()
    ui.heading('Files ' + result['action'] + ' ' + result['status'])
    ui.detail('Profile', result['profile'])
    for row in result['items']:
        if not verbose and row['operation'] in ('unchanged', 'skipped'):
            continue
        ui.emit()
        ui.detail('Resource', row['id'], '94')
        ui.detail('Action', row['outcome'].replace('-', ' ').capitalize())
        ui.resource_detail('Source', row['source'])
        if row.get('target'):
            ui.resource_detail('Target', row['target'])
        ui.detail('Reason', row['reason'])
    counts = result['counts']
    ui.emit()
    summary = [str(counts['checked']) + ' checked']
    for name in ('unchanged', 'skipped', 'unresolved'):
        if counts[name]:
            summary.append(str(counts[name]) + ' ' + name)
    ui.detail('Summary', ', '.join(summary))
    if result['status'] == 'preview':
        planned = Counter(row['operation'] for row in result['items'])
        changes = [str(planned[action]) + ' to ' + action for action in CHANGES if planned[action]]
        ui.detail('Planned', ', '.join(changes) if changes else 'No eligible changes')
        if changes and result['dry_run']:
            ui.detail('Apply', 'Use --yes to apply or -i to choose individual changes.')
    elif result.get('transaction'):
        ui.detail('Applied', ', '.join(str(counts[name]) + ' ' + name for name in DONE.values() if counts[name]))
    if result.get('transaction'):
        ui.detail('Undo', 'dots files undo ' + result['transaction']['id'])


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    validate_cli(args, p)
    if args.interactive and (args.json or not terminal()):
        p.error('--interactive requires a terminal and human output')
    args.dry_run = not (args.yes or args.interactive)
    configure(not args.json and not args.dry_run)
    maintenance = Maintenance(args)
    observer = OperationOutput.for_args(args)
    if maintenance.repair:
        maintenance.repair.install.store.observer = observer
    if maintenance.check:
        maintenance.check.manager.store.observer = observer
    def choose(operation, row):
        render_item = Presentation(sys.stderr)
        with permanent_output():
            render_item.detail('Resource', row['id'])
            render_item.resource_detail('Source', row['source'])
            if row.get('target'):
                render_item.resource_detail('Target', row['target'])
            render_item.detail('Reason', row['reason'])
        return confirm(operation.capitalize() + ' this mapping?', operation.capitalize())
    with sequence('Files ' + args.action, 2) as phases:
        with phases.step('Inspect profile mappings'):
            result = maintenance.inspect(choose if args.interactive else None)
        if args.interactive and result['counts']['eligible']:
            render(result, args.verbose)
            if not confirm('Apply these file changes?'):
                phases.cancel()
                render(maintenance.document('cancelled'))
                return 0
        if not args.dry_run:
            with phases.step('Apply file changes'):
                result = maintenance.apply()
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            render(result, args.verbose)
    return int(bool(result['counts']['unresolved']))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SelectionEnded as error:
        sys.exit(error.status)
    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        Presentation(sys.stderr).emit('dots files: ' + str(error))
        sys.exit(1)
