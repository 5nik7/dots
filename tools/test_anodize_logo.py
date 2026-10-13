#!/usr/bin/env python3
"""Engine-free logo policy, PTY and static-help checks in disposable roots."""
import base64
import errno
import fcntl
import io
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import unittest
from unittest import mock

import test_bash_dots as fixture

sys.path.insert(0, str(fixture.REPO / 'lib/dots/anodize'))
from cli import Presentation
import logo


class Stream(io.StringIO):
    def __init__(self, terminal=True):
        super().__init__()
        self.terminal = terminal

    def isatty(self):
        return self.terminal


class LogoPolicy(unittest.TestCase):
    def draw(self, full=True, terminal=True, **env):
        stream = Stream(terminal)
        with mock.patch.dict(os.environ, {'TERM':'xterm-256color', 'COLUMNS':'80', 'LINES':'24', **env}, clear=True):
            logo.render(Presentation(stream), full)
        return stream.getvalue()

    def test_default_has_no_renderer_process_and_fits(self):
        with mock.patch.object(logo.subprocess, 'run', side_effect=AssertionError('unexpected renderer')):
            for width, rows in [(1, 1), (8, 3), (20, 9), (40, 24), (80, 24), (120, 30)]:
                for layout in logo.LAYOUTS:
                    with self.subTest(width=width, rows=rows, layout=layout):
                        out = self.draw(COLUMNS=str(width), LINES=str(rows), DOTS_COLOR='never', ANODIZE_LOGO_LAYOUT=layout)
                        self.assertTrue(out.strip())
                        self.assertLessEqual(max(map(len, out.splitlines())), max(1, width-1))
                        self.assertLessEqual(len(out.splitlines()), max(1, min(8, rows//3)))

    def test_destination_dimensions_and_bad_environment(self):
        stream = Stream()
        with mock.patch.object(stream, 'fileno', return_value=7), mock.patch.object(logo.os, 'get_terminal_size', return_value=os.terminal_size((40, 12))) as size:
            self.assertEqual(logo.dimensions(stream), (40, 12))
            size.assert_called_once_with(7)
        with mock.patch.dict(os.environ, {'COLUMNS':'bad','LINES':'-1'}, clear=True):
            self.assertEqual(logo.dimensions(stream), (80,24))
        self.assertEqual(self.draw(ANODIZE_LOGO='bad', ANODIZE_LOGO_LAYOUT='bad'), self.draw())

    def test_plain_redirected_and_missing_assets(self):
        with mock.patch.object(logo.subprocess, 'run', side_effect=AssertionError('unexpected renderer')):
            for mode in logo.MODES:
                self.assertNotIn('\x1b', self.draw(ANODIZE_LOGO=mode, NO_COLOR='1'))
                self.assertNotIn('\x1b', self.draw(ANODIZE_LOGO=mode, DOTS_COLOR='never'))
                self.assertNotIn('\x1b_G', self.draw(terminal=False, ANODIZE_LOGO=mode, DOTS_COLOR='always'))
            with mock.patch.object(logo, 'ASSETS', Path('/nonexistent-test-owned-assets')):
                self.assertIn('ANODIZE', self.draw())

    def test_kitty_chunks_fit_and_decode_to_original(self):
        out = self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty')
        chunks = re.findall(r'\x1b_G([^;]+);([^\x1b]+)\x1b\\', out)
        self.assertTrue(chunks)
        self.assertIn('q=2,C=1', chunks[0][0])
        self.assertTrue(chunks[-1][0].endswith('m=0'))
        self.assertTrue(all(len(data) <= 4096 for _, data in chunks))
        self.assertEqual(base64.b64decode(''.join(data for _, data in chunks)), (logo.ASSETS/'horizontal-color-white.png').read_bytes())
        for env in ({'TMUX':'fixture'}, {'STY':'fixture'}, {'ZELLIJ':'fixture'}):
            self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty', **env))
        self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty'))
        self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty', DOTS_ICONS='never'))
        self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty', COLUMNS='8', LINES='3'))

    def test_chafa_bounded_failure_and_ascii_policy(self):
        with mock.patch.object(logo.shutil, 'which', return_value='/fixture/chafa'), mock.patch.object(logo.subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, b'RENDERED\n')
            self.assertIn('RENDERED', self.draw(ANODIZE_LOGO='chafa', DOTS_ICONS='never'))
            args, kwargs = run.call_args
            self.assertIn('--symbols=ascii', args[0])
            self.assertIn('--probe=off', args[0])
            self.assertIn('--polite=on', args[0])
            self.assertIn('--animate=off', args[0])
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(kwargs['timeout'], 1.0)
            for outcome in (subprocess.CompletedProcess([], 1, b'partial'), subprocess.CompletedProcess([], 0, b'')):
                run.return_value = outcome
                self.assertIn('A N O D I Z E', self.draw(ANODIZE_LOGO='chafa'))
            run.side_effect = subprocess.TimeoutExpired('chafa', 1)
            self.assertIn('A N O D I Z E', self.draw(ANODIZE_LOGO='auto'))


class LogoCLI(unittest.TestCase):
    run_dots = fixture.DotsFixture.run_dots

    def setUp(self):
        fixture.DotsFixture.setUp(self)
        for source in [fixture.REPO/'bin/anodize', *fixture.REPO.glob('bin/dots-anodize*')]:
            shutil.copy2(source, self.repo/'bin'/source.name)
        self.env.update(ANODIZE_ENGINE=str(self.root/'missing'), DOTS_COLOR='never')

    def cli(self, *args, code=0):
        result = subprocess.run([str(self.repo/'bin/anodize'), *args], env=self.env, cwd=self.home,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, code, result.stderr)
        return result

    def terminal(self, argv, width=80, height=24, env=None):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        output = bytearray()
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=slave, stderr=slave,
                                cwd=self.home, env=env or self.env)
        os.close(slave)
        try:
            while select.select([master], [], [], 15)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
            self.assertEqual(proc.wait(timeout=3), 0, output)
        finally:
            if proc.poll() is None:
                proc.kill(); proc.wait()
            os.close(master)
        return output.decode().replace('\r\n', '\n')

    def test_help_static_no_extension_execution_and_size_parity(self):
        command = self.repo/'bin/dots-anodize'
        command.write_text(command.read_text().replace('exec python3', 'touch "$HOME/extension-ran"\nexec python3'))
        for width, height in [(40,24),(80,24),(120,30),(10,3)]:
            standalone = self.terminal([str(self.repo/'bin/anodize'), '--help'], width,height)
            dots = self.terminal([str(self.repo/'bin/dots'), 'anodize', '--help'], width,height)
            self.assertEqual(standalone.split('Anodize\n')[0], dots.split('dots anodize\n')[0])
        self.assertFalse((self.home/'extension-ran').exists())
        self.assertIn('ANODIZE', self.run_dots('help','anodize').stdout)
        prefixed = self.run_dots('anodize','--logo','text','--logo-layout=icon','preview','--help').stdout
        self.assertIn('dots anodize preview',prefixed)
        self.assertIn('--app',prefixed)
        # Static help still works when Python is unavailable.
        self.env['PATH'] = str(self.repo/'bin')
        result = subprocess.run([fixture.BASH, str(self.repo/'bin/dots'), 'anodize','--help'], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('ANODIZE',result.stdout)

    def test_option_positions_errors_and_data(self):
        for mode in logo.MODES:
            self.assertIn('Usage',self.cli('--logo='+mode).stdout)
            self.assertIn('ANODIZE',self.cli('--logo',mode,'--help').stdout)
            self.assertIn('ANODIZE',self.cli('list','--logo='+mode,'--help').stdout)
            result=self.cli('list','--logo='+mode,'--json')
            self.assertEqual(json.loads(result.stdout), {'items':[], 'schema':1})
            self.assertEqual(result.stderr,'')
            self.assertEqual(self.cli('completion','bash','--logo='+mode).stdout, (self.repo/'lib/dots/anodize/completion/bash').read_text())
        self.assertIn('ANODIZE', self.cli('list').stdout)
        self.assertIn('ANODIZE', self.cli('invalid',code=2).stderr)
        self.assertIn('ANODIZE', self.cli('modes',code=1).stderr)
        self.cli('--logo=bad','--help',code=2)
        self.assertIn('ANODIZE',self.run_dots('anodize','--logo=bad','--help',code=2).stderr)
        self.assertFalse((self.home/'state').exists())


if __name__ == '__main__':
    unittest.main()
