#!/usr/bin/env python3
"""Real Tab acceptance in owned Bash/Zsh/Fish terminals, including live changes."""
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import termios
import time

from test_bash_dots import BASH, ZSH, FISH


class Terminal:
    def __init__(self, executable, env, cwd):
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
        def setup():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        flags = ['--noprofile', '--norc', '-i'] if executable == BASH else ['-dfi'] if executable == ZSH else ['--no-config', '-i']
        self.process = subprocess.Popen([executable, *flags], stdin=slave, stdout=slave,
                                        stderr=slave, cwd=cwd, env=env, preexec_fn=setup)
        os.close(slave)
        self.output = bytearray()

    def send(self, value):
        os.write(self.master, value.encode())

    def wait(self, marker, timeout=15):
        data = bytearray()
        deadline = time.monotonic() + timeout
        while marker not in data:
            if time.monotonic() >= deadline:
                raise AssertionError('PTY timeout: ' + data[-3000:].decode(errors='replace'))
            if select.select([self.master], [], [], .1)[0]:
                chunk = os.read(self.master, 65536)
                data.extend(chunk); self.output.extend(chunk)
                # Respond to cursor-position requests from interactive shells.
                if b'\x1b[6n' in chunk:
                    os.write(self.master, b'\x1b[1;1R')
        return bytes(data)

    def close(self):
        os.killpg(self.process.pid, signal.SIGTERM)
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait()
        os.close(self.master)


def exercise(fixture, executable):
    (fixture.home / 'marker').unlink(missing_ok=True)
    shell = 'bash' if executable == BASH else 'zsh' if executable == ZSH else 'fish'
    terminal = Terminal(executable, fixture.env, fixture.home)
    try:
        # Startup prompts differ; wait for our explicit initialization marker.
        if shell == 'bash':
            init = 'source "$DOTS/lib/dots/completion/bash"; PS1="READY> "; printf "\\nINITIALIZED\\n"'
        elif shell == 'zsh':
            init = 'autoload -Uz compinit; compinit -D; source "$DOTS/lib/dots/completion/zsh"; PROMPT="READY> "; printf "\\nINITIALIZED\\n"'
        else:
            init = 'source "$DOTS/lib/dots/completion/fish"; function fish_prompt; printf "READY> "; end; printf "\\nINITIALIZED\\n"'
        terminal.send(init + '\r')
        terminal.wait(b'INITIALIZED\r\n')
        # Each executed command records exactly what the shell actually passed.
        for typed, marker, expected in [
            ('dots themes --flavor m\t', b'mocha', 'mocha'),
            ('dots themes --flavor=m\t', b'mocha', '--flavor=mocha'),
            ('dots themes --pick two\t', b'words', 'two words'),
            ('dots themes --pick evil\t', b'marker', 'evil$(touch marker)'),
            ('dots themes folder\t', b'spaces', 'folder with spaces/'),
            ('dots themes "folder\t', b'spaces', 'folder with spaces/'),
        ]:
            capture = fixture.home / 'args'
            if capture.exists(): capture.unlink()
            terminal.send(typed)
            terminal.wait(marker)
            terminal.send(('"' if '"folder' in typed and shell != 'bash' else '') + '\r')
            terminal.wait(b'EXECUTED\r\n')
            args = capture.read_text().splitlines()
            assert args[-1].rstrip('/') == expected.rstrip('/'), (shell, args)
            assert not (fixture.home / 'marker').exists(), shell
        # Add a new command without reloading the adapter or restarting the shell.
        fixture.command('fresh', '# dots:summary=Fresh command', 'printf "LIVE_COMMAND\\n"')
        terminal.send('dots fre\t')
        terminal.wait(b'fresh')
        terminal.send('\r')
        terminal.wait(b'LIVE_COMMAND\r\n')
        for error in (b'bad pattern:', b'command not found:', b'Unknown command:'):
            assert error not in terminal.output, (shell, error)
    finally:
        (fixture.root / (shell + '-pty.log')).write_bytes(terminal.output)
        terminal.close()
