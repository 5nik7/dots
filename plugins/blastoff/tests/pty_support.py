"""Small POSIX PTY driver: real controlling terminal, bounded waits, no profiles."""
import errno
import os
import re
import select
import signal
import time


def terminal(command, env, keys=b'', ready=b'', columns=40, rows=16, timeout=12, followup=None, resize=None):
    import fcntl
    import pty
    import struct
    import termios
    pid, fd = pty.fork()
    if pid == 0:
        # Background launchers may ignore SIGINT; a fresh foreground terminal
        # must start with normal signal dispositions, as an interactive shell does.
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGQUIT, signal.SIG_DFL)
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', rows, columns, 0, 0))
        os.execve(command[0], command, env)
    output = bytearray()
    queries = b''
    # Conservative terminal replies, not screen emulation or visual evidence.
    replies = [(rb'\x1b\[6n', b'\x1b[1;1R'),
               (rb'\x1b\[(?:0)?c', b'\x1b[?1;2c'),
               (rb'\x1b\[>0c', b'\x1b[>0;0;0c'),
               (rb'\x1b\[\?u', b'\x1b[?0u'),
               (rb'\x1b\[>0q', b'\x1bP>|blastoff-test-pty\x1b\\'),
               (rb'\x1b\]11;\?(?:\x07|\x1b\\)', b'\x1b]11;rgb:0000/0000/0000\x1b\\'),
               (rb'\x1bP\+q[0-9a-fA-F;]+\x1b\\', b'\x1bP0+r\x1b\\')]
    sent = False
    status = None
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            readable, _, _ = select.select([fd], [], [], 0.05)
            if readable:
                try:
                    chunk = os.read(fd, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    chunk = b''
                output.extend(chunk)
                # Fish negotiates capabilities before its first prompt. Retain
                # partial query bytes across reads; never rely on startup sleeps.
                queries += chunk
                for pattern, reply in replies:
                    for match in re.finditer(pattern, queries):
                        os.write(fd, reply)
                    queries = re.sub(pattern, b'', queries)
                queries = queries[-256:]
                if resize and resize[0] in output:
                    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH',resize[2],resize[1],0,0))
                    os.killpg(pid,signal.SIGWINCH)
                    resize=None
                if not sent and ready in output:
                    if keys:
                        os.write(fd, keys)
                    sent = True
                if sent and followup and followup[0] in output:
                    os.write(fd, followup[1])
                    followup = None
            done, value = os.waitpid(pid, os.WNOHANG)
            if done:
                status = value
                break
        if status is None:
            raise AssertionError('PTY timeout; tail=' + repr(bytes(output[-1500:])))
        return os.waitstatus_to_exitcode(status), bytes(output)
    finally:
        if status is None:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        os.close(fd)
