"""Read-only, bounded Codex topology snapshots shared by status and menus."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

TTL = 15
MAX_BYTES = 1048576
ID = re.compile(r'\$[0-9]+\Z')
PANE = re.compile(r'%[0-9]+\Z')
WINDOW = re.compile(r'@[0-9]+\Z')
THREAD = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
TTY = re.compile(r'pts/[0-9]+\Z')
PRIORITY = {'idle': 0, 'waiting': 1, 'working': 2}


def root():
    path = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'dots/codex-alerts'
    if not path.is_absolute():
        raise ValueError('state root must be absolute')
    return path


def socket_key(socket):
    info = Path(socket).stat()
    return hashlib.sha256(f'{socket}:{info.st_dev}:{info.st_ino}'.encode()).hexdigest()


def tab_identity(pid, proc=Path('/proc')):
    """Recheck identity without reading argv, environment or terminal contents."""
    path = proc / str(pid)
    if path.stat().st_uid != os.getuid():
        raise ValueError('foreign process')
    with (path / 'stat').open('rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError('oversized process')
    fields = raw[raw.rindex(b')') + 2:].split()
    if (int(raw[:raw.index(b'(')]) != pid or int(fields[3]) != pid
            or int(fields[4]) == 0 or fields[0] in (b'Z', b'X', b'x')):
        raise ValueError('invalid tab leader')
    return int(fields[19])


def load(now=None):
    """Unavailable/old snapshots have no effect on normal status or data APIs."""
    now = time.time() if now is None else now
    try:
        directory = root()
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            return []
        fd = os.open(directory / 'overview.json', os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                return []
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return []
        doc = json.loads(raw)
        if doc['schema'] != 1 or not 0 <= now - doc['time'] <= TTL or len(doc['servers']) > 16:
            return []
        servers = []
        for server in doc['servers']:
            if not 0 <= now - server['updated'] <= TTL:
                continue
            if not isinstance(server['socket'], str) or not Path(server['socket']).is_absolute():
                raise ValueError('invalid socket')
            try:
                if socket_key(server['socket']) != server['key']:
                    continue
            except OSError:
                continue
            if len(server['panes']) > 2048 or len(server['clients']) > 64 or len(server['tabs']) > 256:
                raise ValueError('oversized topology')
            for pane in server['panes']:
                if (not PANE.fullmatch(pane['pane']) or not WINDOW.fullmatch(pane['window'])
                        or pane['state'] not in PRIORITY or type(pane['attention']) is not bool
                        or (pane['thread'] != '-' and not THREAD.fullmatch(pane['thread']))
                        or len(pane['sessions']) > 256):
                    raise ValueError('invalid pane')
                for session in pane['sessions']:
                    if not ID.fullmatch(session['id']) or type(session['created']) is not int:
                        raise ValueError('invalid session')
            for client in server['clients']:
                if not ID.fullmatch(client['session']) or not TTY.fullmatch(client['tty']):
                    raise ValueError('invalid client')
            for tab in server['tabs']:
                if (type(tab['pid']) is not int or tab['pid'] <= 0 or type(tab['started']) is not int
                        or not TTY.fullmatch(tab['tty'])):
                    raise ValueError('invalid tab')
            servers.append(server)
        return servers
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []


def live_tabs(server, proc=Path('/proc')):
    result = {}
    for tab in server['tabs']:
        try:
            if tab_identity(tab['pid'], proc) == tab['started']:
                result[tab['tty']] = tab
        except (OSError, ValueError, IndexError):
            continue
    return result


def sessions(servers):
    """One stable record per server/session; linked panes do not inflate counts."""
    result = []
    for server in servers:
        groups = {}
        for pane in server['panes']:
            for identity in pane['sessions']:
                record = groups.setdefault(identity['id'], dict(identity, socket=server['socket'],
                    key=server['key'], state='idle', panes=[], attention=0))
                record['state'] = max(record['state'], pane['state'], key=PRIORITY.__getitem__)
                record['panes'].append(pane)
                record['attention'] += int(pane['attention'])
        result.extend(groups.values())
    return result


def tab_states(servers, proc=Path('/proc')):
    """Map attached session activity to real tabs, independent of server ancestry."""
    tabs, undisplayed = {}, set()
    for server in servers:
        live = live_tabs(server, proc)
        for session in sessions([server]):
            owners = {c['tty'] for c in server['clients'] if c['session'] == session['id'] and c['tty'] in live}
            if session['attention'] and not owners:
                undisplayed.add((server['key'], session['id']))
            for tty in owners:
                tab = live[tty]
                value = tabs.setdefault((tab['pid'], tab['started'], tty), dict(state='idle', attention=False))
                value['state'] = max(value['state'], session['state'], key=PRIORITY.__getitem__)
                value['attention'] |= bool(session['attention'])
    return tabs, len(undisplayed)
