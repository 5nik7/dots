#!/usr/bin/env python3
"""Cleanup safety/accounting contracts. Every mutable path belongs to a fixture."""
from contextlib import redirect_stdout
import io
import json
import os
import stat
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from cleanup.core import Target, inventory, measure, references
from cleanup.termux import Termux, ORDINARY, CHECKPOINTS, LOGS
from cleanup.receipts import Receipts
from cleanup.engine import run


@unittest.skipIf(os.name == 'nt', 'Termux provider requires POSIX filesystem/process primitives')
class Cleanup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots cleanup 雪 ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.app = self.base / 'com.termux'
        self.home = self.app / 'files/home'
        self.prefix = self.app / 'files/usr'
        self.home.mkdir(parents=True); self.prefix.mkdir(parents=True)
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('DOTS','GO','UV_','CARGO','XDG_','TERMUX','GIT_'))}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), PREFIX=str(self.prefix),
                        XDG_CACHE_HOME=str(self.home/'.cache'), XDG_STATE_HOME=str(self.home/'.local/state'),
                        XDG_CONFIG_HOME=str(self.home/'.config'), XDG_DATA_HOME=str(self.home/'.local/share'),
                        LOCALAPPDATA=str(self.home/'Local'), APPDATA=str(self.home/'Roaming'),
                        DOTS=str(ROOT), DOTS_PROFILE='termux', DOTS_COLOR='never', DOTS_ICONS='never',
                        DOTS_PROGRESS='never', TERM='dumb', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        self.adapter = Termux(self.env)
        self.store = Receipts(self.home / '.local/state/dots/cleanup')

    def file(self, relative, text='fixture'):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
        return path

    def cli(self, *args, native=False, expected=0, env=None, process_fixture=False):
        command = [sys.executable, '-B', str(ROOT/'lib/dots'/('cli.py' if native else 'cleanup_cli.py'))]
        if native: command.append('cleanup')
        if process_fixture:
            # Only this fixture's destructive CLI test substitutes process
            # evidence. Native open-handle detection has its own separate test;
            # unrelated host daemons must not make the fixture nondeterministic.
            code = ('import sys,functools;sys.path.insert(0,sys.argv.pop(1));'
                    'import cleanup.engine as engine;'
                    'engine.run=functools.partial(engine.run,inspect=lambda paths:([],[]));'
                    'import cleanup_cli;sys.exit(cleanup_cli.main(sys.argv[1:]))')
            command = [sys.executable,'-B','-c',code,str(ROOT/'lib/dots')]
        result = subprocess.run([*command,*args],env=env or self.env,cwd=self.home,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
        return result

    def execute(self, groups=('downloads',), decision='delete', inspect=lambda _: ([], [])):
        targets, issues = self.adapter.candidates(groups, 30)
        return run(self.adapter, targets, groups, issues, self.store, lambda *_: decision, inspect=inspect)

    def test_scan_is_recursive_inert_and_exact_json(self):
        self.file('.npm/_cacache/a/hidden/.entry', 'abc')
        a = self.cli('scan','--json').stdout
        forced = dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')
        b = self.cli('scan','--json',env=forced).stdout
        for data in (json.loads(a),json.loads(b)):
            self.assertEqual(data['candidates'][0]['files'],1)
            self.assertEqual(data['candidates'][0]['logical_bytes'],3)
        self.assertNotIn('\x1b',b)
        self.assertFalse(self.store.directory.exists())

    def test_delete_receipt_totals_and_repeat(self):
        self.file('.npm/_cacache/a','1234'); self.file('.cache/pip/sub/b','56789')
        first = self.execute()
        self.assertEqual(first['status'],'completed')
        self.assertEqual(first['totals']['files'],2)
        self.assertEqual(first['totals']['logical_bytes'],9)
        self.assertEqual(first['cumulative'],first['totals'])
        self.assertEqual(list((self.home/'.npm/_cacache').iterdir()),[])
        second = self.execute()
        self.assertIsNone(second['id']); self.assertEqual(second['totals']['files'],0)
        self.assertEqual(len(self.store.rows()),1)
        self.assertEqual(second['cumulative'],first['totals'])

    def test_skip_stop_create_no_receipts(self):
        p=self.file('.npm/_cacache/keep')
        for decision,status in [('skip','completed'),('stop','stopped')]:
            self.assertEqual(self.execute(decision=decision)['status'],status)
            self.assertTrue(p.exists());self.assertFalse(self.store.directory.exists())

    def test_stale_group_preflight_preserves_every_member(self):
        a=self.file('.npm/_cacache/a');b=self.file('.cache/pip/b')
        targets,issues=self.adapter.candidates(('downloads',),30)
        b.write_text('changed')
        result=run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['status'],'partial');self.assertTrue(a.exists());self.assertTrue(b.exists())
        self.assertEqual(result['totals']['files'],0)

    def test_linked_root_and_escape_refused(self):
        foreign=self.base/'outside';foreign.mkdir();(foreign/'keep').write_text('keep')
        (self.home/'.cache').mkdir();(self.home/'.cache/pip').symlink_to(foreign,target_is_directory=True)
        targets,issues=self.adapter.candidates(('downloads',),30)
        self.assertFalse(targets);self.assertTrue(issues);self.assertTrue((foreign/'keep').exists())
        for value in (str(self.home),str(foreign),str(self.home/'.codex/sessions'),str(self.home/'dots')):
            adapter=Termux(dict(self.env,GOCACHE=value))
            _,issues=adapter.candidates(('builds',),30);self.assertTrue(issues)

    def test_nested_symlink_is_unlinked_not_followed(self):
        foreign=self.base/'outside';foreign.mkdir();keep=foreign/'keep';keep.write_text('keep')
        self.file('.npm/_cacache/a');link=self.home/'.npm/_cacache/link';link.symlink_to(foreign,target_is_directory=True)
        result=self.execute();self.assertTrue(keep.exists());self.assertFalse(link.exists())
        self.assertEqual(result['totals']['symlinks'],1)

    def test_replaced_parent_is_not_followed(self):
        source=self.file('.npm/_cacache/a');targets,issues=self.adapter.candidates(('downloads',),30)
        original=source.parent;original.rename(original.with_name('old'))
        outside=self.base/'outside';outside.mkdir();(outside/'a').write_text('keep');original.symlink_to(outside,target_is_directory=True)
        result=run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['status'],'partial');self.assertEqual((outside/'a').read_text(),'keep')

    def test_directory_swap_during_scan_is_not_followed(self):
        import cleanup.core as core
        source=self.file('.npm/_cacache/a');foreign=self.base/'foreign';foreign.mkdir()
        (foreign/'keep').write_text('keep');original=core.directory_fd
        def swap(path):
            if path==source.parent:
                path.rename(path.with_name('retained'))
                path.symlink_to(foreign,target_is_directory=True)
            return original(path)
        with patch('cleanup.core.directory_fd',side_effect=swap):
            targets,issues=self.adapter.candidates(('downloads',),30)
        self.assertFalse(targets);self.assertTrue(issues);self.assertEqual((foreign/'keep').read_text(),'keep')

    def test_explicit_cli_run_deletes_and_records_only_selected_group(self):
        p=self.file('.npm/_cacache/a','abc');keep=self.file('.cpan/build/keep')
        result=json.loads(self.cli('run','--group','downloads','--yes','--json',process_fixture=True).stdout)
        self.assertEqual(result['totals']['files'],1);self.assertFalse(p.exists());self.assertTrue(keep.exists())
        self.assertEqual(self.store.cumulative(),result['totals'])

    def test_busy_and_uninspectable_skip(self):
        p=self.file('.npm/_cacache/a')
        for inspection in (([str(p.parent)],[]),([],['denied'])):
            result=self.execute(inspect=lambda _, i=inspection:i)
            self.assertEqual(result['status'],'partial');self.assertTrue(p.exists())

    def test_real_open_handle_is_detected(self):
        p=self.file('.npm/_cacache/a')
        child=subprocess.Popen([sys.executable,'-c','import sys,time; f=open(sys.argv[1]); print("ready",flush=True); time.sleep(30)',str(p)],stdout=subprocess.PIPE,env=self.env)
        try:
            self.assertEqual(child.stdout.readline(),b'ready\n')
            hits,errors=references([p.parent]);self.assertIn(str(p.parent),hits)
        finally:child.terminate();child.wait();child.stdout.close()

    def test_apt_and_neovim_allowlists(self):
        archive=self.app/'cache/apt/archives';archive.mkdir(parents=True)
        (archive/'a.deb').write_text('deb');(archive/'lock').write_text('lock');(archive/'partial').mkdir();(archive/'partial/a.deb').write_text('partial')
        for name in LOGS:self.file('.local/state/nvim/'+name)
        keep=self.file('.local/state/nvim/undo/keep');chat=self.file('.local/state/nvim/CopilotChat.log')
        result=self.execute(('downloads','logs'))
        self.assertEqual(result['totals']['files'],8);self.assertTrue(keep.exists());self.assertTrue(chat.exists())
        self.assertEqual(sorted(p.name for p in archive.iterdir()),['lock','partial'])

    def test_hardlinks_and_sparse_accounting(self):
        def link(source, target):
            if hasattr(os,'link'):os.link(source,target)
            elif shutil.which('ln'):
                result=subprocess.run(['ln','--',str(source),str(target)],capture_output=True)
                if result.returncode:self.skipTest('native hardlinks unavailable on this filesystem')
            else:self.skipTest('no native hardlink primitive')
        a=self.file('.npm/_cacache/a','x'*8192);outside=self.home/'kept-link';link(a,outside)
        b=self.file('.npm/_cacache/b','b'*8192);link(b,b.with_name('c'))
        sparse=self.file('.npm/_cacache/sparse','')
        with sparse.open('wb') as stream:stream.seek(4*1024*1024);stream.write(b'x')
        result=self.execute();self.assertEqual(result['totals']['files'],4)
        self.assertLess(result['totals']['allocated_bytes'],result['totals']['logical_bytes'])
        self.assertTrue(outside.exists())

    def test_sparse_and_synthetic_hardlink_accounting(self):
        sparse=self.file('.npm/_cacache/sparse','')
        with sparse.open('wb') as stream:stream.seek(4*1024*1024);stream.write(b'x')
        result=self.execute()
        self.assertEqual(result['totals']['logical_bytes'],4*1024*1024+1)
        self.assertLess(result['totals']['allocated_bytes'],result['totals']['logical_bytes'])
        # Android forbids hardlinks here; exercise inode accounting independently.
        info=(1,2,stat.S_IFREG|0o600,1000,2,8192,1,1,4096)
        self.assertEqual(measure({'a':info})['allocated_bytes'],0)
        both=measure({'a':info,'b':info})
        self.assertEqual((both['files'],both['allocated_bytes'],both['logical_bytes']),(2,4096,8192))

    def test_partial_and_interrupted_direct_counts_are_durable(self):
        self.file('.npm/_cacache/a','abc');self.file('.npm/_cacache/b','defg')
        targets,issues=self.adapter.candidates(('downloads',),30)
        def interrupt(label,*args):
            if label.startswith('Removing'):raise KeyboardInterrupt
        result=run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',interrupt,inspect=lambda _: ([],[]))
        self.assertEqual(result['status'],'stopped');self.assertEqual(result['totals']['files'],1)
        self.assertGreater(result['totals']['logical_bytes'],0)
        self.assertEqual(self.store.rows()[0]['totals'],result['totals'])
        again=self.execute();self.assertEqual(again['cumulative']['files'],2)
        self.assertEqual(again['cumulative']['logical_bytes'],7)

    def test_native_failed_or_interrupted_removal_is_uncertain(self):
        for error in (ValueError('helper failed'),KeyboardInterrupt()):
            p=self.file('go/pkg/mod/a')
            def native(target):p.unlink();raise error
            with patch.object(self.adapter,'native',side_effect=native):result=self.execute(('builds',))
            self.assertIn(result['status'],('partial','stopped'))
            self.assertEqual(result['totals']['files'],0)
            self.assertIn('uncertainty',result['groups'][0]['targets'][0])

    def test_native_helpers_use_only_fixture_caches(self):
        for name,rule,relative in [('go','go-module-cache','go/pkg/mod'),('go','go-build-cache','.cache/go-build'),('uv','uv-cache','.cache/uv')]:
            if not shutil.which(name):continue
            leaf=('00/'+('0'*64)+'-a') if rule=='go-build-cache' else 'dummy'
            cache_file=self.file(relative+'/'+leaf,'cache');path=self.home/relative
            kept=self.file('unselected/keep')
            target=Target(rule,'builds',path);target.entries=inventory(target,self.app)
            self.adapter.native(target)
            self.assertFalse(cache_file.exists(),rule)
            self.assertTrue(kept.exists())

    def test_lock_contention_and_private_receipts(self):
        p=self.file('.npm/_cacache/a')
        holder=Receipts(self.store.directory);holder.acquire()
        try:
            result=self.execute();self.assertEqual(result['status'],'partial');self.assertTrue(p.exists())
        finally:holder.close()
        result=self.execute();self.assertEqual(result['totals']['files'],1)
        self.assertEqual(self.store.directory.stat().st_mode&0o077,0)
        self.assertEqual((self.store.directory/(result['id']+'.json')).stat().st_mode&0o077,0)

    def test_nested_mount_foreign_owner_and_special_files_refused(self):
        p=self.file('.npm/_cacache/a')
        original=os.path.ismount
        with patch('cleanup.core.os.path.ismount',side_effect=lambda path:Path(path)==p.parent or original(path)):
            targets,issues=self.adapter.candidates(('downloads',),30)
            self.assertFalse(targets);self.assertTrue(issues)
        with patch('cleanup.core.os.getuid',return_value=os.getuid()+1):
            targets,issues=self.adapter.candidates(('downloads',),30)
            self.assertFalse(targets);self.assertTrue(issues)
        fifo=p.with_name('pipe');os.mkfifo(fifo)
        targets,issues=self.adapter.candidates(('downloads',),30)
        self.assertFalse(targets);self.assertTrue(issues);self.assertTrue(p.exists())

    def test_native_helper_timeout_is_bounded(self):
        from cleanup.termux import command
        for script in ('import time;time.sleep(10)','import os,time;os.close(1);os.close(2);time.sleep(10)'):
            with self.assertRaises(ValueError):
                command([sys.executable,'-c',script],self.env,self.home,timeout=.1)

    def test_exact_data_and_narrow_human_reports(self):
        import fcntl,pty,re,struct,termios
        from argparse import Namespace
        from cleanup.presentation import render
        from config_values import current
        from style_config import current as styles
        from resources import cells
        self.file('.npm/_cacache/雪\x1b[31mfile','abc')
        report=self.execute()
        for width in (40,80,120):
            for color,bg in [('never','0;0'),('always','15;0'),('always','0;15')]:
                master,slave=pty.openpty()
                try:
                    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',80,width,0,0))
                    with patch.dict(os.environ,dict(self.env,COLUMNS=str(width),DOTS_COLOR=color,DOTS_ICONS=color,COLORFGBG=bg),clear=True):
                        current.cache_clear();styles.cache_clear()
                        with os.fdopen(os.dup(slave),'w') as stream:
                            render(report,Namespace(json=False,quiet=False,verbose=True),stream)
                    os.close(slave);slave=-1
                    chunks=[]
                    while True:
                        try:chunk=os.read(master,65536)
                        except OSError:break
                        if not chunk:break
                        chunks.append(chunk)
                    text=b''.join(chunks).decode()
                    plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                    self.assertIn('Removed',plain);self.assertIn('Combined',plain)
                    self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
                    self.assertEqual(re.sub(r'\s','',plain).count(report['id']),1)
                    if color=='never':self.assertNotIn('\x1b',text)
                finally:
                    if slave>=0:os.close(slave)
                    os.close(master)
        args=Namespace(json=True,quiet=False,verbose=True)
        outputs=[]
        for mode in ('never','always'):
            with patch.dict(os.environ,DOTS_COLOR=mode,DOTS_ICONS=mode),redirect_stdout(io.StringIO()) as out:render(report,args)
            outputs.append(out.getvalue())
        self.assertEqual(*outputs);self.assertEqual(json.loads(outputs[0])['totals']['files'],1)
        current.cache_clear();styles.cache_clear()

    def test_checkpoint_git_classification_and_bounded_scope(self):
        git=shutil.which('git')
        if not git:self.skipTest('Git unavailable')
        root=self.file('.pi/agent/ayu/checkpoints/sessions/git/manifest.json',json.dumps({'version':1,'cwd':str(self.home/'project')})).parent
        def invoke(*args):
            result=subprocess.run([git,'-C',str(root),*args],env=self.env,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
        invoke('init','--quiet');invoke('config','user.name','Fixture');invoke('config','user.email','fixture@example.invalid')
        (root/'source.txt').write_text('source');invoke('add','source.txt');invoke('commit','--quiet','-m','fixture')
        self.assertEqual(self.adapter.classify(root),'project-checkpoints')
        (root/'.env.local').write_text('fixture value');invoke('add','.env.local');invoke('commit','--quiet','-m','fixture')
        self.assertEqual(self.adapter.classify(root),'sensitive-checkpoints')
        # All history matters, even if sensitive data was removed from HEAD.
        invoke('rm','--quiet','.env.local');invoke('commit','--quiet','-m','removed')
        self.assertEqual(self.adapter.classify(root),'sensitive-checkpoints')
        with patch('cleanup.termux.command',return_value=b'abc\n'*129):
            self.assertEqual(self.adapter.classify(root),'unclassified-checkpoints')

    def test_quiet_keeps_failures_and_history_reports(self):
        from argparse import Namespace
        from cleanup.presentation import render
        with patch('sys.stderr',io.StringIO()) as err,redirect_stdout(io.StringIO()) as out:
            render({'issues':[{'reason':'fixture failure'}]},Namespace(json=False,quiet=True))
            self.assertEqual(out.getvalue(),'');self.assertIn('fixture failure',err.getvalue())
        self.file('.npm/_cacache/a');result=self.execute()
        history=json.loads(self.cli('history','--json').stdout)
        self.assertEqual(history['runs'][0]['id'],result['id'])
        detail=json.loads(self.cli('report',result['id'],'--json',native=True).stdout)
        self.assertEqual(detail['cumulative'],result['totals'])
        self.cli('report','unknown',expected=1)

    def test_prompt_skip_stop_and_failed_selector(self):
        from cleanup.presentation import confirm
        from interaction import SelectionEnded
        self.file('.npm/_cacache/a');targets,_=self.adapter.candidates(('downloads',),30)
        for answer,expected in [('\n','skip'),('no\n','skip'),('yes\n','delete'),('stop\n','stop'),('','stop')]:
            with patch.dict(os.environ,self.env,clear=True),patch('sys.stdin',io.StringIO(answer)),patch('sys.stderr',io.StringIO()):
                self.assertEqual(confirm('downloads',targets),expected)
        with patch.dict(os.environ,dict(self.env,TERM='xterm'),clear=True),patch('sys.stderr',io.StringIO()),patch('cleanup.presentation.shutil.which',return_value='/fixture/tool'),patch('cleanup.presentation.Selector.pick',side_effect=SelectionEnded(1)):
            with self.assertRaises(ValueError):confirm('downloads',targets)
        self.assertFalse(self.store.directory.exists())

    def test_menu_actions_keep_review_boundary(self):
        from menu_cli import ACTIONS,FAMILIES
        self.assertTrue(any(a.id=='cleanup' for a in ACTIONS))
        actions=FAMILIES['cleanup']
        self.assertEqual({a.id for a in actions},{'run','scan','groups','checkpoints','history','report','configuration'})
        for action in actions:self.assertNotIn('--yes',action.options)

    def test_sensitive_groups_cannot_bypass_approval(self):
        for args in [('run','--group','sensitive-checkpoints','--yes'),('run','--include-checkpoints','--yes'),('--yes',),('run','--json')]:
            self.cli(*args,expected=2)
        self.assertFalse(self.store.directory.exists())

    def test_linux_native_scan_surface(self):
        env=dict(self.env);env.pop('PREFIX')
        data=json.loads(self.cli('scan','--json',env=env,native=True).stdout)
        self.assertEqual(data['status'],'planned');self.assertFalse(self.store.directory.exists())
        self.assertIn(json.loads(self.cli('groups','--json',env=env,native=True).stdout)['platform'],('linux','wsl'))

    def test_dry_run_and_default_noninteractive_do_not_delete(self):
        p=self.file('.npm/_cacache/a')
        for args in [('--json',),('run','--yes','--dry-run','--json')]:
            self.assertEqual(json.loads(self.cli(*args).stdout)['status'],'planned')
            self.assertTrue(p.exists());self.assertFalse(self.store.directory.exists())

    def test_native_missing_does_not_fall_back_to_recursive_delete(self):
        p=self.file('go/pkg/mod/a')
        with patch('cleanup.termux.shutil.which',return_value=None):result=self.execute(('builds',))
        self.assertEqual(result['status'],'partial');self.assertTrue(p.exists())

    def test_checkpoint_age_and_explicit_scope(self):
        p=self.file('.pi/agent/ayu/checkpoints/sessions/old/.git/object')
        for parent in (p,*list(p.parents)[:2]):os.utime(parent,(time.time()-40*86400,)*2)
        with patch.object(self.adapter,'classify',return_value='sensitive-checkpoints'):
            ordinary,_=self.adapter.candidates(ORDINARY,30);self.assertFalse(ordinary)
            selected,_=self.adapter.candidates(('project-checkpoints',),30);self.assertFalse(selected)
            selected,_=self.adapter.candidates(('sensitive-checkpoints',),30);self.assertEqual(len(selected),1)
            p.write_text('new');selected,_=self.adapter.candidates(CHECKPOINTS,30);self.assertFalse(selected)

    def test_checkpoint_auth_classification_never_reads_auth(self):
        p=self.file('.pi/agent/ayu/checkpoints/sessions/old/manifest.json',json.dumps({'version':1,'cwd':str(self.home/'.pi/agent')})).parent
        self.assertEqual(self.adapter.classify(p),'sensitive-checkpoints')
        (p/'manifest.json').write_text('{invalid');self.assertEqual(self.adapter.classify(p),'unclassified-checkpoints')

    def test_receipt_failure_before_delete(self):
        p=self.file('.npm/_cacache/a')
        with patch.object(self.store,'write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.execute()
        self.assertTrue(p.exists())

    def test_interruption_keeps_verified_count(self):
        self.file('.npm/_cacache/a');self.file('.npm/_cacache/b')
        targets,issues=self.adapter.candidates(('downloads',),30)
        def interrupt(*args):raise KeyboardInterrupt
        # Initial engine progress interrupts before deletion.
        result=run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',interrupt,inspect=lambda _: ([],[]))
        self.assertEqual(result['status'],'stopped');self.assertEqual(result['totals']['files'],0)
        self.assertEqual(self.store.rows()[0]['status'],'stopped')

    def test_incomplete_receipts_are_not_replayed(self):
        self.file('.npm/_cacache/a');result=self.execute()
        path=self.store.directory/(result['id']+'.json');data=json.loads(path.read_text());data['status']='running';path.write_text(json.dumps(data))
        self.assertEqual(self.store.rows()[0]['status'],'incomplete')
        self.assertEqual(self.store.cumulative(),result['totals'])

    def test_native_help_and_six_shell_completion_are_inert(self):
        self.cli('--help',native=True)
        for shell in ('bash','zsh','fish','nu','xonsh'):
            out=subprocess.run([str(ROOT/'bin/dots'),'__complete',shell,'4','--','dots','cleanup','run','--group','b'],env=self.env,cwd=self.home,capture_output=True,text=True,timeout=15)
            self.assertEqual(out.returncode,0,out.stderr);self.assertIn('candidate\tbuilds\t',out.stdout)
        out=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/cli.py'),'__complete','cleanup','run','--group','b'],env=self.env,cwd=self.home,capture_output=True,text=True)
        self.assertIn('candidate\tbuilds\t',out.stdout);self.assertFalse(self.store.directory.exists())


class NativeCleanup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots native cleanup 雪 ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base/'home'
        if os.name == 'nt':
            from cleanup.windows import NativeReader
            NativeReader().mkdir_private(self.home)
        else:
            self.home.mkdir()
        self.env = {key:value for key,value in os.environ.items()
                    if not key.startswith(('DOTS','GO','UV_','CARGO','XDG_','TERMUX','GIT_','PIP_','npm_','NPM_'))
                    and key != 'PREFIX'}
        self.env.update(HOME=str(self.home),USERPROFILE=str(self.home),
                        XDG_CACHE_HOME=str(self.home/'.cache'),XDG_STATE_HOME=str(self.home/'.state'),
                        XDG_CONFIG_HOME=str(self.home/'.config'),XDG_DATA_HOME=str(self.home/'.data'),
                        APPDATA=str(self.home/'Roaming'),LOCALAPPDATA=str(self.home/'Local'),
                        DOTS=str(ROOT),DOTS_COLOR='never',DOTS_ICONS='never',DOTS_PROGRESS='never')
        from cleanup.linux import Linux
        from cleanup.windows import Windows
        self.adapter = Windows(self.env) if os.name == 'nt' else Linux(self.env)
        self.store = Receipts(self.home/'.state/dots/cleanup')

    def file(self, relative, data='fixture'):
        path = self.home/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(data)
        return path

    def cli(self, *args, expected=0):
        result = subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/cleanup_cli.py'),*args],
                                env=self.env,cwd=self.home,input='',capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return json.loads(result.stdout)

    def unsafe_acl(self, path):
        # Deliberately insecure ACL on a fixture-owned path, without elevation.
        import ctypes as c
        from ctypes import wintypes as w
        from cleanup.windows import NativeReader
        reader = NativeReader()
        reader.a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (w.LPCWSTR,w.DWORD,c.POINTER(w.LPVOID),w.LPVOID)
        reader.a.GetSecurityDescriptorDacl.argtypes = (w.LPVOID,c.POINTER(w.BOOL),c.POINTER(w.LPVOID),c.POINTER(w.BOOL))
        reader.a.SetNamedSecurityInfoW.argtypes = (w.LPWSTR,c.c_int,w.DWORD,w.LPVOID,w.LPVOID,w.LPVOID,w.LPVOID)
        descriptor, dacl = w.LPVOID(), w.LPVOID()
        present, defaulted = w.BOOL(), w.BOOL()
        self.assertTrue(reader.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            'D:P(A;OICI;FA;;;WD)',1,c.byref(descriptor),None))
        try:
            self.assertTrue(reader.a.GetSecurityDescriptorDacl(descriptor,c.byref(present),c.byref(dacl),c.byref(defaulted)))
            self.assertEqual(reader.a.SetNamedSecurityInfoW(str(path),1,0x80000004,None,None,dacl,None),0)
        finally:
            reader.k.LocalFree(descriptor)

    def test_native_scan_is_owned_readonly_and_reports_platform_capability(self):
        path = self.file('Local/npm-cache/_cacache/sub/.entry' if os.name == 'nt' else '.npm/_cacache/sub/.entry','abc')
        data = self.cli('scan','--group','downloads','--json')
        self.assertEqual(data['status'],'planned')
        self.assertEqual(data['candidates'][0]['files'],1)
        self.assertEqual(data['candidates'][0]['logical_bytes'],3)
        self.assertTrue(path.is_file())
        self.assertFalse(self.store.directory.exists())
        catalog = {row['id']:row for row in self.cli('groups','--json')['catalog']}
        self.assertTrue(catalog['downloads']['scan_supported'])
        self.assertTrue(catalog['downloads']['run_supported'])
        self.assertFalse(catalog['project-checkpoints']['scan_supported'])

    def test_group_catalog_is_static_and_platform_specific(self):
        import cleanup_cli
        from cleanup.termux import GROUPS
        for platform in ('windows','linux','wsl','termux'):
            with self.subTest(platform=platform), patch.object(cleanup_cli,'detect',return_value={'platform':platform}), \
                    patch.object(cleanup_cli.Windows,'__init__',side_effect=AssertionError('provider queried')), \
                    patch.object(cleanup_cli.Linux,'__init__',side_effect=AssertionError('provider queried')), \
                    patch.object(cleanup_cli.Termux,'__init__',side_effect=AssertionError('provider queried')), \
                    patch.dict(os.environ,self.env,clear=True), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cleanup_cli.main(['groups','--json']),0)
                catalog = {row['id']:row for row in json.loads(output.getvalue())['catalog']}
                self.assertEqual(tuple(catalog),tuple(GROUPS))
                if platform == 'termux':
                    for key, row in catalog.items():
                        self.assertEqual((row['label'],row['risk'],row['description']),GROUPS[key])
                else:
                    self.assertNotIn('APT',output.getvalue());self.assertNotIn('CPAN',output.getvalue())
                    self.assertFalse(catalog['project-checkpoints']['scan_supported'])
                    self.assertFalse(catalog['project-checkpoints']['supported'])
                    self.assertIn('Not implemented',catalog['project-checkpoints']['description'])
                self.assertTrue(catalog['downloads']['run_supported'])
                self.assertEqual(catalog['builds']['scan_supported'],platform != 'windows')
        self.assertFalse(self.store.directory.exists())

    def test_linked_cache_is_refused_without_reading_outside(self):
        outside = self.base/'outside'
        outside.mkdir();(outside/'keep').write_text('keep')
        path = self.home/('Local/pip/Cache' if os.name == 'nt' else '.cache/pip')
        path.parent.mkdir(parents=True)
        try:
            path.symlink_to(outside,target_is_directory=True)
        except OSError as error:
            self.skipTest('native symlink capability unavailable: ' + str(error))
        targets, issues = self.adapter.candidates(('downloads',),30)
        self.assertEqual(targets,[])
        self.assertTrue(issues)
        self.assertEqual((outside/'keep').read_text(),'keep')
        self.assertFalse(self.store.directory.exists())

    @unittest.skipUnless(os.name == 'nt', 'native Windows read-only adapter')
    def test_windows_unsupported_group_keeps_receipts_and_cache_untouched(self):
        path = self.file('Local/npm-cache/_cacache/keep')
        data = self.cli('run','--group','builds','--yes','--json',expected=1)
        self.assertEqual(data['status'],'partial')
        self.assertIn('pending',data['issues'][0]['reason'])
        self.assertTrue(path.exists())
        self.assertFalse(self.store.directory.exists())

    @unittest.skipUnless(os.name == 'nt', 'native Windows handles')
    def test_windows_active_writer_is_retained(self):
        path = self.file('Local/npm-cache/_cacache/active')
        with path.open('r+b'):
            targets, issues = self.adapter.candidates(('downloads',),30)
        self.assertEqual(targets,[])
        self.assertTrue(issues)
        self.assertEqual(path.read_text(),'fixture')

    @unittest.skipUnless(os.name == 'nt', 'native Windows exact handle deletion')
    def test_windows_exact_deletion_private_receipt_and_repeat(self):
        path = self.file('Local/npm-cache/_cacache/sub/-owned 雪','abc')
        targets, issues = self.adapter.candidates(('downloads',),30)
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['status'],'completed',result)
        self.assertFalse(path.exists())
        self.assertTrue((self.home/'Local/npm-cache/_cacache').is_dir())
        self.assertEqual(result['totals']['files'],1)
        self.assertEqual(result['totals']['logical_bytes'],3)
        self.assertEqual(self.store.rows()[0]['totals'],result['totals'])
        targets, issues = self.adapter.candidates(('downloads',),30)
        self.assertFalse(targets);self.assertFalse(issues)
        again = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertIsNone(again['id']);self.assertEqual(again['totals']['files'],0)

    @unittest.skipUnless(os.name == 'nt', 'native Windows whole-group guards')
    def test_windows_group_busy_reader_drift_and_process_failure_retain_all(self):
        first = self.file('Local/npm-cache/_cacache/a','first')
        second = self.file('Local/pip/Cache/b','second')
        targets, issues = self.adapter.candidates(('downloads',),30)
        for inspector in (lambda _: (['busy'],[]),lambda _: ([],['unknown'])):
            result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=inspector)
            self.assertEqual(result['groups'][0]['status'],'blocked',result)
            self.assertTrue(first.exists());self.assertTrue(second.exists())
        # A read-only handle also blocks the whole group, not merely its own file.
        with second.open('rb'):
            result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['groups'][0]['status'],'blocked',result)
        self.assertTrue(first.exists());self.assertTrue(second.exists())
        second.write_text('changed')
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['groups'][0]['status'],'blocked',result)
        self.assertEqual(result['totals']['files'],0)
        self.assertTrue(first.exists());self.assertTrue(second.exists())

    @unittest.skipUnless(os.name == 'nt', 'native Windows refusal invariants')
    def test_windows_readonly_hardlink_and_new_entry_are_retained(self):
        from cleanup.windows import PinnedGroup
        first = self.file('Local/npm-cache/_cacache/a','first')
        second = self.file('Local/npm-cache/_cacache/b','second')
        second.chmod(stat.S_IREAD)
        self.addCleanup(lambda: second.chmod(stat.S_IWRITE) if second.exists() else None)
        targets, issues = self.adapter.candidates(('downloads',),30)
        with self.assertRaisesRegex(ValueError,'read-only'):
            with PinnedGroup(targets,self.home):
                self.fail('readonly group accepted')
        self.assertTrue(first.exists())
        second.chmod(stat.S_IWRITE)
        outside = self.home/'outside-alias'
        os.link(second,outside)
        targets, issues = self.adapter.candidates(('downloads',),30)
        with self.assertRaisesRegex(ValueError,'multiply-linked'):
            with PinnedGroup(targets,self.home):
                self.fail('hardlinked group accepted')
        outside.unlink()
        targets, issues = self.adapter.candidates(('downloads',),30)
        with PinnedGroup(targets,self.home) as pinned:
            new = self.file('Local/npm-cache/_cacache/arrived','new')
            with self.assertRaisesRegex(ValueError,'directory entries changed'):
                pinned.delete_entries(targets[0],self.home)
        self.assertTrue(first.exists());self.assertTrue(second.exists());self.assertTrue(new.exists())

    @unittest.skipUnless(os.name == 'nt', 'native Windows private receipts')
    def test_windows_receipt_lock_acl_reparse_and_legacy_reader(self):
        from cleanup.windows import NativeReader
        self.store.acquire()
        other = Receipts(self.store.directory)
        with self.assertRaisesRegex(ValueError,'lock'):
            other.acquire()
        self.store.close()
        reader = NativeReader()
        with reader.opened(self.store.directory,owner=True,private=True):
            pass
        # Existing unprotected state is refused, never permission-repaired.
        unsafe = self.base/'unsafe-state';unsafe.mkdir();self.unsafe_acl(unsafe)
        with self.assertRaisesRegex(ValueError,'another principal'):
            Receipts(unsafe).acquire()
        link = self.home/'linked-state'
        try:
            link.symlink_to(self.store.directory,target_is_directory=True)
        except OSError as error:
            self.skipTest('native symlink capability unavailable: '+str(error))
        with self.assertRaisesRegex(ValueError,'reparse'):
            Receipts(link).rows()
        self.file('Local/npm-cache/_cacache/a')
        targets, issues = self.adapter.candidates(('downloads',),30)
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        journal = self.store.directory/(result['id']+'.jsonl')
        old = self.store.directory/(result['id']+'.json')
        old.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.store.rows()
        journal.unlink()
        self.assertEqual(self.store.rows()[0]['totals'],result['totals'])

    @unittest.skipUnless(os.name == 'nt', 'native Windows interruption accounting')
    def test_windows_interrupted_tail_and_unrecorded_delete_keep_conservative_totals(self):
        self.file('Local/npm-cache/_cacache/a','abc')
        targets, issues = self.adapter.candidates(('downloads',),30)
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        journal = self.store.directory/(result['id']+'.jsonl')
        with journal.open('ab') as stream:
            stream.write(b'{"unfinished":');stream.flush();os.fsync(stream.fileno())
        row = self.store.rows()[0]
        self.assertEqual(row['status'],'incomplete')
        self.assertEqual(row['totals']['files'],1)
        path = self.file('Local/npm-cache/_cacache/b','def')
        targets, issues = self.adapter.candidates(('downloads',),30)
        original = self.store.write
        def fail_after_delete(report):
            if not path.exists():
                raise OSError('fixture interrupted before accounting append')
            original(report)
        with patch.object(self.store,'write',side_effect=fail_after_delete):
            with self.assertRaisesRegex(OSError,'accounting append'):
                run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertFalse(path.exists())
        newest = self.store.rows()[0]
        self.assertEqual(newest['status'],'incomplete')
        self.assertEqual(newest['totals']['files'],0)

    @unittest.skipUnless(os.name == 'nt', 'native Windows process-query boundary')
    def test_windows_process_probe_fails_closed_and_scan_never_queries(self):
        from cleanup.windows import process_references
        self.file('Local/npm-cache/_cacache/a')
        with patch('cleanup.windows.process_references',side_effect=AssertionError('scan queried processes')):
            self.adapter.candidates(('downloads',),30)
        for result in (subprocess.CompletedProcess([],1,'','failure'),
                       subprocess.CompletedProcess([],0,'false','warning'),
                       subprocess.CompletedProcess([],0,'garbage','')):
            with patch('cleanup.windows.subprocess.run',return_value=result):
                active, unknown = process_references(['C:/fixture'],os.getpid())
                self.assertFalse(active);self.assertTrue(unknown)
        with patch('cleanup.windows.subprocess.run',side_effect=subprocess.TimeoutExpired('fixture',20)):
            self.assertTrue(process_references(['C:/fixture'],os.getpid())[1])

    @unittest.skipUnless(os.name == 'nt', 'native Windows mapped-file and cwd guards')
    def test_windows_mapped_file_and_directory_reference_are_retained(self):
        import mmap
        from cleanup.windows import PinnedGroup, NativeReader
        path = self.file('Local/npm-cache/_cacache/mapped','mapped data')
        targets, issues = self.adapter.candidates(('downloads',),30)
        stream = path.open('rb')
        mapping = mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ)
        stream.close()
        try:
            # Even an observer that incorrectly reports idle cannot bypass the
            # kernel's mapped-file refusal at exact-handle disposition.
            result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
            self.assertEqual(result['totals']['files'],0,result)
            self.assertEqual(result['status'],'partial',result)
            self.assertEqual(mapping[:],b'mapped data');self.assertTrue(path.exists())
        finally:
            mapping.close()
        reader = NativeReader()
        with reader.opened(path.parent):
            with self.assertRaises(OSError):
                with PinnedGroup(targets,self.home):
                    self.fail('active directory reference accepted')

    @unittest.skipUnless(os.name == 'nt', 'native Windows group process inspection')
    def test_windows_pre_pin_query_includes_self_and_failures_prevent_mutation(self):
        path = self.file('Local/npm-cache/_cacache/a')
        targets, issues = self.adapter.candidates(('downloads',),30)
        with patch('cleanup.windows.process_references',return_value=([str(path)],[])) as probe:
            result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete')
        self.assertEqual(result['groups'][0]['status'],'blocked',result)
        probe.assert_called_once_with([str(path)],0)
        self.assertTrue(path.exists())

    @unittest.skipUnless(os.name == 'nt', 'native Windows ACL drift and pinned ancestors')
    def test_windows_acl_drift_and_ancestor_replacement_fail_closed(self):
        from cleanup.windows import PinnedGroup
        path = self.file('Local/npm-cache/_cacache/a')
        targets, issues = self.adapter.candidates(('downloads',),30)
        with PinnedGroup(targets,self.home):
            with self.assertRaises(OSError):
                path.parent.rename(self.home/'moved-cache')
            with self.assertRaises(OSError):
                with path.open('wb'):
                    self.fail('pinned file became writable')
        self.unsafe_acl(path)
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['groups'][0]['status'],'blocked',result)
        self.assertIn('another principal',result['groups'][0]['reason'])
        self.assertTrue(path.exists())

    @unittest.skipUnless(os.name == 'nt', 'native Windows owned cwd reference')
    def test_windows_owned_child_cwd_prevents_group_pinning(self):
        from cleanup.windows import PinnedGroup
        path = self.file('Local/npm-cache/_cacache/a')
        targets, issues = self.adapter.candidates(('downloads',),30)
        child = subprocess.Popen([sys.executable,'-I','-B','-c',
            'import sys;print("ready",flush=True);sys.stdin.readline()'],cwd=path.parent,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'ready')
            with self.assertRaises(OSError):
                with PinnedGroup(targets,self.home):
                    self.fail('active cwd accepted')
        finally:
            child.communicate('\n',timeout=10)
        self.assertTrue(path.exists())

    @unittest.skipUnless(os.name == 'nt', 'native Windows receipt failure and partial subtotals')
    def test_windows_receipt_failure_prevents_delete_and_interruption_counts_exactly(self):
        first = self.file('Local/npm-cache/_cacache/a','abc')
        second = self.file('Local/npm-cache/_cacache/b','def')
        targets, issues = self.adapter.candidates(('downloads',),30)
        with patch.object(self.store,'write',side_effect=OSError('fixture receipt failure')):
            with self.assertRaisesRegex(OSError,'receipt failure'):
                run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertTrue(first.exists());self.assertTrue(second.exists())
        def interrupt(message,*args):
            if message.startswith('Removing'):
                raise KeyboardInterrupt
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',interrupt,inspect=lambda _: ([],[]))
        self.assertEqual(result['status'],'stopped',result)
        self.assertEqual(result['totals']['files'],1,result)
        self.assertEqual(sum(path.exists() for path in (first,second)),1)
        self.assertEqual(self.store.rows()[0]['totals']['files'],1)

    @unittest.skipUnless(os.name == 'nt', 'native Windows Restart Manager ABI fixture')
    def test_windows_restart_manager_query_fixture_never_controls_processes(self):
        import ctypes as c
        from ctypes import wintypes as w
        from types import SimpleNamespace
        from cleanup.windows import reference_probe
        def callback(function):
            # Python functions support the ctypes argtypes annotation used by
            # the adapter; none calls a real registry or process API.
            return function
        for pid, owner, reboot, code, expected in ((12,0,0,0,True),(12,12,0,0,False),
                                                  (0,0,0,0,False),(0,0,1,0,None),(0,0,0,5,None)):
            ended, registered = [], []
            def start(handle, flags, key):
                c.cast(handle,c.POINTER(w.DWORD))[0] = 1
                return 0
            def register(handle,count,paths,*args):
                registered.extend(paths[index] for index in range(count))
                return 0
            def listing(handle,needed,count,rows,reasons):
                c.cast(reasons,c.POINTER(w.DWORD))[0] = reboot
                if code:
                    return code
                c.cast(needed,c.POINTER(w.UINT))[0] = int(bool(pid))
                if rows is None:
                    return 234 if pid else 0
                rows[0].process.pid = pid
                c.cast(count,c.POINTER(w.UINT))[0] = 1
                return 0
            def end(handle):
                ended.append(True)
                return 0
            fake = SimpleNamespace(RmStartSession=callback(start),RmRegisterResources=callback(register),
                                   RmGetList=callback(listing),RmEndSession=callback(end))
            with self.subTest(pid=pid,owner=owner,reboot=reboot,code=code),patch('ctypes.WinDLL',return_value=fake):
                if expected is None:
                    with self.assertRaises((ValueError,OSError)):
                        reference_probe(['C:/fixture-only'],owner)
                else:
                    self.assertEqual(reference_probe(['C:/fixture-only'],owner),expected)
            self.assertEqual(registered,['C:/fixture-only']);self.assertEqual(ended,[True])

    @unittest.skipUnless(os.name == 'nt', 'native Windows empty-directory and allocation accounting')
    def test_windows_large_native_directory_enumeration_and_sparse_accounting(self):
        import ctypes as c
        import msvcrt
        from ctypes import wintypes as w
        from cleanup.windows import PinnedGroup, NativeReader
        for index in range(650):
            self.file('Local/npm-cache/_cacache/entry-'+str(index),'')
        path = self.file('Local/pip/Cache/sparse')
        reader = NativeReader()
        reader.k.DeviceIoControl.argtypes = (w.HANDLE,w.DWORD,w.LPVOID,w.DWORD,w.LPVOID,w.DWORD,c.POINTER(w.DWORD),w.LPVOID)
        with path.open('r+b') as stream:
            returned = w.DWORD()
            self.assertTrue(reader.k.DeviceIoControl(msvcrt.get_osfhandle(stream.fileno()),0x900C4,
                None,0,None,0,c.byref(returned),None))  # FSCTL_SET_SPARSE, fixture only.
            stream.truncate(16*1024*1024)
            stream.seek(16*1024*1024-1);stream.write(b'X');stream.flush()
            zeros = (c.c_longlong*2)(0,16*1024*1024-65536)
            self.assertTrue(reader.k.DeviceIoControl(msvcrt.get_osfhandle(stream.fileno()),0x980C8,
                zeros,c.sizeof(zeros),None,0,c.byref(returned),None))  # FSCTL_SET_ZERO_DATA.
        targets, issues = self.adapter.candidates(('downloads',),30)
        self.assertFalse(issues)
        sparse = next(target for target in targets if target.rule == 'pip-cache').entries['sparse']
        self.assertEqual(sparse[5],16*1024*1024)
        self.assertLess(sparse[8],sparse[5])
        with PinnedGroup(targets,self.home) as pinned:
            for target in targets:
                self.assertEqual(pinned.inventory(target,self.home),target.entries)
        self.assertEqual(sum(measure(target.entries)['files'] for target in targets),651)

    @unittest.skipIf(os.name == 'nt', 'native Linux/WSL deletion primitives')
    def test_linux_busy_drift_delete_and_repeat(self):
        path = self.file('.npm/_cacache/owned','abc')
        targets, issues = self.adapter.candidates(('downloads',),30)
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',
                     inspect=lambda _: ([str(path)],[]))
        self.assertEqual(result['status'],'partial');self.assertTrue(path.exists())
        path.write_text('changed')
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['status'],'partial');self.assertTrue(path.exists())
        targets, issues = self.adapter.candidates(('downloads',),30)
        result = run(self.adapter,targets,('downloads',),issues,self.store,lambda *_:'delete',inspect=lambda _: ([],[]))
        self.assertEqual(result['platform'],'linux')
        self.assertEqual(result['status'],'completed');self.assertFalse(path.exists())
        self.assertEqual(result['totals']['files'],1)
        targets, issues = self.adapter.candidates(('downloads',),30)
        self.assertEqual(targets,[])

    @unittest.skipIf(os.name == 'nt', 'native Linux/WSL boundary checks')
    def test_linux_overrides_checkpoint_and_system_cache_boundaries(self):
        from cleanup.linux import Linux
        for value in (str(self.base/'outside/cache'),str(self.home/'.config/cache'),str(self.home)):
            with self.subTest(value=value),self.assertRaises(ValueError):
                Linux(dict(self.env,XDG_CACHE_HOME=value))
        adapter = Linux(dict(self.env,PIP_CACHE_DIR=str(self.home/'.ssh/pip')))
        targets, issues = adapter.candidates(('downloads','project-checkpoints'),30)
        self.assertFalse(targets);self.assertEqual(len(issues),2)


if __name__ == '__main__':unittest.main()
