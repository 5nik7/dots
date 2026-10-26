"""Private, bounded tmux-to-ZLE snapshot transport; no shell evaluation."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import select
import signal
import socket
import stat
import struct
import sys
import time

LIMIT = 16 * 1024 * 1024
MAGIC = b'dots-zsh-keys-1\0'
CLIENT_TIMEOUT = 1.0
WORKER_TIMEOUT = 2.0
UNAVAILABLE = 'Live Zsh unavailable in the source pane; showing configuration only. Reload the capture adapter or return to the Zsh prompt.'


def context():
    value = os.environ.get('TMUX', '').rsplit(',', 1)[0]
    path, sep, pid = value.rpartition(',')
    if not sep or not path.startswith('/') or not pid.isdecimal():
        raise ValueError('invalid tmux context')
    return value, pid


def runtime_root():
    base = os.environ.get('XDG_RUNTIME_DIR') or os.environ.get('TMPDIR') or '/tmp'
    if not os.path.isabs(base):
        raise ValueError('runtime directory must be absolute')
    return Path(base) / ('dots-k-' + str(os.geteuid()))


def private(path, kind):
    info = path.lstat()
    return kind(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o077


def candidates(root, server, pane):
    if not private(root, stat.S_ISDIR):
        return []
    found = []
    pattern = re.compile(re.escape(server + '-' + pane[1:] + '-') + r'([0-9]+)-[0-9]+\Z')
    with os.scandir(root) as entries:
        for count, entry in enumerate(entries):
            if count >= 256:
                raise ValueError('too many runtime entries')
            match = pattern.fullmatch(entry.name)
            if not match:
                continue
            directory = root / entry.name
            try:
                os.kill(int(match[1]), 0)
                if private(directory, stat.S_ISDIR) and private(directory / 's', stat.S_ISSOCK):
                    found.append(directory / 's')
            except (OSError, ValueError):
                continue
            if len(found) > 16:
                raise ValueError('too many shell responders')
    return found


def receive(path, request, deadline):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            def remaining():
                value = deadline - time.monotonic()
                if value <= 0:
                    raise TimeoutError()
                client.settimeout(value)
            remaining(); client.connect(str(path))
            remaining(); client.sendall(request)
            response = bytearray()
            size = None
            header = len(MAGIC) + 4
            while True:
                remaining()
                part = client.recv(min(65536, LIMIT + header + 1 - len(response)))
                if not part:
                    break
                response.extend(part)
                if size is None and len(response) >= header:
                    if not response.startswith(MAGIC):
                        return None
                    size = struct.unpack('!I', response[len(MAGIC):header])[0]
                    if size > LIMIT:
                        return None
                if len(response) > LIMIT + header or size is not None and len(response) > header + size:
                    return None
            if size is None or len(response) != header + size:
                return None
            from .providers import snapshot
            rows, apps = snapshot(bytes(response[header:]), 'shell')
            return rows if apps == {'zsh'} else None
    except (OSError, ValueError):
        return None


def capture(pane):
    """Return (rows or None, coverage note), without creating any runtime files."""
    if os.name == 'nt' or not re.fullmatch(r'%[0-9]+', pane):
        return None, UNAVAILABLE
    try:
        identity, server = context()
        paths = candidates(runtime_root(), server, pane)
        if not paths:
            return None, UNAVAILABLE
        request = MAGIC + identity.encode() + b'\0' + pane.encode() + b'\0'
        if len(request) > 4096:
            return None, UNAVAILABLE
        deadline = time.monotonic() + CLIENT_TIMEOUT
        with ThreadPoolExecutor(max_workers=len(paths)) as pool:
            results = list(pool.map(lambda path: receive(path, request, deadline), paths))
        valid = [rows for rows in results if rows is not None]
        if len(valid) == 1:
            return valid[0], 'Captured Zsh keymaps from tmux pane ' + pane + '.'
        if len(valid) > 1:
            return None, 'Multiple Zsh responders in the source pane; showing configuration only.'
    except (OSError, ValueError):
        pass
    return None, UNAVAILABLE


def serve(fd, identity, pane):
    """Worker owns only the accepted socket and an anonymous snapshot pipe."""
    def expired(*_):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, WORKER_TIMEOUT)
    expected = MAGIC + identity.encode() + b'\0' + pane.encode() + b'\0'
    with socket.socket(fileno=fd) as client:
        client.settimeout(0.25)
        request = bytearray()
        while len(request) < len(expected):
            part = client.recv(len(expected) - len(request))
            if not part:
                return
            request.extend(part)
        if request != expected:
            return
        payload = bytearray()
        while True:
            if not select.select([0], [], [], WORKER_TIMEOUT)[0]:
                return
            part = os.read(0, min(65536, LIMIT + 1 - len(payload)))
            if not part:
                break
            payload.extend(part)
            if len(payload) > LIMIT:
                return
        client.settimeout(WORKER_TIMEOUT)
        client.sendall(MAGIC + struct.pack('!I', len(payload)) + payload)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 5 or sys.argv[1] != 'serve':
            raise ValueError('invalid private operation')
        serve(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    except (OSError, ValueError):
        sys.exit(1)
