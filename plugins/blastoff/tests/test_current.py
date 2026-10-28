"""Pretty current/doctor status, explicit JSON and read-only local discovery."""
import io
import json
import os
import re
import shutil
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from test_blastoff import CORE, ROOT, Harness, core


class CurrentOutput(Harness):
    def sample(self):
        self.write(self.config, '[directory]\nstyle="purple"\n')
        self.theme('blastoff', self.config.read_text())

    def snapshot(self):
        return {str(p): (p.lstat().st_mode, p.lstat().st_size, p.lstat().st_mtime_ns)
                for p in [self.home, *self.home.rglob('*')]}

    def test_default_is_human_readable_and_aliases_match(self):
        self.sample()
        before = self.snapshot()
        result = self.invoke('current')
        self.assertIn('Current configuration', result.stdout)
        self.assertRegex(result.stdout, r'MATCHES +blastoff')
        self.assertIn(str(self.config), result.stdout)
        self.assertIn('regular file', result.stdout)
        self.assertNotIn('matching_themes', result.stdout)
        self.assertNotIn('\x1b', result.stdout)
        self.assertEqual(result.stderr, '')
        self.assertEqual(self.invoke('-t').stdout, result.stdout)
        self.assertEqual(self.invoke('--theme').stdout, result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_json_schema_is_unchanged_and_uncolored(self):
        self.sample()
        result = self.invoke('current', '--json', '--color', 'always')
        self.assertEqual({k:v for k,v in json.loads(result.stdout).items() if k != 'provenance'}, {
            'config': str(self.config), 'resolved_config': str(self.config), 'exists': True,
            'matching_themes': ['blastoff'], 'symlink': False,
        })
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertNotIn('\x1b', result.stdout)

    def test_missing_no_match_and_duplicate_matches(self):
        before = self.snapshot()
        self.assertIn('(no active config)', self.invoke('current').stdout)
        self.assertEqual(self.snapshot(), before)
        self.write(self.config, '# custom configuration\n')
        self.assertIn('(no local match)', self.invoke('current').stdout)
        self.theme('zebra', self.config.read_text())
        self.theme('alpha', self.config.read_text())
        self.assertRegex(self.invoke('current').stdout, r'MATCHES +alpha, zebra')
        self.assertEqual(json.loads(self.invoke('current', '--json').stdout)['matching_themes'], ['alpha', 'zebra'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink fixture')
    def test_symlink_status_and_missing_target_error_stay_read_only(self):
        target = self.write(self.home/'target.toml', '# target\n')
        self.config.parent.mkdir()
        self.config.symlink_to(target)
        before = self.snapshot()
        self.assertIn('symlink', self.invoke('current').stdout)
        self.assertTrue(json.loads(self.invoke('current', '--json').stdout)['symlink'])
        self.assertEqual(self.snapshot(), before)
        target.unlink()
        before = self.snapshot()
        self.assertEqual(self.invoke('current', code=1).stdout, '')
        self.assertEqual(self.snapshot(), before)

    def test_color_policy_and_terminal_resets(self):
        self.sample()
        self.env.pop('NO_COLOR')
        self.env['TERM'] = 'xterm-256color'
        self.env.update(DOTS_MENU_CAPTURE='1', DOTS_COLOR='never', DOTS_ICONS='never')
        plain = self.invoke('current').stdout
        self.assertNotIn('\x1b', plain)
        forced = self.invoke('current', '--color', 'always').stdout
        self.assertIn('\x1b[1;96m', forced)
        self.assertIn('\x1b[94m', forced)
        self.assertIn('\x1b[0m', forced)
        self.assertEqual(re.sub(r'\x1b\[[0-9;]*m', '', forced), plain)
        self.assertNotIn('\x1b', self.invoke('current', '--color', 'never').stdout)
        self.env['NO_COLOR'] = '1'
        self.assertIn('\x1b', self.invoke('current', '--color', 'always').stdout)
        self.assertNotIn('\x1b', self.invoke('current', '--color', 'auto').stdout)

    @unittest.skipUnless(os.name == 'posix', 'Native terminal fixture')
    def test_native_tty_and_bash_wrapper(self):
        self.sample()
        self.env.pop('NO_COLOR')
        self.env['TERM'] = 'xterm-256color'
        import sys

        from pty_support import terminal
        code, screen = terminal([sys.executable, '-I', str(CORE), 'current'], self.env, columns=80, rows=24)
        self.assertEqual(code, 0)
        self.assertIn(b'Current configuration', screen)
        self.assertIn(b'\x1b[94m', screen)
        if shutil.which('bash'):
            result = subprocess.run([shutil.which('bash'), str(ROOT/'bin/blastoff'), 'current'],
                                    env=self.env, capture_output=True, text=True, timeout=5, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, self.invoke('current').stdout)

    @unittest.skipUnless(os.name == 'posix', 'Control character filename fixture')
    def test_human_paths_cannot_inject_terminal_controls(self):
        self.config = self.home/'config\x1b[31m\n.toml'
        self.env['STARSHIP_CONFIG'] = str(self.config)
        self.write(self.config, '# fixture\n')
        text = self.invoke('current').stdout
        self.assertNotIn('\x1b', text)
        self.assertIn('\\x1b', text)
        self.assertEqual(json.loads(self.invoke('current', '--json').stdout)['config'], str(self.config))


class DoctorOutput(Harness):
    def snapshot(self):
        return {str(p): (p.lstat().st_mode, p.lstat().st_size, p.lstat().st_mtime_ns)
                for p in [self.home, *self.home.rglob('*')]}

    def test_default_is_human_readable_and_read_only(self):
        before = self.snapshot()
        result = self.invoke('doctor')
        self.assertTrue(result.stdout.startswith('Blastoff doctor\n'))
        for value in (core.VERSION, str(self.config), str(self.store), 'not found (needed for presets)',
                      'not found (optional)', 'THEMES', 'MODULES', 'PYTHON'):
            self.assertIn(value, result.stdout)
        self.assertNotIn('config_exists', result.stdout)
        self.assertNotIn('\x1b', result.stdout)
        self.assertEqual(result.stderr, '')
        self.assertEqual(self.snapshot(), before)

    def test_explicit_json_preserves_schema(self):
        import sys
        result = self.invoke('doctor', '--json', '--color', 'always')
        self.assertEqual(json.loads(result.stdout), {
            'version': core.VERSION, 'python': sys.version.split()[0], 'config': str(self.config), 'resolved_config': str(self.config),
            'blastoff_home': str(self.store), 'themes': str(self.store/'themes'),
            'modules': str(self.store/'modules'), 'starship': None, 'fzf': None, 'gum': None,
            'config_exists': False, 'config_symlink': False,
        })
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertNotIn('\x1b', result.stdout)

    def test_color_policy(self):
        self.env.pop('NO_COLOR')
        self.env['TERM'] = 'xterm-256color'
        self.env.update(DOTS_MENU_CAPTURE='1', DOTS_COLOR='never', DOTS_ICONS='never')
        plain = self.invoke('doctor').stdout
        forced = self.invoke('doctor', '--color', 'always').stdout
        self.assertNotIn('\x1b', plain)
        self.assertIn('\x1b[1;96m', forced)
        self.assertIn('\x1b[94m', forced)
        self.assertEqual(re.sub(r'\x1b\[[0-9;]*m', '', forced), plain)
        self.assertNotIn('\x1b', self.invoke('doctor', '--color', 'never').stdout)
        self.env['NO_COLOR'] = '1'
        self.assertIn('\x1b', self.invoke('doctor', '--color', 'always').stdout)
        self.assertNotIn('\x1b', self.invoke('doctor', '--color', 'auto').stdout)

    def test_does_not_read_config_or_launch_tools(self):
        self.write(self.config, 'this is not TOML\x1b[31m\n')
        before = self.snapshot()
        output = io.StringIO()
        with patch.dict(os.environ, self.env, clear=True), redirect_stdout(output), \
                patch.object(core, 'read', side_effect=AssertionError('must not read config')), \
                patch.object(core.subprocess, 'Popen', side_effect=AssertionError('must not launch tools')), \
                patch.object(core.shutil, 'which', return_value='/tools/found\x1b[31m'):
            self.assertEqual(core.run(['doctor']), 0)
        self.assertIn('present', output.getvalue())
        self.assertIn('/tools/found\\x1b[31m', output.getvalue())
        self.assertNotIn('\x1b', output.getvalue())
        self.assertEqual(self.snapshot(), before)

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink fixture')
    def test_symlink_status_preserves_existing_presence_semantics(self):
        self.config.parent.mkdir()
        self.config.symlink_to(self.home/'missing-target')
        before = self.snapshot()
        self.assertIn('present (symlink)', self.invoke('doctor').stdout)
        result = json.loads(self.invoke('doctor', '--json').stdout)
        self.assertTrue(result['config_exists'])
        self.assertTrue(result['config_symlink'])
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
