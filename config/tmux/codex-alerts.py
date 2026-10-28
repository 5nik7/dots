#!/usr/bin/env python3
"""Observational Codex event bridge and private tmux attention worker.

Hook stdout stays empty: no approval decisions or model context. Notification
delivery never runs in the read-only status helper. No transcripts are read.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import unicodedata

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('codex_status', HERE / 'codex-status.py')
status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(status)
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
IDENTITY = re.compile(UUID + r'\Z')
# Only a full pipe-delimited UUID field is transported; titles stay in tmux.
TMUX_UUID = '-'.join('[0-9a-f]' * count for count in (8, 4, 4, 4, 12))
THREAD = ('#{?#{m/r:(^|[|] *)' + TMUX_UUID + ' *$,#{pane_title}},'
          '#{s/^.*(' + TMUX_UUID + ').*$/\\1/:pane_title},-}')
INVENTORY = status.INVENTORY + ' ' + THREAD
ROW = re.compile(r'(@[0-9]+) (%[0-9]+) ([1-9][0-9]*) ([01]) ([01]) (' + UUID + r'|-)\Z')
MAX_INPUT = 262144
MAX_EVENTS = 4096
EXPIRE = 600  # Unmatched candidates are not replayed when a session opens later.
PREFIXES = {'choice': 'Codex needs input', 'approval': 'Codex needs approval', 'complete': 'Codex finished'}
ANSI = re.compile(r'\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])')


def preferences():
    with (HERE / 'codex-alerts.toml').open('rb') as stream:
        doc = tomllib.load(stream)
    if doc['schema'] != 1 or doc['poll_seconds'] != 5:
        raise ValueError('unsupported preferences')
    for value in (doc['enabled'], doc['unfocused_only'], doc['clear_on_view'],
                  *doc['events'].values(), doc['termux']['enabled'],
                  doc['termux']['force_vibration'], doc['termux']['toast_short']):
        if type(value) is not bool:
            raise ValueError('invalid preference')
    options = doc['termux']
    if (type(options['vibration_ms']) is not int or not 1 <= options['vibration_ms'] <= 10000
            or type(options['excerpt_chars']) is not int or not 40 <= options['excerpt_chars'] <= 1000
            or options['toast_gravity'] not in ('top', 'middle', 'bottom')):
        raise ValueError('invalid notification preference')
    for key in ('toast_background', 'toast_foreground'):
        if not re.fullmatch('[a-z_]+', options[key]):
            raise ValueError('invalid palette role')
    return doc


def codex_home():
    return Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))


def installation():
    path = codex_home() / 'dots-notifications.json'
    with path.open('rb') as stream:
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise ValueError('oversized installation record')
    doc = json.loads(raw)
    if (doc.get('schema') != 1 or doc.get('owner') != 'dots-codex-alerts'
            or doc.get('bridge') != str(Path(__file__).resolve())):
        raise ValueError('unowned installation record')
    return doc


def private(path, directory=False):
    info = path.lstat()
    valid = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not valid or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('unsafe private runtime path')


@contextlib.contextmanager
def database():
    root = status.alert_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    private(root, True)
    path = root / 'events.sqlite3'
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    private(path)
    db = sqlite3.connect(path, timeout=1)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA secure_delete=ON')
        db.execute('PRAGMA temp_store=MEMORY')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, thread TEXT, turn TEXT, request TEXT,
                kind TEXT, created REAL, phase TEXT, message TEXT, seen INTEGER DEFAULT 0,
                resolved INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS turns (thread TEXT PRIMARY KEY, turn TEXT, stopped INTEGER);
            CREATE TABLE IF NOT EXISTS sockets (id TEXT PRIMARY KEY, path TEXT, updated REAL);
            CREATE TABLE IF NOT EXISTS panes (
                socket TEXT, pane TEXT, window TEXT, thread TEXT, state TEXT, focused INTEGER,
                PRIMARY KEY(socket,pane));
        ''')
        db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def excerpt(kind, text, limit):
    text = ANSI.sub('', text if isinstance(text, str) else '')
    text = ''.join(' ' if c.isspace() else c for c in text if c.isspace() or not unicodedata.category(c).startswith('C'))
    text = ' '.join(text.split())
    result = PREFIXES[kind] + (': ' + text if text else '')
    return result if len(result) <= limit else result[:limit - 1].rstrip() + '…'


def approval_key(tool, args):
    # Descriptions are added by the approval path, not the original tool call.
    args = {key: value for key, value in args.items() if key not in ('description', 'justification')}
    return hashlib.sha256(json.dumps([tool, args], sort_keys=True).encode()).hexdigest()


def normalize(payload, prefs):
    if not isinstance(payload, dict):
        raise ValueError('invalid event')
    thread = payload.get('session_id', payload.get('thread-id', ''))
    turn = payload.get('turn_id', payload.get('turn-id', ''))
    if not isinstance(thread, str) or not IDENTITY.fullmatch(thread):
        return None
    if not isinstance(turn, str) or len(turn) > 160:
        return None
    event = payload.get('hook_event_name', '')
    tool = payload.get('tool_name', '').split('.')[-1]
    args = payload.get('tool_input') or {}
    if not isinstance(args, dict):
        args = {}
    request = payload.get('tool_use_id', '')
    if not isinstance(request, str) or len(request) > 256:
        return None
    kind, message = '', ''
    if payload.get('type') == 'agent-turn-complete' and turn:
        kind, message = 'complete', payload.get('last-assistant-message', '')
    elif event == 'PreToolUse' and tool in ('request_user_input', 'request_user_input_async') and request:
        kind = 'choice'
        questions = args.get('questions', [])
        if isinstance(questions, list):
            message = ' / '.join(q.get('question', q.get('title', '')) for q in questions
                                 if isinstance(q, dict) and isinstance(q.get('question', q.get('title', '')), str))
    elif event == 'PermissionRequest' and turn:
        kind, message = 'approval', args.get('description', args.get('justification', ''))
        # Approval hooks have no tool_use_id. Hash args only for identity; never store them.
        request = approval_key(tool, args)
    elif event in ('UserPromptSubmit', 'Interrupt', 'SessionEnd'):
        kind = {'UserPromptSubmit': 'start', 'Interrupt': 'interrupt', 'SessionEnd': 'end'}[event]
    elif event == 'PostToolUse' and tool == 'request_user_input' and request:
        kind = 'answered'
    elif event == 'PostToolUse' and tool != 'request_user_input_async':
        kind, request = 'resolved', approval_key(tool, args)
    else:
        return None
    switch = {'choice': 'choices', 'approval': 'approvals', 'complete': 'completion'}.get(kind)
    if switch and not prefs['events'][switch]:
        return None
    identity = hashlib.sha256(json.dumps([thread, turn, kind, request]).encode()).hexdigest()
    return dict(id=identity, thread=thread, turn=turn, kind=kind, request=request,
                message=excerpt(kind, message, prefs['termux']['excerpt_chars']) if switch else '')


def acknowledge(db, clause, values):
    db.execute("UPDATE events SET phase='ack', message='' WHERE " + clause, values)


def focused_at_receipt(thread):
    # Hooks may run in a shared daemon without TMUX_PANE. Consult only registered
    # sockets, with a combined bound, so a focus change before the next tick does
    # not turn an already-viewed event into a new notification.
    with database() as db:
        servers = db.execute('SELECT path FROM sockets WHERE updated>? LIMIT 16', (time.time() - 15,)).fetchall()
    deadline = time.monotonic() + 1
    for server in servers:
        try:
            rows = snapshot(server['path'], deadline)
            if any(row['thread'] == thread and row['focused'] for row in rows):
                return True
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    return False


def record(payload, prefs):
    event = normalize(payload, prefs)
    if not event or not prefs['enabled']:
        return
    viewed = (prefs['unfocused_only'] and event['kind'] in PREFIXES
              and focused_at_receipt(event['thread']))
    with database() as db:
        thread, turn, kind = event['thread'], event['turn'], event['kind']
        if kind == 'start':
            current = db.execute('SELECT turn FROM turns WHERE thread=?', (thread,)).fetchone()
            if current is None or current['turn'] != turn:
                acknowledge(db, 'thread=?', (thread,))
            db.execute('INSERT OR REPLACE INTO turns VALUES (?,?,0)', (thread, turn))
        elif kind in ('end', 'interrupt'):
            acknowledge(db, 'thread=?' + (' AND turn=?' if turn else ''), (thread, turn) if turn else (thread,))
            db.execute('INSERT OR REPLACE INTO turns VALUES (?,?,1)', (thread, turn))
        elif kind in ('answered', 'resolved'):
            acknowledge(db, 'thread=? AND request=?', (thread, event['request']))
            db.execute('UPDATE events SET resolved=1 WHERE thread=? AND request=?', (thread, event['request']))
        else:
            current = db.execute('SELECT * FROM turns WHERE thread=?', (thread,)).fetchone()
            if current and (current['stopped'] or (current['turn'] and current['turn'] != turn)):
                return  # Late notification from a superseded or interrupted turn.
            now = time.time()
            if kind == 'approval':
                previous = db.execute("SELECT id,resolved FROM events WHERE thread=? AND turn=? AND request=? "
                                      "AND kind='approval' ORDER BY created DESC", (thread, turn, event['request'])).fetchall()
                if previous:
                    event['id'] = (hashlib.sha256((event['id'] + ':' + str(len(previous))).encode()).hexdigest()
                                   if previous[0]['resolved'] else previous[0]['id'])
            db.execute("DELETE FROM events WHERE phase='ack' AND created<?", (now - 7 * 86400,))
            if db.execute('SELECT count(*) FROM events').fetchone()[0] >= MAX_EVENTS:
                return
            db.execute('INSERT OR IGNORE INTO events (id,thread,turn,request,kind,created,phase,message) '
                       'VALUES (:id,:thread,:turn,:request,:kind,:created,:phase,:message)',
                       dict(event, created=now, phase='ack' if viewed else 'candidate',
                            message='' if viewed else event['message']))


def bounded(command, timeout=1):
    """Discard stderr and bound stdout/time, including any surviving child group."""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline, output = time.monotonic() + timeout, bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                if not selector.select(status.remaining(deadline)):
                    continue
                chunk = os.read(process.stdout.fileno(), 4096)
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > status.MAX_INVENTORY:
                    raise ValueError('oversized command response')
        if process.wait(timeout=status.remaining(deadline)):
            raise ValueError('command failed')
        return bytes(output)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()


def parse_inventory(raw):
    rows = {}
    for line in raw.decode('ascii').splitlines():
        match = ROW.fullmatch(line)
        if not match or len(rows) >= status.MAX_PANES:
            raise ValueError('invalid pane inventory')
        window, pane, pid, working, waiting, thread = match.groups()
        row = dict(window=window, pane=pane, pid=int(pid), thread=thread,
                   state='waiting' if waiting == '1' else 'working' if working == '1' else 'idle')
        if pane in rows and rows[pane] != row:
            raise ValueError('conflicting pane inventory')
        rows[pane] = row
    return list(rows.values())


def snapshot(socket, deadline=None):
    deadline = deadline or time.monotonic() + status.TIMEOUT
    panes = status.inventory(socket, deadline, INVENTORY, parse_inventory)
    records = status.processes(Path('/proc'), deadline) if panes else {}
    clients = bounded(['tmux', '-S', socket, 'list-clients', '-F',
                       '#{client_control_mode} #{client_flags} #{pane_id}'],
                      timeout=status.remaining(deadline)).decode('ascii').splitlines()
    focused = set()
    for line in clients:
        parts = line.split()
        if len(parts) != 3 or parts[0] not in ('0', '1') or not re.fullmatch('%[0-9]+', parts[2]):
            raise ValueError('invalid client inventory')
        if parts[0] == '0' and 'focused' in parts[1].split(','):
            focused.add(parts[2])
    return [dict(row, focused=row['pane'] in focused) for row in panes
            if row['thread'] != '-' and status.render([(row['window'], row['pid'], row['state'])], records)]


def atomic_snapshot(key, windows, now):
    root = status.alert_root()
    fd, name = tempfile.mkstemp(prefix='.snapshot-', dir=root)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(dict(time=now, windows=sorted(windows)), stream)
        os.replace(name, root / (key + '.json'))
    finally:
        Path(name).unlink(missing_ok=True)


def reconcile(db, prefs, now, deliver=True):
    """All claims and acknowledgements serialize across server workers."""
    db.execute('DELETE FROM panes WHERE socket IN (SELECT id FROM sockets WHERE updated<?)', (now - 15,))
    db.execute('DELETE FROM sockets WHERE updated<?', (now - 15,))
    views = list(db.execute('SELECT * FROM panes'))
    notifications = []
    for event in db.execute("SELECT * FROM events WHERE phase!='ack' ORDER BY created,id").fetchall():
        matches = [v for v in views if v['thread'] == event['thread']]
        focused = any(v['focused'] for v in matches)
        waiting = any(v['state'] == 'waiting' for v in matches)
        if ((focused and (prefs['clear_on_view'] or (event['phase'] == 'candidate' and prefs['unfocused_only'])))
                or (event['seen'] and not matches)
                or (event['phase'] == 'candidate' and now - event['created'] > EXPIRE)
                or (event['phase'] == 'alert' and event['kind'] != 'complete' and not waiting)
                or not prefs['enabled']):
            acknowledge(db, 'id=?', (event['id'],))
        elif matches and event['phase'] == 'candidate' and deliver and (event['kind'] == 'complete' or waiting):
            db.execute("UPDATE events SET phase='alert',message='',seen=1 WHERE id=?", (event['id'],))
            notifications.append(event['message'])
        elif matches:
            db.execute('UPDATE events SET seen=1 WHERE id=?', (event['id'],))
    alerted = {row['thread'] for row in db.execute("SELECT thread FROM events WHERE phase='alert'")}
    changed = []
    for server in db.execute('SELECT * FROM sockets'):
        windows = {v['window'] for v in views if v['socket'] == server['id'] and v['thread'] in alerted}
        path = status.alert_root() / (server['id'] + '.json')
        try:
            previous = json.loads(path.read_text())['windows']
        except (OSError, ValueError, KeyError):
            previous = []
        atomic_snapshot(server['id'], windows, now)
        if set(previous) != windows:
            changed.append(server['path'])
    return notifications, changed


def colors(prefs):
    try:
        path = status.alert_root().parent / 'current/theme/palette.json'
        with path.open('rb') as stream:
            data = stream.read(262145)
        if len(data) > 262144:
            raise ValueError('oversized palette')
        palette = json.loads(data)['colors']
    except (OSError, ValueError, KeyError, TypeError):
        palette = {}
    def color(role, fallback):
        value = palette.get(role) if isinstance(palette, dict) else None
        return value if isinstance(value, str) and re.fullmatch('#[0-9a-fA-F]{6}', value) else fallback
    options = prefs['termux']
    return color(options['toast_background'], '#000000'), color(options['toast_foreground'], '#ffff00')


def notify_device(message, prefs):
    options = prefs['termux']
    if not os.environ.get('TERMUX_VERSION') or not options['enabled']:
        return
    background, foreground = colors(prefs)
    commands = [(['termux-vibrate', '-d', str(options['vibration_ms'])] +
                 (['-f'] if options['force_vibration'] else [])),
                (['termux-toast', '-b', background, '-c', foreground, '-g', options['toast_gravity']] +
                 (['-s'] if options['toast_short'] else []) + ['--', message])]
    for command in commands:
        if shutil.which(command[0]):
            try:
                bounded(command, timeout=2)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass  # Independent, at-most-once attempts, never a retry storm.


def tick(socket, prefs, deliver=True):
    key, now = status.socket_key(socket), time.time()
    panes = snapshot(socket)
    with database() as db:
        db.execute('INSERT OR REPLACE INTO sockets VALUES (?,?,?)', (key, socket, now))
        db.execute('DELETE FROM panes WHERE socket=?', (key,))
        db.executemany('INSERT INTO panes VALUES (?,?,?,?,?,?)',
                       [(key, p['pane'], p['window'], p['thread'], p['state'], int(p['focused'])) for p in panes])
        notifications, changed = reconcile(db, prefs, now, deliver)
    for server in changed:
        try:
            # Request redraws only; tmux still owns client selection and scrolling.
            clients = bounded(['tmux', '-S', server, 'list-clients', '-F', '#{client_name}']).decode().splitlines()
            for client in clients[:64]:
                bounded(['tmux', '-S', server, 'refresh-client', '-S', '-t', client])
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    for message in notifications:
        notify_device(message, prefs)


def watch(socket):
    import fcntl  # Unix adapter; Windows imports and pure tests remain usable.
    key = status.socket_key(socket)
    with database():
        pass
    fd = os.open(status.alert_root() / (key + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        while True:
            try:
                installation()
                if status.socket_key(socket) != key:
                    return
                prefs = preferences()
                tick(socket, prefs)
            except FileNotFoundError:
                return
            except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError):
                # No fabricated completion/notification; the snapshot expires.
                pass
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['hook', 'notify', 'start', 'watch', 'ack'])
    parser.add_argument('payload', nargs='?')
    parser.add_argument('--socket')
    args = parser.parse_args()
    if os.name == 'nt':
        return  # Explicit platform exception: no native tmux/Android consumer.
    os.umask(0o077)
    try:
        installed = installation()
        prefs = preferences()
        if args.mode in ('hook', 'notify'):
            raw = args.payload.encode() if args.mode == 'notify' and args.payload else sys.stdin.buffer.read(MAX_INPUT + 1)
            if len(raw) > MAX_INPUT:
                return
            payload = json.loads(raw)
            try:
                record(payload, prefs)
            except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError):
                pass  # An unavailable queue must not suppress an existing notifier.
            if args.mode == 'notify' and installed.get('previous_notify'):
                try:
                    bounded([*installed['previous_notify'], raw.decode()], timeout=3)
                except (OSError, ValueError, subprocess.SubprocessError):
                    pass
        elif args.socket and args.mode == 'start':
            subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), 'watch', '--socket', args.socket],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True, close_fds=True)
        elif args.socket and args.mode == 'watch':
            watch(args.socket)
        elif args.socket and args.mode == 'ack':
            tick(args.socket, prefs, deliver=False)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error, subprocess.SubprocessError):
        pass  # Hooks are observational and never print potentially private input.


if __name__ == '__main__':
    main()
