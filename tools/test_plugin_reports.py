#!/usr/bin/env python3
"""Plugin report policies, data contracts and real popup rendering in owned roots."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_menus import MenuFixture, NativeMenuFixture, ROOT
import menu_pager
from plugin_presentation import report
from resources import cells

sys.path.insert(0, str(ROOT / 'plugins/pkgs'))
if os.name != 'nt':
    from pkgs_lib import cli as pkgs
    from pkgs_lib.common import Package, Error

# The shared default roles resolve headings to bold cyan and success to green.
# Keep exact report contracts while honoring configured semantic colors.
ANSI = re.compile(r'\x1b\[[0-9;]*m')


class Terminal(io.StringIO):
    def isatty(self):
        return True


def blastoff_fixture(fixture):
    fixture.env.update(BLASTOFF_HOME=str(fixture.home/'blastoff'),
                       STARSHIP_CONFIG=str(fixture.home/'active configuration.toml'),
                       DOTS=str(ROOT))
    store = Path(fixture.env['BLASTOFF_HOME'])
    (store/'themes').mkdir(parents=True)
    (store/'themes/aurora.toml').write_text('x=1\n')
    Path(fixture.env['STARSHIP_CONFIG']).write_text('x=1\n')
    binaries = fixture.base/'bin'; binaries.mkdir()
    for name in ('starship', 'fzf', 'gum'):
        path = binaries/name
        path.write_text('#!' + sys.executable + '\nimport sys\nprint("fixture-preset" if "--list" in sys.argv else "0.74.0")\n')
        path.chmod(0o700)
    fixture.env['PATH'] = str(binaries) + os.pathsep + fixture.env['PATH']


class Reports(MenuFixture):
    def setUp(self):
        super().setUp()
        blastoff_fixture(self)
        os.environ.update(self.env)

    def blastoff(self, args, *, env=None, frontend='core', code=0):
        command = [sys.executable, '-B', '-I', str(ROOT/'plugins/blastoff/lib/blastoff.py')]
        if frontend == 'native':
            command = [sys.executable, '-B', str(ROOT/'lib/dots/cli.py'), 'blastoff']
        elif frontend in ('standalone', 'dots'):
            command = [shutil.which('bash'), str(ROOT/'bin'/('blastoff' if frontend == 'standalone' else 'dots'))]
            if frontend == 'dots': command += ['blastoff']
        result = subprocess.run([*command, *args], env=env or self.env, cwd=self.home,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, code, result.stderr)
        return result.stdout, result.stderr

    def packages(self, args, *, terminal=False, rows=None, failure=False, config_color='auto'):
        output, errors = (Terminal() if terminal else io.StringIO()), io.StringIO()
        backend = SimpleNamespace(name='apt', scope='fixture system')
        rows = [Package('editor', '1.2', 'Unicode 界 and spaces', True),
                Package('long-'+'name'*12, '2.0', 'inert \x1b[31m text', True)] if rows is None else rows
        completion = lambda shell, action: dict(shell=shell, file=str(self.home/'completion files'/shell),
            status='missing', version='1', installed_version=None, activation='unverified',
            loader='not found', notice='Fixture loader unavailable')
        with redirect_stdout(output), redirect_stderr(errors), \
             patch.object(pkgs, 'config', return_value=dict(color=config_color, manager='auto', external_detection=False)), \
             patch.object(pkgs, 'available', side_effect=lambda name: name == 'apt'), \
             patch.object(pkgs, 'default_manager', return_value='apt'), \
             patch.object(pkgs, 'choose_manager', return_value=backend), \
             patch.object(pkgs, 'inventory', side_effect=Error('fixture failure') if failure else None, return_value=rows) as inventory, \
             patch.object(pkgs, 'fzf_details', return_value=dict(path='', source='PATH', version='missing', supported=False)), \
             patch.object(pkgs, 'manage', side_effect=completion), \
             patch.object(pkgs, 'which', return_value=None), \
             patch('pkgs_lib.common.subprocess.Popen', side_effect=AssertionError('host query forbidden')):
            code = pkgs.main(args)
        self.assertEqual(inventory.call_count, int(args[0] == 'list'))
        return code, output.getvalue(), errors.getvalue()

    def test_controls_capture_plain_and_independent_streams(self):
        for mode, no_color, explicit, expected in (
                ('auto', '', None, True), ('auto', '1', None, False),
                ('never', '', None, False), ('always', '1', None, True),
                ('always', '', 'never', False), ('never', '', 'always', True)):
            with patch.dict(os.environ, DOTS_COLOR=mode, NO_COLOR=no_color):
                ui = report(explicit, stream=Terminal())
                self.assertEqual(ui.ui.color, expected)
                self.assertIsNone(report(explicit, stream=Terminal(), data=True))
        with patch.dict(os.environ, DOTS_COLOR='auto', DOTS_ICONS='never', TERM='dumb'):
            self.assertFalse(report(stream=Terminal()).ui.color)
        with patch.dict(os.environ, DOTS_COLOR='auto', DOTS_ICONS='never'):
            self.assertIsNone(report(stream=io.StringIO()))
            self.assertTrue(report(stream=Terminal()).ui.color)
        with patch.dict(os.environ, DOTS_MENU_CAPTURE='1', DOTS_COLOR='never', DOTS_ICONS='always'):
            ui = report(stream=io.StringIO())
            self.assertFalse(ui.ui.color); self.assertTrue(ui.ui.icons)
        with patch.dict(os.environ, DOTS_MENU_CAPTURE='1', DOTS_COLOR='always', DOTS_ICONS='never'):
            ui = report(stream=io.StringIO())
            self.assertTrue(ui.ui.color); self.assertFalse(ui.ui.icons)

    def test_blastoff_frontends_aliases_and_capture_data_bytes(self):
        colored = dict(self.env, DOTS_COLOR='always', DOTS_ICONS='never')
        baseline = self.blastoff(['current'], env=colored)
        self.assertIn(b'\x1b[1;36mCurrent configuration', baseline[0])
        for frontend in ('native', *(() if os.name == 'nt' else ('standalone', 'dots'))):
            self.assertEqual(self.blastoff(['current'], env=colored, frontend=frontend), baseline)
        for alias in ('-t', '--theme'):
            self.assertEqual(self.blastoff([alias], env=colored), baseline)
        for args in (['current', '--json'], ['theme', 'list', '--json'], ['doctor', '--json'],
                     ['backup', 'list', '--json'], ['completion', 'bash']):
            plain = self.blastoff(args)
            decorated = self.blastoff([*args, '--color', 'always'],
                env=dict(colored, DOTS_MENU_CAPTURE='1', DOTS_ICONS='always'))
            self.assertEqual(decorated, plain)
            self.assertNotIn(b'\x1b', decorated[0])
        modules = Path(self.env['BLASTOFF_HOME'])/'modules'; modules.mkdir()
        (modules/'sample.toml').write_bytes(b'# raw\n[directory]\nstyle="blue"\n')
        self.assertEqual(self.blastoff(['module', 'show', 'sample', '--color', 'always'], env=colored)[0],
                         (modules/'sample.toml').read_bytes())

    def test_plain_capture_has_human_layout_and_redirect_keeps_format(self):
        ordinary, _ = self.blastoff(['current'])
        self.assertIn(b'MATCHES', ordinary)
        self.assertIn(str(self.home).encode(), ordinary)
        command = [sys.executable, '-B', '-I', str(ROOT/'plugins/blastoff/lib/blastoff.py'), 'current']
        spool = self.base/'capture'; spool.mkdir()
        code, source = menu_pager.capture(command, spool, environment=self.env)
        captured = source.read_bytes()
        self.assertEqual(code, 0)
        self.assertIn(b'Matches', captured); self.assertIn(b'Origin\n', captured)
        self.assertNotIn(b'\x1b', captured)

    @unittest.skipIf(os.name == 'nt', 'pkgs reports require POSIX; native refusal is tested by bundled apps')
    def test_pkgs_nested_reports_empty_error_and_json(self):
        for args in (['list', '--installed'], ['managers'], ['doctor']):
            baseline = self.packages([*args, '--json'])
            with patch.dict(os.environ, DOTS_MENU_CAPTURE='1', DOTS_COLOR='always', DOTS_ICONS='always'):
                self.assertEqual(self.packages([*args, '--json', '--color', 'always']), baseline)
                code, text, _ = self.packages(args)
                self.assertEqual(code, 0); self.assertIn('\x1b[1;36m', text)
                self.assertNotIn('"supported":', text); self.assertNotIn('"shell":', text)
                self.assertNotIn('\x1b[31m', text)
        with patch.dict(os.environ, DOTS_MENU_CAPTURE='1'):
            code, text, _ = self.packages(['list', '--installed'], rows=[])
            self.assertEqual(code, 0); self.assertIn('No packages match', text)
            code, _, error = self.packages(['list'], failure=True)
            self.assertEqual(code, 1); self.assertIn('fixture failure', error)

    @unittest.skipIf(os.name == 'nt', 'pkgs reports require POSIX')
    def test_pkgs_report_color_precedence_including_redirected_config_override(self):
        with patch.dict(os.environ, DOTS_COLOR='never'):
            self.assertNotIn('\x1b', self.packages(['list'], config_color='always')[1])
            self.assertIn('\x1b', self.packages(['list', '--color', 'always'])[1])
        with patch.dict(os.environ, DOTS_COLOR='always'):
            self.assertNotIn('\x1b', self.packages(['list', '--color', 'never'])[1])
            self.assertIn('\x1b', self.packages(['list'], config_color='never')[1])
        os.environ.pop('DOTS_COLOR')
        self.assertIn('\x1b', self.packages(['list'], config_color='always')[1])

    def test_resource_snapshot_and_narrow_widths_preserve_values(self):
        theme = Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'; theme.mkdir(parents=True)
        (theme/'file-styles.tsv').write_text('dots-file-styles\t1\nsuffix\t.toml\t38;2;18;52;86\tfold\n')
        for width in (40, 80, 120):
            env = dict(self.env, DOTS_COLOR='always', COLUMNS=str(width))
            for args in (['current'], ['theme', 'list'], ['backup', 'list'], ['doctor']):
                output, _ = self.blastoff(args, env=env)
                plain = ANSI.sub('', output.decode())
                self.assertTrue(all(cells(line) <= width for line in plain.splitlines()), plain)
                if args == ['current']:
                    self.assertIn(b'\x1b[38;2;18;52;86m', output)
                    self.assertIn('activeconfiguration.toml', ''.join(plain.split()))
            with patch.dict(os.environ, env):
                if os.name == 'nt':
                    continue
                for args in (['list', '--installed'], ['managers'], ['doctor']):
                    code, text, _ = self.packages(args)
                    self.assertEqual(code, 0)
                    self.assertTrue(all(cells(line) <= width for line in ANSI.sub('', text).splitlines()), text)

    @unittest.skipUnless(os.name == 'nt', 'native Windows PowerShell acceptance')
    def test_native_powershell_report_parity(self):
        engines = [shutil.which(name) for name in ('powershell', 'pwsh')]
        if not any(engines): self.skipTest('native PowerShell unavailable')
        env = dict(self.env, DOTS_COLOR='always')
        expected, _ = self.blastoff(['current'], env=env)
        for engine in filter(None, engines):
            result = subprocess.run([engine, '-NoLogo', '-NoProfile', '-NonInteractive',
                '-File', str(ROOT/'bin/blastoff.ps1'), 'current'], env=env,
                capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)

    @unittest.skipUnless(os.name == 'posix', 'native POSIX PTY')
    def test_terminal_save_success_and_cancel_with_owned_config(self):
        sys.path.insert(0, str(ROOT/'plugins/blastoff/tests'))
        from pty_support import terminal
        command = [sys.executable, '-B', '-I', str(ROOT/'plugins/blastoff/lib/blastoff.py'), 'theme', 'save']
        env = dict(self.env, DOTS_COLOR='always')
        for answer, expected in ((b'\n', 130), (b'new-theme\n', 0)):
            code, text = terminal(command, env, keys=answer, ready=b'(empty cancels):', columns=80)
            self.assertEqual(code, expected, text)
            self.assertIn(b'\x1b[1;36mSave active theme', text)
            self.assertEqual(Path(env['STARSHIP_CONFIG']).read_text(), 'x=1\n')
        self.assertIn(b'\x1b[32mSaved', text)
        self.assertEqual((Path(env['BLASTOFF_HOME'])/'themes/new-theme.toml').read_text(), 'x=1\n')


class NativeReports(NativeMenuFixture):
    def test_package_report_color_and_scrolling_in_private_popup(self):
        if not shutil.which('less'): self.skipTest('less unavailable')
        from menu_tmux import TmuxContext
        command = self.command("""import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, """ + repr(str(ROOT/'plugins/pkgs')) + """)
from pkgs_lib import cli
from pkgs_lib.common import Package
with patch.object(cli, 'config', return_value=dict(color='auto', manager='auto', external_detection=False)), patch.object(cli, 'choose_manager', return_value=SimpleNamespace(name='apt',scope='fixture')), patch.object(cli, 'inventory', return_value=[Package('package-'+str(i), '1.0', 'Fixture description', True) for i in range(100)]), patch('pkgs_lib.common.subprocess.Popen', side_effect=AssertionError('host query forbidden')):
    sys.exit(cli.main(['list', '--installed']))
""")
        for width in (40, 80, 120):
            self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', 30, width, 0, 0))
            context = TmuxContext.capture(client=self.first[2]); deadline = time.monotonic() + 3
            while context.verify() != (width, 30) and time.monotonic() < deadline: time.sleep(.05)
            self.drain(self.first[1]); self.drain(self.second[1])
            worker = self.worker("import os,json;from menus import run_action;from menu_tmux import TmuxContext;run_action(json.loads(os.environ['COMMAND']),kind='output',title='Package fixture',context=TmuxContext.capture(client=os.environ['CLIENT']))", COMMAND=json.dumps(command), DOTS_COLOR='auto')
            text = self.receive(self.first[1], b'Back q')
            self.assertIn(b'Installed packages', text)
            self.assertNotIn(b'Installed packages', self.drain(self.second[1]))
            os.write(self.first[1], b'G')
            self.receive(self.first[1], b'package-99')
            os.write(self.first[1], b'q')
            _, error = worker.communicate(timeout=15)
            self.assertEqual(worker.returncode, 0, error)

    def test_blastoff_report_reaches_only_invoking_popup_at_all_widths(self):
        if not shutil.which('less'): self.skipTest('less unavailable')
        blastoff_fixture(self)
        from menu_tmux import TmuxContext
        for width in (40, 80, 120):
            self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', 30, width, 0, 0))
            context = TmuxContext.capture(client=self.first[2]); deadline = time.monotonic() + 3
            while context.verify() != (width, 30) and time.monotonic() < deadline: time.sleep(.05)
            for color in ('auto', 'never'):
                self.drain(self.first[1]); self.drain(self.second[1])
                code = "import os;from menu_cli import invoke,FAMILIES;from pathlib import Path;from menu_tmux import TmuxContext;invoke(Path(os.environ['DOTS']),next(a for a in FAMILIES['blastoff'] if a.id=='current'),TmuxContext.capture(client=os.environ['CLIENT']))"
                worker = self.worker(code, DOTS_COLOR=color)
                text = self.receive(self.first[1], b'Back q')
                self.assertIn(b'Current configuration', text)
                self.assertIn(b'Matches', text)
                self.assertNotIn(b'Current configuration', self.drain(self.second[1]))
                os.write(self.first[1], b'q')
                _, error = worker.communicate(timeout=15)
                self.assertEqual(worker.returncode, 0, error)


if __name__ == '__main__':
    unittest.main()
