#!/usr/bin/env python3
"""Keys/Weather menu consumers and Config controls in disposable roots."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import time
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from config_values import current as controls
from style_config import current as styles
from files.catalog import Presentation
from interaction import RichSelector
from keys.presentation import menu_rows, menu_layout, binding_label, styles as binding_styles
from keys.browser import choose_mode
from keys.model import record
from menus import Menu, styled_labels
from resources import cells
from wttr import browser as weather
from test_menus import NativeMenuFixture

ANSI = re.compile(r'\x1b\[[0-9;]*m')


class MenuStyles(unittest.TestCase):
    run_config = fixtures.ProfileConfig.run_config

    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default', self.root/'default')
        self.env.update(TERM='xterm-256color', DOTS_COLOR='always', DOTS_ICONS='always')
        scope = patch.dict(os.environ, self.env, clear=True)
        scope.start(); self.addCleanup(scope.stop)
        self.addCleanup(styles.cache_clear); self.addCleanup(controls.cache_clear)
        self.reset()

    def reset(self):
        styles.cache_clear(); controls.cache_clear()

    def configure(self, style_text='', icon_text='', **manifest):
        (self.path.parent/'colors.toml').write_text(style_text)
        (self.path.parent/'icons.toml').write_text(icon_text)
        doc=json.loads(self.path.read_text());doc.update(manifest)
        self.path.write_text(json.dumps(doc));self.reset()

    def ui(self):
        return Presentation(io.StringIO(), terminal=True)

    def test_shared_spans_glyph_and_entry_overrides_reach_actual_consumers(self):
        self.configure(style_text='''[apps.menu.icon]
fg="#123456"
bg="#112233"
bold=true
[apps.menu.label]
fg="#234567"
[apps.menu.description]
fg="#345678"
[icons.applications.tmux]
fg="#456789"
[icons.weather.daily]
fg="#56789a"
''', icon_text='[applications]\ntmux="界"\n[weather]\ndaily="D"\n',
            colors={'apps':{'menu':{'entries':{
                'keys:categories:tmux':{'icon':{'fg':'#6789ab','bold':False}},
                'wttr:main:daily':{'icon':{'fg':'#789abc','bg':'#223344','bold':False}},
                'wttr:Units:metric':{'label':{'fg':'#89abcd'}}}}}})
        ui=self.ui();original=dict(ui.formatting)
        rows=menu_rows(ui,[dict(app='tmux',count=7)])
        self.assertEqual([row[0] for row in rows],['all','tmux'])
        self.assertEqual(ANSI.sub('',rows[1][1]),' 界 tmux · [7]')
        self.assertIn('\x1b[38;2;103;137;171;48;2;17;34;51m界 ',rows[1][1])
        self.assertIn('38;2;35;69;103mtmux',rows[1][1])
        self.assertIn('38;2;52;86;120m · [7]',rows[1][1])
        self.assertEqual(ui.formatting,original)
        labels=styled_labels(Menu('wttr:main','Weather',weather.ENTRIES),ui,compact=True)
        self.assertIn('\x1b[38;2;120;154;188;48;2;34;51;68mD ',labels[1])
        self.assertNotIn('38;2;86;120;154',labels[1])
        with patch('menus.terminal',return_value=True),patch('menus.shutil.which',return_value='fzf'), \
             patch('interaction.rich_fzf_available',return_value=True), \
             patch.object(RichSelector,'fzf',return_value=[1]) as picker:
            self.assertEqual(weather.select('Units',weather.UNIT_ENTRIES,None),'metric')
        self.assertIn('38;2;137;171;205mMetric:',picker.call_args.args[1][1])
        self.assertIn('fg+:-1:regular',picker.call_args.args[6])

    def test_mode_all_identity_empty_icons_and_plain_rendering(self):
        self.configure(icon_text='[weather]\ndaily=""\n',colors={'apps':{'menu':{'entries':{
            'keys:modes:all':{'label':{'fg':'#112233'}},
            'keys:modes:mode:all':{'label':{'fg':'#445566'}}}}}})
        ui=self.ui()
        with patch.object(RichSelector,'fzf',return_value=[1]) as picker:
            self.assertEqual(choose_mode(ui,[record('tmux','all','x','literal')],None),'all')
        labels=picker.call_args.args[1]
        self.assertIn('38;2;17;34;51mall',labels[0])
        self.assertIn('38;2;68;85;102mall',labels[1])
        self.assertEqual([ANSI.sub('',line) for line in labels],[' all',' all'])
        for mode in ('', '\0', '\\u0000', 'mode-json:"\\u0000"'):
            with patch.object(RichSelector,'fzf',return_value=[1]) as picker:
                self.assertEqual(choose_mode(ui,[record('tmux',mode,'x','literal')],None),mode)
            self.assertNotIn('\0',''.join(picker.call_args.args[1]))
        menu=Menu('wttr:main','Weather',weather.ENTRIES)
        for color in ('always','never','auto'):
            for icons in ('always','never'):
                with patch.dict(os.environ,DOTS_COLOR=color,DOTS_ICONS=icons,NO_COLOR='1'):
                    labels=styled_labels(menu,self.ui(),compact=True)
                self.assertEqual(ANSI.sub('',labels[1]),' Daily forecast')
                self.assertEqual('\x1b[' in ''.join(labels),color=='always')
                if icons=='never':
                    self.assertEqual([ANSI.sub('',line) for line in labels],[' '+entry.label for entry in weather.ENTRIES])
        self.assertEqual(tuple(entry.id for entry in weather.ENTRIES),
                         ('current','daily','hourly','location','units','refresh','help','back'))
        for entries in (weather.ENTRIES,weather.LOCATION_ENTRIES,weather.UNIT_ENTRIES):
            self.assertTrue(all(entry.icon and entry.icon_role for entry in entries))

    def test_profile_parent_inheritance_and_reset(self):
        parent=self.root/'profiles/linux';child=parent/'distros/menu';child.mkdir(parents=True)
        (child/'profile.json').write_text(json.dumps(dict(schema=1,id='linux/menu',extends=['linux'])))
        (parent/'icons.toml').write_text('[weather]\ndaily="P"\n')
        (parent/'colors.toml').write_text('[apps.menu.label]\nfg="#112233"\nbold=true\n')
        (child/'icons.toml').write_text('[weather]\ndaily="C"\n')
        (child/'colors.toml').write_text('[apps.menu.label]\nbold=false\n')
        with patch.dict(os.environ,DOTS_PROFILE='linux/menu'):
            self.reset();menu=Menu('wttr:main','Weather',weather.ENTRIES)
            labels=styled_labels(menu,self.ui(),compact=True)
            self.assertIn('C ',ANSI.sub('',labels[1]));self.assertIn('\x1b[38;2;17;34;51mDaily',labels[1])
            self.run_config('unset','icons.weather.daily','--profile','linux/menu','--no-refresh')
            self.reset();labels=styled_labels(menu,self.ui(),compact=True)
            self.assertIn('P ',ANSI.sub('',labels[1]))
            self.run_config('unset','colors.apps.menu.label.bold','--profile','linux/menu','--no-refresh')
            self.reset();labels=styled_labels(menu,self.ui(),compact=True)
            self.assertIn('\x1b[1;38;2;17;34;51mDaily',labels[1])

    def test_new_roles_config_discovery_edit_explain_popup_and_completion(self):
        from profile_config import keys
        from config_menu import Inventory
        from config_completion import key_candidates
        available=set(keys(self.root));inventory=Inventory(self.root,self.platform)
        for role in ('weather.daily','weather.hourly','weather.units','navigation.refresh','navigation.back'):
            key='icons.'+role
            self.assertIn(key,available);self.assertIsNotNone(inventory.find(key))
            self.assertIn('colors.icons.'+role+'.fg',available)
            self.assertIn(key,[name for name,_ in key_candidates(self.root,key)])
        key='icons.weather.daily'
        self.run_config('set',key,'界','--no-refresh')
        self.assertEqual(self.run_config('get',key,native=True).stdout,'界\n')
        info=json.loads(self.run_config('explain',key,'--json').stdout)
        self.assertIn('cli',str(info))
        self.reset();labels=styled_labels(Menu('wttr:main','Weather',weather.ENTRIES),self.ui(),compact=True)
        self.assertIn('界 Daily forecast',ANSI.sub('',labels[1]))
        self.run_config('unset',key,'--no-refresh')
        self.assertEqual(self.run_config('get',key).stdout,'󰖙\n')

    def test_category_percentage_columns_use_final_fit_width_without_ui_drift(self):
        from row_layout import width as column_width
        self.configure(formatting={'apps':{'menu':{'label_width':'40%','label_gap':2,
                        'popup':{'width':'fit','height':'fit'}}}})
        ui=self.ui();before=(ui.width,dict(ui.formatting))
        coverage=[dict(app='tmux',count=47),dict(app='zsh',count=2)]
        row=record('tmux','root','C-x','fixture')
        binding=binding_label(ui,row,binding_styles(ui))
        for width in (40,80,120):
            labels,popup_width,height=menu_layout(ui,lambda view:[text for _,text in menu_rows(view,coverage)],
                                                size=(width,24),popup=True)
            self.assertLessEqual(popup_width,width-2);self.assertLessEqual(height,22)
            for label in labels:
                text=ANSI.sub('',label)
                expected=1+column_width('40%',popup_width-6,indent=1,gap=2)+2
                self.assertEqual(cells(text[:text.index('·')]),expected)
            self.assertEqual((ui.width,ui.formatting),before)
            self.assertEqual(binding_label(ui,row,binding_styles(ui)),binding)


class NativeStyledMenus(NativeMenuFixture):
    terminal_features = 'xterm-256color:RGB'

    def test_all_five_views_in_private_clients_and_light_dark_palettes(self):
        root=Path(self.env['DOTS']);root.mkdir()
        shutil.copytree(fixtures.ROOT/'default',root/'default')
        for platform in ('termux','linux','wsl','windows'):
            folder=root/'profiles'/platform;folder.mkdir(parents=True)
            (folder/'profile.json').write_text(json.dumps(dict(schema=1,id=platform)))
        config=self.home/'weather.toml';config.write_text('default_location="Fixture City"\n')
        log=self.base/'rows.json';self.views=[]
        code='''import json,os
from pathlib import Path
from files.catalog import Presentation
from interaction import RichSelector
from menu_tmux import TmuxContext
from keys_cli import choose_category
from keys.browser import choose_mode
from keys.model import record
from wttr import browser
original=RichSelector.fzf
def observe(self,*args,**kwargs):
    Path(os.environ['ROWS']).write_text(json.dumps(dict(labels=args[1],colors=args[6],popup=kwargs.get('popup'))))
    return original(self,*args,**kwargs)
RichSelector.fzf=observe
context=TmuxContext.capture(client=os.environ['CLIENT'])
ui=Presentation(terminal=True);ui.menu_context=context
view=os.environ['VIEW']
if view=='categories': result=choose_category(ui,[dict(app='tmux',count=47),dict(app='zsh',count=2)])
elif view=='modes': result=choose_mode(ui,[record('tmux','root','x','fixture')],None)
elif view=='weather':
    path,cfg=browser.config(os.environ['WEATHER_CONFIG'])
    result=browser.pick(browser.Session(path,cfg,None),{},context)
elif view=='location': result=browser.select('Location',browser.LOCATION_ENTRIES,context)
else: result=browser.select('Units',browser.UNIT_ENTRIES,context)
print(result)
'''
        for theme,fg,bg in (('dark','#abcdef','#101820'),('light','#234567','#f0f4f8')):
            (root/'default/colors.toml').write_text(
                '[apps.menu.icon]\nfg="#d07842"\n[apps.menu.label]\nfg="'+fg+'"\n'
                '[apps.menu.description]\nfg="#778899"\n')
            defaults=json.loads((root/'default/config.json').read_text())
            defaults['colors']['apps']['menu']['popup']['body'].update(fg=fg,bg=bg)
            (root/'default/config.json').write_text(json.dumps(defaults))
            for width,height in ((40,12),(80,24),(120,30)):
                self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',height,width,0,0))
                from menu_tmux import TmuxContext
                context=TmuxContext.capture(client=self.first[2])
                for _ in range(30):
                    if context.verify()==(width,height):break
                    time.sleep(.05)
                self.assertEqual(context.verify(),(width,height))
                for view,needle in (('categories',b'tmux'),('modes',b'modes:'),('weather',b'Current'),
                                    ('location',b'Location:'),('units',b'Units:')):
                    self.drain(self.first[1]);self.drain(self.second[1])
                    worker=self.worker(code,VIEW=view,ROWS=str(log),WEATHER_CONFIG=str(config),
                                       DOTS_COLOR='always',DOTS_ICONS='always',COLORTERM='truecolor')
                    rendered=self.receive(self.first[1],needle)
                    data=json.loads(log.read_text())
                    self.assertIn('fg+:-1:regular',data['colors'])
                    self.assertIn('\x1b[', ''.join(data['labels']))
                    self.assertIn(('38;2;171;205;239m' if theme=='dark' else '38;2;35;69;103m'), rendered.decode(errors='replace'))
                    self.assertTrue(all(int(n)<=limit for n,limit in zip(data['popup'].split(',')[1:3],(width,height))))
                    self.assertNotIn(needle,self.drain(self.second[1]))
                    os.write(self.first[1],b'\r')
                    output,error=worker.communicate(timeout=15)
                    self.assertEqual(worker.returncode,0,error)
                    self.views.append(dict(theme=theme,width=width,height=height,view=view,
                                           labels=data['labels'],terminal=rendered.decode(errors='replace'),result=output.strip()))
        self.assertFalse((Path(self.env['XDG_CACHE_HOME'])/'wttr').exists())
        self.assertEqual(config.read_text(),'default_location="Fixture City"\n')
        self.assertFalse(list(self.base.glob('dots-menu-*')))


if __name__=='__main__':
    unittest.main(verbosity=2)
