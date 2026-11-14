"""Hierarchical package work without native package effects or changed data streams."""
import contextlib
from fractions import Fraction
import io
import os
import re
import time
import unittest
from unittest.mock import Mock, patch

import test_workflows as fixtures
from test_upgrade_output import Terminal
from pkgs_lib import streams, upgrade_output, workflows, manifests, outdated, reports
from pkgs_lib.backends import Backend
from pkgs_lib.common import Package
import progress


class ProgressCounts(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    args = fixtures.Workflows.args

    @contextlib.contextmanager
    def terminal(self):
        out, err = Terminal(), Terminal()
        with patch.dict(os.environ, TERM='xterm', DOTS_PROGRESS='both'), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
             patch.object(progress, 'DELAY', 60):
            yield out, err

    def test_commands_advance_after_return_and_preserve_failure(self):
        plan = workflows.Plan(Backend('npm'), 'install', commands=[['first'], ['second'], ['third']])
        seen = []
        cfg = dict(self.cfg, output='auto')
        with self.terminal(), workflows.progress('Install packages', cfg) as meter:
            output = upgrade_output.Output('npm', cfg, meter, action='install')
            def run(command, settings, **kwargs):
                output.begin(command)
                seen.append((command, meter.overall[0], meter.step_hint))
                return 42 if command == ['second'] else 0
            with patch.object(streams, 'run', side_effect=run):
                self.assertEqual(workflows.apply(plan, dict(cfg, _upgrade_output=output)), 42)
            self.assertEqual(meter.overall[0], 1)  # The failed sequence is resolved, not successful.
        self.assertEqual(seen, [(['first'], Fraction(0), ('step', 1, 3)),
                                (['second'], Fraction(1, 3), ('step', 2, 3))])

    def test_independent_pip_targets_resolve_skipped_hooks_without_running_them(self):
        steps = [(['bad'], [['bad'], ['skipped-hook']]), (['good'], [['good']])]
        plan = workflows.Plan(Backend('pip'), 'upgrade', commands=[['bad'], ['skipped-hook'], ['good']], steps=steps)
        cfg = dict(self.cfg, output='auto'); seen = []
        with self.terminal(), workflows.progress('Upgrade', cfg) as meter:
            output = upgrade_output.Output('pip', cfg, meter)
            def run(command, settings, **kwargs):
                seen.append((command, meter.overall[0], meter.step_hint))
                return 17 if command == ['bad'] else 0
            with patch.object(streams, 'run', side_effect=run):
                self.assertEqual(workflows.apply(plan, dict(cfg, _upgrade_output=output)), 17)
        self.assertEqual(seen, [(['bad'], Fraction(0), ('step', 1, 3)),
                                (['good'], Fraction(2, 3), ('step', 3, 3))])
        self.assertEqual(plan.failed, [('bad', 17)]); self.assertEqual(plan.completed, ['good'])

    def test_native_bytes_are_local_and_never_finish_an_opaque_command(self):
        cfg = dict(self.cfg, output='auto')
        with self.terminal(), workflows.progress('Upgrade', cfg) as meter:
            with progress.sequence('Commands', 2) as commands:
                with commands.step('pip'):
                    output = upgrade_output.Output('pip', cfg, meter)
                    output.line('Progress 1024 of 4096', '\n', io.StringIO())
                    self.assertEqual(meter.state[1:], (1024, 4096))
                    self.assertEqual(meter.overall[0], 0)
                    output.line('Progress 4096 of 4096', '\n', io.StringIO())
                    self.assertEqual(meter.overall[0], 0)
                    output.line('Building wheel for hello', '\n', io.StringIO())
                    self.assertEqual(meter.state[1:], (0, 0))
                    self.assertEqual(meter.overall[0], 0)
                    output.line('Progress 2048 of 0', '\n', io.StringIO())
                    self.assertEqual(meter.state[1:], (0, 0))
                    self.assertNotIn('%', str(meter.state[0]))
                self.assertEqual(meter.overall[0], Fraction(1, 2))
        meter = Mock(); output = upgrade_output.Output('pacman', self.cfg, meter)
        output.line('(2/5) upgrading hello...', '\n', io.StringIO())
        self.assertEqual(meter.update_spans.call_args.args[1:], (1, 5))
        self.assertEqual(output.package, 'hello')
        output.line('(9/0) upgrading hello...', '\n', io.StringIO())
        self.assertEqual(meter.update_spans.call_args.args[1:], (0, 0))
        output.begin(['next'])
        self.assertEqual(meter.update_spans.call_args.args[1:], (0, 0))
        self.assertNotIn(' · commands', str(meter.update_spans.call_args_list))

    def test_bulk_managers_have_equal_shares_and_keep_just_in_time_planning(self):
        cfg = dict(self.cfg, output='styled'); seen = []; fractions = []; meters = []
        def selection(*args):
            meters.append(progress._current)
            return [('npm', 'global'), ('go', 'tools')]
        def plan(backend, *args, **kwargs):
            meters.append(progress._current)
            seen.append('plan '+backend.name)
            return workflows.Plan(backend, 'upgrade', commands=[[backend.name, 'first']] +
                                  ([[backend.name, 'second']] if backend.name == 'npm' else []))
        def run(command, settings, **kwargs):
            seen.append('run '+' '.join(command))
            fractions.append(progress._current.overall)
            return 23 if command == ['npm', 'second'] else 0
        with self.terminal(), patch.object(upgrade_output, 'enabled', return_value=True), \
             patch.object(workflows.scopes, 'bulk', side_effect=selection), \
             patch.object(workflows.scopes, 'make', side_effect=lambda name, scope: Backend(name)), \
             patch.object(workflows, 'available', return_value=True), \
             patch.object(workflows, 'plan', side_effect=plan), \
             patch.object(workflows, 'installed_versions', return_value={}), \
             patch.object(streams, 'run', side_effect=run):
            self.assertEqual(workflows.upgrade(self.args('up'), cfg), 1)
        self.assertEqual(seen, ['plan npm', 'run npm first', 'run npm second', 'plan go', 'run go first'])
        self.assertEqual([row[0] for row in fractions], [Fraction(1, 6), Fraction(1, 4), Fraction(2, 3)])
        self.assertEqual([row[1:] for row in fractions], [('manager', 1, 2), ('manager', 1, 2), ('manager', 2, 2)])
        self.assertIsNotNone(meters[0])
        self.assertTrue(all(meter is meters[0] for meter in meters))

    def test_finalization_keeps_a_reserved_share_after_native_commands(self):
        from pkgs_lib.npm_scripts import Pending
        cfg = dict(self.cfg, output='styled'); seen = []
        item = workflows.Plan(Backend('npm'), 'upgrade', commands=[['npm', 'install']])
        def versions(backend):
            seen.append(('inventory', progress._current.overall[0])); return {}
        def review(pending, item, cfg, output, rc):
            seen.append(('review', progress._current.overall[0])); return rc
        with self.terminal(), patch.object(workflows, 'installed_versions', side_effect=versions), \
             patch.object(streams, 'run', return_value=0), patch.object(Pending, 'review', new=review):
            self.assertEqual(workflows.apply_compact(item, cfg), 0)
        self.assertEqual(seen, [('inventory', 0), ('review', Fraction(2, 3)), ('inventory', Fraction(2, 3))])

    def test_explicit_preparation_and_execution_share_one_monotonic_meter(self):
        cfg = dict(self.cfg, output='styled'); seen = []
        backend = Backend('npm')
        item = workflows.Plan(backend, 'install', ['hello'], commands=[['first'], ['second']])
        def record(label):
            meter = progress._current
            seen.append((label, meter, meter.overall[0]))
        def prepare(*args, **kwargs):
            record('prepare'); return item
        def run(command, *args, **kwargs):
            record(command[0]); return 0
        with self.terminal(), patch.object(upgrade_output, 'enabled', return_value=True), \
             patch.object(workflows, 'plan', side_effect=prepare), \
             patch.object(streams, 'run', side_effect=run), \
             patch.object(upgrade_output.Output, 'result', side_effect=lambda *args, **kwargs: record('result')):
            self.assertEqual(workflows.execute(backend, 'install', ['hello'], self.args('in', 'hello'), cfg), 0)
        self.assertEqual([row[0] for row in seen], ['prepare', 'first', 'second', 'result'])
        self.assertEqual([row[2] for row in seen], [0, Fraction(1, 3), Fraction(1, 2), Fraction(2, 3)])
        self.assertTrue(all(row[1] is seen[0][1] for row in seen))
        self.assertEqual(seen[0][1].overall[0], 1)

    def test_declined_removal_freezes_preparation_without_native_execution(self):
        cfg = dict(self.cfg, output='styled'); seen = []
        backend = Backend('npm')
        item = workflows.Plan(backend, 'uninstall', ['hello'], commands=[['remove']])
        def prepare(*args, **kwargs):
            seen.append(progress._current); return item
        def decline(*args):
            self.assertIs(progress._current, seen[0])
            self.assertEqual(progress._current.overall[0], 0)
            return False
        with self.terminal() as (out, _), patch.object(upgrade_output, 'enabled', return_value=True), \
             patch.object(workflows, 'plan', side_effect=prepare), \
             patch.object(workflows, 'confirm', side_effect=decline), patch.object(streams, 'run') as run:
            self.assertEqual(workflows.execute(backend, 'uninstall', ['hello'], self.args('un', 'hello'), cfg), 0)
            self.assertIn('Cancelled; no packages changed.', out.getvalue())
        run.assert_not_called()
        self.assertTrue(seen[0].cancelled)
        self.assertEqual(seen[0].overall[0], 0)
        self.assertIsNone(progress._current)

    def test_native_cancellation_freezes_before_command_completion(self):
        for status in (130, 143, -2, -15):
            cfg = dict(self.cfg, output='styled'); seen = []
            backend = Backend('npm')
            item = workflows.Plan(backend, 'install', ['hello'], commands=[['first'], ['second']])
            def run(*args, **kwargs):
                seen.append(progress._current); return status
            with self.subTest(status=status), self.terminal(), \
                 patch.object(upgrade_output, 'enabled', return_value=True), \
                 patch.object(workflows, 'plan', return_value=item), patch.object(streams, 'run', side_effect=run) as native:
                rc = workflows.execute(backend, 'install', ['hello'], self.args('in', 'hello'), cfg)
            self.assertEqual(rc, status if status > 0 else 128-status)
            native.assert_called_once()
            self.assertTrue(seen[0].cancelled)
            self.assertEqual(seen[0].overall[0], Fraction(1, 3))

    def test_pip_cancellation_preserves_interrupt_and_freezes_the_step(self):
        for status in (130, 143):
            cfg = dict(self.cfg, output='auto')
            item = workflows.Plan(Backend('pip'), 'upgrade', commands=[['bad'], ['unrun']],
                                  steps=[(['bad'], [['bad']]), (['unrun'], [['unrun']])])
            with self.subTest(status=status), self.terminal(), workflows.progress('Upgrade', cfg) as meter:
                output = upgrade_output.Output('pip', cfg, meter)
                with patch.object(streams, 'run', return_value=status) as native:
                    with self.assertRaises(KeyboardInterrupt):
                        workflows.apply(item, dict(cfg, _upgrade_output=output))
                native.assert_called_once()
                self.assertTrue(meter.cancelled)
                self.assertEqual(meter.overall[0], 0)

    def test_modes_render_named_counts_and_data_gates_suppress_them(self):
        for mode in ('none', 'spinner', 'bar', 'both'):
            out, err = Terminal(), Terminal()
            with self.subTest(mode=mode), patch.dict(os.environ, TERM='xterm', DOTS_PROGRESS=mode), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                 patch.object(progress, 'DELAY', .001), patch.object(progress, 'INTERVAL', .002):
                with workflows.work_sequence('Installing', 3, dict(self.cfg, output='auto')) as sequence:
                    with sequence.step('npm · Installing', 1): time.sleep(.03)
                self.assertEqual(out.getvalue(), '')
                if mode == 'none': self.assertEqual(err.getvalue(), '')
                else:
                    self.assertNotIn('Overall', err.getvalue())
                    self.assertIn('33%', err.getvalue())
                    self.assertIn('2/3', err.getvalue())
                    self.assertNotIn('step 2/3', err.getvalue())
                    self.assertEqual(bool(re.search(r'\[[#━-]+\]', err.getvalue())), mode in ('bar', 'both'))
        for cfg, out in ((self.cfg, Terminal()), (dict(self.cfg, output='auto', _quiet_progress=True), Terminal()),
                         (dict(self.cfg, output='auto'), io.StringIO())):
            err = Terminal()
            with patch.dict(os.environ, TERM='xterm', DOTS_PROGRESS='both'), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch.object(progress, 'DELAY', .001):
                with workflows.work_sequence('Must stay quiet', 2, cfg) as work:
                    with work.step('Quiet'): time.sleep(.01)
            self.assertEqual(err.getvalue(), '')

    def test_prompt_suspends_both_rows_and_preserves_overall(self):
        out, err = Terminal(), Terminal()
        with patch.dict(os.environ, TERM='xterm', DOTS_PROGRESS='both'), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
             patch.object(progress, 'DELAY', .001), patch.object(progress, 'INTERVAL', .002):
            cfg = dict(self.cfg, output='auto')
            with workflows.work_sequence('Working', 3, cfg) as sequence:
                with sequence.step('npm', 1):
                    meter = progress._current
                    output = upgrade_output.Output('npm', cfg, meter)
                    time.sleep(.02); overall = meter.overall
                    output.prompt('Continue? ', err)
                    before = err.getvalue(); time.sleep(.02)
                    self.assertEqual(err.getvalue(), before)
                    self.assertEqual(meter.overall, overall)
                    output.close()
            self.assertIsNone(progress._current)

    def test_export_uses_manager_sequence_without_changing_manifest_data(self):
        seen = []; meters = []
        def selection(*args):
            meters.append(progress._current)
            return [('npm', 'global')]
        def inventory(*args, **kwargs):
            meters.append(progress._current)
            seen.append(progress._current.overall)
            return [(Package('hello', '1'), 'explicit', '')]
        with self.terminal() as (out, err), patch.object(manifests.scopes, 'inventory', side_effect=inventory), \
             patch.object(manifests.scopes, 'bulk', side_effect=selection):
            data, failed = manifests.export(self.args('export'), dict(self.cfg, output='auto'))
        self.assertFalse(failed); self.assertEqual(data['groups'][0]['packages'][0]['name'], 'hello')
        self.assertEqual(seen, [(Fraction(0), 'manager', 1, 1)])
        self.assertIsNotNone(meters[0]); self.assertIs(meters[0], meters[1])
        self.assertEqual(out.getvalue(), '')

    def test_update_listing_gives_each_manager_an_equal_share(self):
        seen = []
        def inspect(backend, *args, **kwargs):
            seen.append(progress._current.overall)
            return dict(manager=backend.name, scope=backend.scope, packages=[], skipped=[], error='', status='ok')
        with self.terminal(), patch.object(outdated.scopes, 'bulk', return_value=[('npm', 'global'), ('go', 'tools')]), \
             patch.object(outdated.scopes, 'make', side_effect=lambda name, scope: Backend(name)), \
             patch.object(outdated, 'available', return_value=True), patch.object(outdated, 'inspect', side_effect=inspect):
            self.assertEqual(outdated.cli(self.args('up', '--list'), dict(self.cfg, output='auto')), 0)
        self.assertEqual(seen, [(Fraction(0), 'manager', 1, 2), (Fraction(1, 2), 'manager', 2, 2)])


if __name__ == '__main__': unittest.main()
