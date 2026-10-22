#!/usr/bin/env python3
"""Television rendering, journaled connectors and native PTY acceptance."""
import json
import os
from pathlib import Path
import select
import shutil
import struct
import subprocess
import sys
import time
import tomllib
import unittest
from unittest.mock import patch

if os.name != "nt":
    import fcntl
    import pty
    import termios

import test_themes as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
from palette_native import Themes
from app_paths import television_config_directory, config_directory
import theme_cli
from transactions import Store

ROLES = dict(background='background', border_fg='muted', text_fg='foreground',
             dimmed_text_fg='muted', input_text_fg='accent', result_count_fg='accent',
             result_name_fg='blue', result_line_number_fg='yellow', result_value_fg='bright_blue',
             selection_fg='selection_foreground', selection_bg='selection_background', match_fg='accent',
             preview_title_fg='orange', channel_mode_fg='background', channel_mode_bg='magenta',
             remote_control_mode_fg='background', remote_control_mode_bg='green',
             action_picker_mode_fg='background', action_picker_mode_bg='blue')


class TelevisionTheme(unittest.TestCase):
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

    def test_all_palettes_and_native_renderer(self):
        self.wal_export()
        (self.home / 'cache/wal/colors.json').write_text(json.dumps({
            'special': {'background':'#102030', 'foreground':'#eeeeee', 'cursor':'#abcdef'},
            'colors': {f'color{i}': f'#{i+32:02x}{i+48:02x}{i+64:02x}' for i in range(16)}}))
        for identity in self.dots('theme', 'list').stdout.splitlines():
            with self.subTest(theme=identity):
                out = self.render(identity)
                raw = (out / 'television.toml').read_text()
                self.assertNotIn('{{', raw)
                doc = tomllib.loads(raw)
                colors = json.loads((out / 'colors.json').read_text())['colors']
                self.assertEqual(set(doc), set(ROLES))
                for field, role in ROLES.items():
                    self.assertEqual(doc[field], colors[role])
                    self.assertRegex(doc[field], r'^#[0-9a-fA-F]{6}$')
                native = self.root / ('native-' + identity); native.mkdir()
                with patch.dict(os.environ, self.env, clear=True):
                    Themes().render(identity, native)
                self.assertEqual(tomllib.loads((native / 'television.toml').read_text()), doc)

    def test_paths_and_validation(self):
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(television_config_directory(), self.home / 'config/television')
            with patch.dict(os.environ, XDG_CONFIG_HOME='', LOCALAPPDATA=str(self.home / 'Local')):
                self.assertEqual(config_directory('television'), self.home / 'Local/television/config')
                self.assertEqual(television_config_directory(), self.home / '.config/television')
            custom = self.home / '-tv ü space'
            with patch.dict(os.environ, TELEVISION_CONFIG=str(custom)):
                self.assertEqual(television_config_directory(), custom)
                with patch.dict(os.environ, DOTS_APP_TELEVISION_CONFIG=str(self.home / 'explicit')):
                    self.assertEqual(television_config_directory(), self.home / 'explicit')
            for value in ('relative', str(self.home)+'/../bad', str(self.home)+'/./bad', str(self.home)+'\n', str(self.home)+'\x7f'):
                with patch.dict(os.environ, TELEVISION_CONFIG=value), self.assertRaises(ValueError):
                    television_config_directory()
        self.dots('theme', 'set', 'nord', '--dry-run', code=1,
                  env=dict(self.env, TELEVISION_CONFIG='relative'))
        self.assertFalse(self.state.exists())

    def test_missing_parent_preview_refresh_and_rollback(self):
        base = self.home / '-television ü'; base.mkdir()
        self.env['TELEVISION_CONFIG'] = str(base)
        target = base / 'themes/dots.toml'
        for color in ('always', 'never'):
            preview = self.dots('theme', 'set', 'nord', '--dry-run', env=dict(self.env, DOTS_COLOR=color))
            if color == 'never':
                self.assertIn(str(target), preview.stdout)
                self.assertNotIn('\x1b', preview.stdout)
            else:
                self.assertIn('~/-television ü/themes/dots.toml', preview.stdout)
        self.assertFalse(target.parent.exists())
        self.assertFalse(self.state.exists())
        self.dots('theme', 'set', 'nord')
        first = self.generation()
        self.assertEqual(target.resolve(), first / 'television.toml')
        inode = target.lstat().st_ino
        self.dots('theme', 'refresh')
        self.assertEqual(self.generation(), first)
        self.assertEqual(target.lstat().st_ino, inode)
        self.engine('dt_restore "' + str(first) + '"')
        self.assertFalse(target.parent.exists())
        self.assertTrue(base.is_dir())

    def test_backups_conflicts_and_drift(self):
        base = self.home / 'config/television/themes'; base.mkdir(parents=True)
        target = base / 'dots.toml'
        for broken in (False, True):
            if broken: target.symlink_to(base / 'missing')
            else: target.write_text('personal')
            self.dots('theme', 'set', 'nord')
            self.engine('dt_restore "' + str(self.generation()) + '"')
            if broken: self.assertEqual(target.readlink(), base / 'missing')
            else: self.assertEqual(target.read_text(), 'personal')
            target.unlink()
        target.mkdir()
        self.dots('theme', 'set', 'nord', code=1)
        target.rmdir()
        base.rmdir(); base.write_text('conflict')
        self.dots('theme', 'set', 'nord', code=1)
        base.unlink(); base.mkdir()
        self.dots('theme', 'set', 'nord')
        target.unlink(); target.write_text('user edit')
        self.engine('dt_restore "' + str(self.generation()) + '"', code=1)
        self.assertEqual(target.read_text(), 'user edit')

    def test_interruption_recovers_created_parent(self):
        base = self.home / 'config/television'; base.mkdir(parents=True)
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then kill -KILL "$BASHPID"; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set nord''', code=137)
        self.dots('theme', 'set', 'catppuccin-latte')
        self.assertEqual((base / 'themes/dots.toml').resolve(), self.generation() / 'television.toml')
        self.assertIn('rolled-back\n', [p.read_text() for p in self.state.glob('generations/*/status')])
        (base / 'themes/user.toml').write_text('preserve')
        self.engine('dt_restore "' + str(self.generation()) + '"', code=1)
        self.assertEqual((base / 'themes/user.toml').read_text(), 'preserve')

    def test_parent_replacement_is_not_touched(self):
        base = self.home / 'config/television'; base.mkdir(parents=True)
        self.dots('theme', 'set', 'nord')
        (base / 'themes').rename(base / 'retained')
        (base / 'themes').mkdir()
        target = base / 'themes/dots.toml'
        target.symlink_to(self.home / 'state/dots/current/theme/television.toml')
        self.engine('dt_restore "' + str(self.generation()) + '"', code=1)
        self.assertTrue(target.is_symlink())

    def test_ambiguous_parent_creation_requires_review(self):
        base = self.home / 'config/television'; base.mkdir(parents=True)
        self.engine('''stat() { kill -KILL "$BASHPID"; }
dt_set nord''', code=137)
        self.assertTrue((base / 'themes').is_dir())
        result = self.dots('theme', 'set', 'nord', code=1)
        self.assertIn('requires manual recovery', result.stderr)
        self.assertTrue((base / 'themes').is_dir())

    def test_render_without_optional_consumers(self):
        binaries = self.root / 'minimal-bin'; binaries.mkdir()
        for command in ('bash', 'python3', 'cp', 'mkdir', 'cat', 'uname', 'readlink', 'sha256sum', 'sort'):
            (binaries / command).symlink_to(shutil.which(command))
        self.env['PATH'] = str(binaries)
        self.assertIsNone(shutil.which('tv', path=self.env['PATH']))
        out = self.render('nord')
        with patch.dict(os.environ, self.env, clear=True):
            native = self.root / 'native'; native.mkdir(); Themes().render('nord', native)
        self.assertEqual((out / 'television.toml').read_bytes(), (native / 'television.toml').read_bytes())

    def test_optional_directory_and_template_precedence(self):
        self.dots('theme', 'set', 'nord')
        self.assertFalse((self.home / 'config/television').exists())
        personal = self.home / 'config/dots/themed/television.toml.tpl'; personal.parent.mkdir(parents=True)
        personal.write_text("text_fg = '{{ accent }}'\n")
        self.dots('theme', 'refresh'); first = self.generation()
        self.assertEqual(set(tomllib.loads((first / 'television.toml').read_text())), {'text_fg'})
        personal.write_text("border_fg = '{{ accent }}'\n")
        self.dots('theme', 'refresh'); self.assertNotEqual(first, self.generation())
        bundled = self.repo / 'themes/nord/television.toml'; bundled.write_text("text_fg = '#112233'\n")
        self.dots('theme', 'refresh')
        self.assertEqual((self.generation() / 'television.toml').read_bytes(), bundled.read_bytes())
        with patch.dict(os.environ, self.env, clear=True):
            themes = Themes(); before = themes.fingerprint('nord')
            out = self.root / 'native'; out.mkdir(); themes.render('nord', out)
            self.assertEqual((out / 'television.toml').read_bytes(), bundled.read_bytes())
            bundled.write_text("text_fg = '#445566'\n")
            self.assertNotEqual(themes.fingerprint('nord'), before)
        bundled.unlink(); personal.write_text("text_fg = '{{ nonexistent }}'\n")
        previous = self.generation(); self.dots('theme', 'refresh', code=1)
        self.assertEqual(self.generation(), previous)

    def test_native_transaction_failure_and_undo(self):
        base = self.home / 'config/television'; base.mkdir(parents=True)
        target = base / 'themes/dots.toml'
        with patch.dict(os.environ, self.env, clear=True), patch.object(theme_cli, 'reload_apps'):
            themes = Themes()
            theme_cli.publication(themes, 'nord', dry=True)
            self.assertFalse(target.parent.exists())
            save = Store.save
            injected = []
            def fail(store, doc):
                save(store, doc)
                if target.is_symlink() and doc['status'] == 'applying' and not injected:
                    injected.append(True)
                    raise OSError('fixture interruption')
            with patch.object(Store, 'save', fail), self.assertRaisesRegex(OSError, 'fixture interruption'):
                theme_cli.publication(themes, 'nord')
            self.assertFalse(target.parent.exists())
            first = theme_cli.publication(themes, 'nord')
            self.assertEqual(theme_cli.publication(themes, 'nord'), first)
            store = Store(themes.state)
            record = next(r for r in store.records() if r['status'] == 'complete')
            operations, guards, _ = store.inverse(record['id'])
            store.apply('test-undo', operations, guards, retain=True)
            self.assertFalse(target.is_symlink())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('tv'), 'Television unavailable')
    def test_native_tv_dark_light_pty(self):
        base = self.home / 'television'; (base / 'themes').mkdir(parents=True)
        (base / 'cable').mkdir()
        (base / 'config.toml').write_text('[ui]\ntheme = "dots"\n')
        for palette in ('catppuccin-mocha', 'catppuccin-latte'):
            out = self.render(palette)
            shutil.copyfile(out / 'television.toml', base / 'themes/dots.toml')
            colors = tomllib.loads((out / 'television.toml').read_text())
            for width in (40, 80, 120):
                with self.subTest(palette=palette, width=width):
                    master, slave = pty.openpty()
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, width, 0, 0))
                    env = dict(self.env, TELEVISION_CONFIG=str(base), TELEVISION_DATA=str(self.home / 'tv-data'), COLORTERM='truecolor')
                    proc = subprocess.Popen([shutil.which('tv'), '--source-command', "printf 'alpha\\nbeta\\n'", '--no-remote', '--no-preview', '--cable-dir', str(base / 'cable')],
                                            stdin=slave, stdout=slave, stderr=slave, cwd=self.home, env=env)
                    os.close(slave)
                    data = bytearray()
                    try:
                        deadline = time.monotonic() + 1.5
                        while time.monotonic() < deadline:
                            if select.select([master], [], [], .1)[0]:
                                try: data.extend(os.read(master, 65536))
                                except OSError: break
                        os.write(master, b'\x1b')
                        proc.wait(timeout=5)
                    finally:
                        if proc.poll() is None: proc.kill(); proc.wait()
                        os.close(master)
                    text = data.decode(errors='replace')
                    self.assertEqual(proc.returncode, 0, text)
                    self.assertIn('alpha', text)
                    self.assertNotIn('Error', text)
                    for key in ('background', 'selection_bg', 'selection_fg'):
                        rgb = ';'.join(str(int(colors[key][i:i+2], 16)) for i in (1, 3, 5))
                        self.assertIn(';2;' + rgb, text, key)


if __name__ == '__main__':
    unittest.main()
