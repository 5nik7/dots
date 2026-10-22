#!/usr/bin/env python3
"""Default eza generation and publication; every mutable root is disposable."""
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

import test_themes as fixture

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
from palette_native import Themes
from app_paths import eza_config_directory, config_directory
import theme_cli
from transactions import Store


class EzaTheme(unittest.TestCase):
    setUp = fixture.Themes.setUp
    run_command = fixture.Themes.run_command
    dots = fixture.Themes.dots
    engine = fixture.Themes.engine
    shell = fixture.Themes.shell
    generation = fixture.Themes.generation
    wal_export = fixture.Themes.wal_export

    def render(self, identity):
        out = self.root / ('render-' + identity)
        out.mkdir(exist_ok=True)
        self.env.update(RENDER_THEME=identity, RENDER_OUTPUT=str(out))
        self.engine('dt_load "$RENDER_THEME" && dt_render "$RENDER_OUTPUT"')
        return out

    @unittest.skipUnless(yaml, 'PyYAML required for schema comparisons')
    def test_all_palettes_and_native_renderer(self):
        self.wal_export()
        (self.home / 'cache/wal/colors.json').write_text(json.dumps({
            'special': {'background':'#102030', 'foreground':'#eeeeee', 'cursor':'#abcdef'},
            'colors': {f'color{i}':f'#{i+32:02x}{i+48:02x}{i+64:02x}' for i in range(16)}}))
        for identity in self.dots('theme', 'list').stdout.splitlines():
            with self.subTest(theme=identity):
                out = self.render(identity)
                raw = (out / 'eza.yml').read_text()
                self.assertNotIn('{{', raw)
                doc = yaml.safe_load(raw)
                self.assertTrue(doc['colourful'])
                self.assertEqual(set(doc['security_context']), {'selinux'})
                self.assertEqual(set(doc['security_context']['selinux']), {'colon','user','role','typ','range'})
                self.assertTrue(doc['perms']['user_read']['is_bold'])
                colors = json.loads((out / 'colors.json').read_text())['colors']
                self.assertEqual(doc['filekinds']['directory']['foreground'], colors['accent'])
                self.assertEqual(doc['filekinds']['normal']['foreground'], colors['foreground'])
                for key, role in {'new':'added','modified':'modified','typechange':'modified','deleted':'deleted','renamed':'renamed','ignored':'ignored','conflicted':'conflict'}.items():
                    value = colors['git'][role]
                    self.assertEqual(doc['git'][key]['foreground'], 'default' if value == 'reset' else value)
                native = self.root / ('native-' + identity); native.mkdir()
                with patch.dict(os.environ, self.env, clear=True):
                    Themes().render(identity, native)
                self.assertEqual(yaml.safe_load((native / 'eza.yml').read_text()), doc)
                if shutil.which('eza'):
                    # eza consumes theme.yml, not the artifact filename.
                    (out / 'theme.yml').symlink_to('eza.yml')
                    result = self.run_command(['eza', '--color=always', '--icons=never', str(self.repo)],
                                              env=dict(self.env, EZA_CONFIG_DIR=str(out)))
                    self.assertEqual(result.stderr, '')
                    self.assertIn('38;2;', result.stdout)

    def test_paths_precedence_and_validation(self):
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(eza_config_directory(), self.home / 'config/eza')
            with patch.dict(os.environ, APPDATA=str(self.home / 'Roaming')):
                self.assertEqual(config_directory('eza'), self.home / 'Roaming/eza')
            native = self.home / '-native ü'; dots = self.home / 'dots space'
            with patch.dict(os.environ, EZA_CONFIG_DIR=str(native)):
                self.assertEqual(eza_config_directory(), native)
                with patch.dict(os.environ, DOTS_APP_EZA_CONFIG=str(dots)):
                    self.assertEqual(eza_config_directory(), dots)
            for value in ('relative', str(self.home)+'/../escape', str(self.home)+'/./dots', str(self.home)+'\nsecret', str(self.home)+'\x7f'):
                with patch.dict(os.environ, EZA_CONFIG_DIR=value), self.assertRaises(ValueError):
                    eza_config_directory()
        for variable in ('EZA_CONFIG_DIR', 'DOTS_APP_EZA_CONFIG'):
            result = self.dots('theme', 'set', 'nord', code=1, env=dict(self.env, **{variable:'relative'}))
            self.assertIn('eza configuration', result.stderr)
        self.assertFalse((self.home / 'state/dots/current/theme').exists())

    def test_bash_connector_backup_idempotence_and_rollback(self):
        directory = self.home / '-eza ü'; directory.mkdir()
        self.env['EZA_CONFIG_DIR'] = str(directory)
        target = directory / 'theme.yml'; target.write_text('personal theme\n')
        self.dots('theme', 'set', 'nord')
        generation = self.generation()
        self.assertEqual(target.resolve(), generation / 'eza.yml')
        before = target.lstat().st_mtime_ns
        self.dots('theme', 'refresh')
        self.assertEqual(self.generation(), generation)
        self.assertEqual(target.lstat().st_mtime_ns, before)
        self.engine('dt_restore "' + str(generation) + '"')
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_text(), 'personal theme\n')
        target.unlink(); target.symlink_to(directory / 'missing')
        self.dots('theme', 'set', 'nord')
        self.engine('dt_restore "' + str(self.generation()) + '"')
        self.assertEqual(target.readlink(), directory / 'missing')

    def test_absent_directory_overrides_and_conflicts(self):
        default = self.home / 'config/eza'; default.mkdir(parents=True)
        custom = self.home / 'custom eza'
        self.env.update(EZA_CONFIG_DIR=str(custom), DOTS_APP_EZA_CONFIG=str(custom))
        self.dots('theme', 'set', 'nord')
        self.assertFalse(custom.exists())
        self.assertFalse((default / 'theme.yml').exists())
        custom.mkdir(); (custom / 'theme.yml').mkdir()
        self.dots('theme', 'set', 'catppuccin-latte', code=1)
        self.assertEqual(self.dots('theme', 'current').stdout, 'nord\n')
        (custom / 'theme.yml').rmdir()
        staging = custom / 'theme.yml.dots-theme-new'; staging.write_text('unowned')
        self.dots('theme', 'set', 'catppuccin-latte', code=1)
        self.assertEqual(staging.read_text(), 'unowned')

    def test_interruption_recovery_and_drift(self):
        directory = self.home / 'config/eza'; directory.mkdir(parents=True)
        target = directory / 'theme.yml'; target.write_text('original')
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then kill -KILL "$BASHPID"; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin mocha''', code=137)
        self.dots('theme', 'set', 'nord')
        self.assertTrue(target.is_symlink())
        self.assertIn('rolled-back\n', [p.read_text() for p in self.state.glob('generations/*/status')])
        target.unlink(); target.write_text('changed after publication')
        self.engine('dt_restore "' + str(self.generation()) + '"', code=1)
        self.assertEqual(target.read_text(), 'changed after publication')

    def test_personal_and_bundled_overrides_and_fingerprints(self):
        personal = self.home / 'config/dots/themed/eza.yml.tpl'; personal.parent.mkdir(parents=True)
        personal.write_text('header: {foreground: "{{ accent }}"}\n')
        self.dots('theme', 'set', 'nord')
        first = self.generation()
        self.assertTrue((first / 'eza.yml').read_text().startswith('header:'))
        personal.write_text('date: {foreground: "{{ accent }}"}\n')
        self.dots('theme', 'refresh')
        self.assertNotEqual(first, self.generation())
        bundled = self.repo / 'themes/nord/eza.yml'; bundled.write_text('colourful: false\n')
        self.dots('theme', 'refresh')
        self.assertEqual((self.generation() / 'eza.yml').read_bytes(), bundled.read_bytes())
        with patch.dict(os.environ, self.env, clear=True):
            themes = Themes(); before = themes.fingerprint('nord')
            native = self.root / 'native'; native.mkdir(); themes.render('nord', native)
            self.assertEqual((native / 'eza.yml').read_bytes(), bundled.read_bytes())
            bundled.write_text('colourful: true\n')
            self.assertNotEqual(themes.fingerprint('nord'), before)
        self.dots('theme', 'refresh')
        self.assertEqual((self.generation() / 'eza.yml').read_bytes(), bundled.read_bytes())

    def test_resolved_git_roles_and_reset(self):
        overlay = self.home / 'config/dots/file-colors.toml'; overlay.parent.mkdir(parents=True)
        overlay.write_text('[git.modified]\nfg = "#123456"\n[git.added]\nfg = "reset"\n')
        out = self.render('nord')
        raw = (out / 'eza.yml').read_text()
        self.assertIn('new: {foreground: "default"}', raw)
        self.assertIn('modified: {foreground: "#123456"}', raw)
        with patch.dict(os.environ, self.env, clear=True):
            native = self.root / 'native'; native.mkdir(); Themes().render('nord', native)
        self.assertEqual((native / 'eza.yml').read_text(), raw)
        if shutil.which('eza'):
            (out / 'theme.yml').symlink_to('eza.yml')
            self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                            GIT_TERMINAL_PROMPT='0', EZA_CONFIG_DIR=str(out))
            repo = self.home / 'git fixture'
            self.run_command(['git', 'init', str(repo)])
            sample = repo / 'sample'; sample.write_text('before\n')
            self.run_command(['git', '-C', str(repo), 'add', 'sample'])
            self.run_command(['git', '-C', str(repo), '-c', 'user.name=Fixture',
                              '-c', 'user.email=fixture@example.invalid', '-c', 'core.hooksPath=' + os.devnull,
                              '-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture'])
            sample.write_text('after\n')
            (repo / 'new').write_text('new\n')
            result = self.run_command(['eza', '--color=always', '--icons=never', '--long', '--git', str(repo)])
            self.assertEqual(result.stderr, '')
            self.assertIn('38;2;18;52;86', result.stdout)

    def test_render_without_optional_consumers(self):
        tools = self.root / 'minimal-bin'; tools.mkdir()
        for command in ('bash', 'python3', 'cp', 'mkdir', 'cat', 'uname', 'readlink', 'sha256sum', 'sort'):
            (tools / command).symlink_to(shutil.which(command))
        self.env['PATH'] = str(tools)
        self.assertIsNone(shutil.which('eza', path=self.env['PATH']))
        self.assertIsNone(shutil.which('vivid', path=self.env['PATH']))
        out = self.render('nord')
        self.assertNotIn('{{', (out / 'eza.yml').read_text())
        with patch.dict(os.environ, self.env, clear=True):
            native = self.root / 'native'; native.mkdir(); Themes().render('nord', native)
        self.assertEqual((native / 'eza.yml').read_bytes(), (out / 'eza.yml').read_bytes())

    def test_native_pywal_export_invalidates_fingerprint(self):
        export = self.home / 'cache/wal/colors.json'; export.parent.mkdir(parents=True)
        doc = {'special': {'background':'#102030', 'foreground':'#eeeeee', 'cursor':'#abcdef'},
               'colors': {f'color{i}':f'#{i+32:02x}{i+48:02x}{i+64:02x}' for i in range(16)}}
        export.write_text(json.dumps(doc))
        with patch.dict(os.environ, self.env, clear=True):
            themes = Themes(); before = themes.fingerprint('pywal16-current')
            doc['colors']['color4'] = '#123456'; export.write_text(json.dumps(doc))
            self.assertNotEqual(themes.fingerprint('pywal16-current'), before)
            self.assertEqual(themes.load('pywal16-current')['colors']['blue'], '#123456')

    def test_native_transaction_undo_and_failure(self):
        directory = self.home / 'eza'; directory.mkdir()
        target = directory / 'theme.yml'; target.write_text('original')
        self.env['EZA_CONFIG_DIR'] = str(directory)
        with patch.dict(os.environ, self.env, clear=True), patch.object(theme_cli, 'reload_apps'):
            themes = Themes()
            theme_cli.publication(themes, 'nord', dry=True)
            self.assertEqual(target.read_text(), 'original')
            save = Store.save
            injected = []
            def fail(store, doc):
                save(store, doc)
                if target.is_symlink() and doc['status'] == 'applying' and not injected:
                    injected.append(True)
                    raise OSError('fixture interruption after eza replacement')
            with patch.object(Store, 'save', fail), self.assertRaisesRegex(OSError, 'fixture interruption'):
                theme_cli.publication(themes, 'nord')
            self.assertEqual(target.read_text(), 'original')
            self.assertFalse(target.is_symlink())
            first = theme_cli.publication(themes, 'nord')
            self.assertTrue(target.is_symlink())
            self.assertEqual(theme_cli.publication(themes, 'nord'), first)
            store = Store(themes.state)
            record = next(r for r in store.records() if r['status'] == 'complete')
            operations, guards, _ = store.inverse(record['id'])
            store.apply('test-undo', operations, guards, retain=True)
            self.assertEqual(target.read_text(), 'original')

    @unittest.skipUnless(shutil.which('eza'), 'eza unavailable')
    def test_native_eza_dark_light_and_environment_precedence(self):
        directory = self.home / 'config/eza'; directory.mkdir(parents=True)
        listing = self.home / 'listing'; listing.mkdir(); (listing / 'folder').mkdir()
        (listing / 'plain').write_text('fixture')
        (listing / 'link').symlink_to('plain')
        for identity in ('catppuccin-mocha', 'catppuccin-latte'):
            self.dots('theme', 'set', identity)
            colors = json.loads((self.generation() / 'colors.json').read_text())['colors']
            result = self.run_command(['eza','--color=always','--icons=never','--long','--header',str(listing)])
            self.assertEqual(result.stderr, '')
            for role in ('accent', 'foreground', 'red'):
                value = colors[role]; rgb = ';'.join(str(int(value[i:i+2], 16)) for i in (1,3,5))
                self.assertIn('38;2;' + rgb, result.stdout)
            self.assertIn('folder', result.stdout)
            result = self.run_command(['eza','--color=always','--icons=never',str(listing)],
                env=dict(self.env, LS_COLORS='di=38;2;1;2;3', EZA_COLORS='di=38;2;4;5;6'))
            self.assertIn('\x1b[38;2;4;5;6mfolder', result.stdout)


if __name__ == '__main__':
    unittest.main()
