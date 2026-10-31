#!/usr/bin/env python3
"""Offline topic, source reader and data-contract acceptance in owned roots."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_wiki import WikiFixture, ROOT
import wiki
from wiki_topics import headings, snapshot, search


class Topics(WikiFixture):
    def test_offline_ranking_sections_and_no_writes(self):
        shutil.rmtree(self.target)
        (self.root/'docs/guide.md').write_text('# Guide\n\n## Config precedence\n\nParent overrides and config values.\n\n### Child\n\nchild-only secret phrase\n\n## Environment variables\n\nDifferent section.\n')
        before = sorted(str(p) for p in self.base.rglob('*'))
        doc = json.loads(self.cli('search','CONFIG precedence','--topics','--json').stdout)
        decorated=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')
        self.assertEqual(json.loads(self.cli('search','CONFIG precedence','--topics','--json',env=decorated).stdout),doc)
        hit = doc['items'][0]
        self.assertEqual((doc['schema'],doc['mode'],hit['page'],hit['anchor']), (1,'topics','Guide','config-precedence'))
        self.assertEqual(hit['line'],3)
        self.assertTrue(hit['url'].endswith('/Guide#config-precedence'))
        self.assertNotIn('content',hit)
        self.assertEqual(sorted(str(p) for p in self.base.rglob('*')), before)
        self.assertEqual(self.cli('search','no match','--topics','--json',code=1).stdout,
                         '{"schema": 1, "mode": "topics", "query": "no match", "items": []}\n')
        self.cli('search','   ','--topics',code=1)
        self.cli('search','config','--titles','--topics',code=2)
        _,rows=snapshot(self.root)
        self.assertEqual([r['heading'] for r in search(rows,'child-only secret phrase')], ['Child'])

    def test_fences_unicode_duplicates_and_literal_queries(self):
        text='# Guide\n\n## Café `value`\n\n```sh\n## fake\n~~~\n```\n\n## Café `value`\n\n### Nested\n\n## Other\n'
        rows=headings(text)
        self.assertEqual([r['anchor'] for r in rows], ['guide','café-value','café-value-1','nested','other'])
        (self.root/'docs/guide.md').write_text(text+'\nLiteral $(touch NOT-RUN) and [regex].\n')
        doc=json.loads(self.cli('search','$(touch NOT-RUN)','--topics','--json').stdout)
        self.assertTrue(doc['items'])
        self.assertFalse((self.base/'NOT-RUN').exists())
        self.assertEqual(wiki.anchors(text),set(r['anchor'] for r in rows))

    def test_legacy_search_and_raw_bytes(self):
        self.build()
        path=self.target/'Guide.md'
        data=path.read_bytes()
        expected=[dict(page=row['id'],line=i,text=line) for row in self.spec['pages']
                  for i,line in enumerate((self.target/(row['id']+'.md')).read_text().splitlines(),1) if 'hello' in line.lower()]
        doc=json.loads(self.cli('search','HELLO','--json').stdout)
        self.assertEqual(doc,dict(schema=1,items=expected))
        decorated=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')
        self.assertEqual(self.cli('show','Guide','--raw',env=decorated).stdout.encode(),data)
        path.write_text('stale generated text')
        self.assertTrue(json.loads(self.cli('search','hello','--topics','--json').stdout)['items'])

    def test_section_reader_full_page_back_cancel_and_no_optional_tools(self):
        from wiki_browser import browse, pick
        from catalog import Presentation
        ui=Presentation(io.StringIO())
        # Source browsing is independent of a generated export.
        shutil.rmtree(self.target)
        with patch('wiki_browser.pick',return_value=0), patch('shutil.which',return_value='fixture'), patch('themes.file_preview.run_renderer',return_value=None), patch('menu_pager.page_text') as page:
            self.assertEqual(browse(self.root,'hello',ui),0)
            content=page.call_args.args[0].decode()
            self.assertIn('Hello world',content)
            self.assertIn('A guide',content)
            self.assertTrue(page.call_args.kwargs['defer'])
        with patch('wiki_browser.pick',side_effect=[1,None,1,0]), patch('shutil.which',return_value='fixture'), patch('themes.file_preview.run_renderer',return_value=None), patch('menu_pager.page_text') as page:
            self.assertEqual(browse(self.root,None,ui),0)
            self.assertEqual(page.call_args.args[0],(self.root/'docs/guide.md').read_bytes())
        (self.root/'docs/guide.md').write_bytes(b'# Guide\r\n\r\n## Hello world\r\n\r\nText.\r\n')
        with patch('wiki_browser.pick',side_effect=[1,0]), patch('shutil.which',return_value='fixture'), patch('themes.file_preview.run_renderer',return_value=None), patch('menu_pager.page_text') as page:
            browse(self.root,None,ui)
            self.assertEqual(page.call_args.args[0],b'# Guide\n\n## Hello world\n\nText.\n')
        with patch('shutil.which',return_value=None), patch('interaction.rich_fzf_available',return_value=False), patch('builtins.input',return_value='2'):
            self.assertEqual(pick('Topic',['First','Second'],ui),1)
        with patch('wiki_browser.pick',return_value=None):
            self.assertEqual(browse(self.root,'hello',ui),0)

    def test_topic_flags_reach_both_frontends_and_completion(self):
        shutil.copytree(ROOT/'lib/dots',self.root/'lib/dots',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for path in [ROOT/'bin/dots',*ROOT.glob('bin/dots-wiki*')]:shutil.copy2(path,self.root/'bin'/path.name)
        frontends=[[sys.executable,'-B',str(self.root/'lib/dots/cli.py')]]
        if os.name!='nt':frontends.append([str(self.root/'bin/dots')])
        for frontend in frontends:
            result=subprocess.run(frontend+['wiki','search','hello','--topics','--json'],env=self.env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['items'][0]['page'],'Guide')
        native=[sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete']
        for route,flag in [('search','--topics'),('browse','--query')]:
            p=subprocess.run(native+['wiki',route,'--'],env=self.env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('candidate\t'+flag+'\t',p.stdout)
            if os.name!='nt':
                p=subprocess.run([str(self.root/'bin/dots'),'__complete','bash','3','--','dots','wiki',route,'--'],env=self.env,capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr);self.assertIn('candidate\t'+flag+'\t',p.stdout)

    @unittest.skipIf(os.name=='nt','POSIX PTY')
    def test_topic_views_at_40_80_120_columns(self):
        import errno,fcntl,pty,select,struct,termios,time
        from resources import cells
        for width in (40,80,120):
            master,slave=pty.openpty()
            try:
                fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                p=subprocess.Popen([sys.executable,'-B',str(ROOT/'lib/dots/wiki.py'),'search','hello','--topics'],
                    env=dict(self.env,TERM='xterm-256color'),stdout=slave,stderr=subprocess.PIPE)
                os.close(slave);slave=None;data=b'';deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    if not select.select([master],[],[],.2)[0]:continue
                    try:chunk=os.read(master,65536)
                    except OSError as error:
                        if error.errno==errno.EIO:break
                        raise
                    if not chunk:break
                    data+=chunk
                _,err=p.communicate(timeout=5);self.assertEqual(p.returncode,0,err)
                text=data.decode().replace('\r\n','\n')
                self.assertIn('Hello world',text)
                for line in text.splitlines():self.assertLessEqual(cells(line),width,line)
            finally:
                if slave is not None:os.close(slave)
                os.close(master)

    def test_top_three_current_documentation_queries(self):
        # Read repository docs only; no environment, application or export mutation.
        _,records=snapshot(ROOT)
        cases={'config precedence':{'Configuration'},'environment variables':{'Environment'},
               'nvim themes':{'Neovim'},'files rollback':{'Files','Safety','Core'},
               'wiki search':{'Wiki','Command-reference'}}
        for query,pages in cases.items():
            self.assertTrue(pages & {r['page'] for r in search(records,query)[:3]},query)


if __name__=='__main__':unittest.main()
