#!/usr/bin/env python3
"""Read local foreground Codex presence and emit bounded window/state tokens."""
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time


TIMEOUT = 1.0
MAX_INVENTORY = 131072
MAX_PANES = 2048
MAX_PROCESSES = 8192
MAX_STAT = 4096
# Reduce untrusted titles to flags inside tmux; never transport their text.
INVENTORY = ('#{window_id} #{pane_id} #{pane_pid} '
             '#{m/r:(^|[|] *)Working([.]*|…)( *[|]|$),#{pane_title}} '
             '#{m/r:(^|[|] *)[[] [!.] []] Action Required( *[|]|$),#{pane_title}}')
ROW = re.compile(r'(@[0-9]+) (%[0-9]+) ([1-9][0-9]*) ([01]) ([01])\Z')
STATE_PRIORITY = {'idle': 0, 'waiting': 1, 'working': 2}


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError('status deadline')
    return value


def inventory(socket, deadline):
    process = subprocess.Popen(['tmux', '-S', socket, 'list-panes', '-a',
                                '-f', '#{==:#{pane_dead},0}', '-F', INVENTORY],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        output = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                if not selector.select(remaining(deadline)):
                    continue
                chunk = os.read(process.stdout.fileno(), 4096)
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > MAX_INVENTORY:
                    raise ValueError('oversized inventory')
        if process.wait(timeout=remaining(deadline)):
            raise ValueError('inventory unavailable')
        return parse_inventory(bytes(output))
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()


def parse_inventory(raw):
    if len(raw) > MAX_INVENTORY:
        raise ValueError('oversized inventory')
    rows = raw.decode('ascii').splitlines()
    if len(rows) > MAX_PANES:
        raise ValueError('too many panes')
    panes = {}
    for row in rows:
        match = ROW.fullmatch(row)
        if not match:
            raise ValueError('invalid inventory')
        window, pane, pid, working, waiting = match.groups()
        # A blocked pane can retain a Working field; explicit input wins here.
        state = 'waiting' if waiting == '1' else 'working' if working == '1' else 'idle'
        record = (window, int(pid), state)
        if pane in panes and panes[pane] != record:
            raise ValueError('conflicting pane')
        panes[pane] = record  # Linked windows may repeat identical panes.
    return list(panes.values())


def parse_stat(raw):
    if len(raw) > MAX_STAT:
        raise ValueError('oversized process record')
    opening, closing = raw.index(b'('), raw.rindex(b')')
    fields = raw[closing + 1:].split()
    # comm can contain spaces, parentheses and newlines. No argv or environment.
    return dict(pid=int(raw[:opening]), name=raw[opening + 1:closing],
                state=fields[0], group=int(fields[2]), tty=int(fields[4]),
                foreground=int(fields[5]))


def processes(proc_root, deadline):
    if not hasattr(os, 'getuid'):
        raise OSError('procfs unsupported')
    uid, records, count = os.getuid(), {}, 0
    for directory in proc_root.iterdir():
        remaining(deadline)
        if not directory.name.isascii() or not directory.name.isdecimal():
            continue
        try:
            if directory.stat().st_uid != uid:
                continue
            count += 1
            if count > MAX_PROCESSES:
                raise ValueError('too many processes')
            with (directory / 'stat').open('rb') as stream:
                record = parse_stat(stream.read(MAX_STAT + 1))
            if record['pid'] != int(directory.name):
                raise ValueError('process identity changed')
            records[record['pid']] = record
        except (FileNotFoundError, ProcessLookupError):
            continue  # Normal exit races; all other failures clear the snapshot.
    remaining(deadline)
    return records


def render(panes, records):
    inactive = (b'T', b't', b'Z', b'X', b'x')
    foreground = {(record['group'], record['tty']) for record in records.values()
                  if record['name'] == b'codex' and record['state'] not in inactive
                  and record['tty'] != 0 and record['group'] > 0}
    windows = {}
    for window, pid, state in panes:
        parent = records.get(pid)
        if (parent is None or parent['state'] in inactive
                or (parent['foreground'], parent['tty']) not in foreground):
            continue
        # Across separate panes, any actual Working pane wins over waiting.
        windows[window] = max(windows.get(window, 'idle'), state, key=STATE_PRIORITY.__getitem__)
    tokens = [window + ':' + windows[window]
              for window in sorted(windows, key=lambda value: int(value[1:]))]
    return '|' + '|'.join(tokens) + '|' if tokens else ''


def status(socket, proc_root=Path('/proc')):
    try:
        deadline = time.monotonic() + TIMEOUT
        panes = inventory(socket, deadline)
        if not panes:
            return ''
        result = render(panes, processes(proc_root, deadline))
        remaining(deadline)
        return result
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return ''


if __name__ == '__main__':
    # A newline clears tmux's previous successful value after failure or exit.
    print(status(sys.argv[1]) if len(sys.argv) == 2 else '')
