#!/usr/bin/env python3
"""Status-heading icons, Config and both renderers in exclusively owned roots."""
import io
import itertools
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_style_config as fixtures
from files.catalog import Presentation
from git_output import GitView, STATUS_ICONS
from style_config import Styles, current

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


class StatusIcons(unittest.TestCase):
    setUp = fixtures.StyleConfig.setUp
    run_config = fixtures.StyleConfig.run_config

    def test_config_roundtrip_reset_and_only_consumed_browser_completion_keys(self):
        from config_menu import Inventory
        from config_icon_samples import PublishedSamples
        from config_view import icon_sample
        from style_catalog import consumers, fields
        for role, glyph in STATUS_ICONS.items():
            key = 'git.status.' + role
            self.assertEqual(self.run_config('get', 'icons.' + key).stdout, glyph + '\n')
            self.assertEqual(consumers('icons', key), ['cli'])
            self.assertEqual(fields('icons.' + key, 'cli'), ())
        result = json.loads(self.run_config('set', 'icons.git.status.modified', 'EDIT', '--json').stdout)
        self.assertEqual(result['refresh']['consumers'], [dict(app='cli', status='next invocation')])
        self.assertEqual(self.run_config('get', 'icons.git.status.modified', native=True).stdout, 'EDIT\n')
        self.assertEqual(self.run_config('get', 'icons.git.modified').stdout, '!\n')
        self.run_config('set', 'icons.git.status.ignored', '')
        self.assertEqual(self.run_config('get', 'icons.git.status.ignored').stdout, '\n')
        for value in ('bad\ntext', '\x1b[31m', 'x' * 65):
            self.run_config('set', 'icons.git.status.modified', value, code=1)
        self.run_config('unset', 'icons.git.status.modified')
        self.assertEqual(self.run_config('get', 'icons.git.status.modified').stdout, '\n')
        explained = json.loads(self.run_config('explain', 'icons.git.status.modified', '--json').stdout)
        self.assertEqual([c['app'] for c in explained['consumers']], ['cli'])
        self.assertEqual(explained['consumers'][0]['refresh'], 'next invocation')
        with patch.dict(os.environ, self.env, clear=True):
            inventory = Inventory(self.root, self.platform)
            self.assertTrue(any(row.key == 'icons.git.status.modified' for row in inventory.rows))
            styles = Styles(self.root)
            sample = icon_sample(styles, 'git.status.modified', '', published=PublishedSamples(styles))
            self.assertIn('Git modified fallback', sample.annotation)
            self.assertEqual(sample.code, '0;' + Presentation().resources.git_style('modified'))
        keys = subprocess.check_output([sys.executable, '-B', str(self.root/'lib/dots/profile_config.py'), '__keys'], env=self.env, text=True)
        self.assertIn('icons.git.status.modified\n', keys)
        self.assertIn('icons.apps.cli.git.status.modified\n', keys)
        for app in ('tmux', 'gitmux', 'starship', 'yazi'):
            self.assertNotIn('icons.apps.' + app + '.git.status.modified\n', keys)
        self.assertNotIn('colors.apps.cli.icons.git.status.modified.fg\n', keys)
        self.assertFalse((Path(self.env['XDG_STATE_HOME'])/'dots/current/theme').exists())

    def test_inherited_custom_empty_icons_and_all_statuses_through_both_renderers(self):
        from profile_config import context
        parent = self.root/'profiles/linux'
        child = parent/'distros/icons'
        child.mkdir(parents=True)
        (child/'profile.json').write_text(json.dumps(dict(schema=1, id='linux/icons', extends=['linux'])))
        (parent/'icons.toml').write_text('[git.status]\nmodified="parent"\ncopied="COPY"\n')
        (child/'icons.toml').write_text('[git.status]\nignored=""\n[apps.cli.git.status]\nmodified="EDIT"\n[navigation]\nedit="EDIT"\n')
        (child/'colors.toml').write_text('[icons.navigation.edit]\nfg="#123456"\n')
        # Mixed states must retain their complete label, with one dominant icon.
        cases = [(' M', 'EDIT', 'unstaged modified'), ('M ', 'EDIT', 'staged modified'),
                 ('MM', 'EDIT', 'staged modified + unstaged modified'),
                 ('A ', '󰐕', 'staged added'), (' D', '󰆴', 'unstaged deleted'),
                 ('RM', '', 'staged renamed + unstaged modified'), ('C ', 'COPY', 'staged copied'),
                 (' T', '󰑓', 'unstaged type changed'), ('??', '', 'untracked'),
                 ('!!', '', 'ignored'), ('  ', '', 'selected'),
                 ('AM', '󰐕', 'staged added + unstaged modified'),
                 ('RD', '󰆴', 'staged renamed + unstaged deleted'),
                 ('TM', '󰑓', 'staged type changed + unstaged modified')]
        conflicts = {'DD':'both deleted', 'AU':'added by us', 'UD':'deleted by them',
                     'UA':'added by them', 'DU':'deleted by us', 'AA':'both added', 'UU':'both modified'}
        cases += [(xy, '', 'conflict: ' + label) for xy, label in conflicts.items()]
        files = [dict(xy=xy, path=f'file{index}.txt') for index, (xy, _, _) in enumerate(cases)]
        for file in files: (self.home/file['path']).write_text('fixture')
        shell = '\n'.join(['DOTS_LIB_DIR="$DOTS/lib/dots"', 'source "$DOTS_LIB_DIR/git/ui.bash"',
                          'source "$DOTS_LIB_DIR/git/views.bash"', 'GIT_VIEW=default FULL_PATHS=0',
                          'codes=(' + ' '.join(shlex.quote(f['xy']) for f in files) + ')',
                          'paths=(' + ' '.join(shlex.quote(f['path']) for f in files) + ')',
                          'oldpaths=(' + ' '.join("''" for _ in files) + ')', 'view_status_files "$HOME"'])
        for icons, color, mode in itertools.product(('always', 'never'), ('always', 'never'), ('default', 'verbose')):
            env = dict(self.env, DOTS_PROFILE='linux/icons', DOTS_ICONS=icons, DOTS_COLOR=color,
                       DOTS_MENU_CAPTURE='1', TERM='xterm-256color', COLUMNS='120')
            current.cache_clear()
            with patch.dict(os.environ, env, clear=True):
                # Project the explicitly inspected child into the same
                # literal rows used by compiled startup, without pretending
                # that this host runs that Linux distro profile.
                styles = Styles(self.root, context(self.root, 'linux/icons'))
                rows = ['\t'.join(row) for row in styles.rows()]
                projected = '_DOTS_PROFILE_SETTINGS_CHECKOUT="$DOTS"\n_DOTS_PROFILE_SETTING_ROWS=(' + ' '.join(map(shlex.quote, rows)) + ')\n'
                output = io.StringIO()
                view = GitView(Presentation(output, terminal=True), mode)
                with patch.object(view, 'header'), patch.object(view, 'metadata'):
                    view.status(dict(path=str(self.home), files=files))
                python_output = output.getvalue()
            result = subprocess.run([shutil.which('bash'), '--noprofile', '--norc', '-c', projected + shell.replace('GIT_VIEW=default', 'GIT_VIEW=' + mode)], env=env,
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = ['    ' + (glyph + ' ' if glyph and icons == 'always' else '') + ('[' + xy + '] ' if mode == 'verbose' else '') + label + ' (1)'
                        for xy, glyph, label in cases]
            for frontend, text in (('Python', python_output), ('Bash', result.stdout)):
                lines = text.splitlines()
                headings = [ANSI.sub('', line) for line in lines if ANSI.sub('', line).startswith('    ')
                            and not ANSI.sub('', line).startswith('     ')]
                self.assertEqual(headings, expected, frontend)
                self.assertEqual('\x1b[' in text, color == 'always')
                for file in files:
                    line = next(line for line in ANSI.sub('', text).splitlines() if line.endswith(file['path']))
                    self.assertTrue(line.startswith('      ') and not line.startswith('       '), line)
                if color == 'always':
                    label = ('EDIT ' if icons == 'always' else '') + ('[ M] ' if mode == 'verbose' else '') + 'unstaged modified (1)'
                    self.assertRegex(text, r'\x1b\[[0-9;]+m' + re.escape(label) + r'\x1b\[0m')

    def test_batch_preview_and_save_apply_without_publishing(self):
        import config_refresh
        from config_cli import StylePlan
        from profile_config import context
        with patch.dict(os.environ, self.env, clear=True):
            before = config_refresh.effective(self.root)
            (self.path.parent/'icons.toml').write_text('[git.status]\nmodified="EDIT"\n[progress.bar]\nfilled="="\n')
            with patch.object(config_refresh, 'refresh', side_effect=AssertionError('theme publication')):
                self.assertEqual(config_refresh.after_save(self.root, before)['consumers'],
                                 [dict(app='cli', status='next invocation')])
            plan = StylePlan(self.root, context(self.root), 'icons', False)
            plan.edit('git.status.copied', 'COPY')
            self.assertIn('no theme publication', config_refresh.preview_save(self.root, plan)['reason'])

    def test_compiled_shell_icons_invalidate_and_warm_without_python(self):
        import test_profiles
        fixture = test_profiles.Profiles()
        fixture.setUp(); self.addCleanup(fixture.doCleanups); fixture.public()
        shutil.copytree(fixtures.ROOT/'default', fixture.root/'default')
        icons = fixture.root/'default/icons.toml'
        original = icons.read_text()
        for shell in ('bash', 'zsh'):
            if not shutil.which(shell): continue
            code = 'source "$DOTS/lib/dots/shell/init.' + shell + '"; printf "%s" "${_DOTS_STYLE_ICONS[git.status.modified]}"'
            cold = fixture.run_shell(shell, code)
            self.assertEqual(cold.returncode, 0, cold.stderr)
            self.assertEqual(cold.stdout, '')
            icons.write_text(original.replace('modified = ""', 'modified = "EDIT"'))
            changed = fixture.run_shell(shell, code)
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertEqual(changed.stdout, 'EDIT')
            shims = fixture.home/('status-shims-' + shell)
            shims.mkdir()
            shim = shims/'python3'
            shim.write_text('#!' + shutil.which('sh') + '\nprintf UNEXPECTED_PYTHON >&2\nexit 99\n')
            shim.chmod(0o700)
            warm = fixture.run_shell(shell, code, PATH=str(shims) + os.pathsep + fixture.env['PATH'])
            self.assertEqual(warm.returncode, 0, warm.stderr)
            self.assertEqual(warm.stdout, 'EDIT')
            self.assertNotIn('UNEXPECTED_PYTHON', warm.stderr)
            icons.write_text(original)


if __name__ == '__main__': unittest.main()
