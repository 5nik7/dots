"""Portable native PowerShell acceptance; no Bash or live profile is used."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PWSH = shutil.which(os.environ.get('DOTS_TEST_POWERSHELL') or 'pwsh')
if os.environ.get('DOTS_TEST_POWERSHELL') and not PWSH:
    raise SystemExit('required PowerShell engine unavailable: ' + os.environ['DOTS_TEST_POWERSHELL'])


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
                     'shells/powershell/Microsoft.PowerShell_profile.ps1',
                     'shells/powershell/profile.ps1', 'shells/powershell/helpers.ps1',
                     'shells/powershell/optional.ps1', 'shells/powershell/coreutils.ps1',
                     'shells/shared/starship-default.ps1', 'scripts/pdiff.ps1',
                     'shells/powershell/Scripts/Invoke-Wh.ps1'):
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, self.repo / name)
        shutil.copytree(REPO / 'lib/dots', self.repo / 'lib/dots',
                        ignore=shutil.ignore_patterns('__pycache__'))
        # Use real profile generation with inert owned preferences. The fixed
        # editor avoids unrelated discovery in the prompt/optional-tool mocks.
        for platform in ('windows', 'linux', 'wsl'):
            folder = self.repo / 'profiles' / platform
            folder.mkdir(parents=True)
            (folder / 'profile.json').write_text(json.dumps(dict(
                schema=1, id=platform, environment=dict(EDITOR='vi'))))
        # Warm-start PATH deliberately contains no Python, Bash or other tools.
        self.env = {'HOME': str(self.home), 'USERPROFILE': str(self.home),
                    'DOTS': str(self.repo), 'PATH': str(self.repo / 'bin'),
                    'PSModulePath': str(self.home / 'modules'),
                    'APPDATA': str(self.home / 'appdata'),
                    'LOCALAPPDATA': str(self.home / 'localappdata'),
                    'TMPDIR': str(self.root), 'TEMP': str(self.root), 'TMP': str(self.root),
                    'XDG_CONFIG_HOME': str(self.home / 'config'),
                    'XDG_DATA_HOME': str(self.home / 'data'),
                    'XDG_STATE_HOME': str(self.home / 'state'),
                    'XDG_CACHE_HOME': str(self.home / 'cache')}
        for key in ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'LD_PRELOAD', 'OS'):
            if key in os.environ:
                self.env[key] = os.environ[key]
        # Keep native application paths inside existing fixture directories.
        for key in ('APPDATA', 'LOCALAPPDATA'):
            Path(self.env[key]).mkdir(parents=True, exist_ok=True)
        self.env.update(CODEX_HOME=str(self.home / 'codex'),
                        PSModuleAnalysisCachePath=str(self.root / 'ModuleAnalysisCache'),
                        POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off',
                        PYTHONUTF8='1', PYTHONIOENCODING='utf-8')

    def prepare_environment(self):
        cache = self.home / 'cache/dots/startup/environment.ps1'
        result = subprocess.run([sys.executable, '-B',
                                 str(self.repo / 'lib/dots/native_startup.py'),
                                 'powershell', str(cache)],
                                env=dict(self.env, DOTS=str(self.repo)),
                                cwd=self.home, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return cache

    def run_ps(self, *args, prepare=True):
        if prepare:
            self.prepare_environment()
        return subprocess.run([PWSH, '-NoProfile', '-NonInteractive', *args],
                              cwd=self.home, env=self.env, text=True,
                              capture_output=True, timeout=30)

    def test_native_files_parse(self):
        files = ','.join(literal(file) for file in self.repo.rglob('*.ps1'))
        code = ('foreach ($file in @(' + files + ')) { '
                '$tokens = $null; $errors = $null; '
                '[void][System.Management.Automation.Language.Parser]::ParseFile('
                '$file, [ref]$tokens, [ref]$errors); '
                'if ($errors.Count) { Write-Error ($file + ": " + ($errors | Out-String)); exit 1 } }')
        p = self.run_ps('-Command', code)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_cold_environment_preparation_and_warm_cache(self):
        cache = self.home / 'cache/dots/startup/environment.ps1'
        self.assertFalse(cache.exists())
        self.env['PATH'] = str(Path(sys.executable).parent)
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        cold = self.run_ps('-Command', f'. {entry}; $env:DOTS_PROFILE', prepare=False)
        self.assertEqual(cold.returncode, 0, cold.stderr)
        self.assertEqual(cold.stderr, '')
        if os.name == 'nt':
            self.assertEqual(cold.stdout.strip(), 'windows')
        else:
            self.assertIn(cold.stdout.strip(), ('linux', 'wsl'))
        self.assertTrue(cache.is_file())
        before = cache.read_bytes()
        self.assertTrue(before.startswith(b'\xef\xbb\xbf'))
        metadata = json.loads(cache.with_suffix('.ps1.json').read_text())
        self.assertEqual(metadata['digest'], hashlib.sha256(before).hexdigest())
        self.env['PATH'] = str(self.repo / 'bin')
        warm = self.run_ps('-Command',
                           "function Get-Command { throw 'warm environment discovered a tool' }; "
                           f'. {entry}; $env:DOTS_PROFILE', prepare=False)
        self.assertEqual(warm.returncode, 0, warm.stderr)
        self.assertEqual(warm.stderr, '')
        self.assertEqual(warm.stdout, cold.stdout)
        self.assertEqual(cache.read_bytes(), before)

    def python_guard_environment(self):
        aliases = self.root / 'Microsoft/WindowsApps'
        aliases.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            # Discovery must reject this unexecutable app-execution alias even
            # though it precedes an installed native interpreter on PATH.
            (aliases / 'python3.exe').write_bytes(b'fixture must never execute')
        self.env['PATH'] = os.pathsep.join((str(aliases), str(Path(sys.executable).parent)))
        self.env.update(PYTHON_MANAGER_AUTOMATIC_INSTALL='true', PYLAUNCHER_ALLOW_INSTALL='1',
                        PYLAUNCHER_ALWAYS_INSTALL='1')
        return ("function python3 { throw 'python3 function invoked' }; "
                "function python { throw 'python function invoked' }; ")

    def test_cold_python_discovery_bypasses_aliases_and_restores_acquisition_flags(self):
        shadow = self.python_guard_environment()
        startup = self.repo / 'lib/dots/native_startup.py'
        original = startup.read_text()
        marker = self.home / 'python-guard.json'
        probe = ("import json, os\nfrom pathlib import Path\n"
                 "Path(os.environ['HOME'], 'python-guard.json').write_text(json.dumps("
                 "[os.environ.get('PYTHON_MANAGER_AUTOMATIC_INSTALL'), "
                 "os.environ.get('PYLAUNCHER_ALLOW_INSTALL'), os.environ.get('PYLAUNCHER_ALWAYS_INSTALL')]))\n")
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        for failed in (False, True):
            with self.subTest(failed=failed):
                startup.write_text(probe + ('raise SystemExit(7)\n' if failed else original))
                (self.home / 'cache/dots/startup/environment.ps1').unlink(missing_ok=True)
                p = self.run_ps('-Command', shadow + "$WarningPreference='SilentlyContinue'; "
                    f'. {entry}; ' +
                    "@{manager=$env:PYTHON_MANAGER_AUTOMATIC_INSTALL; "
                    "launcher=$env:PYLAUNCHER_ALLOW_INSTALL; always=$env:PYLAUNCHER_ALWAYS_INSTALL} | ConvertTo-Json -Compress", prepare=False)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(json.loads(marker.read_text()), ['false', None, None])
                self.assertEqual(json.loads(p.stdout), {'manager': 'true', 'launcher': '1', 'always': '1'})

    def test_native_python_call_boundaries_disable_acquisition_and_restore_preferences(self):
        shadow = self.python_guard_environment()
        probe = ("import json, os, sys\n"
                 "print(json.dumps([os.environ.get('PYTHON_MANAGER_AUTOMATIC_INSTALL'), "
                 "os.environ.get('PYLAUNCHER_ALLOW_INSTALL'), os.environ.get('PYLAUNCHER_ALWAYS_INSTALL')]))\nsys.exit(9)\n")
        (self.repo / 'lib/dots/native.py').write_text(probe)
        (self.repo / 'lib/dots/cli.py').write_text(probe)
        (self.repo / 'lib/dots/clipboard.py').write_text('import sys\nsys.stdin.read()\n' + probe)
        (self.repo / 'lib/dots/profile_config.py').write_text(
            "import os\nprint('__help.tagline\\t' + os.environ.get('PYTHON_MANAGER_AUTOMATIC_INSTALL', '') "
            "+ '|' + os.environ.get('PYLAUNCHER_ALLOW_INSTALL', '') + '|' + os.environ.get('PYLAUNCHER_ALWAYS_INSTALL', ''))\n")
        code = shadow + f'''
. {literal(self.repo / 'lib/dots/files/entry.ps1')}
$entry=Invoke-DotsFiles $env:DOTS cli @() @{{}} {literal(sys.executable)}; $entryCode=$script:DotsFilesExitCode
. {literal(self.repo / 'lib/dots/help-style.ps1')}
$help=Get-DotsHelpPreferences $env:DOTS
. {literal(self.repo / 'lib/dots/shell/keys.ps1')}
$keys=dots keys; $keysCode=$LASTEXITCODE
. {literal(self.repo / 'lib/dots/clipboard.ps1')}
$clipboard=Invoke-DotsClipboard $env:DOTS cpy @() @('owned input') $true; $clipboardCode=$LASTEXITCODE
@{{entry=$entry; entryCode=$entryCode; help=$help.tagline; keys=$keys; keysCode=$keysCode;
 clipboard=$clipboard; clipboardCode=$clipboardCode; manager=$env:PYTHON_MANAGER_AUTOMATIC_INSTALL;
 launcher=$env:PYLAUNCHER_ALLOW_INSTALL; always=$env:PYLAUNCHER_ALWAYS_INSTALL}} | ConvertTo-Json -Compress
'''
        p = self.run_ps('-Command', code, prepare=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        for key in ('entry', 'keys', 'clipboard'):
            self.assertIsInstance(result[key], str, (key, result[key]))
            self.assertEqual(json.loads(result[key]), ['false', None, None], key)
            self.assertEqual(result[key + 'Code'], 9, key)
        self.assertEqual(result['help'], 'false||')
        self.assertEqual(result['manager'], 'true')
        self.assertEqual(result['launcher'], '1')
        self.assertEqual(result['always'], '1')

    def test_help_preferences_fail_without_hiding_basic_help(self):
        shadow = self.python_guard_environment()
        (self.repo / 'lib/dots/profile_config.py').write_text(
            "import sys\nprint('fixture runtime unavailable', file=sys.stderr)\nraise SystemExit(7)\n")
        adapter = literal(self.repo / 'lib/dots/help-style.ps1')
        p = self.run_ps('-Command', shadow + f'. {adapter}; ' +
            "$preferences=Get-DotsHelpPreferences $env:DOTS; "
            "@{tagline=$preferences.tagline; manager=$env:PYTHON_MANAGER_AUTOMATIC_INSTALL; "
            "launcher=$env:PYLAUNCHER_ALLOW_INSTALL; always=$env:PYLAUNCHER_ALWAYS_INSTALL} | ConvertTo-Json -Compress", prepare=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        self.assertEqual(json.loads(p.stdout), {'tagline': 'Manage your dotfiles and more...',
                                              'manager': 'true', 'launcher': '1', 'always': '1'})
        p = self.run_ps('-File', str(self.repo / 'bin/dots.ps1'), '--help', prepare=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        self.assertIn('Manage your dotfiles and more...', p.stdout)

    def test_bootstrap_warm_avoids_discovery_and_cold_disables_acquisition(self):
        shadow = self.python_guard_environment()
        # Replace the embedded bootstrap payload with an inert owned probe. It
        # fails before checkout preparation and cannot install/fetch anything.
        (self.repo / 'lib/dots/bootstrap.py').write_text(
            "import json, os\nfrom pathlib import Path\n"
            "Path(os.environ['HOME'], 'bootstrap-guard.json').write_text(json.dumps("
            "[os.environ.get('PYTHON_MANAGER_AUTOMATIC_INSTALL'), "
            "os.environ.get('PYLAUNCHER_ALLOW_INSTALL'), os.environ.get('PYLAUNCHER_ALWAYS_INSTALL')]))\nraise SystemExit(7)\n")
        generated = subprocess.run([sys.executable, '-B',
            str(self.repo / 'lib/dots/bootstrap_snippet.py'), 'powershell'],
            env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(generated.returncode, 0, generated.stderr)
        (self.repo / 'shells/powershell/profile.ps1').write_text('$global:bootstrapLoaded=$true\n')
        self.env['DOTS_BOOTSTRAP_DIR'] = str(self.repo)
        warm = self.run_ps('-Command', "function Get-Command { throw 'warm bootstrap probed Python' }; "
            + generated.stdout + '\n$global:bootstrapLoaded', prepare=False)
        self.assertEqual(warm.returncode, 0, warm.stderr)
        self.assertEqual(warm.stdout.strip(), 'True')
        self.assertFalse((self.home / 'bootstrap-guard.json').exists())
        self.env['DOTS_BOOTSTRAP_DIR'] = str(self.root / 'missing checkout')
        cold = self.run_ps('-Command', shadow + generated.stdout +
            '\n@{manager=$env:PYTHON_MANAGER_AUTOMATIC_INSTALL; launcher=$env:PYLAUNCHER_ALLOW_INSTALL; always=$env:PYLAUNCHER_ALWAYS_INSTALL} | ConvertTo-Json -Compress',
            prepare=False)
        self.assertEqual(cold.returncode, 0, cold.stderr)
        self.assertEqual(json.loads((self.home / 'bootstrap-guard.json').read_text()), ['false', None, None])
        self.assertEqual(json.loads(cold.stdout), {'manager': 'true', 'launcher': '1', 'always': '1'})
        self.assertFalse((self.root / 'missing checkout').exists())

    def test_help_styles_and_undecorated_hook(self):
        adapter = str(self.repo / 'bin/dots.ps1')
        rich = self.run_ps('-File', adapter, '--color=always', '--icons=never', '--help')
        self.assertEqual(rich.returncode, 0, rich.stderr)
        self.assertIn('Manage your dotfiles and more...', rich.stdout)
        self.assertIn('\x1b', rich.stdout)
        plain = self.run_ps('-File', adapter, '--color=never', '--icons=never', '--help')
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertNotIn('\x1b', plain.stdout + plain.stderr)
        original = self.run_ps('-File', adapter, 'init', 'powershell')
        forced = self.run_ps('-File', adapter, '--color=always', '--icons=always', 'init', 'powershell')
        self.assertEqual(forced.returncode, 0, forced.stderr)
        self.assertEqual(forced.stdout, original.stdout)
        self.assertNotIn('\x1b', forced.stdout)

    def test_theme_shortcut_completion_mapping_and_retirement(self):
        registry = self.home/'state/dots/themes/commands/current'
        registry.mkdir(parents=True)
        (registry/'names').write_text('fixturepalette-theme\n')
        (registry/'map.tsv').write_text('fixturepalette-theme\tfixturepalette\n')
        (self.repo/'bin/dots.ps1').write_text("$args | ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $env:HOME 'completion.json')\n\"candidate`tblue`tBlue\"\n")
        code = r'''
$adapter = Join-Path $env:DOTS 'lib/dots/completion/powershell'
. ([scriptblock]::Create([IO.File]::ReadAllText($adapter)))
$line = 'fixturepalette-theme.ps1 bl'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput($line, [ref]$tokens, [ref]$errors)
$commandAst = $ast.EndBlock.Statements[0].PipelineElements[0]
$global:LASTEXITCODE = 17
$rows = @(& $dotsCompleter 'bl' $commandAst $line.Length)
if ($rows.Count -ne 1 -or $rows[0].CompletionText -ne 'blue' -or $global:LASTEXITCODE -ne 17) { exit 11 }
$forwarded = Get-Content -Raw -LiteralPath (Join-Path $env:HOME 'completion.json') | ConvertFrom-Json
if (($forwarded -join '|') -ne '__complete|theme|fixturepalette|bl') { exit 12 }
$registry = Join-Path $env:XDG_STATE_HOME 'dots/themes/commands/current'
[IO.File]::WriteAllText((Join-Path $registry 'map.tsv'), '')
[IO.File]::WriteAllText((Join-Path $registry 'names'), '')
. ([scriptblock]::Create([IO.File]::ReadAllText($adapter)))
if (@(& $dotsCompleter 'bl' $commandAst $line.Length).Count -ne 0) { exit 13 }
if ($dotsNewCompletionNames.Count -ne 0) { exit 14 }
# Old generations without maps use exact identity names, including -theme.
Remove-Item -LiteralPath (Join-Path $registry 'map.tsv')
[IO.File]::WriteAllText((Join-Path $registry 'names'), "fixturepalette-theme`n")
. ([scriptblock]::Create([IO.File]::ReadAllText($adapter)))
$null = @(& $dotsCompleter 'bl' $commandAst $line.Length)
$forwarded = Get-Content -Raw -LiteralPath (Join-Path $env:HOME 'completion.json') | ConvertFrom-Json
if (($forwarded -join '|') -ne '__complete|theme|fixturepalette-theme|bl') { exit 15 }
'''
        result = self.run_ps('-Command', code)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
        self.assertLess(entries.index(str(self.repo / 'bin')), entries.index(str(self.repo / 'scripts')))

    def test_missing_loader_emits_no_code(self):
        adapter = str(self.repo / 'bin/dots.ps1')
        # A missing selected loader must fail before emitting generated code.
        (self.repo / 'lib/dots/shell/init.ps1').unlink()
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
        self.repo = moved
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

    def run_interactive(self, code):
        self.prepare_environment()
        # -NoExit exercises the interactive loader; explicit exit avoids a REPL.
        # Redirected input keeps PSReadLine out of these deterministic checks.
        return subprocess.run([PWSH, '-NoProfile', '-NoLogo', '-NoExit', '-Command',
            "$PROFILE.CurrentUserAllHosts=" + literal(self.home / "Documents" / "profile.ps1") + "; " +
            "$ErrorActionPreference='Stop'; try { " + code +
            " } catch { [Console]::Error.WriteLine($_); exit 1 }; exit 0"],
            cwd=self.home, env=self.env, input='', text=True,
            capture_output=True, timeout=30)

    def test_escape_variable_case_alias_and_readonly_reload(self):
        self.env.update(DOTS=str(self.repo), DOTS_INIT_THEME='0', DOTS_INIT_COLORS='0',
                        DOTS_INIT_COMMANDS='0', DOTS_INIT_COMPLETION='0')
        entry = literal(self.repo / 'lib/dots/shell/init.ps1')
        # The generated owned cache supplies settings without Python on PATH.
        p = self.run_interactive(
            f". {entry}; [Console]::Write($esc + '|' + $ESC + '|'); "
            "Set-Variable -Name esc -Scope Global -Option ReadOnly; "
            f". {entry}; [Console]::Write($esc + '|' + $ESC + '|')")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.encode(), b'\x1b|' * 4)

    def test_lean_startup_and_repeat_preserve_prompt_exit_and_paths(self):
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        p = self.run_interactive(
            "function Get-Command { param($Name, $CommandType, $ErrorAction); "
            "if ($Name -ne 'starship') { throw 'unexpected startup discovery' } }; "
            "function Get-Module { throw 'startup module discovery' }; "
            "function Import-Module { throw 'startup optional import' }; "
            f". {entry}; $first=$env:PATH; $wrapper=(Get-Item Function:prompt).ScriptBlock.ToString(); "
            f". {entry}; $global:LASTEXITCODE=37; $text=prompt; "
            "@{text=$text; code=$LASTEXITCODE; samePath=($first -eq $env:PATH); "
            "samePrompt=($wrapper -eq (Get-Item Function:prompt).ScriptBlock.ToString()); "
            "wrapped=($wrapper -match 'Update-DotsTheme'); "
            "ready=$global:_DotsLeanPowerShellReady; alias=(Get-Alias ls).Definition} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        result = json.loads(p.stdout)
        self.assertEqual(result['code'], 37)
        self.assertEqual(result['text'], '[' + str(self.home) + '] $ ')
        for key in ('samePath', 'samePrompt', 'wrapped', 'ready'):
            self.assertTrue(result[key], key)
        self.assertEqual(result['alias'], 'Invoke-eza')

    def test_noninteractive_profile_does_not_load_helpers(self):
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        p = self.run_ps('-Command', f'. {entry}; '
                        "if (Test-Path Function:Invoke-DotsFuzzyCompletion) { exit 1 }; $env:DOTS")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        self.assertEqual(p.stdout.strip(), str(self.repo))

    def test_blastoff_path_default_and_explicit_override(self):
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        for override in (None, str(self.home / 'my blastoff')):
            if override:
                self.env['BLASTOFF_HOME'] = override
            p = self.run_ps('-Command', f'. {entry}; $env:BLASTOFF_HOME')
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout.strip(), override or str(self.repo / 'config/blastoff'))

    def test_core_only_features_refuse_desktop_before_import(self):
        optional = literal(self.repo / 'shells/powershell/optional.ps1')
        p = self.run_ps('-Command',
            "if ($PSEdition -eq 'Core') { exit 0 }; "
            "function Import-Module { throw 'IMPORT MUST NOT RUN' }; "
            f"foreach ($feature in 'command-not-found') {{ try {{ . {optional} $feature; exit 1 }} "
            "catch { if ($_.Exception.Message -notlike '*requires PowerShell Core*') { exit 2 } } }; exit 0")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_optional_blastoff_uses_bundled_launcher_without_module_import(self):
        optional = literal(self.repo / 'shells/powershell/optional.ps1')
        launcher = self.repo / 'bin/blastoff.ps1'
        launcher.parent.mkdir(exist_ok=True)
        launcher.write_text("$args | ConvertTo-Json -Compress; exit 23\n")
        p = self.run_ps('-Command',
            "function Import-Module { throw 'IMPORT MUST NOT RUN' }; "
            f". {optional} blastoff; blastoff 'two words' ''; if ($LASTEXITCODE -ne 23) {{ exit 1 }}; exit 0")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), ['two words', ''])

    def test_automatic_starship_failure_keeps_plain_prompt(self):
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        p = self.run_interactive(
            "function Get-Command { { $global:LASTEXITCODE=1; 'throw \"must not evaluate\"' } }; "
            f". {entry}; $text=prompt; if ($text -ne ('['+$PWD.Path+'] $ ')) {{ throw 'lost fallback' }}")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('Initialization failed: starship', p.stdout)

    @unittest.skipUnless(os.name == 'nt', 'Windows executable PATH precedence')
    def test_automatic_starship_uses_first_path_match(self):
        folders = [self.root / 'first tools', self.root / 'second tools']
        for folder, label in zip(folders, ('first', 'second')):
            folder.mkdir()
            (folder / 'starship.cmd').write_text(
                '@echo off\necho function global:prompt { "' + label +
                '> " }\nexit /b 0\n')
        self.env['PATH'] = os.pathsep.join(map(str, folders))
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        p = self.run_interactive(
            "$matches=@(Get-Command starship -CommandType Application); "
            f". {entry}; . {entry}; "
            "@{matches=$matches.Count; text=(prompt); "
            "loaded=[bool]$global:_DotsOptionalFeatures['starship']} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        self.assertNotIn('WARNING:', p.stdout)
        self.assertEqual(json.loads(p.stdout),
                         {'matches': 2, 'text': 'first> ', 'loaded': True})

    def test_integration_profile_selection_and_repeated_chain(self):
        # The optional environment path supplies an inspected vendor file for
        # native acceptance; ordinary CI uses a small deterministic wrapper.
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        shared = literal(self.repo / 'lib/dots/shell/init.ps1')
        documents = self.home / 'Documents'
        for folder in ('PowerShell', 'WindowsPowerShell'):
            (documents / folder).mkdir(parents=True)
            target = documents / folder / 'shell-integration_v7.ps1'
            vendor = os.environ.get('DOTS_TEST_TERMINAL_INTEGRATION')
            if vendor:
                shutil.copy2(vendor, target)
            else:
                target.write_text("""if (-not $global:__ShellInteg_Installed) {
  $global:__ShellInteg_Installed=$true
  $global:__ShellInteg_OriginalPrompt=$function:prompt
  function global:prompt { 'mark<' + (& $global:__ShellInteg_OriginalPrompt) + '>mark' }
  $global:__ShellInteg_Wrapper=$function:prompt
}
function global:__ShellInteg_Rearm {
  if ($function:prompt -ne $global:__ShellInteg_Wrapper) {
    $global:__ShellInteg_OriginalPrompt=$function:prompt
    Set-Item Function:\\global:prompt $global:__ShellInteg_Wrapper
  }
}
__ShellInteg_Rearm
""", encoding='utf-8-sig')
            with target.open('a', encoding='utf-8') as stream:
                stream.write(f"\n$global:loadedIntegration='{folder}'\n")
        code = ("$folder=if ($PSEdition -eq 'Core') {'PowerShell'} else {'WindowsPowerShell'}; "
            "$PROFILE.CurrentUserAllHosts=Join-Path " + literal(documents) + " ($folder+'/profile.ps1'); "
            "function Get-Command { { $global:generations++; $global:LASTEXITCODE=0; "
            "'function global:prompt { \"fixture-starship> \" }' } }; "
            f". {entry}; $wrapper=$function:prompt; . {entry}; . {shared}; "
            ". (Join-Path (Split-Path $PROFILE.CurrentUserAllHosts) 'shell-integration_v7.ps1'); "
            "$global:LASTEXITCODE=23; $text=prompt; "
            "@{text=$text; code=$LASTEXITCODE; same=($function:prompt -eq $wrapper); "
            "generations=$global:generations; expected=$folder; actual=$global:loadedIntegration; "
            "wrapped=($global:__ShellInteg_OriginalPrompt -eq $global:_DotsPromptWrapper)} | ConvertTo-Json -Compress")
        p = self.run_interactive(code)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        result = json.loads(p.stdout)
        self.assertEqual(result['text'].count('fixture-starship> '), 1)
        self.assertEqual(result['generations'], 1)
        self.assertEqual(result['code'], 23)
        self.assertEqual(result['expected'], result['actual'])
        self.assertTrue(result['same'])
        self.assertTrue(result['wrapped'])

    def test_prompt_preserves_failure_signal_for_renderer(self):
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        p = self.run_interactive(f'. {entry}; '
            "Install-DotsPrompt -Renderer { if ($?) {'good'} else {'failed'} }; "
            "Get-Variable '__fixture_missing__' -ErrorAction Ignore; prompt")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), 'failed')

    def test_prompt_refreshes_published_theme_and_keeps_last_good_snapshot(self):
        themes = self.home / 'state/dots/themes'
        for generation, theme, color in [('g.A', 'first', '#112233'), ('g.B', 'second', '#445566')]:
            folder = themes / 'generations' / generation
            folder.mkdir(parents=True)
            (folder / 'shell.tsv').write_text(
                f'@theme\tid\t{theme}\n@theme\tfamily\t{theme}\n'
                f'@theme\tflavor\tdark\nblue\thex\t{color}\n'
                'foreground\thex\t#eeeeee\nbackground\thex\t#111111\n')
            (folder / 'ls_colors').write_text('di=34')
        current = themes / 'current'
        current.write_text('g.A')
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        p = self.run_interactive(f'. {entry}; $first=$env:DOTS_THEME_ID; '
            f"[IO.File]::WriteAllText({literal(current)}, 'invalid'); $null=prompt; "
            "$retained=$env:DOTS_THEME_ID; "
            f"[IO.File]::WriteAllText({literal(current)}, 'g.B'); $null=prompt; "
            "@{first=$first; retained=$retained; current=$env:DOTS_THEME_ID; "
            "color=$global:dots_colors['blue']['hex']; ls=$env:LS_COLORS} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {'first': 'first', 'retained': 'first',
                        'current': 'second', 'color': '#445566', 'ls': 'di=34'})

    def test_helpers_preserve_touch_contents_and_forward_literal_backup_paths(self):
        target = self.home / '-file [a] ü.txt'
        target.write_bytes(b'keep\x00all\xffbytes')
        directory = self.home / 'directory [a]'
        directory.mkdir()
        (directory / 'child').write_text('child')
        # New-Backup delegates to the managed backup controller. Verify this
        # adapter's literal argv; lifecycle/rollback belongs to the backup suite.
        (self.repo / 'bin/dots.ps1').write_text(
            '$args | ConvertTo-Json -Compress; $global:LASTEXITCODE=0\n')
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        p = self.run_ps('-Command', "$ErrorActionPreference='Stop'; "
            f". {helper}; touch {literal(target)}; "
            f"$a=New-Backup {literal(target)} -Copy; "
            f"$b=New-Backup {literal(directory)}; "
            "$c=New-Backup '-relative [name] ü.txt' -Copy; "
            "@{file=$a; directory=$b; relative=$c} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(target.read_bytes(), b'keep\x00all\xffbytes')
        self.assertEqual(json.loads(result['file']), ['bak', 'create', '--copy', '--', str(target)])
        self.assertEqual(json.loads(result['directory']), ['bak', 'create', '--', str(directory)])
        self.assertEqual(json.loads(result['relative']), ['bak', 'create', '--copy', '--', '-relative [name] ü.txt'])
        self.assertEqual((directory / 'child').read_text(), 'child')

    def test_clear_cache_forwards_guarded_cleanup_and_refusal(self):
        (self.repo / 'bin/dots.ps1').write_text(
            '$args | ConvertTo-Json -Compress; $global:LASTEXITCODE=3\n')
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        p = self.run_ps('-Command', f'. {helper}; ' + r'''
function Remove-Item { throw 'legacy cache deletion must not run' }
$result=Clear-Cache --group 'literal [ü]' --yes; $status=$LASTEXITCODE
@{arguments=$result; status=$status} | ConvertTo-Json -Compress
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['status'], 3)
        self.assertEqual(json.loads(result['arguments']),
                         ['cleanup', 'run', '--group', 'literal [ü]', '--yes'])

    def test_git_helpers_dirty_status_paths_and_failures(self):
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        p = self.run_ps('-Command', f'. {helper}; ' + r'''
$global:fixtureOutput=''; $global:fixtureCode=0
function git { $global:gitArgs=@($args); $global:LASTEXITCODE=$global:fixtureCode; $global:fixtureOutput }
$clean=@(gitcheck); $cleanCode=$LASTEXITCODE
$global:fixtureOutput=" M literal [name] ü`0R  renamed ü`0old name`0?? -untracked`0"
$quiet=@(gitcheck); $dirtyCode=$LASTEXITCODE
$verbose=@(gitcheck -v '-path [ü]'); $statusArgs=$global:gitArgs
$global:fixtureOutput="1 .M N... 100644 100644 100644 a b ordinary`0" +
 "1 .M S.M. 160000 160000 160000 a b module [ü]`0" +
 "1 .. S... 160000 160000 160000 a b unchanged`0" +
 "2 R. SC.. 160000 160000 160000 a b R100 renamed module`0old module`0"
$modules=@(gitsubmodule '-module'); $moduleCode=$LASTEXITCODE; $moduleArgs=$global:gitArgs
$global:fixtureOutput=''; $none=@(gitsubmodule); $noneCode=$LASTEXITCODE
$global:fixtureCode=128; $failed=@(gitcheck); $failureCode=$LASTEXITCODE
$failedModules=@(gitsubmodule); $moduleFailureCode=$LASTEXITCODE
@{clean=$clean; cleanCode=$cleanCode; quiet=$quiet; dirtyCode=$dirtyCode; verbose=$verbose;
 statusArgs=$statusArgs; modules=$modules; moduleCode=$moduleCode; moduleArgs=$moduleArgs;
 none=$none; noneCode=$noneCode; failed=$failed; failureCode=$failureCode;
 failedModules=$failedModules; moduleFailureCode=$moduleFailureCode} | ConvertTo-Json -Compress
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        for key in ('clean', 'quiet', 'none', 'failed', 'failedModules'):
            self.assertEqual(result[key], [], key)
        self.assertEqual([result[k] for k in ('cleanCode', 'dirtyCode', 'moduleCode', 'noneCode',
                                             'failureCode', 'moduleFailureCode')], [1, 0, 0, 1, 128, 128])
        self.assertEqual(result['verbose'], ['literal [name] ü', 'renamed ü', '-untracked'])
        self.assertEqual(result['modules'], ['module [ü]', 'renamed module'])
        self.assertEqual(result['statusArgs'], ['status', '--porcelain=v1', '-z',
                         '--untracked-files=normal', '--ignore-submodules=none', '--', '-path [ü]'])
        self.assertEqual(result['moduleArgs'], ['status', '--porcelain=v2', '-z',
                         '--ignore-submodules=none', '--', '-module'])

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable for owned native repository check')
    def test_gitcheck_native_unicode_owned_repository(self):
        git = shutil.which('git')
        env = dict(self.env, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        init = subprocess.run([git, 'init', '--quiet', str(self.home)],
                              env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(init.returncode, 0, init.stderr)
        name = '-literal [ü].txt'
        (self.home / name).write_text('owned')
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        p = self.run_ps('-Command', f'. {helper}; '
                        f'function git {{ & {literal(git)} @args }}; '
                        "$paths=@(gitcheck -v); $status=$LASTEXITCODE; "
                        "@{paths=$paths; status=$status} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['status'], 0)
        self.assertIn(name, result['paths'])

    def test_gup_forwards_bounded_publish_and_explicit_flags(self):
        (self.repo / 'bin/dots.ps1').write_text(
            '$args | ConvertTo-Json -Compress; $global:LASTEXITCODE=23\n')
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        p = self.run_ps('-Command', f'. {helper}; ' + r'''
function git { throw 'gup bypassed core publisher' }
$a=gup; $aCode=$LASTEXITCODE
$b=gup -Message '-literal [ü] $(throw 1)' -All -Yes -DryRun; $bCode=$LASTEXITCODE
$c=gup -Message ''; $cCode=$LASTEXITCODE
@{a=$a; aCode=$aCode; b=$b; bCode=$bCode; c=$c; cCode=$cCode} | ConvertTo-Json -Compress
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        base = ['git', 'publish', '-C', str(self.home), '--no-wiki']
        self.assertEqual(json.loads(result['a']), base)
        self.assertEqual(json.loads(result['b']), base + ['--all', '--yes', '--dry-run',
                                                        '--message', '-literal [ü] $(throw 1)'])
        self.assertEqual(json.loads(result['c']), base + ['--message', ''])
        self.assertEqual([result[k] for k in ('aCode', 'bCode', 'cCode')], [23, 23, 23])

    def test_mkcd_literal_paths_and_file_conflict(self):
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        (self.home / 'occupied').write_text('keep')
        p = self.run_ps('-Command', f'. {helper}; ' + r'''
$initial=$PWD.Path; $refused=$false
try { mkcd occupied } catch { $refused=$true }
$afterFailure=$PWD.Path
mkcd '-leading [ü]'; mkcd '..'
$missingRefused=$false; try { mkcd } catch { $missingRefused=$true }
mkcd 'space ü/[literal]/-dash'; $created=$PWD.Path
mkcd '.'; $repeated=$PWD.Path
@{refused=$refused; missingRefused=$missingRefused; afterFailure=$afterFailure;
 created=$created; repeated=$repeated} | ConvertTo-Json -Compress
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertTrue(result['refused'])
        self.assertTrue(result['missingRefused'])
        self.assertTrue((self.home / '-leading [ü]').is_dir())
        self.assertEqual(result['afterFailure'], str(self.home))
        self.assertEqual(result['created'], str(self.home / 'space ü/[literal]/-dash'))
        self.assertEqual(result['created'], result['repeated'])
        self.assertEqual((self.home / 'occupied').read_text(), 'keep')

    def test_yazi_changes_directory_only_on_success(self):
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        target = self.home / 'destination [ü]'
        target.mkdir()
        p = self.run_ps('-Command', f'. {helper}; $global:target={literal(target)}; ' + r'''
$global:fixtureCode=13; $global:temporary=@()
function Get-Command { {
  $global:yaziArgs=@($args)
  $file=$args[-1].Substring('--cwd-file='.Length); $global:temporary+=@($file)
  [IO.File]::WriteAllText($file, $global:target)
  $global:LASTEXITCODE=$global:fixtureCode
} }
y '-literal [ü]'; $failedCode=$LASTEXITCODE; $failedPath=$PWD.Path
$global:fixtureCode=0; y ''; $successCode=$LASTEXITCODE; $successPath=$PWD.Path
$retained=@($global:temporary | Where-Object { Test-Path -LiteralPath $_ })
@{failedCode=$failedCode; failedPath=$failedPath; successCode=$successCode;
 successPath=$successPath; retained=$retained; arguments=$global:yaziArgs} | ConvertTo-Json -Compress
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['failedCode'], 13)
        self.assertEqual(result['failedPath'], str(self.home))
        self.assertEqual(result['successCode'], 0)
        self.assertEqual(result['successPath'], str(target))
        self.assertEqual(result['retained'], [])
        self.assertEqual(result['arguments'][0], '')

    def test_ff_picker_literal_pipeline_cancellation_and_missing_tool(self):
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        p = self.run_ps('-Command', f'. {helper}; ' + r'''
$global:fixtureCode=0
function Get-Command { {
  $global:fzfArgs=@($args); $global:fzfInput=@($input)
  if ($global:fixtureCode -eq 0) { 'selected [ü] $(throw 1)' }
  $global:LASTEXITCODE=$global:fixtureCode
} }
$selected=@('one','-two [ü]') | ff '--query' 'literal ü'; $successCode=$LASTEXITCODE
$savedArgs=$global:fzfArgs; $savedInput=$global:fzfInput
$global:fixtureCode=130; $cancelled=@(ff); $cancelCode=$LASTEXITCODE
function Get-Command { $null }
$missing=@(ff); $missingCode=$LASTEXITCODE
@{selected=$selected; successCode=$successCode; arguments=$savedArgs; input=$savedInput;
 cancelled=$cancelled; cancelCode=$cancelCode; missing=$missing; missingCode=$missingCode} | ConvertTo-Json -Compress
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['selected'], 'selected [ü] $(throw 1)')
        self.assertEqual(result['successCode'], 0)
        self.assertEqual(result['arguments'], ['--query', 'literal ü'])
        self.assertEqual(result['input'], ['one', '-two [ü]'])
        self.assertEqual(result['cancelled'], [])
        self.assertEqual(result['cancelCode'], 130)
        self.assertEqual(result['missing'], [])
        self.assertEqual(result['missingCode'], 127)
        self.assertIn('use Find-File SEARCH for a table', p.stderr)

    @unittest.skipUnless(shutil.which('fzf'), 'FZF unavailable for owned native filter check')
    def test_ff_native_filter_preserves_unicode_pipeline(self):
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        self.env['PATH'] += os.pathsep + str(Path(shutil.which('fzf')).parent)
        p = self.run_ps('-Command', f'. {helper}; ' + r'''
$encodingBefore=$OutputEncoding
$selected=@('plain', '-literal [ü]') | ff --filter 'ü'
$status=$LASTEXITCODE
@{selected=$selected; status=$status; encodingPreserved=($OutputEncoding -eq $encodingBefore)} | ConvertTo-Json -Compress
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {'selected': '-literal [ü]', 'status': 0,
                                              'encodingPreserved': True})

    def test_editor_precedence_and_listing_fallback(self):
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        marker = self.home / 'visible [file].txt'
        marker.touch()
        p = self.run_ps('-Command', "$ErrorActionPreference='Stop'; "
            f". {helper}; $env:EDITOR=''; "
            "function Get-Command { param($Name, $CommandType, $ErrorAction); "
            "if ($Name -eq 'nvim') { 'present' } }; "
            "function nvim { param($Path); $Path }; "
            "$edited=Edit-Item 'literal [name]'; "
            "$listing=@(Invoke-eza | ForEach-Object Name); "
            "@{editor=$env:EDITOR; edited=$edited; listing=$listing} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['editor'], 'nvim')
        self.assertEqual(result['edited'], 'literal [name]')
        self.assertIn(marker.name, result['listing'])

    def test_yazi_cleanup_after_failure(self):
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        before = set(self.root.iterdir())
        p = self.run_ps('-Command', "$ErrorActionPreference='Stop'; "
            f". {helper}; function Get-Command {{ {{ throw 'fixture yazi failure' }} }}; "
            "try { y } catch { $_.Exception.Message }; "
            "if ($Error[0].Exception.Message -ne 'fixture yazi failure') { exit 1 }")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('fixture yazi failure', p.stdout)
        self.assertEqual(set(self.root.iterdir()), before)

    def test_optional_module_is_explicit_idempotent_and_retryable(self):
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        optional = literal(self.repo / 'shells/powershell/optional.ps1')
        p = self.run_interactive(f'. {entry}; '
            "$global:imports=0; function Import-Module { param($Name, [switch]$Global, $ErrorAction); "
            "$global:imports++; if ($global:imports -eq 1) { throw 'missing module' } }; "
            f"try {{ . {optional} icons }} catch {{ }}; "
            f". {optional} icons; . {optional} icons; "
            "@{imports=$imports; loaded=$global:_DotsOptionalFeatures['icons']} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {'imports': 2, 'loaded': True})

    def test_optional_generated_prompt_keeps_dots_hooks_and_rejects_failed_code(self):
        entry = literal(self.repo / 'shells/powershell/profile.ps1')
        optional = literal(self.repo / 'shells/powershell/optional.ps1')
        p = self.run_interactive(f'. {entry}; '
            "function Get-Command { { $global:LASTEXITCODE=0; "
            "'function global:prompt { \"fixture> \" }' } }; "
            f". {optional} starship; $global:LASTEXITCODE=19; $text=prompt; "
            "$preserved=$LASTEXITCODE; "
            "function Get-Command { { $global:LASTEXITCODE=1; '$global:badCodeRan=$true' } }; "
            f"try {{ . {optional} mise }} catch {{ }}; "
            "@{text=$text; code=$preserved; wrapped=((Get-Item Function:prompt).ScriptBlock.ToString() "
            "-match 'Update-DotsTheme'); failedCode=[bool]$global:badCodeRan; "
            "marked=[bool]$global:_DotsOptionalFeatures['mise']} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {'text': 'fixture> ', 'code': 19,
                        'wrapped': True, 'failedCode': False, 'marked': False})


    @unittest.skipUnless(os.name == 'nt', 'Directory junctions require native Windows')
    def test_junction_directory(self):
        junction = self.home / 'config junction'
        target = self.repo / 'shells/powershell'
        # Windows PowerShell 5.1 expands wildcards in the junction target.
        p = self.run_ps('-Command', '$target=' + literal(target) + '; '
                        'if ($PSVersionTable.PSVersion.Major -lt 6) { '
                        '$target=[Management.Automation.WildcardPattern]::Escape($target) }; '
                        'New-Item -ItemType Junction -Path ' + literal(junction) +
                        ' -Target $target | Out-Null')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.env['DOTS'] = str(self.root / 'wrong checkout')
        p = self.run_ps('-Command', '. ' + literal(junction / 'Microsoft.PowerShell_profile.ps1') + '; $env:DOTS')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), str(self.repo))


if __name__ == '__main__':
    unittest.main()
