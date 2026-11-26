"""POSIX privilege handling with fake managers and a private controlling terminal."""
import io
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_workflows as fixtures
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error


# Only the platform and effective UID are simulated. Dispatch, planning, output
# and process execution use the ordinary CLI with a PATH containing only fixtures.
DRIVER = """
import sys
from unittest.mock import patch
from pkgs_lib.cli import main
with patch('pkgs_lib.backends.termux', return_value=False), patch('os.geteuid', return_value=1000):
    raise SystemExit(main(sys.argv[1:]))
"""

NATIVE = r"""
import getpass, json, os, sys, time
from pathlib import Path
program = Path(sys.argv[0]).name
args = sys.argv[1:]
mode = os.environ.get('TEST_SUDO_MODE', 'prompt')
with open(os.environ['TEST_PRIVILEGE_CALLS'], 'a') as log:
    print(json.dumps([program, *args]), file=log)

def challenge():
    print('PAM fixture notice', file=sys.stderr, flush=True)
    return getpass.getpass('Fixture authentication: ') == 'fixture-only-response'

if program == 'sudo':
    if args[:1] == ['-n']:
        args = args[1:]
        if mode != 'cached':
            print('sudo: a password is required', file=sys.stderr)
            sys.exit(1)
    elif mode != 'cached':
        if not challenge():
            print('Try again', file=sys.stderr, flush=True)
            if not challenge():
                sys.exit(1)
    if mode == 'interrupted':
        sys.exit(130)
    os.execvp(args[0], args)
elif program in ('yay', 'paru'):
    print(':: Synchronizing package databases...', flush=True)
    if not challenge():
        sys.exit(1)
elif program == 'apt':
    print('Unpacking sample (2) ...', file=sys.stderr, flush=True)
    sys.stderr.buffer.write(b'native output\xff\n')
    sys.stderr.flush()
    if mode == 'cached':
        sys.exit(0)
    with open('/dev/tty', 'w') as terminal:
        print('manager running', file=terminal, flush=True)
        time.sleep(.7)
        print('manager finished', file=terminal, flush=True)
"""


@unittest.skipIf(os.name == 'nt', 'sudo and a POSIX controlling terminal')
class SudoTransactions(unittest.TestCase):
    def setUp(self):
        fixtures.Workflows.setUp(self)
        self.calls = self.home / 'privilege-calls.jsonl'
        self.env.update(PYTHONPATH=str(fixtures.APP), TEST_PRIVILEGE_CALLS=str(self.calls),
                        TERM='xterm', DOTS_PROGRESS='spinner', NO_COLOR='1')
        for name in ('sudo', 'apt', 'apt-cache', 'dpkg-query', 'pacman', 'yay', 'paru'):
            path = self.bin / name
            path.write_text('#!' + sys.executable + '\n' + NATIVE)
            path.chmod(0o755)

    def commands(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def configure_bulk(self):
        path = Path(self.env['XDG_CONFIG_HOME']) / 'pkgs/config.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'upgrade': {'managers': ['apt', 'npm']}}))

    def detached(self, *words, mode='prompt'):
        return subprocess.run([sys.executable, '-B', '-c', DRIVER, *words], capture_output=True,
                              start_new_session=True, env=dict(self.env, TEST_SUDO_MODE=mode), timeout=10)

    def terminal(self, words, replies, *, mode='prompt', width=80):
        import fcntl
        import pty
        import struct
        import termios

        pid, fd = pty.fork()
        if pid == 0:
            try:
                fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                os.environ.update(self.env, TEST_SUDO_MODE=mode)
                before = termios.tcgetattr(0)
                from pkgs_lib.cli import main
                with patch('pkgs_lib.backends.termux', return_value=False), patch('os.geteuid', return_value=1000):
                    status = main(words)
                if termios.tcgetattr(0) != before:
                    raise AssertionError('terminal settings changed')
                os._exit(status)
            except BaseException as error:
                print(repr(error), file=sys.stderr, flush=True)
                os._exit(99)
        data = b''
        prompt = b'Fixture authentication: '
        waits = []
        deadline = time.monotonic() + 10
        waiting_since = None
        status = None
        try:
            while time.monotonic() < deadline:
                if select.select([fd], [], [], .04)[0]:
                    try:
                        chunk = os.read(fd, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    data += chunk
                if len(waits) < len(replies) and data.count(prompt) > len(waits):
                    if waiting_since is None:
                        waiting_since = time.monotonic()
                    # Hold input long enough for several renderer frames.
                    if time.monotonic() - waiting_since > .7:
                        waits.append(data.rpartition(prompt)[2])
                        os.write(fd, replies[len(waits)-1])
                        waiting_since = None
                ended, state = os.waitpid(pid, os.WNOHANG)
                if ended:
                    status = state
                    break
        finally:
            if status is None:
                ended, status = os.waitpid(pid, os.WNOHANG)
                if not ended:
                    os.killpg(pid, signal.SIGKILL)
                    status = os.waitpid(pid, 0)[1]
            os.close(fd)
        self.assertEqual(len(waits), len(replies), data)
        for segment in waits:
            self.assertNotIn(b'\x1b[2K', segment)
        self.assertNotIn(b'fixture-only-response', data)
        self.assertNotIn(b'wrong-fixture-response', data)
        return os.waitstatus_to_exitcode(status), data

    def test_system_manager_privilege_selection(self):
        with patch('pkgs_lib.backends.which', return_value='/fixture/bin/manager'), \
                patch('pkgs_lib.backends.termux', return_value=False):
            for manager in ('apt', 'pacman', 'dnf', 'xbps', 'paru', 'yay', 'npm', 'gem'):
                with self.subTest(manager=manager), patch('os.geteuid', return_value=1000):
                    command = Backend(manager).transaction('upgrade', ['sample'], True)
                    self.assertEqual(command[0] == 'sudo', manager in ('apt', 'pacman', 'dnf', 'xbps'))
                with patch('os.geteuid', return_value=0):
                    self.assertNotEqual(Backend(manager).transaction('upgrade', ['sample'], True)[0], 'sudo')
        with patch('pkgs_lib.backends.which', return_value=None), patch('pkgs_lib.backends.termux', return_value=False), \
                patch('os.geteuid', return_value=1000), self.assertRaisesRegex(Error, 'sudo is required'):
            Backend('apt').transaction('upgrade', [], True)

    def test_prompt_stays_visible_then_native_progress_resumes(self):
        rc, data = self.terminal(['up', '--manager', 'apt', '--yes'],
                                 [b'wrong-fixture-response\n', b'fixture-only-response\n'])
        self.assertEqual(rc, 0, data)
        active = data.partition(b'manager running')[2].partition(b'manager finished')[0]
        self.assertIn(b'apt', active)
        self.assertIn(b'\x1b[2K', active, 'progress should repaint while the native transaction runs')
        self.assertEqual(self.commands().count(['apt', 'upgrade', '-y', '--']), 1)

    def test_native_helper_prompt_and_raw_sudo(self):
        for manager, width in (('yay', 40), ('paru', 120)):
            with self.subTest(manager=manager):
                rc, data = self.terminal(['up', '--manager', manager], [b'fixture-only-response\n'], width=width)
                self.assertEqual(rc, 0, data)
                self.assertFalse(any(c[0] == 'sudo' for c in self.commands()))
        rc, data = self.terminal(['up', '--manager', 'apt', '--raw'], [b'fixture-only-response\n'])
        self.assertEqual(rc, 0, data)
        self.assertIn(b'native output\xff', data)

    def test_captured_prompt_keeps_native_pause_through_the_workflow(self):
        from pkgs_lib.upgrade_output import Output
        observer = Output('apt', self.cfg)
        with patch('pkgs_lib.workflows.pause') as pause:
            with observer.authenticating():
                observer.prompt('Continue? ', io.StringIO())
            pause.return_value.__exit__.assert_not_called()
            observer.close()
            pause.return_value.__exit__.assert_called_once()
            pause.assert_called_once()

    def test_detached_denial_cached_credentials_and_preview(self):
        preview = self.detached('up', '--manager', 'apt', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn(b'sudo apt upgrade', preview.stdout)
        self.assertEqual(self.commands(), [])
        self.configure_bulk()
        denied = self.detached('up')
        self.assertEqual(denied.returncode, 1, denied.stderr)
        self.assertIn(b'a password is required', denied.stderr)
        self.assertEqual(self.commands(), [['sudo', '-n', 'apt', 'upgrade', '-y', '--']])
        self.assertTrue((self.home/'calls.jsonl').exists(), 'independent npm manager should continue')
        cached = self.detached('up', '--manager', 'apt', '--raw', mode='cached')
        self.assertEqual(cached.returncode, 0, cached.stderr)
        self.assertEqual(cached.stderr, b'Unpacking sample (2) ...\nnative output\xff\n')
        self.assertEqual(self.commands()[-1], ['apt', 'upgrade', '-y', '--'])

    def test_no_terminal_uses_sudo_option_even_with_manager_n_flag(self):
        path = Path(self.env['XDG_CONFIG_HOME']) / 'pkgs/config.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'policies': {'apt': {'upgrade': {'flags': ['-n']}}}}))
        result = self.detached('up', '--manager', 'apt')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.commands(), [['sudo', '-n', 'apt', 'upgrade', '-y', '-n', '--']])

    def test_interrupt_stops_bulk_upgrade_without_followup_manager(self):
        self.configure_bulk()
        for mode, reply in (('prompt', b'\x03'), ('interrupted', b'fixture-only-response\n')):
            with self.subTest(mode=mode):
                rc, data = self.terminal(['up'], [reply], mode=mode)
                self.assertEqual(rc, 130, data)
                self.assertFalse((self.home/'calls.jsonl').exists())
                self.assertFalse(any(c[0] == 'apt' for c in self.commands()))
