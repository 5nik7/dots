#!/usr/bin/env python3
"""First-stage acquisition with local remotes and test-owned prerequisite adapters."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REQUESTED_POWERSHELL = os.environ.get('DOTS_TEST_POWERSHELL')
if REQUESTED_POWERSHELL and not shutil.which(REQUESTED_POWERSHELL):
    raise SystemExit('required PowerShell engine unavailable: ' + REQUESTED_POWERSHELL)


def owned_environment(home):
    """Only explicit native runtime inputs survive into the fixture."""
    env = {key: os.environ[key] for key in
           ('SystemRoot', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT',
            'LD_PRELOAD', 'PREFIX', 'TERMUX__PREFIX', 'TERMUX_VERSION') if key in os.environ}
    runtime = home/'runtime'
    for directory in (runtime, runtime/'git-template', runtime/'git-hooks', runtime/'tools'):
        directory.mkdir(parents=True, exist_ok=True)
    env.update(HOME=str(home), USERPROFILE=str(home),
        XDG_CONFIG_HOME=str(home/'config'), XDG_DATA_HOME=str(home/'data'),
        XDG_STATE_HOME=str(home/'state'), XDG_CACHE_HOME=str(home/'cache'),
        XDG_RUNTIME_DIR=str(runtime), APPDATA=str(home/'Roaming'), LOCALAPPDATA=str(home/'Local'),
        CODEX_HOME=str(home/'codex'), TEMP=str(runtime), TMP=str(runtime), TMPDIR=str(runtime),
        PSModulePath=str(runtime/'modules'), PSModuleAnalysisCachePath=str(runtime/'ModuleAnalysisCache'),
        POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off',
        DOTNET_MultiCoreJitNoProfileGather='1', PYTHONNOUSERSITE='1',
        PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
        PYTHON_MANAGER_AUTOMATIC_INSTALL='false',
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0',
        GCM_INTERACTIVE='Never', GIT_ALLOW_PROTOCOL='file',
        GIT_TEMPLATE_DIR=str(runtime/'git-template'), GIT_CONFIG_COUNT='1',
        GIT_CONFIG_KEY_0='core.hooksPath', GIT_CONFIG_VALUE_0=str(runtime/'git-hooks'),
        DOTS_TERMUX_AUTOSTART='0', TERM='dumb')
    return env


@unittest.skipIf(os.name == 'nt', 'POSIX bootstrap; native adapter has a separate gate')
class Bootstrap(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-bootstrap-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = owned_environment(self.home)
        self.env.update(PATH=os.environ.get('PATH',''), REAL_PYTHON=sys.executable)
        self.source = self.home/'source with spaces 雪'; self.source.mkdir()
        self.layout(self.source)
        self.git('init','-b','main',str(self.source))
        self.git('-C',str(self.source),'add','.')
        self.git('-C',str(self.source),'-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
        self.launch = self.home/'download';self.launch.mkdir()
        self.script = self.launch/'bootstrap.sh';shutil.copy2(ROOT/'bootstrap.sh',self.script)
        self.destination = self.home/'installed dots'

    def git(self,*args):
        return subprocess.run([shutil.which('git'),*args],env=self.env,cwd=self.home,
                              stdin=subprocess.DEVNULL,capture_output=True,text=True,check=True,timeout=30)

    def layout(self,root):
        for name in ('bin/dots','bin/dots.ps1','lib/dots/files/install.py','install.ps1'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture\n')
        (root/'install.sh').write_text('#!/bin/sh\nexec python3 -B -c \'import json,sys;print(json.dumps({"installer_args":sys.argv[1:]}))\' "$@"\n')
        (root/'.gitmodules').write_text('[submodule "private"]\n path = private\n url = https://invalid.invalid/private\n')

    def run_bootstrap(self,*args,code=0,**env):
        command=[shutil.which('sh'),str(self.script),'--source',str(self.source),'--destination',str(self.destination),*args]
        result=subprocess.run(command,env=dict(self.env,**env),cwd=self.home,stdin=subprocess.DEVNULL,
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return result

    def test_fresh_acquisition_and_literal_handoff(self):
        result=self.run_bootstrap('--yes','--component','core','--resource','literal "雪"','--json')
        self.assertEqual(json.loads(result.stdout)['installer_args'],['--json','--yes','--with-dependencies','--component','core','--resource','literal "雪"'])
        self.assertTrue((self.destination/'bin/dots').is_file())
        self.assertFalse((self.destination/'private').exists())
        journals=list(self.home.glob('.installed dots.bootstrap-*/journal.json'))
        self.assertEqual(len(journals),1)
        record=json.loads(journals[0].read_text())
        self.assertEqual(record['status'],'committed')
        self.assertEqual(record['commit'],self.git('-C',str(self.source),'rev-parse','HEAD').stdout.strip())

    def test_preview_and_offline_do_not_create_destination(self):
        self.destination=self.home/'missing parent/dots'
        data=json.loads(self.run_bootstrap('--dry-run','--json').stdout)
        self.assertEqual(data['status'],'planned')
        self.assertFalse(self.destination.parent.exists())
        self.run_bootstrap('--offline','--yes',code=1)
        self.assertFalse(self.destination.parent.exists())

    def test_existing_checkout_retains_changes_and_never_fetches(self):
        self.destination.mkdir();self.layout(self.destination)
        (self.destination/'custom').write_text('retain')
        preview=json.loads(self.run_bootstrap('--dry-run','--offline','--json').stdout)
        self.assertIn('--with-dependencies',preview['installer_args'])
        self.assertIn('--offline',preview['installer_args'])
        self.run_bootstrap('--source','https://invalid.invalid/no-fetch.git','--yes','--json')
        self.assertEqual((self.destination/'custom').read_text(),'retain')
        self.assertEqual(list(self.home.glob('.installed dots.bootstrap-*')),[])

    def test_failure_retains_journal_without_publishing(self):
        self.run_bootstrap('--ref','not-a-real-ref','--yes',code=1)
        self.assertFalse(self.destination.exists())
        journals=list(self.home.glob('.installed dots.bootstrap-*/journal.json'))
        self.assertEqual(json.loads(journals[0].read_text())['status'],'failed')

    def test_occupied_destination_and_credential_source_refused(self):
        self.destination.mkdir(); (self.destination/'original').write_text('retain')
        self.run_bootstrap('--yes',code=1)
        self.assertEqual((self.destination/'original').read_text(),'retain')
        self.run_bootstrap('--source','https://name:secret@example.invalid/dots','--yes',code=1)
        self.assertEqual(list(self.home.glob('.installed dots.bootstrap-*')),[])

    def test_missing_python_uses_only_reviewed_fake_prerequisites(self):
        self.destination.mkdir();self.layout(self.destination)
        bindir=self.home/'com.termux/files/usr/bin';bindir.mkdir(parents=True)
        for name in ('env','sh','bash','dirname','id'):
            (bindir/name).symlink_to(shutil.which(name))
        python=bindir/'python3';python.write_text('#!/bin/sh\nexit 1\n');python.chmod(0o755)
        log=self.home/'package-log'
        pkg=bindir/'pkg';pkg.write_text('''#!/bin/sh
printf '%s\\n' "$*" > "$PACKAGE_LOG"
printf '#!/bin/sh\\nexec "%s" "$@"\\n' "$REAL_PYTHON" > "$TEST_BIN/python3"
''');pkg.chmod(0o755)
        settings=dict(PATH=str(bindir),PREFIX=str(bindir.parent),TERMUX__PREFIX=str(bindir.parent),
                      PACKAGE_LOG=str(log),TEST_BIN=str(bindir))
        self.run_bootstrap('--non-interactive',code=1,**settings)
        self.assertFalse(log.exists())
        result=self.run_bootstrap('--yes','--json',**settings)
        self.assertEqual(log.read_text().strip(),'install -y python')
        self.assertIn('--with-dependencies',json.loads(result.stdout)['installer_args'])

    def test_git_transport_and_hooks_are_isolated(self):
        result=subprocess.run([shutil.which('git'),'ls-remote','https://invalid.invalid/fixture'],
                              env=self.env,cwd=self.home,stdin=subprocess.DEVNULL,
                              capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("transport 'https' not allowed",result.stderr)
        hook=self.source/'.git/hooks/pre-commit';hook.parent.mkdir(exist_ok=True)
        hook.write_text('#!/bin/sh\nprintf executed > "$HOME/hook-ran"\n');hook.chmod(0o755)
        self.git('-C',str(self.source),'-c','user.name=fixture','-c','user.email=fixture@example.invalid',
                 'commit','--allow-empty','-m','hook isolation')
        self.assertFalse((self.home/'hook-ran').exists())
        self.assertEqual(list((self.home/'runtime/git-template').iterdir()),[])


@unittest.skipUnless(os.name=='nt', 'native Windows PowerShell 5.1/7 bootstrap acceptance pending')
class NativeBootstrap(unittest.TestCase):
    def engines(self):
        engines = [shutil.which(REQUESTED_POWERSHELL)] if REQUESTED_POWERSHELL else [
            shutil.which(name) for name in ('powershell', 'pwsh') if shutil.which(name)]
        if not engines:
            self.skipTest('PowerShell runtime unavailable')
        return engines

    def run_script(self, engine, script, home, missing=()):
        env = owned_environment(home)
        env.update(OS='Windows_NT', PATH=str(home/'runtime/tools'))
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        python = '$null' if 'python' in missing else quote(sys.executable)
        git = '$null' if 'git' in missing or not shutil.which('git') else quote(shutil.which('git'))
        # Run the unmodified production script. Intercept its actual external
        # discovery and OS acquisition boundaries, not the bootstrap functions
        # which the script defines again in its own scope.
        guards = '''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
function Get-Command {
    [CmdletBinding()] param([Parameter(Position=0)][string[]] $Name, $CommandType)
    foreach ($item in $Name) {
        if ($item -in @('py','python3','python')) {
            $selected = FIXTURE_PYTHON
            if ($selected -and $item -eq 'python') { [pscustomobject]@{ Name='python.exe'; Source=$selected } }
        } elseif ($item -eq 'git') {
            $selected = FIXTURE_GIT
            if ($selected) { [pscustomobject]@{ Name='git.exe'; Source=$selected } }
        } elseif ($item -notin @('winget','pymanager')) { throw ('fixture forbidden discovery: ' + $item) }
    }
}
function Invoke-RestMethod { throw 'fixture forbidden: Invoke-RestMethod' }
function Invoke-WebRequest { throw 'fixture forbidden: Invoke-WebRequest' }
function Add-AppxPackage { throw 'fixture forbidden: Add-AppxPackage' }
function Start-Process { throw 'fixture forbidden: Start-Process' }
function Read-Host { throw 'fixture forbidden: Read-Host' }
'''.replace('FIXTURE_PYTHON',python).replace('FIXTURE_GIT',git)
        encoded = base64.b64encode((guards+script).encode('utf-16-le')).decode('ascii')
        return subprocess.run([engine, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                              env=env, cwd=home, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding='utf-8', timeout=30)

    def test_native_python_probe_disables_acquisition_and_restores_environment(self):
        # Extract discovery alone and substitute an inert launcher. No real
        # Python manager, package provider or startup hook runs in this fixture.
        with tempfile.TemporaryDirectory(prefix='dots-native-python-probe-') as tmp:
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            script = '''
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(SCRIPT, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$helper = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Find-DotsBootstrapPython' }, $true)
. ([scriptblock]::Create($helper.Extent.Text))
function Get-Command { [pscustomobject]@{ Name = 'python.exe'; Source = 'Invoke-FixturePython' } }
function Invoke-FixturePython {
    $script:probed = $true
    $script:guarded = ($env:PYTHON_MANAGER_AUTOMATIC_INSTALL -eq 'false' -and
        -not (Test-Path Env:PYLAUNCHER_ALLOW_INSTALL) -and
        -not (Test-Path Env:PYLAUNCHER_ALWAYS_INSTALL))
    if ($script:failure) { throw 'fixture missing runtime' }
    $global:LASTEXITCODE = 0
    return PYTHON
}
$results = @(foreach ($initial in @($null, '0', '1')) {
    foreach ($failure in @($false, $true)) {
        $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = $initial
        $env:PYLAUNCHER_ALLOW_INSTALL = $initial
        $env:PYLAUNCHER_ALWAYS_INSTALL = $initial
        $script:probed = $false; $script:guarded = $false; $script:failure = $failure
        $found = Find-DotsBootstrapPython
        [pscustomobject]@{
            probed = $script:probed; guarded = $script:guarded
            found = $found; failure = $failure
            restored = ($env:PYTHON_MANAGER_AUTOMATIC_INSTALL -ceq $initial -and
                $env:PYLAUNCHER_ALLOW_INSTALL -ceq $initial -and
                $env:PYLAUNCHER_ALWAYS_INSTALL -ceq $initial)
        }
    }
})
ConvertTo-Json -InputObject $results -Compress
'''.replace('SCRIPT', quote(ROOT/'bootstrap.ps1')).replace('PYTHON\n', quote(sys.executable)+'\n')
            for engine in self.engines():
                with self.subTest(engine=engine):
                    result = self.run_script(engine, script, Path(tmp))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    rows = json.loads(result.stdout)
                    self.assertEqual(len(rows), 6)
                    for row in rows:
                        self.assertTrue(row['probed'], row)
                        self.assertTrue(row['guarded'], row)
                        self.assertTrue(row['restored'], row)
                        self.assertEqual(row['found'], None if row['failure'] else sys.executable)

    def test_native_prerequisite_output_and_failure_status(self):
        # Extract only this helper: no acquisition, package tool or startup hook.
        with tempfile.TemporaryDirectory(prefix='dots-native-helper-') as tmp:
            home = Path(tmp)
            command = home/'fake prerequisite.py'
            command.write_text('import sys\nprint("progress")\nprint("diagnostic", file=sys.stderr)\nsys.exit(int(sys.argv[1]))\n')
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            for engine in self.engines():
                for code in (0, 47):
                    with self.subTest(engine=engine, code=code):
                        script = '''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(SCRIPT, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$helper = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-DotsBootstrapNative' }, $true)
. ([scriptblock]::Create($helper.Extent.Text))
try { Invoke-DotsBootstrapNative PYTHON @('-B', COMMAND, 'CODE'); exit 0 }
catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }
'''.replace('SCRIPT', quote(ROOT/'bootstrap.ps1')).replace('PYTHON', quote(sys.executable)).replace('COMMAND', quote(command)).replace('CODE', str(code))
                        result = self.run_script(engine, script, home)
                        self.assertEqual(result.returncode, int(code != 0), result.stderr)
                        self.assertEqual(result.stdout, '')
                        self.assertIn('progress', result.stderr)
                        self.assertIn('diagnostic', result.stderr)
                        if code:
                            self.assertIn('Prerequisite command failed (47)', result.stderr)

    def test_native_existing_checkout_preserves_literal_handoff_and_exit_status(self):
        with tempfile.TemporaryDirectory(prefix='dots-native-bootstrap-') as tmp:
            home = Path(tmp)
            destination = home/'checkout with spaces 雪'
            for name in ('install.ps1', 'bin/dots.ps1', 'lib/dots/files/install.py'):
                path = destination/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture\n')
            (destination/'lib/dots/files/entry.ps1').write_text('''
function Invoke-DotsFiles($Root, $Mode, $CliArguments, $Environment, $Python) {
    ConvertTo-Json -InputObject @($CliArguments) -Compress
    $script:DotsFilesExitCode = 47
}
''')
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            args = ['-Destination', str(destination), '-DryRun', '-Offline', '-Json',
                    '--resource', 'literal "雪"', '--resource', '', '--component', 'core']
            for engine in self.engines():
                with self.subTest(engine=engine):
                    script = ('[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)\n'
                              '$arguments = @(' + ','.join(map(quote,args)) + ')\n& ' +
                              quote(ROOT/'bootstrap.ps1') + ' @arguments\nexit $LASTEXITCODE')
                    result = self.run_script(engine, script, home)
                    self.assertEqual(result.returncode, 47, result.stderr)
                    self.assertEqual(json.loads(result.stdout), ['install','--with-dependencies',
                        '--resource','literal "雪"','--resource','','--component','core',
                        '--offline','--dry-run','--json'])
                    self.assertFalse((home/'state').exists())

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable for owned local acquisition')
    def test_native_local_acquisition_keeps_progress_off_json(self):
        with tempfile.TemporaryDirectory(prefix='dots-native-acquire-') as tmp:
            home = Path(tmp)
            source = home/'source with spaces 雪'
            for name in ('install.ps1', 'bin/dots.ps1', 'lib/dots/files/install.py'):
                path = source/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture\n')
            try:
                probe = home/'probe'
                probe.symlink_to(source, target_is_directory=True)
                probe.unlink()
            except OSError as error:
                self.skipTest('native symlink probe requires existing capability: ' + str(error))
            (source/'lib/dots/files/entry.ps1').write_text('''
function Invoke-DotsFiles($Root, $Mode, $CliArguments, $Environment, $Python) {
    @{ status = 'fixture'; arguments = @($CliArguments) } | ConvertTo-Json -Compress
    $script:DotsFilesExitCode = 0
}
''')
            env = owned_environment(home)
            env['PATH'] = str(home/'runtime/tools')
            for args in (['init','-b','main'], ['add','.'],
                         ['-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture']):
                result = subprocess.run([shutil.which('git'),'-C',str(source),*args],env=env,cwd=home,
                                        stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            for index, engine in enumerate(self.engines()):
                with self.subTest(engine=engine):
                    destination = home/('engine-'+str(index))/'owned checkout 雪'
                    args = ['-Destination',str(destination),'-Source',str(source),'-Yes','-Json',
                            '--component','core']
                    script = ("$env:GIT_CONFIG_GLOBAL = " + quote(os.devnull) + "; $env:GIT_CONFIG_NOSYSTEM = '1'\n"
                              '[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)\n'
                              '$arguments = @(' + ','.join(map(quote,args)) + ')\n& ' +
                              quote(ROOT/'bootstrap.ps1') + ' @arguments\nexit $LASTEXITCODE')
                    result = self.run_script(engine, script, home)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(json.loads(result.stdout)['status'],'fixture')
                    self.assertTrue((destination/'bin/dots.ps1').is_file())
                    self.assertFalse(list(destination.glob('dots-link-probe-*')))
                    journal = next(destination.parent.glob('.dots-bootstrap-*/journal.json'))
                    self.assertEqual(json.loads(journal.read_text(encoding='utf-8-sig'))['status'],'committed')

    def test_native_dry_run_uses_owned_destination(self):
        engines=self.engines()
        with tempfile.TemporaryDirectory(prefix='dots-native-bootstrap-') as tmp:
            home=Path(tmp)
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            for index,engine in enumerate(engines):
                with self.subTest(engine=engine):
                    destination=home/('engine-'+str(index))/'dots'
                    script='& '+quote(ROOT/'bootstrap.ps1')+' -Destination '+quote(destination)+' -DryRun -Json\n'
                    result=self.run_script(engine,script,home)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(json.loads(result.stdout)['status'],'planned')
                    self.assertFalse(destination.parent.exists())

    def test_native_missing_prerequisites_and_forbidden_boundaries_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix='dots-native-bootstrap-guards-') as tmp:
            home=Path(tmp)
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            for engine in self.engines():
                # Positive controls prove every installed tripwire terminates
                # before the corresponding real command can run.
                for boundary in ('Invoke-RestMethod','Invoke-WebRequest','Add-AppxPackage','Start-Process','Read-Host'):
                    with self.subTest(engine=engine,boundary=boundary):
                        result=self.run_script(engine,boundary,home)
                        self.assertNotEqual(result.returncode,0)
                        self.assertIn('fixture forbidden: '+boundary,result.stderr)
                for missing,boundary in (('python','Add-AppxPackage'),('git','Invoke-RestMethod')):
                    with self.subTest(engine=engine,missing=missing):
                        destination=home/('missing-'+missing)
                        script=('& '+quote(ROOT/'bootstrap.ps1')+' -Destination '+quote(destination)+
                                ' -Source '+quote(home/'unused local source')+' -Yes -Json\nexit $LASTEXITCODE')
                        result=self.run_script(engine,script,home,missing=(missing,))
                        self.assertNotEqual(result.returncode,0)
                        self.assertIn('fixture forbidden: '+boundary,result.stderr)
                        self.assertFalse(destination.exists())


if __name__=='__main__':unittest.main()
