"""Static utility completion and native editor insertion in owned roots."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from public_fixture import copy_public_tree
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
import native_completion
from utility_commands import NAMES, complete, canonical


class UtilityCompletion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-utility-completion-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home ü'
        self.home.mkdir()
        self.repo = self.home / 'repo'
        for name in ('lib/dots', 'bin', 'default'):
            copy_public_tree(ROOT / name, self.repo / name, repo=ROOT, fixture=self.repo,
                             exclude=('__pycache__',))
        (self.repo / 'scripts').mkdir()
        for name in NAMES:
            # None of these executable implementations may run for completion.
            (self.repo / 'scripts' / (name + '.ps1')).write_text("throw 'implementation executed'\n")
            entry = self.repo / 'scripts' / name
            entry.write_text('#!/bin/sh\necho implementation-executed >&2\nexit 97\n', newline='\n')
            entry.chmod(0o755)
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith(('DOTS_', 'BAT_', 'TERMUX')) or key in ('DOTS','TMUX','DISPLAY','WAYLAND_DISPLAY'):
                self.env.pop(key)
        self.env.update(DOTS=str(self.repo), HOME=str(self.home), USERPROFILE=str(self.home),
                        APPDATA=str(self.home / 'Roaming'), LOCALAPPDATA=str(self.home / 'Local'),
                        CODEX_HOME=str(self.home / 'codex'), DOTS_COLOR='always', DOTS_ICONS='always',
                        PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
                        TMP=str(self.home), TEMP=str(self.home))
        for kind in ('CONFIG', 'STATE', 'DATA', 'CACHE'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / kind.lower())

    def test_shared_data_context_and_no_implementation_import(self):
        with patch.dict(os.environ, self.env, clear=True):
            for shell in ('nu', 'xonsh', 'powershell'):
                rows = native_completion.complete(self.repo, shell, ['linked', '--so'])
                self.assertIn('--source', [row['value'] for row in rows])
                self.assertEqual(native_completion.complete(self.repo, shell, ['linked', '--', '--so']), [])
                self.assertEqual(native_completion.complete(self.repo, shell, ['linked', '--format', '--so']), [])
                rows = native_completion.complete(self.repo, shell, ['fzopt', 'color', 'pro'])
                self.assertIn('prompt', [row['value'] for row in rows])
            names = native_completion.command_names()
            for name in NAMES:
                expected = name.casefold() if os.name == 'nt' else name
                self.assertIn(expected, names)
                self.assertIn(expected + '.ps1', names)
            self.assertEqual(canonical('HTTPGET.PS1', windows=True), 'httpGet')
            self.assertEqual(canonical('HTTPGET', windows=False), '')
            self.assertEqual(canonical('httpGet', windows=False), 'httpGet')
        self.assertNotIn('utility_cli', sys.modules)
        self.assertFalse((self.home / 'state').exists())

    def test_protocol_keeps_machine_output_plain(self):
        for typed in (False, True):
            args = ['--display-types'] if typed else []
            result = subprocess.run([sys.executable, '-B', str(self.repo / 'lib/dots/utility_completion.py'),
                *args, 'linked', '--so'], env=self.env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(result.stderr)
            self.assertNotIn('\x1b', result.stdout)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertTrue(rows)
            self.assertTrue(all(len(row) == (4 if typed else 3) for row in rows))
            if typed: self.assertTrue(all(row[-1] == 'option' for row in rows))

    @unittest.skipUnless(os.name == 'nt', 'native Windows PowerShell editor acceptance')
    def test_powershell_real_tab_expansion_preserves_literal_insertion(self):
        requested = os.environ.get('DOTS_TEST_POWERSHELL')
        engines = [shutil.which(requested)] if requested else [
            r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
            r'C:\Program Files\PowerShell\7\pwsh.exe']
        filename = "file space ü's $(Write-Error injected).txt"
        (self.home / filename).write_text('owned')
        (self.repo / 'scripts/completion-functions.ps1').write_text(
            "function global:linked { throw 'function implementation executed' }\n")
        code = r'''
$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'
$env:PATH=$env:TEST_PYTHON_DIR+[IO.Path]::PathSeparator+$env:PATH
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $env:DOTS 'lib/dots/completion/powershell'))))
$rows=@()
foreach($kind in @('ExternalScript','Function')) {
 if($kind -eq 'Function') { . (Join-Path $env:DOTS 'scripts/completion-functions.ps1') }
 $resolved=Get-Command linked -ErrorAction Stop
 if($resolved.CommandType.ToString() -ne $kind) { throw ('unexpected command resolution: '+$resolved.CommandType) }
 $source=if($kind -eq 'Function'){$resolved.ScriptBlock.File}else{$resolved.Path}
 if(-not $source.StartsWith($env:DOTS+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
  throw 'completion fixture resolved a command outside its owned checkout'
 }
 foreach($line in @('linked --so','LINKED.PS1 --so','linked -- ','fzopt color pro','isfile fi')) {
  $global:LASTEXITCODE=37
  $Error.Clear()
  $values=@((TabExpansion2 $line $line.Length).CompletionMatches | ForEach-Object {$_.CompletionText})
  $errorText=if($Error.Count){$Error[0].Exception.Message}else{''}
  $rows+=@{kind=$kind;line=$line;values=$values;lastExit=$global:LASTEXITCODE;error=$errorText}
 }
}
$rows | ConvertTo-Json -Depth 6 -Compress
'''
        for engine in engines:
            self.assertTrue(engine and Path(engine).is_file(), 'required engine unavailable')
            env = dict(self.env, PATH=str(self.repo / 'scripts'), OS='Windows_NT',
                       TEST_PYTHON_DIR=str(Path(sys.executable).parent),
                       PSModulePath=str(Path(engine).parent / 'Modules'),
                       PSModuleAnalysisCachePath=str(self.home / 'module-cache'),
                       POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off')
            result = subprocess.run([engine, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand',
                base64.b64encode(code.encode('utf-16-le')).decode()], env=env, cwd=self.home,
                capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            document = json.loads(result.stdout)
            self.assertEqual({row['kind'] for row in document}, {'ExternalScript','Function'})
            for kind in ('ExternalScript','Function'):
                with self.subTest(engine=engine, resolution=kind):
                    rows = {row['line']:row for row in document if row['kind'] == kind}
                    self.assertIn('--source', rows['linked --so']['values'], result.stdout + result.stderr)
                    self.assertIn('--source', rows['LINKED.PS1 --so']['values'])
                    self.assertNotIn('--source', rows['linked -- ']['values'])
                    self.assertIn('prompt', rows['fzopt color pro']['values'])
                    self.assertIn("'" + filename.replace("'", "''") + "'", rows['isfile fi']['values'])
                    self.assertTrue(all(row['lastExit'] == 37 for row in rows.values()))
            self.assertFalse((self.home / 'injected').exists())

    @unittest.skipIf(os.name == 'nt', 'native POSIX shells required; Windows bash.exe is not a fixture')
    def test_bash_provider_and_registered_completion(self):
        bash = shutil.which('bash')
        if not bash: self.skipTest('Bash unavailable')
        env = dict(self.env, PATH=str(self.repo / 'bin') + os.pathsep + self.env['PATH'])
        for shell in ('bash', 'zsh', 'fish'):
            result = subprocess.run([bash, str(self.repo / 'bin/dots'), '__complete', shell,
                '1', '--', 'linked', '--so'], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('candidate\t--source\t', result.stdout)
        script = r'''
source "$DOTS/lib/dots/completion/bash"
COMP_LINE='linked --so'; COMP_POINT=${#COMP_LINE}
COMP_WORDS=(linked --so); COMP_CWORD=1
_dots_complete_bash
printf '%s\n' "${COMPREPLY[@]}"
'''
        result = subprocess.run([bash, '--noprofile', '--norc', '-c', script], env=env,
                                cwd=self.home, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--source', result.stdout.splitlines())
        self.assertNotIn('implementation-executed', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
