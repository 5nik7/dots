"""Private, bounded snapshots for tmux's disposable one-shot status workers."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time

LIMIT = 128 * 1024
CHILDREN = []


def read(path, limit=LIMIT):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('not a regular cache file')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('cache exceeds limit')
    return raw


def age(updated, now=None):
    now = time.time() if now is None else now
    if type(updated) not in (int, float) or not math.isfinite(updated) or not 0 < updated <= now:
        return float('inf')
    return now - updated


def command(argv, timeout, limit, **kwargs):
    """Bound bytes and wall time, including descendants holding output open."""
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, start_new_session=True, **kwargs)
    deadline, output = time.monotonic() + timeout, bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('provider deadline')
                if not selector.select(remaining):
                    continue
                chunk = os.read(process.stdout.fileno(), min(4096, limit + 1))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > limit:
                    raise ValueError('provider output exceeds limit')
        if process.wait(timeout=max(.001, deadline-time.monotonic())):
            raise ValueError('provider unavailable')
        return output.decode('utf-8')
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()


class Cache:
    def __init__(self, kind, identity):
        base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')
        if not base.is_absolute():
            raise ValueError('cache root must be absolute')
        self.root = base / 'dots/tmux-widgets'
        digest = hashlib.sha256(json.dumps([kind, identity], sort_keys=True).encode()).hexdigest()
        self.path = self.root / (kind + '-' + digest + '.json')

    def read(self):
        try:
            row = json.loads(read(self.path))
            if not isinstance(row, dict) or row.get('schema') != 1 or not isinstance(row.get('value', {}), dict):
                return {}
            for key in ('updated', 'written', 'lease', 'next_at'):
                if type(row.get(key, 0)) not in (int, float) or not math.isfinite(row.get(key, 0)):
                    return {}
            if age(row.get('written')) == float('inf'):
                return {}
            if row.get('lease',0)>row['written']+120 or row.get('next_at',0)>row['written']+86400:
                return {}
            return row
        except (OSError, ValueError, RecursionError):
            return {}

    def prepare(self):
        # Inspect each existing ancestor before creating any owned child.
        for path in reversed((self.root, *self.root.parents)):
            try:
                mode = path.lstat().st_mode
            except FileNotFoundError:
                try:path.mkdir(mode=0o700)
                except FileExistsError:pass
                mode = path.lstat().st_mode
            if not stat.S_ISDIR(mode):
                raise ValueError('unsafe cache directory')

    @contextmanager
    def locked(self):
        self.prepare()
        fd = os.open(self.path.with_suffix('.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        with os.fdopen(fd, 'r+b') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('unsafe cache lock')
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def write(self, row):
        row = dict(row, schema=1, written=time.time())
        payload = json.dumps(row, allow_nan=False, ensure_ascii=True).encode()
        if len(payload) > LIMIT:
            raise ValueError('cache exceeds limit')
        if self.path.is_symlink() or self.path.exists() and not self.path.is_file():
            raise ValueError('unsafe cache target')
        fd, temporary = tempfile.mkstemp(prefix='.widget-', dir=self.root)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def schedule(self, script, args=(), timeout=10, due=False):
        try:
            with self.locked():
                row, now = self.read(), time.time()
                if now < row.get('lease',0) or not due and now < row.get('next_at',0):
                    return
                token = secrets.token_hex(16)
                row.update(token=token, lease=now+timeout+10)
                self.write(row)
                try:
                    CHILDREN[:]=[child for child in CHILDREN if child.poll() is None]
                    child=subprocess.Popen([sys.executable, '-B', str(script), '--_worker', token, *args],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
                    CHILDREN.append(child)
                except OSError:
                    row.update(lease=0, next_at=now+5, failed=True)
                    self.write(row)
        except (OSError, ValueError):
            pass

    def work(self, token, producer, interval, retry=5):
        # Scheduler releases the lock immediately after spawning the child.
        for attempt in range(20):
            try:
                with self.locked():
                    row = self.read()
                    if row.get('token') != token:
                        return
                    delay = interval
                    try:
                        value, delay = producer(row.get('value', {}))
                        row.update(value=value, updated=time.time(), failed=False)
                    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
                        row['failed'] = True
                        delay = retry
                    row.update(lease=0, next_at=time.time()+delay)
                    self.write(row)
                    return
            except BlockingIOError:
                time.sleep(.025)
            except (OSError, ValueError):
                return
