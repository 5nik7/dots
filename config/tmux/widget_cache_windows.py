"""Native file and pipe operations for an explicitly requested quota refresh."""
import errno
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lib/dots/files'))
from file_platform import lock, open_nofollow, reparse


def open_file(path, flags):
    if any(reparse(parent) for parent in path.parents):
        raise ValueError('unsafe cache directory')
    return open_nofollow(path, flags | os.O_BINARY)


def lock_file(stream):
    try:
        lock(stream)
    except PermissionError as error:
        # msvcrt reports an occupied byte-range lock as EACCES.
        if error.errno == errno.EACCES:
            raise BlockingIOError('widget refresh in progress') from error
        raise


def replace_file(source, target):
    # An overlapping CRT reader can briefly deny DELETE sharing.
    deadline = time.monotonic() + .25
    while True:
        try:
            os.replace(source, target)
            return
        except PermissionError as error:
            if getattr(error, 'winerror', None) not in (5, 32) or time.monotonic() >= deadline:
                raise
            time.sleep(.01)


def provider_output(argv, timeout, limit):
    # Windows selectors do not accept anonymous pipes. Drain bounded bytes on
    # a separate thread so even a descendant holding stdout cannot stall us.
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, bufsize=0,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + timeout
    output = bytearray()
    errors = []

    def read_output():
        try:
            with process.stdout as stream:
                while len(output) <= limit:
                    chunk = stream.read(min(65536, limit + 1 - len(output)))
                    if not chunk:
                        break
                    output.extend(chunk)
        except OSError as error:
            errors.append(error)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        reader.join(timeout)
        if reader.is_alive():
            raise TimeoutError('provider deadline')
        if errors or len(output) > limit:
            raise ValueError('invalid provider output')
        if process.wait(timeout=max(0, deadline - time.monotonic())):
            raise ValueError('provider unavailable')
        return output.decode('utf-8')
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
