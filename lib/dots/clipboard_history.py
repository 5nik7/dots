"""Private, transactional text history. Reads never create files or capture text."""
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import uuid

DEFAULTS = dict(record_copies=False, max_entries=500, max_age_days=30,
                max_entry_bytes=65536, deduplicate=True, exclude_patterns=[],
                poll_seconds=2, preview=True, preview_lines=8, list_limit=50)
ID = re.compile(r'[0-9a-f]{32}')


def preferences():
    from config_values import Controls
    from profile_config import checkout
    return {**DEFAULTS, **Controls(checkout()).values.get('apps', {}).get('clipboard', {})}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def fingerprint(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def metadata(row):
    return {k: v for k, v in row.items() if k not in ('text', 'digest')}


class History:
    def __init__(self, directory=None, settings=None):
        from files.file_platform import state_root
        self.directory = Path(directory) if directory is not None else state_root() / 'clipboard'
        self.path = self.directory / 'history.sqlite3'
        self.settings = preferences() if settings is None else {**DEFAULTS, **settings}

    def _check(self):
        for path in (self.directory, self.path):
            if path.is_symlink():
                raise ValueError('clipboard history paths must not be symlinks')
            if path.exists():
                info = path.stat()
                if (path == self.path and not stat.S_ISREG(info.st_mode)) or (path == self.directory and not stat.S_ISDIR(info.st_mode)):
                    raise ValueError('invalid clipboard history path')
                if os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
                    raise ValueError('clipboard history requires owner-only permissions')

    @contextmanager
    def connect(self, write=False):
        self._check()
        if not write and not self.path.exists():
            yield None
            return
        if write:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not self.path.exists():
                try:
                    fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                except FileExistsError:
                    pass  # Another writer created the same owned database.
                else:
                    os.close(fd)
        self._check()
        db = sqlite3.connect(str(self.path) if write else self.path.as_uri() + '?mode=ro',
                             uri=not write, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            if write:
                db.execute('PRAGMA secure_delete=ON')
                db.execute('PRAGMA journal_mode=DELETE')
                db.execute('BEGIN IMMEDIATE')
                version = db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0, 1):
                    raise ValueError('unsupported clipboard history schema')
                db.execute('CREATE TABLE IF NOT EXISTS entries (id TEXT PRIMARY KEY, text TEXT NOT NULL, digest TEXT NOT NULL, source TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL, pinned INTEGER NOT NULL)')
                db.execute('CREATE INDEX IF NOT EXISTS entries_digest ON entries(digest)')
                db.execute('CREATE TABLE IF NOT EXISTS control (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                db.execute('PRAGMA user_version=1')
            elif db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('unsupported clipboard history schema')
            yield db
            if write:
                db.execute('COMMIT')
        except BaseException:
            if write and db.in_transaction:
                db.execute('ROLLBACK')
            raise
        finally:
            db.close()

    @staticmethod
    def control_get(db, key, default=None):
        row = db.execute('SELECT value FROM control WHERE key=?', (key,)).fetchone() if db else None
        return json.loads(row[0]) if row else default

    @staticmethod
    def control_set(db, key, value):
        db.execute('INSERT OR REPLACE INTO control VALUES (?,?)', (key, json.dumps(value)))

    def control(self, key, default=None):
        with self.connect() as db:
            return self.control_get(db, key, default)

    def set_control(self, key, value):
        with self.connect(True) as db:
            self.control_set(db, key, value)

    def rows(self, query='', pinned=False, source=None, since=None, until=None, limit=None):
        clauses, values = [], []
        for field, op, value in (('source', '=', source), ('updated', '>=', since), ('updated', '<=', until)):
            if value is not None:
                clauses.append(field + op + '?'); values.append(value)
        if pinned:
            clauses.append('pinned=1')
        with self.connect() as db:
            rows = [] if db is None else [dict(r) for r in db.execute(
                'SELECT * FROM entries' + (' WHERE ' + ' AND '.join(clauses) if clauses else '') + ' ORDER BY updated DESC,id', values)]
        if query:
            words = query.casefold().split()
            rows = [r for r in rows if all(w in r['text'].casefold() for w in words)]
        for row in rows:
            row['pinned'] = bool(row['pinned'])
            row['bytes'] = len(row['text'].encode('utf-8'))
        return rows[:limit] if limit is not None else rows

    def ids(self):
        with self.connect() as db:
            return [r[0] for r in db.execute('SELECT id FROM entries ORDER BY updated DESC,id')] if db else []

    def get(self, identity):
        if not ID.fullmatch(identity):
            raise ValueError('expected a full clipboard entry ID')
        with self.connect() as db:
            row = db.execute('SELECT * FROM entries WHERE id=?', (identity,)).fetchone() if db else None
        if row is None:
            raise ValueError('clipboard entry no longer exists')
        result = dict(row); result['pinned'] = bool(result['pinned']); result['bytes'] = len(result['text'].encode('utf-8'))
        return result

    def validate_text(self, text):
        if not isinstance(text, str) or '\0' in text:
            raise ValueError('clipboard history requires UTF-8 text without NUL')
        try:
            length = len(text.encode('utf-8'))
        except UnicodeError:
            raise ValueError('clipboard history requires valid UTF-8 text') from None
        if length > self.settings['max_entry_bytes']:
            raise ValueError('clipboard entry exceeds the configured size limit')
        return length

    def excluded(self, text):
        return any(fnmatch.fnmatchcase(text, pattern) for pattern in self.settings['exclude_patterns'])

    def _put(self, db, text, source, pinned=False, automatic=False):
        self.validate_text(text)
        if self.excluded(text) or (automatic and self.control_get(db, 'paused', False)):
            return None
        digest = fingerprint(text)
        if automatic and digest == self.control_get(db, 'last_digest'):
            return None
        stamp = now()
        found = db.execute('SELECT * FROM entries WHERE digest=? ORDER BY updated DESC LIMIT 1', (digest,)).fetchone() if self.settings['deduplicate'] else None
        if found:
            identity = found['id']
            db.execute('UPDATE entries SET updated=?,source=?,pinned=? WHERE id=?',
                       (stamp, source, int(pinned or found['pinned']), identity))
        else:
            identity = uuid.uuid4().hex
            db.execute('INSERT INTO entries VALUES (?,?,?,?,?,?,?)', (identity, text, digest, source, stamp, stamp, int(pinned)))
        self.control_set(db, 'last_digest', digest)
        self._prune(db)
        if db.execute('SELECT COUNT(*) FROM entries').fetchone()[0] > self.settings['max_entries']:
            raise ValueError('history is full of pinned entries; unpin or remove an entry')
        if not db.execute('SELECT 1 FROM entries WHERE id=?', (identity,)).fetchone():
            raise ValueError('history is full of pinned entries; unpin or remove an entry')
        return identity

    def add(self, text, source='manual', pinned=False, automatic=False):
        self.validate_text(text)
        if self.excluded(text):
            return None
        with self.connect(True) as db:
            identity = self._put(db, text, source, pinned, automatic)
            row = dict(db.execute('SELECT * FROM entries WHERE id=?',(identity,)).fetchone()) if identity else None
        if row:
            row['pinned']=bool(row['pinned']); row['bytes']=len(row['text'].encode('utf-8'))
        return row

    def _prune(self, db, preview=False):
        rows = [dict(r) for r in db.execute('SELECT * FROM entries ORDER BY updated DESC,id')]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.settings['max_age_days'])).isoformat()
        remove = [r for r in rows if not r['pinned'] and r['updated'] < cutoff]
        expired = {r['id'] for r in remove}
        remaining = [r for r in rows if r['id'] not in expired]
        extra = max(0, len(remaining) - self.settings['max_entries'])
        remove += [r for r in reversed(remaining) if not r['pinned']][:extra]
        if not preview:
            db.executemany('DELETE FROM entries WHERE id=?', [(r['id'],) for r in remove])
        return remove

    def prune_candidates(self):
        with self.connect() as db:
            return self._prune(db, True) if db else []

    def change(self, rows, *, delete=False, pinned=None):
        with self.connect(True) as db:
            for row in rows:
                current = db.execute('SELECT * FROM entries WHERE id=?', (row['id'],)).fetchone()
                if current is None or any(current[key] != row[key] for key in ('updated', 'digest', 'pinned')):
                    raise ValueError('clipboard selection changed; review it again')
            for row in rows:
                if delete:
                    db.execute('DELETE FROM entries WHERE id=?', (row['id'],))
                else:
                    db.execute('UPDATE entries SET pinned=?,updated=? WHERE id=?', (int(pinned), now(), row['id']))
            if delete:
                # Removing the most recent text must not preserve a content hash.
                db.execute("DELETE FROM control WHERE key='last_digest'")

    def import_entries(self, document, dry_run=False):
        if not isinstance(document, dict) or document.get('schema') != 1 or not isinstance(document.get('entries'), list):
            raise ValueError('expected a schema-1 clipboard export')
        rows = document['entries']
        if len(rows) > self.settings['max_entries']:
            raise ValueError('import exceeds the configured entry count')
        for row in rows:
            if not isinstance(row, dict) or type(row.get('pinned', False)) is not bool:
                raise ValueError('invalid clipboard import entry')
            self.validate_text(row.get('text'))
        if dry_run:
            return len(rows)
        with self.connect(True) as db:
            for row in reversed(rows):
                self._put(db, row['text'], 'import', row.get('pinned', False))
        return len(rows)


def record_copy(text, source='dots'):
    """A recording failure must never turn a successful clipboard copy into failure."""
    try:
        settings = preferences()
        if not settings['record_copies']:
            return
        History(settings=settings).add(text, source=source, automatic=True)
    except (ValueError, OSError, sqlite3.Error):
        print('clipboard: copy succeeded; history recording unavailable', file=__import__('sys').stderr)
