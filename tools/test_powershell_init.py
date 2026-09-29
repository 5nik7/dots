"""Portable native PowerShell acceptance; no Bash or live profile is used."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PWSH = shutil.which('pwsh')


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(PWSH, 'PowerShell unavailable; native acceptance not verified')
class PowerShellInitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-powershell-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo space ü ' [literal]"
        self.home = self.root / 'home'
        self.home.mkdir()
        for directory in ('bin', 'scripts', 'local/bin', 'shells/powershell'):
            (self.repo / directory).mkdir(parents=True, exist_ok=True)
        for name in ('bin/dots.ps1', 'shells/powershell/init.ps1',
                     'shells/powershell/environment.ps1', 'shells/powershell/interactive.ps1',
                     'shells/powershell/Microsoft.PowerShell_profile.ps1'):
            shutil.copy2(REPO / name, self.repo / name)
        # PATH deliberately contains no Bash or other external tools.
        self.env = {'HOME': str(self.home), 'USERPROFILE': str(self.home),
                    'DOTS': str(self.repo), 'PATH': str(self.repo / 'bin'),
                    'APPDATA': str(self.home / 'appdata'),
                    'LOCALAPPDATA': str(self.home / 'localappdata'),
                    'TMPDIR': str(self.root), 'TEMP': str(self.root), 'TMP': str(self.root),
                    'XDG_CONFIG_HOME': str(self.home / 'config'),
                    'XDG_DATA_HOME': str(self.home / 'data'),
                    'XDG_STATE_HOME': str(self.home / 'state'),
                    'XDG_CACHE_HOME': str(self.home / 'cache')}
        for key in ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'LD_PRELOAD'):
            if key in os.environ:
                self.env[key] = os.environ[key]

    def run_ps(self, *args):
        return subprocess.run([PWSH, '-NoProfile', '-NonInteractive', *args],
                              cwd=self.home, env=self.env, text=True,
                              capture_output=True, timeout=30)

    def test_native_files_parse(self):
        for file in self.repo.rglob('*.ps1'):
            code = ('$tokens = $null; $errors = $null; '
                    '[void][System.Management.Automation.Language.Parser]::ParseFile('
                    + literal(file) + ', [ref]$tokens, [ref]$errors); '
                    'if ($errors.Count) { $errors | Out-String | Write-Error; exit 1 }')
            p = self.run_ps('-Command', code)
            self.assertEqual(p.returncode, 0, str(file) + p.stderr)

    def test_generator_and_environment_without_bash(self):
        # Prove noninteractive initialization never evaluates the interactive body.
        (self.repo / 'shells/powershell/interactive.ps1').write_text("throw 'interactive body ran'\n")
        self.env['DOTCONFIG'] = str(self.home / 'override')
        adapter = literal(self.repo / 'bin/dots.ps1')
        code = (f'$hook = & {adapter} init powershell; '
                'if (-not $?) { exit 1 }; '
                '$hook | Out-String | Invoke-Expression; '
                '$hook | Out-String | Invoke-Expression; '
                '@{root=$env:DOTS; config=$env:DOTCONFIG; path=$env:PATH} | ConvertTo-Json -Compress')
        p = self.run_ps('-Command', code)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        result = json.loads(p.stdout)
        self.assertEqual(result['root'], str(self.repo))
        self.assertEqual(result['config'], str(self.repo / 'config'))
        entries = result['path'].split(os.pathsep)
        for directory in ('bin', 'scripts'):
            self.assertEqual(entries.count(str(self.repo / directory)), 1)
        self.assertNotIn(str(self.repo / 'local/bin'), entries)
        self.assertLess(entries.index(str(self.repo / 'scripts')), entries.index(str(self.repo / 'bin')))

    def test_invalid_route_and_missing_loader_emit_no_code(self):
        adapter = str(self.repo / 'bin/dots.ps1')
        for args in [('status',), ('init', 'bash'), ('init', 'powershell', 'extra')]:
            p = self.run_ps('-File', adapter, *args)
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertEqual(p.stdout, '')
        (self.repo / 'shells/powershell/init.ps1').unlink()
        p = self.run_ps('-File', adapter, 'init')
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(p.stdout, '')


    def test_profile_links_and_relocation(self):
        (self.repo / 'shells/powershell/interactive.ps1').write_text("throw 'interactive body ran'\n")
        profile = self.repo / 'shells/powershell/Microsoft.PowerShell_profile.ps1'
        link = self.home / 'linked-profile.ps1'
        try:
            link.symlink_to(profile)
        except OSError as error:
            self.skipTest('Filesystem symlink capability unavailable: ' + str(error))
        relative = self.home / 'relative-profile.ps1'
        relative.symlink_to('linked-profile.ps1')
        directory = self.home / 'linked-directory'
        directory.symlink_to(profile.parent, target_is_directory=True)
        for entry in (profile, link, relative, directory / profile.name):
            with self.subTest(entry=entry):
                self.env['DOTS'] = str(self.root / 'wrong checkout')
                self.env['DOTCONFIG'] = str(self.root / 'wrong config')
                code = ('. ' + literal(entry) + '; . ' + literal(entry) + '; '
                        '@{root=$env:DOTS; config=$env:DOTCONFIG; shell=$env:PWSH; cwd=(Get-Location).Path} | ConvertTo-Json -Compress')
                p = self.run_ps('-Command', code)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stderr, '')
                result = json.loads(p.stdout)
                self.assertEqual(result['root'], str(self.repo))
                self.assertEqual(result['config'], str(self.repo / 'config'))
                self.assertEqual(result['shell'], str(profile.parent))
                self.assertEqual(result['cwd'], str(self.home))
        moved = self.root / 'moved checkout'
        self.repo.rename(moved)
        link.unlink()
        link.symlink_to(moved / 'shells/powershell' / profile.name)
        p = self.run_ps('-Command', '. ' + literal(relative) + '; $env:DOTS')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), str(moved))

    def test_missing_checkout_returns_error(self):
        (self.repo / 'bin/dots.ps1').unlink()
        p = self.run_ps('-Command', '. ' + literal(self.repo / 'shells/powershell/Microsoft.PowerShell_profile.ps1'))
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(p.stdout, '')
        self.assertIn('checkout layout', p.stderr)


    @unittest.skipUnless(os.name == 'nt', 'Directory junctions require native Windows')
    def test_junction_directory(self):
        junction = self.home / 'config junction'
        target = self.repo / 'shells/powershell'
        p = self.run_ps('-Command', 'New-Item -ItemType Junction -Path ' + literal(junction) +
                        ' -Target ' + literal(target) + ' | Out-Null')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.env['DOTS'] = str(self.root / 'wrong checkout')
        p = self.run_ps('-Command', '. ' + literal(junction / 'Microsoft.PowerShell_profile.ps1') + '; $env:DOTS')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), str(self.repo))


if __name__ == '__main__':
    unittest.main()
