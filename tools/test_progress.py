#!/usr/bin/env python3
"""Native PTY progress contracts. All command roots and homes are disposable."""
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

import test_file_operations as file_fixtures
import test_git_operations as git_fixtures

PROJECT = Path(__file__).resolve().parents[1]
LIB = PROJECT / 'lib/dots'
BASH = shutil.which('bash')
ANSI = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]')


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-progress-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home space ü'
        self.home.mkdir()
        self.env = dict(PATH=os.environ['PATH'], HOME=str(self.home), TERM='xterm-256color',
                        DOTS_COLOR='always', DOTS_ICONS='never', TMPDIR=str(self.root),
                        PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(LIB), DOTS_PROGRESS='auto')
        for kind in ('CONFIG', 'CACHE', 'STATE', 'DATA'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / kind.lower())
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']

    def bash(self, body):
        return [BASH, '--noprofile', '--norc', '-c',
                'source ' + shlex.quote(str(LIB / 'ui.bash')) + '; source ' +
                shlex.quote(str(LIB / 'progress.bash')) + '; DOTS_PROGRESS_HUMAN=1; ' + body]

    def python(self, body):
        return [sys.executable, '-B', '-c', 'import progress, time, sys, os\nprogress.configure()\n' + body]

    def fixture_env(self, fixture, **settings):
        env = dict(fixture.env, PYTHONPATH=str(LIB), TERM='xterm-256color',
                   DOTS_COLOR='always', DOTS_ICONS='never', DOTS_PROGRESS='auto',
                   TMPDIR=str(fixture.base), PYTHONDONTWRITEBYTECODE='1')
        for kind in ('CONFIG', 'CACHE', 'STATE', 'DATA', 'RUNTIME'):
            env['XDG_' + kind + ('_DIR' if kind == 'RUNTIME' else '_HOME')] = str(fixture.home / ('.' + kind.lower()))
        env.update(settings)
        return env

    def terminal(self, argv, env=None, width=80, interrupt=False):
        pid, fd = pty.fork()
        if not pid:
            os.chdir(self.home)
            os.execve(argv[0], argv, env or self.env)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
        data = b''
        started = time.monotonic()
        sent = False
        ended = False
        try:
            while time.monotonic() - started < 12:
                if interrupt and not sent and b'Waiting' in data:
                    if interrupt == 'term':
                        os.kill(pid, signal.SIGTERM)
                    else:
                        os.write(fd, b'\x03')
                    sent = True
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        block = os.read(fd, 65536)
                    except OSError:
                        ended = True
                        break
                    if not block:
                        ended = True
                        break
                    data += block
            self.assertTrue(ended, ('PTY/worker did not close', data))
        finally:
            if not ended:
                os.killpg(pid, signal.SIGKILL)
            _, status = os.waitpid(pid, 0)
            os.close(fd)
        return os.waitstatus_to_exitcode(status), data

    def test_delayed_spinner_and_counted_phases(self):
        commands = [self.bash("dots::progress_start Scanning; sleep 0.65; dots::progress_update Copying 1 3; sleep 0.2; dots::progress_stop; echo done"),
                    self.python("with progress.Progress('Scanning'):\n time.sleep(.65)\n progress.report('Copying',1,3)\n time.sleep(.2)\nprint('done')")]
        for command in commands:
            code, data = self.terminal(command)
            self.assertEqual(code, 0, data)
            self.assertIn(b'Scanning', data)
            self.assertIn(b'1/3', data)
            self.assertIn(b'Copying', data)
            self.assertIn(b'\x1b[96m', data)
            self.assertTrue(data.endswith(b'done\r\n'), data)

    def test_fast_commands_are_silent(self):
        for command in [self.bash('dots::progress_run Fast true; echo done'),
                        self.python("with progress.Progress('Fast'): pass\nprint('done')")]:
            self.assertEqual(self.terminal(command), (0, b'done\r\n'))

    def test_disabled_modes_and_redirection(self):
        commands = [self.bash('dots::progress_run Hidden sleep 0.65; echo done'),
                    self.python("with progress.Progress('Hidden'): time.sleep(.65)\nprint('done')")]
        for command in commands:
            for settings in (dict(DOTS_PROGRESS='never'), dict(DOTS_PROGRESS='invalid'), dict(TERM='dumb')):
                self.assertEqual(self.terminal(command, dict(self.env, **settings)), (0, b'done\r\n'))
            result = subprocess.run(command, env=self.env, cwd=self.home, capture_output=True, timeout=5)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'done\n', b''))
        # A terminal on stderr alone does not opt a redirected data stream in.
        code, data = self.terminal(self.bash('exec > "$HOME/output"; dots::progress_run Hidden sleep .65; echo data'))
        self.assertEqual((code, data), (0, b''))
        self.assertEqual((self.home / 'output').read_text(), 'data\n')

    def test_policy_and_width(self):
        label = 'Long ' + 'x' * 160 + '\x1b[31m\n-dash ü 界'
        commands = [self.bash('dots::progress_run ' + shlex.quote(label) + ' sleep .65'),
                    self.python('with progress.Progress(' + repr(label) + '): time.sleep(.65)')]
        for command in commands:
            for width in (40, 80, 120):
                code, data = self.terminal(command, dict(self.env, DOTS_COLOR='auto', NO_COLOR='1'), width)
                self.assertEqual(code, 0, data)
                self.assertNotIn(b'\x1b', data)
                self.assertTrue(all(len(line) < width for line in data.split(b'\r')), data)
            self.assertIn(b'\x1b[96m', self.terminal(command, dict(self.env, NO_COLOR='1'))[1])
        for command in [self.bash("dots::progress_run $'Bad\\e[31m\\nName' sleep .65"),
                        self.python("with progress.Progress('Bad\\x1b[31m\\nName'): time.sleep(.65)")]:
            _, data = self.terminal(command, dict(self.env, DOTS_COLOR='never'))
            self.assertNotIn(b'\x1b', data)
            self.assertNotIn(b'\n', data)
            self.assertIn(b'Name', data)

    def test_status_and_prompt_suspension(self):
        code, data = self.terminal(self.bash("work() { sleep .65; return 7; }; dots::progress_run Working work; rc=$?; echo result:$rc; exit $rc"))
        self.assertEqual(code, 7, data)
        self.assertTrue(data.endswith(b'result:7\r\n'), data)
        code, data = self.terminal(self.bash("dots::progress_start Inspecting; sleep .65; dots::progress_external Credentials; echo 'Prompt:'; sleep .3; echo done"))
        self.assertEqual(code, 0, data)
        self.assertEqual(data.split(b'Prompt:\r\n')[1], b'done\r\n')

    def test_unicode_markers_and_optional_width_tool(self):
        commands = [self.bash('dots::progress_start Copying 1 3; sleep .65; dots::progress_stop'),
                    self.python("with progress.Progress('Copying'):\n progress.report('Copying',1,3)\n time.sleep(.65)")]
        for command in commands:
            code, data = self.terminal(command, dict(self.env, DOTS_ICONS='always'))
            self.assertEqual(code, 0, data)
            self.assertIn('━'.encode(), data)
        code, data = self.terminal(self.bash("command() { [[ $* != '-v stty' ]] || return 1; builtin command \"$@\"; }; COLUMNS=40; dots::progress_run Copying sleep .65"))
        self.assertEqual(code, 0, data)
        self.assertIn(b'Copying', data)

    def test_interrupt_and_parent_exit_cleanup(self):
        commands = [self.bash("trap 'exit 130' INT; dots::progress_run Waiting sleep 5"),
                    self.python("try:\n with progress.Progress('Waiting'): time.sleep(5)\nexcept KeyboardInterrupt: sys.exit(130)")]
        for command in commands:
            code, data = self.terminal(command, interrupt=True)
            self.assertEqual(code, 130, data)
            self.assertIn(b'Waiting', data)
        code, data = self.terminal(self.bash('dots::progress_start Waiting; sleep .65; exit 9'))
        self.assertEqual(code, 9, data)
        code, data = self.terminal(self.python("with progress.Progress('Waiting'): time.sleep(5)"), interrupt='term')
        self.assertEqual(code, -signal.SIGTERM, data)
        self.assertTrue(data.endswith(b'\r'), data)

    def test_nested_calls_and_renderer_failure(self):
        code, data = self.terminal(self.bash("inner() { sleep .65; }; outer() { dots::progress_run Inner inner; }; dots::progress_run Outer outer; echo done"))
        self.assertEqual(code, 0, data)
        self.assertIn(b'Inner', data)
        code, data = self.terminal(self.bash("dots::progress_start Waiting; sleep .65; kill \"$DOTS_PROGRESS_PID\"; wait \"$DOTS_PROGRESS_PID\"; dots::progress_update Still 1 2; dots::progress_stop; echo done"))
        self.assertEqual(code, 0, data)
        self.assertTrue(data.endswith(b'done\r\n'), data)
        body = """with progress.Progress('Outer') as outer:
 with progress.Progress('Inner') as inner:
  assert inner is outer
  progress.report('Preparing', 0, 2)
  time.sleep(.65)
 assert progress._current is outer
assert progress._current is None
print('done')
"""
        self.assertEqual(self.terminal(self.python(body))[0], 0)

    def test_file_transaction_progress_and_rollback(self):
        for fail in (False, True):
            fixture = file_fixtures.Operations()
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            env = self.fixture_env(fixture)
            before = fixture.path.read_bytes()
            # Delay real journal writes in a disposable transaction, then inject
            # failure after replacement to check that reporting cannot own undo.
            body = '''import sys, time
sys.path.insert(0, sys.argv.pop(1))
import manage, transactions
save = transactions.Store.save
failed = False
def slow_save(self, doc):
 global failed
 save(self, doc)
 time.sleep(.12)
 if FAIL and not failed and any(e['phase']=='done' for e in doc['operations']):
  failed = True
  raise ValueError('injected failure')
transactions.Store.save = slow_save
try:
 manage.main()
except ValueError as error:
 print(error, file=sys.stderr)
 sys.exit(1)
'''.replace('FAIL', repr(fail))
            command = [sys.executable, '-B', '-c', body, str(LIB / 'files'), 'add', str(fixture.path), '--yes']
            code, data = self.terminal(command, env)
            self.assertEqual(code, int(fail), data)
            self.assertIn(b'Preparing files', data)
            self.assertIn(b'Applying files', data)
            self.assertRegex(ANSI.sub(b'', data), rb'\d+/\d+')
            if fail:
                self.assertEqual(fixture.path.read_bytes(), before)
                self.assertIn(b'Rolling back files', data)
                self.assertTrue(data.endswith(b'injected failure\r\n'), data)
            else:
                self.assertIn(b'File operation complete', ANSI.sub(b'', data))

    def test_json_and_dry_run_controllers_disable_progress(self):
        fixture = file_fixtures.Operations()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        env = self.fixture_env(fixture, DOTS_ICONS='always')
        # Guard the worker boundary, not output substrings: these paths must
        # never launch animation even with real terminal streams.
        body = '''import sys
sys.path.insert(0, sys.argv.pop(1))
import progress, manage
def forbidden(self):
 raise AssertionError('progress started for data/preview')
progress.threading.Thread.start = forbidden
manage.main()
'''
        for flags in (['--json', '--yes'], ['--dry-run']):
            command = [sys.executable, '-B', '-c', body, str(LIB / 'files'), 'add', str(fixture.path), *flags]
            code, data = self.terminal(command, env)
            self.assertEqual(code, 0, data)

    def test_git_status_progress_and_data_output(self):
        fixture = git_fixtures.GitOperations()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        repo = fixture.repo('status space ü')
        tools = self.root / 'tools'
        tools.mkdir()
        git = tools / 'git'
        git.write_text('#!' + BASH + '\nfor arg; do [[ $arg != status ]] || sleep .7; done\nexec ' +
                       shlex.quote(shutil.which('git')) + ' "$@"\n')
        git.chmod(0o700)
        env = self.fixture_env(fixture, PATH=str(tools) + os.pathsep + self.env['PATH'])
        command = [BASH, str(PROJECT / 'bin/dots'), 'git', 'status', '-C', str(repo)]
        code, data = self.terminal(command, env)
        self.assertEqual(code, 0, data)
        self.assertIn(b'Inspecting repositories', data)
        self.assertIn(b'0/1', data)
        self.assertIn(b'clean', data)
        for settings in (env, dict(env, DOTS_PROGRESS='never')):
            code, data = self.terminal(command + ['--json'], settings)
            self.assertEqual(code, 0, data)
            self.assertNotIn(b'\x1b', data)
            self.assertNotIn(b'Inspecting repositories', data)
            self.assertEqual(len(json.loads(data)['repositories']), 1)


if __name__ == '__main__':
    unittest.main()
