#!/usr/bin/env python3
"""Bounded daylight token for tmux. wttr owns weather/location/cache policy."""
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time


def daylight():
    script = Path(__file__).resolve().parents[2] / 'lib/dots/wttr/cli.py'
    process = subprocess.Popen([sys.executable, '-B', str(script), '--daylight'],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        deadline, result = time.monotonic() + 1, b''
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return 'unknown'
                if not selector.select(remaining):
                    continue
                chunk = os.read(process.stdout.fileno(), 64)
                if not chunk:
                    break
                result += chunk
                if len(result) > 16:
                    return 'unknown'
        if process.wait(timeout=max(.001, deadline - time.monotonic())):
            return 'unknown'
        return result.decode('ascii').strip() if result in (b'day\n', b'night\n', b'unknown\n') else 'unknown'
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()


if __name__ == '__main__':
    try:
        print(daylight())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print('unknown')
