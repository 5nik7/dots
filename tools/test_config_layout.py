#!/usr/bin/env python3
"""Native placement fragments on a private tmux server with owned adapters."""
import json
import re
import shutil
import unittest
from pathlib import Path
import sys
import test_tmux_status as fixtures
sys.path.insert(0,str(fixtures.REPO/'lib/dots'))
from tmux_config import layout,validate_layout
from unittest.mock import patch

@unittest.skipUnless(fixtures.TMUX,'tmux unavailable')
class Layout(unittest.TestCase):
    def setUp(self):
        fixtures.TmuxStatus.setUp(self)
        shutil.copy2(fixtures.REPO/'config/tmux/tmux.conf',self.repo/'config/tmux/tmux.conf')
        self.defaults=json.loads((fixtures.REPO/'default/config.json').read_text())
        self.selected=dict(facts=dict(platform='termux'),layers=[],current='termux')
    android_snapshot=fixtures.TmuxStatus.android_snapshot
    weather_stub=fixtures.TmuxStatus.weather_stub
    snapshot=fixtures.TmuxStatus.snapshot
    stub=fixtures.TmuxStatus.stub
    server=fixtures.TmuxStatus.server
    write_config=fixtures.TmuxStatus.write_config

    def publish(self,tmux):
        (self.repo/'default/config.json').write_text(json.dumps(self.defaults))
        text=layout(self.repo,self.selected)
        path=self.root/'layout.conf';path.write_text(text)
        tmux('source-file',str(path))
        return text

    def test_defaults_reorder_reset_and_invalid_components(self):
        tmux,_=self.server('placement')
        tmux('source-file',str(self.write_config(workspace_hooks=False)))
        before=[tmux('show-option','-gqv','status-format['+str(i)+']') for i in (0,1)]
        self.publish(tmux)
        after=[tmux('show-option','-gqv','status-format['+str(i)+']') for i in (0,1)]
        self.assertEqual(after[1],before[1])
        self.assertIn('@dots-config-clock',after[0])
        config=self.defaults['formatting']['apps']['tmux'];config.update(position='bottom',main_row=0,termux_row=1,main_left=['windows','session'],main_right=['git','indicators'])
        self.publish(tmux)
        self.assertEqual(tmux('show-option','-gqv','status-position'),'bottom')
        row=tmux('show-option','-gqv','status-format[0]')
        self.assertLess(row.index('@dots-layout-main-left-windows'),row.index('@dots-layout-main-left-session'))
        self.assertIn('align=right',row)
        self.assertIn('@dots-gitmux-content',tmux('show-option','-gqv','@dots-layout-main-right-git'))
        self.assertNotIn('align=right',tmux('show-option','-gqv','@dots-gitmux-content'))
        for width in (40,48,80,120):
            tmux('set-option','-g','default-size',str(width)+'x24')
            self.assertNotIn('invalid',tmux('display-message','-p','#{E:status-format[0]}').lower())
        with self.assertRaises(ValueError):validate_layout(dict(rows=1,main_row=1),'termux')
        with self.assertRaises(ValueError):validate_layout(dict(rows=2,main_row=0,termux_row=0),'termux')

    def test_multi_project_visibility_survives_custom_layout_and_refresh(self):
        tmux,_=self.server('multi-placement')
        tmux('source-file',str(self.write_config(workspace_hooks=False)))
        tmux('set-option','-g','@dots-workspace-data','{"schema":1}')
        tmux('set-option','-g','@dots-workspace-auto','1')
        tmux('set-option','-g','@dots-workspace-label','multi')
        tmux('set-option','-g','@dots-workspace-project-count','2')
        tmux('set-option','-g','@dots-session-number','9')
        tmux('set-option','-g','@dots-git-snapshot','HOST|')
        tmux('rename-window','multi')
        tmux('set-option','-g','@dots-codex-snapshot','|@0:idle|')
        for multiple in (False,True):
            self.defaults['apps']['tmux']['session']['multiple']=multiple
            for left in (['session','windows'],['windows','session']):
                self.defaults['formatting']['apps']['tmux']['main_left']=left
                # A visual refresh must replace an older server's predicates.
                tmux('set-option','-g','@dots-session-multi','0')
                tmux('set-option','-g','@dots-window-name','')
                tmux('set-option','-g','@dots-windows-visible','0')
                self.publish(tmux)
                self.assertEqual(tmux('display-message','-p','#{E:status-left}'),'')
                self.assertEqual(tmux('display-message','-p','#{E:@dots-session-visible}'),'0')
                self.assertEqual(tmux('display-message','-p','#{E:@dots-windows-visible}'),'1')
                window=tmux('display-message','-p','#{E:@dots-window-format}')
                self.assertEqual(re.sub(r'#\[[^]]*\]','',window),' multi  ')
                self.assertNotIn('HOST',window)
        self.defaults['apps']['tmux']['session']['multiple']=False
        self.publish(tmux)
        # The literal project name multi is not evidence of multiple roots.
        tmux('set-option','-g','@dots-workspace-project-count','1')
        text=tmux('display-message','-p','#{E:status-left}')
        self.assertIn('HOST',text);self.assertIn('multi',text)
        self.assertEqual(tmux('display-message','-p','#{E:@dots-windows-visible}'),'0')
        for count in ('0','', '2'):
            tmux('set-option','-g','@dots-workspace-project-count',count)
            tmux('set-option','-g','@dots-workspace-auto','0')
            text=tmux('display-message','-p','#{E:status-left}')
            self.assertNotIn('HOST',text)
            self.assertIn('fixture',text)

    def test_saved_legacy_layout_keeps_git_right_without_quota_acquisition(self):
        tmux,_=self.server('legacy-placement')
        tmux('source-file',str(self.write_config(workspace_hooks=False)))
        cfg=self.defaults['formatting']['apps']['tmux']
        cfg.update(main_left=['session','windows','git'],main_right=['indicators'])
        self.publish(tmux)
        row=tmux('show-option','-gqv','status-format[1]')
        self.assertIn('@dots-gitmux-segment',row)
        self.assertIn('align=right',tmux('show-option','-gqv','@dots-gitmux-segment'))
        self.assertEqual(tmux('show-option','-gqv','@dots-codex-usage'),'')
        cfg.update(rows=1,main_left=['session'],main_right=['git'],termux_right=['codex_usage'])
        self.publish(tmux)
        self.assertEqual(tmux('show-option','-gqv','@dots-codex-usage'),'')

    def test_custom_quota_and_git_hide_without_orphan_dividers(self):
        tmux,_=self.server('optional-placement')
        tmux('source-file',str(self.write_config(workspace_hooks=False)))
        self.defaults['formatting']['apps']['tmux']['main_left']=['session']
        self.publish(tmux)
        tmux('set-option','-g','status-left','')
        tmux('set-option','-g','status-right','')
        for quota,git,expected in (('Q 72%','BRANCH','Q 72% · BRANCH'),
                                   ('','BRANCH','BRANCH'),('Q 72%','','Q 72%'),('','','')):
            tmux('set-option','-g','@dots-codex-usage',quota)
            tmux('set-option','-g','@dots-gitmux',git)
            text=tmux('display-message','-p','#{E:status-format[1]}')
            text=re.sub(r'#\[[^]]*\]','',text)
            self.assertEqual(text.strip(),expected)
        fmt=self.defaults['formatting']['apps']['tmux']
        fmt['codex_usage']['git_separator']=''
        self.publish(tmux)
        self.assertEqual(tmux('show-option','-gqv','@dots-codex-git-separator'),'')
        fmt['codex_usage']['git_separator']=' ·'
        fmt['main_right']=['git','codex_usage']
        self.publish(tmux)
        self.assertEqual(tmux('show-option','-gqv','@dots-codex-git-separator'),'')

class GeneratedStatus(fixtures.TmuxStatus):
    def setUp(self):
        super().setUp()
        # Shared native assertions use an explicit baseline, independent of
        # the owner's editable box padding, icon and indicator preferences.
        path=self.repo/'default/config.json';data=json.loads(path.read_text())
        data['formatting']['apps']['tmux']['battery'].update(before='',after='',width=4)
        for key,label in (('copy','COPY'),('prefix','PREFIX'),('zoom','ZOOM')):
            data['apps']['tmux']['indicators'][key]['text']=label
        path.write_text(json.dumps(data))
        profile=self.repo/'profiles/termux'
        with (profile/'colors.toml').open('a') as stream:
            for part in ('icon','text','spacer','surround'):
                stream.write('\n[apps.tmux.battery.'+part+']\nbg="default"\n')
        (profile/'icons.toml').write_text('[applications]\ncodex=""\n')

    def write_theme(self,*args,**kwargs):
        from theme_styles import tokens,snapshot
        palette={}
        def capture(colors,root):
            palette.update(colors)
            return tokens(colors,root)
        with patch('theme_styles.tokens',side_effect=capture):path=super().write_theme(*args,**kwargs)
        shutil.copy2(fixtures.REPO/'config/tmux/tmux.conf',self.repo/'config/tmux/tmux.conf')
        generation=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme';generation.mkdir(parents=True,exist_ok=True)
        from profile_config import context
        from style_config import Styles
        # The fixture has no active theme pointer, so use its published defaults.
        with patch.dict(fixtures.os.environ,self.env,clear=True):
            selected=context(self.repo,'termux')
            selected['facts']['platform']='termux'
            styles=Styles(self.repo,selected,palette=palette)
            (generation/'tmux-controls.conf').write_text(layout(self.repo,selected,styles))
            (generation/'preferences.json').write_text(json.dumps(snapshot(palette,styles=styles)))
        return path

    def test_open_marker_colors_widths_empty_override_and_attention(self):
        import shlex
        inner,base=self.server('open-inner')
        self.write_theme()
        inner('source-file',str(self.write_config(workspace_hooks=False)))
        inner('set-option','-g','@dots-termux-default','1')
        inner('set-option','-gw','automatic-rename','off')
        inner('rename-window','shell')
        pane=inner('new-window','-d','-P','-F','#{pane_id}','-n','agent','sleep 120')
        window=inner('display-message','-p','-t',pane,'#{window_id}')
        inner('set-option','-g','@dots-codex-snapshot','|'+window+':idle|')
        inner('set-option','-g','@dots-codex-usage','')
        outer,_=self.server('open-view',termux=False)
        outer('set-option','-g','status','off')
        outer('set-option','-g','default-terminal','tmux-256color')
        attach=shlex.join(['env','-u','TMUX','-u','TMUX_PANE',*base,'attach-session','-t','fixture'])
        outer('new-session','-d','-s','view','-x','80','-y','24',attach)
        for background,dark_background in (('#112233','#223344'),('#ffffff','#ddeeff')):
            self.write_theme(background=background,dark_background=dark_background)
            generation=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'
            inner('source-file',str(self.tmux_config/'dots-theme.conf'))
            inner('source-file',str(generation/'tmux-controls.conf'))
            inner('set-option','-g','@dots-codex-usage','')
            for width in (40,80,120):
                outer('resize-window','-t','view','-x',str(width),'-y','24')
                for selected in (':0',pane):
                    inner('select-window','-t',selected)
                    rows=self.await_screen(outer,'view',lambda rows:'agent ' in rows[1])
                    row=rows[1]
                    self.assertEqual(self.plain(row).count(''),1)
                    self.assertEqual(self.colors_at(row,'')['fg'],(136,136,136))
                    self.assertEqual(self.colors_at(row,'')['bg'],self.colors_at(row,'agent')['bg'])
                    self.assertFalse(self.bold_at(row,''));self.assertFalse(self.dim_at(row,''))
                inner('set-option','-w','-t',pane,'@dots-window-alert','1')
                rows=self.await_screen(outer,'view',lambda rows:'[1 agent ]' in rows[1])
                self.assertEqual(self.colors_at(rows[1],'')['fg'],(255,85,85))
                self.assertTrue(self.bold_at(rows[1],''))
                inner('set-option','-uw','-t',pane,'@dots-window-alert')
        with (self.repo/'profiles/termux/icons.toml').open('a') as stream:
            stream.write('\n[apps.tmux.status]\nopen=""\n')
        self.write_theme()
        inner('source-file',str(generation/'tmux-controls.conf'))
        inner('set-option','-g','@dots-codex-usage','')
        rows=self.await_screen(outer,'view',lambda rows:rows[1].rstrip()==' 0 shell │ 1 agent')
        self.assertNotIn('',rows[1])
        self.assertEqual(inner('display-message','-p','-t',pane,'#{E:@dots-window-marker}'),'')

    def test_question_finished_one_marker_two_clients_and_themes(self):
        import shlex
        inner,base=self.server('types-inner')
        self.write_theme()
        inner('source-file',str(self.write_config(workspace_hooks=False)))
        inner('set-option','-g','@dots-termux-default','1')
        inner('set-option','-gw','automatic-rename','off')
        inner('rename-window','shell')
        pane=inner('new-window','-d','-P','-F','#{pane_id}','-n','agent','sleep 120')
        window=inner('display-message','-p','-t',pane,'#{window_id}')
        outer,_=self.server('types-view',termux=False)
        outer('set-option','-g','status','off')
        outer('set-option','-g','default-terminal','tmux-256color')
        attach=shlex.join(['env','-u','TMUX','-u','TMUX_PANE',*base,'attach-session','-t','fixture'])
        for name in ('view','view2'):outer('new-session','-d','-s',name,'-x','80','-y','24',attach)
        for background,dark in (('#112233','#223344'),('#ffffff','#ddeeff')):
            self.write_theme(background=background,dark_background=dark)
            generation=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'
            inner('source-file',str(self.tmux_config/'dots-theme.conf'))
            inner('source-file',str(generation/'tmux-controls.conf'))
            inner('set-option','-g','@dots-codex-usage','')
            for width in (40,80,120):
                for name in ('view','view2'):outer('resize-window','-t',name,'-x',str(width),'-y','24')
                for tokens,glyph,color,alert in (
                    (('idle',),'',(136,136,136),False),
                    (('working',),'',(171,205,239),False),
                    (('waiting',),'',(171,205,239),False),
                    (('working','waiting','question'),'',(255,85,85),False),
                    (('working','question','attention'),'',(255,85,85),True),
                    (('idle','attention','finished'),'',(85,255,85),True)):
                    inner('set-option','-g','@dots-codex-snapshot','|'+''.join(window+':'+t+'|' for t in tokens))
                    expected=('[1 agent '+glyph+']') if alert else '1 agent '+glyph
                    for name in ('view','view2'):
                        rows=self.await_screen(outer,name,lambda rows: expected in self.plain(rows[1]) and self.colors_at(rows[1],glyph)['fg']==color,styled=True)
                        row=rows[1];plain=self.plain(row)
                        self.assertEqual(sum(plain.count(g) for g in ('','','')),1)
                        if alert:
                            for part in ('[','agent',glyph,']'):
                                self.assertEqual(self.colors_at(row,part)['fg'],color)
                                self.assertTrue(self.bold_at(row,part))
                        if glyph=='':self.assertTrue(self.bold_at(row,glyph))

    def test_component_span_attributes_do_not_leak(self):
        import shlex
        profile=self.repo/'profiles/termux'
        data=json.loads((profile/'profile.json').read_text())
        data['apps']={'tmux':{'clock':{'icon_mode':'fixed'}}}
        data['formatting']={'apps':{'tmux':{'battery':{'before':' ','after':' '}}}}
        (profile/'profile.json').write_text(json.dumps(data))
        (profile/'icons.toml').write_text('[apps.tmux.clock]\nfixed="I"\n[apps.tmux.battery]\nnormal="B"\n')
        (profile/'colors.toml').write_text('[apps.tmux.clock.icon]\nbold=false\n'+
            '\n'.join('[apps.tmux.battery.'+part+']\nbg="dark_background"\n'+
                      ('bold=true\n' if part=='icon' else '')
                      for part in ('icon','text','spacer','surround')))
        self.write_theme()
        inner,base=self.server('span-inner')
        inner('source-file',str(self.write_config(workspace_hooks=False)))
        outer,_=self.server('span-view',termux=False)
        outer('set-option','-g','status','off')
        outer('set-option','-g','default-terminal','tmux-256color')
        attach=shlex.join(['env','-u','TMUX','-u','TMUX_PANE',*base,'attach-session','-t','fixture'])
        outer('new-session','-d','-s','view','-x','80','-y','24',attach)
        for width in (40,48,80,120):
            outer('resize-window','-t','view','-x',str(width),'-y','24')
            lines=self.await_screen(outer,'view',lambda rows:rows and 'I ' in rows[0] and 'B 80%' in rows[0])
            self.assertFalse(self.bold_at(lines[0],'I'))
            self.assertTrue(self.bold_at(lines[0],'I ',2))
            self.assertTrue(self.bold_at(lines[0],'B'))
            self.assertFalse(self.bold_at(lines[0],'80%'))
            # Every battery cell, including both outer spaces and the inner
            # spacer, has the clock's background with no uncolored holes.
            label=' B 80%   '
            self.assertIn(label,self.plain(lines[0]))
            clock_bg=self.colors_at(lines[0],'I')['bg']
            self.assertEqual(clock_bg,(34,51,68))
            for offset in range(len(label)):
                self.assertEqual(self.colors_at(lines[0],label,offset)['bg'],clock_bg)
            self.assertNotEqual(self.colors_at(lines[0],label,-1)['bg'],clock_bg)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite([loader.loadTestsFromTestCase(Layout),
        GeneratedStatus('test_native_two_clients_widths_colors_and_failure_clearing'),
        GeneratedStatus('test_native_compact_badges_names_and_padding'),
        GeneratedStatus('test_native_singletons_and_alerts'),
        GeneratedStatus('test_native_termux_attention_cells_widths_and_clearing'),
        GeneratedStatus('test_component_span_attributes_do_not_leak'),
        GeneratedStatus('test_open_marker_colors_widths_empty_override_and_attention'),
        GeneratedStatus('test_question_finished_one_marker_two_clients_and_themes')])


if __name__=='__main__':unittest.main()
