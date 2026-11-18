"""Escape dismissal for Dots' less reader, preserving terminal key sequences."""
import errno
import os
import select
import signal
import subprocess
import threading
import time


def run(argv, *, stdin, env):
    if os.name == 'nt':
        # Native Windows less reads console keys, with non-Escape scan codes for
        # arrows. Its owned lesskey source is supplied by menu_pager.
        return subprocess.call(argv, stdin=stdin, env=env)
    try:
        terminal = os.open('/dev/tty', os.O_RDWR)
    except OSError:
        return subprocess.call(argv, stdin=stdin, env=env)
    try:
        return _posix(argv, stdin, env, terminal)
    finally:
        os.close(terminal)


def _write(fd, data):
    while data:
        data = data[os.write(fd, data):]


def _posix(argv, content, environment, terminal):
    import fcntl
    import pty
    import termios
    import tty

    original = termios.tcgetattr(terminal)
    size = fcntl.ioctl(terminal, termios.TIOCGWINSZ, b'\0' * 8)
    pid, master = pty.fork()
    if pid == 0:
        try:
            fcntl.ioctl(1, termios.TIOCSWINSZ, size)
            os.dup2(content.fileno(), 0)
            os.execve(argv[0], argv, environment)
        finally:
            os._exit(127)
    status = None
    escaped = False
    cancelled = False
    pending_escape = None
    closing = None
    previous_resize = None
    def resize(signum, frame):
        fcntl.ioctl(master, termios.TIOCSWINSZ,
                    fcntl.ioctl(terminal, termios.TIOCGWINSZ, b'\0' * 8))
    try:
        if threading.current_thread() is threading.main_thread():
            previous_resize = signal.signal(signal.SIGWINCH, resize)
        tty.setraw(terminal)
        while True:
            now = time.monotonic()
            if pending_escape is not None and now >= pending_escape:
                # Let less restore its screen/mouse modes through its normal
                # termination handler. Do not turn Escape into search text.
                os.killpg(pid, signal.SIGTERM)
                escaped = True
                closing = now + 1
                pending_escape = None
            if closing is not None and now >= closing:
                os.killpg(pid, signal.SIGKILL)
                closing = None
            deadline = pending_escape or closing
            timeout = max(0, deadline - now) if deadline is not None else None
            ready, _, _ = select.select([master] if escaped or cancelled else [master, terminal], [], [], timeout)
            if master in ready:
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    data = b''
                if not data:
                    break
                _write(terminal, data)
            if terminal in ready:
                data = os.read(terminal, 4096)
                if not data:
                    break
                if b'\x03' in data:
                    os.killpg(pid, signal.SIGTERM)
                    cancelled = True
                    closing = time.monotonic() + 1
                    pending_escape = None
                    continue
                if pending_escape is not None:
                    data = b'\x1b' + data
                    pending_escape = None
                if data.endswith(b'\x1b'):
                    data = data[:-1]
                    # Only a lone Escape closes. An arrow, mouse event or Alt
                    # chord arriving in this interval is forwarded unchanged.
                    pending_escape = time.monotonic() + .1
                _write(master, data)
        _, status = os.waitpid(pid, 0)
    finally:
        if status is None:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        if previous_resize is not None:
            signal.signal(signal.SIGWINCH, previous_resize)
        termios.tcsetattr(terminal, termios.TCSADRAIN, original)
        os.close(master)
    return 130 if cancelled else 0 if escaped else os.waitstatus_to_exitcode(status)
