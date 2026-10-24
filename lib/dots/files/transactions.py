"""Journaled, bounded native object replacement for dots files.

No automatic force, pruning, or live-root defaults in this engine. Callers supply
validated paths. Recovery payloads are independent of optional retained backups.
"""
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
from pathlib import Path
import shutil
import stat
import uuid

from catalog import atomic_json, read_json
from file_platform import sync_dir, lock, open_nofollow, check_object, copy_file, prepare_text


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from progress import tracked, report


def exists(path):
    return os.path.lexists(path)


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
        check_object(parent)
        if parent.is_symlink():
            raise ValueError(f"symlinked parent requires manual review: {parent}")
        if exists(parent) and not parent.is_dir():
            raise ValueError(f"parent is not a directory: {parent}")


def digest(path):
    """Hash object identity/content, without following symlinks or special files."""
    path = Path(path)
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    h = hashlib.sha256()
    def visit(p, rel):
        check_object(p)
        st = p.lstat()
        h.update(os.fsencode(rel) + b'\0' + str(stat.S_IMODE(st.st_mode)).encode() + b'\0')
        if stat.S_ISLNK(st.st_mode):
            h.update(b'L' + os.fsencode(os.readlink(p)))
        elif stat.S_ISREG(st.st_mode):
            h.update(b'F')
            fd = open_nofollow(p, os.O_RDONLY)
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
        dest.symlink_to(os.readlink(source), target_is_directory=source.is_dir() or bool(getattr(source.lstat(), 'st_file_attributes', 0) & 0x10))
    elif source.is_dir():
        shutil.copytree(source, dest, symlinks=True, copy_function=copy_file)
    else:
        copy_file(source, dest)
    if digest(dest) != before or digest(source) != before:
        raise ValueError('copy verification failed or source changed')
    sync_directories(dest)


def sync_directories(path):
    # File payloads were already flushed through the writable copy handle.
    if path.is_symlink():
        return
    if path.is_dir():
        for child in path.iterdir():
            sync_directories(child)
        sync_dir(path)


def discard(path):
    if not exists(path):
        return
    if Path(path).is_dir() and not Path(path).is_symlink():
        def readonly_retry(function, name, error):
            item = Path(name)
            check_object(item)
            info = item.lstat()
            if (not isinstance(error[1], PermissionError) or not stat.S_ISREG(info.st_mode)
                    or item.is_symlink() or not getattr(info, 'st_file_attributes', 0) & 1):
                raise error[1]
            # Only an already-authorized discarded object is changed here;
            # retained recovery copies keep the original read-only attribute.
            os.chmod(item, info.st_mode | stat.S_IWRITE)
            function(name)
        shutil.rmtree(path, onerror=readonly_retry if os.name == 'nt' else None)
    else:
        Path(path).unlink()


class Store:
    def __init__(self, state, observer=None):
        self.state = Path(state)
        self.root = self.state / 'files' / 'transactions'
        self.backups = self.state / 'backups'
        self.observer = observer

    def notify(self, label, source=None, target=None, **details):
        if self.observer is not None:
            try:
                self.observer(label, source, target, **details)
            except Exception:
                # Observers are optional; they cannot change transaction outcomes.
                pass

    @tracked('Reading transaction history')
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
                fd = open_nofollow(path, os.O_RDWR | os.O_CREAT, 0o600)
                handle = os.fdopen(fd, 'a')
                handles.append(handle)
                lock(handle)
            yield
        finally:
            for handle in reversed(handles):
                handle.close()

    def save(self, doc):
        atomic_json(self.root / doc['id'] / 'journal.json', doc)

    @contextlib.contextmanager
    def publication_locked(self, operations, enabled=True):
        paths = {str(self.state / 'installation.json'), str(self.state / 'current/theme'),
                 str(self.state / 'themes/current'), str(self.state / 'themes/commands/current')}
        if not enabled or not any(op['path'] in paths for op in operations):
            yield
            return
        with contextlib.ExitStack() as stack:
            for path in (self.state / 'themes/commands/lock', self.state / 'themes/lock'):
                parents_safe(path)
                private_directory(path.parent)
                handle = stack.enter_context(os.fdopen(open_nofollow(path, os.O_RDWR | os.O_CREAT), 'a'))
                lock(handle)
            yield

    @tracked('Checking file operation inputs')
    def apply(self, action, operations, guards, retain=False, catalogs=(), identity=None, publication_locked=False):
        """Operations are {path, source|link|data|delete}; guards bind preview inputs."""
        if not operations:
            return {'schema': 1, 'status': 'unchanged', 'operations': []}
        identities = [os.path.normcase(os.path.abspath(op['path'])) for op in operations]
        if len(identities) != len(set(identities)):
            raise ValueError('duplicate or case-colliding operation targets')
        with self.publication_locked(operations, enabled=not publication_locked), self.locked(catalogs):
            for record in self.records():
                if record['status'] in ('applying', 'rolling-back', 'recovery-required', 'preparing'):
                    raise ValueError('unfinished transaction: run dots files recover ' + record['id'])
            for path, expected in guards.items():
                parents_safe(path)
                if digest(path) != expected:
                    raise ValueError(f'changed after preview: {path}')
            identity = identity or uuid.uuid4().hex
            if len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
                raise ValueError('invalid transaction identity')
            directory = self.root / identity
            directory.mkdir(mode=0o700)
            sync_dir(self.root)
            doc = {'schema': 1, 'id': identity, 'action': action, 'status': 'preparing',
                   'created': datetime.now(timezone.utc).isoformat(), 'guards': guards,
                   'retain_backup': retain, 'catalogs': list(map(str, catalogs)), 'operations': [], 'created_parents': []}
            self.save(doc)
            try:
                report('Preparing files', 0, len(operations))
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
                            entry['before_directory'] = path.is_dir() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x10)
                        elif 'data' in op:
                            entry['before_data'] = read_json(path)
                    after = directory / f'{i}-after'
                    if 'source' in op:
                        copy_object(op['source'], after)
                    elif 'link' in op:
                        try:
                            after.symlink_to(op['link'], target_is_directory=op.get('directory', Path(op['link']).is_dir()))
                        except OSError as error:
                            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                                raise ValueError('Windows refused symbolic-link creation. Enable link capability yourself or explicitly select a supported copy strategy; Dots will not elevate or silently copy.') from error
                            raise
                    elif 'text' in op:
                        prepare_text(after, op['text'], path)
                    elif 'data' in op:
                        atomic_json(after, op['data'])
                        if path.exists():
                            os.chmod(after, stat.S_IMODE(path.stat().st_mode))
                    entry['after'] = digest(after)
                    doc['operations'].append(entry)
                    self.save(doc)
                    if before is not None:
                        self.notify('Recovery copy', path, directory / f'{i}-before',
                                    reason='temporary until transaction finalization')
                    report('Preparing files', i + 1, len(operations))
                report('Verifying prepared files')
                # All copies and metadata are ready before the first live replacement.
                for path, expected in guards.items():
                    if digest(path) != expected:
                        raise ValueError(f'changed during preflight: {path}')
                doc['status'] = 'applying'
                self.save(doc)
                report('Applying files', 0, len(doc['operations']))
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
                    op = operations[i]
                    if 'link' in op:
                        source = op['link'] if os.path.isabs(op['link']) else os.path.abspath(path.parent / op['link'])
                        self.notify('Linked', source, path, target_kind='symlink')
                    elif 'source' in op:
                        self.notify('Restored' if action in ('uninstall', 'undo', 'backups-restore') else 'Copied',
                                    op['source'], path)
                    else:
                        self.notify('Removed' if entry['after'] is None else 'Updated', path,
                                    reason='metadata' if 'data' in op else '')
                    report('Applying files', i + 1, len(doc['operations']))
                report('Finalizing file transaction')
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
            if retain:
                for i, entry in enumerate(doc['operations']):
                    if entry['before'] is not None:
                        self.notify('Backup kept', directory / f'{i}-before', reason='backup ID ' + identity)
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
                    if entry['before'] is not None:
                        self.notify('Cleaned', directory / f'{i}-before', reason='temporary recovery copy removed')
        if doc['status'] == 'rolled-back':
            backup = self.backups / (doc['id'] + '.json')
            if exists(backup):
                backup.unlink()

    @tracked('Rolling back files')
    def rollback(self, doc):
        doc['status'] = 'rolling-back'
        self.save(doc)
        directory = self.root / doc['id']
        report('Rolling back files', 0, len(doc['operations']))
        for completed, i in enumerate(reversed(range(len(doc['operations'])))):
            report('Rolling back files', completed, len(doc['operations']))
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
            self.notify('Rolled back', path, reason='original restored' if entry['before'] is not None else 'created object removed')
        report('Finalizing file recovery')
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

    @tracked('Recovering files')
    def recover(self, identity):
        doc = self.load(identity)
        with self.publication_locked(doc['operations']), self.locked(doc['catalogs']):
            doc = self.load(identity)
            if doc['status'] not in ('preparing', 'applying', 'rolling-back', 'recovery-required'):
                raise ValueError('transaction does not need recovery')
            self.rollback(doc)
        return doc

    @tracked('Verifying undo inputs')
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
                    op['directory'] = entry.get('before_directory', Path(entry['before_link']).is_dir())
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
