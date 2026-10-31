#!/usr/bin/env python3
"""Wiki preferences reach human consumers while data remains exact; owned roots."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_wiki import WikiFixture, ROOT
import test_profile_config as profiles
from config_values import current as controls
from style_config import current as styles
from wiki_presentation import WikiPresentation, document, topics, report


class WikiViews(WikiFixture):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT/'default',self.root/'default')
        self.profile=self.root/'profiles/linux/profile.json'
        self.profile.parent.mkdir(parents=True)
        self.profile.write_text(json.dumps(dict(schema=1,id='linux',settings={},files={})))
        self.env['DOTS_PROFILE']='linux';os.environ['DOTS_PROFILE']='linux'
        controls.cache_clear();styles.cache_clear()
        self.addCleanup(controls.cache_clear);self.addCleanup(styles.cache_clear)

    def settings(self, **groups):
        data=json.loads(self.profile.read_text());data.update(groups)
        self.profile.write_text(json.dumps(data));controls.cache_clear();styles.cache_clear()

    def test_preferences_leave_redirected_and_data_interfaces_exact(self):
        self.build()
        calls=[('list',),('search','hello'),('search','hello','--topics'),('check',),
               ('path','Guide','--source'),('open','Guide','--print-url'),('show','Guide','--source'),
               ('show','Guide','--raw'),('list','--json'),('search','hello','--json'),
               ('search','hello','--topics','--json'),('check','--json'),('build','--dry-run','--json')]
        baseline={args:self.cli(*args).stdout for args in calls}
        self.settings(apps={'wiki':dict(list_details='full',search_snippets=False,search_urls=False,reader='plain')},
                      formatting={'apps':{'wiki':{'row_gap':0},'cli':{'indent':1,'label_width':'40%','label_gap':3,'alignment':'right'}}})
        for args in calls:
            self.assertEqual(self.cli(*args).stdout,baseline[args],args)
            if '--json' in args or args[0] in ('path','open','show'):
                self.assertEqual(self.cli(*args,env=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')).stdout,baseline[args],args)
        env=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='never')
        visible=self.cli('search','hello','--topics',env=env).stdout
        self.assertNotIn('Text',visible);self.assertNotIn('https://',visible)
        listing=self.cli('list',env=env).stdout
        self.assertIn('Source',listing);self.assertIn('guide.md',listing)
        self.assertIn('No matching',self.cli('list','--section','absent',env=env).stdout)

    def test_styles_icons_and_resource_fields_reach_human_reports(self):
        (self.profile.parent/'colors.toml').write_text('[wiki.heading]\nfg="#102030"\nbg="#304050"\nbold=false\n[wiki.page]\nfg="#abcdef"\n[wiki.label]\nfg="#123456"\n[icons.menu.wiki]\nfg="#aabbcc"\n')
        (self.profile.parent/'icons.toml').write_text('[menu]\nwiki="WIKI"\n')
        styles.cache_clear()
        env=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')
        output=self.cli('list',env=env).stdout
        for marker in ('WIKI','38;2;16;32;48','48;2;48;64;80','38;2;171;205;239','38;2;18;52;86','38;2;170;187;204'):
            self.assertIn(marker,output)
        self.assertNotIn('WIKI',self.cli('list',env=dict(env,DOTS_ICONS='never')).stdout)
        # An explicit empty icon overrides the inherited glyph without a stray prefix.
        (self.profile.parent/'icons.toml').write_text('[menu]\nwiki=""\n')
        plain=self.cli('list',env=dict(env,DOTS_COLOR='never')).stdout
        self.assertTrue(plain.startswith('Dots wiki list\n'));self.assertNotIn('\x1b',plain)
        self.build()
        self.settings(apps={'wiki':{'list_details':'full'}})
        output=self.cli('list',env=env).stdout
        self.assertIn('Source',output);self.assertIn('guide.md',output)

    def test_reader_plain_option_literal_text_and_control_safety(self):
        self.settings(apps={'wiki':{'reader':'plain'}})
        ui=WikiPresentation(io.StringIO(),terminal=True)
        text=b'# Literal \\n text\r\n\x1b]52;bad\x07\n'
        with patch('themes.file_preview.run_renderer',side_effect=AssertionError('plain must not invoke renderer')):
            output=document(text,ui)
        self.assertIn(b'Literal \\n text\n',output);self.assertNotIn(b'\x1b',output)
        self.settings(apps={'wiki':{'reader':'auto'}})
        with patch('shutil.which',return_value='bat'),patch('themes.file_preview.run_renderer',return_value=b'highlighted') as render:
            self.assertEqual(document(text,ui),b'highlighted');self.assertIn('--color=never',render.call_args.args[0])

    def test_menu_settings_and_literal_selection_all_backends(self):
        from wiki_browser import pick,choice,browse
        self.settings(apps={'wiki':{'menu_descriptions':False,'section_breadcrumbs':False}},
                      formatting={'apps':{'menu':{'label_width':12,'label_gap':3,'alignment':'right','padding':2}}})
        (self.profile.parent/'colors.toml').write_text('[menu.label]\nfg="#123456"\n')
        styles.cache_clear()
        entry=choice('stable','literal $(no-execute)','Hidden description')
        self.assertEqual(entry.description,'')
        with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='never'):
            ui=WikiPresentation(io.StringIO(),terminal=True)
            with patch('shutil.which',return_value=None),patch('interaction.rich_fzf_available',return_value=True),patch('interaction.RichSelector.fzf',return_value=(0,)) as picker:
                self.assertEqual(pick('Wiki',[entry],ui),0)
                self.assertIn('38;2;18;52;86',picker.call_args.args[1][0])
                self.assertIn('$(no-execute)',picker.call_args.args[1][0]);self.assertTrue(picker.call_args.kwargs['wrap'])
            with patch('shutil.which',return_value='fixture'),patch.dict(os.environ,TERM='xterm-256color'),patch('interaction.Selector.pick',side_effect=lambda kind,title,labels:labels[0]) as gum:
                self.assertEqual(pick('Wiki',[entry],ui),0)
                self.assertNotIn('\x1b',gum.call_args.args[2][0])
            with patch('shutil.which',return_value=None),patch('interaction.rich_fzf_available',return_value=False),patch('builtins.input',return_value='1'):
                self.assertEqual(pick('Wiki',[entry],ui),0)
                self.assertIn('$(no-execute)',ui.stream.getvalue())
            with patch('shutil.which',return_value=None),patch('interaction.rich_fzf_available',return_value=False),patch('builtins.input',side_effect=EOFError):
                self.assertIsNone(pick('Wiki',[entry],ui))
        (self.root/'docs/guide.md').write_text('# Guide\n\n## Parent\n\n### Child\n\ntext\n\n## Whole\n\n## Back\n')
        choices=[]
        def capture(title,entries,ui,**kwargs):
            choices.append(entries)
            return 1 if title=='Wiki pages' and len(choices)==1 else (len(entries)-1 if title=='A guide' else None)
        with patch('wiki_browser.pick',side_effect=capture):browse(self.root,None,ui)
        self.assertEqual([e.label for e in choices[1]],['Whole page','Parent','Child','Whole','Back','Back'])
        self.assertEqual(len({e.id for e in choices[1]}),len(choices[1]))

    @unittest.skipIf(os.name=='nt','POSIX PTY; native PowerShell visual acceptance pending')
    def test_automatic_terminal_policy_and_all_reports_40_80_120(self):
        import errno,fcntl,pty,select,struct,termios,time
        from resources import cells
        self.settings(formatting={'apps':{'cli':{'label_width':'40%','label_gap':2,'alignment':'right'}}})
        actions=[([],0),(['list'],0),(['list','--section','absent'],0),(['search','hello','--topics'],0),
                 (['search','no-match','--topics'],1),(['check'],1),(['build','--dry-run'],0),
                 (['init','--dry-run'],0),(['show','absent'],1)]
        for width in (40,80,120):
            for args,code in actions:
                master,slave=pty.openpty()
                try:
                    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                    env=dict(self.env,TERM='xterm-256color',DOTS_COLOR='auto',DOTS_ICONS='never',NO_COLOR='1',COLUMNS=str(width))
                    p=subprocess.Popen([sys.executable,'-B',str(ROOT/'lib/dots/wiki.py'),*args],env=env,stdout=slave,stderr=slave)
                    os.close(slave);slave=None;data=b'';deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        if not select.select([master],[],[],.1)[0]:continue
                        try:chunk=os.read(master,65536)
                        except OSError as error:
                            if error.errno==errno.EIO:break
                            raise
                        if not chunk:break
                        data+=chunk
                    self.assertEqual(p.wait(timeout=5),code,data.decode());self.assertNotIn(b'\x1b',data)
                    for line in data.decode().splitlines():self.assertLessEqual(cells(line),width,(args,line))
                finally:
                    if slave is not None:os.close(slave)
                    os.close(master)


class WikiConfig(unittest.TestCase):
    def run_config(self,*args,native=False,**kwargs):
        return profiles.ProfileConfig.run_config(self,*args,native=native or os.name=='nt',**kwargs)

    def setUp(self):
        profiles.ProfileConfig.setUp(self)
        shutil.copytree(ROOT/'default',self.root/'default')
        self.env['TERM']='xterm-256color'
        self.patcher=patch.dict(os.environ,self.env,clear=True);self.patcher.start();self.addCleanup(self.patcher.stop)
        controls.cache_clear();styles.cache_clear()
        self.addCleanup(controls.cache_clear);self.addCleanup(styles.cache_clear)

    def test_saved_config_discovery_validation_inheritance_reset_and_consumer(self):
        from config_menu import Inventory,Draft
        from config_refresh import after_save,effective
        from config_values import candidates
        from profile_config import keys
        self.assertIn('colors.wiki.page.bg',keys(self.root));self.assertIn('icons.menu.wiki',keys(self.root))
        self.assertEqual(candidates(self.root,'apps.wiki.reader'),['auto','plain'])
        row=Inventory(self.root,self.platform).find('apps.wiki.reader')
        self.assertEqual(row.constraints['choices'],['auto','plain']);self.assertIn('next invocation',row.description)
        before=effective(self.root);Draft(Inventory(self.root,self.platform),row).prepare('plain').plan.apply('set')
        with patch('config_refresh.refresh',side_effect=AssertionError('display save must not publish')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='wiki',status='next invocation or popup')])
        self.assertEqual(self.run_config('get','apps.wiki.reader',native=True,DOTS_COLOR='always').stdout,'plain\n')
        explanation=json.loads(self.run_config('explain','apps.wiki.reader','--json').stdout)
        self.assertIn('next Wiki',explanation['activation']);self.assertEqual(explanation['source'],str(self.path))
        for key,bad in [('apps.wiki.reader','shell'),('apps.wiki.list_details','all'),('apps.wiki.search_urls','42'),('formatting.apps.wiki.row_gap','5')]:
            self.run_config('set',key,bad,'--no-refresh',code=1)
        self.run_config('unset','apps.wiki.reader','--no-refresh')
        self.assertEqual(self.run_config('get','apps.wiki.reader').stdout,'auto\n')
        self.run_config('set','apps.wiki.search_urls','false','--no-refresh')
        controls.cache_clear()
        output=io.StringIO();ui=WikiPresentation(output,terminal=True)
        hit=dict(title='Guide',page='Guide',heading='Section',breadcrumb='Guide / Section',text='A snippet',url='https://example.invalid')
        topics(ui,'a',[hit]);self.assertNotIn('https://',output.getvalue());self.assertIn('A snippet',output.getvalue())
        before=effective(self.root)
        self.run_config('set','formatting.apps.wiki.row_gap','0','--no-refresh')
        controls.cache_clear()
        with patch('config_refresh.refresh',side_effect=AssertionError('spacing must not publish')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='wiki',status='next invocation')])
        output=io.StringIO();topics(WikiPresentation(output,terminal=True),'a',[hit,hit]);self.assertNotIn('\n\n',output.getvalue())
        before=effective(self.root)
        self.run_config('set','colors.wiki.snippet.fg','#abcdef','--no-refresh')
        styles.cache_clear()
        with patch('config_refresh.refresh',side_effect=AssertionError('Wiki styles must not publish')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='wiki',status='next invocation or popup')])
        with patch.dict(os.environ,DOTS_COLOR='always'):
            output=io.StringIO();topics(WikiPresentation(output,terminal=True),'a',[hit])
            self.assertIn('38;2;171;205;239',output.getvalue())
        self.run_config('set','apps.wiki.search_urls','null','--json-value','--no-refresh')
        self.assertEqual(self.run_config('get','apps.wiki.search_urls').stdout,'true\n')

    def test_parent_overrides_completion_and_configuration_menu(self):
        from config_values import Controls
        from profile_config import context
        from menu_cli import FAMILIES
        parent=self.root/'profiles/linux/profile.json'
        data=json.loads(parent.read_text());data['apps']={'wiki':{'reader':'plain','search_urls':False}}
        parent.write_text(json.dumps(data))
        child=parent.parent/'distros/wiki';child.mkdir(parents=True)
        path=child/'profile.json'
        path.write_text(json.dumps(dict(schema=1,id='linux/wiki',extends=['linux'],apps={'wiki':{'search_urls':True}})))
        resolved=Controls(self.root,context(self.root,'linux/wiki'))
        self.assertEqual(resolved.resolve('apps.wiki.reader')['value'],'plain')
        self.assertTrue(resolved.resolve('apps.wiki.search_urls')['value'])
        action=next(a for a in FAMILIES['wiki'] if a.id=='configuration')
        self.assertEqual((action.route,action.options,action.kind),(('config','browse'),('--query','wiki'),'popup'))
        for shell in ('native','bash'):
            if shell=='bash' and os.name=='nt':continue
            prefix=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete'] if shell=='native' else
                    [str(self.root/'bin/dots'),'__complete','bash','4','--','dots'])
            result=subprocess.run(prefix+['config','set','apps.wiki.reader',''],env=self.env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            for choice in ('auto','plain'):self.assertIn('candidate\t'+choice+'\t',result.stdout)


if __name__=='__main__':unittest.main()
