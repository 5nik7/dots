#!/usr/bin/env python3
"""Repair catalog destinations using verified ownership and retained recovery."""
import argparse
from collections import Counter
import copy
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
import sys

from catalog import Catalog, Presentation, platform
from events import OperationOutput
from file_platform import check_object
from identities import canonical, validate_cli
from install import Installation
from transactions import digest, parents_safe
from interaction import SelectionEnded, gum_confirm
from progress import Progress, configure


LINK_ACTIONS = {'add', 'link', 'install', 'edit', 'restore', 'repair'}
REPAIR_ACTIONS = ('link', 'relink', 'replace-with-backup')


@dataclass(frozen=True)
class Finding:
    action: str
    reason: str
    issue: str = ''
    resolution: str = ''
    target_kind: str = ''
    current_link: str = ''
    observations: dict = field(default_factory=dict)


def signature(path):
    """Cheap inspection identity; content guards are captured before review."""
    parents_safe(path)
    check_object(path)
    try:
        value = path.lstat()
    except FileNotFoundError:
        return None
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns,
            os.readlink(path) if stat.S_ISLNK(value.st_mode) else None)


def object_kind(path):
    """Distinguish absence from errors without opening files or following links."""
    parents_safe(path)
    check_object(path)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return 'missing'
    if stat.S_ISLNK(mode):
        return 'link'
    if stat.S_ISREG(mode):
        return 'file'
    if stat.S_ISDIR(mode):
        return 'directory'
    return 'special'


def overlaps(left, right):
    return left.is_relative_to(right) or right.is_relative_to(left)


class Repair:
    def __init__(self, args):
        self.args = args
        self.root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[3]).resolve()
        self.install = Installation(self.root)
        self.receipt_paths = {}
        for path, entry in self.install.entries.items():
            if (not Path(path).is_absolute() or not isinstance(entry.get('id'), str)
                    or not isinstance(entry.get('index'), int) or entry['index'] < 0
                    or not re.fullmatch('[a-f0-9]{32}', entry.get('backup', ''))
                    or any(key not in entry or (entry[key] is not None and
                           (not isinstance(entry[key], str) or not re.fullmatch('[a-f0-9]{64}', entry[key])))
                           for key in ('before', 'after'))):
                raise ValueError('invalid installation receipt entry')
            key = os.path.normcase(os.path.abspath(path))
            if key in self.receipt_paths:
                raise ValueError('case-colliding installation receipt entries')
            self.receipt_paths[key] = path
        self.items = []
        self.rows = {}
        self.findings = {}
        self.choices = {}
        self.skipped = set()
        self.prepared = set()
        self.baseline_entries = copy.deepcopy(self.install.entries)
        self.history = None
        self.history_snapshot = None

    def verify(self):
        # Re-resolve composition as well: bundled profile catalogs can appear
        # without changing the top-level sources manifest.
        if Catalog(self.root, self.install.platform).sources != self.catalog.sources:
            raise ValueError('catalog composition changed after preview')
        if self.history_snapshot is not None and self.history_snapshot != self.history_identity(self.install.store.records()):
            raise ValueError('transaction history changed after preview')
        for identity in self.prepared:
            for path, observed in self.findings[identity].observations.items():
                if signature(Path(path)) != observed:
                    raise ValueError('changed after preview: ' + path)
        for path, expected in self.install.guards.items():
            parents_safe(path)
            if digest(path) != expected:
                raise ValueError('changed after preview: ' + path)

    @staticmethod
    def history_identity(records):
        return sorted((r['id'], r['status']) for r in records)

    def load_history(self):
        self.history = {}
        records = self.install.store.records()
        self.history_snapshot = self.history_identity(records)
        # Only completed operations are effective. The latest touching a path
        # supersedes earlier evidence, including undo and theme work. Corrupt
        # evidence is a shared metadata failure, never a per-row skip.
        for record in records:
            if record['status'] != 'complete':
                continue
            if not re.fullmatch('[a-f0-9]{32}', record['id']):
                raise ValueError('invalid transaction identity')
            journal = self.install.store.root / record['id'] / 'journal.json'
            self.install.guard(journal)
            record = self.install.store.load(record['id'])
            for op in record['operations']:
                if not Path(op['path']).is_absolute():
                    raise ValueError('transaction path must be absolute')
                key = os.path.normcase(op['path'])
                stamp = (record['created'], record['id'])
                previous = self.history.get(key)
                if previous is None or stamp > previous[0]:
                    self.history[key] = (stamp, record['action'], op['after'])

    def history_owner(self, target, current):
        if self.history is None:
            raise ValueError('link changed during inspection; retry the preview')
        evidence = self.history.get(os.path.normcase(str(target)))
        return bool(evidence and evidence[1] in LINK_ACTIONS and evidence[2] == current)

    def classify(self, row):
        def blocked(issue, reason):
            return Finding('unresolved', reason, issue)
        if not row['enabled']:
            return Finding('skipped', 'Resource is stashed; restore it explicitly.')
        if not row['applicable']:
            return Finding('skipped', 'Resource is inactive on this platform.')
        if row['status'] == 'replaced':
            return Finding('skipped', 'Another resource replaces this mapping.')
        if not row['target']:
            return Finding('skipped', 'No supported destination on this platform.')
        # Missing/disabled entries named by replaces are informational. Only
        # actual competing claims make this resource ambiguous.
        if row['status'] == 'conflict':
            return blocked('catalog-conflict', 'Multiple catalog resources claim this destination.')
        if row['strategy'] == 'copy':
            return blocked('mapping', 'Copy repair is unsupported; review the mapping explicitly.')

        source, target = Path(row['source']), Path(row['target'])
        if overlaps(target, self.install.state) or overlaps(source, target):
            return blocked('unsafe-path', 'Source, target or state paths overlap.')
        for owner in self.catalog.sources:
            root = Path(owner['root'])
            if overlaps(target, root):
                return blocked('unsafe-path', 'Destination overlaps a source repository.')
            if owner['id'] != row['repository'] and source.is_relative_to(root):
                own_root = next(Path(s['root']) for s in self.catalog.sources if s['id'] == row['repository'])
                if root.is_relative_to(own_root):
                    return blocked('mapping', 'Source belongs to a nested repository.')

        recorded = self.receipt_paths.get(os.path.normcase(str(target)), str(target))
        if recorded != str(target):
            return blocked('mapping', 'Destination spelling differs from its installation receipt; review the mapping.')
        owned = self.install.entries.get(recorded)
        if owned and canonical(owned['id']) != row['id']:
            issue = 'protected-theme' if owned['id'].startswith('theme:') else 'other-owner'
            return blocked(issue, 'Destination belongs to another installed resource: ' + owned['id'])
        target_kind = object_kind(target)
        observed_target = signature(target)
        if (observed_target is None) != (target_kind == 'missing'):
            raise ValueError('destination changed during inspection; retry the preview')
        current_link = os.readlink(target) if target_kind == 'link' else ''
        linked = Path(os.path.abspath(target.parent / current_link)) if current_link else None
        if linked is not None and (linked.is_relative_to(self.install.state) or '/dots/current/theme/' in linked.as_posix()):
            return Finding('unresolved', 'Generated-state link is protected; inspect dots theme files check.',
                           'protected-theme', target_kind=target_kind, current_link=current_link)
        source_kind = object_kind(source)
        if source_kind not in ('file', 'directory'):
            return blocked('source-unavailable', 'Source is missing, a symlink or unsupported; restore or review the source.')
        if (source_kind == 'directory') != (row['strategy'] == 'directory-link'):
            return blocked('mapping', 'Source type does not match the catalog link strategy.')
        if target_kind == 'special':
            return blocked('unsafe-path', 'Special destination object is preserved; review it manually.')
        observations = {str(target): observed_target, str(source): signature(source)}
        def finding(action, reason, issue='', resolution=''):
            return Finding(action, reason, issue, resolution, target_kind, current_link, observations)
        if target_kind in ('file', 'directory'):
            return finding('unresolved', 'Occupied destination is preserved until you approve backup and replacement.',
                           'occupied-target', 'replace-with-backup')
        if target_kind == 'link':
            try:
                target.stat()
            except FileNotFoundError:
                pass
            else:
                if target.resolve() == source.resolve():
                    return finding('unchanged', 'Link already points to the catalogued source.')
                return finding('unresolved', 'Working link points elsewhere; review before replacing it.',
                               'foreign-link', 'replace-with-backup')
            # Capture link identity before consulting historical ownership.
            self.install.guard(target)
            current = self.install.guards[str(target)]
            evidence = (self.history or {}).get(os.path.normcase(str(target)))
            if evidence and evidence[1].startswith('theme-') and evidence[2] == current:
                return finding('unresolved', 'Generated-theme ownership is protected; inspect dots theme files check.',
                               'protected-theme')
            owner_root = next(Path(s['root']) for s in self.catalog.sources if s['id'] == row['repository'])
            if not owned and not linked.is_relative_to(owner_root):
                return finding('unresolved', 'Historical link points outside its source repository; relocation requires explicit review.',
                               'historical-link', 'relink')
            proven = (owned['after'] == current) if owned else self.history_owner(target, current)
            if not proven:
                return finding('unresolved', 'Broken link has no current matching Dots ownership evidence.',
                               'receipt-drift' if owned else 'unverified-link', 'relink')
            return finding('relink', 'Relink verified broken destination to the current source.', resolution='relink')
        return finding('link', 'Create missing destination from the catalogued source.', resolution='link')

    def prepare(self, identity, *, inspecting=False):
        """Bind an available choice to its inspected objects before showing it."""
        finding = self.findings[identity]
        if not finding.resolution:
            raise ValueError('this issue has no permitted repair action')
        if not inspecting:
            self.verify()
        for path, observed in finding.observations.items():
            if signature(Path(path)) != observed:
                raise ValueError('changed after preview: ' + path)
        row = self.rows[identity]
        if (object_kind(Path(row['source'])) != ('directory' if row['strategy'] == 'directory-link' else 'file')
                or object_kind(Path(row['target'])) != finding.target_kind):
            raise ValueError('object type changed after preview; run dots files repair again')
        # Guard the destination before hashing a source or occupied directory.
        for path in (row['target'], row['source']):
            self.install.guard(path)
        for path, observed in finding.observations.items():
            if signature(Path(path)) != observed:
                raise ValueError('changed after preview: ' + path)
        if not inspecting:
            self.verify()
        self.prepared.add(identity)

    def select(self, identity, resolution):
        """Queue a validated action; this method never writes to disk."""
        if identity not in self.findings:
            raise ValueError('unknown repair selection')
        finding = self.findings[identity]
        if resolution is None:
            self.choices.pop(identity, None)
            self.skipped.add(identity)
        else:
            if not finding.resolution or resolution != finding.resolution:
                raise ValueError('repair resolution is unavailable')
            self.prepare(identity)
            self.choices[identity] = resolution
            self.skipped.discard(identity)
        self.build()

    def build(self):
        """Build only the chosen operations, preserving the captured baseline."""
        self.verify()
        self.install.operations = []
        self.install.items = []
        self.install.entries = copy.deepcopy(self.baseline_entries)
        self.items = []
        for identity, row in self.rows.items():
            finding = self.findings[identity]
            selected = self.choices.get(identity)
            action, reason = finding.action, finding.reason
            if selected:
                if identity not in self.prepared:
                    raise ValueError('repair choice has not been prepared')
                # Only automatic eligibility or an explicit helper choice can
                # reach this override. General installation rules are unchanged.
                self.install.add(identity, Path(row['target']), link=Path(row['source']),
                                 directory=row['strategy'] == 'directory-link', managed=True)
                action = selected
                if finding.action == 'unresolved':
                    reason = 'Explicitly selected; retain the current object for undo before linking the catalog source.'
            elif finding.action in REPAIR_ACTIONS:
                action, reason = 'unresolved', 'Repair skipped for this run.'
            outcome = 'would-' + action if selected else ('skipped' if identity in self.skipped else action)
            self.items.append(dict(row, repair_action=action, reason=reason, outcome=outcome))
        operations = self.install.operations
        for i, left in enumerate(operations):
            for right in operations[i+1:]:
                if overlaps(Path(left['path']), Path(right['path'])):
                    raise ValueError('overlapping repair operations')
        self.verify()

    def inspect(self):
        self.install.guard(self.root / '.dots/sources.json')
        self.catalog = Catalog(self.root, self.install.platform)
        if self.args.repo and not any(s['id'] == self.args.repo for s in self.catalog.sources):
            raise ValueError('unknown repository: ' + self.args.repo)
        for owner in self.catalog.sources:
            if owner['status'] != 'excluded':
                self.install.guard(Path(owner['root']) / '.dots/files.json')
        rows = self.catalog.records()
        ids = set(self.args.values)
        unknown = ids - {r['id'] for r in rows}
        if unknown:
            raise ValueError('unknown resource: ' + ', '.join(sorted(unknown)))
        rows = [r for r in rows if (not ids or r['id'] in ids) and (r['applicable'] or r['id'] in ids)
                and all(getattr(self.args, flag) is None or r[field] == getattr(self.args, flag)
                        for flag, field in (('repo', 'repository'), ('app', 'app'), ('category', 'category')))]
        if any(r['status'] == 'broken-link' for r in rows):
            self.load_history()
        with Progress('Inspecting managed files') as progress:
            for index, row in enumerate(sorted(rows, key=lambda r: r['id'])):
                identity = row['id']
                try:
                    finding = self.classify(row)
                except (OSError, ValueError, RuntimeError) as error:
                    finding = Finding('unresolved', str(error), 'inspection-error')
                self.rows[identity] = row
                self.findings[identity] = finding
                if finding.action in REPAIR_ACTIONS:
                    # The initial batch is verified once by build(), avoiding
                    # repeated hashing of every prior source during the scan.
                    self.prepare(identity, inspecting=True)
                    self.choices[identity] = finding.action
                progress.update('Inspecting managed files', index + 1, len(rows))
        self.build()
        return self.items

    def apply(self):
        self.verify()
        return self.install.apply('repair', retain=True)


def terminal():
    return all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr))


def confirm():
    approved = gum_confirm('Apply these file repairs?')
    if approved is not None:
        return approved
    ui = Presentation(sys.stderr)
    ui.emit('Apply these file repairs? [y/N] ')
    answer = sys.stdin.readline()
    if not answer:
        raise KeyboardInterrupt
    return answer.strip().lower() in ('y', 'yes')


def render(doc, verbose=False, final=False):
    ui = Presentation()
    ui.heading('File repair ' + doc['status'])
    if not final:
        for owner in doc['sources']:
            if owner['status'] != 'available':
                ui.repository_detail('Repository', owner['root'], owner['id'] + ': ' + owner['status'], '93')
        for row in doc['items']:
            action = row['repair_action']
            if action in ('unchanged', 'skipped') and not verbose:
                continue
            ui.emit()
            ui.detail('Resource', row['id'], '94')
            ui.detail('Action', row['outcome'].replace('-', ' ').capitalize(), '93' if action == 'unresolved' else '96')
            ui.resource_detail('Source', row['source'])
            ui.resource_detail('Target', row['target'], kind='symlink' if action in ('link', 'relink') else None)
            ui.detail('Reason', row['reason'])
    for label, count in doc['counts'].items():
        ui.detail(label.title(), count, '96')
    if doc.get('transaction'):
        identity = doc['transaction']['id']
        ui.detail('Transaction', identity)
        ui.detail('Undo', 'dots files undo ' + identity)
    if doc['dry_run']:
        ui.emit('  Preview only; no changes made.')
    elif final and not doc['counts']['repaired']:
        ui.emit('  No changes made.')
    if doc['counts']['unresolved']:
        ui.emit('  Unresolved entries were preserved for manual review.')
        if not final:
            ui.detail('Review', 'Run dots files repair in a terminal without --yes to review these issues.')
    elif not doc['counts']['eligible']:
        ui.emit('  No repairs needed in this scope.')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.set_defaults(action='repair')
    p.add_argument('values', nargs='*', metavar='RESOURCE')
    for flag in ('repo', 'app', 'category'):
        p.add_argument('--' + flag)
    for flag in ('yes', 'dry-run', 'json'):
        p.add_argument('--' + flag, action='store_true')
    p.add_argument('-v', '--verbose', action='store_true')
    return p


def document(repair):
    counts = Counter(r['repair_action'] for r in repair.items)
    return dict(schema=1, action='repair', platform=repair.install.platform, dry_run=repair.args.dry_run,
                status='preview', items=repair.items,
                sources=[s for s in repair.catalog.sources if not repair.args.repo or s['id'] == repair.args.repo],
                counts=dict(checked=len(repair.items), eligible=sum(counts[a] for a in REPAIR_ACTIONS), repaired=0,
                            unchanged=counts['unchanged'], skipped=counts['skipped'], unresolved=counts['unresolved']))


def cancel(doc):
    doc['status'] = 'cancelled'
    for row in doc['items']:
        if row['repair_action'] in REPAIR_ACTIONS:
            row['outcome'] = 'cancelled'
    render(doc, final=True)
    return 0


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    validate_cli(args, p)
    if args.json and not (args.yes or args.dry_run):
        p.error('--json requires --yes or --dry-run')
    configure(not args.json and not args.dry_run)
    repair = Repair(args)
    output = OperationOutput.for_args(args)
    repair.install.store.observer = output
    repair.inspect()
    doc = document(repair)
    if args.dry_run:
        print(json.dumps(doc, ensure_ascii=True)) if args.json else render(doc, args.verbose)
        return int(bool(doc['counts']['unresolved']))
    if not args.yes and terminal() and doc['counts']['unresolved']:
        from repair_picker import RepairHelper
        if not RepairHelper(repair).run():
            return cancel(document(repair))
        # The selected operations and guards are already prepared. Approval
        # must never cause a fresh scan or rebuild of this reviewed batch.
        doc = document(repair)
    eligible = doc['counts']['eligible']
    if eligible and not args.yes and not terminal():
        p.error('use --dry-run to inspect or --yes to apply without terminal input and output')
    if not args.json:
        render(doc, args.verbose)
    if eligible and not args.yes and not confirm():
        return cancel(doc)
    if eligible:
        doc['transaction'] = repair.apply()
        doc['counts']['repaired'] = eligible
        for row in doc['items']:
            if row['repair_action'] in REPAIR_ACTIONS:
                row['outcome'] = 'repaired'
    doc['status'] = ('partial' if eligible else 'unresolved') if doc['counts']['unresolved'] else ('complete' if eligible else 'unchanged')
    print(json.dumps(doc, ensure_ascii=True)) if args.json else render(doc, final=True)
    return int(bool(doc['counts']['unresolved']))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SelectionEnded as end:
        sys.exit(end.status)
    except (KeyboardInterrupt, EOFError):
        Presentation(sys.stderr).emit('Interrupted; inspect dots files history if apply started.')
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots files repair: ' + str(error), '91'))
        sys.exit(1)
