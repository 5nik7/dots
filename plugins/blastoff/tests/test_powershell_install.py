"""Shared backend tests; these are not native PowerShell or Windows evidence."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from release_support import ReleaseHarness
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ps_install',ROOT/'scripts/powershell_install.py')
ps=importlib.util.module_from_spec(spec);spec.loader.exec_module(ps)

class PowerShellInstall(ReleaseHarness):
    def setUp(self):
        super().setUp()
        self.module_root=self.home/'redirected Documents ü'/'PowerShell'/'Modules'
        self.profile=self.home/"profiles ' ü"/'profile.ps1'
        self.context={'host':os.name,'module_root':str(self.module_root),'profile_path':str(self.profile),'known_profiles':[str(self.profile)]}
        self.environment=patch.dict(os.environ,self.env,clear=True);self.environment.start();self.addCleanup(self.environment.stop)
    def plan(self,action='install'):
        return ps.make_plan(action,self.context,verify=False)
    def test_plan_repeat_upgrade_uninstall_and_retention(self):
        self.write(self.profile,'# unrelated\r\n')
        self.write(self.config,'x=1\n');self.theme()
        before=self.tree(); plan=self.plan(); description=ps.description(plan)
        self.assertEqual(self.tree(),before);self.assertIn('Import-Module',description['profiles'][0]['diff'])
        ps.engine.apply(plan)
        installed=self.tree();repeat=self.plan();self.assertEqual(repeat.writes,{})
        ps.engine.apply(repeat);self.assertEqual(installed,self.tree())
        original=ps.core.VERSION
        with patch.object(ps.core,'VERSION','99.0.0'):
            upgrade=self.plan();ps.engine.apply(upgrade)
            self.assertIn('99.0.0',self.profile.read_text())
        with self.assertRaisesRegex(Exception,'downgrade'):self.plan()
        uninstall=self.plan('uninstall');ps.engine.apply(uninstall)
        self.assertEqual(self.profile.read_bytes(),b'# unrelated\r\n')
        self.assertEqual(self.config.read_text(),'x=1\n');self.assertTrue((self.store/'themes/purple.toml').is_file())
        self.assertTrue(list((self.module_root/'blastoff/.blastoff/profile-backups').glob('*.bak')))
    def test_modified_owned_files_and_profile_are_retained(self):
        ps.engine.apply(self.plan())
        target=self.module_root/'blastoff'/ps.core.VERSION/'lib/blastoff.py';target.write_text('user edit')
        with self.assertRaisesRegex(Exception,'changed'):self.plan()
        self.profile.write_text(self.profile.read_text().replace('Import-Module','Import-Module -Verbose'))
        plan=self.plan('uninstall');self.assertTrue(any('Retain modified' in note for note in plan.notes))
        ps.engine.apply(plan);self.assertEqual(target.read_text(),'user edit');self.assertIn('-Verbose',self.profile.read_text())
    def test_conflicts_and_concurrent_edits_precede_writes(self):
        self.write(self.profile,"Import-Module 'other/blastoff.psd1'\n")
        before=self.tree()
        with self.assertRaisesRegex(Exception,'Conflicting'):self.plan()
        self.assertEqual(before,self.tree())
        self.profile.write_text('# fine\n');plan=self.plan();token=ps.description(plan)['token']
        self.profile.write_text('# changed\n')
        with self.assertRaisesRegex(Exception,'changed after planning'):ps.engine.apply(plan)
        self.assertNotEqual(token,ps.description(self.plan())['token'])
        self.assertFalse((self.module_root/'blastoff'/ps.core.VERSION).exists())
    def test_encoding_missing_repair_no_profile_and_payload_immutability(self):
        self.profile.parent.mkdir(parents=True)
        original=b'\xff\xfe'+'# preserved ü\r\n'.encode('utf-16-le');self.profile.write_bytes(original)
        ps.engine.apply(self.plan())
        target=self.module_root/'blastoff'/ps.core.VERSION/'lib/preview.py';expected=target.read_bytes();target.unlink()
        ps.engine.apply(self.plan());self.assertEqual(target.read_bytes(),expected)
        with patch.object(ps,'payload',wraps=ps.payload) as payload:
            pending,root=payload(self.module_root/'blastoff');pending[target]=(b'different release',0o644);payload.return_value=(pending,root);payload.side_effect=lambda _: (pending,root)
            with self.assertRaisesRegex(Exception,'Immutable'):self.plan()
        ps.engine.apply(self.plan('uninstall'));self.assertEqual(self.profile.read_bytes(),original)
        self.context['profile_path']=None
        plan=self.plan();self.assertFalse(plan.profiles)
    def test_uninstall_plan_reports_lock_without_changes(self):
        ps.engine.apply(self.plan())
        lock=self.module_root/'blastoff/.blastoff/.install.lock'
        lock.write_text('another operation')
        before=self.tree()
        with self.assertRaisesRegex(Exception,'lock'):self.plan('uninstall')
        self.assertEqual(before,self.tree())

    def test_wrong_host_and_unowned_collision(self):
        self.context['host']='nt' if os.name=='posix' else 'posix'
        with self.assertRaisesRegex(Exception,'platform mismatch'):self.plan()
        self.context['host']=os.name
        self.write(self.module_root/'blastoff'/ps.core.VERSION/'lib/blastoff.py','unowned')
        before=self.tree()
        with self.assertRaisesRegex(Exception,'Unowned'):self.plan()
        self.assertEqual(before,self.tree())

    def test_frontends_own_independent_resources_and_profile(self):
        import shutil
        real_path=os.environ.get('PATH','')
        # The interpreter's sibling Bash is native on this POSIX test host.
        bash=Path(__import__('sys').executable).parent/'bash'
        if not bash.is_file(): self.skipTest('native Bash unavailable for coexistence fixture')
        self.context['profile_path']=str(self.home/'.config/powershell/profile.ps1')
        self.context['known_profiles']=[]
        ps.engine.apply(self.plan())
        prefix=self.home/'shell-prefix'
        with patch.object(ps.engine.shutil,'which',side_effect=lambda name: str(bash) if name=='bash' else None):
            shell=ps.engine.make_plan('install',prefix)
            ps.engine.apply(shell)
        shell_core=prefix/'share/blastoff/versions'/ps.core.VERSION/'lib/blastoff.py'
        module_core=self.module_root/'blastoff'/ps.core.VERSION/'lib/blastoff.py'
        self.assertIn(ps.core.VERSION,self.invoke('--version',entry=module_core).stdout)
        # Discover an independent managed profile without adopting it.
        with patch.object(ps.engine.integration.shutil,'which',side_effect=lambda name: '/unused/pwsh' if name=='pwsh' else None):
            _,profiles,record,notes,_=ps.integration.plan(ps.core,prefix,shell_core.parent.parent,None,'install',enabled=True)
        self.assertNotIn('powershell',record['profiles'])
        self.assertTrue(any('Independent CurrentUser' in note for note in notes))
        ps.engine.apply(self.plan('uninstall'))
        self.assertTrue(shell_core.is_file());self.assertIn(ps.core.VERSION,self.invoke('--version',entry=shell_core).stdout)
        ps.engine.apply(self.plan())
        ps.engine.apply(ps.engine.make_plan('uninstall',prefix))
        self.assertTrue(module_core.is_file());self.assertIn(ps.core.VERSION,self.invoke('--version',entry=module_core).stdout)


import shutil
import subprocess
import unittest
@unittest.skipUnless(shutil.which('pwsh'), 'pwsh unavailable; native lifecycle/session checks pending')
class NativePowerShellAdapters(unittest.TestCase):
    def test_command_parity(self):
        arguments=[shutil.which('pwsh'),'-NoProfile','-File',str(ROOT/'tests/parity.ps1')]
        if os.name != 'nt': arguments.append('-AllowNonWindows')
        result=subprocess.run(arguments,capture_output=True,text=True,timeout=240)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_fresh_session(self):
        result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(ROOT/'tests/powershell_session.ps1')],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_lifecycle_adapter(self):
        result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(ROOT/'tests/powershell_lifecycle.ps1')],capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stderr)
