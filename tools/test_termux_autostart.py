#!/usr/bin/env python3
"""Bash/Zsh startup with simulated Termux identity and private native tmux."""
import os
from pathlib import Path
import pty
import shlex
import shutil
import subprocess
import sys
import unittest

import test_tmux_sessions


REPO = Path(__file__).resolve().parents[1]


class TermuxAutostart(unittest.TestCase):
    def setUp(self):
        self.fx = test_tmux_sessions.TmuxSessions()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.bin = self.fx.repo / 'profiles/termux/bin'
        self.bin.mkdir(parents=True)
        shutil.copy2(REPO / 'profiles/termux/bin/termux-bar', self.bin / 'bar-source')
        # Run the real launcher with fixture procfs. No real Termux discovery.
        (self.bin / 'termux-bar').write_text('''import os, pathlib, runpy
root = pathlib.Path(os.environ['HOME']) / 'proc'
pid = os.getppid()
directory = root / str(pid)
directory.mkdir(parents=True, exist_ok=True)
fields = ['S', '123', str(pid), str(pid)] + ['0'] * 15 + ['456']
(directory / 'stat').write_text(str(pid) + ' (fixture shell) ' + ' '.join(fields))
namespace = runpy.run_path(str(pathlib.Path(__file__).with_name('bar-source')))
raise SystemExit(namespace['main'](proc_root=root))
''')
        (self.bin / 'termux-sessions').write_text('''import sys
assert sys.argv[1:4] == ['--get', 'pid', '--pid']
print(sys.argv[4])
''')
        if not (self.fx.root / 'tools/python3').exists():
            (self.fx.root / 'tools/python3').symlink_to(sys.executable)
        self.fx.env.update(DOTS_PLATFORM='termux', TERMUX_APP__PID='123')
        self.hook = self.fx.repo / 'shells/shared/termux-tmux.sh'

    def start(self, shell, code, **changes):
        master, slave = pty.openpty()
        try:
            proc = subprocess.Popen(self.fx.shell_args(shell) + ['-i', '-c', code],
                                    env=dict(self.fx.env, **changes), cwd=self.fx.cwd,
                                    stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        finally:
            os.close(slave)
        self.fx.clients.append((proc, master))
        return proc

    def test_auto_attach_detach_reload_and_manual_reattach(self):
        for shell in ('bash', 'zsh'):
            with self.subTest(shell=shell):
                resumed = self.fx.home / ('resumed-' + shell)
                reattach = self.fx.home / ('reattach-' + shell)
                done = self.fx.home / ('done-' + shell)
                code = ('source ' + shlex.quote(str(self.hook)) + '\n' +
                        'source ' + shlex.quote(str(self.hook)) + '\n' +
                        'printf resumed > ' + shlex.quote(str(resumed)) + '\n' +
                        'read -r _fixture_wait\n' +
                        'printf reattach > ' + shlex.quote(str(reattach)) + '\n' +
                        'command python3 -B ' + shlex.quote(str(self.bin / 'termux-bar')) + '\n' +
                        'printf done > ' + shlex.quote(str(done)))
                proc = self.start(shell, code)
                name = f'termux-{proc.pid}-456'
                self.fx.wait_for(lambda: self.fx.client_session() == name, 'auto attachment')
                original = self.fx.session(name)
                self.assertEqual(original[2], str(self.fx.cwd))
                self.assertEqual(self.fx.control('show-options', '-qv', '-t', '=' + name + ':',
                                                '@dots-termux-default').stdout.strip(), '1')
                # Project helper switches this same client, without nested tmux.
                switched = self.fx.home / ('switched-' + shell)
                self.fx.inside(name, 'dots', switched, self.fx.cwd)
                self.assertEqual(self.fx.control('show-options', '-qv', '-t', '=dots:',
                                                '@dots-termux-default').stdout.strip(), '')
                self.fx.control('switch-client', '-t', '=' + name)
                self.fx.control('detach-client', '-s', '=' + name)
                self.fx.wait_for(resumed.exists, 'outer shell survives detach and reload')
                self.assertIsNone(proc.poll())
                self.assertEqual(self.fx.client_session(), '')
                os.write(self.fx.clients[-1][1], b'\n')
                self.fx.wait_for(lambda: reattach.exists() and self.fx.client_session() == name,
                                 'manual reattachment')
                self.assertEqual(self.fx.session(name), original)
                self.fx.control('detach-client', '-s', '=' + name)
                self.fx.wait_for(lambda: proc.poll() is not None, 'outer shell exits normally')
                self.assertEqual(proc.returncode, 0)
                self.assertTrue(done.exists())

    def test_two_tabs_are_independent(self):
        first = self.start('bash', 'source ' + shlex.quote(str(self.hook)))
        second = self.start('zsh', 'source ' + shlex.quote(str(self.hook)))
        names = {f'termux-{process.pid}-456' for process in (first, second)}
        self.fx.wait_for(lambda: set(self.fx.client_session().splitlines()) == names,
                         'independent default sessions for both tabs')
        panes = [self.fx.session(name)[1] for name in names]
        self.assertEqual(len(set(panes)), 2)
        self.fx.control('set-option', '-g', 'detach-on-destroy', 'on')
        self.fx.control('send-keys', '-t', self.fx.session(f'termux-{first.pid}-456')[1], 'exit', 'Enter')
        self.fx.wait_for(lambda: first.poll() is not None, 'first tab exits independently')
        self.assertIsNone(second.poll())
        self.assertEqual(self.fx.client_session(), f'termux-{second.pid}-456')

    def test_last_session_exit_closes_outer_shell(self):
        resumed = self.fx.home / 'last-session-resumed'
        proc = self.start('bash', 'source ' + shlex.quote(str(self.hook)) + '\n' +
                          'printf resumed > ' + shlex.quote(str(resumed)))
        name = f'termux-{proc.pid}-456'
        self.fx.wait_for(lambda: self.fx.client_session() == name, 'initial attachment')
        self.fx.control('kill-session', '-t', '=Work-long')
        self.fx.control('kill-session', '-t', '=' + name)
        self.fx.wait_for(lambda: proc.poll() is not None, 'outer shell finishes after last session exits')
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(resumed.exists())

    def test_exit_and_q_close_only_final_pane_and_its_tab(self):
        self.fx.control('set-option', '-g', 'detach-on-destroy', 'on')
        for shell in ('bash', 'zsh'):
            for project in (False, True):
                with self.subTest(shell=shell, project=project):
                    resumed = self.fx.home / f'resumed-{shell}-{project}'
                    proc = self.start(shell, 'source ' + shlex.quote(str(self.hook)) + '\n'
                                      + 'printf resumed > ' + shlex.quote(str(resumed)))
                    name = f'termux-{proc.pid}-456'
                    self.fx.wait_for(lambda: self.fx.client_session() == name, 'automatic attachment')
                    if project:
                        target = f'project-{shell}'
                        self.fx.seed(target, shell, self.fx.home)
                        self.fx.control('switch-client', '-t', '=' + target)
                    else:
                        target = name
                    first = self.fx.session(target)[1]
                    second = self.fx.control('split-window', '-d', '-P', '-F', '#{pane_id}', '-t', first,
                                             'exec ' + shlex.join(self.fx.shell_args(shell))).stdout.strip()
                    self.fx.control('send-keys', '-t', second, 'exit', 'Enter')
                    self.fx.wait_for(lambda: len(self.fx.control('list-panes', '-t', '=' + target).stdout.splitlines()) == 1,
                                     'exit closes only one pane')
                    self.assertIsNone(proc.poll())
                    self.fx.control('send-keys', '-t', first, "alias q=exit", 'Enter')
                    self.fx.control('send-keys', '-t', first, 'q', 'Enter')
                    self.fx.wait_for(lambda: proc.poll() is not None, 'q exits final pane and outer shell')
                    self.assertEqual(proc.returncode, 0)
                    self.assertFalse(resumed.exists())
                    self.assertIn('Work-long', self.fx.sessions())
                    if project:
                        self.assertIn(name, self.fx.sessions())

    def test_unexpected_server_loss_returns_to_shell(self):
        resumed = self.fx.home / 'server-loss-resumed'
        proc = self.start('zsh', 'source ' + shlex.quote(str(self.hook)) + '\n'
                          + 'printf resumed > ' + shlex.quote(str(resumed)))
        self.fx.wait_for(lambda: self.fx.client_session() == f'termux-{proc.pid}-456', 'attachment')
        self.fx.control('kill-server')
        self.fx.wait_for(lambda: proc.poll() is not None, 'server loss returns to outer shell')
        self.assertTrue(resumed.exists())

    def test_first_tab_starts_a_private_server(self):
        # Cold startup must also work, without reading the owner's tmux config.
        config = self.fx.root / 'cold.conf'
        config.write_text('set -g default-shell ' + shlex.quote(shutil.which('bash')) + '\n' +
                          'set -g default-command ' + shlex.quote('exec ' +
                          shlex.join(self.fx.shell_args('bash'))) + '\n')
        args = [*self.fx.args[:-1], str(config)]
        (self.fx.root / 'tools/tmux').write_text('#!' + shutil.which('bash') + '\nexec ' +
                                                shlex.join(args) + ' "$@"\n')
        self.fx.control('kill-server')
        proc = self.start('bash', 'source ' + shlex.quote(str(self.hook)))
        name = f'termux-{proc.pid}-456'
        self.fx.wait_for(lambda: self.fx.control('list-clients', '-F', '#{session_name}',
                                                 check=False).stdout.strip() == name,
                         'cold server attachment')
        self.assertEqual(self.fx.sessions(), [name])
        self.assertEqual(self.fx.control('show-options', '-qv', '-t', '=' + name + ':',
                                        '@dots-termux-default').stdout.strip(), '1')

    def test_shell_guards_and_failure_leave_plain_shell(self):
        # A sentinel launcher verifies no dependency is invoked for skipped cases.
        calls = self.fx.home / 'launcher-calls'
        (self.bin / 'termux-bar').write_text(
            'from pathlib import Path\nimport os, sys\n' +
            'Path(os.environ["HOME"], "launcher-calls").write_text("called")\nsys.exit(1)\n')
        for shell in ('bash', 'zsh'):
            for env in ({'TMUX': 'already'}, {'SSH_CONNECTION': 'remote'}, {'SSH_CLIENT': 'remote'},
                        {'SSH_TTY': '/dev/pts/9'}, {'DOTS_PLATFORM': 'linux'},
                        {'DOTS_TERMUX_AUTOSTART': '0'}, {'TERMUX_APP__PID': ''}):
                with self.subTest(shell=shell, env=env):
                    proc = self.start(shell, 'source ' + shlex.quote(str(self.hook)), **env)
                    self.fx.wait_for(lambda: proc.poll() is not None, 'guarded shell exits')
                    self.assertEqual(proc.returncode, 0)
                    self.assertFalse(calls.exists())
            proc = self.start(shell, 'source ' + shlex.quote(str(self.hook)))
            self.fx.wait_for(lambda: proc.poll() is not None, 'failed launcher returns to shell')
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(calls.exists())
            calls.unlink()
            for args in (['-c'], ['-i', '-c']):
                # Redirected interactive and noninteractive shell startup both skip.
                result = subprocess.run(self.fx.shell_args(shell) + args +
                                        ['source ' + shlex.quote(str(self.hook))],
                                        env=self.fx.env, cwd=self.fx.home, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0)
                self.assertFalse(calls.exists())


class FullStartup(unittest.TestCase):
    def test_cold_warm_fallback_and_integration_order(self):
        sys.path.insert(0, str(REPO / 'lib/dots'))
        from debug.fixtures import fixture
        for shell in ('bash', 'zsh'):
            if not shutil.which(shell):
                continue
            with self.subTest(shell=shell), fixture(REPO) as (repo, env, base):
                env.update(DOTS_TERMUX_AUTOSTART='1', TERMUX_VERSION='fixture', TERMUX_APP__PID='123')
                # Observe the real loader boundary without loading plugins or
                # starting a tmux server. The launcher remains an owned stub.
                debug = repo / 'lib/dots/shell/debug.bash'
                with debug.open('a') as out:
                    out.write('\n_dots_debug_event() { if [[ $1:$2:$3 == end:startup:phase ]]; then export FIXTURE_STARTUP_ENDED=1; fi; return 0; }\n')
                hook = repo / 'shells/shared/termux-tmux.sh'
                hook.write_text('[[ ${FIXTURE_STARTUP_ENDED:-} == 1 && -z ${_dots_startup_shell+x} ]] || return 33\n' + hook.read_text())
                launcher = repo / 'profiles/termux/bin/termux-bar'
                launcher.parent.mkdir(parents=True)
                launcher.write_text('import os,pathlib\nassert os.environ["FIXTURE_STARTUP_ENDED"] == "1"\n'
                                    'with pathlib.Path(os.environ["HOME"],"calls").open("a") as f:f.write("launch\\n")\n')
                calls = Path(env['HOME']) / 'calls'
                flags = ['--noprofile', '--norc'] if shell == 'bash' else ['-df']
                code = '_DOTS_STARTUP_MODE=full; source "$DOTS/lib/dots/shell/startup.bash"; source "$DOTS/lib/dots/shell/startup.bash"'
                def run(code):
                    master, slave = pty.openpty()
                    try:
                        process = subprocess.Popen([shutil.which(shell), *flags, '-ic', code], env=env,
                                                   stdin=slave, stdout=slave, stderr=subprocess.PIPE)
                        _, err = process.communicate(timeout=30)
                        self.assertEqual(process.returncode, 0, err.decode())
                        return err
                    finally:
                        os.close(slave)
                        os.close(master)
                for count in (1, 2):
                    error = run(code)
                    self.assertNotIn(b'preparation unavailable', error)
                    self.assertEqual(calls.read_text().splitlines(), ['launch'] * count)
                # Preparation failure still reaches a guarded, usable shell.
                (repo / 'lib/dots/startup.py').write_text('raise SystemExit(1)\n')
                error = run(code)
                self.assertIn(b'preparation unavailable', error)
                self.assertEqual(calls.read_text().splitlines(), ['launch'] * 3)
                run('source "$DOTS/lib/dots/shell/startup.bash"')
                self.assertEqual(calls.read_text().splitlines(), ['launch'] * 3)


if __name__ == '__main__':
    unittest.main()
