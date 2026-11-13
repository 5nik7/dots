"""Real work counts without native package effects or changed data streams."""
import contextlib
import io
import os
import time
import unittest
from unittest.mock import Mock, patch

import test_workflows as fixtures
from test_upgrade_output import Terminal
from pkgs_lib import streams, upgrade_output, workflows, manifests
from pkgs_lib.backends import Backend
from pkgs_lib.common import Package


class ProgressCounts(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    args = fixtures.Workflows.args

    def test_command_counts_advance_after_return_and_preserve_failure(self):
        meter = Mock()
        output = upgrade_output.Output('npm', self.cfg, meter)
        plan = workflows.Plan(Backend('npm'), 'install', commands=[['first'], ['second'], ['third']])
        seen = []
        def run(command, cfg, **kwargs):
            output.begin(command)
            seen.append((command, meter.update_spans.call_args.args[1:]))
            return 42 if command == ['second'] else 0
        with patch.object(streams, 'run', side_effect=run):
            self.assertEqual(workflows.apply(plan, dict(self.cfg, _upgrade_output=output)), 42)
        self.assertEqual(seen, [(['first'], (0, 3)), (['second'], (1, 3))])
        self.assertEqual(meter.update_spans.call_args.args[1:], (2, 3))

    def test_independent_pip_targets_count_returned_commands_not_successes(self):
        meter = Mock(); output = upgrade_output.Output('pip', self.cfg, meter)
        steps = [(['bad'], [['bad'], ['skipped-hook']]), (['good'], [['good']])]
        plan = workflows.Plan(Backend('pip'), 'upgrade', commands=[['bad'], ['skipped-hook'], ['good']], steps=steps)
        with patch.object(streams, 'run', side_effect=[17, 0]) as run:
            self.assertEqual(workflows.apply(plan, dict(self.cfg, _upgrade_output=output)), 17)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(plan.failed, [('bad', 17)]); self.assertEqual(plan.completed, ['good'])
        self.assertEqual(meter.update_spans.call_args.args[1:], (2, 3))

    def test_native_bytes_and_transaction_counts_have_explicit_scopes(self):
        meter = Mock(); output = upgrade_output.Output('pip', self.cfg, meter)
        output.commands_progress(1, 4)
        output.line('Progress 1024 of 4096', '\n', io.StringIO())
        self.assertEqual(meter.update_spans.call_args.args[1:], (1024, 4096))
        self.assertIn('bytes', str(meter.update_spans.call_args.args[0]))
        output.line('Building wheel for hello', '\n', io.StringIO())
        self.assertEqual(meter.update_spans.call_args.args[1:], (1, 4))
        output.line('Progress 2048 of 0', '\n', io.StringIO())
        self.assertEqual(meter.update_spans.call_args.args[1:], (1, 4))
        self.assertNotIn('%', str(meter.update_spans.call_args.args[0]))
        output = upgrade_output.Output('pacman', self.cfg, meter)
        output.commands_progress(0, 1)
        output.line('(2/5) upgrading hello...', '\n', io.StringIO())
        self.assertEqual(meter.update_spans.call_args.args[1:], (1, 5))
        self.assertEqual(output.package, 'hello')
        output.line('(9/0) upgrading hello...', '\n', io.StringIO())
        self.assertEqual(meter.update_spans.call_args.args[1:], (0, 1))
        output.begin(['next'])
        self.assertEqual(meter.update_spans.call_args.args[1:], (0, 1))

    def test_bulk_managers_pass_processed_count_including_failed_managers(self):
        cfg = dict(self.cfg, output='styled')
        seen = []
        def execute(item, settings):
            seen.append(settings['_progress_batch'])
            return 23 if len(seen) == 1 else 0
        def plan(backend, *args, **kwargs):
            return workflows.Plan(backend, 'upgrade')
        with patch.object(upgrade_output, 'enabled', return_value=True), \
             patch.object(workflows.scopes, 'bulk', return_value=[('npm', 'global'), ('go', 'tools')]), \
             patch.object(workflows.scopes, 'make', side_effect=lambda name, scope: Backend(name)), \
             patch.object(workflows, 'available', return_value=True), \
             patch.object(workflows, 'plan', side_effect=plan), \
             patch.object(workflows, 'apply_compact', side_effect=execute), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(workflows.upgrade(self.args('up'), cfg), 1)
        self.assertEqual(seen, [(0, 2), (1, 2)])
        meter = Mock(); output = upgrade_output.Output('npm', dict(cfg, _progress_batch=(1, 2)), meter)
        output.commands_progress(0, 1)
        self.assertEqual(meter.update_spans.call_args.args[1:], (1, 2))
        self.assertIn('managers', str(meter.update_spans.call_args.args[0]))

    def test_modes_render_counts_and_data_gates_suppress_them(self):
        import progress
        for mode in ('none', 'spinner', 'bar', 'both'):
            out, err = Terminal(), Terminal()
            with self.subTest(mode=mode), patch.dict(os.environ, TERM='xterm', DOTS_PROGRESS=mode), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                 patch.object(progress, 'DELAY', .001), patch.object(progress, 'INTERVAL', .002):
                with workflows.progress('Preparing', dict(self.cfg, output='auto')) as meter:
                    output = upgrade_output.Output('npm', self.cfg, meter)
                    output.commands_progress(1, 3)
                    time.sleep(.03)
                self.assertEqual(out.getvalue(), '')
                if mode == 'none': self.assertEqual(err.getvalue(), '')
                else:
                    self.assertIn('1/3', err.getvalue())
                    self.assertEqual('[' in err.getvalue(), mode in ('bar', 'both'))
        for cfg, out in ((self.cfg, Terminal()), (dict(self.cfg, output='auto', _quiet_progress=True), Terminal()),
                         (dict(self.cfg, output='auto'), io.StringIO())):
            err = Terminal()
            with patch.dict(os.environ, TERM='xterm', DOTS_PROGRESS='both'), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch.object(progress, 'DELAY', .001):
                with workflows.progress('Must stay quiet', cfg): time.sleep(.01)
            self.assertEqual(err.getvalue(), '')

    def test_prompt_suspends_counted_bar_until_output_closes(self):
        import progress
        out, err = Terminal(), Terminal()
        with patch.dict(os.environ, TERM='xterm', DOTS_PROGRESS='both'), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
             patch.object(progress, 'DELAY', .001), patch.object(progress, 'INTERVAL', .002):
            with workflows.progress('Working', dict(self.cfg, output='auto')) as meter:
                output = upgrade_output.Output('npm', self.cfg, meter)
                output.commands_progress(0, 3); time.sleep(.02)
                output.prompt('Continue? ', err)
                before = err.getvalue(); time.sleep(.02)
                self.assertEqual(err.getvalue(), before)
                output.close()
            self.assertIsNone(progress._current)

    def test_export_reports_known_managers_and_still_emits_only_manifest_data(self):
        meter = Mock()
        @contextlib.contextmanager
        def phase(label): yield meter
        with patch.object(manifests, 'phase', side_effect=phase), \
             patch.object(manifests.scopes, 'inventory', return_value=[(Package('hello', '1'), 'explicit', '')]):
            data, failed = manifests.export(self.args('export', '--manager', 'npm'), dict(self.cfg, output='auto'))
        self.assertFalse(failed); self.assertEqual(data['groups'][0]['packages'][0]['name'], 'hello')
        self.assertEqual([call.args[1:] for call in meter.update.call_args_list], [(0, 1), (1, 1)])


if __name__ == '__main__': unittest.main()
