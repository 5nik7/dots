#!/usr/bin/env python3
"""Approval UIs with disposable homes, catalogs and local-only Git remotes."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest
from unittest import mock

import test_file_operations as files
import test_git_operations as git
import test_theme_picker as picker

PROJECT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
sys.path.insert(0, str(PROJECT / 'lib/dots'))
import interaction


def install_gum(base, env):
    """A deterministic tool fixture that can also simulate input drift."""
    directory = base / 'confirmation tools'
    directory.mkdir()
    tool = directory / 'gum'
    tool.write_text('#!' + sys.executable + '''
import json, os, sys
from pathlib import Path
with (Path(os.environ['HOME']) / 'gum-calls').open('a') as out:
    out.write(json.dumps({'args':sys.argv[1:], 'color':os.environ.get('NO_COLOR'),
        'theme':os.environ.get('GUM_CHOOSE_CURSOR_FOREGROUND')}) + '\\n')
if os.environ.get('GUM_DRIFT'):
    Path(os.environ['GUM_DRIFT']).write_text('changed during review')
value = os.environ.get('GUM_CHOICE', 'Cancel')
if value.startswith('EXIT:'):
    sys.exit(int(value.split(':')[1]))
print(value)
''')
    tool.chmod(0o700)
    env['PATH'] = str(directory) + os.pathsep + env['PATH']
    env['TERM'] = 'xterm-256color'
    return tool


class Confirmations(unittest.TestCase):
    terminal = picker.Picker.terminal

    def fixture(self, kind='files'):
        fixture = files.Operations() if kind == 'files' else git.GitOperations()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.home = fixture.home
        self.env = fixture.env
        self.env.update(XDG_CACHE_HOME=str(self.home / '.cache'),
                        XDG_STATE_HOME=str(self.home / '.state'),
                        XDG_DATA_HOME=str(self.home / '.data'),
                        TMPDIR=str(fixture.base), PYTHONDONTWRITEBYTECODE='1')
        install_gum(fixture.base, self.env)
        if kind == 'files':
            argv = [sys.executable, '-B', str(PROJECT / 'lib/dots/files/manage.py'), 'add', str(fixture.path)]
            self.before = fixture.path.read_bytes()
        else:
            _, self.bare, self.repo = fixture.remote_repo('approval')
            fixture.owned_remote(self.repo, self.bare)
            (self.repo / 'new').write_text('new\n')
            fixture.git(self.repo, 'add', 'new')
            self.before = fixture.git(self.repo, 'rev-parse', 'HEAD')
            self.index = (self.repo / '.git/index').read_bytes()
            argv = [BASH, str(PROJECT / 'bin/dots'), 'git', 'publish', '-C', str(self.repo), '--config', str(fixture.config)]
        self.script = shlex.join(argv)
        return fixture

    def unchanged(self, fixture, kind):
        if kind == 'files':
            self.assertEqual(fixture.path.read_bytes(), self.before)
            self.assertFalse(fixture.path.is_symlink())
            self.assertEqual(fixture.records(), [])
            self.assertFalse((self.home / '.state').exists())
        else:
            self.assertEqual(fixture.git(self.repo, 'rev-parse', 'HEAD'), self.before)
            self.assertEqual(fixture.git(self.bare, 'rev-parse', 'main'), self.before)
            self.assertEqual((self.repo / '.git/index').read_bytes(), self.index)
            self.assertFalse(list(self.repo.rglob('git-it.lock')))

    def test_cancel_errors_and_interrupt_do_not_mutate(self):
        for kind in ('files', 'git'):
            for choice, code in [('Cancel', 0), ('EXIT:1', 1), ('EXIT:7', 1),
                                 ('EXIT:130', 130), ('unexpected', 1), ('Apply\nCancel', 1)]:
                with self.subTest(kind=kind, choice=choice):
                    fixture = self.fixture(kind)
                    self.env['GUM_CHOICE'] = choice
                    out = self.terminal(code=code)
                    self.assertNotIn(b'[y/N]', out)  # Failed UI never retries.
                    self.unchanged(fixture, kind)
                    calls = (self.home / 'gum-calls').read_text().splitlines()
                    self.assertEqual(len(calls), 1)
                    args = json.loads(calls[0])['args']
                    self.assertIn('--selected=Cancel', args)
                    self.assertEqual(args[-2:], ['Cancel', 'Apply' if kind == 'files' else 'Publish'])

    def test_approval_uses_existing_operations(self):
        for kind in ('files', 'git'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                self.env['GUM_CHOICE'] = 'Apply' if kind == 'files' else 'Publish'
                self.terminal()
                if kind == 'files':
                    self.assertTrue(fixture.path.is_symlink())
                    self.assertEqual(fixture.path.read_bytes(), self.before)
                    self.assertEqual(len(fixture.records()), 1)
                else:
                    head = fixture.git(self.repo, 'rev-parse', 'HEAD')
                    self.assertNotEqual(head, self.before)
                    self.assertEqual(fixture.git(self.bare, 'rev-parse', 'main'), head)
                    self.assertFalse(list(self.repo.rglob('git-it.lock')))

    def test_drift_during_approval_is_refused(self):
        for kind in ('files', 'git'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                target = fixture.path if kind == 'files' else self.repo / 'new'
                self.env.update(GUM_DRIFT=str(target), GUM_CHOICE='Apply' if kind == 'files' else 'Publish')
                self.terminal(code=1)
                self.assertEqual(target.read_text(), 'changed during review')
                if kind == 'files':
                    self.assertFalse(target.is_symlink())
                    self.assertEqual(fixture.records(), [])
                else:
                    self.unchanged(fixture, kind)

    def test_dumb_redirected_and_json_keep_plain_prompt(self):
        for kind in ('files', 'git'):
            for mode in ('dumb', 'stdout', 'stderr', 'json', 'json-tty'):
                with self.subTest(kind=kind, mode=mode):
                    fixture = self.fixture(kind)
                    script = self.script
                    captured = self.home / 'captured'
                    if mode == 'dumb':
                        self.env['TERM'] = 'dumb'
                    elif mode.startswith('json'):
                        script += ' --json'
                        if mode == 'json':
                            script += ' > ' + shlex.quote(str(captured))
                    else:
                        script += (' > ' if mode == 'stdout' else ' 2> ') + shlex.quote(str(captured))
                    if mode == 'stderr':
                        # Prompt is deliberately redirected; wait for the visible preview.
                        marker = b'Retained backups:' if kind == 'files' else b'Published child pointers'
                    else:
                        marker = b'[y/N]'
                    output = self.terminal(script, steps=((marker, b'n\r'),))
                    self.assertFalse((self.home / 'gum-calls').exists())
                    self.unchanged(fixture, kind)
                    if mode == 'json-tty':
                        records = [json.loads(line) for line in picker.ANSI.sub(b'', output).splitlines() if line.startswith(b'{')]
                        self.assertEqual(len(records), 1)
                        self.assertEqual(records[0]['schema'], 1)
                    if mode == 'json':
                        data = json.loads(captured.read_text())
                        self.assertEqual(data['schema'], 1)
                        self.assertNotIn('\x1b', captured.read_text())

    def test_yes_dry_run_and_nonterminal_bypass_gum(self):
        for kind in ('files', 'git'):
            for mode in ('--dry-run', '--yes', ''):
                with self.subTest(kind=kind, mode=mode):
                    fixture = self.fixture(kind)
                    if mode:
                        self.terminal(self.script + ' ' + mode)
                    else:
                        result = subprocess.run([BASH, '-c', self.script], env=self.env,
                                                capture_output=True, text=True, timeout=30)
                        self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertFalse((self.home / 'gum-calls').exists())
                    if mode != '--yes':
                        self.unchanged(fixture, kind)

    def test_missing_tools_do_not_start_bridge(self):
        for missing in ('bash', 'gum'):
            with mock.patch.dict(os.environ, TERM='xterm'), \
                    mock.patch.object(sys.stdin, 'isatty', return_value=True), \
                    mock.patch.object(sys.stdout, 'isatty', return_value=True), \
                    mock.patch.object(sys.stderr, 'isatty', return_value=True), \
                    mock.patch.object(interaction.shutil, 'which', side_effect=lambda tool: None if tool == missing else '/tool'), \
                    mock.patch.object(interaction.subprocess, 'run') as run:
                self.assertIsNone(interaction.gum_confirm('Apply?'))
                run.assert_not_called()
        # Bash uses only builtins when Gum is unavailable; no FZF fallback.
        script = ('source ' + shlex.quote(str(PROJECT / 'lib/dots/interactive.bash')) +
                  '; command() { return 1; }; if dots::gum_confirm_available; then exit 1; fi')
        self.fixture()
        self.terminal(script)

    def test_presentation_policy_and_theme_inheritance(self):
        self.fixture()
        self.env.update(DOTS_COLOR='never', DOTS_ICONS='never', FORCE_COLOR='1',
                        GUM_CHOOSE_CURSOR_FOREGROUND='#123456')
        self.terminal()
        call = json.loads((self.home / 'gum-calls').read_text())
        self.assertEqual(call['color'], '1')
        self.assertEqual(call['theme'], '#123456')
        self.assertIn('--show-help=false', call['args'])
        self.assertIn('--cursor=> ', call['args'])

    @unittest.skipUnless(picker.NATIVE_GUM, 'native Gum is unavailable')
    def test_native_gum_default_cancel_apply_and_ctrl_c(self):
        for kind in ('files', 'git'):
            for width, keys, code in [(40, b'\r', 0), (80, b'\x1b[B\r', 0),
                                      (80, b'\x03', 130), (40, b'\x1b', 1)]:
                with self.subTest(kind=kind, width=width, keys=keys):
                    fixture = self.fixture(kind)
                    tool = fixture.base / 'confirmation tools/gum'
                    tool.unlink(); tool.symlink_to(picker.NATIVE_GUM)
                    if keys == b'\x1b[B\r':
                        self.env.update(DOTS_COLOR='always', DOTS_ICONS='always')
                    header = b'Apply these changes?' if kind == 'files' else b'Publish the selected changes?'
                    output = self.terminal(steps=((header, keys),), width=width, code=code)
                    self.assertNotIn(b'[y/N]', output)
                    if keys == b'\x1b[B\r':
                        if kind == 'files':
                            self.assertTrue(fixture.path.is_symlink())
                        else:
                            head = fixture.git(self.repo, 'rev-parse', 'HEAD')
                            self.assertNotEqual(head, self.before)
                            self.assertEqual(fixture.git(self.bare, 'rev-parse', 'main'), head)
                    else:
                        self.unchanged(fixture, kind)
                    self.assertNotIn(b'Traceback', picker.ANSI.sub(b'', output))



if __name__ == '__main__':
    unittest.main()
