#!/usr/bin/env python3
"""Bound Git status/host metadata and keep names literal in tmux formats."""
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time


def compact_fields(output):
    """Normalize only Dots-styled metrics/divergence, never arbitrary Git names."""
    parts = re.split(r'(#\[[^\]]*\])', output)
    for index in range(1, len(parts) - 3, 2):
        style, text, next_style, next_text = parts[index:index + 4]
        if ('@dots-gitmux-added}' in style and re.fullmatch(r'\+[0-9]+ ', text)
                and '@dots-gitmux-deleted}' in next_style and re.fullmatch(r'-[0-9]+ ?', next_text)):
            parts[index + 1] = text[:-1]
        elif ('@dots-gitmux-ahead}' in style and re.fullmatch(r'⇡[0-9]+', text)
              and '@dots-gitmux-behind}' in next_style and re.fullmatch(r'⇣[0-9]+ ?', next_text)):
            parts[index] = style.replace('@dots-gitmux-ahead}', '@dots-gitmux-conflict}')
            parts[index + 2] = next_style.replace('@dots-gitmux-behind}', '@dots-gitmux-conflict}')
    return ''.join(parts)


def literal_names(output):
    """Git refs cannot contain '[', so only configured styles can open '#['."""
    output = output.rstrip('\n')
    if any(ord(char) < 32 or 127 <= ord(char) < 160 for char in output):
        raise ValueError('control character in gitmux output')
    parts = re.split(r'(#\[[^\]]*\])', output)
    return ''.join(part if index % 2 else part.replace('#', '##')
                   for index, part in enumerate(parts))


def collect(directory, snapshot):
    """Independent providers share one deadline, with no persistent metadata."""
    # Both providers change cwd; keep a relative legacy argument from being
    # resolved a second time by gitmux. Joining preserves symlink/.. semantics.
    directory = os.path.join(os.getcwd(), directory)
    commands = {'gitmux': (['gitmux', '-cfg', str(Path.home() / '.gitmux.conf'),
                            '-timeout', '1s', directory], 16384)}
    if snapshot:
        commands['icon'] = (['git-it', 'info', '--json'], 65536)
    processes, buffers, finished = {}, {}, set()
    deadline = time.monotonic() + 1
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    try:
        with selectors.DefaultSelector() as selector:
            for name, (command, _) in commands.items():
                try:
                    process = subprocess.Popen(command, cwd=directory, env=env,
                                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                               stderr=subprocess.DEVNULL, start_new_session=True)
                except OSError:
                    continue
                processes[name], buffers[name] = process, bytearray()
                selector.register(process.stdout, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                for key, _ in selector.select(remaining):
                    name = key.data
                    chunk = os.read(key.fileobj.fileno(), 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        finished.add(name)
                    elif len(buffers[name]) + len(chunk) > commands[name][1]:
                        selector.unregister(key.fileobj)
                        try:
                            os.killpg(processes[name].pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:
                        buffers[name].extend(chunk)
        output = {}
        for name, process in processes.items():
            if name not in finished:
                continue
            try:
                if process.wait(timeout=max(.001, deadline - time.monotonic())) == 0:
                    output[name] = buffers[name].decode('utf-8')
            except (UnicodeError, subprocess.TimeoutExpired):
                pass
        return output
    finally:
        for process in processes.values():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            process.stdout.close()


def remote_icon(raw):
    info = json.loads(raw)
    if (isinstance(info, dict) and isinstance(info.get('remote'), str) and info['remote']
            and info.get('icon') in ('󰊤', '', '', '')):
        return info['icon']
    return ''


def status(directory, snapshot=False):
    output = collect(directory, snapshot)
    try:
        gitmux = literal_names(compact_fields(output.get('gitmux', '')))
    except ValueError:
        gitmux = ''
    if not snapshot:
        return gitmux
    try:
        icon = remote_icon(output.get('icon', ''))
    except (ValueError, RecursionError):
        icon = ''
    return icon + '|' + gitmux


if __name__ == '__main__':
    try:
        if len(sys.argv) == 3 and sys.argv[1] == '--snapshot':
            print(status(sys.argv[2], snapshot=True))
        else:
            print(status(sys.argv[1]) if len(sys.argv) == 2 else '')
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print('')
