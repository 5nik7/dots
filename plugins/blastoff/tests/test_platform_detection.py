"""Host fixtures are not native Windows/WSL/MSYS2 execution evidence."""
import base64
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from test_lifecycle_planning import installer

ROOT = Path(__file__).resolve().parents[1]
platforms = installer.core.ui_module('host_platform')


class PlatformDetection(unittest.TestCase):
    def classify(self, **changes):
        facts = dict(host='posix', platform='linux', android=False, executable='/usr/bin/python3',
                     kernel='6.1.0', env={}, shell='bash', shell_os='linux-gnu')
        facts.update(changes)
        return platforms.classify(**facts)

    def test_linux_wsl_and_inherited_markers(self):
        self.assertEqual(self.classify()['environment'], 'linux')
        for facts in ({'kernel':'5.15.0-microsoft-standard-WSL2'},
                      {'kernel':'4.4.0-Microsoft'}, {'env':{'WSL_INTEROP':'/run/WSL/1_interop'}},
                      {'env':{'WSL_DISTRO_NAME':'Ubuntu'}}):
            self.assertEqual(self.classify(**facts)['environment'], 'wsl')
        self.assertEqual(self.classify(env={'MSYSTEM':'UCRT64','PREFIX':'/unrelated'})['environment'], 'linux')
        windows = self.classify(host='nt', platform='win32', shell='powershell', shell_os='',
                               env={'MSYSTEM':'MINGW64','WSL_DISTRO_NAME':'Ubuntu'})
        self.assertEqual(platforms.validate(windows)['label'], 'Windows')
        self.assertEqual(self.classify(platform='darwin', kernel='Darwin')['label'], 'macOS')

    def test_termux_requires_native_android_and_termux_identity(self):
        facts = {'env':{'TERMUX_VERSION':'fixture','WSL_DISTRO_NAME':'inherited'}}
        self.assertEqual(self.classify(platform='android', **facts)['environment'], 'termux')
        self.assertEqual(self.classify(android=True, **facts)['environment'], 'termux')
        self.assertEqual(self.classify(platform='android')['environment'], 'other')
        self.assertEqual(self.classify(env={'TERMUX_VERSION':'inherited'})['environment'], 'linux')
        info = self.classify(platform='android', **facts)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, PREFIX=directory):
            self.assertEqual(installer.default_prefix(info), Path(directory))
            self.assertEqual(installer.default_prefix(self.classify(kernel='microsoft')), Path.home()/'.local')
        with patch.dict(os.environ, PREFIX=''):
            with self.assertRaisesRegex(installer.core.Failure, 'requires PREFIX'):
                installer.default_prefix(info)

    def test_compatibility_shells_and_wrong_runtime_are_rejected(self):
        for host in ('nt','posix'):
            for variant in ('MSYS','MINGW64','UCRT64','CLANG64','CLANGARM64'):
                info = self.classify(host=host, shell_os='msys', env={'MSYSTEM':variant})
                with self.assertRaisesRegex(ValueError, 'PowerShell 7'):
                    platforms.validate(info)
        for shell_os in ('mingw64','cygwin'):
            with self.assertRaises(ValueError): platforms.validate(self.classify(shell_os=shell_os))
        with self.assertRaisesRegex(ValueError, 'do not mix Windows and WSL'):
            platforms.validate(self.classify(host='nt', platform='win32'))
        # Direct POSIX-emulation Python must not bypass the adapter boundary.
        with self.assertRaises(ValueError):
            platforms.validate(self.classify(platform='cygwin', shell='python', shell_os=''))

    def test_runtime_mismatch_precedes_all_planning(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)/'missing'
            info = self.classify(host='nt', platform='win32')
            with patch.object(platforms,'detect',return_value=info), \
                 patch.object(installer,'make_plan') as plan:
                with self.assertRaises(installer.core.Failure) as caught:
                    installer.run(['--_bash-host-v1','linux-gnu','install','--prefix',str(prefix),'--dry-run'])
                self.assertEqual(caught.exception.code,3)
                plan.assert_not_called()
            self.assertFalse(prefix.exists())

    def test_labels_verbose_evidence_and_explicit_prefix_do_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)/'missing'
            for info in (self.classify(), self.classify(kernel='microsoft'),
                         self.classify(platform='android',env={'TERMUX_VERSION':'fixture'})):
                out, err = io.StringIO(), io.StringIO()
                with patch.object(platforms,'detect',return_value=info), patch.dict(os.environ,PREFIX=''), \
                     redirect_stdout(out), redirect_stderr(err):
                    code=installer.run(['uninstall','--prefix',str(prefix),'--dry-run','--verbose','--color','never'])
                self.assertEqual(code,0)
                self.assertIn('SYSTEM',out.getvalue())
                self.assertIn(info['label'],out.getvalue())
                self.assertIn('Python executable:',err.getvalue())
                self.assertFalse(prefix.exists())

    def test_legacy_powershell_transport_keeps_installer_operands(self):
        with tempfile.TemporaryDirectory(prefix="blastoff ü ' ") as directory:
            prefix = Path(directory)/'missing'
            argv=['uninstall','--prefix',str(prefix),'--dry-run','--color','never']
            encoded=base64.b64encode(json.dumps({'version':1,'host':os.name,'argv':argv}).encode()).decode()
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(installer.run(['--_powershell-argv-v1',encoded]),0)
            self.assertIn(str(prefix),out.getvalue())
            self.assertFalse(prefix.exists())
            with self.assertRaises(installer.core.Failure) as caught:
                installer.run(['--_powershell-argv-v1','invalid'])
            self.assertEqual(caught.exception.code,3)

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Native Bash fixture')
    def test_shell_guard_runs_before_missing_python_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            env=dict(os.environ,HOME=directory,BLASTOFF_PYTHON=str(Path(directory)/'missing-python'))
            for kind in ('msys','cygwin','mingw64'):
                result=subprocess.run([shutil.which('bash'),'-c',
                    'OSTYPE=$1; source "$2/scripts/lifecycle.sh"; blastoff_lifecycle "$2" install --public --dry-run',
                    'fixture',kind,str(ROOT)],env=env,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,3)
                self.assertIn('PowerShell 7+',result.stderr)
                self.assertNotIn('Python runtime not found',result.stderr)
                self.assertEqual(result.stdout,'')
            self.assertEqual(list(Path(directory).iterdir()),[])

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Native Bash fixture')
    def test_missing_python_is_dependency_failure_for_every_bash_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            env=dict(os.environ,HOME=directory,BLASTOFF_PYTHON=str(Path(directory)/'missing-python'))
            for entry in ('bin/blastoff','install.sh','uninstall.sh','scripts/install.sh'):
                result=subprocess.run([shutil.which('bash'),str(ROOT/entry),'--version'],
                                      env=env,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,3,result.stderr)
                self.assertEqual(result.stdout,'')
                self.assertIn('Python 3.11+',result.stderr)
            self.assertEqual(list(Path(directory).iterdir()),[])
