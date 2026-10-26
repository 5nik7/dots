#!/usr/bin/env python3
"""Native command contracts; all writes are confined to temporary fixture roots."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'lib/dots'
sys.path.insert(0, str(LIB))
from command_metadata import catalog, roots, resolve


class NativeCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots native ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home, self.repo = self.base / 'home', self.base / 'repo'
        self.home.mkdir(); self.repo.mkdir()
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith(('DOTS_', 'GIT_', 'BAT_')) or key in ('TMUX','KITTY_LISTEN_ON','WAYLAND_DISPLAY','DISPLAY','DOTHEMES','THEMES','TERMUX_VERSION','EZA_CONFIG_DIR','TELEVISION_CONFIG','TELEVISION_DATA','YAZI_CONFIG_HOME'): self.env.pop(key)
        self.env.update(DOTS=str(self.repo), HOME=str(self.home), USERPROFILE=str(self.home),
                        XDG_CONFIG_HOME=str(self.home/'config'), XDG_STATE_HOME=str(self.home/'state'),
                        XDG_CACHE_HOME=str(self.home/'cache'), XDG_DATA_HOME=str(self.home/'data'),
                        APPDATA=str(self.home/'Roaming'), LOCALAPPDATA=str(self.home/'Local'),
                        CODEX_HOME=str(self.home/'codex'), PI_CODING_AGENT_DIR=str(self.home/'pi'),
                        BAT_CONFIG_DIR=str(self.home/'config/bat'),
                        DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never',
                        PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        engine_cache = self.base / 'powershell-cache'
        engine_cache.mkdir()
        self.env.update(PSModuleAnalysisCachePath=str(engine_cache / 'ModuleAnalysisCache'),
                        POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off')
        shutil.copytree(LIB, self.repo / 'lib/dots', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT / 'bin', self.repo / 'bin', symlinks=True)
        (self.repo / '.dots').mkdir()
        all_platforms = ['termux','linux','wsl','windows']
        (self.repo / '.dots/sources.json').write_text(json.dumps(dict(schema=1, sources=[dict(id='dots',path='.',roots=['config'],platforms=all_platforms)])))
        (self.repo / 'config').mkdir()
        (self.repo / 'config/example ü.txt').write_text('fixture\n')
        (self.repo / '.dots/files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[dict(id='example',source='config/example ü.txt',target='${CONFIG}/example ü.txt',app='example',category='config',platforms=all_platforms,strategy='link')])) )

    def command(self, *args, expected=0):
        result = subprocess.run([sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),*args], env=self.env,
                                text=True, encoding='utf-8', capture_output=True, timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_all_metadata_and_targeted_resolution(self):
        rows = catalog(roots(self.repo))
        self.assertGreaterEqual(len(rows), 84)
        for name in rows:
            stem, path, count = resolve(roots(self.repo), name.split('-') + ['--json'])
            self.assertEqual(stem, name)
            self.assertEqual(count, len(name.split('-')))
        self.command('commands','--check')
        self.assertFalse(list(self.home.iterdir()))

    def test_file_routes_and_completion(self):
        doc = json.loads(self.command('files','list','--json').stdout)
        self.assertEqual(doc['resources'][0]['id'],'dots:example')
        self.assertIn('--pick', self.command('__complete','files','link','--p').stdout)
        self.assertIn('dots:example',self.command('__complete','files','link','dots:').stdout)
        self.assertIn('--verbose',self.command('__complete','init','--setup','--v').stdout)
        self.command('files','link','dots:example','--dry-run','--json')
        self.assertIn('--yes', self.command('__complete','files','repair','--y').stdout)
        self.assertIn('dots:example', self.command('__complete','files','repair','dots:').stdout)
        self.assertEqual(json.loads(self.command('files','repair','--dry-run','--json').stdout)['action'], 'repair')
        self.assertFalse(list(self.home.iterdir()))

    def test_literal_argument_bridge(self):
        spec = importlib.util.spec_from_file_location('dots_native_test', LIB/'native.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        values = ['', '-leading', 'a "quoted" value', "single'quote", 'ü', '$(touch no)', 'a&b|c;d', 'C:\\a b\\']
        encoded = base64.b64encode(json.dumps(values).encode()).decode()
        previous = sys.argv
        try:
            with patch.object(module.runpy,'run_path') as run:
                module.main(['cli',encoded])
                self.assertEqual(sys.argv[1:],values)
                self.assertEqual(run.call_count,1)
            for invalid in ('{}', '[1]', '["\\u0000"]'):
                with self.assertRaises(ValueError): module.main(['cli',base64.b64encode(invalid.encode()).decode()])
        finally: sys.argv = previous

    def test_windows_path_validation(self):
        sys.path.insert(0,str(LIB/'files'))
        from file_platform import validate_windows_path
        for path in ('C:\\Users\\a b\\config.txt', 'D:\\日本語\\file'):
            validate_windows_path(path)
        for path in ('C:relative','C:\\Users\\NUL','C:\\file:stream','C:\\dir.\\file','\\\\wsl.localhost\\Ubuntu\\home\\file'):
            with self.assertRaises(ValueError, msg=path): validate_windows_path(path)

    def test_native_theme_data_matches_bash(self):
        if not shutil.which('bash') or os.name == 'nt': self.skipTest('Bash comparison requires POSIX')
        sys.path.insert(0,str(LIB/'themes'))
        from palette_native import Themes
        with patch.dict(os.environ,dict(self.env,DOTS=str(ROOT)),clear=True):
            themes = Themes()
            for identity in themes.ids():
                if identity == 'pywal16-current': continue
                result = subprocess.run(['bash',str(LIB/'themes/colors-query.bash'),identity],env=dict(self.env,DOTS=str(ROOT)),text=True,capture_output=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                expected = json.loads(result.stdout)
                actual = themes.load(identity)
                self.assertEqual(actual,expected,identity)

    def test_windows_app_paths_and_ambiguous_variants(self):
        sys.path.insert(0, str(LIB / 'files'))
        from app_paths import config_directory
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(config_directory('yazi'), self.home / 'Roaming/yazi/config')
            self.assertEqual(config_directory('eza'), self.home / 'Roaming/eza')
            with patch.dict(os.environ, EZA_CONFIG_DIR=str(self.home / 'custom eza')):
                self.assertEqual(config_directory('eza'), self.home / 'custom eza')
            self.assertEqual(config_directory('glaze-wm'), self.home / '.glzr/glazewm')
            self.assertIsNone(config_directory('wt'))
            stable = self.home / 'Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState'
            stable.mkdir(parents=True)
            self.assertEqual(config_directory('wt'), stable)
            preview = self.home / 'Local/Packages/Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe/LocalState'
            preview.mkdir(parents=True)
            self.assertIsNone(config_directory('wt'))
            with patch.dict(os.environ, DOTS_APP_WT_CONFIG=str(stable)):
                self.assertEqual(config_directory('wt'), stable)
            self.assertIsNone(config_directory('filepilot'))

    def test_native_publication_undo_idempotence_and_drift(self):
        sys.path.insert(0, str(LIB / 'themes'))
        from palette_native import Themes
        import theme_cli
        from transactions import Store
        eza = self.home / 'eza ü/theme.yml'
        eza.parent.mkdir(); eza.write_text('original eza theme\n')
        self.env['EZA_CONFIG_DIR'] = str(eza.parent)
        with patch.dict(os.environ, dict(self.env, DOTS=str(ROOT)), clear=True), patch.object(theme_cli, 'reload_apps') as reload:
            themes = Themes()
            identity = 'catppuccin-mocha'
            theme_cli.publication(themes, identity, dry=True)
            self.assertFalse(themes.state.exists())
            first = theme_cli.publication(themes, identity)
            palette = themes.load(identity)
            snapshot = (themes.state / 'current/theme/shell.tsv').read_text()
            for name in ('foreground', 'background', 'lighter_background'):
                self.assertIn(name + '\thex\t' + palette['colors'][name] + '\n', snapshot)
                self.assertIn("'" + name + "' = @{", theme_cli.shell_init(palette, 'powershell'))
            self.assertTrue(eza.is_symlink())
            self.assertIn('colourful: true', eza.read_text())
            records = Store(themes.state).records()
            self.assertEqual(len(records), 1)
            self.assertEqual(theme_cli.publication(themes, identity), first)
            self.assertEqual(len(Store(themes.state).records()), 1)
            reload.assert_called_once()
            wrapper = themes.state / 'themes/commands/current/bin/catppuccin.ps1'
            original = wrapper.read_bytes()
            wrapper.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'drift'):
                theme_cli.publication(themes, identity)
            wrapper.write_bytes(original)
            store = Store(themes.state)
            operations, guards, _ = store.inverse(records[0]['id'])
            store.apply('test-undo', operations, guards, retain=True)
            self.assertFalse((themes.state / 'current/theme').exists())
            self.assertEqual(eza.read_text(), 'original eza theme\n')
            self.assertFalse(eza.is_symlink())

    def test_native_publication_rolls_back_after_live_replacement(self):
        sys.path.insert(0, str(LIB / 'themes'))
        import theme_cli
        from palette_native import Themes
        from transactions import Store
        eza = self.home / 'eza/theme.yml'
        eza.parent.mkdir(); eza.write_text('original eza theme\n')
        self.env['EZA_CONFIG_DIR'] = str(eza.parent)
        save = Store.save
        injected = []
        def fail_after_generation(store, doc):
            save(store, doc)
            if doc['status'] == 'applying' and eza.is_symlink() and not injected:
                injected.append(True)
                raise OSError('fixture interruption after replacement')
        with patch.dict(os.environ, dict(self.env, DOTS=str(ROOT)), clear=True), patch.object(theme_cli, 'reload_apps'):
            themes = Themes()
            with patch.object(Store, 'save', fail_after_generation), self.assertRaisesRegex(OSError, 'fixture interruption'):
                theme_cli.publication(themes, 'catppuccin-mocha')
            self.assertTrue(injected)
            self.assertEqual(eza.read_text(), 'original eza theme\n')
            self.assertFalse(eza.is_symlink())
            self.assertFalse((themes.state / 'current/theme').exists())
            self.assertFalse((themes.state / 'themes/current').exists())
            self.assertTrue(all(r['status'] == 'rolled-back' for r in Store(themes.state).records()))
            theme_cli.publication(themes, 'catppuccin-mocha')
            self.assertTrue((themes.state / 'current/theme').is_symlink())

    def test_native_environment_and_palette_completion(self):
        shutil.copytree(ROOT / 'themes/catppuccin', self.repo / 'themes/catppuccin')
        for flavor in ('mocha', 'latte', 'frappe', 'macchiato'):
            shutil.copytree(ROOT / ('themes/catppuccin-' + flavor), self.repo / ('themes/catppuccin-' + flavor))
        self.assertIn('candidate\tmocha\t', self.command('__complete','theme','catppuccin','--flavor','').stdout)
        self.assertIn('candidate\tred\t', self.command('__complete','theme','catppuccin','mocha','--color','').stdout)
        self.assertIn('candidate\tansi-24bit\t', self.command('__complete','theme','color','red','').stdout)
        native = json.loads(self.command('env', '--json').stdout)
        if shutil.which('bash') and os.name != 'nt':
            result = subprocess.run(['bash',str(self.repo / 'bin/dots-env'),'--json'],env=self.env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(native,json.loads(result.stdout))
        result = self.command('--color=always','theme','catppuccin','mocha','red','hex')
        self.assertEqual(result.stdout.strip(), '#f38ba8')
        self.assertNotIn('\x1b', result.stdout)

    def test_native_setup_inspection_is_read_only(self):
        env = dict(self.env, DOTS=str(ROOT))
        result = subprocess.run([sys.executable, '-B', str(LIB / 'themes/setup.py'), 'inspect'],
                                env=env, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(len(result.stdout.split(b'\0')), 5)
        self.assertFalse(list(self.home.iterdir()))

    def test_native_setup_preparation_flushes_without_publication(self):
        env = dict(self.env, DOTS=str(ROOT))
        command = [sys.executable, '-B', str(LIB / 'themes/setup.py')]
        inspection = subprocess.run([*command, 'inspect'], env=env, capture_output=True, timeout=30)
        self.assertEqual(inspection.returncode, 0, inspection.stderr.decode())
        fingerprint = inspection.stdout.decode().split('\0')[1]
        prepared = subprocess.run([*command, 'prepare', fingerprint], env=env,
                                  capture_output=True, timeout=60)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        generation = Path(prepared.stdout.decode().split('\0')[0])
        state = self.home / 'state/dots'
        self.assertEqual(generation.parent, state / 'themes/generations')
        self.assertEqual((generation / 'status').read_text(), 'committed\n')
        self.assertTrue((generation / 'palette.json').is_file())
        for name in ('themes/current', 'current/theme', 'themes/commands/current'):
            self.assertFalse(os.path.lexists(state / name), name)

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_native_theme_source_lifecycle_preserves_local_changes(self):
        sys.path.insert(0, str(LIB / 'themes'))
        from palette_native import Themes
        from theme_source import source_operation
        from transactions import Store
        source = self.base / 'upstream theme'
        source.mkdir()
        shutil.copyfile(ROOT / 'themes/catppuccin-mocha/colors.toml', source / 'colors.toml')
        env = dict(self.env, DOTS_TEST_LOCAL_GIT='always',
                   GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                   GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        def git(*args):
            result = subprocess.run(['git', '-C', str(source), *args], env=env,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
        git('init', '--quiet'); git('add', '.'); git('commit', '--quiet', '-m', 'fixture')
        with patch.dict(os.environ, env, clear=True):
            themes = Themes()
            source_operation(themes, 'install', [str(source), '--name', 'fixture-import'])
            target = themes.user / 'fixture-import'
            self.assertEqual(themes.load('fixture-import')['id'], 'fixture-import')
            self.assertFalse((themes.state / 'current/theme').exists())
            (source / 'README.md').write_text('upstream update\n')
            git('add', '.'); git('commit', '--quiet', '-m', 'update')
            source_operation(themes, 'update', ['fixture-import'])
            self.assertEqual((target / 'README.md').read_text(), 'upstream update\n')
            (target / 'README.md').write_text('local edit\n')
            for action in ('update', 'remove'):
                with self.assertRaisesRegex(ValueError, 'local changes'):
                    source_operation(themes, action, ['fixture-import'])
            (target / 'README.md').write_text('upstream update\n')
            source_operation(themes, 'remove', ['fixture-import'])
            self.assertFalse(target.exists())
            self.assertEqual(len(Store(themes.state).records()), 3)

    def assert_read_only_home(self):
        # PowerShell's runtime can write its startup profile even with -NoProfile.
        # Permit only its known files and ancestors, never arbitrary cache writes.
        roots = [self.home / name for name in ('cache/powershell',
                 'Local/Microsoft/Windows/PowerShell', 'Local/Microsoft/PowerShell')]
        for path in self.home.rglob('*'):
            self.assertFalse(path.is_symlink(), str(path))
            if path.is_dir():
                self.assertTrue(any(path == root or path in root.parents for root in roots), str(path))
            else:
                self.assertIn(path.parent, roots, str(path))
                self.assertRegex(path.name, r'^StartupProfileData-(?:NonInteractive|Interactive)$')
        for path in (self.base / 'powershell-cache').iterdir():
            self.assertFalse(path.is_symlink(), str(path))
            self.assertTrue(path.is_file(), str(path))
            self.assertRegex(path.name, r'^ModuleAnalysisCache(?:-[0-9a-fA-F]+)?$')

    def test_read_only_home_rejects_unrelated_cache_writes(self):
        startup = self.home / 'cache/powershell/StartupProfileData-NonInteractive'
        startup.parent.mkdir(parents=True)
        startup.write_bytes(b'engine fixture')
        self.assert_read_only_home()
        unexpected = startup.parent / 'dots'
        unexpected.mkdir()
        with self.assertRaises(AssertionError):
            self.assert_read_only_home()
        unexpected.rmdir()
        unexpected = self.home / 'state'
        unexpected.mkdir()
        with self.assertRaises(AssertionError):
            self.assert_read_only_home()

    def test_native_powershell_engines(self):
        requested = os.environ.get('DOTS_TEST_POWERSHELL')
        names = [requested] if requested else (['powershell','pwsh'] if os.name == 'nt' else ['pwsh'])
        engines = [shutil.which(name) for name in names]
        if requested and not all(engines): self.fail('required PowerShell engine unavailable: ' + requested)
        if not any(engines): self.skipTest('PowerShell unavailable; native acceptance remains pending')
        for engine in filter(None,engines):
            with self.subTest(engine=engine):
                code = "$files = @(Get-ChildItem -LiteralPath $env:DOTS -Recurse -Filter '*.ps1'); "
                code += "$files += @(Get-Item -LiteralPath (Join-Path $env:DOTS 'lib/dots/completion/powershell')); "
                code += "foreach ($file in $files) { $tokens = $null; $errors = $null; "
                code += "[void][System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors); "
                code += "if ($errors.Count) { $errors | Out-String | Write-Error; exit 1 } }"
                result = subprocess.run([engine, '-NoLogo', '-NoProfile', '-EncodedCommand',
                                         base64.b64encode(code.encode('utf-16-le')).decode()],
                                        env=self.env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                for args in (['--help'],['files','list','--json'],['files','link','dots:example','--dry-run','--json'],['files','repair','--dry-run','--json'],['completion','powershell']):
                    result=subprocess.run([engine,'-NoLogo','-NoProfile','-File',str(self.repo/'bin/dots.ps1'),*args],env=self.env,capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    if '--json' in args: json.loads(result.stdout)
                self.assert_read_only_home()
                probe = self.repo / 'local/bin/dots-probe.ps1'
                probe.parent.mkdir(parents=True, exist_ok=True)
                probe.write_text('# dots:summary=Literal argument fixture\n[Console]::WriteLine((ConvertTo-Json -InputObject @($args) -Compress))\nexit 7\n', encoding='utf-8')
                values = ['', 'a "quoted" value', "single'quote", 'ü', '$(throw 1)', 'a&b|c;d', 'C:\\a b\\']
                code = "$values = @(ConvertFrom-Json ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:DOTS_NATIVE_TEST_VALUES)))); & $env:DOTS_NATIVE_TEST_ADAPTER probe @values; exit $LASTEXITCODE"
                env = dict(self.env, DOTS_NATIVE_TEST_VALUES=base64.b64encode(json.dumps(values).encode()).decode(),
                           DOTS_NATIVE_TEST_ADAPTER=str(self.repo / 'bin/dots.ps1'))
                result = subprocess.run([engine, '-NoLogo', '-NoProfile', '-EncodedCommand', base64.b64encode(code.encode('utf-16-le')).decode()],
                                        env=env, capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout), values)


if __name__ == '__main__': unittest.main()
