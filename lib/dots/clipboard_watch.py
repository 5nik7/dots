"""Explicit polling worker, controlled by an owned token rather than PID signals."""
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from clipboard_history import History


LEASE_SECONDS = 30


def status(history):
    state = history.control('watch', {})
    if state.get('token') and time.time() - state.get('heartbeat', 0) > LEASE_SECONDS:
        return {**state, 'status': 'stale'}
    return state or dict(status='stopped')


def start(history, foreground=False):
    from clipboard import _provider
    _provider('read')
    token = uuid.uuid4().hex
    with history.connect(True) as db:
        old = history.control_get(db, 'watch', {})
        if old.get('token') and time.time() - old.get('heartbeat', 0) <= LEASE_SECONDS:
            raise ValueError('clipboard watcher is already running')
        history.control_set(db, 'watch', dict(token=token, status='starting', heartbeat=time.time(), pid=None, error=None))
    try:
        if foreground:
            worker(history, token)
        else:
            options = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.name == 'nt':
                options['creationflags'] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                options['start_new_session'] = True
            env = dict(os.environ)
            env.setdefault('DOTS', str(Path(__file__).resolve().parents[2]))
            subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), token], env=env, **options)
    except BaseException:
        stop(history, token)
        raise
    return status(history)


def stop(history, token=None):
    if not history.path.exists():
        return dict(status='stopped')
    with history.connect(True) as db:
        current = history.control_get(db, 'watch', {})
        if token is None or current.get('token') == token:
            history.control_set(db, 'watch', dict(status='stopped', heartbeat=time.time(), pid=None, error=None))
    return status(history)


def tick(history, token):
    from clipboard import paste
    current = history.control('watch', {})
    if current.get('token') != token:
        return False
    text, error = None, None
    if not history.control('paused', False):
        try:
            text = paste().decode('utf-8')
            history.validate_text(text)
        except (ValueError, OSError):
            error = 'clipboard unavailable or text exceeds limits'
    with history.connect(True) as db:
        state = history.control_get(db, 'watch', {})
        if state.get('token') != token:
            return False
        paused = history.control_get(db, 'paused', False)
        if text is not None and not paused:
            try:
                history._put(db, text, 'watch', automatic=True)
            except ValueError:
                # Roll back a rejected entry without discarding the worker lease.
                raise
        history.control_set(db, 'watch', dict(token=token, pid=os.getpid(), heartbeat=time.time(),
                            status='paused' if paused else 'degraded' if error else 'running', error=error))
    return True


def worker(history, token):
    try:
        while True:
            try:
                from clipboard_history import preferences
                history.settings = preferences()
                if not tick(history, token):
                    break
            except (ValueError, OSError, __import__('sqlite3').Error):
                with history.connect(True) as db:
                    state = history.control_get(db, 'watch', {})
                    if state.get('token') != token:
                        break
                    history.control_set(db, 'watch', dict(token=token, pid=os.getpid(), heartbeat=time.time(),
                                         status='degraded', error='history or clipboard unavailable'))
            time.sleep(history.settings['poll_seconds'])
    finally:
        stop(history, token)


if __name__ == '__main__':
    if len(sys.argv) != 2 or not __import__('re').fullmatch('[0-9a-f]{32}', sys.argv[1]):
        raise SystemExit(2)
    try:
        worker(History(), sys.argv[1])
    except KeyboardInterrupt:
        raise SystemExit(130)
