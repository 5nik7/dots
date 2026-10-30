#!/usr/bin/env python3
"""Journaled resource stashing and source/target mapping edits."""
from identities import validate_cli
import argparse
import copy
import json
import os
from pathlib import Path
import sys

from catalog import Catalog, ID, PLATFORMS, Presentation, platform, relative
from events import OperationOutput
from install import Installation
from manage import Manager
from transactions import digest, exists, parents_safe
from interaction import SelectionEnded, gum_confirm
from progress import Progress, configure


def target_spec(catalog, value):
    if value.startswith('${'):
        catalog.target(value)
        return value
    path = Path(os.path.abspath(os.path.expanduser(value)))
    roots = []
    for token in ('CONFIG', 'BIN', 'TERMUX', 'APPDATA', 'LOCALAPPDATA', 'NVIM_CONFIG', 'HOME'):
        base = catalog.target('${' + token + '}')
        if base and path.is_relative_to(Path(base)):
            roots.append((len(Path(base).parts), token, Path(base)))
    if not roots:
        raise ValueError('target must be within a supported HOME/XDG root or use a destination template')
    _, token, base = max(roots, key=lambda item: item[0])
    suffix = path.relative_to(base).as_posix()
    return '${' + token + '}' + ('/' + suffix if suffix != '.' else '')


def matching(path, source):
    return path.is_symlink() and path.resolve() == Path(source).resolve()


class MappingPlan:
    def __init__(self, backup=False, selected_platform=None):
        self.manager = Manager()
        self.root = self.manager.root
        self.install = Installation(self.root)
        self.catalog = self.manager.catalog
        self.backup = backup
        self.documents = {}
        self.paths = {}
        self.rows = []
        self.live = False
        self.install.guard(self.root / '.dots/sources.json')
        from profile_config import context
        selected = context(self.root, selected_platform) if selected_platform and self.catalog.registry else self.catalog.profile
        self.catalog = Catalog(self.root, selected_platform or self.catalog.platform, profile=selected)
        for path in self.catalog.input_paths():
            self.install.guard(path)
        for owner in self.catalog.sources:
            if owner['status'] == 'excluded':
                continue
            path = self.catalog.base_path(owner)
            self.install.guard(path)
            if owner['status'] == 'available':
                self.paths[owner['id']] = path
                self.documents[owner['id']] = copy.deepcopy(self.catalog.manifest(owner))
        self.original = copy.deepcopy(self.documents)
        self.original_rows = self.catalog.records()
        self.verify()

    def verify(self):
        for path, before in self.install.guards.items():
            parents_safe(path)
            if digest(path) != before:
                raise ValueError('changed after preview: ' + path)

    def record(self, identity):
        row = next((r for r in self.original_rows if r['id'] == identity), None)
        if row is None:
            raise ValueError(('resource needs a mapping in the selected profile: ' if self.catalog.registry and identity in self.catalog.registry.entries else 'resource not found: ') + identity)
        return row

    def raw(self, identity):
        owner, name = identity.split(':', 1)
        return next(r for r in self.documents[owner]['resources'] if r['id'] == name)

    def source(self, owner, rel, strategy, require=True):
        path = Path(next(s['root'] for s in self.catalog.sources if s['id'] == owner)) / relative(rel)
        parents_safe(path)
        for other in self.catalog.sources:
            child = Path(other['root'])
            root = Path(next(s['root'] for s in self.catalog.sources if s['id'] == owner))
            if child != root and child.is_relative_to(root) and path.is_relative_to(child):
                raise ValueError('select the source in its owning repository')
        self.install.guard(path)
        if require and (not path.exists() or path.is_symlink() or not (path.is_file() or path.is_dir())):
            raise ValueError('source must be an existing regular file or owned directory')
        if path.is_dir() and strategy != 'directory-link':
            raise ValueError('whole directories require --strategy directory-link')
        if require and not path.is_dir() and strategy == 'directory-link':
            raise ValueError('directory-link requires a directory source')
        return path

    def operation(self, path, **fields):
        path = str(path)
        if any(op['path'] == path for op in self.install.operations):
            raise ValueError('overlapping operation: ' + path)
        self.install.guard(path)
        self.install.operations.append(dict(path=path, **fields))

    def unlink(self, row, strict=False):
        if not row['target'] or not row['applicable']:
            return 'No applicable destination'
        target = Path(row['target'])
        source = Path(row['source'])
        if target == source or source.is_relative_to(target) or target.is_relative_to(source):
            raise ValueError('source and target overlap')
        self.install.guard(target)
        owned = self.install.entries.get(str(target))
        if owned and self.install.guards[str(target)] != owned['after']:
            raise ValueError('installer-owned target changed: ' + str(target))
        if matching(target, row['source']):
            for other in self.candidate():
                if other['id'] == row['id'] or not other['enabled'] or not other['applicable'] or not other['target']:
                    continue
                claimed = Path(other['target'])
                if claimed == target or claimed.is_relative_to(target) or (other['strategy'] == 'directory-link' and target.is_relative_to(claimed)):
                    raise ValueError('link is still claimed by another enabled resource: ' + other['id'])
            self.operation(target, delete=True)
            self.live = True
            # Keep the first-install baseline, including original backup pointers.
            if owned:
                owned['after'] = None
            return 'Remove matching link; keep repository source'
        if exists(target):
            if strict:
                raise ValueError('old target is not the recorded source link: ' + str(target))
            return 'Preserve unrelated target; disable future installation'
        return 'Target absent; disable future installation'

    def link(self, row, old=None):
        if not row['enabled']:
            raise ValueError('resource is stashed; restore it before live apply')
        if not row['applicable'] or not row['target']:
            raise ValueError('live apply requires an applicable mapped resource')
        if row['status'] in ('conflict', 'replaced'):
            raise ValueError('resource has conflicting or replaced target ownership: ' + row['id'])
        if row['strategy'] == 'copy':
            raise ValueError('live copy installation is not supported; use a link strategy')
        source = self.source(row['repository'], self.raw(row['id'])['source'], row['strategy'])
        target = Path(row['target'])
        if target == source or source.is_relative_to(target) or target.is_relative_to(source):
            raise ValueError('source and target overlap')
        self.install.guard(target)
        known_old = bool(old and old['target'] == row['target'] and matching(target, old['source']))
        owned = self.install.entries.get(str(target))
        if owned and self.install.guards[str(target)] != owned['after']:
            raise ValueError('installer-owned target changed: ' + str(target))
        if target.is_symlink() and not matching(target, source) and not known_old:
            raise ValueError('unrelated link is protected: ' + str(target))
        if exists(target) and not target.is_symlink() and not self.backup:
            raise ValueError('occupied target requires --backup: ' + str(target))
        from git_platform import plan as plan_git_platform
        start = len(self.install.items)
        plan_git_platform(self.install, row)
        self.rows.extend(self.install.items[start:])
        self.install.add(row['id'], target, link=source, directory=source.is_dir(), managed=known_old)
        if self.install.blocked:
            raise ValueError('installation plan contains conflicts')
        self.live = self.live or bool(self.install.operations)

    def retire_receipts(self, identity, keep=None):
        """Retire verified owned links left by metadata-only mapping edits."""
        for path, entry in list(self.install.entries.items()):
            if entry['id'] != identity or path == keep or any(op['path'] == path for op in self.install.operations):
                continue
            self.install.guard(path)
            if self.install.guards[path] != entry['after']:
                raise ValueError('installer-owned historical target changed: ' + path)
            if entry['after'] is None:
                continue
            target = Path(path)
            if not target.is_symlink():
                raise ValueError('historical destination is not a link: ' + path)
            for row in self.candidate():
                source = Path(row['source'])
                if source == target or source.is_relative_to(target):
                    raise ValueError('historical target overlaps a repository source')
                if row['id'] == identity or not row['enabled'] or not row['applicable'] or not row['target']:
                    continue
                claimed = Path(row['target'])
                if claimed == target or claimed.is_relative_to(target) or (row['strategy'] == 'directory-link' and target.is_relative_to(claimed)):
                    raise ValueError('historical target is claimed by another resource: ' + row['id'])
            self.operation(path, delete=True)
            entry['after'] = None
            self.live = True
            self.rows.append(dict(id=identity, status='unlink', target=path,
                                  reason='Remove verified historical installation link; retain original baseline'))

    def stash(self, identities, restore=False):
        ids = list(dict.fromkeys(identities))
        for identity in ids:
            self.record(identity)
            self.raw(identity)['enabled'] = restore
        if restore:
            for selected in PLATFORMS:
                if any(r['id'] in ids and r['applicable'] and r['status'] == 'conflict' for r in self.candidate(selected)):
                    raise ValueError('restored mapping conflicts on ' + selected)
        candidate = self.candidate()
        for identity in ids:
            before = self.record(identity)
            self.source(before['repository'], self.raw(identity)['source'], before['strategy'], require=restore)
            after = next(r for r in candidate if r['id'] == identity)
            if restore:
                self.link(after)
                reason = 'Enable and link resource'
            else:
                # Do not remove a link still claimed by another enabled resource.
                other = [r for r in candidate if r['enabled'] and r['applicable'] and r['target'] == before['target']]
                if other and before['target'] and matching(Path(before['target']), before['source']):
                    raise ValueError('target is still claimed by another enabled resource')
                reason = self.unlink(before)
                if before['strategy'] != 'copy':
                    self.retire_receipts(identity)
            self.rows.append(dict(id=identity, status='restore' if restore else 'stash',
                                  source=after['source'], target=after['target'], reason=reason))

    def candidate(self, selected_platform=None):
        selected = selected_platform or self.catalog.platform
        if self.catalog.registry and selected != self.catalog.platform:
            from registry import Registry
            candidate = Catalog(self.root, selected)
            candidate.registry = Registry(self.catalog.registry.update(self.documents), candidate.sources)
            return candidate.records()
        return Catalog(self.root, selected, self.documents, profile=self.catalog.profile).records()

    def edit(self, args):
        if args.new:
            if not args.repo or args.repo not in self.documents:
                raise ValueError('new mappings require an available --repo')
            if not all(getattr(args, key) for key in ('id', 'source', 'app', 'category', 'target')):
                raise ValueError('new mappings require --id, --source, --target, --app and --category')
            if any(r['id'] == args.id for r in self.documents[args.repo]['resources']):
                raise ValueError('resource ID exists; edit it without --new')
            owner = next(s for s in self.catalog.sources if s['id'] == args.repo)
            raw = dict(id=args.id, source=args.source, target=None, app=args.app, category=args.category,
                       strategy=args.strategy or 'link', platforms=args.platforms or (self.catalog.registry.entries.get(args.repo+':'+args.id, owner['platforms']) if self.catalog.registry else owner['platforms']))
            self.documents[args.repo]['resources'].append(raw)
            identity = args.repo + ':' + args.id
            before = None
        else:
            identity = args.values[0]
            before = self.record(identity)
            raw = self.raw(identity)
        owner_id = identity.split(':', 1)[0]
        if args.source:
            raw['source'] = relative(args.source).as_posix()
        if args.strategy:
            raw['strategy'] = args.strategy
        if args.target:
            selected_catalog = Catalog(self.root, args.platform or self.catalog.platform)
            spec = target_spec(selected_catalog, args.target)
            if args.platform and not self.catalog.registry:
                raw.setdefault('targets', {})[args.platform] = spec
            else:
                raw['target'] = spec
        if args.platforms: raw['platforms'] = args.platforms
        self.source(owner_id, raw['source'], raw['strategy'])
        # Validate effective claims for every platform affected by shared fields.
        for selected in PLATFORMS:
            row = next((r for r in self.candidate(selected) if r['id'] == identity), None)
            if row and row['enabled'] and row['applicable'] and row['status'] == 'conflict':
                raise ValueError('mapping conflicts on ' + selected + ': ' + identity)
        after = next(r for r in self.candidate() if r['id'] == identity)
        if args.apply:
            if self.catalog.profile['current'] != self.manager.catalog.profile['current'] or self.catalog.platform != self.manager.catalog.platform:
                raise ValueError('--apply cannot reconcile another platform')
            if not after['enabled']:
                raise ValueError('resource is stashed; restore it before --apply')
            if before and before['target'] != after['target']:
                self.unlink(before, strict=True)
            # Also reconcile known receipt-owned historical destinations for this ID.
            self.retire_receipts(identity, keep=after['target'])
            self.link(after, before)
        self.rows.append(dict(id=identity, status='edit-and-link' if args.apply else 'edit',
                              source=after['source'], target=after['target'],
                              profile=self.catalog.profile['current'], platforms=after['platforms'],
                              old_platforms=before['platforms'] if before else None,
                              old_source=before['source'] if before else None,
                              old_target=before['target'] if before else None,
                              reason='Reconcile live links' if args.apply else 'Metadata only; existing links remain unchanged'))

    def finish(self):
        documents = {owner: doc for owner, doc in self.documents.items() if doc != self.original[owner]}
        catalogs = []
        for operation in self.catalog.updates(documents):
            path = operation.pop('path')
            self.operation(path, **operation)
            catalogs.append(path)
        operations = self.install.operations
        for i, op in enumerate(operations):
            path = Path(op['path'])
            if path == self.install.state or path.is_relative_to(self.install.state) or self.install.state.is_relative_to(path):
                raise ValueError('operation overlaps state store')
            for other in operations[i+1:]:
                right = Path(other['path'])
                if path.is_relative_to(right) or right.is_relative_to(path):
                    raise ValueError('overlapping operation paths')
        self.verify()
        self.catalogs = [*self.catalog.lock_paths(), *catalogs]

    def apply(self, action):
        self.verify()
        return self.install.apply(action, catalogs=self.catalogs, write_receipt=self.live,
                                  retain=self.live or self.backup)


def terminal():
    return all(s.isatty() for s in (sys.stdin, sys.stdout, sys.stderr))


def pick(title, choices):
    if not terminal():
        raise ValueError('selection requires a terminal; supply explicit IDs/options')
    from picker import choice
    return choice(title, choices)


def prompt(label, default=None):
    if not terminal():
        raise ValueError('missing ' + label + '; supply explicit options without a terminal')
    ui = Presentation()
    ui.detail(label, default or 'required')
    value = input('Value (Enter keeps displayed value): ').strip()
    ui.emit()
    return value or default


def arguments(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('--pick', action='store_true')
    p.add_argument('action', choices=['stash', 'edit'])
    p.add_argument('values', nargs='*')
    for flag in ('restore', 'new', 'apply', 'yes', 'dry-run', 'json'):
        p.add_argument('--' + flag, action='store_true')
    for flag in ('repo', 'id', 'source', 'target', 'app', 'category'):
        p.add_argument('--' + flag)
    p.add_argument('--strategy', choices=['link', 'directory-link', 'copy'])
    p.add_argument('--platform', choices=sorted(PLATFORMS))
    p.add_argument('--platforms', nargs='+', choices=sorted(PLATFORMS))
    group = p.add_mutually_exclusive_group()
    group.add_argument('--backup', action='store_true', default=None)
    group.add_argument('--no-backup', dest='backup', action='store_false')
    args = p.parse_args(argv)
    validate_cli(args, p)
    if args.json and not (args.yes or args.dry_run):
        p.error('--json requires --yes or --dry-run')
    if args.action == 'stash' and any((args.new, args.apply, args.repo, args.id, args.source, args.target, args.app, args.category, args.strategy, args.platform, args.platforms)):
        p.error('mapping options require edit')
    if args.action == 'edit':
        if args.restore or len(args.values) > 1 or (args.new and args.values):
            p.error('edit takes one resource or --new; --restore belongs to stash')
        if not args.new and any((args.repo, args.id, args.app, args.category)):
            p.error('--repo/--id/--app/--category require --new')
    return p, args


def render(doc, final=False):
    ui = Presentation()
    ui.heading('Files ' + doc['action'] + ' — ' + doc['status'])
    ui.detail('Resources', len({row['id'] for row in doc['items']}), '96')
    if not final:
        for row in doc['items']:
            ui.emit()
            ui.detail('Resource', row['id'], '1;94')
            if 'profile' in row: ui.detail('Profile', row['profile'])
            if row.get('old_platforms') and row['old_platforms'] != row.get('platforms'): ui.detail('Old platforms', ', '.join(row['old_platforms']))
            if 'platforms' in row: ui.detail('Platforms', ', '.join(row['platforms']))
            for key, label in (('old_source','Old source'), ('old_target','Old target'), ('source','Source'), ('target','Target')):
                if row.get(key):
                    ui.resource_detail(label, row[key])
            ui.detail('Action', row['reason'], '93')
        ui.detail('Recovery', 'Live changes retain installation baselines; occupied replacements require backup approval.')
    if doc.get('transaction'):
        ui.detail('Transaction', doc['transaction'])
        ui.detail('Undo', 'dots files undo ' + doc['transaction'])
    if doc['status'] in ('preview', 'cancelled', 'unchanged'):
        ui.emit('  No changes made.')


def main(argv=None):
    p, args = arguments(argv)
    from interaction import selection_requested as requested
    picking = requested(p, args, args.values)
    if args.pick and args.dry_run and args.action == 'edit' and not any((args.source, args.target, args.strategy, args.platforms)):
        p.error('--pick --dry-run edit requires explicit --source, --target, --strategy or --platforms')
    configure(not args.json and not args.dry_run)
    with Progress('Loading file mappings'):
        plan = MappingPlan(args.backup if args.backup is not None else Manager().backup_default(), args.platform)
    output = OperationOutput.for_args(args)
    plan.install.store.observer = output
    interactive = not (args.json or args.yes or args.dry_run)
    if picking:
        from picker import select
        rows = plan.original_rows
        if args.action == 'stash':
            rows = [r for r in rows if r['enabled'] != args.restore]
        selected = select(rows, 'restore' if args.restore else args.action,
                          multi=args.action == 'stash', new=args.action == 'edit' and interactive and bool(plan.documents),
                          owners=plan.catalog.sources)
        if not selected:
            return 0
        if selected[0]['id'] == '__new__':
            args.new = True
        else:
            args.values = [r['id'] for r in selected]
    if not args.values and not args.new:
        p.error('supply resource IDs or explicit --new options')
    if args.action == 'edit' and interactive:
        if args.new:
            if not args.repo:
                args.repo = pick('Owning repository', ['Cancel'] + list(plan.documents))
                if args.repo == 'Cancel': return 0
            for field in ('id', 'source', 'target', 'app', 'category'):
                if not getattr(args, field): setattr(args, field, prompt(field.title()))
            if not args.strategy:
                args.strategy = pick('Link strategy', ['link', 'directory-link', 'copy'])
        elif not any((args.source, args.target, args.strategy, args.platforms)):
            row = plan.raw(args.values[0])
            args.source = prompt('Source', row['source'])
            args.target = prompt('Target', row.get('targets', {}).get(args.platform, row.get('target')) if args.platform else row.get('target'))
            args.strategy = pick('Link strategy', [row['strategy']] + [s for s in ('link', 'directory-link', 'copy') if s != row['strategy']])
    with Progress('Planning file mappings'):
        if args.action == 'stash':
            plan.stash(args.values, args.restore)
        else:
            plan.edit(args)
        plan.finish()
    output.plan(plan.rows, args.dry_run)
    doc = dict(schema=1, action='restore' if args.restore else args.action, status='preview', dry_run=args.dry_run, items=plan.rows)
    if args.dry_run:
        print(json.dumps(doc, ensure_ascii=True)) if args.json else render(doc)
        return 0
    if not args.json:
        render(doc)
    if not plan.install.operations:
        doc['status'] = 'unchanged'
        for row in plan.rows:
            output('Unchanged', row.get('target') or row.get('source'),
                   reason=row['id'] + ': mapping and live state already match')
    else:
        if not args.yes:
            if not terminal(): p.error('use --yes or --dry-run without terminal input/output')
            approved = gum_confirm('Apply these file mapping changes?')
            if approved is None:
                approved = prompt('Apply these changes? [y/N]', 'n').lower() in ('y', 'yes')
            if not approved:
                doc['status'] = 'cancelled'
                render(doc, True)
                return 0
        with Progress('Applying file mappings'):
            result = plan.apply(doc['action'])
        doc.update(status=result['status'], transaction=result.get('id'))
    print(json.dumps(doc, ensure_ascii=True)) if args.json else render(doc, True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('Interrupted; if apply started, inspect dots files history for recovery status.', '93'))
        sys.exit(130)
    except SelectionEnded as end:
        sys.exit(end.status)
    except (OSError, ValueError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots files: ' + str(error), '91'))
        sys.exit(1)
