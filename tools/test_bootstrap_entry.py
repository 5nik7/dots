#!/usr/bin/env python3
"""First-stage acquisition with local remotes and test-owned prerequisite adapters."""
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
    def test_native_dry_run_uses_owned_destination(self):
        engines=[name for name in ('powershell','pwsh') if shutil.which(name)]
        if not engines: self.skipTest('PowerShell runtime unavailable')
        with tempfile.TemporaryDirectory(prefix='dots-native-bootstrap-') as tmp:
            for engine in engines:
                with self.subTest(engine=engine):
                    destination=Path(tmp)/engine/'dots'
                    result=subprocess.run([engine,'-NoProfile','-File',str(ROOT/'bootstrap.ps1'),'-Destination',str(destination),'-DryRun','-Json'],capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(json.loads(result.stdout)['status'],'planned')
                    self.assertFalse(destination.parent.exists())


if __name__=='__main__':unittest.main()
