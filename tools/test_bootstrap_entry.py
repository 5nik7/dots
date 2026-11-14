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


@unittest.skipIf(os.name == 'nt', 'POSIX bootstrap; native adapter has a separate gate')
class Bootstrap(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-bootstrap-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = {k:v for k,v in os.environ.items() if k in ('PATH','PREFIX','LD_PRELOAD','SYSTEMROOT')}
        self.env.update(HOME=str(self.home),XDG_CONFIG_HOME=str(self.home/'config'),
            XDG_STATE_HOME=str(self.home/'state'),XDG_CACHE_HOME=str(self.home/'cache'),
            GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1',REAL_PYTHON=sys.executable)
        self.source = self.home/'source with spaces 雪'; self.source.mkdir()
        self.layout(self.source)
        self.git('init','-b','main',str(self.source))
        self.git('-C',str(self.source),'add','.')
        self.git('-C',str(self.source),'-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
        self.launch = self.home/'download';self.launch.mkdir()
        self.script = self.launch/'bootstrap.sh';shutil.copy2(ROOT/'bootstrap.sh',self.script)
        self.destination = self.home/'installed dots'

    def git(self,*args):
        return subprocess.run([shutil.which('git'),*args],env=self.env,capture_output=True,text=True,check=True,timeout=30)

    def layout(self,root):
        for name in ('bin/dots','bin/dots.ps1','lib/dots/files/install.py','install.ps1'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture\n')
        (root/'install.sh').write_text('#!/bin/sh\nexec python3 -B -c \'import json,sys;print(json.dumps({"installer_args":sys.argv[1:]}))\' "$@"\n')
        (root/'.gitmodules').write_text('[submodule "private"]\n path = private\n url = https://invalid.invalid/private\n')

    def run_bootstrap(self,*args,code=0,**env):
        command=[shutil.which('sh'),str(self.script),'--source',str(self.source),'--destination',str(self.destination),*args]
        result=subprocess.run(command,env=dict(self.env,**env),cwd=self.home,capture_output=True,text=True,timeout=30)
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
        bindir=self.home/'test-bin';bindir.mkdir()
        for name in ('sh','bash','dirname','id'):
            (bindir/name).symlink_to(shutil.which(name))
        python=bindir/'python3';python.write_text('#!/bin/sh\nexit 1\n');python.chmod(0o755)
        log=self.home/'package-log'
        pkg=bindir/'pkg';pkg.write_text('''#!/bin/sh
printf '%s\\n' "$*" > "$PACKAGE_LOG"
printf '#!/bin/sh\\nexec "%s" "$@"\\n' "$REAL_PYTHON" > "$TEST_BIN/python3"
''');pkg.chmod(0o755)
        settings=dict(PATH=str(bindir),PREFIX='/data/data/com.termux/files/usr',PACKAGE_LOG=str(log),TEST_BIN=str(bindir))
        self.run_bootstrap('--non-interactive',code=1,**settings)
        self.assertFalse(log.exists())
        result=self.run_bootstrap('--yes','--json',**settings)
        self.assertEqual(log.read_text().strip(),'install -y python')
        self.assertIn('--with-dependencies',json.loads(result.stdout)['installer_args'])


@unittest.skipUnless(os.name=='nt', 'native Windows PowerShell 5.1/7 bootstrap acceptance pending')
class NativeBootstrap(unittest.TestCase):
    def engines(self):
        engines = [name for name in ('powershell', 'pwsh') if shutil.which(name)]
        if not engines:
            self.skipTest('PowerShell runtime unavailable')
        return engines

    def run_script(self, engine, script, home):
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   XDG_CONFIG_HOME=str(home/'config'), XDG_DATA_HOME=str(home/'data'),
                   XDG_STATE_HOME=str(home/'state'), XDG_CACHE_HOME=str(home/'cache'),
                   APPDATA=str(home/'Roaming'), LOCALAPPDATA=str(home/'Local'),
                   CODEX_HOME=str(home/'.codex'))
        encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        return subprocess.run([engine, '-NoProfile', '-EncodedCommand', encoded],
                              env=env, stdin=subprocess.DEVNULL, capture_output=True,
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
            env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                       GIT_TERMINAL_PROMPT='0', HOME=str(home), USERPROFILE=str(home))
            for args in (['init','-b','main'], ['add','.'],
                         ['-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture']):
                result = subprocess.run([shutil.which('git'),'-C',str(source),*args],env=env,
                                        stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            for engine in self.engines():
                with self.subTest(engine=engine):
                    destination = home/engine/'owned checkout 雪'
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
            for engine in engines:
                with self.subTest(engine=engine):
                    destination=Path(tmp)/engine/'dots'
                    result=subprocess.run([engine,'-NoProfile','-File',str(ROOT/'bootstrap.ps1'),'-Destination',str(destination),'-DryRun','-Json'],capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(json.loads(result.stdout)['status'],'planned')
                    self.assertFalse(destination.parent.exists())


if __name__=='__main__':unittest.main()
