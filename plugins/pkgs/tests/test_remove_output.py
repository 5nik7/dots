"""Compact removals keep existing approval and native-status boundaries."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import Mock, patch

import test_workflows as fixtures
import test_install_output as install_fixtures
import test_winget as winget_fixtures
from pkgs_lib import cli, streams, upgrade_output, workflows
from pkgs_lib.backends import Backend
from pkgs_lib.common import Package


class RemoveOutput(unittest.TestCase):
    args = fixtures.Workflows.args
    invoke = fixtures.Workflows.invoke
    styled_config = install_fixtures.InstallOutput.styled_config

    def setUp(self):
        fixtures.Workflows.setUp(self)
        self.styled_config()
        fake = self.bin/'npm'
        text = fake.read_text().replace("else:sys.exit(9)", """elif args[0]=='uninstall':
    if os.environ.get('TEST_FAIL'):print('error: cannot remove',file=sys.stderr);sys.exit(42)
    for name in args[args.index('--')+1:]:data.pop(name,None)
    db.write_text(json.dumps(data));print('Removed packages')
else:sys.exit(9)""")
        fake.write_text(text)

    def installed(self):
        (self.home/'db.json').write_text('{"hello":"1.0", "@scope/other":"2.0"}')

    def test_aliases_and_multiple_packages_report_success_only(self):
        for alias in ('uninstall', 'un', 'remove'):
            self.installed()
            (self.home/'calls.jsonl').unlink(missing_ok=True)
            result = self.invoke(alias, '--manager', 'npm', '--global', 'hello', '@scope/other', '--yes')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Uninstall packages', result.stdout)
            self.assertEqual(result.stdout.count('complete'), 1)
            self.assertIn('Removed', result.stdout)
            self.assertIn('hello, @scope/other', result.stdout)
            self.assertNotIn('Removed packages', result.stdout)
            self.assertNotIn('npm uninstall', result.stdout)
            self.assertNotIn('Installing', result.stdout)
            self.assertEqual(json.loads((self.home/'db.json').read_text()), {})
            calls = [json.loads(line) for line in (self.home/'calls.jsonl').read_text().splitlines()]
            self.assertEqual([call[0] for call in calls], ['ls', 'uninstall'])

    def test_no_terminal_still_requires_approval_and_preview_does_not_remove(self):
        self.installed()
        preview = self.invoke('remove', '--manager', 'npm', '--global', 'hello', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn('npm uninstall --global -- hello', preview.stdout)
        self.assertIn('Dry run', preview.stdout)
        refused = self.invoke('remove', '--manager', 'npm', '--global', 'hello')
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertIn('No controlling terminal', refused.stderr)
        self.assertIn('Remove', refused.stdout)
        self.assertIn('hello', refused.stdout)
        self.assertIn('Manager', refused.stdout)
        self.assertNotIn('Removed', refused.stdout)
        self.assertIn('hello', json.loads((self.home/'db.json').read_text()))

    def test_review_precedes_confirmation_and_cancellation_never_applies(self):
        self.installed()
        for approval in (False, True):
            out, err = io.StringIO(), io.StringIO()
            def confirm(yes):
                self.assertFalse(yes)
                self.assertIn('Manager', out.getvalue())
                self.assertIn('hello', out.getvalue())
                self.assertIn('Remove', out.getvalue())
                self.assertNotIn('Removed', out.getvalue())
                return approval
            with patch.object(workflows, 'confirm', side_effect=confirm), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(['un', '--manager', 'npm', 'hello']), 0)
            if approval:
                self.assertIn('Removed', out.getvalue())
                self.assertNotIn('hello', json.loads((self.home/'db.json').read_text()))
            else:
                self.assertIn('Cancelled', out.getvalue())
                self.assertNotIn('Removed', out.getvalue())
                self.assertIn('hello', json.loads((self.home/'db.json').read_text()))

    def test_failure_and_missing_target_do_not_claim_removed(self):
        self.installed()
        with patch.dict(os.environ, TEST_FAIL='1'):
            failed = self.invoke('un', '--manager', 'npm', 'hello', '--yes')
        self.assertEqual(failed.returncode, 42, failed.stderr)
        self.assertIn('failed (exit 42)', failed.stdout)
        self.assertIn('cannot remove', failed.stderr)
        self.assertNotIn('Removed', failed.stdout)
        missing = self.invoke('remove', '--manager', 'npm', 'absent', '--yes')
        self.assertEqual(missing.returncode, 1, missing.stderr)
        self.assertIn('Not installed', missing.stderr)
        self.assertIn('hello', json.loads((self.home/'db.json').read_text()))

    def test_partial_command_failure_does_not_claim_all_packages_removed(self):
        plan = workflows.Plan(Backend('npm'), 'uninstall', names=['hello','other'], commands=[['one'],['two']])
        out = io.StringIO()
        with patch.object(streams, 'run', side_effect=[0, 42]), contextlib.redirect_stdout(out):
            self.assertEqual(workflows.apply_compact(plan, dict(self.cfg, output='styled')), 42)
        self.assertIn('failed (exit 42)', out.getvalue())
        self.assertNotIn('Removed', out.getvalue())

    def test_picker_cancel_and_selection_still_require_removal_confirmation(self):
        self.installed()
        for selected in ([], [Package('hello', installed=True)]):
            out = io.StringIO()
            with patch.object(cli, 'inventory', return_value=selected), patch.object(cli, 'pick', return_value=selected), \
                 patch.object(workflows, 'confirm', return_value=False) as confirm, contextlib.redirect_stdout(out):
                self.assertEqual(cli.main(['un', '--manager', 'npm']), 0)
            self.assertEqual(confirm.call_count, int(bool(selected)))
            self.assertNotIn('Removed', out.getvalue())
        self.assertIn('hello', json.loads((self.home/'db.json').read_text()))

    def test_raw_and_redirected_output_remain_full(self):
        for options, output in ((['--raw'], 'styled'), ([], 'auto')):
            self.installed()
            (self.home/'config/pkgs/config.json').write_text(json.dumps({'output': output}))
            result = self.invoke('remove', '--manager', 'npm', '--global', 'hello', '--yes', *options)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('npm uninstall --global -- hello', result.stdout)
            self.assertIn('Removed packages', result.stdout)

    def test_native_removal_stages_and_winget_identity(self):
        for manager, event in (('apt', 'Removing hello (1.0) ...'), ('pacman', '(1/2) removing hello...'),
                               ('pip', 'Found existing installation: hello 1.0'), ('gem', 'Successfully uninstalled hello-1.0')):
            meter = Mock(); output = upgrade_output.Output(manager, self.cfg, meter, action='uninstall')
            output.begin(); output.line(event, '\n', io.StringIO())
            self.assertIn('Removing', meter.update.call_args.args[0])
            self.assertNotIn('Installing', meter.update.call_args.args[0])
            if manager != 'gem': self.assertEqual(output.package, 'hello')
        backend = winget_fixtures.WinGetTests().backend()
        out = io.StringIO()
        def run(command, cfg, **kwargs):
            self.assertEqual(command[:2], ['winget.exe', 'uninstall'])
            self.assertEqual(command[command.index('--scope')+1], 'user')
            observer = cfg['_upgrade_output']; observer.begin(command)
            self.assertEqual(observer.package, 'Vendor.App')
            self.assertEqual(observer.stage, 'Removing')
            return 0
        with patch.object(backend, 'installed', return_value=[Package('Vendor.App', installed=True, details={'disabled_reason':''})]), \
             patch('pkgs_lib.winget.bridge', return_value={}), patch.object(streams, 'run', side_effect=run), \
             contextlib.redirect_stdout(out):
            self.assertEqual(workflows.execute(backend, 'uninstall', ['Vendor.App'], self.args('uninstall','--yes'), dict(self.cfg, output='styled')), 0)
        self.assertIn('Removed', out.getvalue())
        self.assertIn('Vendor.App', out.getvalue())


if __name__ == '__main__': unittest.main()
