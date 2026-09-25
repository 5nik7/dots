"""Journaled, bounded POSIX object replacement for dots files.

No automatic force, pruning, or live-root defaults in this engine. Callers supply
validated paths. Recovery payloads are independent of optional retained backups.
"""
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import uuid

from catalog import atomic_json, read_json


def exists(path):
    return os.path.lexists(path)


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def private_directory(path):
    """Create state directories durably without widening existing permissions."""
    path = Path(path)
    parents_safe(path / 'placeholder')
    missing = []
    for parent in (path, *path.parents):
        if parent.exists():
            break
        missing.append(parent)
    for parent in reversed(missing):
        parent.mkdir(mode=0o700)
        sync_dir(parent.parent)


def parents_safe(path):
    for parent in Path(path).parents:
        if parent.is_symlink():
            raise ValueError(f"symlinked parent requires manual review: {parent}")
        if exists(parent) and not parent.is_dir():
            raise ValueError(f"parent is not a directory: {parent}")


def digest(path):
    """Hash object identity/content, without following symlinks or special files."""
    path = Path(path)
    if not exists(path):
        return None
    h = hashlib.sha256()
    def visit(p, rel):
        st = p.lstat()
        h.update(os.fsencode(rel) + b'\0' + str(stat.S_IMODE(st.st_mode)).encode() + b'\0')
        if stat.S_ISLNK(st.st_mode):
            h.update(b'L' + os.fsencode(os.readlink(p)))
        elif stat.S_ISREG(st.st_mode):
            h.update(b'F')
            fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError('source type changed')
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
        elif stat.S_ISDIR(st.st_mode):
            h.update(b'D')
            for child in sorted(p.iterdir()):
                visit(child, rel + '/' + child.name)
        else:
            raise ValueError(f"unsupported special file: {p}")
        h.update(b'\0')
    visit(path, '.')
    return h.hexdigest()


def copy_object(source, dest):
    source, dest = Path(source), Path(dest)
    before = digest(source)
    if before is None:
        raise ValueError('copy source disappeared')
    if exists(dest):
        raise ValueError('copy destination already exists')
    if source.is_symlink():
        dest.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, dest, symlinks=True)
    else:
        shutil.copy2(source, dest, follow_symlinks=False)
    if digest(dest) != before or digest(source) != before:
        raise ValueError('copy verification failed or source changed')
    flush_tree(dest)


def flush_tree(path):
    if path.is_symlink():
        return
    if path.is_dir():
        for child in path.iterdir():
            flush_tree(child)
        sync_dir(path)
    else:
        with path.open('rb') as stream:
            os.fsync(stream.fileno())


def discard(path):
    if not exists(path):
        return
    if Path(path).is_dir() and not Path(path).is_symlink():
        shutil.rmtree(path)
    else:
        Path(path).unlink()


class Store:
    def __init__(self, state):
        self.state = Path(state)
        self.root = self.state / 'files' / 'transactions'
        self.backups = self.state / 'backups'

    def records(self):
        if not self.root.exists():
            return []
        return sorted((read_json(p) for p in self.root.glob('*/journal.json')), key=lambda row: row.get('created', row['id']))

    def load(self, identity):
        if not identity or any(c not in '0123456789abcdef' for c in identity) or len(identity) != 32:
            raise ValueError('invalid transaction or backup ID')
        return read_json(self.root / identity / 'journal.json')

    @contextlib.contextmanager
    def locked(self, catalogs=()):
        parents_safe(self.root / 'placeholder')
        private_directory(self.root)
        handles = []
        try:
            paths = [self.root.parent / '.lock'] + sorted(set(Path(p).with_suffix('.lock') for p in catalogs))
            for path in paths:
                parents_safe(path)
                fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
                handle = os.fdopen(fd, 'a')
                handles.append(handle)
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            for handle in reversed(handles):
                handle.close()

    def save(self, doc):
        atomic_json(self.root / doc['id'] / 'journal.json', doc)

    def apply(self, action, operations, guards, retain=False, catalogs=()):
        """Operations are {path, source|link|data|delete}; guards bind preview inputs."""
        if not operations:
            return {'schema': 1, 'status': 'unchanged', 'operations': []}
        with self.locked(catalogs):
            for record in self.records():
                if record['status'] in ('applying', 'rolling-back', 'recovery-required', 'preparing'):
                    raise ValueError('unfinished transaction: run dots files recover ' + record['id'])
            for path, expected in guards.items():
                parents_safe(path)
                if digest(path) != expected:
                    raise ValueError(f'changed after preview: {path}')
            identity = uuid.uuid4().hex
            directory = self.root / identity
            directory.mkdir(mode=0o700)
            sync_dir(self.root)
            doc = {'schema': 1, 'id': identity, 'action': action, 'status': 'preparing',
                   'created': datetime.now(timezone.utc).isoformat(), 'guards': guards,
                   'retain_backup': retain, 'catalogs': list(map(str, catalogs)), 'operations': [], 'created_parents': []}
            self.save(doc)
            try:
                for i, op in enumerate(operations):
                    path = Path(op['path'])
                    parents_safe(path)
                    before = digest(path)
                    if str(path) not in guards or guards[str(path)] != before:
                        raise ValueError('operation is missing a verified preview guard')
                    entry = {'path': str(path), 'before': before, 'after': None, 'phase': 'prepared',
                             'old': str(path.with_name(path.name + '.dots-' + identity)),
                             'temp': str(path.with_name(path.name + '.dots-new-' + identity))}
                    if exists(entry['old']) or exists(entry['temp']):
                        raise ValueError('transaction sibling already exists')
                    if before is not None:
                        copy_object(path, directory / f'{i}-before')
                        if path.is_symlink():
                            entry['before_link'] = os.readlink(path)
                        elif 'data' in op:
                            entry['before_data'] = read_json(path)
                    after = directory / f'{i}-after'
                    if 'source' in op:
                        copy_object(op['source'], after)
                    elif 'link' in op:
                        after.symlink_to(op['link'])
                    elif 'data' in op:
                        atomic_json(after, op['data'])
                        if path.exists():
                            os.chmod(after, stat.S_IMODE(path.stat().st_mode))
                    entry['after'] = digest(after)
                    doc['operations'].append(entry)
                    self.save(doc)
                # All copies and metadata are ready before the first live replacement.
                for path, expected in guards.items():
                    if digest(path) != expected:
                        raise ValueError(f'changed during preflight: {path}')
                doc['status'] = 'applying'
                self.save(doc)
                for i, entry in enumerate(doc['operations']):
                    path = Path(entry['path'])
                    missing = []
                    for parent in path.parents:
                        if parent.exists():
                            break
                        missing.append(parent)
                    for parent in reversed(missing):
                        creation = {'path': str(parent), 'created': False}
                        doc['created_parents'].append(creation)
                        self.save(doc)
                        parent.mkdir(mode=0o700)
                        creation['created'] = True
                        self.save(doc)
                        sync_dir(parent.parent)
                    parents_safe(path)
                    if digest(path) != entry['before']:
                        raise ValueError(f'changed before replacement: {path}')
                    if entry['after'] is not None:
                        copy_object(directory / f'{i}-after', entry['temp'])
                    entry['phase'] = 'replacing'
                    self.save(doc)
                    if exists(path):
                        os.rename(path, entry['old'])
                        sync_dir(path.parent)
                    if entry['after'] is not None:
                        os.rename(entry['temp'], path)
                        sync_dir(path.parent)
                    entry['phase'] = 'done'
                    self.save(doc)
                if retain:
                    parents_safe(self.backups / identity)
                    private_directory(self.backups)
                    atomic_json(self.backups / (identity + '.json'), {'schema': 1, 'id': identity,
                                'transaction': identity, 'created': doc['created'], 'action': action, 'objects': [e for e in doc['operations'] if e['before'] is not None]})
                doc['status'] = 'complete'
                self.save(doc)
            except BaseException:
                try:
                    self.rollback(doc)
                except BaseException:
                    doc['status'] = 'recovery-required'
                    self.save(doc)
                raise
            self.cleanup(doc)
            return doc

    def cleanup(self, doc):
        # An application may still hold the renamed original open. Never discard
        # newly written data, even after the replacement itself succeeded.
        for entry in doc['operations']:
            if exists(entry['old']) and digest(entry['old']) != entry['before']:
                doc['status'] = 'recovery-required'
                self.save(doc)
                raise ValueError('retired object changed; preserve and review: ' + entry['old'])
        for entry in doc['operations']:
            for key, expected in [('old', entry['before']), ('temp', entry['after'])]:
                if exists(entry[key]) and (digest(entry[key]) == expected or (key == 'temp' and doc['status'] == 'rolled-back' and digest(entry[key]) == entry['before'])):
                    discard(entry[key])
        directory = self.root / doc['id']
        if doc['status'] in ('complete', 'rolled-back'):
            for i, entry in enumerate(doc['operations']):
                discard(directory / f'{i}-after')
                if not doc['retain_backup'] or doc['status'] == 'rolled-back':
                    discard(directory / f'{i}-before')
        if doc['status'] == 'rolled-back':
            backup = self.backups / (doc['id'] + '.json')
            if exists(backup):
                backup.unlink()

    def rollback(self, doc):
        doc['status'] = 'rolling-back'
        self.save(doc)
        directory = self.root / doc['id']
        for i in reversed(range(len(doc['operations']))):
            entry = doc['operations'][i]
            path = Path(entry['path'])
            parents_safe(path)
            current = digest(path)
            if exists(entry['old']) and digest(entry['old']) != entry['before']:
                raise ValueError('retired object changed; manual recovery required: ' + entry['old'])
            if entry['phase'] == 'prepared':
                continue
            if current == entry['before']:
                entry['phase'] = 'rolled-back'
                self.save(doc)
                continue
            if current not in (None, entry['after']):
                raise ValueError(f'drift blocks recovery: {path}')
            if entry['before'] is not None:
                payload = directory / f'{i}-before'
                if digest(payload) != entry['before']:
                    raise ValueError('recovery payload failed verification')
                # Restore through a sibling, never by overwriting live contents.
                if exists(entry['temp']):
                    if digest(entry['temp']) not in (entry['after'], entry['before']):
                        raise ValueError('changed transaction temporary file')
                    discard(entry['temp'])
                copy_object(payload, entry['temp'])
                if digest(entry['temp']) != entry['before']:
                    raise ValueError('recovery copy changed during verification')
            discard(path)
            if entry['before'] is not None:
                os.rename(entry['temp'], path)
            sync_dir(path.parent)
            entry['phase'] = 'rolled-back'
            self.save(doc)
        for parent in reversed(doc['created_parents']):
            if not parent['created']:
                continue
            try:
                Path(parent['path']).rmdir()
            except OSError:
                pass
        doc['status'] = 'rolled-back'
        self.save(doc)
        self.cleanup(doc)

    def recover(self, identity):
        doc = self.load(identity)
        with self.locked(doc['catalogs']):
            doc = self.load(identity)
            if doc['status'] not in ('preparing', 'applying', 'rolling-back', 'recovery-required'):
                raise ValueError('transaction does not need recovery')
            self.rollback(doc)
        return doc

    def inverse(self, identity):
        doc = self.load(identity)
        if doc['status'] != 'complete':
            raise ValueError('only a completed transaction can be undone')
        operations, guards = [], {}
        for i in reversed(range(len(doc['operations']))):
            entry = doc['operations'][i]
            if digest(entry['path']) != entry['after']:
                raise ValueError('drift blocks undo: ' + entry['path'])
            op = {'path': entry['path']}
            if entry['before'] is not None:
                source = self.root / identity / f'{i}-before'
                if 'before_link' in entry:
                    op['link'] = entry['before_link']
                elif 'before_data' in entry:
                    op['data'] = entry['before_data']
                elif exists(source):
                    if digest(source) != entry['before']:
                        raise ValueError('undo payload failed verification')
                    op['source'] = str(source)
                    guards[str(source)] = entry['before']
                else:
                    reusable = next((path for path, expected in doc.get('guards', {}).items()
                                     if expected == entry['before'] and digest(path) == expected), None)
                    if not reusable:
                        reusable = next((e['path'] for e in doc['operations']
                                         if e['after'] == entry['before'] and digest(e['path']) == entry['before']), None)
                    if not reusable:
                        raise ValueError('original content unavailable; no retained backup')
                    op['source'] = reusable
                    guards[reusable] = entry['before']
            else:
                op['delete'] = True
            operations.append(op)
            guards[entry['path']] = entry['after']
        return operations, guards, doc['catalogs']
