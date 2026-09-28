#!/usr/bin/env python3
"""Interactive metadata browser over the existing guarded file-operation engine."""
import argparse
import os
from pathlib import Path
import sys

from catalog import Presentation
from manage import Manager, show
from transactions import digest, parents_safe
from interaction import Selector, SelectionEnded as EndBrowser


def planned_operation(identity, action, backup):
    """Retain the exact plan plus all catalog inputs governing its ownership."""
    root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[3]).resolve()
    composition = root / '.dots/sources.json'
    parents_safe(composition)
    metadata = {str(composition): digest(composition)}
    manager = Manager()
    if manager.catalog.platform == 'windows':
        raise ValueError('native Windows managed operations are not implemented')
    for owner in manager.catalog.sources:
        if owner['status'] == 'excluded':
            continue
        path = Path(owner['root']) / '.dots/files.json'
        parents_safe(path)
        metadata[str(path)] = digest(path)
    row = next((r for r in manager.catalog.records() if r['id'] == identity), None)
    if row:
        for key in ('source', 'target'):
            if row[key]:
                parents_safe(row[key])
                metadata[row[key]] = digest(row[key])
    args = argparse.Namespace(action=action, values=[identity], backup=backup)
    operations, guards, catalogs, views = manager.plan(args)
    for path, expected in metadata.items():
        if digest(path) != expected or (path in guards and guards[path] != expected):
            raise ValueError('input changed while preparing preview; reopen the resource')
    guards.update(metadata)
    return manager, operations, guards, catalogs, views


class Browser:
    def __init__(self, args, selector=None):
        self.args = args
        self.ui = Presentation()
        self.backup = Manager().backup_default()
        self.selector = selector

    def pick(self, header, choices, kind='choose'):
        if self.selector is None:
            self.selector = Selector()
        choice = self.selector.pick(kind, header, choices, choices[0] if kind == 'choose' else '')
        if choice not in choices:
            raise ValueError('selector returned an unknown choice')
        if choice == 'Exit':
            raise EndBrowser()
        return choice

    def catalog(self):
        manager = Manager()
        rows = manager.catalog.records()
        rows = [r for r in rows if r['applicable'] and all(
            getattr(self.args, field) is None or r[key] == getattr(self.args, field)
            for field, key in (('repo', 'repository'), ('app', 'app'),
                               ('category', 'category'), ('status', 'status')))]
        return manager, sorted(rows, key=lambda r: r['id'])

    def run(self):
        while True:
            manager, rows = self.catalog()
            self.ui.heading('Browse tracked configs')
            for source in manager.catalog.sources:
                if source['status'] != 'available':
                    self.ui.detail('Repository', source['id'] + ': ' + source['status'])
            if not rows:
                self.ui.emit('  No matching tracked configs. Use dots files list to inspect filters.')
                return
            labels = {}
            for row in rows:
                label = ' | '.join(self.ui.clean(x) for x in (
                    row['id'], row['app'], row['status'],
                    self.ui.path(row['source']), self.ui.path(row['target'])))
                labels[label] = row['id']
            selected = self.pick('Select a config to inspect', [*labels, 'Exit'], 'filter')
            if selected not in labels:
                raise ValueError('selector returned an unknown resource')
            self.resource(labels[selected])

    def resource(self, identity):
        while True:
            manager, rows = self.catalog()
            row = next((r for r in rows if r['id'] == identity), None)
            if row is None:
                self.ui.emit('  Resource no longer matches this view; returning to the list.')
                return
            self.ui.render('show', [row], manager.catalog.platform)
            self.ui.emit('  Stop managing keeps the repository source and preserves a usable config;')
            self.ui.emit('  absent targets remain absent. Review the plan before applying.')
            toggle = 'Retained backups: ' + ('on' if self.backup else 'off')
            choice = self.pick('Config action', ['Back to list', 'Link', 'Stop managing', toggle, 'Exit'])
            if choice == 'Back to list':
                return
            if choice == toggle:
                self.backup = not self.backup
                continue
            if choice not in ('Link', 'Stop managing'):
                raise ValueError('selector returned an unknown action')
            action = 'link' if choice == 'Link' else 'remove'
            try:
                manager, operations, guards, catalogs, views = planned_operation(identity, action, self.backup)
            except (OSError, ValueError, KeyError, TypeError) as error:
                self.ui.emit(self.ui.paint('Blocked: ' + str(error), '93'))
                self.pick('Operation blocked', ['Back', 'Exit'])
                continue
            show('File operation preview', views)
            self.ui.detail('Retained backups', 'enabled' if self.backup else 'disabled')
            self.ui.emit('  Preview only; no changes made.')
            if self.pick('Review operation', ['Back', 'Apply', 'Exit']) == 'Back':
                continue
            # Apply the approved objects, never a fresh --yes invocation.
            # Also check no-op plans, for which Store.apply needs no transaction.
            for path, expected in guards.items():
                parents_safe(path)
                if digest(path) != expected:
                    raise ValueError('changed after preview: ' + path)
            try:
                result = manager.store.apply(action, operations, guards, self.backup, catalogs)
            except (OSError, ValueError, KeyError, TypeError) as error:
                raise ValueError(str(error) + '; inspect dots files history for transaction/recovery status') from error
            self.ui.heading('File operation ' + result['status'])
            if result.get('id'):
                self.ui.detail('Transaction', result['id'])
                if self.backup:
                    self.ui.detail('Backup', result['id'])
            self.pick('Operation finished', ['Return to list', 'Exit'])
            return


def main():
    parser = argparse.ArgumentParser(description='Browse tracked configs and review managed operations.')
    parser.color = False
    for flag in ('repo', 'app', 'category', 'status'):
        parser.add_argument('--' + flag, help='Filter by ' + flag)
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('browser needs terminal input and output; use dots files list/show and link/remove for scripts')
    Browser(args).run()


if __name__ == '__main__':
    try:
        main()
    except EndBrowser as end:
        sys.exit(end.status)
    except KeyboardInterrupt:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('Interrupted; if Apply had started, inspect dots files history for recovery status.', '93'))
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots files browse: ' + str(error), '91'))
        sys.exit(1)
