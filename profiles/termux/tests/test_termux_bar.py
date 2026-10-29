#!/usr/bin/env python3
"""Launcher failure and identity contracts; all process/tmux access is mocked."""
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch


BAR = Path(__file__).resolve().parents[1] / 'bin/termux-bar'
MODULE = runpy.run_path(str(BAR))
# Functions retain run_path's execution globals, rather than the returned copy.
G = MODULE['main'].__globals__


def result(code=0, out=''):
    return subprocess.CompletedProcess([], code, out, '')


class TermuxBar(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='termux-bar-test-')
        self.addCleanup(temp.cleanup)
        self.proc = Path(temp.name)
        self.stat(42, parent=10, sid=42, start=1234)

    def stat(self, pid, parent, sid, start):
        directory = self.proc / str(pid)
        directory.mkdir(exist_ok=True)
        fields = ['S', str(parent), str(pid), str(sid)] + ['0'] * 15 + [str(start)]
        (directory / 'stat').write_text(f'{pid} (shell (with spaces)) ' + ' '.join(fields))

    def test_identity_reuse_and_pid_recycling(self):
        with patch('subprocess.run', return_value=result(out='42\n')) as run:
            name = G['default_session'](True, {'TERMUX_APP__PID': '10'}, 42, self.proc)
            self.assertEqual(name, 'termux-42-1234')
            self.assertEqual(run.call_args.args[0][-4:], ['--get', 'pid', '--pid', '42'])
            self.stat(42, parent=10, sid=42, start=9999)
            self.assertNotEqual(name, G['default_session'](True, {'TERMUX_APP__PID': '10'}, 42, self.proc))

    def test_child_shell_skips_before_discovery(self):
        self.stat(43, parent=42, sid=42, start=5678)
        with patch('subprocess.run') as run:
            self.assertIsNone(G['default_session'](True, {'TERMUX_APP__PID': '10'}, 43, self.proc))
            run.assert_not_called()
        with patch('subprocess.run', return_value=result(out='42\n')):
            self.assertEqual(G['default_session'](False, {'TERMUX_APP__PID': '10'}, 43, self.proc),
                             'termux-42-1234')

    def test_discovery_failure_and_changed_identity(self):
        for response in [result(1), result(out='42\n43\n'), result(out='-1'), result(out='0')]:
            with patch('subprocess.run', return_value=response):
                with self.assertRaises(G['BarError']):
                    G['default_session'](True, {'TERMUX_APP__PID': '10'}, 42, self.proc)
        self.stat(42, parent=99, sid=42, start=1234)
        with patch('subprocess.run', return_value=result(out='42')):
            with self.assertRaises(G['BarError']):
                G['default_session'](False, {'TERMUX_APP__PID': '10'}, 42, self.proc)

    def test_existing_session_collision_and_creation_race(self):
        import contextlib
        import types
        workspaces = unittest.mock.Mock()
        workspaces.locked.side_effect = lambda: contextlib.nullcontext()
        workspaces.sessions.return_value = ['$7']
        workspaces.metadata.return_value = {'origin': '42-1234'}
        workspaces.read.return_value = '$7'
        factory = unittest.mock.Mock(side_effect=ValueError('no server running'))
        module = types.SimpleNamespace(Workspaces=factory)
        with patch.dict('sys.modules', tmux_workspaces=module), patch('subprocess.run', return_value=result(out='')) as run:
            with self.assertRaises(G['BarError']):
                G['ensure_session']('tmux', 'termux-42-1234')
            self.assertEqual(run.call_count, 2)
        factory.side_effect = [ValueError('no server running'), workspaces]
        with patch.dict('sys.modules', tmux_workspaces=module), \
                patch('subprocess.run', side_effect=[result(1), result(1), result(out='1\n')]):
            self.assertEqual(G['ensure_session']('tmux', 'termux-42-1234'), '$7')
            workspaces.reconcile.assert_called_once_with(adopt=True, session='$7')
        factory.side_effect = ValueError('no server running')
        with patch.dict('sys.modules', tmux_workspaces=module), \
                patch('subprocess.run', side_effect=[result(1), result(1), result(1)]):
            with self.assertRaises(G['BarError']):
                G['ensure_session']('tmux', 'termux-42-1234')

    def test_auto_guards_and_manual_terminal_requirement(self):
        for env in [{'TMUX': 'socket'}, {'SSH_CONNECTION': 'remote'}, {'SSH_CLIENT': 'remote'},
                    {'SSH_TTY': '/dev/pts/0'}, {'DOTS_TERMUX_AUTOSTART': '0'}, {}]:
            with patch.dict(os.environ, env, clear=True), patch('os.isatty', return_value=False), \
                    patch('subprocess.run') as run:
                self.assertEqual(G['main'](['--auto'], proc_root=self.proc), 0)
                run.assert_not_called()
        with patch.dict(os.environ, {}, clear=True), patch('os.isatty', return_value=False), \
                redirect_stderr(io.StringIO()) as err:
            self.assertEqual(G['main']([], proc_root=self.proc), 1)
            self.assertIn('terminal is required', err.getvalue())

    def test_missing_tmux_and_timeout_return_to_shell(self):
        for failure in [None, subprocess.TimeoutExpired('fixture', 2)]:
            with patch.dict(os.environ, {}, clear=True), patch('os.isatty', return_value=True), \
                    patch.dict(G, default_session=lambda *args: 'termux-42-1234'), \
                    patch('shutil.which', return_value=None), redirect_stderr(io.StringIO()) as err:
                if failure:
                    with patch.dict(G, default_session=unittest.mock.Mock(side_effect=failure)):
                        self.assertEqual(G['main']([], proc_root=self.proc), 1)
                else:
                    self.assertEqual(G['main']([], proc_root=self.proc), 1)
                self.assertIn('plain shell', err.getvalue())

    def test_attachment_completion_is_not_just_an_exit_code(self):
        from contextlib import redirect_stdout
        for auto, message, status, expected in [
            (True, b'[exited]\n', 0, 20), (False, b'[exited]\n', 0, 0),
            (True, b'[detached (from session example)]\n', 0, 0),
            (True, b'[server exited]\n', 1, 1), (True, b'', 20, 1),
            (True, b'unrecognized\n', 0, 0), (True, b'[exited]\n', 1, 1),
        ]:
            process = unittest.mock.Mock(stdout=io.BytesIO(message))
            process.wait.return_value = process.poll.return_value = status
            with patch('subprocess.Popen', return_value=process), redirect_stdout(io.StringIO()):
                self.assertEqual(G['attach']('tmux', '=example', auto), expected)


if __name__ == '__main__':
    unittest.main()
