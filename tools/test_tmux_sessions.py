#!/usr/bin/env python3
"""Native shared t helper contracts; private socket, config, roots and PTY clients."""
import fcntl
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import struct
import subprocess
import termios
import time
import unittest

import test_shell_init


class TmuxSessions(unittest.TestCase):
    def setUp(self):
        self.tmux = shutil.which('tmux')
        if not self.tmux:
            self.skipTest('tmux unavailable; no native session verification')
        self.fixture = test_shell_init.InitTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.minimal_tools()
        self.root, self.repo, self.home, self.env = (
            getattr(self.fixture, key) for key in ('root', 'repo', 'home', 'env'))
        for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
            Path(self.env[key]).mkdir(parents=True, exist_ok=True)
        runtime = self.root / 'runtime'
        runtime.mkdir(mode=0o700)
        self.env.update(XDG_RUNTIME_DIR=str(runtime), TMUX_TMPDIR=str(runtime),
                        TERM='xterm-256color', LANG='C.UTF-8', LC_ALL='C.UTF-8')
        self.socket = runtime / 'tmux.sock'
        self.args = [self.tmux, '-S', str(self.socket), '-f', '/dev/null']
        self.clients = []
        # Registered before starting the server, including on assertion failure.
        self.addCleanup(self.stop_server)
        wrapper = self.root / 'tools/tmux'
        wrapper.write_text('#!' + shutil.which('bash') + '\nexec ' +
                           shlex.join(self.args) + ' "$@"\n')
        wrapper.chmod(0o700)
        self.functions = self.repo / 'shells/shared/functions.sh'
        self.cwd = self.home / 'start space ü'
        self.cwd.mkdir()
        self.other = self.home / 'other directory'
        self.other.mkdir()
        self.seed('Work-long', 'bash', self.home)
        self.control('set-option', '-g', 'default-shell', shutil.which('bash'))
        self.control('set-option', '-g', 'default-command',
                     shlex.join([shutil.which('bash'), '--noprofile', '--norc']))
        self.control('set-option', '-g', 'status', 'off')

    def control(self, *args, check=True):
        proc = subprocess.run(self.args + list(args), env=self.env, cwd=self.home,
                              capture_output=True, text=True, timeout=5)
        if check:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def stop_server(self):
        # Always explicitly address our socket; never use inherited TMUX/defaults.
        try:
            self.control('kill-server', check=False)
        finally:
            for proc, master in self.clients:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
                os.close(master)

    def shell_args(self, shell):
        exe = shutil.which(shell)
        if not exe:
            self.skipTest(shell + ' unavailable; no native verification')
        return [exe] + (['--noprofile', '--norc'] if shell == 'bash' else ['-df'])

    def seed(self, name, shell, cwd):
        self.control('new-session', '-d', '-s', name, '-c', str(cwd),
                     'exec ' + shlex.join(self.shell_args(shell)))

    def drain(self):
        for _, master in self.clients:
            while select.select([master], [], [], 0)[0]:
                try:
                    if not os.read(master, 65536):
                        break
                except OSError:
                    break

    def wait_for(self, predicate, description):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            self.drain()
            if predicate():
                return
            time.sleep(0.03)
        self.fail('timed out: ' + description)

    def session(self, name):
        return self.control('display-message', '-p', '-t', '=' + name + ':',
                            '#{session_id}\t#{pane_id}\t#{pane_current_path}').stdout.strip().split('\t')

    def sessions(self):
        return self.control('list-sessions', '-F', '#{session_name}').stdout.splitlines()

    def client_session(self):
        return self.control('list-clients', '-F', '#{session_name}').stdout.strip()

    def attach(self, shell, name=None, cwd=None, expected=None):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 100, 0, 0))
        code = 'source ' + shlex.quote(str(self.functions)) + '\nt'
        if name is not None:
            code += ' ' + shlex.quote(name)
        try:
            proc = subprocess.Popen(self.shell_args(shell) + ['-c', code],
                                    env=self.env, cwd=cwd or self.cwd,
                                    stdin=slave, stdout=slave, stderr=slave,
                                    start_new_session=True)
        except BaseException:
            os.close(master)
            raise
        finally:
            os.close(slave)
        self.clients.append((proc, master))
        self.wait_for(lambda: self.client_session() == (expected or name or 'Work'),
                      'client attached to exact session')
        self.assertIsNone(proc.poll())
        return proc

    def detach(self, proc):
        self.control('detach-client', '-s', '=' + self.client_session())
        self.wait_for(lambda: proc.poll() is not None, 'client exits after detach')
        self.assertEqual(proc.returncode, 0)

    def inside(self, source, target, marker, cwd, expected=None):
        pane = self.session(source)[1]
        code = ('builtin cd -- ' + shlex.quote(str(cwd)) + '; source ' +
                shlex.quote(str(self.functions)) + '; t' +
                (' ' + shlex.quote(target) if target is not None else '') +
                '; printf "%s\\n" "$?" > ' + shlex.quote(str(marker)))
        self.control('send-keys', '-t', pane, '-l', code)
        self.control('send-keys', '-t', pane, 'Enter')
        self.wait_for(lambda: marker.exists() and marker.read_text() == '0\n',
                      'inside t returns successfully')
        self.wait_for(lambda: self.client_session() == (expected or target), 'current client switches')

    def test_outside_exact_default_and_existing_names(self):
        for shell in ('bash', 'zsh'):
            with self.subTest(shell=shell):
                # Start the default case with Work-long but no Work, for each shell.
                if 'Work' in self.sessions():
                    self.control('kill-session', '-t', '=Work')
                before = self.session('Work-long')
                proc = self.attach(shell)
                created = self.session('Work')
                self.assertEqual(created[2], str(self.cwd))
                self.assertEqual(self.session('Work-long'), before)
                self.assertEqual(set(self.sessions()), {'Work-long', 'Work'})
                self.detach(proc)
                proc = self.attach(shell, cwd=self.other)
                self.assertEqual(self.session('Work'), created)
                self.assertEqual(set(self.sessions()), {'Work-long', 'Work'})
                self.detach(proc)
                for name in ('space session', 'équipe 日本', '-dash'):
                    proc = self.attach(shell, name)
                    original = self.session(name)
                    self.assertEqual(original[2], str(self.cwd))
                    self.detach(proc)
                    proc = self.attach(shell, name, self.other)
                    self.assertEqual(self.session(name), original)
                    self.assertEqual(self.sessions().count(name), 1)
                    self.detach(proc)
                    self.control('kill-session', '-t', '=' + name)

    def test_project_defaults_from_nested_repositories_and_worktrees(self):
        git = shutil.which('git')
        if not git:
            self.skipTest('Git unavailable; no native repository detection verification')
        (self.root / 'tools/git').symlink_to(git)
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        project = self.home / 'dots'
        project.mkdir()

        def run_git(*args):
            result = subprocess.run([git, '-c', 'core.hooksPath=' + os.devnull, *args],
                                    env=self.env, cwd=project, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)

        run_git('init', '-q', '-b', 'main')
        run_git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '-q', '--allow-empty', '--no-gpg-sign', '-m', 'test-owned fixture')
        linked = self.home / 'linked.worktree'
        run_git('worktree', 'add', '-q', '--detach', str(linked))
        for shell in ('bash', 'zsh'):
            for directory, name in ((project, 'dots'), (linked, 'linked-worktree')):
                with self.subTest(shell=shell, project=name):
                    nested = directory / 'src/nested'
                    nested.mkdir(parents=True, exist_ok=True)
                    proc = self.attach(shell, cwd=nested, expected=name)
                    created = self.session(name)
                    self.assertEqual(created[2], str(directory))
                    self.detach(proc)
                    proc = self.attach(shell, cwd=directory, expected=name)
                    self.assertEqual(self.session(name), created)
                    self.assertEqual(self.sessions().count(name), 1)
                    self.detach(proc)
                    proc = self.attach(shell, 'override', cwd=nested)
                    self.assertEqual(self.session('override')[2], str(nested))
                    self.detach(proc)
                    self.control('kill-session', '-t', '=override')
                    self.control('kill-session', '-t', '=' + name)
                    source = 'Source-project'
                    self.seed(source, shell, nested)
                    proc = self.attach(shell, source)
                    marker = self.home / 'project-result'
                    marker.unlink(missing_ok=True)
                    self.inside(source, None, marker, nested, expected=name)
                    self.assertEqual(self.session(name)[2], str(directory))
                    self.assertEqual(self.session(source)[2], str(nested))
                    self.detach(proc)
                    self.control('kill-session', '-t', '=' + name)
                    self.control('kill-session', '-t', '=' + source)

    def test_inside_creates_switches_and_reuses_exact_sessions(self):
        for shell in ('bash', 'zsh'):
            with self.subTest(shell=shell):
                source = 'Source-' + shell
                self.seed(source, shell, self.cwd)
                proc = self.attach(shell, source)
                source_state = self.session(source)
                prefix_state = self.session('Work-long')
                for number, name in enumerate(('Work', 'space session', 'équipe 日本', '-dash')):
                    # A successful function call must return to its original pane,
                    # not create a nested client or rename the source session.
                    marker = self.home / f'result-{shell}-{number}'
                    self.inside(source, name, marker, self.cwd)
                    created = self.session(name)
                    self.assertEqual(created[2], str(self.cwd))
                    self.assertEqual(self.session(source), source_state)
                    self.assertEqual(self.session('Work-long'), prefix_state)
                    self.assertEqual(self.control('list-clients', '-F', '#{client_name}').stdout.count('\n'), 1)
                    self.control('switch-client', '-t', '=' + source)
                    marker.unlink()
                    self.inside(source, name, marker, self.other)
                    self.assertEqual(self.session(source)[2], str(self.other))
                    self.assertEqual(self.session(name), created)
                    self.assertEqual(self.sessions().count(name), 1)
                    self.control('switch-client', '-t', '=' + source)
                    self.control('kill-session', '-t', '=' + name)
                self.detach(proc)
                self.control('kill-session', '-t', '=' + source)


if __name__ == '__main__':
    unittest.main()
