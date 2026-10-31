#!/usr/bin/env python3
"""Isolated acceptance of profile inspection and source-only diagnostic traces."""
import argparse
from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import shutil
import signal
import re
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib/dots'))
from debug.fixtures import fixture
from debug.startup import one_run,finish_events,source_plan
from debug.inspect import cache_report,path_report,command_report
from profile_views import selected,validate,identities


class Diagnostics(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root,self.env,self.base=self.stack.enter_context(fixture(ROOT))
        self.stack.enter_context(patch.dict(os.environ,self.env,clear=True))
        for path in ROOT.glob('bin/dots-*'):
            if path.name.startswith(('dots-profile','dots-debug')):
                target=self.root/'bin'/path.name;shutil.copy2(path,target)
                if os.name!='nt':
                    # Termux fixtures intentionally omit the host's exec preload.
                    interpreter=Path(shutil.which('bash')).resolve()
                    target.write_text('#!'+str(interpreter)+'\n'+target.read_text().partition('\n')[2])

    def cli(self,*args,code=0,env=None):
        p=subprocess.run([sys.executable,'-B',str(self.root/'lib/dots/debug_cli.py'),*args],env=env or self.env,capture_output=True,text=True,timeout=45)
        self.assertEqual(p.returncode,code,p.stderr+p.stdout)
        return p

    def profiles(self,*args,code=0):
        p=subprocess.run([sys.executable,'-B',str(self.root/'lib/dots/profiles.py'),*args],env=self.env,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,code,p.stderr+p.stdout)
        return json.loads(p.stdout)

    def test_selected_context_and_parent_precedence(self):
        p=self.root/'profiles/linux/distros/demo';p.mkdir(parents=True)
        (p/'profile.json').write_text('{"schema":1,"id":"linux/demo","environment":{"EDITOR":"demo"}}')
        result=selected(self.root,'linux/demo')
        self.assertEqual([r['id'] for r in result['layers']],['linux','linux/demo'])
        self.assertTrue(result['inspection_only']);self.assertEqual(result['facts']['runtime'],'not evaluated')
        result=self.profiles('profile','layers','linux/demo','--json')
        self.assertEqual([r['id'] for r in result['rows']],['universal','linux','linux/demo'])

    def test_singular_list_and_check_scopes(self):
        listed=self.profiles('profile','list','--platform','windows','--json')
        self.assertEqual([row['id'] for row in listed['profiles']],['windows'])
        one=self.profiles('profile','check','windows','--json')
        self.assertEqual([row['profile'] for row in one['checks']],['windows'])
        all_profiles=self.profiles('profile','check','--all','--json')
        self.assertEqual({row['profile'] for row in all_profiles['checks']},{'termux','linux','wsl','windows'})
        for args in (['profiles','list'],['profile','check','windows','--all'],['profile','list','windows']):
            result=subprocess.run([sys.executable,'-B',str(self.root/'lib/dots/profiles.py'),*args],env=self.env,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)

    def test_inactive_errors_are_aggregated(self):
        for platform in ('linux','windows'):
            (self.root/'profiles'/platform/'profile.json').write_text('{bad')
        result=self.profiles('profile','check','--all','--json',code=1)
        self.assertEqual({r['profile'] for r in result['checks'] if r['status']=='failed'},{'linux','windows','wsl','termux'})

    def test_profile_environment_is_declarations_and_redacted(self):
        p=self.root/'profiles/linux/profile.json'
        p.write_text(json.dumps(dict(schema=1,id='linux',environment=dict(EDITOR='declared',API_KEY='secret-marker'))))
        result=self.profiles('profile','env','linux','--json')
        self.assertEqual(next(row for row in result['rows'] if row['name']=='EDITOR')['template'],'declared')
        self.assertEqual(next(row for row in result['rows'] if row['name']=='PROFILE')['template'],str(p.parent))
        self.assertNotIn('secret-marker',json.dumps(result))

    def test_path_scalar_and_existing_filters(self):
        p=subprocess.run([sys.executable,'-B',str(self.root/'lib/dots/profiles.py'),'profile','paths','linux','--kind','bin','--raw'],env=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always'),capture_output=True,text=True)
        self.assertEqual(p.stdout,str(self.root/'profiles/linux/bin')+'\n')
        result=self.profiles('profile','paths','linux','--kind','bin','--existing','--json')
        self.assertEqual(result['rows'],[])

    def test_static_plan_does_not_run_hooks_or_create_cache(self):
        secret=self.root/'secrets';secret.mkdir();(secret/'secrets.env').write_text('touch "$HOME/BAD"\n')
        before=list(Path(self.env['XDG_CACHE_HOME']).rglob('*'))
        result=json.loads(self.cli('startup','--shell','zsh','--json').stdout)
        self.assertEqual(result['mode'],'plan');self.assertFalse((Path(self.env['HOME'])/'BAD').exists())
        self.assertEqual(before,list(Path(self.env['XDG_CACHE_HOME']).rglob('*')))
        self.assertLess(result['modules'].index('shells/zsh/interactive.zsh'),result['modules'].index('shells/zsh/core/environment.zsh'))

    def test_path_shadow_and_route_nonexecution(self):
        dirs=[self.base/'first',self.base/'second']
        executable_name='demo.exe' if os.name=='nt' else 'demo'
        for d in dirs:
            d.mkdir();p=d/executable_name;p.write_text('DO NOT EXECUTE');p.chmod(0o755)
        with patch.dict(os.environ,PATH=os.pathsep.join(map(str,[*dirs,dirs[0]]))):
            report=path_report(self.root,executable_name)
        self.assertEqual(report['selected'],str(dirs[0]/executable_name));self.assertTrue(report['rows'][2]['duplicate'])
        result=command_report(self.root,['profile','paths','--kind','bin'])
        self.assertEqual(result['forwarded_count'],2);self.assertTrue(result['selected'].endswith('dots-profile-paths'))

    def test_cache_changes_without_sourcing_guard(self):
        executable=shutil.which('bash',path=self.env['PATH'])
        if not executable:self.skipTest('Bash unavailable')
        run=one_run(self.root,self.env,'bash',False,15,True,self.base)
        self.assertEqual(run['exit_code'],0)
        report=cache_report(self.root,'bash');self.assertEqual(report['rows'][0]['status'],'valid')
        source=self.root/'shells/shared/session.sh';source.write_text(source.read_text()+'\n# changed\n')
        self.assertEqual(cache_report(self.root,'bash')['rows'][0]['status'],'stale')
        self.assertIn('changed input:',str(cache_report(self.root,'bash')))

    def test_source_timings_nested_repeated_and_private_output(self):
        if not any(shutil.which(s,path=self.env['PATH']) for s in ('bash','zsh')): self.skipTest('POSIX shells unavailable')
        for shell in ('bash','zsh'):
            if not shutil.which(shell,path=self.env['PATH']):continue
            private=self.root/'secrets';private.mkdir(exist_ok=True)
            (private/'secrets.env').write_text('export FIXTURE_SECRET=NEVER_PRINT_THIS\nprintf NEVER_PRINT_THIS >&2\n')
            p=self.root/'profiles/termux/shells';p.mkdir(exist_ok=True)
            (p/('init.'+shell)).write_text('_dots_debug_event begin repeated source\nsleep 0.01\n_dots_debug_event begin nested source\nsleep 0.01\n_dots_debug_event end nested source 0\n_dots_debug_event end repeated source 0\n_dots_debug_event begin repeated source\n_dots_debug_event end repeated source 7\n')
            result=one_run(self.root,self.env,shell,False,15,True,self.base)
            self.assertEqual(result['exit_code'],0)
            self.assertNotIn('NEVER_PRINT_THIS',json.dumps(result));self.assertIsNotNone(result['startup_ms'])
            repeats=[r for r in result['events'] if r['name']=='repeated']
            self.assertEqual(len(repeats),2);self.assertGreater(repeats[0]['duration_ms'],10)
            self.assertEqual(repeats[1]['exit_status'],7)
            if shell=='zsh':self.assertTrue(any(r['kind']=='source-entry' for r in result['events']))

    @unittest.skipIf(os.name=='nt','POSIX shell fixture')
    def test_timeout_keeps_incomplete_events(self):
        (Path(self.env['HOME'])/'.bashrc').unlink()
        (Path(self.env['HOME'])/'.bashrc').write_text('source "$DOTS/lib/dots/shell/debug.bash"\n_dots_debug_event begin waiting phase\nsleep 10\n')
        result=one_run(self.root,self.env,'bash',False,0.2,True,self.base)
        self.assertEqual(result['exit_code'],124)
        self.assertTrue(any(r['name']=='waiting' and r['status']=='incomplete' for r in result['events']))

    @unittest.skipIf(os.name=='nt','POSIX shell fixture')
    def test_early_exit_and_invalid_execution_options(self):
        (Path(self.env['HOME'])/'.bashrc').unlink();(Path(self.env['HOME'])/'.bashrc').write_text('exit 7\n')
        result=one_run(self.root,self.env,'bash',False,5,True,self.base)
        self.assertEqual(result['status'],'failed');self.assertIsNone(result['startup_ms'])
        self.cli('startup','--shell','powershell','--login',code=2)
        self.cli('startup','--runs','21','--isolated',code=2)
        self.cli('startup','--live','--isolated',code=2)

    def test_powershell_events_when_available(self):
        if not (shutil.which('pwsh') or shutil.which('powershell')): self.skipTest('PowerShell engine unavailable')
        result=one_run(self.root,self.env,'powershell',False,30,True,self.base)
        self.assertEqual(result['exit_code'],0)
        self.assertTrue(any(e['kind']=='module' for e in result['events']))

    def test_report_boundaries_and_widths(self):
        from debug_cli import render
        from files.catalog import Presentation
        data=dict(version=1,checks=[dict(name='fixture\x1b[31m',status='failed',detail='a long path '+str(self.root))])
        for width in (40,80,120):
            out=io.StringIO()
            with patch('sys.stdout',out),patch('shutil.get_terminal_size',return_value=os.terminal_size((width,30))):render(data,'check')
            self.assertNotIn('\x1b',out.getvalue());self.assertTrue(all(len(line)<=width for line in out.getvalue().splitlines()))
        result=self.cli('check','--only','platform','--json',env=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')).stdout
        self.assertNotIn('\x1b',result);self.assertEqual(json.loads(result)['version'],1)

    def test_interruption_retains_trace(self):
        if os.name=='nt': self.skipTest('POSIX signal fixture')
        (Path(self.env['HOME'])/'.bashrc').unlink()
        (Path(self.env['HOME'])/'.bashrc').write_text('source "$DOTS/lib/dots/shell/debug.bash"\n_dots_debug_event begin waiting phase\ntouch "$HOME/started"\nsleep 10\n')
        code="import sys,os,json;from pathlib import Path;sys.path.insert(0,os.environ['DOTS']+'/lib/dots');from debug.startup import one_run;print(json.dumps(one_run(Path(os.environ['DOTS']),dict(os.environ),'bash',False,15,True,Path(os.environ['TMPDIR']))))"
        process=subprocess.Popen([sys.executable,'-B','-c',code],env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+5
            while not (Path(self.env['HOME'])/'started').exists() and time.monotonic()<deadline: time.sleep(0.02)
            process.send_signal(signal.SIGINT)
            output,error=process.communicate(timeout=5)
            self.assertEqual(json.loads(output)['exit_code'],130,error)
        finally:
            if process.poll() is None: process.kill();process.wait()

    @unittest.skipIf(os.name=='nt','POSIX PTY presentation fixture')
    def test_trace_views_in_owned_terminals(self):
        import pty, fcntl, termios, struct
        from resources import cells
        data=dict(version=1,mode='isolated',shell='zsh',runs=[dict(status='completed',checkout=str(self.root),startup_ms=12.5,process_ms=15,
             events=[dict(name=str(self.root/'shells/zsh/目录 long source.zsh'),kind='inlined',status='completed',duration_ms=10.1,offset_ms=1,depth=1),
                     dict(name='unsafe\x1b[31m',kind='phase',status='incomplete',duration_ms=None,offset_ms=12,depth=0)])],
             summary=dict(median_ms=12.5,min_ms=12.5,max_ms=12.5))
        code="import sys,json;from pathlib import Path;sys.path.insert(0,str(Path.cwd()/'lib/dots'));from debug_cli import render;render(json.load(sys.stdin),'startup')"
        for width in (40,80,120):
            for mode in ('always','never'):
                master,slave=pty.openpty()
                try:
                    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,width,0,0))
                    process=subprocess.Popen([sys.executable,'-B','-c',code],cwd=self.root,env=dict(self.env,DOTS_COLOR=mode,DOTS_ICONS=mode,COLUMNS=str(width)),stdin=subprocess.PIPE,stdout=slave,stderr=slave)
                    os.close(slave);slave=None
                    process.stdin.write(json.dumps(data).encode());process.stdin.close()
                    output=b''
                    while True:
                        try: chunk=os.read(master,65536)
                        except OSError: break
                        if not chunk: break
                        output+=chunk
                    self.assertEqual(process.wait(timeout=5),0)
                    text=output.decode();plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                    self.assertIn('incomplete',plain);self.assertIn('unsafe\\x1b',plain)
                    self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
                    if mode=='never': self.assertNotIn('\x1b',text)
                finally:
                    os.close(master)
                    if slave is not None: os.close(slave)

    def test_native_routes_and_profile_completion(self):
        env=dict(self.env,PATH=self.env['PATH']+os.pathsep+str(Path(sys.executable).parent))
        args=[sys.executable,'-B',str(self.root/'lib/dots/cli.py')]
        p=subprocess.run([*args,'profile','show','linux','--json'],env=env,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['current'],'linux')
        p=subprocess.run([*args,'debug','check','--only','platform','--json'],env=env,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        from command_metadata import read
        self.assertEqual(read(self.root/'bin/dots-profile-show')['argument'][0][1],'profile-id')
        commands=[[*args,'__complete','profile','show','']]
        if os.name!='nt': commands.append([str(self.root/'bin/dots'),'__complete','bash','3','--','dots','profile','show',''])
        for command in commands:
            p=subprocess.run(command,env=env,text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('termux',p.stdout)
        frontends=[args]
        if os.name!='nt': frontends.append([str(self.root/'bin/dots')])
        views=[]
        for frontend in frontends:
            p=subprocess.run([*frontend,'debug'],env=env,text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('startup',p.stdout);views.append(p.stdout)
            p=subprocess.run([*frontend,'debug','not-a-route'],env=env,text=True,capture_output=True)
            self.assertEqual(p.returncode,2,p.stderr)
        self.assertTrue(all(view==views[0] for view in views))
        result=command_report(self.root,['profile','show','PRIVATE_ARGUMENT_VALUE'])
        self.assertNotIn('PRIVATE_ARGUMENT_VALUE',json.dumps(result))

    def test_debug_detail_and_record_completion_parity(self):
        env=dict(self.env,PATH=self.env['PATH']+os.pathsep+str(Path(sys.executable).parent))
        native=[sys.executable,'-B',str(self.root/'lib/dots/cli.py')]
        for words,expected in ((['debug','startup','--detail',''],{'files','changes','deep'}),
                               (['debug','startup','--view',''],{'tree','sequence','summary','slowest'}),
                               (['debug','record',''],{'start','stop','status'}),
                               (['debug','startup','--'],{'--changes','--file','--name','--show-values','--depth','--limit','--min-ms'})):
            commands=[[*native,'__complete',*words]]
            if os.name!='nt':commands.append([str(self.root/'bin/dots'),'__complete','bash',str(len(words)),'--','dots',*words])
            for command in commands:
                result=subprocess.run(command,env=env,text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
                candidates={line.split('\t')[1] if line.startswith('candidate\t') else line for line in result.stdout.splitlines()}
                self.assertTrue(expected<=candidates,result.stdout)


if __name__=='__main__':unittest.main()
