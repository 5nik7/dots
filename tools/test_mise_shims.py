"""Check mise path precedence using disposable homes and literal global settings."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib/dots'))
from mise_shims import resolve
from native_startup import generate
from native_environment import exports


class MiseShims(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='dots mise ü ')
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        self.env = {'HOME': str(self.home), 'USERPROFILE': str(self.home)}

    def test_precedence_and_missing_config_watch(self):
        env, home = self.env, self.home
        windows = os.name == 'nt'
        self.assertEqual(resolve(env, windows), home / ('AppData/Local' if windows else '.local/share') / 'mise/shims')
        env['XDG_DATA_HOME'] = str(home / 'xdg')
        self.assertEqual(resolve(env, windows), home / 'xdg/mise/shims')
        env['MISE_DATA_DIR'] = str(home / 'data')
        env['MISE_GLOBAL_CONFIG_FILE'] = str(home / 'alternate.toml')
        inputs = []
        self.assertEqual(resolve(env, windows, inputs), home / 'data/shims')
        self.assertEqual(inputs, [home / 'alternate.toml'])
        inputs[0].write_text("[settings]\nshims_dir = '~/global shims'\n", encoding='utf-8')
        self.assertEqual(resolve(env, windows), home / 'global shims')
        inputs[0].write_bytes(b'\xff invalid')
        self.assertEqual(resolve(env, windows), home / 'data/shims')
        env['MISE_SHIMS_DIR'] = str(home / 'explicit')
        self.assertEqual(resolve(env, windows), home / 'explicit')
        env['MISE_SHIMS_DIR'] = '../relative'
        self.assertIsNone(resolve(env, windows))

    @unittest.skipUnless(shutil.which('mise'), 'mise unavailable')
    def test_installed_mise_global_config_overrides(self):
        env = {key: os.environ[key] for key in ('PATH','SystemRoot','PATHEXT','COMSPEC') if key in os.environ}
        env.update(self.env, APPDATA=str(self.home/'appdata'), LOCALAPPDATA=str(self.home/'local'),
                   MISE_CONFIG_DIR=str(self.home/'config'), MISE_DATA_DIR=str(self.home/'data'),
                   MISE_CACHE_DIR=str(self.home/'cache'), MISE_STATE_DIR=str(self.home/'state'), MISE_ENV='dev')
        directory = Path(env['MISE_CONFIG_DIR'])
        folder = directory/'conf.d'/'folder'
        folder.mkdir(parents=True)
        for config in (folder.parent/'one.toml', folder/'mise.toml', directory/'config.toml',
                       directory/'config.dev.toml', directory/'config.local.toml',
                       directory/'config.override.toml', self.home/'alternative.toml'):
            if config.parent == self.home:
                env['MISE_GLOBAL_CONFIG_FILE'] = str(config)
            expected = self.home / (config.stem + ' shims')
            config.write_text("[settings]\nshims_dir = '" + expected.as_posix() + "'\n", encoding='utf-8')
            result = subprocess.run([shutil.which('mise'), 'settings', 'get', 'shims_dir'], cwd=self.home,
                                    env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()), expected)
            self.assertEqual(resolve(env, os.name == 'nt'), Path(result.stdout.strip()))

    @unittest.skipUnless(shutil.which('pwsh'), 'pwsh unavailable')
    def test_activated_versions_keep_precedence_on_reload(self):
        root = Path(__file__).resolve().parents[1]
        shim, installed, original = (self.home/name for name in ('shims', 'installed', 'original'))
        for directory in (shim, installed, original):
            directory.mkdir()
        env = {k: os.environ[k] for k in ('SystemRoot','PATHEXT','COMSPEC','OS') if k in os.environ}
        env.update(self.env, DOTS=str(root), MISE_SHIMS_DIR=str(shim), MISE_SHELL='pwsh',
                   __MISE_ORIG_PATH=str(original), DOTS_PROFILE_PATHS=str(shim),
                   APPDATA=str(self.home/'roam'), LOCALAPPDATA=str(self.home/'local'),
                   XDG_CACHE_HOME=str(self.home/'cache'), PSModuleAnalysisCachePath=str(self.home/'ps.cache'),
                   POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off')
        with patch.dict(os.environ, env, clear=True):
            (self.home/'cache.ps1').write_text(generate(root, 'powershell'), encoding='utf-8-sig')
        for initial, expected in (([installed, original, shim], [installed, original, shim]),
                                  ([installed, original], [installed, shim, original])):
            env['PATH'] = os.pathsep.join(map(str, initial))
            python_path = exports(root, env)['PATH']
            result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command',
                                     '$ok = . ./cache.ps1; if (-not $ok) { exit 1 }; $env:PATH'],
                                    env=env, cwd=self.home, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            for path in (python_path, result.stdout.strip()):
                self.assertEqual([Path(p) for p in path.split(os.pathsep) if Path(p) in expected], expected)

    @unittest.skipUnless(shutil.which('pwsh'), 'pwsh unavailable')
    def test_warm_cache_rejects_new_and_deleted_global_config(self):
        root = Path(__file__).resolve().parents[1]
        env = {key: os.environ[key] for key in ('PATH','SystemRoot','PATHEXT','COMSPEC','OS') if key in os.environ}
        env.update(self.env, DOTS=str(root), MISE_CONFIG_DIR=str(self.home / 'config'),
                   APPDATA=str(self.home / 'roam'), LOCALAPPDATA=str(self.home / 'local'),
                   XDG_CACHE_HOME=str(self.home / 'cache'), XDG_STATE_HOME=str(self.home / 'state'),
                   PSModuleAnalysisCachePath=str(self.home / 'modules.cache'),
                   POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off')
        def prepare():
            with patch.dict(os.environ, env, clear=True):
                (self.home / 'generated.ps1').write_text(generate(root, 'powershell'), encoding='utf-8-sig')
        def load():
            result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command',
                                     '. ./generated.ps1'], cwd=self.home, env=env, capture_output=True,
                                    text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()
        prepare()
        self.assertEqual(load(), 'True')
        config = self.home / 'config/config.toml'
        config.parent.mkdir()
        config.write_text("[settings]\nshims_dir = '~/shims'\n")
        self.assertEqual(load(), 'False')
        prepare()
        self.assertEqual(load(), 'True')
        config.unlink()
        self.assertEqual(load(), 'False')


if __name__ == '__main__':
    unittest.main()
