#!/usr/bin/env python3
"""Native placement fragments on a private tmux server with owned adapters."""
import json
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
        self.assertLess(row.index('#{W:'),row.index('E:status-left'))
        self.assertIn('align=right',row)
        self.assertIn('@dots-gitmux-content',row)
        self.assertNotIn('align=right',tmux('show-option','-gqv','@dots-gitmux-content'))
        for width in (40,48,80,120):
            tmux('set-option','-g','default-size',str(width)+'x24')
            self.assertNotIn('invalid',tmux('display-message','-p','#{E:status-format[0]}').lower())
        with self.assertRaises(ValueError):validate_layout(dict(rows=1,main_row=1),'termux')
        with self.assertRaises(ValueError):validate_layout(dict(rows=2,main_row=0,termux_row=0),'termux')

class GeneratedStatus(fixtures.TmuxStatus):
    def setUp(self):
        super().setUp()
        # Shared native assertions use an explicit baseline, independent of
        # the owner's editable box padding, icon and indicator preferences.
        path=self.repo/'default/config.json';data=json.loads(path.read_text())
        data['formatting']['apps']['tmux']['battery'].update(before='',after='')
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
        GeneratedStatus('test_component_span_attributes_do_not_leak')])


if __name__=='__main__':unittest.main()
