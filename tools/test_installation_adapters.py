#!/usr/bin/env python3
"""Native entry-point and presentation checks in disposable roots."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which('pwsh') or (shutil.which('powershell') if os.name == 'nt' else None)


class Adapters(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='dots adapters ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.home=self.base/'home'
        self.repo=self.base/'repo'
        self.home.mkdir()
        self.repo.mkdir()
        shutil.copytree(ROOT/'lib/dots/files',self.repo/'lib/dots/files')
        for name in ('progress.py','interaction.py','ui.bash','ui.ps1','bootstrap-ui.sh',
                     'resources.py','resources.bash','resources.tsv',
                     'dispatch.bash','catalog.bash','complete.bash','init.bash'):
            shutil.copy2(ROOT/'lib/dots'/name,self.repo/'lib/dots'/name)
        shutil.copytree(ROOT/'lib/dots/shell',self.repo/'lib/dots/shell')
        (self.repo/'bin').mkdir()
        for name in ('dots','dots.ps1','dots-files-install','dots-files-uninstall','dots-files-check','dots-files-stash','dots-files-edit'):
            shutil.copy2(ROOT/'bin'/name,self.repo/'bin'/name)
        for name in ('install.sh','uninstall.sh','install.ps1','uninstall.ps1'):
            shutil.copy2(ROOT/name,self.repo/name)
        (self.repo/'.dots').mkdir()
        (self.repo/'settings').write_text('fixture settings\n')
        platforms=['termux','linux','wsl','windows']
        (self.repo/'.dots/sources.json').write_text(json.dumps(dict(schema=1,sources=[dict(id='dots',path='.',roots=['.'],platforms=platforms)])))
        (self.repo/'.dots/files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[dict(id='example',app='example',category='config',source='settings',target='${CONFIG}/example/settings',strategy='link',platforms=platforms)])))
        self.env=dict(os.environ,HOME=str(self.home),USERPROFILE=str(self.home),DOTS=str(self.repo),
                      XDG_CONFIG_HOME=str(self.home/'.config'),XDG_STATE_HOME=str(self.home/'.state'),
                      XDG_CACHE_HOME=str(self.home/'.cache'),XDG_DATA_HOME=str(self.home/'.data'),
                      APPDATA=str(self.home/'Roaming'),LOCALAPPDATA=str(self.home/'Local'),
                      CODEX_HOME=str(self.home/'.codex'),PI_CODING_AGENT_DIR=str(self.home/'.pi'),
                      DOTS_COLOR='never',DOTS_ICONS='never',TERM='xterm-256color')

    def run_command(self, argv, ok=True, **env):
        result=subprocess.run(list(map(str,argv)),env=dict(self.env,**env),capture_output=True,text=True,timeout=30)
        if ok:self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
        else:self.assertNotEqual(result.returncode,0)
        return result

    @unittest.skipIf(os.name=='nt','POSIX shell entry points')
    def test_shell_entry_points_and_setup_routing(self):
        for cmd in ([self.repo/'install.sh'],[self.repo/'bin/dots','init','--setup'],[self.repo/'bin/dots','files','install']):
            doc=json.loads(self.run_command([*cmd,'--dry-run','--json']).stdout)
            self.assertEqual(doc['action'],'install')
        self.assertFalse(list(self.home.iterdir()))
        self.run_command([self.repo/'install.sh','--yes'])
        self.run_command([self.repo/'uninstall.sh','--yes'])
        self.assertFalse((self.home/'.config/example/settings').exists())

    @unittest.skipIf(os.name=='nt','Bash hook generation')
    def test_hook_bytes_and_setup_completion(self):
        cmd=[self.repo/'bin/dots']
        before=self.run_command([*cmd,'init','bash']).stdout
        after=self.run_command([*cmd,'--color=always','--icons=always','init','bash']).stdout
        self.assertEqual(before,after)
        self.assertNotIn('\x1b',after)
        out=self.run_command([*cmd,'__complete','bash','3','--','dots','init','--setup','']).stdout
        self.assertIn('--dry-run',out)
        self.assertIn('--with-source',out)
        self.assertFalse(list(self.home.iterdir()))

    def test_help_json_and_plain_presentation(self):
        cmd=[sys.executable,'-B',self.repo/'lib/dots/files/install.py','install']
        help_out=self.run_command([*cmd,'--help','--color=always']).stdout
        self.assertIn('\x1b[',help_out)
        self.assertIn('--dry-run',help_out)
        for width in ('40','80','120'):
            result=self.run_command([*cmd,'--dry-run','--color=always'],COLUMNS=width)
            self.assertIn('\x1b[95m',result.stdout)
            self.assertNotIn('\r',result.stderr)
            self.assertIn('No changes made.',result.stdout)
        result=self.run_command([*cmd,'--dry-run','--json','--color=always','--icons=always'])
        json.loads(result.stdout)
        self.assertNotIn('\x1b',result.stdout+result.stderr)
        result=self.run_command([*cmd,'--dry-run'],NO_COLOR='1')
        self.assertNotIn('\x1b',result.stdout+result.stderr)
        self.assertFalse(list(self.home.iterdir()))

    def test_native_target_mapping_and_missing_profile(self):
        path=self.repo/'.dots/files.json'
        doc=json.loads(path.read_text())
        doc['resources'][0]['targets']={'windows':'${APPDATA}/Code/User/settings.json'}
        doc['resources'].append(dict(id='profile',app='powershell',category='shell',source='settings',
                                    target='${POWERSHELL_PROFILE}',strategy='link',platforms=['windows']))
        path.write_text(json.dumps(doc))
        cmd=[sys.executable,'-B',self.repo/'lib/dots/files/catalog.py','list','--platform','windows','--json']
        out=json.loads(self.run_command(cmd,DOTS_POWERSHELL_PROFILE='').stdout)
        rows={r['id']:r for r in out['resources']}
        self.assertEqual(Path(rows['dots:example']['target']),self.home/'Roaming/Code/User/settings.json')
        self.assertIsNone(rows['dots:profile']['target'])
        profile=self.home/'Documents/profile.ps1'
        out=json.loads(self.run_command(cmd,DOTS_POWERSHELL_PROFILE=str(profile)).stdout)
        self.assertEqual(Path(next(r for r in out['resources'] if r['id']=='dots:profile')['target']),profile)
        self.assertFalse(list(self.home.iterdir()))

    @unittest.skipUnless(PWSH, 'PowerShell unavailable; native check route not verified')
    def test_native_catalog_check(self):
        (self.repo/'settings').unlink()
        cmd=[PWSH,'-NoProfile','-File',str(self.repo/'bin/dots.ps1'),'files','check']
        preview=json.loads(self.run_command([*cmd,'--dry-run','--json']).stdout)
        self.assertEqual(preview['counts']['eligible'],1)
        result=json.loads(self.run_command([*cmd,'--yes','--json']).stdout)
        self.assertEqual(result['counts']['removed'],1)
        self.assertEqual(json.loads((self.repo/'.dots/files.json').read_text())['resources'],[])

    @unittest.skipUnless(PWSH, 'PowerShell unavailable; native mapping routes not verified')
    def test_native_mapping_routes(self):
        cmd=[PWSH,'-NoProfile','-File',str(self.repo/'bin/dots.ps1'),'files']
        preview=json.loads(self.run_command([*cmd,'stash','dots:example','--dry-run','--json']).stdout)
        self.assertEqual(preview['status'],'preview')
        self.run_command([*cmd,'stash','dots:example','--yes'])
        self.run_command([*cmd,'edit','dots:example','--target','${CONFIG}/new','--yes'])
        row=json.loads((self.repo/'.dots/files.json').read_text())['resources'][0]
        self.assertFalse(row['enabled'])
        self.assertEqual(row['target'],'${CONFIG}/new')

    @unittest.skipIf(os.name=='nt','POSIX owned terminal')
    def test_owned_terminal_progress_and_widths(self):
        import pty
        import fcntl
        import struct
        import termios
        import re
        code='''import sys,time
sys.path.insert(0,sys.argv[1])
import install
original=install.Installation.plan_install
def slow(self):
    original(self)
    time.sleep(0.7)
install.Installation.plan_install=slow
sys.exit(install.main(['install','--yes']))
'''
        for width in (40,80,120):
            master,slave=pty.openpty()
            try:
                fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                proc=subprocess.Popen([sys.executable,'-B','-c',code,str(self.repo/'lib/dots/files')],
                                      stdin=slave,stdout=slave,stderr=slave,
                                      env=dict(self.env,DOTS_COLOR='always',DOTS_PROGRESS='auto',COLUMNS=str(width)))
                os.close(slave);slave=None
                chunks=[]
                while True:
                    try:
                        block=os.read(master,65536)
                    except OSError:break
                    if not block:break
                    chunks.append(block)
                self.assertEqual(proc.wait(timeout=20),0)
                output=b''.join(chunks).decode(errors='replace')
                self.assertIn('Planning install',output)
                self.assertIn('\x1b[96m',output)
                plain=re.sub(r'\x1b\[[0-9;]*m','',output)
                self.assertIn('Dots install',plain)
                self.assertIn('Completed.',plain)
                self.assertNotIn('\x1b[?25l',output)
            finally:
                os.close(master)
                if slave is not None:os.close(slave)

    @unittest.skipUnless(PWSH,'PowerShell unavailable')
    def test_native_powershell_wrappers(self):
        def quote(path):return "'"+str(path).replace("'","''")+"'"
        # Override the host profile explicitly; never inspect the runner's profile.
        prefix="$PROFILE = "+quote(self.home/'profile.ps1')+"; $PROFILE | Add-Member -NotePropertyName CurrentUserCurrentHost -NotePropertyValue $PROFILE -Force; "
        for script,args in [('install.ps1','-DryRun -Json'),('uninstall.ps1','-DryRun -Json'),('bin/dots.ps1','init --setup --dry-run --json')]:
            out=self.run_command([PWSH,'-NoProfile','-NonInteractive','-Command',prefix+'& '+quote(self.repo/script)+' '+args+'; exit $LASTEXITCODE'])
            json.loads(out.stdout)
        self.assertFalse(list(self.home.iterdir()))

    @unittest.skipUnless(os.name=='nt','Native Windows capability check')
    def test_native_windows_link_or_explicit_refusal(self):
        cmd=[sys.executable,'-B',self.repo/'lib/dots/files/install.py','install','--yes','--json']
        result=subprocess.run(list(map(str,cmd)),env=self.env,capture_output=True,text=True)
        target=self.home/'.config/example/settings'
        if result.returncode:
            self.assertIn('symbolic links unavailable',result.stderr)
            self.assertFalse(target.exists())
            self.assertFalse((self.home/'.state/dots/installation.json').exists())
        else:
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.read_text(),'fixture settings\n')
            self.run_command([sys.executable,'-B',self.repo/'lib/dots/files/install.py','uninstall','--yes'])
            self.assertFalse(target.exists())


if __name__=='__main__':
    unittest.main(verbosity=2)
