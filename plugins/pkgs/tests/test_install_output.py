"""Compact installs use owned state and fake managers; no host transactions."""
import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

import test_workflows as fixtures
from pkgs_lib import cli, streams, upgrade_output, workflows
from pkgs_lib.backends import Backend
from pkgs_lib.common import Package
import test_winget as winget_fixtures


class InstallOutput(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    invoke = fixtures.Workflows.invoke
    args = fixtures.Workflows.args

    def styled_config(self, **values):
        path = self.home/'config/pkgs/config.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(output='styled', **values)))

    def test_alias_multiple_targets_and_popup_share_compact_result(self):
        for alias in ('install', 'in'):
            with self.subTest(alias=alias), patch.dict(os.environ, DOTS_MENU_CAPTURE='1'):
                result = self.invoke(alias, '--manager', 'npm', '--global', 'hello', '@scope/other')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Install packages', result.stdout)
            self.assertEqual(result.stdout.count('complete'), 1)
            self.assertIn('Installed', result.stdout)
            self.assertIn('hello, @scope/other', result.stdout)
            self.assertNotIn('Upgrading', result.stdout)
            for hidden in ('Command', 'npm install', 'Installed packages', 'Proceed?'):
                self.assertNotIn(hidden, result.stdout)
            self.assertIn('fixture detail', result.stderr)
        self.assertEqual(json.loads((self.home/'db.json').read_text()), {'hello':'2.0', '@scope/other':'2.0'})

    def test_redirect_raw_and_preview_preserve_detail_and_literal_operands(self):
        for options in ([], ['--raw']):
            result = self.invoke('install', '--manager', 'npm', '--global', '@scope/hello', *options)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('npm install --global -- @scope/hello', result.stdout)
            self.assertIn('Installed packages', result.stdout)
        self.styled_config()
        (self.home/'calls.jsonl').unlink()
        preview = self.invoke('in', '--manager', 'npm', '--global', '@scope/hello', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn('npm install --global -- @scope/hello', preview.stdout)
        self.assertIn('Dry run', preview.stdout)
        self.assertFalse((self.home/'calls.jsonl').exists())
        raw = self.invoke('in', '--manager', 'npm', '@scope/hello', '--raw')
        self.assertIn('Installed packages', raw.stdout)

    def test_policy_skip_and_real_exit_status(self):
        self.styled_config(policies={'npm': {'skip': ['held']}})
        skipped = self.invoke('in', '--manager', 'npm', 'held')
        self.assertEqual(skipped.returncode, 1, skipped.stderr)
        self.assertIn('Skipped by policy', skipped.stderr)
        self.assertFalse((self.home/'calls.jsonl').exists())
        out = io.StringIO()
        empty = workflows.Plan(Backend('npm'), 'install', skipped=[dict(package='held', reason='policy')])
        with contextlib.redirect_stdout(out):
            self.assertEqual(workflows.apply_compact(empty, dict(self.cfg, output='styled')), 0)
        self.assertIn('unchanged', out.getvalue())
        self.assertIn('1 skipped', out.getvalue())
        self.assertNotIn('Installed', out.getvalue())
        with patch.dict(os.environ, TEST_FAIL='1'):
            failed = self.invoke('in', '--manager', 'npm', 'hello')
        self.assertEqual(failed.returncode, 42, failed.stderr)
        self.assertIn('failed (exit 42)', failed.stdout)
        self.assertNotIn('complete', failed.stdout)
        self.assertNotIn('Installed', failed.stdout)
        self.assertEqual((self.home/'db.json').read_text(), '{}')

    def test_picker_accept_and_cancel(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(cli, 'inventory', return_value=[Package('hello')]), \
             patch.object(cli, 'pick', return_value=[Package('hello')]), \
             patch.dict(os.environ, DOTS_MENU_CAPTURE='1'), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(['in', '--manager', 'npm']), 0)
        self.assertIn('Install packages', out.getvalue())
        self.assertIn('complete', out.getvalue())
        self.assertIn('Installed', out.getvalue())
        self.assertIn('hello', out.getvalue())
        self.assertNotIn('Command', out.getvalue())
        calls = (self.home/'calls.jsonl').read_bytes()
        with patch.object(cli, 'inventory', return_value=[]), patch.object(cli, 'pick', return_value=[]):
            self.assertEqual(cli.main(['in', '--manager', 'npm']), 0)
        self.assertEqual((self.home/'calls.jsonl').read_bytes(), calls)

    def test_custom_recipe_prompts_and_bounded_failure_diagnostics(self):
        out, err = io.StringIO(), io.StringIO()
        meter = Mock()
        summary = upgrade_output.Output('npm', self.cfg, meter, action='install')
        summary.begin(['custom-recipe'])
        self.assertEqual(meter.update.call_args.args[0], 'npm · Installing')
        formatter = streams.Formatter(err, dict(self.cfg, _manager='npm'), summary)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            formatter.feed(b'Proceed? [y/N] ')
            formatter.flush_partial()
            formatter.feed(b'\n'+b'error: failure\n'+b'\n'.join(('warning: detail '+str(n)).encode() for n in range(7))+b'\n')
            summary.result(17)
        self.assertIn('Proceed? [y/N]', err.getvalue())
        self.assertIn('failed (exit 17)', out.getvalue())
        self.assertIn('5 more diagnostic lines', err.getvalue())
        self.assertNotIn('detail 6', err.getvalue())

    def test_native_events_and_install_fallback_are_truthful(self):
        for manager, line, package in (
            ('apt', 'Unpacking bun (1.2.0) ...', 'bun'),
            ('apt', 'Setting up libfoo:arm64 (2.0) ...', 'libfoo:arm64'),
            ('pacman', '( 1/2) installing bun...', 'bun'),
            ('pip', 'Collecting hello', 'hello'),
            ('npm', 'npm http fetch GET 200 https://registry.invalid/hello 15ms', 'hello'),
        ):
            with self.subTest(manager=manager):
                meter = Mock()
                summary = upgrade_output.Output(manager, self.cfg, meter, action='install')
                summary.begin()
                self.assertEqual(meter.update.call_args.args[0], manager+' · Installing')
                summary.line(line, '\n', io.StringIO())
                self.assertEqual(summary.package, package)
                self.assertNotIn('Upgrading', meter.update.call_args.args[0])
        for manager in ('gem', 'uv-tool', 'dnf', 'apt'):
            meter = Mock(); summary = upgrade_output.Output(manager, self.cfg, meter, action='install')
            summary.line('Unrecognized native status', '\n', io.StringIO())
            self.assertEqual(meter.update.call_args.args[0], manager+' · Installing')
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            summary = upgrade_output.Output('apt', self.cfg, action='install')
            summary.line('E: File has unexpected size (mirror sync)', '\n', err)
            summary.result(100)
        self.assertIn('retry the install', err.getvalue())
        self.assertNotIn('pkgs upgrade', err.getvalue())

    def test_winget_install_scope_exact_ids_and_single_summary(self):
        backend = winget_fixtures.WinGetTests().backend('machine')
        out, err, commands = io.StringIO(), io.StringIO(), []
        def native(command, cfg, **kwargs):
            commands.append(command)
            observer = cfg['_upgrade_output']
            observer.begin(command)
            self.assertEqual(observer.package, command[command.index('--id')+1])
            self.assertEqual(observer.stage, 'Installing')
            observer.line('Native installer output', '\n', out)
            self.assertEqual(observer.package, command[command.index('--id')+1])
            return 0
        with patch('pkgs_lib.winget.bridge', side_effect=lambda action, **kw: {} if action == 'capabilities' else {'packages':[winget_fixtures.row(kw['id'])]}), \
             patch.object(streams, 'run', side_effect=native), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = workflows.execute(backend, 'install', ['Vendor.App', 'Second.App'], self.args('install'), dict(self.cfg, output='styled'))
        self.assertEqual(rc, 0)
        self.assertEqual(len(commands), 2)
        for command in commands:
            self.assertEqual(command[:2], ['winget.exe', 'install'])
            self.assertEqual(command[command.index('--scope')+1], 'machine')
            self.assertIn('--exact', command)
        self.assertEqual(out.getvalue().count('complete'), 1)
        self.assertNotIn('Native installer output', out.getvalue())
        self.assertIn('machine', out.getvalue())
        self.assertIn('Installed', out.getvalue())
        self.assertIn('Vendor.App, Second.App', out.getvalue())

    def test_install_activity_and_quiet_time_for_language_managers(self):
        for manager, command, event, package in (
            ('npm', ['npm','install','--','hello'], 'npm http fetch GET 200 https://registry.invalid/hello 1ms', 'hello'),
            ('pip', [sys.executable,'-m','pip','install','hello'], 'Collecting hello', 'hello'),
            ('go', ['go','install','example.org/hello@latest'], 'go: downloading example.org/dependency v1.0.0', 'hello'),
        ):
            with self.subTest(manager=manager):
                meter = Mock(); summary = upgrade_output.Output(manager, self.cfg, meter, action='install')
                with patch.object(upgrade_output.time, 'monotonic', return_value=0):
                    summary.begin(command)
                    summary.line(event, '\n', io.StringIO())
                summary.tick(now=65)
                self.assertIn('quiet 1:05', meter.update.call_args.args[0])
                self.assertIn(package, meter.update.call_args.args[0])
                self.assertNotIn('Upgrading', repr(meter.update.call_args_list))

    def test_recipe_executes_once_with_full_raw_bytes(self):
        recipe = self.home/'custom recipe.py'
        recipe.write_text("import sys\nsys.stdout.buffer.write(b'\\x1b[31mcustom\\rbytes\\x1b[0m\\n')\nsys.exit(23)\n")
        self.styled_config(policies={'npm': {'install': {'replace': [[sys.executable, str(recipe)]]}}})
        compact = self.invoke('in', '--manager', 'npm', 'hello')
        self.assertEqual(compact.returncode, 23, compact.stderr)
        self.assertIn('failed (exit 23)', compact.stdout)
        self.assertNotIn('Installed', compact.stdout)
        self.assertNotIn('Command', compact.stdout)
        import subprocess
        raw = subprocess.run([sys.executable, '-B', str(fixtures.APP/'main.py'), 'in', '--manager', 'npm', 'hello', '--raw'],
                             capture_output=True, env=dict(os.environ), timeout=15, start_new_session=True)
        self.assertEqual(raw.returncode, 23, raw.stderr)
        self.assertIn(b'\x1b[31mcustom\rbytes\x1b[0m\n', raw.stdout)

    def test_package_summary_wraps_full_names_without_duplicate_rows(self):
        import re
        from resources import cells
        from test_upgrade_output import Terminal
        names = ['@scope/very-long-package-identity-for-a-narrow-terminal', 'second']
        for width in (40, 80, 120):
            for action, label in (('install', 'Installed'), ('uninstall', 'Removed')):
                out = Terminal()
                with patch.dict(os.environ, COLUMNS=str(width), DOTS_MENU_CAPTURE='1'), contextlib.redirect_stdout(out):
                    output = upgrade_output.Output('npm', self.cfg, action=action)
                    output.result(0, names=names+[names[0]])
                plain = re.sub(r'\x1b\[[0-9;]*m', '', out.getvalue())
                self.assertEqual(plain.count(label), 1)
                self.assertTrue(all(cells(line)<=width for line in plain.splitlines()), plain)
                joined = ''.join(plain.split())
                for name in names: self.assertEqual(joined.count(name), 1)


if __name__ == '__main__': unittest.main()
