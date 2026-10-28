"""Offline PowerShell completion guards, plus an optional real-engine matrix.

Static checks are not a PowerShell parser or native Windows evidence. The engine
matrix is skipped when pwsh is absent; it never invokes the Blastoff application.
"""
import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'powershell' / 'blastoff.psm1'
PWSH = shutil.which('pwsh')


class PowerShellCompletionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODULE.read_text(encoding='utf-8')
        cls.wrapper, cls.completer = cls.source.split('Register-ArgumentCompleter ', 1)

    def test_native_registration_for_unbound_function_arguments(self):
        self.assertTrue(self.completer.startswith(
            '-Native -CommandName blastoff, Invoke-Blastoff -ScriptBlock {'))
        self.assertIn('param($wordToComplete, $commandAst, $cursorPosition)', self.completer)
        self.assertNotIn('-ParameterName', self.completer)
        self.assertIn('CompletionResult]::new(', self.completer)
        self.assertIn('Export-ModuleMember -Function Invoke-Blastoff -Alias blastoff', self.source)

    def test_wrapper_forwarding_and_status_remain_intact(self):
        self.assertNotIn('CmdletBinding(', self.wrapper)
        self.assertNotIn('param(', self.wrapper)
        self.assertIn('& $runtime @prefix -I -B $script:CorePath --_powershell-argv-v1 $envelope', self.wrapper)
        self.assertIn('$global:LASTEXITCODE = $LASTEXITCODE', self.wrapper)
        self.assertIn('$global:LASTEXITCODE = 3', self.wrapper)
        self.assertIn('Set-Alias -Name blastoff -Value Invoke-Blastoff', self.wrapper)
        self.assertNotIn('LASTEXITCODE', self.completer)

    def test_completion_has_no_application_process_content_or_write_calls(self):
        code = re.sub(r'(?m)^\s*#.*$', '', self.completer)
        for forbidden in ('Invoke-Blastoff', 'python', 'starship', 'Get-Content',
                          'Set-Content', 'Add-Content', 'New-Item', 'Remove-Item',
                          'Start-Process', 'Invoke-Expression', 'Invoke-Command',
                          'Invoke-WebRequest', 'Invoke-RestMethod', 'WriteAll',
                          'ReadAll', 'Get-Command', '.Invoke(', 'SafeGetValue'):
            # The command name in the registration is declarative, not a call.
            body = code.split('-ScriptBlock {', 1)[1].split('Export-ModuleMember', 1)[0]
            self.assertNotIn(forbidden.lower(), body.lower())
        self.assertNotRegex(code, r'(?m)^\s*[&.]\s')
        self.assertIn('StringConstantExpressionAst', code)
        self.assertIn('Extent.EndOffset -ge $cursorPosition', code)

    def test_storage_root_aliases_keep_child_and_network_guards(self):
        self.assertIn("$item.LinkType -notin @('SymbolicLink', 'Junction')", self.completer)
        self.assertIn('$redirect -ge 40', self.completer)
        self.assertIn('$targets = @($item.Target)', self.completer)
        self.assertIn('[IO.Path]::GetFullPath($target,', self.completer)
        self.assertIn("DriveType -eq 'Network'", self.completer)
        self.assertIn('Get-Item -LiteralPath $directory', self.completer)
        self.assertIn('($item.Attributes -band $unsafe)', self.completer)

    def test_deduplication_preserves_case_distinct_names(self):
        self.assertIn('Sort-Object -CaseSensitive -Unique', self.completer)

    def test_static_vocabulary_and_safe_local_candidates(self):
        for word in ('list', 'current', 'pick', 'doctor', 'theme', 'preset',
                     'module', 'backup', 'migrate', 'completion', 'apply', 'save',
                     'copy', 'import', 'delete', 'load', 'create', 'restore',
                     '--help', '--json', '--color', '--force', '--replace-link',
                     '--verbose', '--dry-run', '--fancy', '--fzf', '--all', '--pick', '--yes', 'unicode', 'ascii', 'show', 'edit',
                     '--version', 'local:', 'preset:', 'bash', 'zsh', 'fish'):
            self.assertIn("'" + word + "'", self.completer)
        self.assertIn('$env:BLASTOFF_HOME', self.completer)
        self.assertNotIn('STARSHIP_CONFIG', self.completer)
        self.assertIn("Join-Path $HOME '.config/blastoff'", self.completer)
        self.assertIn('IsPathFullyQualified', self.completer)
        self.assertIn('-LiteralPath $directory', self.completer)
        self.assertIn('FileAttributes]::ReparsePoint', self.completer)
        self.assertIn(r'\A[A-Za-z0-9][A-Za-z0-9_-]{0,95}\z', self.completer)
        self.assertIn(r'\A(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])\z', self.completer)
        self.assertIn('$positionals.Count -eq 2', self.completer)
        self.assertIn("$kind = 'backups'", self.completer)


@unittest.skipUnless(PWSH, 'pwsh unavailable; no PowerShell/native Windows verification')
class PowerShellCompletionEngineTests(unittest.TestCase):
    def test_import_and_real_tab_expansion_are_offline(self):
        with tempfile.TemporaryDirectory(prefix='blastoff ps completion ') as tmp:
            home = Path(tmp)
            store = home / "store [literal] ' spaces"
            themes = store / 'themes'
            themes.mkdir(parents=True)
            (store / 'modules').mkdir()
            (store / 'backups').mkdir()
            for suffix in ('json','toml'):
                (store/'backups'/('sample.'+suffix)).write_text('')
            # Invalid TOML intentionally: completion must inspect names, not content.
            for name in ('alpha', 'a' * 96, 'a' * 97, 'bad.name', '_bad', 'éclair'):
                (themes / (name + '.toml')).write_text('not TOML', encoding='utf-8')
            # Probe the temporary filesystem, not the host OS, for case sensitivity.
            case_sensitive = not (themes / 'Alpha.toml').exists()
            if case_sensitive:
                (themes / 'Alpha.toml').write_text('not TOML')
            defaults = home / '.config' / 'blastoff'
            (defaults / 'themes').mkdir(parents=True)
            (defaults / 'themes' / 'default-theme.toml').write_text('not TOML')
            # Windows forbids creating device names even inside a temporary root.
            if os.name != 'nt':
                (themes / 'CON.toml').write_text('')
                (themes / 'linked.toml').symlink_to('alpha.toml')
                os.mkfifo(themes / 'pipe.toml')
            (themes / 'directory.toml').mkdir()
            (store / 'modules' / 'snippet.toml').write_text('not TOML')
            alias = home / 'linked store'
            if os.name == 'nt':
                cmd = str(Path(os.environ['SystemRoot'])/'System32/cmd.exe')
                subprocess.run([cmd, '/d', '/c', 'mklink', '/J', str(alias), str(store)],
                               capture_output=True, check=True, timeout=10)
            else:
                alias.symlink_to(store, target_is_directory=True)
            config = home / 'active.toml'
            config.write_text('unchanged')
            empty_bin = home / 'empty-bin'
            empty_bin.mkdir()
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                       BLASTOFF_HOME=str(store), STARSHIP_CONFIG=str(config),
                       BLASTOFF_PYTHON=str(empty_bin / 'must-not-run'),
                       BLASTOFF_TEST_PYTHON=sys.executable,
                       BLASTOFF_TEST_CASE_SENSITIVE=str(int(case_sensitive)),
                       BLASTOFF_TEST_LINKED_STORE=str(alias),
                       PATH=str(empty_bin), XDG_CACHE_HOME=str(home / 'cache'),
                       XDG_CONFIG_HOME=str(home / 'config'))
            manifest = str(ROOT / 'powershell' / 'blastoff.psd1').replace("'", "''")
            script = r'''
$ErrorActionPreference = 'Stop'
$global:LASTEXITCODE = 73
Import-Module '__MANIFEST__' -Force
if ($LASTEXITCODE -ne 73) { throw 'Import changed LASTEXITCODE' }
if (-not $IsWindows -and -not (Get-Item -LiteralPath '__MANIFEST__').PSObject.Properties['UnixMode']) { $env:BLASTOFF_PYTHON=$env:BLASTOFF_TEST_PYTHON }
function Check($line, $wanted, $unwanted, $cursor = $line.Length) {
    $matches = @((TabExpansion2 $line $cursor).CompletionMatches | ForEach-Object { $_.CompletionText })
    foreach ($value in $wanted) {
        if ($value -cnotin $matches) { throw "Missing $value for [$line]: $matches" }
    }
    foreach ($value in $unwanted) {
        if ($value -cin $matches) { throw "Unexpected $value for [$line]: $matches" }
    }
    if ($global:LASTEXITCODE -ne 73) { throw 'Completion changed LASTEXITCODE' }
}
foreach ($command in @('blastoff', 'Invoke-Blastoff')) {
    Check "$command th" @('theme') @()
    Check "$command theme " @('list', 'apply', 'save', 'copy', 'import', 'delete') @('restore')
    Check "$command --" @('--json', '--color', '--force', '--replace-link', '--version') @()
    Check "$command theme --" @('--help') @('--version', '--theme')
    Check "$command --color " @('auto', 'always', 'never') @('theme')
    Check "$command theme apply --color=a" @('--color=auto', '--color=always') @('alpha')
    Check "$command theme apply a" @('alpha', ('a' * 96)) @(('a' * 97))
    Check "$command theme apply " @('alpha', 'local:', 'preset:') @('CON', 'linked', 'pipe', 'directory', 'bad.name', '_bad', 'éclair')
    Check "$command theme apply local:a" @('local:alpha') @('alpha')
    Check "$command 'theme' 'apply' a" @('alpha') @()
    $prefix = "$command theme apply al"
    Check "$prefix --color never" @('alpha') @('never') $prefix.Length
    if ($env:BLASTOFF_TEST_CASE_SENSITIVE -eq '1') {
        Check "$command theme apply a" @('alpha', 'Alpha') @()
    }
    Check "$command --json theme --color auto apply --force a" @('alpha') @()
    Check "$command -theme a" @('alpha') @()
    Check "$command theme delete a" @('alpha') @('local:', 'preset:')
    Check "$command module load s" @('snippet') @('alpha')
    Check "$command module show s" @('snippet') @()
    Check "$command backup restore s" @('sample') @()
    Check "$command backup delete sample " @('sample','y','yes') @('all')
    Check "$command backup delete --all " @('y','yes') @('sample')
    Check "$command pick --fancy " @('unicode','ascii') @()
    Check "$command pick " @('fancy','fzf') @()
    Check "$command module show --" @('--fancy','--fzf') @()
    Check "$command backup delete --pick --" @('--fancy','--fzf') @()
    Check "$command module delete s" @('snippet') @()
    Check "$command theme copy alpha " @() @('alpha', 'local:', 'preset:')
    Check "$command theme save " @() @('alpha')
    Check "$command module save " @() @('snippet')
    Check "$command preset apply " @() @('alpha', 'plain-text-symbols')
    Check "$command theme apply preset:" @() @('preset:plain-text-symbols')
    Check "$command completion " @('bash', 'zsh', 'fish') @('powershell')
    Check "$command theme apply -- --" @() @('--json', '--force')
}
# Re-import must retain completion without touching exit status or launching a runtime.
Import-Module '__MANIFEST__' -Force
Check 'blastoff theme apply a' @('alpha') @()
$env:BLASTOFF_HOME = $env:BLASTOFF_TEST_LINKED_STORE
Check 'blastoff theme apply a' @('alpha') @('linked', 'pipe')
Check 'Invoke-Blastoff module load s' @('snippet') @()
# Default/tilde roots are resolved at completion time; never cached at import.
$env:BLASTOFF_HOME = ''
Check 'blastoff theme apply ' @('default-theme', 'local:', 'preset:') @('alpha')
$env:BLASTOFF_HOME = '~/.config/blastoff'
Check 'Invoke-Blastoff theme apply d' @('default-theme') @('alpha')
$env:BLASTOFF_HOME = '~/missing'
Check 'blastoff module load ' @() @('snippet')
$env:BLASTOFF_HOME = 'relative'
Check 'blastoff theme apply ' @() @('alpha')
'completion matrix passed'
'''.replace('__MANIFEST__', manifest)

            def snapshot():
                return {str(p): (p.lstat().st_mode, p.lstat().st_size, p.lstat().st_mtime_ns)
                        for p in [config, alias, store, *store.rglob('*'), defaults, *defaults.rglob('*')]}

            before = snapshot()
            encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
            result = subprocess.run([PWSH, '-NoLogo', '-NoProfile', '-NonInteractive',
                                     '-EncodedCommand', encoded], env=env, cwd=home,
                                    capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertIn('completion matrix passed', result.stdout)
            self.assertEqual(snapshot(), before)


if __name__ == '__main__':
    unittest.main()
