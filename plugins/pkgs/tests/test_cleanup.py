"""Cleanup review, current ownership, cancellation and drift acceptance."""
import contextlib
import io
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_workflows as fixtures
from pkgs_lib import cleanup, manifests, scopes, workflows
from pkgs_lib.common import Error, Package
from pkgs_lib.backends import Backend


class Cleanup(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    args = fixtures.Workflows.args

    def data(self):
        return dict(schema=1,groups=[dict(manager='pip',scope='base',platforms=['termux','linux','wsl'],packages=[
            dict(name='source',enabled=False,reason=cleanup.REASON),
            dict(name='system',enabled=False,reason=cleanup.REASON),
            dict(name='other',enabled=False,reason='not proven pip-owned'),
            dict(name='enabled',enabled=True,reason=cleanup.REASON)])])

    def metadata(self, name='source', **extra):
        root = self.home/(name+'.dist-info'); root.mkdir(exist_ok=True)
        (root/'METADATA').write_text('Name: '+name+'\nVersion: 1.0\n')
        return dict(metadata=dict(name=name,version='1.0'),installer='pip',metadata_location=str(root),
                    direct_url=dict(url='file:///source'),**extra)

    def proof(self):
        return {'source':dict(name='source',version='1.0',reason='',proof='unchanged'),
                'system':dict(name='system',version='1.0',reason='owned by the system package manager',proof='system')}

    def test_provenance_requires_pip_source_and_negative_system_ownership(self):
        items = [self.metadata(n) for n in ('source','system','unknown','changed','foreign')]
        items[3].pop('direct_url'); items[4]['installer']='apt'
        def owners(paths):
            return {p:'apt-owned' if 'system.dist-info' in p else None if 'unknown.dist-info' in p else '' for p in paths}
        with patch.object(cleanup,'query',return_value=subprocess.CompletedProcess([],0,json.dumps(dict(version='1',installed=items)),'')), \
             patch.object(cleanup,'default_manager',return_value='apt'), patch.object(Backend,'owners',side_effect=owners):
            rows = cleanup.provenance()
            self.assertEqual(rows['source']['reason'],'')
            for name in ('system','unknown','changed','foreign'): self.assertTrue(rows[name]['reason'],name)
            before = rows['source']['proof']
            (Path(items[0]['metadata_location'])/'METADATA').write_text('changed')
            self.assertNotEqual(cleanup.provenance()['source']['proof'],before)
        self.assertNotIn('file:',json.dumps(rows))

    def test_only_exact_disabled_reason_and_current_scope_can_be_selected(self):
        document=manifests.validate(self.data())
        with patch.object(cleanup,'provenance',return_value=self.proof()), patch.object(manifests,'platform',return_value='termux'):
            backend,rows,proofs = cleanup.inspect(document)
        self.assertEqual([r['name'] for r in rows],['source','system'])
        self.assertEqual(list(proofs),['source'])
        with patch.object(cleanup,'provenance',side_effect=AssertionError('wrong scope')), \
             patch.object(scopes,'scope_id',return_value='venv'):
            self.assertTrue(all(not r['eligible'] for r in cleanup.inspect(document)[1]))

    def invoke_cleanup(self, *options, pick=None, confirm=True, changed=False, mutate=None, apply_rc=0):
        path = self.home/'-packages ü.json';path.write_text(json.dumps(self.data()))
        args = self.args('cleanup',str(path),*options)
        proofs = self.proof()
        output = io.StringIO()
        def approve(*args):
            if mutate: mutate(path)
            return confirm
        selected = [Package('source')] if pick is None else pick
        next_proof = {**proofs,'source':{**proofs['source'],'proof':'changed'}} if changed else proofs
        with contextlib.redirect_stdout(output), patch.object(cleanup,'terminal'), \
             patch.object(cleanup,'provenance',side_effect=[proofs,next_proof]), \
             patch('pkgs_lib.ui.pick',return_value=selected) as picker, \
             patch.object(workflows,'confirm',side_effect=approve) as confirmation, \
             patch.object(Backend,'installed',side_effect=[[Package('source')],[]]), \
             patch.object(workflows,'apply',return_value=apply_rc) as apply:
            try: rc = cleanup.cli(args,self.cfg)
            except Error as error: rc = error
        return rc,output.getvalue(),picker,confirmation,apply,path

    def test_preview_and_json_never_select_confirm_or_remove(self):
        for flag in ('--dry-run','--json'):
            rc,text,picker,confirm,apply,path = self.invoke_cleanup(flag)
            self.assertEqual(rc,0,text)
            picker.assert_not_called();confirm.assert_not_called();apply.assert_not_called()
            if flag=='--json': self.assertEqual(json.loads(text)['packages'][0]['name'],'source')

    def test_cancel_selection_and_decline_confirmation_leave_manifest(self):
        for options in (dict(pick=[]),dict(confirm=False)):
            rc,text,picker,confirm,apply,path = self.invoke_cleanup(**options)
            self.assertEqual(rc,0);apply.assert_not_called()
            self.assertEqual(json.loads(path.read_text()),self.data())
            self.assertIn('Cancelled',text)

    def test_accepted_selection_runs_only_reviewed_native_uninstall_and_retains_manifest(self):
        rc,text,picker,confirm,apply,path = self.invoke_cleanup()
        self.assertEqual(rc,0,text);confirm.assert_called_once_with()
        plan = apply.call_args.args[0]
        self.assertEqual(plan.names,['source'])
        self.assertEqual(plan.commands,[[sys.executable,'-m','pip','uninstall','-y','source']])
        self.assertEqual(json.loads(path.read_text()),self.data())
        self.assertIn('Removed 1 package(s)',text)

    def test_stale_manifest_provenance_and_invalid_selection_refuse_removal(self):
        for options in (dict(changed=True),dict(mutate=lambda p:p.write_text('{}')),dict(pick=[Package('system')])):
            rc,text,picker,confirm,apply,path = self.invoke_cleanup(**options)
            self.assertIsInstance(rc,Error);apply.assert_not_called()

    def test_native_failure_is_not_reported_as_removed(self):
        rc,text,picker,confirm,apply,path = self.invoke_cleanup(apply_rc=42)
        self.assertEqual(rc,42);self.assertNotIn('Removed 1',text)

    def test_yes_cannot_bypass_cleanup_and_default_path_is_profile_owned(self):
        with self.assertRaisesRegex(Error,'cannot bypass'):
            cleanup.cli(self.args('cleanup','--yes'),self.cfg)
        path=self.home/'profile/packages.json';path.parent.mkdir();path.write_text(json.dumps(dict(schema=1,groups=[])))
        with patch.object(manifests,'default_path',return_value=path), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cleanup.cli(self.args('cleanup','--json'),self.cfg),0)
        self.assertEqual(json.loads(output.getvalue())['manifest'],str(path))

    @unittest.skipUnless(os.name=='posix','private terminal requires POSIX')
    def test_cli_picker_confirm_and_native_uninstall_with_owned_fake_pip(self):
        import pty
        path=self.home/'packages.json';path.write_text(json.dumps(self.data()))
        record=self.metadata()
        module=self.home/'modules/pip';module.mkdir(parents=True)
        (module/'__init__.py').write_text('')
        (module/'__main__.py').write_text('''import json,os,sys
from pathlib import Path
db=Path(os.environ['TEST_DB']);data=json.loads(db.read_text());args=sys.argv[1:]
if args[0]=='inspect':print(json.dumps(dict(version='1',installed=data)))
elif args[0]=='list':print(json.dumps([p['metadata'] for p in data]))
elif args==['uninstall','-y','source']:
    db.write_text('[]');print('Successfully uninstalled source')
else:sys.exit(99)
''')
        for name in ('apt','apt-cache','bash','dpkg-query','fzf'):
            executable=self.bin/name
            executable.write_text('#!'+sys.executable+'\n'+'''import os,sys
name=os.path.basename(sys.argv[0])
if name=='dpkg-query':
    for path in sys.argv[sys.argv.index('--')+1:]:print('dpkg-query: no path found matching pattern '+path,file=sys.stderr)
    sys.exit(1)
if name=='fzf':
    if '--version' in sys.argv:print('0.74.5');sys.exit(0)
    if os.environ.get('TEST_CANCEL'):sys.exit(130)
    print(sys.stdin.read().splitlines()[0])
''');executable.chmod(0o755)
        env=dict(self.env,PYTHONPATH=str(module.parent),TERMUX_APP_PACKAGE_MANAGER='apt',
                 FZF_DEFAULT_OPTS='',FZF_DEFAULT_OPTS_FILE='',DOTS_PROGRESS='never')
        for cancelled,answer,removed in ((True,b'y\n',False),(False,b'n\n',False),(False,b'y\n',True)):
            (self.home/'db.json').write_text(json.dumps([record]))
            childenv=dict(env,TEST_CANCEL='1' if cancelled else '')
            pid,fd=pty.fork()
            if pid==0:
                os.execve(sys.executable,[sys.executable,'-B',str(fixtures.APP/'main.py'),'cleanup',str(path)],childenv)
            data=b'';sent=False;deadline=time.monotonic()+15
            try:
                while time.monotonic()<deadline:
                    if select.select([fd],[],[],.1)[0]:
                        try: chunk=os.read(fd,4096)
                        except OSError: break
                        if not chunk:break
                        data+=chunk
                        if b'Proceed?' in data and not sent:os.write(fd,answer);sent=True
                finished,status=os.waitpid(pid,os.WNOHANG)
                if not finished:
                    # The terminal can close just before waitpid observes exit.
                    for _ in range(20):
                        time.sleep(.01);finished,status=os.waitpid(pid,os.WNOHANG)
                        if finished:break
                self.assertTrue(finished,data.decode(errors='replace'))
                if finished:pid=0
                self.assertEqual(os.waitstatus_to_exitcode(status),0,data.decode(errors='replace'))
                self.assertEqual(json.loads((self.home/'db.json').read_text())==[],removed,data.decode(errors='replace'))
                self.assertEqual(json.loads(path.read_text()),self.data())
                self.assertTrue((Path(record['metadata_location'])/'METADATA').is_file())
            finally:
                os.close(fd)
                if pid:
                    try:os.kill(pid,9)
                    except ProcessLookupError:pass
                    os.waitpid(pid,0)

    @unittest.skipUnless(os.name=='posix','private terminal requires POSIX')
    def test_confirmation_works_on_a_real_terminal_and_defaults_no(self):
        import pty
        for answer,expected in ((b'y\n','True'),(b'\n','False')):
            pid,fd = pty.fork()
            if pid == 0:
                os.execv(sys.executable,[sys.executable,'-B','-c',
                    'import sys;sys.path.insert(0,'+repr(str(fixtures.APP))+');from pkgs_lib.workflows import confirm;print("accepted:",confirm())'])
            data=b'';sent=False;status=None;deadline=time.monotonic()+10
            try:
                while time.monotonic()<deadline:
                    if select.select([fd],[],[],.1)[0]:
                        try: chunk=os.read(fd,4096)
                        except OSError: break
                        if not chunk: break
                        data+=chunk
                        if b'Proceed?' in data and not sent: os.write(fd,answer);sent=True
                    child,status=os.waitpid(pid,os.WNOHANG)
                    if child: pid=0;break
                self.assertIn(('accepted: '+expected).encode(),data)
            finally:
                os.close(fd)
                if pid:
                    try: os.kill(pid,9)
                    except ProcessLookupError: pass
                    os.waitpid(pid,0)


if __name__ == '__main__': unittest.main()
