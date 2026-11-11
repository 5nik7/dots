"""Default-no npm approvals, exact targets, metadata drift and terminal safety."""
import contextlib
import io
import json
import os
import re
import sys
import unittest
from unittest.mock import Mock, patch

import test_workflows as fixtures
from pkgs_lib import npm_scripts, streams, upgrade_output, workflows
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error

SPEC = '@scope/tool@1.2.3'


class NpmScripts(unittest.TestCase):
    setUp = fixtures.Workflows.setUp

    def pending(self):
        output=upgrade_output.Output('npm',self.cfg)
        output.begin(['npm','install','--global','--','@scope/tool'])
        fmt=streams.Formatter(io.StringIO(),dict(self.cfg,_manager='npm'),output)
        fmt.feed(b'npm warn install-scripts 1 package had install scripts blocked because they are not covered by allowScripts:\n')
        fmt.feed(('npm warn install-scripts   '+SPEC+' (postinstall: node private-script.js)\n').encode())
        fmt.feed(b'npm warn install-scripts\nnpm warn install-scripts Run `npm install -g --allow-scripts=@scope/tool` to allow these scripts once\n',final=True)
        return output

    def item(self):
        return workflows.Plan(Backend('npm',True),'upgrade',['@scope/tool'],[['npm','install','--global','--','@scope/tool']])

    def test_explicit_approval_runs_only_exact_version_without_persisting(self):
        output=self.pending(); item=self.item()
        out=io.StringIO()
        def rebuilt(*args,**kwargs):
            output.line('npm warn rebuild 2 packages had install scripts blocked because they are not covered by allowScripts. Review other packages.', '\n',sys.stderr)
            output.pending.observe('npm info run '+SPEC+' postinstall { code: 0, signal: null }')
            return 0
        with patch.object(npm_scripts,'terminal',return_value=True), \
             patch.object(npm_scripts,'evidence',return_value={SPEC:['metadata']}) as evidence, \
             patch.object(npm_scripts,'approve',return_value=True) as approve, \
             patch.object(streams,'run',side_effect=rebuilt) as run, contextlib.redirect_stdout(out):
            self.assertEqual(output.pending.review(item,self.cfg,output,0),0)
            output.result(0)
        self.assertEqual(evidence.call_count,2)
        approve.assert_called_once_with(SPEC)
        self.assertEqual(run.call_args.args[0],['npm','rebuild','--global','--loglevel=info','--allow-scripts=@scope/tool','--',SPEC])
        self.assertIn('Scripts ran: '+SPEC,out.getvalue())
        self.assertNotIn('private-script',out.getvalue())
        self.assertEqual(output.warnings,[]); self.assertEqual(output.extra,0)

    def test_decline_nonterminal_and_native_failure_do_not_execute_scripts(self):
        for tty, answer, status in ((True,False,0),(False,True,0),(True,True,7)):
            output=self.pending()
            with patch.object(npm_scripts,'terminal',return_value=tty), \
                 patch.object(npm_scripts,'evidence',return_value={}) as evidence, \
                 patch.object(npm_scripts,'approve',return_value=answer) as approve, \
                 patch.object(streams,'run') as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(output.pending.review(self.item(),self.cfg,output,status),status)
            run.assert_not_called()
            self.assertEqual(approve.call_count,int(tty and not status))
            self.assertEqual(evidence.call_count,int(tty and not status))

    def test_drift_and_script_failure_keep_failure_visible(self):
        for drift in (True,False):
            output=self.pending(); err=io.StringIO()
            with patch.object(npm_scripts,'terminal',return_value=True), \
                 patch.object(npm_scripts,'approve',return_value=True), \
                 patch.object(npm_scripts,'evidence',side_effect=[{'x':1},{'x':2 if drift else 1}]), \
                 patch.object(streams,'run',return_value=8) as run, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),1 if drift else 8)
                output.result(1)
            self.assertEqual(run.call_count,0 if drift else 1)
            if drift: self.assertIn('metadata changed',err.getvalue())
            self.assertEqual(output.pending.ran,[])

    def test_success_without_native_script_evidence_is_not_claimed_as_run(self):
        output=self.pending()
        with patch.object(npm_scripts,'terminal',return_value=True), \
             patch.object(npm_scripts,'approve',return_value=True), \
             patch.object(npm_scripts,'evidence',return_value={}), \
             patch.object(streams,'run',return_value=0), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),1)
        self.assertEqual(output.pending.ran,[])
        self.assertIn('did not confirm',output.errors[0])

    def test_project_custom_scope_unrecognized_and_incomplete_output_never_approve(self):
        recipe=npm_scripts.Pending()
        recipe.begin(['npm','install','-g','--force','@scope/tool'])
        self.assertTrue(recipe.enabled)
        for command in (['npm','install','--','tool'],['custom','install','--global'],
                        ['npm','install','--global','--prefix=/elsewhere','--','tool']):
            output=self.pending();output.pending=npm_scripts.Pending();output.begin(command)
            output.line('npm warn install-scripts   '+SPEC+' (postinstall: node x)','\n',io.StringIO())
            self.assertEqual(output.pending.specs,set())
            self.assertTrue(output.warnings)
        output=self.pending()
        output.line('npm warn install-scripts 2 packages had install scripts blocked because they are not covered by allowScripts:','\n',io.StringIO())
        output.line('npm warn install-scripts evil@1.0.0;touch /tmp/no','\n',io.StringIO())
        with patch.object(npm_scripts,'approve') as approve:
            self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),0)
        approve.assert_not_called(); self.assertTrue(output.pending.invalid)

    def test_inventory_requires_registry_identity_and_catches_script_changes(self):
        row=dict(name='@scope/tool',version='1.2.3',resolved='https://registry.invalid/tool-1.2.3.tgz',
                 path=str(self.home/'node_modules/@scope/tool'),scripts={'postinstall':'node x'})
        def inventory(): return Mock(returncode=0,stdout=json.dumps({'dependencies':{'@scope/tool':row}}))
        with patch.object(npm_scripts,'query',side_effect=lambda *a,**k:inventory()) as query:
            before=npm_scripts.evidence([SPEC]);row['scripts']['postinstall']='node y'
            self.assertNotEqual(before,npm_scripts.evidence([SPEC]))
            for field,value in (('resolved','file:/tmp/source'),('link',True),('version','2.0.0')):
                original=row.get(field);row[field]=value
                with self.assertRaises(Error):npm_scripts.evidence([SPEC])
                if original is None:row.pop(field)
                else:row[field]=original
        self.assertEqual(query.call_args.args[0][-2:],['--',SPEC])

    @unittest.skipIf(os.name=='nt','private POSIX controlling terminal')
    def test_real_terminal_yes_no_eof_and_no_yes_bypass_at_narrow_widths(self):
        import pty, select, time, fcntl, struct, termios
        for width,answer in ((40,b'n\n'),(80,b'y\n'),(120,b'\x04')):
            pid,fd=pty.fork()
            if pid==0:
                try:
                    # No Gum in the isolated fixture PATH; exercise the fallback.
                    os.environ['TERM']='dumb'
                    print('APPROVED='+str(npm_scripts.approve(SPEC)),flush=True)
                    os._exit(0)
                except BaseException:os._exit(1)
            fcntl.ioctl(fd,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
            data=b'';sent=False;status=None;done=0
            try:
                deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    ready,_,_=select.select([fd],[],[],.1)
                    if ready:
                        try:chunk=os.read(fd,4096)
                        except OSError:break
                        data+=chunk
                        if b'[y/N]' in data and not sent:os.write(fd,answer);sent=True
                    done,status=os.waitpid(pid,os.WNOHANG)
                    if done:break
                if not done:
                    done,status=os.waitpid(pid,os.WNOHANG)
                    if not done:
                        import signal
                        os.kill(pid,signal.SIGKILL);_,status=os.waitpid(pid,0)
                self.assertEqual(os.waitstatus_to_exitcode(status),0,data)
                self.assertIn(b'APPROVED='+str(answer==b'y\n').encode(),data)
            finally:os.close(fd)

    @unittest.skipIf(os.name=='nt','private POSIX controlling terminal')
    def test_cli_yes_flag_still_prompts_and_rebuild_status_propagates(self):
        import pty,select,time,signal,termios
        from pkgs_lib import cli
        fake=self.bin/'npm'
        fake.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
args=sys.argv[1:]
with open(os.environ['TEST_CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
if args[0]=='ls':
    print(json.dumps({'dependencies':{'@scope/tool':{'name':'@scope/tool','version':'1.2.3',
        'path':os.environ['TEST_DB'],'scripts':{'postinstall':'node fixture.js'}}}}))
elif args[0]=='install':
    print('npm warn install-scripts 1 package had install scripts blocked because they are not covered by allowScripts:',file=sys.stderr)
    print('npm warn install-scripts   @scope/tool@1.2.3 (postinstall: node fixture.js)',file=sys.stderr)
elif args[0]=='rebuild':
    code=int(os.environ.get('TEST_SCRIPT_EXIT','0'))
    if code:print('npm error fixture script failed',file=sys.stderr)
    else:print('npm info run @scope/tool@1.2.3 postinstall { code: 0, signal: null }',file=sys.stderr)
    sys.exit(code)
else:sys.exit(99)
''');fake.chmod(0o755)
        for answer,script_code,expected in ((b'n\n',0,0),(b'y\n',0,0),(b'y\n',9,9),(b'\x03',0,130)):
            (self.home/'calls.jsonl').write_text('')
            pid,fd=pty.fork()
            if pid==0:
                os.environ.update(TERM='dumb',TEST_SCRIPT_EXIT=str(script_code))
                before=termios.tcgetattr(0)
                code=cli.main(['up','--manager','npm','--global','@scope/tool','--yes'])
                assert before==termios.tcgetattr(0)
                sys.stdout.flush();sys.stderr.flush();os._exit(code)
            data=b'';sent=False;status=None
            try:
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    if select.select([fd],[],[],.05)[0]:
                        try:chunk=os.read(fd,65536)
                        except OSError:break
                        if not chunk:break
                        data+=chunk
                        if b'[y/N]' in data and not sent:os.write(fd,answer);sent=True
                    ended,state=os.waitpid(pid,os.WNOHANG)
                    if ended:status=state;break
                if status is None:
                    ended,status=os.waitpid(pid,os.WNOHANG)
                    if not ended:os.kill(pid,signal.SIGKILL);status=os.waitpid(pid,0)[1]
                self.assertEqual(os.waitstatus_to_exitcode(status),expected,data)
                self.assertTrue(sent,data)
                calls=[json.loads(line) for line in (self.home/'calls.jsonl').read_text().splitlines()]
                self.assertEqual(any(c[0]=='rebuild' for c in calls),answer==b'y\n')
                if answer==b'y\n' and not script_code:self.assertIn(b'Scripts ran',data)
                else:self.assertNotIn(b'Scripts ran',data)
            finally:os.close(fd)


if __name__=='__main__':unittest.main()
