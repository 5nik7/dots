#!/usr/bin/env python3
"""Shared Markdown consumers, failures and Config contracts in owned roots."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from functools import partial
from unittest.mock import patch

from test_menus import MenuFixture, ROOT
import markdown_viewer as viewer
from files.catalog import Presentation


class Markdown(MenuFixture):
    def setUp(self):
        super().setUp()
        self.ui = Presentation(io.StringIO(), terminal=True)
        self.ui.width = 40

    def test_priority_each_available_position_and_builtin(self):
        for index, selected in enumerate(viewer.PRIORITY):
            available = set(viewer.PRIORITY[index:]) - {'builtin'}
            with patch.object(viewer, 'executable', side_effect=lambda name: name if name in available else None), \
                 patch('themes.file_preview.run_renderer', return_value=b'rendered') as render:
                result = viewer.render(b'# Source', self.ui, viewer='auto')
                if selected == 'builtin':
                    self.assertEqual(result, b'# Source'); render.assert_not_called()
                else:
                    self.assertEqual(result, b'rendered')
                    self.assertEqual(render.call_args.args[0][0], selected)

    def test_explicit_choices_and_failure_fallback_without_retry(self):
        for selected in viewer.CHOICES[1:]:
            with patch.object(viewer, 'executable', side_effect=lambda name: name), \
                 patch('themes.file_preview.run_renderer', return_value=b'rendered') as render:
                result = viewer.render(b'# Source', self.ui, viewer=selected)
                if selected == 'builtin':
                    self.assertEqual(result, b'# Source'); render.assert_not_called()
                else:
                    self.assertEqual(render.call_args.args[0][0], selected)
        for failure in (None, b'', OSError('gone')):
            def run(command, data, env):
                if command[0] == 'glow':
                    if isinstance(failure, Exception): raise failure
                    return failure
                return b'fallback'
            with patch.object(viewer, 'executable', side_effect=lambda name: name), \
                 patch('themes.file_preview.run_renderer', side_effect=run) as render, redirect_stderr(io.StringIO()) as notice:
                self.assertEqual(viewer.render(b'# Source', self.ui, viewer='glow'), b'fallback')
                self.assertEqual([c.args[0][0] for c in render.call_args_list], ['glow', 'leaf'])
                self.assertIn('automatic fallback', notice.getvalue())

    def test_literal_input_plain_color_and_control_safety(self):
        source = b'# $(touch NOT-RUN)\n\x1b]52;c;bad\x07\n'
        output = b'\x1b[31mred\x1b[0m\x1b]52;c;bad\x07\x1b[2J\n'
        for color in (False, True):
            self.ui.color = color
            with patch.object(viewer, 'executable', return_value='/literal program'), \
                 patch('themes.file_preview.run_renderer', return_value=output) as render:
                result = viewer.render(source, self.ui, viewer='leaf')
                self.assertEqual(result, b'\x1b[31mred\x1b[0m\n' if color else b'red\n')
                self.assertIn(b'$(touch NOT-RUN)', render.call_args.args[1])
                self.assertNotIn(b'\x1b', render.call_args.args[1])
                self.assertNotIn('$(touch', ' '.join(render.call_args.args[0]))
        with patch.object(viewer, 'executable', side_effect=AssertionError('builtin probes')):
            self.assertEqual(viewer.render(b'# Plain\r\n', self.ui, viewer='builtin'), b'# Plain\n')
        self.assertFalse((self.home/'NOT-RUN').exists())

    def test_deadline_output_limit_and_renderer_exit_are_fallbacks(self):
        from themes.file_preview import run_renderer
        cases = ['import time;time.sleep(5)', 'import sys;sys.stdout.write("x"*4096)', 'raise SystemExit(2)']
        for code in cases:
            with patch.object(viewer, 'executable', side_effect=lambda name: sys.executable if name=='leaf' else None), \
                 patch.object(viewer, 'arguments', return_value=[sys.executable, '-c', code]), \
                 patch('themes.file_preview.run_renderer', partial(run_renderer, timeout=.15, limit=256)), \
                 redirect_stderr(io.StringIO()):
                self.assertEqual(viewer.render(b'# Source', self.ui, viewer='leaf'), b'# Source')

    def test_executable_aliases_and_portable_choices(self):
        with patch('shutil.which', side_effect=lambda name: '/bin/'+name if name in ('rich','batcat') else None):
            self.assertEqual(viewer.executable('rich-cli'), '/bin/rich')
            self.assertEqual(viewer.executable('bat'), '/bin/batcat')
            self.assertEqual(viewer.availability(), 'auto, rich-cli, bat, builtin')

    def test_popup_fallback_notice_stays_visible_in_the_reader(self):
        with patch.object(viewer, 'executable', return_value=None), redirect_stderr(io.StringIO()) as stderr:
            result = viewer.render(b'# Source', self.ui, viewer='leaf', inline_notice=True)
        self.assertIn(b'using automatic fallback.', result)
        self.assertTrue(result.endswith(b'# Source'))
        self.assertEqual(stderr.getvalue(), '')

    def test_installed_renderers_captured_in_owned_environment(self):
        for name in ('leaf', 'mdcat', 'rich-cli', 'bat', 'cat'):
            if not viewer.executable(name): continue
            for width in (40, 80, 120):
                self.ui.width = width
                for color in (False, True):
                    self.ui.color = color
                    with redirect_stderr(io.StringIO()) as notices:
                        result = viewer.render(b'# Markdown probe\n\n**bold** and `code`.\n', self.ui, viewer=name)
                    self.assertEqual(notices.getvalue(), '', (name, width, color))
                    self.assertIn(b'Markdown probe', result)
                    if not color: self.assertNotIn(b'\x1b', result)


class Configuration(MenuFixture):
    def setUp(self):
        runtime = {key: os.environ[key] for key in ('TERMUX__PREFIX', 'TERMUX_VERSION') if key in os.environ}
        super().setUp()
        # Retain the outer fixture's owned loader prefix and platform identity.
        self.env.update(runtime)
        os.environ.update(runtime)
        self.root = Path(self.env['DOTS'])
        shutil.copytree(ROOT/'default', self.root/'default')
        # Unqualified saves resolve the execution platform, not DOTS_PROFILE.
        for name in ('linux', 'wsl', 'windows', 'termux'):
            directory = self.root/'profiles'/name
            directory.mkdir(parents=True)
            (directory/'profile.json').write_text(json.dumps(dict(schema=1, id=name, files={}, settings={})))
        shutil.copy2(ROOT/'profiles/termux/config.json', self.root/'profiles/termux/config.json')

    def test_defaults_override_reset_validation_and_completion(self):
        from config_values import Controls, constraints, validate_value, candidates
        from config_cli import ControlPlan as Plan
        from profile_config import context
        selected = context(self.root, 'linux')
        controls = Controls(self.root, selected)
        key = 'apps.cli.markdown_viewer'
        self.assertEqual(controls.resolve(key)['value'], 'auto')
        self.assertEqual(Controls(self.root, context(self.root,'termux')).resolve(key)['value'], 'leaf')
        self.assertEqual(constraints(controls.defaults, key)['choices'], list(viewer.CHOICES))
        with patch('shutil.which', side_effect=AssertionError('completion probes PATH')):
            self.assertEqual(candidates(self.root, key), list(viewer.CHOICES))
        for choice in viewer.CHOICES:
            validate_value(controls.defaults, tuple(key.split('.')), choice)
        for bad in ('lesf', 'leaf --watch', '$(no)', True):
            with self.assertRaises(ValueError): validate_value(controls.defaults, tuple(key.split('.')), bad)
        plan = Plan(self.root, context(self.root, 'linux'))
        plan.edit(key, 'cat')
        plan.apply('set')
        self.assertEqual(Controls(self.root, selected).resolve(key)['value'], 'cat')
        plan = Plan(self.root, context(self.root, 'linux'))
        plan.edit(key, None, unset=True)
        plan.apply('unset')
        self.assertEqual(Controls(self.root, selected).resolve(key)['value'], 'auto')

    def test_save_is_next_view_and_does_not_publish(self):
        from config_cli import ControlPlan
        from config_refresh import effective, after_save, preview_save
        from profile_config import context
        from config_values import current
        from style_config import current as styles
        current.cache_clear(); styles.cache_clear()
        self.addCleanup(current.cache_clear); self.addCleanup(styles.cache_clear)
        selected = context(self.root)
        self.assertEqual(selected['layers'][-1]['id'], selected['facts']['platform'])
        plan = ControlPlan(self.root, selected)
        plan.edit('apps.cli.markdown_viewer', 'cat')
        self.assertIn('no theme publication', preview_save(self.root, plan)['reason'])
        before = effective(self.root)
        plan.apply('set')
        current.cache_clear(); styles.cache_clear()
        with patch('config_refresh.refresh', side_effect=AssertionError('renderer save published')):
            result = after_save(self.root, before)
        self.assertEqual(result['consumers'], [dict(app='cli',status='next invocation')])

    def test_fresh_controller_preview_is_next_invocation_without_writes(self):
        self.check_preview([sys.executable, '-B', str(ROOT/'lib/dots/config_cli.py')])

    @unittest.skipUnless(shutil.which('bash'), 'Bash unavailable; frontend not verified')
    def test_bash_preview_is_next_invocation_without_writes(self):
        shutil.copytree(ROOT/'lib', self.root/'lib', symlinks=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(ROOT/'bin', self.root/'bin', symlinks=True)
        self.check_preview([shutil.which('bash'), str(self.root/'bin/dots'), 'config'])

    def check_preview(self, command):
        from files.transactions import digest
        from profile_config import context
        selected = context(self.root)['current']
        before = digest(self.base)
        env = dict(self.env)
        env.pop('PYTHONPATH', None)
        result = subprocess.run([
            *command,
            'set', 'apps.cli.markdown_viewer', 'cat', '--profile', selected,
            '--dry-run', '--json',
        ], env=env, cwd=self.home, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertNotIn(b'\x1b', result.stdout)
        preview = json.loads(result.stdout)
        self.assertEqual(preview['status'], 'preview')
        self.assertEqual(preview['refresh']['reason'],
                         'Next invocation or popup; no theme publication or reload')
        self.assertIn('cli', preview['refresh']['consumers'])
        self.assertEqual(digest(self.base), before)


if __name__ == '__main__': unittest.main()
