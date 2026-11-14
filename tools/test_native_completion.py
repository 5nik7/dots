#!/usr/bin/env python3
"""Native completion/data-shell boundaries in owned roots; no live providers."""
import json
import base64
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from public_fixture import copy_public_tree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
import native_completion as completion
from shell.runtime import paths
from files.file_platform import config_root, state_root

REQUESTED_ENGINE = os.environ.get('DOTS_TEST_POWERSHELL')
POWERSHELL_ENGINES = [shutil.which(REQUESTED_ENGINE)] if REQUESTED_ENGINE else [
    shutil.which('powershell'),
    str(Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'PowerShell/7/pwsh.exe')]
NUSHELL = shutil.which('nu') or shutil.which('nushell')


class NativeCompletion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-native-completion-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home ü'
        self.home.mkdir()
        self.repo = self.base / 'checkout with spaces'
        for name in ('lib/dots', 'bin', 'themes', 'default'):
            copy_public_tree(ROOT / name, self.repo / name, repo=ROOT, fixture=self.repo,
                             exclude=('__pycache__',))
        self.env = dict(HOME=str(self.home), USERPROFILE=str(self.home), DOTS=str(self.repo),
                        PATH='', APPDATA=str(self.home / 'Roaming'), LOCALAPPDATA=str(self.home / 'Local'),
                        XDG_CONFIG_HOME=str(self.home / 'config'), XDG_STATE_HOME=str(self.home / 'state'),
                        XDG_CACHE_HOME=str(self.home / 'cache'), XDG_DATA_HOME=str(self.home / 'data'),
                        DOTS_COLOR='always', DOTS_ICONS='always', PYTHONDONTWRITEBYTECODE='1')
        for key in ('SystemRoot', 'SYSTEMROOT', 'SystemDrive', 'WINDIR', 'COMSPEC', 'PATHEXT'):
            if key in os.environ:
                self.env[key] = os.environ[key]
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, self.env, clear=True).start()

    def query(self, *words, shell='nu'):
        return completion.complete(self.repo, shell, list(words))

    def test_all_standalones_use_inert_existing_grammar_without_shells(self):
        before = list(self.home.rglob('*'))
        with patch('subprocess.run', side_effect=AssertionError('completion ran a provider')):
            for shell in ('nu', 'xonsh', 'powershell'):
                for name in completion.STANDALONE:
                    with self.subTest(shell=shell, name=name):
                        rows = self.query(name, '--h', shell=shell)
                        self.assertTrue(rows, name)
                        self.assertTrue(all('\x1b' not in row['value'] for row in rows))
                        self.assertEqual(rows, self.query(str(self.repo/'bin'/(name+'.ps1')), '--h', shell=shell))
        self.assertEqual(list(self.home.rglob('*')), before)

    def test_native_bridge_runs_with_python_only_path(self):
        result = subprocess.run([sys.executable, '-B', str(self.repo/'lib/dots/native_completion.py'),
                                 '--complete', 'nu', 'pkgs.ps1', '--h'],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--help', [row['value'] for row in json.loads(result.stdout)])

    def test_unknown_commands_decline_and_clipboard_never_accesses_provider(self):
        with patch('clipboard._provider', side_effect=AssertionError('clipboard accessed')):
            self.assertIsNone(self.query('foreign', ''))
            self.assertEqual(self.query('cpy', '--', '-'), [])
            self.assertEqual({r['value'] for r in self.query('pst', '')}, {'-h', '--help'})

    def test_windows_command_identity_preserves_case_sensitive_operands(self):
        with patch.object(completion, 'os', SimpleNamespace(name='nt')):
            for name in ('CPY', 'PKGS.PS1', 'C:\\Owned Path\\DOTS.PS1'):
                original = self.query(name, '--h')
                self.assertEqual(original, self.query(name.lower(), '--h'))
                self.assertTrue(original)
                self.assertEqual(self.query(name, '--H'), [])
        with patch.object(completion, 'os', SimpleNamespace(name='posix')):
            self.assertIsNone(self.query('CPY', '--h'))

    def test_data_shell_python_boundaries_without_optional_runtimes(self):
        nu = (self.repo/'lib/dots/shell/init.nu').read_text(encoding='utf-8')
        selection = nu.split('let dots_python = ', 1)[1].split('$env._DOTS_PYTHON =', 1)[0]
        self.assertIn('which --all python3 python', selection)
        self.assertIn("$nu.os-info.name == 'windows'", selection)
        self.assertIn("$path !~ '/windowsapps/'", selection)
        self.assertIn("str ends-with '.exe'", selection)
        boundary = nu.split('def --wrapped _dots-python ', 1)[1].split('do --env {', 1)[0]
        self.assertIn("with-env {PYTHON_MANAGER_AUTOMATIC_INSTALL: 'false'}", boundary)
        self.assertIn('hide-env --ignore-errors PYLAUNCHER_ALLOW_INSTALL PYLAUNCHER_ALWAYS_INSTALL', boundary)
        self.assertNotIn('PYLAUNCHER_ALLOW_INSTALL:', boundary)
        self.assertNotIn('PYLAUNCHER_ALWAYS_INSTALL:', boundary)
        self.assertLess(boundary.index('hide-env --ignore-errors'), boundary.index('^($env._DOTS_PYTHON)'))
        self.assertEqual(nu.count('^($env._DOTS_PYTHON)'), 1)
        nu_guard = nu.split('let basename = ($spans.0 | path basename)', 1)[1].split('if $env.dots_options.DOTS_INIT_COMPLETION', 1)[0]
        self.assertIn("if $nu.os-info.name == 'windows' { $basename | str lowercase } else { $basename }", nu_guard)
        self.assertIn("$identity | str replace --regex '\\.ps1$' ''", nu_guard)
        self.assertIn('--complete nu ...$spans', nu)
        xonsh = (self.repo/'lib/dots/shell/init.xsh').read_text(encoding='utf-8')
        self.assertIn('_dots_sys.executable', xonsh)
        self.assertNotIn("which('python", xonsh)
        xonsh_guard = xonsh.split('command = _DotsPath(context.command).name', 1)[1].split('if command not in', 1)[0]
        self.assertIn("if __import__('os').name == 'nt':", xonsh_guard)
        self.assertLess(xonsh_guard.index('command.casefold()'), xonsh_guard.index("command.removesuffix('.ps1')"))
        self.assertIn('words = [arg.value for arg in context.args[:context.arg_index]] + [context.prefix]', xonsh)

    @unittest.skipUnless(NUSHELL, 'native Nu acquisition-boundary acceptance pending')
    def test_nu_child_hides_launcher_flags_and_preserves_caller_environment(self):
        nu = (self.repo/'lib/dots/shell/init.nu').read_text(encoding='utf-8')
        boundary = 'def --wrapped _dots-python ' + nu.split('def --wrapped _dots-python ', 1)[1].split('do --env {', 1)[0]
        child = self.base/'inspect_child.py'
        names = ['PYTHON_MANAGER_AUTOMATIC_INSTALL','PYLAUNCHER_ALLOW_INSTALL','PYLAUNCHER_ALWAYS_INSTALL']
        child.write_text('import json,os\nprint(json.dumps({name: os.environ.get(name) for name in '+repr(names)+'}))\n', encoding='utf-8')
        script = self.base/'guard.nu'
        script.write_text(boundary + '''
$env._DOTS_PYTHON = $env.TEST_PYTHON
$env.PYTHON_MANAGER_AUTOMATIC_INSTALL = 'caller'
$env.PYLAUNCHER_ALLOW_INSTALL = 'caller'
$env.PYLAUNCHER_ALWAYS_INSTALL = 'caller'
let child = (_dots-python $env.TEST_CHILD)
{child: ($child.stdout | from json), caller: [$env.PYTHON_MANAGER_AUTOMATIC_INSTALL $env.PYLAUNCHER_ALLOW_INSTALL $env.PYLAUNCHER_ALWAYS_INSTALL]} | to json --raw
''', encoding='utf-8')
        result = subprocess.run([NUSHELL,'--no-config-file',str(script)], cwd=self.home,
                                env=dict(self.env, TEST_PYTHON=sys.executable, TEST_CHILD=str(child)),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['child'], {names[0]:'false', names[1]:None, names[2]:None})
        self.assertEqual(data['caller'], ['caller'] * 3)

    def test_native_paths_use_supplied_environment_and_no_creation(self):
        env = {k:v for k,v in self.env.items() if k not in ('HOME','XDG_CONFIG_HOME','XDG_STATE_HOME')}
        result = paths(self.repo, env)
        self.assertEqual(result['config'], str(config_root(env)/'dots/config.env'))
        self.assertEqual(result['state'], str(state_root(env)))
        expected = self.home/'Local/dots' if os.name == 'nt' else self.home/'.local/state/dots'
        self.assertEqual(Path(result['state']), expected)
        self.assertTrue(result['theme_command'].endswith('theme.ps1' if os.name == 'nt' else 'theme'))
        self.assertEqual(list(self.home.iterdir()), [])

    def test_file_candidates_preserve_literal_paths_and_filter_controls(self):
        folder = self.home / 'folder space ü'
        folder.mkdir()
        name = "literal $(touch nope) '雪.txt"
        (folder/name).write_text('fixture')
        rows = completion.path_candidates('file', '--output=', '--output='+str(folder)+os.sep+'literal')
        self.assertEqual(rows, [dict(value='--output='+str(folder/name), description='File')])
        self.assertEqual(completion.path_candidates('directory', '', str(folder)+os.sep+'literal'), [])
        self.assertFalse((self.home/'nope').exists())

    def test_generated_alias_map_is_validated_and_removed_alias_declines(self):
        folder = state_root()/'themes/commands/current'
        folder.mkdir(parents=True)
        mapping = folder/'map.tsv'
        mapping.write_text('palette\tcatppuccin\nmalicious$(touch nope)\tcatppuccin\n')
        self.assertEqual(completion.theme_aliases(state_root()), {'palette':'catppuccin'})
        self.assertEqual(self.query('palette', '--h'), self.query('dots', 'theme', 'catppuccin', '--h'))
        mapping.write_text('')
        self.assertIsNone(self.query('palette', ''))

    @unittest.skipUnless(os.name == 'nt', 'actual native Windows PowerShell acceptance')
    def test_powershell_tab_expansion_clipboard_weather_and_literal_context(self):
        cases = ['wttr --h', 'wttr.ps1 --h', 'cpy --h', 'cpy.ps1 --h', 'pst --h', 'pst.ps1 --h', 'CPY.PS1 --h',
                 'cpy ', "cpy '' ", 'cpy -- ', 'pst -- ',
                 'cpy $(Set-Content -LiteralPath injected -Value bad) --h']
        cases.append("& '" + str(self.repo/'bin/cpy.ps1').replace("'", "''") + "' --h")
        code = r'''
$ErrorActionPreference = 'Stop'
$completion = Join-Path $env:DOTS 'lib/dots/completion/powershell'
# Loading registrations must work with no Python command available.
$env:PATH = Join-Path $env:DOTS 'bin'
. ([scriptblock]::Create([IO.File]::ReadAllText($completion)))
. ([scriptblock]::Create([IO.File]::ReadAllText($completion)))
$env:PATH += [IO.Path]::PathSeparator + $env:TEST_PYTHON_DIR
$global:LASTEXITCODE = 23
$rows = @()
foreach ($line in (ConvertFrom-Json $env:TEST_COMPLETION_LINES)) {
    $matches = @((TabExpansion2 $line $line.Length).CompletionMatches | ForEach-Object { $_.CompletionText })
    $rows += @{ line = $line; values = $matches; lastExit = $global:LASTEXITCODE }
}
# Completion registered after Dots must survive a Dots reload.
Register-ArgumentCompleter -Native -CommandName pst -ScriptBlock { 'later-provider' }
. ([scriptblock]::Create([IO.File]::ReadAllText($completion)))
$line = 'pst --h'
$later = @((TabExpansion2 $line $line.Length).CompletionMatches | ForEach-Object { $_.CompletionText })
@{ rows = $rows; later = $later; injected = (Test-Path -LiteralPath injected) } | ConvertTo-Json -Depth 8 -Compress
'''
        for engine in POWERSHELL_ENGINES:
            with self.subTest(engine=engine):
                self.assertTrue(engine and Path(engine).is_file(), 'required native engine unavailable')
                env = dict(self.env, PATH=str(self.repo/'bin'), OS='Windows_NT',
                           TEST_PYTHON_DIR=str(Path(sys.executable).parent),
                           TEST_COMPLETION_LINES=json.dumps(cases),
                           PSModuleAnalysisCachePath=str(self.base/'module-cache'),
                           PSModulePath=str(Path(engine).parent/'Modules'),
                           POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off',
                           TEMP=str(self.base), TMP=str(self.base), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
                result = subprocess.run([engine,'-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',
                                         base64.b64encode(code.encode('utf-16-le')).decode()],
                                        cwd=self.home, env=env, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                for row in data['rows']:
                    if row['line'] in ('cpy -- ', 'pst -- '):
                        self.assertNotIn('--help', row['values'])
                    else: self.assertIn('--help', row['values'], data)
                    self.assertEqual(row['lastExit'], 23)
                self.assertEqual(data['later'], ['later-provider'])
                self.assertFalse(data['injected'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
