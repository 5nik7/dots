#!/usr/bin/env python3
"""Existing-key Config fallbacks and repeatable categories in owned roots."""
import copy
import io
import json
import os
import re
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_config_alignment as fixtures
import test_profile_config as profile_fixtures
from config_fallbacks import Fallbacks,fzf_values,fzf_sample
from config_view import listing,Glyph
from profile_config import context
from style_config import Styles
from files.catalog import Presentation
from resources import cells


class ConfigList(unittest.TestCase):
    setUp=fixtures.Alignment.setUp

    def publication(self):
        state=self.home/'state/dots';generation=state/'themes/generations/g.test'
        generation.mkdir(parents=True);(generation/'id').write_text('fixture\n')
        (state/'current').mkdir();(state/'current/theme').symlink_to(generation)
        (generation/'fzf.sh').write_text('export _FZF_COLORS_="fg+:strip:#123456:bold,bg:-1,fg:regular,preview-label:red,preview-label:blue,madeup:green"\n')
        return generation

    def test_only_existing_keys_receive_fallbacks_no_inventory_or_execution(self):
        self.publication()
        config={'apps':{'fzf':{'colors':{'fg+':None,'bg':None,'fg':None,'preview-label':None,'nth':None}}},
                'formatting':{'apps':{'tmux':{'main_row':None,'termux_row':None}}}}
        original=copy.deepcopy(config);styles=Styles(self.root)
        with patch('subprocess.run',side_effect=AssertionError('no execution')),patch('files.catalog.Catalog.records',side_effect=AssertionError('no inventory')):
            result=Fallbacks(styles,config).tree(config)
        self.assertEqual(config,original)
        def keys(value,path=()):
            return [p for key,item in value.items() for p in (keys(item,(*path,key)) if isinstance(item,dict) else [(*path,key)])]
        self.assertEqual(keys(result),keys(original))
        colors=result['apps']['fzf']['colors']
        self.assertEqual(colors['fg+'].text,'fg:#123456,bold,strip')
        self.assertIn('38;2;18;52;86',colors['fg+'].code)
        self.assertIn('default/themed/fzf.sh.tpl',colors['fg+'].annotation)
        self.assertEqual(colors['bg'].text,'bg:default')
        self.assertEqual(colors['fg'].text,'regular')
        self.assertEqual(colors['preview-label'].text,'fg:blue')
        self.assertEqual(colors['nth'].text,'inherited')
        self.assertNotIn('madeup',colors)
        self.assertEqual(result['formatting']['apps']['tmux']['main_row'].text,'1' if self.platform=='termux' else '0')

    def test_override_scope_runtime_owners_and_literal_safety(self):
        generation=self.publication();styles=Styles(self.root)
        config={'apps':{'fzf':{'colors':{'fg+':'red:underline'}}}}
        reader=Fallbacks(styles,config)
        with patch.object(reader,'fzf',side_effect=AssertionError('override does not need publication')):
            value=reader.tree(config)['apps']['fzf']['colors']['fg+']
        self.assertEqual(value.text,'fg:red,underline');self.assertEqual(value.annotation,'')
        inactive='windows' if self.platform!='windows' else 'linux'
        for selected in (Styles(self.root,context(self.root,inactive)),Styles(self.root,defaults=True)):
            scoped=Fallbacks(selected,{})
            value=scoped.leaf(('apps','fzf','colors','fg+'),None)
            self.assertEqual(value.text,'inherited');self.assertNotIn('123456',value.code)
            with patch('config_fallbacks.read_data',side_effect=AssertionError('no other-scope provider inspection')):
                value=scoped.leaf(('apps','tmux','battery','critical'),None)
                self.assertEqual(value.text,'inherited')
                self.assertIn('not inspected',value.annotation)
        value=reader.leaf(('apps','nvim','options','number'),None)
        self.assertEqual(value.text,'runtime value');self.assertIn('dots_config.lua',value.annotation)
        marker=reader.leaf(('apps','tmux','indicators','working','text'),None)
        self.assertEqual(marker.text,styles.icon('status.working',app='tmux'))
        (generation/'fzf.sh').write_text('export _FZF_COLORS_="fg:$(touch NEVER)"\n')
        self.assertEqual(fzf_values((generation/'fzf.sh').read_text()),{})
        self.assertFalse((self.root/'NEVER').exists())

    def test_categories_json_errors_and_frontend_completion(self):
        run=lambda *args,**kwargs:profile_fixtures.ProfileConfig.run_config(self,*args,**kwargs)
        for native in (False,True):
            result=json.loads(run('list','colors','--profile',self.platform,'icons','colors','formatting','--json',native=native).stdout)
            self.assertEqual(list(result['config']),['colors','icons','formatting'])
            self.assertNotIn('observed',result)
            self.assertNotIn('categories',json.loads(run('list','all','icons','--json',native=native).stdout))
            self.assertIn('unknown configuration category',run('list','unknown',native=native,code=2).stderr)
            run('get','DOTS_COLOR','unexpected','--json',native=native,code=2)
            run('list','--sources',native=native,code=2)
        for words in (['config','list',''],['config','list','colors','']):
            outputs=[]
            for shell in ('bash','zsh','fish','native'):
                command=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete',*words] if shell=='native' else
                         [str(self.root/'bin/dots'),'__complete',shell,str(len(words)),'--','dots',*words])
                p=subprocess.run(command,env=self.env,text=True,capture_output=True,timeout=30)
                self.assertEqual(p.returncode,0,p.stderr)
                candidates=[line.split('\t')[1] for line in p.stdout.splitlines()]
                for name in ('icons','colors','formatting','apps','files'):self.assertIn(name,candidates)
                outputs.append(candidates)
            self.assertTrue(all(rows==outputs[0] for rows in outputs))

    def test_filtered_human_views_keep_keys_and_widths_and_json_stays_declared(self):
        self.publication()
        config={'settings':{'HIDDEN':True},'apps':{'fzf':{'colors':{'fg+':None}}},'icons':{'menu':{'wiki':'W'}}}
        result=dict(profile=self.platform,path=str(self.path),config=config,categories=['apps','icons'])
        for width in (40,80,120):
            for color in (False,True):
                ui=Presentation(io.StringIO(),terminal=True);ui.width=width;ui.color=color
                listing(ui,result);text=re.sub(r'\x1b\[[0-9;]*m','',ui.stream.getvalue())
                self.assertNotIn('HIDDEN',text);self.assertNotIn('Native sources',text)
                self.assertLess(text.index('Apps'),text.index('Icons'))
                self.assertIn('fg:#123456,bold,strip',''.join(text.split()))
                self.assertTrue(all(cells(line)<=width for line in text.splitlines()),text)
        raw=json.loads(profile_fixtures.ProfileConfig.run_config(self,'list','apps','--json').stdout)
        self.assertIsNone(raw['config']['apps']['fzf']['colors']['fg+'])


if __name__=='__main__':unittest.main()
