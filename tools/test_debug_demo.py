#!/usr/bin/env python3
"""Read-only mock gallery, native routing and terminal lifecycle in owned roots."""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from debug.fixtures import fixture
from debug import demo
import debug_cli
import progress


class Gallery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.root, cls.env, cls.base = cls.stack.enter_context(fixture(ROOT))
        shutil.copytree(ROOT / 'default', cls.root / 'default')
        shutil.copytree(ROOT / 'plugins/pkgs/pkgs_lib', cls.root / 'plugins/pkgs/pkgs_lib',
                        ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('dots-debug', 'dots-debug-demo'):
            target = cls.root / 'bin' / name
            shutil.copy2(ROOT / 'bin' / name, target)
            if os.name != 'nt':
                target.write_text('#!' + str(Path(shutil.which('bash')).resolve()) + '\n' + target.read_text().partition('\n')[2])
        cls.env.update(DOTS_COLOR='never', DOTS_ICONS='never', PYTHONDONTWRITEBYTECODE='1')

    @classmethod
    def tearDownClass(cls): cls.stack.close()

    def setUp(self):
        self.environment = patch.dict(os.environ, self.env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(progress.configure, False)

    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            try: code = debug_cli.main(['demo', *args])
            except SystemExit as exc: code = exc.code
        return code, output.getvalue(), error.getvalue()

    def child(self, *args, native=False, env=None):
        controller = 'cli.py' if native else 'debug_cli.py'
        words = ['debug', 'demo', *args] if native else ['demo', *args]
        return subprocess.run([sys.executable, '-B', str(self.root / 'lib/dots' / controller), *words],
                              env=env or self.env, capture_output=True, text=True, timeout=15)

    def test_static_gallery_is_mock_only_and_immediate(self):
        from git_identity import Identities
        before = sorted(str(p.relative_to(self.base)) for p in self.base.rglob('*'))
        with patch('subprocess.run', side_effect=AssertionError('provider executed')), \
             patch('subprocess.Popen', side_effect=AssertionError('provider executed')), \
             patch.object(Identities, 'host', side_effect=AssertionError('Git discovery')), \
             patch('debug.demo.time.sleep', side_effect=AssertionError('snapshot slept')):
            code, out, err = self.invoke('all', '--static')
        self.assertEqual((code, err), (0, ''))
        for value in ('Mock progress', 'Mock spinner', 'npm', 'pip', 'apt', 'uv', 'failed (exit 1)',
                      'Git default', 'Git short', 'Git verbose', 'clean-repo', 'conflict', 'new idea.txt',
                      'bin/dots-git-info', '界 café', 'Mock warning', '--duration SECONDS'):
            self.assertIn(value, out)
        self.assertNotIn('\x1b', out)
        self.assertEqual(before, sorted(str(p.relative_to(self.base)) for p in self.base.rglob('*')))

    def test_json_has_only_versioned_fixture_data_even_with_forced_decoration(self):
        with patch.dict(os.environ, DOTS_COLOR='always', DOTS_ICONS='always'), \
             patch('debug.demo.presentation', side_effect=AssertionError('JSON built a view')), \
             patch('debug.demo.time.sleep', side_effect=AssertionError('JSON slept')):
            for kind in (None, *demo.KINDS):
                args = [] if kind is None else [kind]
                code, out, err = self.invoke(*args, '--json')
                self.assertEqual((code, err), (0, ''))
                self.assertEqual(json.loads(out), demo.document(kind))
                self.assertNotIn('\x1b', out)
                self.assertNotIn(str(self.base), out)

    def test_bare_route_lists_examples_without_starting_progress(self):
        with patch('debug.demo.animate', side_effect=AssertionError('listing animated')):
            code, out, err = self.invoke()
        self.assertEqual((code, err), (0, ''))
        for kind in demo.KINDS: self.assertIn(kind, out)
        self.assertIn('dots debug demo progress --duration 4', out)

    def test_invalid_combinations_fail_before_rendering(self):
        invalid = [('unknown',), ('progress', '--duration', '0'), ('progress', '--duration', '61'),
                   ('progress', '--duration', '1.5'), ('files', '--duration', '4'), ('--duration', '4'),
                   ('all', '--loop'), ('pkgs', '--loop'), ('progress', '--loop', '--static'),
                   ('spinner', '--loop', '--json'), ('spinner', '--loop')]
        with patch('debug.demo.presentation', side_effect=AssertionError('invalid request rendered')):
            for args in invalid:
                code, out, err = self.invoke(*args)
                self.assertEqual((code, out), (2, ''), args)
                self.assertIn('error:', err)

    def test_redirected_and_dumb_demos_have_no_delay_or_cursor_controls(self):
        with patch('debug.demo.time.sleep', side_effect=AssertionError('fallback slept')):
            for term in ('xterm-256color', 'dumb'):
                with patch.dict(os.environ, TERM=term):
                    for kind in demo.ANIMATED:
                        code, out, err = self.invoke(kind, '--duration', '60')
                        self.assertEqual((code, err), (0, ''))
                        self.assertNotIn('\x1b', out)

    def test_gallery_animation_budget_and_mode_override_are_local(self):
        with patch('progress.eligible', return_value=True), patch('debug.demo.animate') as animate:
            code, out, err = self.invoke('all', '--duration', '6')
        self.assertEqual((code, err), (0, ''))
        self.assertEqual([(c.args[1], c.args[2], c.args[3]) for c in animate.call_args_list],
                         [('progress', 3, False), ('spinner', 3, False)])
        with patch.dict(os.environ, DOTS_PROGRESS='none'), patch('progress.eligible', return_value=True), \
             patch('debug.demo.time.sleep') as sleep:
            with redirect_stdout(io.StringIO()): demo.animate(demo.presentation(), 'progress', 1, False)
            self.assertAlmostEqual(sum(c.args[0] for c in sleep.call_args_list), 1)
        self.assertIsNone(progress._current)
        self.assertIsNone(progress._active_step)

    def test_loop_interrupt_cleans_up_the_shared_renderer(self):
        ui = demo.presentation()
        with patch('progress.eligible', return_value=True), \
             patch('debug.demo.time.sleep', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): demo.animate(ui, 'spinner', 1, True)
        self.assertIsNone(progress._current)
        self.assertIsNone(progress._active_step)

    def test_native_controller_and_bash_route_share_exact_json(self):
        expected = json.dumps(demo.document('all'), ensure_ascii=True) + '\n'
        forced = dict(self.env, DOTS_COLOR='always', DOTS_ICONS='always')
        for native in (False, True):
            result = self.child('all', '--json', native=native, env=forced)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, ''))
        if os.name != 'nt':
            result = subprocess.run([shutil.which('bash'), str(self.root / 'bin/dots'),
                                     'debug', 'demo', 'all', '--json'], env=forced,
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, ''))

    def test_static_metadata_and_shared_completion_are_inert(self):
        from command_metadata import catalog, read, roots
        from cli import complete, main
        metadata = read(self.root / 'bin/dots-debug-demo')
        self.assertEqual(metadata['argument'][0][1], 'choice:' + ','.join(demo.KINDS))
        self.assertEqual({row[0] for row in metadata['option']}, {'--static', '--duration', '--loop', '--json'})
        directories = roots(self.root)
        with patch('subprocess.run', side_effect=AssertionError('completion executed provider')), \
             patch('subprocess.Popen', side_effect=AssertionError('completion executed provider')):
            self.assertIn('debug-demo', catalog(directories))
            output = io.StringIO()
            with redirect_stdout(output): complete(self.root, directories, ['debug', 'demo', ''])
            for kind in demo.KINDS: self.assertIn('candidate\t' + kind + '\t', output.getvalue())
            for shell in ('bash', 'zsh', 'fish', 'powershell'):
                output = io.StringIO()
                with redirect_stdout(output): main(['completion', shell])
                self.assertTrue(output.getvalue())
                self.assertNotIn('\x1b', output.getvalue())
            output = io.StringIO()
            with redirect_stdout(output): main(['__complete', 'debug', 'demo', ''])
            for kind in demo.KINDS: self.assertIn('candidate\t' + kind + '\t', output.getvalue())
        if os.name != 'nt':
            # Nushell and Xonsh request this protocol from their init adapters;
            # they do not have a `dots completion` script-emission route.
            for shell in ('bash', 'zsh', 'fish', 'nu', 'xonsh'):
                result = subprocess.run([shutil.which('bash'), str(self.root / 'bin/dots'),
                                         '__complete', shell, '3', '--', 'dots', 'debug', 'demo', ''],
                                        env=self.env, capture_output=True, text=True, timeout=15)
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                for kind in demo.KINDS: self.assertIn('candidate\t' + kind + '\t', result.stdout)

    def test_static_snapshots_fit_phone_and_wide_terminals(self):
        from resources import cells
        for columns in (40, 80, 120):
            with patch.dict(os.environ, COLUMNS=str(columns), DOTS_COLOR='always', DOTS_ICONS='always'):
                code, out, err = self.invoke('all', '--static')
            self.assertEqual((code, err), (0, ''))
            plain = re.sub(r'\x1b\[[0-9;]*m', '', out)
            self.assertTrue(all(cells(line) <= columns for line in plain.splitlines()),
                            [(cells(line), line) for line in plain.splitlines() if cells(line) > columns])
            self.assertIn('━', plain)
            self.assertIn('27%', plain)

    @unittest.skipIf(os.name == 'nt', 'POSIX PTY lifecycle; native Windows terminal acceptance remains separate')
    def test_terminal_animation_mode_override_resize_and_interrupt(self):
        import fcntl
        import pty
        import select
        import struct
        import termios
        for kind, loop in (('progress', False), ('spinner', True)):
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 120, 0, 0))
            command = [sys.executable, '-B', str(self.root / 'lib/dots/debug_cli.py'),
                       'demo', kind, '--duration', '1', *(['--loop'] if loop else [])]
            child = subprocess.Popen(command, env=dict(self.env, DOTS_PROGRESS='none', COLUMNS='999'),
                                     stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
            os.close(slave)
            output = bytearray()
            started = time.monotonic()
            resized = interrupted = False
            try:
                while child.poll() is None or select.select([master], [], [], 0)[0]:
                    elapsed = time.monotonic() - started
                    if elapsed > 8: self.fail('demo did not finish')
                    if elapsed > .65 and not resized:
                        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 40, 0, 0))
                        resized = True
                    if loop and elapsed > .85 and b'\x1b[2K' in output and not interrupted:
                        os.killpg(child.pid, signal.SIGINT)
                        interrupted = True
                    if select.select([master], [], [], .05)[0]:
                        try:
                            data = os.read(master, 65536)
                            if not data: break
                            output.extend(data)
                        except OSError: break
                self.assertEqual(child.wait(timeout=5), 130 if loop else 0, output.decode(errors='replace'))
            finally:
                if child.poll() is None: child.kill(); child.wait()
                os.close(master)
            text = output.decode(errors='replace')
            self.assertIn('\x1b[2K', text)
            self.assertNotIn('\x1b[?25l', text)
            self.assertNotIn('Overall', text)
            self.assertTrue(resized)
            if not loop:
                self.assertIn('100%', text)
                self.assertIn('Mock demo complete', text)


if __name__ == '__main__': unittest.main()
