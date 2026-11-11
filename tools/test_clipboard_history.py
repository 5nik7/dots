#!/usr/bin/env python3
"""History, CLI and capture contracts; all stores/providers belong to fixtures."""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib/dots'))
from clipboard_history import History, DEFAULTS
import clipboard_watch


class Storage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='dots-history-store-'); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state with spaces 雪'
        self.history=History(self.path,settings={})

    def test_absent_reads_never_create_state(self):
        self.assertEqual(self.history.rows(),[])
        self.assertEqual(self.history.control('paused',False),False)
        with self.assertRaises(ValueError): self.history.get('a'*32)
        self.assertFalse(self.path.exists())

    def test_unicode_dedup_pins_retention_and_revisions(self):
        row=self.history.add('雪\n\n',source='manual')
        duplicate=self.history.add('雪\n\n',source='cpy')
        self.assertEqual(row['id'],duplicate['id'])
        self.assertEqual(len(self.history.rows()),1)
        with self.assertRaisesRegex(ValueError,'changed'): self.history.change([row],delete=True)
        self.history.change([duplicate],pinned=True)
        self.history.settings['max_entries']=2
        second=self.history.add('second'); self.history.add('third')
        self.assertEqual({r['text'] for r in self.history.rows()},{'雪\n\n','third'})
        self.assertTrue(self.history.get(row['id'])['pinned'])
        with self.assertRaises(ValueError):self.history.get(second['id'])
        with self.history.connect(True) as db:
            db.execute("UPDATE entries SET updated='2000-01-01T00:00:00.000000+00:00'")
        candidates=self.history.prune_candidates()
        self.assertEqual([r['text'] for r in candidates],['third'])
        self.history.change(candidates,delete=True)
        self.assertEqual(self.history.control('last_digest'),None)
        self.assertEqual(len(self.history.rows()),1)

    def test_atomic_import_rejects_invalid_batch_and_pin_overflow(self):
        original=self.history.add('retain me',pinned=True)
        before=self.history.rows()
        for rows in ([dict(text='valid'),dict(text=4)], [dict(text='x'*70000)]):
            with self.assertRaises(ValueError):self.history.import_entries(dict(schema=1,entries=rows))
            self.assertEqual(self.history.rows(),before)
        self.history.settings['max_entries']=1
        with self.assertRaisesRegex(ValueError,'pinned'):
            self.history.import_entries(dict(schema=1,entries=[dict(text='new pinned',pinned=True)]))
        self.assertEqual(self.history.rows(),before)
        self.assertEqual(self.history.get(original['id'])['text'],'retain me')

    def test_exclusions_pause_and_self_duplicate(self):
        self.history.settings['exclude_patterns']=['*private*']
        self.assertIsNone(self.history.add('private text'))
        self.assertFalse(self.path.exists())
        first=self.history.add('public',automatic=True)
        self.assertIsNone(self.history.add('public',automatic=True))
        self.history.set_control('paused',True)
        self.assertIsNone(self.history.add('different',automatic=True))
        self.assertIsNotNone(self.history.add('explicit'))
        self.assertEqual(len(self.history.rows()),2)

    def test_parallel_writers_and_secure_delete(self):
        def write(index):return History(self.path,settings={}).add('text '+str(index))
        with ThreadPoolExecutor(max_workers=5) as pool: list(pool.map(write,range(20)))
        self.assertEqual(len(self.history.rows()),20)
        secret='UNIQUE_CLEARABLE_CLIPBOARD_PAYLOAD'
        row=self.history.add(secret)
        self.history.change([row],delete=True)
        self.assertNotIn(secret.encode(),self.history.path.read_bytes())
        self.assertFalse(self.history.path.with_name('history.sqlite3-journal').exists())
        if os.name!='nt':
            self.assertEqual(self.history.path.stat().st_mode & 0o777,0o600)
            self.assertEqual(self.path.stat().st_mode & 0o777,0o700)

    def test_symlink_store_refused(self):
        if os.name=='nt':self.skipTest('native link permission not assumed')
        other=self.path.parent/'other';other.mkdir()
        self.path.symlink_to(other,target_is_directory=True)
        with self.assertRaises(ValueError):self.history.add('never written')
        self.assertEqual(list(other.iterdir()),[])

    def test_watcher_lease_pause_failure_and_stop_races(self):
        token='a'*32
        self.history.set_control('watch',dict(token=token,status='starting',heartbeat=time.time()))
        with patch('clipboard.paste',return_value=b'watched') as paste:
            self.assertTrue(clipboard_watch.tick(self.history,token))
            self.assertTrue(clipboard_watch.tick(self.history,token))
        self.assertEqual(len(self.history.rows()),1)
        self.history.set_control('paused',True)
        with patch('clipboard.paste',side_effect=AssertionError('must not read paused clipboard')):
            self.assertTrue(clipboard_watch.tick(self.history,token))
        self.history.set_control('paused',False)
        with patch('clipboard.paste',side_effect=ValueError('secret details')):
            clipboard_watch.tick(self.history,token)
        state=clipboard_watch.status(self.history)
        self.assertEqual(state['status'],'degraded');self.assertNotIn('secret',json.dumps(state))
        def stop_during_read():
            clipboard_watch.stop(self.history)
            return b'must not be recorded'
        with patch('clipboard.paste',side_effect=stop_during_read):
            self.assertFalse(clipboard_watch.tick(self.history,token))
        self.assertEqual(len(self.history.rows()),1)
        self.history.set_control('watch',dict(token=token,status='running',heartbeat=1))
        self.assertEqual(clipboard_watch.status(self.history)['status'],'stale')


class Commands(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='dots-history-cli-');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.repo=self.base/'repo 雪';self.repo.mkdir()
        shutil.copytree(ROOT/'default',self.repo/'default')
        for name in ('termux','linux','wsl','windows'):
            path=self.repo/'profiles'/name;path.mkdir(parents=True)
            (path/'profile.json').write_text(json.dumps(dict(schema=1,id=name)))
        self.env=dict(os.environ,DOTS=str(self.repo),HOME=str(self.base/'home'),
                      XDG_CONFIG_HOME=str(self.base/'config'),XDG_STATE_HOME=str(self.base/'state'),
                      XDG_CACHE_HOME=str(self.base/'cache'),XDG_DATA_HOME=str(self.base/'data'),
                      DOTS_COLOR='never',DOTS_ICONS='never',DOTS_PROGRESS='never',PYTHONDONTWRITEBYTECODE='1')
        for name in ('DOTS_PROFILE','DOTS_CONFIG_FILE','DOTS_MENU_CONTEXT','TMUX','TMUX_PANE','DOTS_STYLE_ROOT'):
            self.env.pop(name,None)
        self.store=self.base/'state/dots/clipboard'

    def cli(self,*args,input=b'',check=True,native=False):
        if native:
            # Native dispatch exercises the same Python route without a Windows engine.
            command=[sys.executable,'-B',str(ROOT/'lib/dots/cli.py'),'clipboard',*args]
        else:command=[sys.executable,'-B',str(ROOT/'lib/dots/clipboard_cli.py'),*args]
        result=subprocess.run(command,input=input,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        if check:self.assertEqual(result.returncode,0,result.stderr.decode())
        return result

    def add(self,text):return json.loads(self.cli('add',text,'--json').stdout)['items'][0]['id']

    def test_read_only_and_help_and_dry_runs(self):
        for args in (('--help',),('list','--json'),('clear','--dry-run','--json'),('capture','--dry-run','--json'),('watch','start','--dry-run','--json'),('pause','--dry-run','--json')):
            self.cli(*args)
        self.assertFalse(self.store.exists())

    def test_cli_literal_data_filters_export_import_and_destructive_scope(self):
        identity=self.add('雪\n$(touch nope)\n\n')
        self.assertEqual(self.cli('print',identity).stdout,'雪\n$(touch nope)\n\n'.encode())
        self.env.update(DOTS_COLOR='always',DOTS_ICONS='always')
        self.assertEqual(self.cli('show',identity,'--raw').stdout,'雪\n$(touch nope)\n\n'.encode())
        rows=json.loads(self.cli('search','雪','--json').stdout)['items'];self.assertEqual(rows[0]['id'],identity)
        self.cli('pin',identity,'--json')
        self.cli('clear','--yes','--json')
        self.assertEqual(len(json.loads(self.cli('list','--json').stdout)['items']),1)
        preview=json.loads(self.cli('clear','--include-pinned','--dry-run','--json').stdout)
        self.assertEqual(preview['items'][0]['id'],identity)
        refusal=self.cli('remove',identity,'--json',check=False);self.assertNotEqual(refusal.returncode,0)
        exported=self.cli('export').stdout
        self.cli('clear','--include-pinned','--yes','--json')
        self.cli('import','--json',input=exported)
        self.assertEqual(json.loads(self.cli('export').stdout),json.loads(exported))
        self.assertFalse((self.base/'nope').exists())

    def test_config_consumers_and_literal_copy_hook(self):
        defaults=self.repo/'default/config.json';doc=json.loads(defaults.read_text());doc['apps']['clipboard'].update(record_copies=True,max_entries=1,exclude_patterns=['secret*']);defaults.write_text(json.dumps(doc))
        script="""import sys
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
import clipboard
with patch('clipboard._run'):
    clipboard.copy('first')
    clipboard.copy('second')
    clipboard.copy('secret content')
"""
        result=subprocess.run([sys.executable,'-B','-c',script,str(ROOT/'lib/dots')],env=self.env,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        rows=json.loads(self.cli('list','--json').stdout)['items']
        self.assertEqual([r['text'] for r in rows],['second'])
        self.cli('pause','--json')
        result=subprocess.run([sys.executable,'-B','-c',script,str(ROOT/'lib/dots')],env=self.env,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.cli('list','--json').stdout)['items'],rows)

    def test_detached_watcher_uses_owned_store_and_provider(self):
        fake=self.base/'fake bin';fake.mkdir()
        payload=self.base/'clipboard input';payload.write_text('external 雪\n')
        script='#!'+sys.executable+'\nimport os,sys\nfrom pathlib import Path\nsys.stdout.buffer.write(Path(os.environ["FIXTURE_CLIP"]).read_bytes())\n'
        for name in ('termux-clipboard-get','wl-paste','xclip','xsel'):
            path=fake/name;path.write_text(script);path.chmod(0o700)
        env=dict(self.env,PATH=str(fake)+os.pathsep+self.env['PATH'],FIXTURE_CLIP=str(payload),WAYLAND_DISPLAY='fixture')
        defaults=self.repo/'default/config.json';doc=json.loads(defaults.read_text());doc['apps']['clipboard']['poll_seconds']=1;defaults.write_text(json.dumps(doc))
        original=subprocess.Popen;workers=[]
        def launch(*a,**kw):
            child=original(*a,**kw);workers.append(child);return child
        with patch.dict(os.environ,env,clear=True):
            history=History()
            try:
                with patch('clipboard_watch.subprocess.Popen',side_effect=launch):clipboard_watch.start(history)
                deadline=time.monotonic()+10
                while not history.rows() and time.monotonic()<deadline:time.sleep(.1)
                self.assertEqual([r['text'] for r in history.rows()],['external 雪\n'])
                with self.assertRaisesRegex(ValueError,'already running'):clipboard_watch.start(history)
                history.set_control('paused',True)
                payload.write_text('next external')
                time.sleep(1.2)
                self.assertEqual(len(history.rows()),1)
                history.set_control('paused',False)
                deadline=time.monotonic()+5
                while len(history.rows())<2 and time.monotonic()<deadline:time.sleep(.1)
                self.assertEqual(len(history.rows()),2)
            finally:
                clipboard_watch.stop(history)
                for child in workers:child.wait(timeout=12)
            self.assertEqual(clipboard_watch.status(history)['status'],'stopped')

    def test_frontends_and_six_shell_completion(self):
        (self.repo/'bin').symlink_to(ROOT/'bin',target_is_directory=True)
        (self.repo/'lib').symlink_to(ROOT/'lib',target_is_directory=True)
        identity=self.add('completion text')
        self.assertEqual(json.loads(self.cli('list','--json',native=True).stdout)['items'][0]['id'],identity)
        for shell in ('bash','zsh','fish','powershell','nu','xonsh'):
            args=['bash',str(ROOT/'bin/dots'),'__complete',shell,'3','--','dots','clipboard','copy',''] if shell!='powershell' else [sys.executable,'-B',str(ROOT/'lib/dots/cli.py'),'__complete','clipboard','copy','']
            result=subprocess.run(args,env=self.env,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(('candidate\t'+identity+'\t').encode(),result.stdout)
        for args,expected in [(('watch','s'),'start'),(('init','p'),'powershell'),(('list','--source='),'watch')]:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/clipboard_commands.py'),*args],env=self.env,capture_output=True)
            self.assertIn(expected.encode(),result.stdout)
        result=subprocess.run([str(ROOT/'bin/dots'),'clipboard','watch','status','--json'],env=self.env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['watch_status'],'stopped')

    def test_bash_and_zsh_widgets_preserve_input_without_evaluation(self):
        from clipboard_widgets import code
        text='雪\n$(touch should-not-exist)\n\n'
        request=json.dumps(dict(schema=1,text=text))
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            fake="dots() { printf '%s' "+__import__('shlex').quote(request)+"; }\nbind() { :; }\nbindkey() { :; }\nzle() { :; }\n"
            setup="READLINE_LINE='prePOST'; READLINE_POINT=3; _dots_clipboard_widget; printf '%s' \"$READLINE_LINE\"" if shell=='bash' else "LBUFFER=pre; _dots_clipboard_widget; printf '%s' \"${LBUFFER}POST\""
            result=subprocess.run([shell,'-c',fake+code(shell)+setup],env=self.env,cwd=self.base,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,('pre'+text+'POST').encode())
            self.assertFalse((self.base/'should-not-exist').exists())
        if shutil.which('fish'):
            fake="function dots; printf '%s' "+__import__('shlex').quote(request)+"; end\nfunction commandline; if test \"$argv[1]\" = --insert; printf '%s' \"$argv[3]\"; end; end\n"
            result=subprocess.run(['fish','-c',fake+code('fish')+'\n_dots_clipboard_widget'],env=self.env,cwd=self.base,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,text.encode())
        # Cancelling the picker produces neither inserted text nor decoder errors.
        result=subprocess.run(['bash','-c',"dots() { return 130; }; bind() { :; };\n"+code('bash')+"READLINE_LINE=keep; READLINE_POINT=4; _dots_clipboard_widget; printf %s \"$READLINE_LINE\""],env=self.env,capture_output=True)
        self.assertEqual(result.stdout,b'keep');self.assertEqual(result.stderr,b'')

    def test_invalid_import_and_usage_preserve_history(self):
        self.add('retained');before=self.cli('export').stdout
        for data in (b'not json',b'{"schema":1,"entries":[{"text":"okay"},{"text":42}]}'):
            self.assertNotEqual(self.cli('import',input=data,check=False).returncode,0)
            self.assertEqual(self.cli('export').stdout,before)
        self.assertNotEqual(self.cli('list','--limit','-1',check=False).returncode,0)
        self.assertNotEqual(self.cli('list','--since','bad',check=False).returncode,0)

    def test_insertion_control_refusal_and_shell_widgets(self):
        from clipboard_menu import insertion_text
        for text in ('a\x1b[201~danger','x\rcommand','\0','\x7f'):
            with self.assertRaises(ValueError):insertion_text(text)
        self.assertEqual(insertion_text('a\n雪\t'),'a\n雪\t')
        for shell in ('bash','zsh','fish','powershell'):
            output=self.cli('init',shell).stdout.decode()
            self.assertNotIn('\x1b',output)
            self.assertIn('clipboard pick --json',output)
            if shell!='powershell' and shutil.which(shell):
                result=subprocess.run([shell,'-n'],input=output.encode(),env=self.env,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.store.exists())


if __name__=='__main__':unittest.main()
