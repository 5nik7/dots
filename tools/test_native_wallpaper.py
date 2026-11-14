"""Native wallpaper boundaries; never invoke a desktop or lock-screen setter."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'lib/dots'
for path in (LIB, LIB / 'files', LIB / 'themes'):
    sys.path.insert(0, str(path))
import wallpaper
import theme_cli


class NativeWallpaper(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-wallpaper-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home ü'
        self.home.mkdir()
        self.image = self.home / '-image ü & literal.png'
        self.image.write_bytes(b'fixture; no image decoder or setter runs')
        self.env = {key: value for key, value in os.environ.items()
                    if key.upper() in ('SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC', 'PATHEXT', 'PATH', 'OS')}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home),
                        APPDATA=str(self.home / 'Roaming'), LOCALAPPDATA=str(self.home / 'Local'),
                        DOTS=str(self.home / 'repo'), DOTS_COLOR='never', DOTS_ICONS='never',
                        DOTS_PROGRESS='never', PYTHONDONTWRITEBYTECODE='1')
        for kind in ('CONFIG', 'DATA', 'STATE', 'CACHE'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / kind.lower())
        self.env.update(TEMP=str(self.home / 'tmp'), TMP=str(self.home / 'tmp'))
        (self.home / 'tmp').mkdir()
        self.guard = patch.dict(os.environ, self.env, clear=True)
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def test_private_transport_is_literal_and_check_never_supplies_image(self):
        response = SimpleNamespace(returncode=0, stdout='{"supported":true}')
        with patch.object(wallpaper, 'windows_powershell', return_value=Path('engine.exe')), \
             patch.object(wallpaper.subprocess, 'run', return_value=response) as run:
            self.assertTrue(wallpaper.lock_screen_supported())
            self.assertEqual(run.call_args.args[0][-1], '-Check')
            self.assertEqual(run.call_args.kwargs['input'], '')
            response.stdout = '{"applied":true}'
            self.assertEqual(wallpaper.lock_screen_request(self.image), {'applied': True})
            self.assertNotIn(str(self.image), run.call_args.args[0])
            self.assertEqual(json.loads(run.call_args.kwargs['input']), {'path': str(self.image)})
            self.assertEqual(run.call_args.kwargs['timeout'], 15)
            response.returncode = 1
            self.assertFalse(wallpaper.lock_screen_supported())
            with self.assertRaises(ValueError): wallpaper.lock_screen_request(self.image)
            run.side_effect = subprocess.TimeoutExpired('fixture', 15)
            self.assertFalse(wallpaper.lock_screen_supported())

    @unittest.skipUnless(os.name == 'nt', 'native Windows WinRT projection required')
    def test_native_storage_file_and_setter_boundary(self):
        engine = wallpaper.windows_powershell()
        source = str(LIB / 'themes/wallpaper.ps1').replace("'", "''")
        payload = base64.b64encode(json.dumps({'path': str(self.image)}).encode()).decode()
        # Only StorageFile resolution is real. The sole setter boundary is
        # replaced before any request; no native image operation can execute.
        code = f"""
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
. '{source}'
function Test-DotsLockScreenSupport {{ $true }}
function Set-DotsLockScreenFile {{ param($File,$Deadline)
 if($File.Path -cne $env:DOTS_TEST_IMAGE) {{throw 'path changed'}}
 $script:called=$true
}}
$request=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload}'))
$result=Invoke-DotsLockScreenRequest $request | ConvertFrom-Json
if(-not $result.applied -or -not $script:called) {{throw 'setter boundary missing'}}
function Test-DotsLockScreenSupport {{ $false }}
$script:called=$false
try {{Invoke-DotsLockScreenRequest $request;throw 'unexpected success'}} catch {{
 if($_.Exception.Message -ne 'Windows lock-screen API is unavailable.') {{throw}}
}}
if($script:called) {{throw 'unsupported setter called'}}
# Exercise the same IAsyncAction projection with an owned disposable file,
# never the lock-screen API. StorageFile resolution above already owns this path.
$file=Get-DotsLockScreenFile $env:DOTS_TEST_IMAGE ([DateTime]::UtcNow.AddSeconds(12))
Wait-DotsWallpaperAction ($file.DeleteAsync()) ([DateTime]::UtcNow.AddSeconds(12))
if([IO.File]::Exists($env:DOTS_TEST_IMAGE)) {{throw 'owned async action incomplete'}}
'ok'
"""
        result = subprocess.run([str(engine), '-NoLogo', '-NoProfile', '-NonInteractive',
            '-EncodedCommand', base64.b64encode(code.encode('utf-16-le')).decode()],
            env=dict(self.env, DOTS_TEST_IMAGE=str(self.image)), capture_output=True,
            text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), 'ok')
        self.assertFalse(result.stderr)

    @unittest.skipUnless(os.name == 'nt', 'native Windows route')
    def test_preflight_is_read_only_and_failed_setter_preserves_record(self):
        themes = SimpleNamespace(directory=lambda _: self.home / 'theme',
                                 config=self.home / 'config', state=self.home / 'state',
                                 current=lambda: 'fixture')
        with patch.object(wallpaper, 'lock_screen_supported', return_value=False), \
             patch.object(theme_cli.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'API unavailable'):
                theme_cli.backgrounds(themes, 'set', [str(self.image), '--lock-screen'], preflight=True)
            run.assert_not_called()
            self.assertFalse(themes.state.exists())
        with patch.object(wallpaper, 'lock_screen_supported', return_value=True), \
             patch.object(wallpaper, 'lock_screen_request') as request, \
             patch.object(theme_cli.subprocess, 'run') as run:
            self.assertEqual(theme_cli.backgrounds(themes, 'set', [str(self.image), '--lock-screen'], preflight=True), str(self.image))
            run.assert_not_called()
            request.assert_not_called()
            self.assertFalse(themes.state.exists())
            themes.state.mkdir()
            current = themes.state / 'background-current'
            current.write_text('original desktop\n')
            request.return_value = {'applied': False}
            with self.assertRaisesRegex(ValueError, 'wallpaper failed'):
                theme_cli.backgrounds(themes, 'set', [str(self.image), '--lock-screen'])
            self.assertEqual(current.read_text(), 'original desktop\n')
            request.assert_called_once_with(self.image)
            run.assert_not_called()
            journal = next((themes.state / 'backgrounds').glob('action.*.json'))
            self.assertEqual(json.loads(journal.read_text())['status'], 'failed')
            request.return_value = {'applied': True}
            theme_cli.backgrounds(themes, 'set', [str(self.image), '--lock-screen'])
            self.assertEqual(current.read_text(), 'original desktop\n')
            self.assertFalse((themes.state / 'backgrounds/fixture').exists())


if __name__ == '__main__':
    unittest.main()
