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

    def cli(self, *args, native=False, expected=0, env=None):
        command = [sys.executable, '-B', str(ROOT/'lib/dots'/('cli.py' if native else 'cleanup_cli.py'))]
        if native: command.append('cleanup')
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
        result=json.loads(self.cli('run','--group','downloads','--yes','--json').stdout)
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

    def test_unsupported_native_surface(self):
        env=dict(self.env);env.pop('PREFIX')
        data=json.loads(self.cli('scan','--json',env=env,expected=3,native=True).stdout)
        self.assertEqual(data['status'],'unsupported');self.assertFalse(self.store.directory.exists())
        self.assertEqual(json.loads(self.cli('groups','--json',env=env,native=True).stdout)['platform'],'linux')

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


if __name__ == '__main__':unittest.main()
