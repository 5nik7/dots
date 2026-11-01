#!/usr/bin/env python3
"""Smart Config endpoints and human trees in owned profile roots."""
import copy
import io
import argparse
import re
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_config_alignment as fixtures
import test_profile_config as profile_fixtures
from config_completion import key_candidates,value_candidates,value_spec
from config_menu import Inventory,tree_rows,filter_choices,pick,input_value,Draft
from config_view import listing
from files.catalog import Presentation
from resources import cells
from interaction import SelectionEvent


class Browsing(unittest.TestCase):
    setUp=fixtures.Alignment.setUp

    def test_smart_endpoints_and_style_fields(self):
        inventory=Inventory(self.root,self.platform)
        all_rows={row.key:row for row in tree_rows(inventory)}
        self.assertIn('icons.git.branch',all_rows)
        endpoint='colors.apps.todo.field.alias.value'
        self.assertEqual(all_rows[endpoint].kind,'branch')
        self.assertNotIn(endpoint+'.fg',all_rows)
        self.assertNotIn('colors',all_rows)
        self.assertNotIn('icons',all_rows)
        fields=tree_rows(inventory,endpoint)
        self.assertIn(endpoint+'.fg',[row.key for row in fields])
        self.assertIn(endpoint+'.bold',[row.key for row in fields])
        self.assertTrue(all(row.kind!='branch' for row in fields))
        icons=tree_rows(inventory,'icons')
        self.assertTrue(all(row.group=='icons' and row.kind!='branch' for row in icons))
        choices=dict(filter_choices(inventory,'colors',{}))
        self.assertIn('category:icons',choices)
        self.assertIn('filter:colors.apps',choices)
        self.assertIn('sort:reverse',choices)
        self.assertIn('sort:local',choices)
        rows=tree_rows(inventory,'colors',True)
        self.assertIn(endpoint+'.fg',[row.key for row in rows])
        self.assertTrue(all(row.group=='colors' for row in rows))

    def test_filter_sort_and_focus_use_stable_keys(self):
        inventory=Inventory(self.root,self.platform)
        frame=dict(mode='get',filter_prefix='colors.apps.todo',sort='reverse',query='alias',selected='colors.apps.todo.field.alias.value')
        with patch('config_menu.RichSelector.fzf') as selector:
            selector.side_effect=lambda *args,**kwargs:[kwargs['focus_index']]
            row=pick(inventory,'colors',frame,None)
        self.assertEqual(row.key,frame['selected'])
        call=selector.call_args
        self.assertEqual(call.kwargs['navigation_keys']['alt-f'],'filter')
        self.assertFalse(call.kwargs['sort'])
        self.assertEqual(call.kwargs['query'],'alias')
        labels=[re.sub(r'\x1b\[[0-9;]*m','',label) for label in call.args[1]]
        self.assertTrue(all('colors.apps.todo.' in label for label in labels))
        keys=[label.strip().split()[0] for label in labels]
        self.assertEqual(keys,sorted(keys,reverse=True))

    def test_browser_filter_sort_style_back_preserves_frame(self):
        import config_menu as menu
        inventory=Inventory(self.root,self.platform)
        seen=[]
        def choose_row(inv,category,frame,context):
            step=len(seen);seen.append((category,dict(frame)))
            if step in (0,1,2):raise SelectionEvent('filter')
            if step==3:
                frame.update(query='alias',selected='colors.apps.todo.field.alias.value')
                return next(row for row in tree_rows(inv,'colors') if row.key==frame['selected'])
            raise SelectionEvent('back')
        args=argparse.Namespace(action='browse',key=None,query='',profile=None,defaults=False,client=None,no_refresh=True)
        with patch.object(menu,'Inventory',return_value=inventory),patch.object(menu,'terminal',return_value=True), \
             patch.object(menu.TmuxContext,'from_environment',return_value=None),patch.object(menu,'browser_available',return_value=True), \
             patch.object(menu,'pick',side_effect=choose_row), \
             patch.object(menu,'select',side_effect=['list','category:colors','filter:colors.apps','sort:reverse',None]):
            self.assertEqual(menu.browse(self.root,inventory.selected,args),0)
        self.assertEqual([category for category,_ in seen],['all','colors','colors','colors','colors','colors'])
        self.assertEqual(seen[2][1]['filter_prefix'],'colors.apps')
        self.assertEqual(seen[3][1]['sort'],'reverse')
        self.assertEqual(seen[4][1]['branch'],'colors.apps.todo.field.alias.value')
        self.assertEqual(seen[5][1]['query'],'alias')
        self.assertEqual(seen[5][1]['filter_prefix'],'colors.apps')
        self.assertEqual(seen[5][1]['sort'],'reverse')

    def test_full_key_and_allowed_value_candidates(self):
        keys=dict(key_candidates(self.root))
        self.assertIn('icons.git.branch',keys)
        self.assertIn('colors.apps.todo.field.alias.value.bold',keys)
        self.assertNotIn('colors.apps.todo.field.alias.value',keys)
        self.assertNotIn('colors.',keys)
        self.assertEqual([key for key,_ in key_candidates(self.root,'DOTS_INIT_COMPLETION')],['DOTS_INIT_COMPLETION'])
        self.assertIn(('colors.','Branch'),key_candidates(self.root,'..'))
        self.assertEqual(key_candidates(self.root,'colors..'),key_candidates(self.root,'colors.'))
        self.assertEqual(key_candidates(self.root,'@DOTS_INIT_COMPLETION'),[])
        cases={'DOTS_COLOR':['auto','always','never'],
               'settings.DOTS_INIT_THEME':['0','1'],
               'settings.files.backup':['true','false'],
               'colors.apps.todo.field.alias.value.bold':['true','false'],
               'apps.wttr.units':['us','metric'],
               'apps.wttr.widget_color_format':['ansi','plain','tmux'],
               'apps.wttr.icon_colors["113"].bold':['true','false']}
        for key,expected in cases.items():
            with self.subTest(key=key):
                self.assertEqual([value for value,_ in value_candidates(self.root,key)],expected)
                self.assertTrue(value_spec(self.root,key)['choices'])
        inventory=Inventory(self.root,self.platform)
        row=inventory.find('settings.DOTS_COLOR')
        with patch('config_menu.select',return_value='always') as select:
            result=input_value(row,'auto',None,root=self.root)
        self.assertIn(('always','always'),select.call_args.args[1])
        self.assertEqual(Draft(inventory,row).prepare(result).proposed,'always')

    def test_human_tree_widths_alias_files_icons_and_nested_children(self):
        result=dict(profile='termux',path=str(self.path),config={
            'profile':{'alias':'DROIDOTS'},'files':{'dots':[{},{}]},
            'settings':{'DOTS_THEME_DEFAULT':'catppuccin-mocha','files.backup':False},
            'icons':{'files':{'archive':'X'},'navigation':{'new':'N'}},
            'colors':{'apps':{'todo':{'field':{'alias':{'value':{'fg':'cyan','bold':False}}}}}},
            'apps':{'wttr':{'units':'metric','icons':{'location':'L','113':'S'},'icon_colors':{'location':'cyan','113':{'fg':'yellow','bold':True}}}},
            'environment':{'API_KEY':'[redacted]'}})
        original=copy.deepcopy(result)
        for columns in (40,80,120):
            for color in (False,True):
                stream=io.StringIO();ui=Presentation(stream,terminal=True);ui.width=columns;ui.color=color;ui.icons=False
                listing(ui,result)
                text=re.sub(r'\x1b\[[0-9;]*m','',stream.getvalue())
                self.assertTrue(all(cells(line)<=columns for line in text.splitlines()),text)
                self.assertIn('termux (DROIDOTS)',text)
                self.assertIn('dots(2)',text)
                self.assertIn('dots config get files.dots',' '.join(text.split()))
                self.assertIn('cyan',text);self.assertIn('fg:yellow,bold',text)
                lines=text.splitlines()
                parent=next(line for line in lines if line.strip()=='‒ alias')
                child=next(line for line in lines if line.strip().startswith('‒ value '))
                self.assertEqual(len(child)-len(child.lstrip()),len(parent)-len(parent.lstrip())+2)
        self.assertEqual(result,original)

    def test_list_data_and_native_frontend_contracts(self):
        run=lambda *args,**kw:profile_fixtures.ProfileConfig.run_config(self,*args,**kw)
        plain=run('list',DOTS_COLOR='never',DOTS_ICONS='never').stdout
        self.assertNotIn('‒ ',plain)
        raw=run('list','--json',DOTS_COLOR='never',DOTS_ICONS='never').stdout
        for native in (False,True):
            self.assertEqual(run('list','--json',native=native,DOTS_COLOR='always',DOTS_ICONS='always').stdout,raw)
            human=run('list',native=native,DOTS_COLOR='always',DOTS_ICONS='never').stdout
            self.assertIn('‒ ',human)
            self.assertEqual(run('get','DOTS_COLOR',native=native).stdout,'auto\n')

    def test_tree_respects_explicit_column_preferences(self):
        from row_layout import width
        for setting in (0,16,'40%'):
            fixtures.Alignment.configure(self,cli={'label_width':setting,'label_gap':3,'indent':4})
            stream=io.StringIO();ui=Presentation(stream,terminal=True);ui.color=False;ui.icons=False;ui.width=80
            listing(ui,dict(profile=self.platform,path=str(self.path),config={'settings':{'Key':'VALUE'}}))
            line=next(line for line in stream.getvalue().splitlines() if 'VALUE' in line)
            self.assertEqual(cells(line[:line.index('VALUE')]),4+max(cells('‒ Key'),width(setting,80,indent=4,gap=3))+3)

    def test_compact_styles_and_icon_samples_use_exact_colors_and_resets(self):
        import json
        from pathlib import Path
        from style_config import current
        theme=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme';theme.mkdir(parents=True)
        (theme/'palette.json').write_text(json.dumps({'colors':{'warning':'#aabb00','bright_foreground':'#ffffff','selection_background':'#112244'}}))
        (self.path.parent/'colors.toml').write_text('[icons.git.branch]\nfg="#123456"\nbold=true\n[icons.git.repository]\nfg="#654321"\nunderline=true\n')
        (self.path.parent/'icons.toml').write_text('[git]\nbranch="G"\nrepository="G"\n')
        current.cache_clear()
        result=dict(profile=self.platform,path=str(self.path),config={
            'icons':{'git':{'branch':'G','repository':'G'}},
            'colors':{'priority':{'high':{'fg':'warning','bold':True,'underline':True}},
                      'selection':{'fg':'bright_foreground','bg':'selection_background','bold':True},
                      'empty':{'fg':None,'bold':False}},
            'apps':{'wttr':{'icons':{'location':'W','113':'S','116':'C','humidity':'H','sunrise':'R'},'icon_colors':{'location':'cyan','humidity':0,'113':{'fg':208,'bold':True},'unknown':'blue'}}}})
        for columns in (40,80,120):
            stream=io.StringIO();ui=Presentation(stream,terminal=True);ui.color=True;ui.icons=True;ui.width=columns
            previous={'G':'31'};ui._icon_paints=previous
            listing(ui,result);text=stream.getvalue();plain=re.sub(r'\x1b\[[0-9;]*m','',text)
            self.assertIs(ui._icon_paints,previous)
            self.assertTrue(all(cells(line)<=columns for line in plain.splitlines()),plain)
            self.assertIn('\x1b[0;1;38;2;18;52;86mG\x1b[0m',text)
            self.assertIn('\x1b[0;4;38;2;101;67;33mG\x1b[0m',text)
            self.assertIn('\x1b[0;1;4;38;2;170;187;0m',text)
            self.assertIn('\x1b[0;1;38;2;255;255;255;48;2;17;34;68m',text)
            self.assertIn('\x1b[0;1;38;5;208mS\x1b[0m',text)
            self.assertIn('\x1b[0;38;5;0mH\x1b[0m',text)
            joined=''.join(plain.split())
            self.assertIn('highfg:warning,bold,underline',joined)
            self.assertIn('fg:null,bold:false',joined)
            self.assertIn('colors.icons.git.branch.fg',joined)
            self.assertIn('apps.wttr.icon_colors.unknown',joined)
            self.assertIn('H0',joined)
            self.assertIn('colors.daylight.sunrise.fg',joined)
            self.assertNotIn('‒ fg',plain)

    def test_icon_samples_follow_selected_profile_and_palette_fallback(self):
        from config_view import icon_sample,compact_styles
        from style_config import Styles
        from profile_config import context
        other='windows' if self.platform!='windows' else 'linux'
        path=self.root/'profiles'/other/'colors.toml'
        path.write_text('[icons.git.branch]\nfg="#abcdef"\n[ui.heading]\nfg="palette.unavailable"\n')
        styles=Styles(self.root,context(self.root,other))
        sample=icon_sample(styles,'git.branch','G')
        self.assertIn('38;2;171;205;239',sample.code)
        self.assertIn('colors.icons.git.branch.fg',sample.annotation)
        record=compact_styles({'ui':{'heading':{'fg':'palette.unavailable'}}},styles)['ui']['heading']
        self.assertEqual(record.text,'fg:palette.unavailable')
        self.assertEqual(record.code,'0;'+styles.sgr('ui.heading'))

    def test_tmux_icon_samples_name_the_actual_component_controls(self):
        from config_view import icon_sample
        from style_config import Styles
        (self.path.parent/'colors.toml').write_text('[apps.tmux.clock.icon]\nfg="#123456"\n[apps.tmux.battery.low.icon]\nfg="#654321"\n[apps.tmux.session.icon]\nfg="#abcdef"\n')
        styles=Styles(self.root)
        clock=icon_sample(styles,'apps.tmux.clock.day','C')
        self.assertIn('38;2;18;52;86',clock.code)
        self.assertEqual(clock.annotation,'colors.apps.tmux.clock.icon.fg')
        battery=icon_sample(styles,'apps.tmux.battery.low','B')
        self.assertIn('38;2;101;67;33',battery.code)
        self.assertEqual(battery.annotation,'colors.apps.tmux.battery.low.icon.fg')
        session=icon_sample(styles,'apps.tmux.session.default','S')
        self.assertIn('38;2;171;205;239',session.code)
        self.assertEqual(session.annotation,'colors.apps.tmux.session.icon.fg (active)')
        window=icon_sample(styles,'apps.tmux.window.default','W')
        self.assertIn('colors.apps.tmux.windows.active.fg',window.annotation)

    def test_menu_icon_samples_match_menu_accent_and_unstyled_icons_have_no_annotation(self):
        from config_view import icon_sample,tree
        from style_config import Styles
        from menus import Menu,Entry,entry_spans
        styles=Styles(self.root,palette={'colors':{'accent':'#123456','foreground':'#ffffff'}})
        ui=Presentation(io.StringIO(),terminal=True);ui.icons=True
        menu=Menu('example','Example',(Entry('wiki','Wiki',icon='W',icon_role='menu.wiki'),))
        sample=icon_sample(styles,'menu.wiki','W')
        rendered=entry_spans(menu,menu.entries[0],ui,preferences=styles,formatting={})[0]
        self.assertEqual(sample.code,'0;'+rendered[1])
        self.assertIn('38;2;18;52;86',sample.code)
        self.assertEqual(sample.annotation,'colors.apps.menu.icon.fg')
        (self.path.parent/'colors.toml').write_text('[icons.menu.wiki]\nfg="#abcdef"\nunderline=true\n')
        override=Styles(self.root,palette={'colors':{'accent':'#123456'}})
        selected=icon_sample(override,'menu.wiki','W')
        rendered=entry_spans(menu,menu.entries[0],ui,preferences=override,formatting={})[0]
        self.assertEqual(selected.code,'0;'+rendered[1])
        self.assertEqual(selected.annotation,'colors.icons.menu.wiki.fg')
        plain_icon=icon_sample(styles,'files.archive','A')
        self.assertEqual(plain_icon.annotation,'')
        for color in (False,True):
            for columns in (40,80,120):
                ui.stream=io.StringIO();ui.color=color;ui.width=columns;ui._config_tree_auto_columns=True;ui._icon_paints={}
                tree(ui,{'menu':{'wiki':sample},'files':{'archive':plain_icon}})
                text=re.sub(r'\x1b\[[0-9;]*m','',ui.stream.getvalue())
                self.assertIn('colors.apps.menu.icon.fg',''.join(text.split()))
                self.assertNotIn('colors.ui.foreground',text)
                self.assertNotIn('terminal foreground',text)
                self.assertEqual(next(line for line in text.splitlines() if 'archive' in line).rstrip(),next(line for line in text.splitlines() if 'archive' in line))
                self.assertTrue(all(cells(line)<=columns for line in text.splitlines()),text)

    def test_other_menu_and_status_icons_match_consumers(self):
        from config_view import icon_sample
        from config_icon_samples import menu_entry
        from style_config import Styles
        from menus import Menu,Entry,entry_spans
        styles=Styles(self.root,palette={'colors':{'accent':'#123456'}})
        ui=Presentation(io.StringIO(),terminal=True);ui.icons=True
        formatting={'entries':{'keys:categories:nvim':{'icon':{'fg':'#abcdef','bg':'#654321','underline':True}},
                               'session-actions:new':{'icon':{'fg':'#112233'}}}}
        for role in ('applications.nvim','weather.daily','navigation.back','navigation.new','files.configuration','status.todo'):
            identity,has_role=menu_entry(role);menu_id,entry_id=identity.rsplit(':',1)
            entry=Entry(entry_id,entry_id,icon='X',icon_role=role if has_role else '')
            expected=entry_spans(Menu(menu_id,menu_id,(entry,)),entry,ui,preferences=styles,formatting=formatting)[0][1]
            sample=icon_sample(styles,role,'X',menu_formatting=formatting)
            self.assertEqual(sample.code,'0;'+expected,role)
            self.assertIn('formatting.apps.menu.entries' if identity in formatting['entries'] else 'colors.apps.menu.icon.fg',sample.annotation)
        for role,code in (('error','91'),('success','92'),('warning','93'),('info','94')):
            sample=icon_sample(styles,'status.'+role,'X')
            self.assertEqual(sample.code,'0;'+styles.code(code))
        # Stash styling is a foreground token: tmux attributes are not consumed.
        (self.path.parent/'colors.toml').write_text('[apps.tmux.ui.muted]\nfg="#112233"\nbold=true\n')
        sample=icon_sample(Styles(self.root),'git.stashed','S')
        self.assertEqual(sample.code,'0;38;2;17;34;51')
        self.assertEqual(sample.annotation,'colors.apps.tmux.ui.muted.fg (Gitmux)')

    def test_published_icon_samples_follow_resource_rules_and_real_owners(self):
        import json
        from config_view import icon_sample,tree
        from config_icon_samples import PublishedSamples
        from style_config import Styles
        from resources import Resources
        state=self.home/'state/dots/current/theme';state.mkdir(parents=True)
        (state/'file-styles.tsv').write_text('dots-file-styles\t1\ntype\texecutable\t0;1;38;2;1;2;3\t-\n'
            'extension\t.py\t0;38;2;4;5;6\tfold\nsuffix\t.rs\t0;38;2;9;8;7\tfold\n'
            'default_mime\timage/*\t0;38;2;7;8;9\t-\n')
        (state/'git-styles.tsv').write_text('dots-git-styles\t1\nrepo\t0;1;38;2;11;12;13\nbranch\t0;38;2;14;15;16\n')
        (state/'colors.json').write_text(json.dumps({'schema':1,'rules':{
            'type':{'executable':{'fg':'green'},'media':{'fg':'magenta'}},
            'extension':{'.py':{'fg':'yellow'}},'mime':{'image/*':{'use':'media'}},
            'git':{'repo':{'fg':'blue'},'branch':{'fg':'magenta'},'modified':{'fg':'warning','bg':'red'}}},
            'styles':{'git':{'modified':{'fg':'#010203','bg':'#ff0000'}}}}))
        styles=Styles(self.root);published=PublishedSamples(styles)
        for role,path,kind,mime,source in (
            ('files.executable','executable','executable',None,'type.executable.fg'),
            ('files.python','.py','file','text/x-python','extension[".py"].fg'),
            ('files.image','.svg','file','image/svg+xml','type.media.fg'),
            ('files.rust','.rs','file','text/x-rust','Vivid suffix ".rs"')):
            sample=icon_sample(styles,role,'X',published=published)
            self.assertEqual(sample.code,'0;'+Resources(state).describe(path,kind,mime)[2])
            self.assertIn(source,sample.annotation)
            self.assertNotIn('colors.icons.',sample.annotation)
            for width in (40,80,120):
                ui=Presentation(io.StringIO(),terminal=True);ui.width=width;ui._config_tree_auto_columns=True
                tree(ui,{'sample':sample})
                self.assertTrue(all(cells(line)<=width for line in re.sub(r'\x1b\[[0-9;]*m','',ui.stream.getvalue()).splitlines()))
        for role,expected in (('hosts.github','repo'),('git.branch','branch')):
            self.assertEqual(icon_sample(styles,role,'X',published=published).code,'0;'+Resources(state).git_style(expected))
        modified=icon_sample(styles,'git.modified','M',published=published)
        self.assertEqual(modified.code,'0;1;38;2;1;2;3')
        self.assertNotIn('.bg',modified.annotation)
        (self.path.parent/'colors.toml').write_text('[icons.files.python]\nbg="#123456"\n')
        background=icon_sample(Styles(self.root),'files.python','P',published=published)
        self.assertIn('38;2;4;5;6',background.code)
        self.assertIn('48;2;18;52;86',background.code)
        self.assertIn('extension[".py"].fg',background.annotation)
        self.assertIn('colors.icons.files.python.bg',background.annotation)
        (self.path.parent/'colors.toml').write_text('[icons.files.python]\nfg="#abcdef"\n')
        override=icon_sample(Styles(self.root),'files.python','P',published=published)
        self.assertIn('38;2;171;205;239',override.code)
        self.assertEqual(override.annotation,'colors.icons.files.python.fg')
        empty=PublishedSamples(styles,self.home/'missing publication')
        self.assertEqual(icon_sample(styles,'files.python','P',published=empty).annotation,'')
        self.assertEqual(icon_sample(styles,'navigation.ellipsis','E',published=published).annotation,'')
        (state/'colors.json').write_text('{"schema":1,"rules":[]}')
        self.assertIsNone(PublishedSamples(styles).sample('files.python'))

    def test_published_samples_are_scoped_and_weather_fallbacks_identify_controls(self):
        from config_view import icon_sample
        from style_config import Styles
        styles=Styles(self.root)
        sample=icon_sample(styles,'weather.humidity','H',weather={'icon_colors':{'humidity':{'fg':'#123456','bold':True}}})
        self.assertEqual(sample.code,'0;1;38;2;18;52;86')
        self.assertEqual(sample.annotation,'apps.wttr.icon_colors.humidity (wttr fallback glyph)')
        for profile,expected in ((self.platform,True),('defaults',False),('windows' if self.platform!='windows' else 'linux',False)):
            ui=Presentation(io.StringIO(),terminal=True)
            with patch('config_icon_samples.PublishedSamples',return_value=None) as samples:
                listing(ui,dict(profile=profile,path=str(self.path),config={'icons':{'files':{'python':'P'}}}))
            self.assertEqual(samples.called,expected)

    def test_all_key_and_value_provider_frontend_parity(self):
        for words in (['config','set','icons.navigation.new'],
                      ['config','set','..'],
                      ['config','set','colors..'],
                      ['config','set','colors.apps.todo.field.alias.value.bold',''],
                      ['config','set','DOTS_COLOR',''],
                      ['config','set','apps.wttr.units','']):
            commands=[[str(self.root/'bin/dots'),'__complete','zsh',str(len(words)),'--','dots',*words],
                      [sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete',*words]]
            results=[subprocess.run(command,env=self.env,capture_output=True,text=True,timeout=20) for command in commands]
            self.assertTrue(all(result.returncode==0 and not result.stderr for result in results),results)
            self.assertEqual(results[0].stdout,results[1].stdout)
            self.assertNotIn('\x1b',results[0].stdout)


if __name__=='__main__':unittest.main()
