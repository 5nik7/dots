"""Portable native PowerShell acceptance; no Bash or live profile is used."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PWSH = shutil.which(os.environ.get('DOTS_TEST_POWERSHELL') or 'pwsh')


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
                     'shells/shared/starship-default.ps1'):
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, self.repo / name)
        shutil.copytree(REPO / 'lib/dots/shell', self.repo / 'lib/dots/shell')
        shutil.copy2(REPO / 'lib/dots/ui.ps1', self.repo / 'lib/dots/ui.ps1')
        shutil.copy2(REPO / 'lib/dots/help.ps1', self.repo / 'lib/dots/help.ps1')
        shutil.copytree(REPO / 'lib/dots/metadata', self.repo / 'lib/dots/metadata')
        (self.repo / 'lib/dots/completion').mkdir()
        shutil.copy2(REPO / 'lib/dots/completion/powershell', self.repo / 'lib/dots/completion/powershell')
        # PATH deliberately contains no Bash or other external tools.
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
        for key in ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'LD_PRELOAD'):
            if key in os.environ:
                self.env[key] = os.environ[key]
        # Keep native application paths inside existing fixture directories.
        for key in ('APPDATA', 'LOCALAPPDATA'):
            Path(self.env[key]).mkdir(parents=True, exist_ok=True)

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

    def test_help_styles_and_undecorated_hook(self):
        adapter = str(self.repo / 'bin/dots.ps1')
        rich = self.run_ps('-File', adapter, '--color=always', '--icons=never', '--help')
        self.assertEqual(rich.returncode, 0, rich.stderr)
        self.assertIn('\x1b[1;96mDots', rich.stdout)
        plain = self.run_ps('-File', adapter, '--color=never', '--icons=never', '--help')
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertNotIn('\x1b', plain.stdout + plain.stderr)
        original = self.run_ps('-File', adapter, 'init', 'powershell')
        forced = self.run_ps('-File', adapter, '--color=always', '--icons=always', 'init', 'powershell')
        self.assertEqual(forced.returncode, 0, forced.stderr)
        self.assertEqual(forced.stdout, original.stdout)
        self.assertNotIn('\x1b', forced.stdout)

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

    def test_missing_loader_emits_no_code(self):
        adapter = str(self.repo / 'bin/dots.ps1')
        # Non-init dispatch now belongs to the native CLI suite. This minimal
        # fixture intentionally contains neither its Python controller nor files.
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
        # -NoExit exercises the interactive loader; explicit exit avoids a REPL.
        # Redirected input keeps PSReadLine out of these deterministic checks.
        return subprocess.run([PWSH, '-NoProfile', '-NoLogo', '-NoExit', '-Command',
            "$PROFILE.CurrentUserAllHosts=" + literal(self.home / "Documents" / "profile.ps1") + "; " +
            "$ErrorActionPreference='Stop'; try { " + code +
            " } catch { [Console]::Error.WriteLine($_); exit 1 }; exit 0"],
            cwd=self.home, env=self.env, input='', text=True,
            capture_output=True, timeout=30)

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
            f"foreach ($feature in 'blastoff','command-not-found') {{ try {{ . {optional} $feature; exit 1 }} "
            "catch { if ($_.Exception.Message -notlike '*requires PowerShell Core*') { exit 2 } } }; exit 0")
        self.assertEqual(p.returncode, 0, p.stderr)

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
                f'@theme\tflavor\tdark\nblue\thex\t{color}\n')
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

    def test_helpers_preserve_file_contents_and_literal_backup_paths(self):
        target = self.home / '-file [a] ü.txt'
        target.write_bytes(b'keep\x00all\xffbytes')
        directory = self.home / 'directory [a]'
        directory.mkdir()
        (directory / 'child').write_text('child')
        helper = literal(self.repo / 'shells/powershell/helpers.ps1')
        p = self.run_ps('-Command', "$ErrorActionPreference='Stop'; "
            f". {helper}; touch {literal(target)}; "
            f"$a=New-Backup {literal(target)} -Copy; "
            f"$b=New-Backup {literal(directory)}; "
            "@{file=$a; directory=$b} | ConvertTo-Json -Compress")
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(target.read_bytes(), b'keep\x00all\xffbytes')
        self.assertEqual(Path(result['file']).read_bytes(), target.read_bytes())
        self.assertFalse(directory.exists())
        self.assertEqual((Path(result['directory']) / 'child').read_text(), 'child')

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
