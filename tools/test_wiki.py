#!/usr/bin/env python3
"""Wiki generation and command tests; every mutation uses owned temporary roots."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib/dots'))
import wiki
from transactions import Store


class WikiFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='dots wiki ü ');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'source';self.target=self.base/'wiki';self.home=self.base/'home'
        for p in (self.root/'.dots',self.root/'docs',self.root/'bin',self.home,self.target):p.mkdir(parents=True)
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','DOTS_','XDG_'))}
        self.env.update(HOME=str(self.home),USERPROFILE=str(self.home),DOTS=str(self.root),DOTS_WIKI_DIR=str(self.target),XDG_CONFIG_HOME=str(self.home/'config'),XDG_STATE_HOME=str(self.home/'state'),XDG_CACHE_HOME=str(self.home/'cache'),XDG_DATA_HOME=str(self.home/'data'),APPDATA=str(self.home/'config'),LOCALAPPDATA=str(self.home/'data'),GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',GIT_AUTHOR_NAME='Fixture',GIT_COMMITTER_NAME='Fixture',GIT_AUTHOR_EMAIL='fixture@example.invalid',GIT_COMMITTER_EMAIL='fixture@example.invalid',DOTS_COLOR='never',DOTS_ICONS='never')
        self.patcher=patch.dict(os.environ,self.env,clear=True);self.patcher.start();self.addCleanup(self.patcher.stop)
        self.spec=dict(schema=1,checkout='${HOME}/repos/dots.wiki',clone_url='https://github.com/example/test.wiki.git',source_url='https://github.com/example/test',web_url='https://github.com/example/test/wiki',source_branch='main',exclude_docs=[],pages=[dict(id='Home',title='Home',section='Start here',source='docs/home.md'),dict(id='Guide',title='A guide',section='Use Dots',source='docs/guide.md'),dict(id='Commands',title='Commands',section='Reference',generated='commands')])
        self.save_spec()
        (self.root/'docs/home.md').write_text('# Home\n\n[Guide](guide.md#hello-world)\n')
        (self.root/'docs/guide.md').write_text('# Guide\n\n## Hello world\n\n[Home](home.md)\n![Image](../image.png)\n[Code](../bin/dots-sample)\n\n```sh\n[untouched](example.md)\n```\n')
        (self.root/'image.png').write_bytes(b'image')
        (self.root/'bin/dots-sample').write_text('#!/bin/sh\n# dots:summary=Sample command\n# dots:usage=[OPTIONS]\n# dots:option=--json||flag|Data\ntouch '+str(self.base/'EXECUTED')+'\n')
        self.git(self.target,'init','-b','master');(self.target/'Home.md').write_text('Welcome to the dots wiki!\n')
        self.git(self.target,'add','.');self.git(self.target,'-c','commit.gpgSign=false','commit','-m','starter')

    def git(self,path,*args):
        p=subprocess.run(['git','-C',str(path),*args],env=self.env,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr);return p.stdout.strip()

    def save_spec(self): (self.root/'.dots/wiki.json').write_text(json.dumps(self.spec))

    def cli(self,*args,code=0,env=None):
        p=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/wiki.py'),*args],env=env or self.env,cwd=self.base,text=True,capture_output=True,timeout=30)
        self.assertEqual(p.returncode,code,p.stderr+'\n'+p.stdout);return p

    def build(self):return json.loads(self.cli('build','--yes','--json').stdout)


class WikiTests(WikiFixture):
    def test_generation_links_navigation_and_nonexecution(self):
        spec,files,_=wiki.generate(self.root)
        guide=files['Guide.md'].decode()
        self.assertIn('[Home](Home)',guide);self.assertIn('/raw/main/image.png',guide)
        self.assertIn('/blob/main/bin/dots-sample',guide);self.assertIn('[untouched](example.md)',guide)
        self.assertIn('[Guide](Guide#hello-world)',files['Home.md'].decode())
        self.assertIn('**Use Dots**',files['_Sidebar.md'].decode())
        self.assertIn('dots sample',files['Commands.md'].decode());self.assertFalse((self.base/'EXECUTED').exists())
        self.assertIn('/tree/main/bin',files['Commands.md'].decode())
        self.assertEqual(wiki.generate(self.root)[1],files)

    def test_build_check_idempotence_and_undo(self):
        before=list(self.home.rglob('*'))
        self.cli('build','--dry-run','--json');self.assertEqual(list(self.home.rglob('*')),before)
        self.assertEqual((self.target/'Home.md').read_text(),'Welcome to the dots wiki!\n')
        doc=self.build();self.cli('check','--json')
        self.assertEqual(self.build()['status'],'unchanged')
        store=Store(wiki.state_root());ops,guards,catalogs=store.inverse(doc['transaction']);store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertEqual((self.target/'Home.md').read_text(),'Welcome to the dots wiki!\n');self.assertFalse((self.target/'Guide.md').exists())

    def test_drift_and_unknown_files_are_preserved(self):
        self.build();(self.target/'Notes.md').write_text('manual notes')
        (self.root/'docs/guide.md').write_text('# Guide\n\n## Hello world\n\nUpdated\n')
        self.build();self.assertEqual((self.target/'Notes.md').read_text(),'manual notes')
        (self.target/'Guide.md').write_text('manual edit')
        self.cli('check','--json',code=1)
        self.assertIn('reconcile',self.cli('build','--yes','--json',code=1).stderr)
        self.assertEqual((self.target/'Guide.md').read_text(),'manual edit')

    def test_removed_pages_and_inventory_validation(self):
        self.build();self.spec['pages'].pop();self.save_spec();self.build()
        self.assertFalse((self.target/'Commands.md').exists())
        inventory=self.target/wiki.INVENTORY;data=json.loads(inventory.read_text());data['outputs']['../outside.md']='x';inventory.write_text(json.dumps(data))
        self.assertIn('unsafe',self.cli('build','--yes',code=1).stderr)

    def test_source_mapping_and_heading_validation(self):
        (self.root/'docs/new.md').write_text('# New')
        self.assertIn('missing from wiki manifest',self.cli('check','--source-only',code=1).stderr)
        (self.root/'docs/new.md').unlink();(self.root/'docs/home.md').write_text('# Home\n[Broken](guide.md#absent)')
        self.assertIn('broken heading',self.cli('check','--source-only',code=1).stderr)
        self.spec['pages'][1]['id']='home';self.save_spec()
        self.assertIn('duplicate',self.cli('check','--source-only',code=1).stderr)

    def test_reserved_navigation_names_and_malformed_manifest(self):
        self.spec['pages'][1]['id']='AGENTS';self.save_spec()
        self.assertIn('reserved',self.cli('check','--source-only',code=1).stderr)
        self.spec['pages'][1]['id']='Guide';self.spec['pages'][0]['id']='home';self.save_spec()
        self.assertIn('Home page is required',self.cli('check','--source-only',code=1).stderr)
        self.spec.pop('source_url');self.save_spec()
        result=self.cli('check','--source-only',code=1)
        self.assertIn('source_url',result.stderr);self.assertNotIn('Traceback',result.stderr)

    def test_generation_requires_matching_controller_version(self):
        source=self.root/'lib/dots/wiki.py';source.parent.mkdir(parents=True)
        source.write_text('# different generator revision\n')
        self.assertIn('matching Dots checkout',self.cli('check','--source-only',code=1).stderr)

    def test_read_interfaces_and_overrides(self):
        self.build()
        decorated=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')
        self.assertEqual(self.cli('show','Guide','--raw',env=decorated).stdout,(self.target/'Guide.md').read_text())
        self.assertEqual(self.cli('path','Guide','--source',env=decorated).stdout,str(self.root/'docs/guide.md')+'\n')
        self.assertEqual(self.cli('open','Guide','--print-url').stdout,'https://github.com/example/test/wiki/Guide\n')
        self.assertNotIn('\x1b',self.cli('list','--json',env=decorated).stdout)
        self.assertTrue(json.loads(self.cli('--json','list').stdout)['items'])
        self.assertTrue(json.loads(self.cli('search','HELLO','--json').stdout)['items'])
        self.cli('search','no match','--json',code=1)
        self.cli('browse',code=1);self.cli('show','../Home',code=1)
        self.assertFalse((self.base/'EXECUTED').exists())

    def test_source_only_without_checkout(self):
        shutil.rmtree(self.target);self.cli('check','--source-only','--json')
        self.cli('check','--json',code=1);self.cli('init','--dry-run','--json')
        self.assertFalse(self.target.exists())

    def test_transaction_preflight_and_rollback(self):
        operations,guards=wiki.build_plan(self.root,self.target)
        (self.root/'docs/guide.md').write_text('changed after preview')
        with self.assertRaisesRegex(ValueError,'changed after preview'):Store(wiki.state_root()).apply('wiki-build',operations,guards,retain=True)
        self.assertEqual((self.target/'Home.md').read_text(),'Welcome to the dots wiki!\n')
        (self.root/'docs/guide.md').write_text('# Guide\n## Hello world\n')
        operations,guards=wiki.build_plan(self.root,self.target);store=Store(wiki.state_root());save=store.save;failed=False
        def fault(doc):
            nonlocal failed
            save(doc)
            if not failed and any(op['phase']=='done' for op in doc['operations']):failed=True;raise OSError('injected')
        with patch.object(store,'save',side_effect=fault):
            with self.assertRaisesRegex(OSError,'injected'):store.apply('wiki-build',operations,guards,retain=True)
        self.assertEqual((self.target/'Home.md').read_text(),'Welcome to the dots wiki!\n');self.assertFalse((self.target/'Guide.md').exists())

    def test_interrupted_build_recovers_from_durable_journal(self):
        code='''
import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import wiki
root=Path(os.environ['DOTS']);target=Path(os.environ['DOTS_WIKI_DIR'])
ops,guards=wiki.build_plan(root,target)
store=wiki.Store(wiki.state_root());save=store.save
def interrupt(record):
    save(record)
    if any(op['phase']=='done' for op in record['operations']):os._exit(77)
store.save=interrupt
store.apply('wiki-build',ops,guards,retain=True)
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'lib/dots')],env=self.env,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,77,result.stderr)
        store=Store(wiki.state_root());record=store.records()[0]
        self.assertEqual(record['status'],'applying')
        store.recover(record['id'])
        self.assertEqual(store.load(record['id'])['status'],'rolled-back')
        self.assertEqual((self.target/'Home.md').read_text(),'Welcome to the dots wiki!\n')
        self.assertEqual({p.name for p in self.target.iterdir()},{'.git','Home.md'})

    def test_clone_from_local_remote_and_occupied_refusal(self):
        bare=self.base/'wiki.git';self.git(self.base,'clone','--bare',str(self.target),str(bare))
        shutil.rmtree(self.target);self.spec['clone_url']=str(bare);self.save_spec()
        result=json.loads(self.cli('init','--yes','--json').stdout)
        self.assertEqual(result['status'],'cloned');self.assertTrue(Path(result['journal']).is_file())
        self.assertEqual(self.git(self.target,'branch','--show-current'),'master')
        self.assertEqual(json.loads(self.cli('init','--yes','--json').stdout)['status'],'available')
        shutil.rmtree(self.target);self.target.mkdir();(self.target/'keep').write_text('mine')
        self.cli('init','--yes','--json',code=1);self.assertEqual((self.target/'keep').read_text(),'mine')

    def test_editor_and_browser_are_explicit_literal_actions(self):
        editor=self.base/'editor script.py';report=self.base/'editor.json'
        editor.write_text('import json,sys;from pathlib import Path;Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))')
        import shlex
        env=dict(self.env,VISUAL=shlex.join([sys.executable,str(editor),str(report)]))
        self.cli('edit','Guide',env=env)
        self.assertEqual(json.loads(report.read_text()),[str(self.root/'docs/guide.md')])
        with patch('webbrowser.open',return_value=True) as browser:
            self.assertEqual(wiki.main(['open','Guide']),0)
            browser.assert_called_once_with('https://github.com/example/test/wiki/Guide')

    def test_browse_uses_shared_selector_and_preserves_cancellation(self):
        from interaction import SelectionEnded
        with patch.object(sys.stdin,'isatty',return_value=True), patch.object(sys.stdout,'isatty',return_value=True), patch('shutil.which',return_value='available'), patch.dict(os.environ,TERM='xterm-256color'), patch('interaction.Selector.pick',side_effect=SelectionEnded(130)) as pick:
            self.assertEqual(wiki.main(['browse']),130)
            pick.assert_called_once_with('filter','Wiki pages',['Home','Guide','Commands'])

    def test_only_interactive_browse_pages_selected_document(self):
        self.build()
        with patch.object(sys.stdin,'isatty',return_value=True), patch.object(sys.stdout,'isatty',return_value=True), patch('shutil.which',return_value='available'), patch.dict(os.environ,TERM='xterm-256color'), patch('interaction.Selector.pick',return_value='Guide'), patch('themes.file_preview.run_renderer',return_value=b'Entire highlighted document'), patch('menu_pager.page_text') as page:
            self.assertEqual(wiki.main(['browse']),0)
            page.assert_called_once_with(b'Entire highlighted document',title='A guide',defer=True)
        with patch('menu_pager.page_text',side_effect=AssertionError('data path paged')):
            self.assertEqual(self.cli('show','Guide','--raw').stdout,(self.target/'Guide.md').read_text())
            self.assertEqual(self.cli('show','Guide').stdout,(self.target/'Guide.md').read_text())

    def test_frontend_help_completion_and_native_routes(self):
        shutil.copytree(ROOT/'lib/dots',self.root/'lib/dots',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for path in [ROOT/'bin/dots',*ROOT.glob('bin/dots-wiki*')]:shutil.copy2(path,self.root/'bin'/path.name)
        self.build()
        commands=[[str(self.root/'bin/dots'),'wiki','list','--json'],
                  [sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'wiki','list','--json']]
        if os.name=='nt':commands=commands[1:]
        for command in commands:
            result=subprocess.run(command,env=self.env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual([r['id'] for r in json.loads(result.stdout)['items']],['Home','Guide','Commands'])
        commands=[[str(self.root/'bin/dots'),'__complete','bash','3','--','dots','wiki','show','G'],
                  [sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete','wiki','show','G']]
        if os.name=='nt':commands=commands[1:]
        for command in commands:
            result=subprocess.run(command,env=self.env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('candidate\tGuide\t',result.stdout)
        self.assertFalse((self.base/'EXECUTED').exists())

    @unittest.skipIf(os.name=='nt','POSIX PTY')
    def test_terminal_widths_and_plain_navigation(self):
        import errno,fcntl,pty,select,struct,termios,time
        from resources import cells
        self.build()
        for width in (40,80,120):
            master,slave=pty.openpty()
            try:
                fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                process=subprocess.Popen([sys.executable,'-B',str(ROOT/'lib/dots/wiki.py')],env=dict(self.env,TERM='xterm-256color'),stdout=slave,stderr=subprocess.PIPE)
                os.close(slave);slave=None;data=b'';deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    if not select.select([master],[],[],1)[0]:continue
                    try:part=os.read(master,65536)
                    except OSError as error:
                        if error.errno==errno.EIO:break
                        raise
                    if not part:break
                    data+=part
                _,err=process.communicate(timeout=5);self.assertEqual(process.returncode,0,err)
                output=data.decode().replace('\r\n','\n');self.assertIn('Start here',output);self.assertNotIn('\x1b',output)
                for line in output.splitlines():self.assertLessEqual(cells(line),width,line)
            finally:
                os.close(master)
                if slave is not None:os.close(slave)

    @unittest.skipIf(os.name=='nt','POSIX symlink fixture')
    def test_symlink_and_special_file_refusal(self):
        (self.root/'docs/guide.md').unlink();(self.root/'docs/guide.md').symlink_to(self.root/'docs/home.md')
        self.cli('check','--source-only',code=1)
        (self.root/'docs/guide.md').unlink();os.mkfifo(self.root/'docs/guide.md')
        self.cli('check','--source-only',code=1)


if __name__=='__main__':unittest.main()
