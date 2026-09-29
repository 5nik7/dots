#!/usr/bin/env python3
"""Theme plugins in disposable roots; never execute live hooks or desktop apps."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

import test_themes as theme_tests
from test_themes import REPO, BASH


class Plugins(unittest.TestCase):
    run_command = theme_tests.Themes.run_command
    dots = theme_tests.Themes.dots
    generation = theme_tests.Themes.generation

    def setUp(self):
        theme_tests.Themes.setUp(self)
        # Exercise escaped roots as well as the already space-containing checkout.
        for kind in ('CONFIG', 'STATE', 'CACHE', 'DATA'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / (kind.lower() + ' space ü'))
        self.config = Path(self.env['XDG_CONFIG_HOME'])
        self.state = Path(self.env['XDG_STATE_HOME']) / 'dots/themes'
        self.plugin_state = self.state.parent / 'theme-plugins'
        self.hooks = self.config / 'dots/hooks/theme-set.d'
        self.log = self.home / 'hook-log'
        self.python = sys.executable
        (self.repo / '.dots').mkdir()
        (self.repo / '.dots/sources.json').write_text('{"schema":1,"sources":[]}')
        for path in REPO.glob('bin/dots-files*'):
            shutil.copy2(path, self.repo / 'bin' / path.name)

    def hook(self, file, body, enabled=False):
        self.hooks.mkdir(parents=True, exist_ok=True)
        path = self.hooks / file
        path.write_text(body)
        if enabled:
            self.plugins('enable', file.split('-', 1)[1][:-3])
        return path

    def plugins(self, *args, code=0, env=None):
        return self.dots('theme', 'plugins', *args, code=code, env=env)

    def publish(self):
        return self.dots('theme', 'set', 'nord')

    def stub(self, name):
        path = self.repo / 'bin' / name
        path.write_text('#!' + BASH + '\nexit 0\n')
        path.chmod(0o700)

    def apps(self):
        for name, command in [('gtk-3.0', 'gtk-launch'), ('qt6ct', 'qt6ct')]:
            (self.config / name).mkdir(parents=True, exist_ok=True)
            self.stub(command)
        self.gtk = self.config / 'gtk-3.0/gtk.css'
        self.qt = self.config / 'qt6ct/qt6ct.conf'
        self.gtk.write_text('/* user CSS */\nlabel { padding: 3px; }\n')
        self.qt.write_bytes(b'# retained\r\n[Appearance]\r\nstyle=Fusion\r\ncustom_palette=false\r\n[Fonts]\r\ngeneral=Custom\r\n')
        self.plugins('enable', 'gtk')
        self.plugins('enable', 'qt6ct')

    def snapshot(self):
        return {str(p.relative_to(self.home)): (p.lstat().st_mtime_ns, os.readlink(p) if p.is_symlink()
                else hashlib.sha256(p.read_bytes()).hexdigest()) for p in self.home.rglob('*')
                if p.is_symlink() or p.is_file()}

    def test_read_only_help_doctor_completion_and_defaults(self):
        self.hook('20-custom.sh', 'touch "$HOME/executed"\n')
        before = self.snapshot()
        rows = json.loads(self.plugins('list', '--json').stdout)['plugins']
        self.assertEqual({r['name'] for r in rows}, {'gtk', 'qt6ct', 'custom'})
        self.assertFalse(any(r['enabled'] for r in rows))
        self.plugins('doctor', '--json')
        self.plugins()
        self.dots('commands', '--check')
        for shell in ('bash', 'zsh', 'fish'):
            out = self.dots('__complete', shell, '4', '--', 'dots', 'theme', 'plugins', 'enable', '').stdout
            self.assertIn('custom', out)
            for action in ('list', 'enable', 'disable', 'run', 'doctor'):
                self.assertIn(action, self.dots('help', 'theme', 'plugins', action).stdout)
        self.dots('theme', 'set', 'nord', '--dry-run')
        self.assertEqual(before, self.snapshot())

    def test_selection_order_refresh_and_disabled_output(self):
        for filename in ('100-late.sh', '2-first.sh', '10-middle.sh'):
            self.hook(filename, 'printf "%s %s\\n" "$DOTS_THEME_PLUGIN" "$DOTS_THEME_REASON" >> "$HOME/hook-log"\n', True)
        self.assertFalse(self.log.exists())
        self.publish()
        self.assertEqual(self.log.read_text().splitlines(), ['first set', 'middle set', 'late set'])
        generation = self.generation()
        self.publish()
        self.assertEqual(len(self.log.read_text().splitlines()), 3)
        self.dots('theme', 'refresh')
        self.assertEqual(generation, self.generation())
        self.assertEqual(self.log.read_text().splitlines()[-3:], ['first refresh', 'middle refresh', 'late refresh'])
        self.plugins('disable', 'first')
        self.assertIn('enable first', self.plugins('run', 'first', code=1).stderr)
        self.plugins('run', 'middle')
        self.assertEqual(self.log.read_text().splitlines()[-1], 'middle manual')
        self.assertTrue((self.hooks / '2-first.sh').exists())

    def test_new_filename_does_not_inherit_enablement(self):
        path = self.hook('20-local.sh', 'exit 0', True)
        path.rename(self.hooks / '30-local.sh')
        self.plugins('run', code=1)
        self.plugins('disable', 'local', code=1)  # Two distinct identities share a name.
        (self.hooks / '30-local.sh').rename(path)
        self.plugins('disable', 'local')

    def test_duplicates_symlinks_and_malformed_selection(self):
        self.hook('25-gtk.sh', 'touch "$HOME/executed"')
        self.assertIn('ambiguous', self.plugins('list', '--json', code=1).stdout)
        self.plugins('enable', 'gtk', code=1)
        (self.hooks / '25-gtk.sh').unlink()
        (self.hooks / '25-linked.sh').symlink_to(self.repo / 'lib/dots/themes/plugins/10-gtk.sh')
        self.plugins('doctor', 'linked', code=1)
        self.plugins('enable', 'linked', code=1)
        path = self.config / 'dots/theme-plugins.json'
        path.write_text('{"schema":1,"enabled":[],"schema":1}')
        self.plugins('list', code=1)
        self.assertFalse((self.home / 'executed').exists())

    def test_mapping_bash_environment_and_clean_json(self):
        self.hook('20-colors.sh', '''
python3 - <<'PY'
import json,os
from pathlib import Path
keys=['primary_background','primary_foreground','cursor_color','selection_background','selection_foreground','normal_black','bright_white','rgb_primary_background','DOTS_THEME_ID','DOTS_THEME_MODE','DOTS_THEME_DIR','DOTS_THEME_PALETTE']
Path(os.environ['HOME'],'colors.json').write_text(json.dumps({k:os.environ[k] for k in keys}))
PY
printf 'hook stdout\\n'\nprintf 'hook stderr\\n' >&2
''', True)
        self.publish()
        env = dict(self.env, BASH_ENV=str(self.home / 'bad-env'), DOTS_COLOR='always')
        # Invoke Python directly so the CLI's own Bash launcher is not the probe.
        (self.home / 'bad-env').write_text('touch "$HOME/injected"')
        out = self.run_command([self.python, '-B', str(self.lib / 'plugins.py'), 'run', '--json'], env=env)
        self.assertEqual(json.loads(out.stdout)['plugins'][0]['status'], 'success')
        self.assertIn('hook stdout', out.stderr)
        self.assertFalse((self.home / 'injected').exists())
        values = json.loads((self.home / 'colors.json').read_text())
        palette = json.loads((self.generation() / 'palette.json').read_text())
        self.assertEqual(values['primary_background'], palette['colors']['background'][1:].lower())
        self.assertEqual(values['bright_white'], palette['colors']['color15'][1:].lower())
        self.assertEqual(values['rgb_primary_background'], '46, 52, 64')
        self.assertEqual(Path(values['DOTS_THEME_DIR']), self.generation())

    def test_corrupt_published_palette_is_reported_without_execution(self):
        self.publish()
        self.hook('20-local.sh', 'touch "$HOME/executed"', True)
        path = self.generation() / 'palette.json'
        data = json.loads(path.read_text())
        for colors in (None, [], {}, {'background': '$(touch nope)'}):
            path.write_text(json.dumps(dict(data, colors=colors)))
            result = self.plugins('run', code=1)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse((self.home / 'executed').exists())

    def test_manual_progress_uses_shared_terminal_policy(self):
        self.publish()
        self.hook('20-slow.sh', 'sleep 0.8', True)
        for mode in ('auto', 'never'):
            master, slave = pty.openpty()
            process = subprocess.Popen([BASH, str(self.repo / 'bin/dots'), 'theme', 'plugins', 'run'],
                                       env=dict(self.env, DOTS_PROGRESS=mode), cwd=self.home,
                                       stdin=subprocess.DEVNULL, stdout=slave, stderr=slave)
            os.close(slave)
            output = bytearray()
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        try:
                            block = os.read(master, 8192)
                        except OSError:
                            break
                        if not block:
                            break
                        output.extend(block)
                    elif process.poll() is not None:
                        break
                self.assertEqual(process.wait(timeout=2), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)
            self.assertEqual(b'Running theme plugin slow' in output, mode == 'auto')
            self.assertIn(b'success', output)

    def test_failure_isolation_auto_semantics_and_retry(self):
        failed = self.hook('10-fail.sh', 'echo failure >&2; exit 9', True)
        self.hook('20-skip.sh', 'exit 77', True)
        self.hook('30-later.sh', 'echo later >> "$HOME/hook-log"', True)
        result = self.publish()
        self.assertIn('Theme remains published', result.stderr)
        self.assertTrue(self.generation().is_dir())
        rows = json.loads(self.plugins('run', '--json', code=1).stdout)['plugins']
        self.assertEqual([r['status'] for r in rows], ['failure', 'skipped', 'success'])
        failed.write_text('exit 0')
        self.plugins('run', 'fail')
        self.assertEqual(len(self.log.read_text().splitlines()), 2)

    def test_recursion_and_read_only_calls_do_not_deadlock(self):
        self.hook('20-nested.sh', '''
dots theme current > "$HOME/current-in-hook" || exit 1
dots theme plugins list --json > "$HOME/plugins-in-hook" || exit 2
if dots theme plugins run; then exit 3; fi
if dots theme set nord; then exit 4; fi
if dots theme plugins disable nested; then exit 5; fi
echo ok >> "$HOME/hook-log"
''', True)
        self.publish()
        self.assertEqual(self.log.read_text(), 'ok\n')
        self.assertIn('nord', (self.home / 'current-in-hook').read_text())

    def test_failed_publication_and_downloaded_scripts(self):
        self.hook('20-custom.sh', 'touch "$HOME/executed"', True)
        downloaded = self.config / 'dots/themes/downloaded'
        downloaded.mkdir(parents=True)
        shutil.copy2(self.repo / 'themes/nord/colors.toml', downloaded / 'colors.toml')
        (downloaded / '10-evil.sh').write_text('touch "$HOME/download-executed"')
        (downloaded / 'theme-set.d').mkdir()
        (downloaded / 'theme-set.d/10-evil.sh').write_text('touch "$HOME/download-executed"')
        self.dots('theme', 'set', 'downloaded', '--dry-run')
        self.assertFalse((self.home / 'executed').exists())
        broken = self.config / 'dots/themed/broken.tpl'
        broken.parent.mkdir()
        broken.write_text('{{ missing_color }}')
        self.dots('theme', 'set', 'downloaded', code=1)
        self.assertFalse((self.home / 'executed').exists())
        broken.unlink()
        self.dots('theme', 'set', 'downloaded')
        self.assertTrue((self.home / 'executed').exists())
        self.assertFalse((self.home / 'download-executed').exists())

    def test_optional_dependencies_and_platform_skip(self):
        self.plugins('enable', 'gtk')
        self.plugins('enable', 'qt6ct')
        self.publish()
        rows = json.loads(self.plugins('run', '--json').stdout)['plugins']
        self.assertEqual([r['status'] for r in rows], ['skipped', 'skipped'])
        sys.path.insert(0, str(self.lib))
        spec = importlib.util.spec_from_file_location('tested_plugins', self.lib / 'plugins.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(module.sys, 'platform', 'darwin'):
            result = module.availability({'problems': [], 'origin': 'user'}, self.config)
        self.assertEqual(result[0], 'unavailable')

    def test_apps_preserve_settings_idempotence_disable_and_drift(self):
        self.apps()
        self.publish()
        self.assertIn('/* user CSS */\nlabel { padding: 3px; }\n', self.gtk.read_text())
        self.assertIn(b'style=Fusion\r\n', self.qt.read_bytes())
        self.assertIn(b'[Fonts]\r\ngeneral=Custom\r\n', self.qt.read_bytes())
        gtk_output = self.config / 'gtk-3.0/dots-theme.css'
        qt_output = self.config / 'qt6ct/colors/dots.conf'
        self.assertFalse(gtk_output.is_symlink())
        self.assertEqual(len(qt_output.read_text().split('active_colors=', 1)[1].splitlines()[0].split(',')), 22)
        before = self.snapshot()
        self.plugins('run')
        self.assertEqual(before, self.snapshot())
        # Independent user configuration remains editable between plugin runs.
        self.gtk.write_text(self.gtk.read_text() + 'button { margin: 2px; }\n')
        self.qt.write_bytes(self.qt.read_bytes().replace(b'general=Custom', b'general=Changed'))
        self.dots('theme', 'set', 'catppuccin-latte')
        self.assertIn('margin: 2px', self.gtk.read_text())
        self.assertIn('general=Changed', self.qt.read_text())
        original = gtk_output.read_bytes()
        self.plugins('disable', 'gtk')
        self.dots('theme', 'set', 'nord')
        self.assertEqual(original, gtk_output.read_bytes())
        qt_output.write_text('user edit')
        out = self.plugins('run', 'qt6ct', code=1)
        self.assertIn('drift', out.stderr)
        self.assertEqual(qt_output.read_text(), 'user edit')
        self.plugins('doctor', 'qt6ct', code=1)

    def test_app_collisions_preflight_and_registration_drift(self):
        self.apps()
        self.publish()
        self.gtk.write_text(self.gtk.read_text().replace('dots-theme.css', 'other.css'))
        before = self.snapshot()
        self.plugins('run', 'gtk', code=1)
        self.assertEqual(before, self.snapshot())
        self.qt.write_text(self.qt.read_text().replace('custom_palette=true', 'custom_palette=false'))
        self.plugins('run', 'qt6ct', code=1)
        (self.plugin_state / 'qt6ct.json').unlink()
        self.assertIn('collision', self.plugins('run', 'qt6ct', code=1).stderr)

    def test_app_registration_preserves_utf8_bom_and_charset(self):
        self.apps()
        self.gtk.write_bytes(b'\xef\xbb\xbf@charset "UTF-8";\n/* user CSS */\n')
        self.qt.write_bytes(b'\xef\xbb\xbf[Appearance]\nstyle=Fusion\ncustom_palette=false\n')
        self.publish()
        self.assertTrue(self.gtk.read_bytes().startswith(b'\xef\xbb\xbf@charset "UTF-8";\n/* dots'))
        self.assertTrue(self.qt.read_bytes().startswith(b'\xef\xbb\xbf[Appearance]\n'))
        self.assertEqual(self.qt.read_bytes().count(b'[Appearance]'), 1)
        before = self.snapshot()
        self.plugins('run')
        self.assertEqual(before, self.snapshot())

    def test_app_undo_and_drift_aware_restoration(self):
        self.apps()
        before = self.gtk.read_bytes()
        self.publish()
        journals = list((self.state.parent / 'files/transactions').glob('*/journal.json'))
        record = next(json.loads(p.read_text()) for p in journals if json.loads(p.read_text())['action'] == 'theme-plugin-gtk')
        installed = self.gtk.read_bytes()
        self.gtk.write_bytes(installed + b'/* later */')
        self.dots('files', 'undo', record['id'], '--yes', code=1)
        self.gtk.write_bytes(installed)
        self.dots('files', 'undo', record['id'], '--yes')
        self.assertEqual(before, self.gtk.read_bytes())
        self.assertFalse((self.config / 'gtk-3.0/dots-theme.css').exists())
        self.assertFalse((self.plugin_state / 'gtk.json').exists())

    def test_interrupted_app_write_recovery(self):
        self.apps()
        self.plugins('disable', 'gtk')
        self.plugins('disable', 'qt6ct')
        self.publish()
        before = self.gtk.read_bytes()
        script = '''
import os,sys
sys.path.insert(0,sys.argv[1])
import plugins,plugin_apps,transactions
original=transactions.os.rename
def stop(source,target):
    original(source,target)
    if str(target).endswith('/gtk.css'):
        os._exit(91)
transactions.os.rename=stop
_,config,state=plugins.roots()
generation,_=plugins.published(state)
plugin_apps.apply('gtk',config,state,generation)
'''
        self.run_command([self.python, '-B', '-c', script, str(self.lib)], code=91)
        record = next(json.loads(p.read_text()) for p in (self.state.parent / 'files/transactions').glob('*/journal.json'))
        self.assertEqual(record['status'], 'applying')
        self.dots('files', 'recover', record['id'], '--yes')
        self.assertEqual(before, self.gtk.read_bytes())
        self.assertFalse((self.config / 'gtk-3.0/dots-theme.css').exists())
        self.plugins('enable', 'gtk')
        self.plugins('run', 'gtk')

    def test_concurrency_interruption_and_lock_release(self):
        self.publish()
        self.hook('20-wait.sh', 'touch "$HOME/started"; sleep 30', True)
        command = [BASH, str(self.repo / 'bin/dots'), 'theme', 'plugins', 'run']
        process = subprocess.Popen(command, env=self.env, cwd=self.home, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not (self.home / 'started').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.home / 'started').exists())
            self.plugins('run', code=1)
            self.plugins('disable', 'wait', code=1)
            self.dots('theme', 'set', 'catppuccin-latte', code=1)
            self.plugins('doctor', 'wait')
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 130)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        self.plugins('disable', 'wait')
        self.dots('theme', 'refresh')

    def test_automatic_run_holds_publication_lock(self):
        self.hook('20-wait.sh', 'touch "$HOME/started"; while [[ ! -f "$HOME/release" ]]; do sleep 0.05; done', True)
        process = subprocess.Popen([BASH, str(self.repo / 'bin/dots'), 'theme', 'set', 'nord'],
                                   env=self.env, cwd=self.home, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not (self.home / 'started').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.home / 'started').exists())
            self.assertEqual((self.generation() / 'status').read_text().strip(), 'committed')
            self.plugins('run', code=1)
            self.dots('theme', 'set', 'catppuccin-latte', code=1)
            self.plugins('list', '--json')
        finally:
            (self.home / 'release').touch()
            process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0)
        self.plugins('run', 'wait')

    def test_unsafe_app_objects_and_atomic_preflight(self):
        self.apps()
        self.plugins('disable', 'gtk')
        self.plugins('disable', 'qt6ct')
        self.publish()
        original = self.gtk.read_bytes()
        self.gtk.unlink()
        outside = self.home / 'keep-css'
        outside.write_bytes(original)
        self.gtk.symlink_to(outside)
        self.plugins('enable', 'gtk')
        self.plugins('run', 'gtk', code=1)
        self.assertEqual(outside.read_bytes(), original)
        self.assertFalse((self.config / 'gtk-3.0/dots-theme.css').exists())
        self.gtk.unlink()
        os.mkfifo(self.gtk)
        self.plugins('run', 'gtk', code=1)
        self.plugins('doctor', 'gtk', code=1)
        self.assertFalse((self.config / 'gtk-3.0/dots-theme.css').exists())

    def test_app_failure_rolls_back_completed_operations(self):
        self.apps()
        self.plugins('disable', 'gtk')
        self.plugins('disable', 'qt6ct')
        self.publish()
        original = self.gtk.read_bytes()
        script = '''
import sys
sys.path.insert(0,sys.argv[1])
import plugins,plugin_apps,transactions
save=transactions.Store.save
def fail(self,record):
    save(self,record)
    if record['status']=='applying' and record['operations'][0]['phase']=='done':
        raise OSError('injected app write failure')
transactions.Store.save=fail
_,config,state=plugins.roots()
generation,_=plugins.published(state)
try:
    plugin_apps.apply('gtk',config,state,generation)
except OSError:
    pass
else:
    raise AssertionError('injection did not run')
'''
        self.run_command([self.python, '-B', '-c', script, str(self.lib)])
        self.assertEqual(self.gtk.read_bytes(), original)
        self.assertFalse((self.config / 'gtk-3.0/dots-theme.css').exists())
        record = next(json.loads(p.read_text()) for p in (self.state.parent / 'files/transactions').glob('*/journal.json'))
        self.assertEqual(record['status'], 'rolled-back')


if __name__ == '__main__':
    unittest.main()
