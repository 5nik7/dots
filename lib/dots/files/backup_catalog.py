"""User backups composed into the existing file Store, never a second writer.

Plans are read-only. Payloads, catalog updates and their consumer operations are
committed together; Store's temporary recovery copies remain independent.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import uuid

from catalog import read_json
from file_platform import state_root, check_object, native_link_text, native_staging_suffix
from transactions import Store, digest, exists, parents_safe

ID = re.compile(r'[0-9a-f]{32}')


def absolute(value):
    value = os.fspath(value)
    if not value or '\0' in value:
        raise ValueError('paths must be nonempty and contain no NUL')
    return Path(os.path.abspath(os.path.expanduser(value)))


def physical(value, guards):
    """Pin linked ancestors, preserving the final object (including broken links)."""
    path = absolute(value)
    pending = list(path.parts[1:])
    current = Path(path.anchor)
    redirects = 0
    while pending:
        part = pending.pop(0)
        candidate = current / part
        check_object(candidate)
        if pending and candidate.is_symlink():
            redirects += 1
            if redirects > 40:
                raise ValueError('too many parent links: ' + str(path))
            before = digest(candidate)
            target = native_link_text(os.readlink(candidate))
            if digest(candidate) != before:
                raise ValueError('parent link changed during inspection')
            guards[str(candidate)] = before
            destination = absolute(candidate.parent / target)
            if not destination.is_dir():
                raise ValueError('parent link must resolve to a directory: ' + str(candidate))
            pending = list(destination.parts[1:]) + pending
            current = Path(destination.anchor)
        else:
            if pending and exists(candidate) and not candidate.is_dir():
                raise ValueError('parent is not a directory: ' + str(candidate))
            current = candidate
    return current


def disjoint(paths):
    paths = [absolute(p) for p in paths]
    for i, path in enumerate(paths):
        if path == Path(path.anchor):
            raise ValueError('filesystem roots cannot be replaced')
        for other in paths[:i]:
            if os.path.normcase(str(path)) == os.path.normcase(str(other)) or path in other.parents or other in path.parents:
                raise ValueError('overlapping paths: ' + str(path) + ' and ' + str(other))


def bounded_json(path, default):
    parents_safe(path)
    if not exists(path):
        return deepcopy(default)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('backup metadata must be a bounded regular file: ' + str(path))
    return read_json(path)


class BackupPlan:
    def __init__(self, state=None, directory=None, location='store', *, identity=None):
        self.state = absolute(state if state is not None else state_root())
        self.directory = absolute(directory if directory is not None else Path.home() / '.bakstore')
        if location not in ('store', 'adjacent'):
            raise ValueError('backup location must be store or adjacent')
        self.location = location
        self.index = self.state / 'bak/catalog.json'
        self.receipt = self.state / 'installation.json'
        self.guards = {}
        self.guard(self.index)
        self.document = bounded_json(self.index, {'schema': 1, 'entries': {}})
        if not isinstance(self.document, dict) or set(self.document) != {'schema', 'entries'} or self.document['schema'] != 1 or not isinstance(self.document['entries'], dict):
            raise ValueError('invalid backup catalog')
        for ident, entry in self.document['entries'].items():
            if not ID.fullmatch(ident) or not isinstance(entry, dict) or entry.get('id') != ident:
                raise ValueError('invalid backup identity')
            if not isinstance(entry.get('path'), str) or not Path(entry['path']).is_absolute():
                raise ValueError('invalid backup payload path')
            if entry.get('original') is not None and (not isinstance(entry['original'], str) or not Path(entry['original']).is_absolute()):
                raise ValueError('invalid backup original path')
            if not isinstance(entry.get('fingerprint'), str) or not re.fullmatch(r'[0-9a-f]{64}', entry['fingerprint']):
                raise ValueError('invalid backup fingerprint')
            if not isinstance(entry.get('created'), str) or datetime.fromisoformat(entry['created']).utcoffset() is None:
                raise ValueError('backup timestamps must include a timezone')
        if digest(self.index) != self.guards[str(self.index)]:
            raise ValueError('backup catalog changed during inspection')
        self.initial = deepcopy(self.document)
        self.identity = identity or uuid.uuid4().hex
        self.operations = []
        self.items = []

    def guard(self, path):
        path = Path(path)
        parents_safe(path)
        value = digest(path)
        key = str(path)
        if key in self.guards and self.guards[key] != value:
            raise ValueError('changed during preview: ' + key)
        self.guards[key] = value
        return value

    def path(self, value):
        return physical(value, self.guards)

    def protect_source(self, path):
        if path == Path(path.anchor):
            raise ValueError('filesystem roots cannot be backed up')
        if path == self.state or path in self.state.parents or self.state in path.parents:
            raise ValueError('backup/recovery metadata cannot be moved or backed up')
        if path == self.directory or path in self.directory.parents:
            raise ValueError('backup destination is inside the source')

    def add(self, operation):
        path = Path(operation['path'])
        if any(op['path'] == str(path) for op in self.operations):
            raise ValueError('duplicate operation target: ' + str(path))
        self.guard(path)
        self.operations.append(operation)

    def snapshot(self, value, *, move=False, origin='manual', original=None):
        path = self.path(value)
        self.protect_source(path)
        before = self.guard(path)
        if before is None:
            raise ValueError('backup source does not exist: ' + str(path))
        ident = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        filename = path.name + '.' + now.strftime('%Y%m%dT%H%M%S.%fZ') + '.bak' + native_staging_suffix(path)
        parent = path.parent if self.location == 'adjacent' else self.path(self.directory / ident)
        if self.location == 'store' and self.guard(parent) is not None:
            raise ValueError('backup container is occupied')
        payload = parent / filename
        # No directory collision or implicit overwrite, even with a frozen clock.
        if exists(payload):
            payload = parent / (path.name + '.' + now.strftime('%Y%m%dT%H%M%S.%fZ') + '-' + ident[:8] + '.bak' + native_staging_suffix(path))
        if exists(payload):
            raise ValueError('backup destination is occupied')
        self.add({'path': str(payload), 'source': str(path)})
        record = dict(id=ident, created=now.isoformat(), original=str(absolute(original or value)),
                      path=str(payload), fingerprint=before, origin=origin,
                      mode='move' if move else 'copy', transaction=self.identity,
                      kind='link' if path.is_symlink() else 'directory' if path.is_dir() else 'file')
        self.document['entries'][ident] = record
        if move:
            self.add({'path': str(path), 'delete': True})
        self.items.append(dict(record, action='move' if move else 'backup'))
        return record

    def create(self, values, *, copy=False):
        paths = [self.path(value) for value in values]
        disjoint(paths)
        for value in values:
            self.snapshot(value, move=not copy)

    def import_backup(self, values, *, original=None):
        if original is not None and len(values) != 1:
            raise ValueError('--original requires exactly one imported backup')
        paths = [self.path(value) for value in values]
        disjoint(paths)
        for path in paths:
            self.protect_source(path)
            if any(r['path'] == str(path) for r in self.document['entries'].values()):
                raise ValueError('backup is already cataloged: ' + str(path))
            before = self.guard(path)
            if before is None:
                raise ValueError('backup does not exist: ' + str(path))
            ident = uuid.uuid4().hex
            record = dict(id=ident, created=datetime.now(timezone.utc).isoformat(),
                          original=str(absolute(original)) if original else None,
                          path=str(path), fingerprint=before, origin='import', mode='registered',
                          transaction=self.identity,
                          kind='link' if path.is_symlink() else 'directory' if path.is_dir() else 'file')
            self.document['entries'][ident] = record
            self.items.append(dict(record, action='import'))

    def entry(self, ident):
        if not ID.fullmatch(ident) or ident not in self.document['entries']:
            raise ValueError('unknown backup ID: ' + str(ident))
        return self.document['entries'][ident]

    def installation(self):
        self.guard(self.receipt)
        receipt = bounded_json(self.receipt, {'schema': 1, 'entries': {}, 'transactions': []})
        if not isinstance(receipt.get('entries'), dict):
            raise ValueError('invalid installation receipt')
        return receipt

    def protected(self):
        return {entry['backup_id']: path for path, entry in self.installation()['entries'].items()
                if entry.get('backup_id')}

    def records(self):
        protected = self.protected()
        return [dict(entry, protected=entry['id'] in protected,
                     status='available' if exists(entry['path']) else 'missing')
                for entry in sorted(self.document['entries'].values(), key=lambda e: (e['created'], e['id']), reverse=True)]

    def verified_payload(self, entry):
        path = self.path(entry['path'])
        if self.guard(path) != entry['fingerprint']:
            raise ValueError('backup is missing or changed: ' + entry['id'])
        return path

    def restore(self, ident, *, destination=None, backup=True):
        entry = self.entry(ident)
        source = self.verified_payload(entry)
        destination = destination if destination is not None else entry.get('original')
        if destination is None:
            raise ValueError('original path is unknown; supply --to')
        target = self.path(destination)
        self.protect_source(target)
        disjoint((source, target))
        before = self.guard(target)
        receipt = self.installation()
        owned = receipt['entries'].get(str(target))
        if owned and owned.get('backup_id') == ident:
            # Also release ownership when someone already restored identical
            # baseline bytes by hand; this explicit restore reconciles it.
            del receipt['entries'][str(target)]
            receipt['transactions'].append(self.identity)
            self.add({'path': str(self.receipt), 'data': receipt})
        if before == entry['fingerprint']:
            self.items.append(dict(id=ident, action='unchanged', source=str(source), target=str(target)))
            return
        if before is not None and backup:
            self.snapshot(destination, origin='restore')
        self.add({'path': str(target), 'source': str(source)})
        self.items.append(dict(id=ident, action='restore', source=str(source), target=str(target), retained=True))

    def delete(self, identities):
        protected = self.protected()
        for ident in dict.fromkeys(identities):
            if ident in protected:
                raise ValueError('backup is required for uninstall: ' + ident)
            entry = self.entry(ident)
            parents_safe(entry['path'])
            path = self.path(entry['path'])
            before = self.guard(path)
            if before is not None and before != entry['fingerprint']:
                raise ValueError('backup is missing or changed: ' + ident)
            target = path
            parent = path.parent
            # Ownership comes from the creating journal, never a UUID-shaped
            # directory name alone. Old store entries need no schema migration.
            if parent.name == ident and entry.get('origin') != 'import':
                transaction = entry.get('transaction', '')
                if isinstance(transaction, str) and ID.fullmatch(transaction):
                    journal_path = self.state / 'files/transactions' / transaction / 'journal.json'
                    self.guard(journal_path)
                    journal = bounded_json(journal_path, {})
                    owned = any(p.get('path') == str(parent) and p.get('created') is True
                                for p in journal.get('created_parents', []))
                    if owned and parent.is_dir() and not parent.is_symlink():
                        self.guard(parent)
                        if all(member == path for member in parent.iterdir()):
                            # One directory operation makes container removal
                            # reversible; nested operations would overlap.
                            target = parent
            if exists(target):
                self.add({'path': str(target), 'delete': True})
            del self.document['entries'][ident]
            self.items.append(dict(entry, action='delete', removed_directory=str(target) if target != path else None))

    def prune(self, *, keep=None, older_than=None):
        if keep is None and older_than is None:
            raise ValueError('prune requires --keep COUNT or --older-than DAYS')
        if keep is not None and keep < 0 or older_than is not None and older_than < 0:
            raise ValueError('prune limits must be nonnegative')
        threshold = datetime.now(timezone.utc) - timedelta(days=older_than) if older_than is not None else None
        counts, selected = {}, []
        for row in self.records():
            key = row['original'] or row['id']
            counts[key] = counts.get(key, 0) + 1
            if row['protected'] or keep is not None and counts[key] <= keep:
                continue
            if threshold is not None and datetime.fromisoformat(row['created']) >= threshold:
                continue
            selected.append(row['id'])
        self.delete(selected)

    def finish(self):
        operations = list(self.operations)
        if self.document != self.initial:
            if len(json.dumps(self.document, ensure_ascii=True).encode()) > 4*1024*1024:
                raise ValueError('backup catalog would exceed 4 MiB; prune unneeded records first')
            operations.append(dict(path=str(self.index), data=self.document))
        return operations

    def report(self):
        return dict(schema=1, status='planned' if self.finish() else 'unchanged',
                    items=self.items, operations=[dict(path=op['path'],
                    action='remove' if op.get('delete') else 'link' if 'link' in op else 'write')
                    for op in self.finish()])

    def apply(self, action, *, observer=None):
        operations = self.finish()
        result = Store(self.state,observer=observer).apply(action, operations, self.guards, identity=self.identity)
        return dict(self.report(), status=result['status'], transaction=result.get('id'))
