#!/usr/bin/env python3
"""Popup-specific appearance, with owned profiles and private native clients."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from test_menus import NativeMenuFixture
from config_values import current as controls
from style_config import current as styles
from interaction import RichSelector, SelectionEnded
from menu_tmux import TmuxContext
from menu_popup import geometry, tmux_flags, dimensions, content_size


class PopupConfig(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default', self.root/'default')
        self.env.update(TERM='xterm-256color', DOTS_COLOR='always', DOTS_ICONS='always')
        self.environment=patch.dict(os.environ,self.env,clear=True)
        self.environment.start();self.addCleanup(self.environment.stop)
        self.addCleanup(controls.cache_clear);self.addCleanup(styles.cache_clear)
        self.configure({})

    def configure(self, options):
        doc=json.loads(self.path.read_text());doc.setdefault('apps',{}).setdefault('menu',{})['popup']=options
        self.path.write_text(json.dumps(doc));controls.cache_clear();styles.cache_clear()

    def cli(self,*args,**kwargs):
        return fixtures.ProfileConfig.run_config(self,*args,**kwargs)

    def test_config_discovery_inheritance_validation_and_next_popup(self):
        from profile_config import keys
        from config_menu import Inventory,Draft
        self.assertIn('apps.menu.popup.colors.border',keys(self.root))
        self.assertEqual(self.cli('get','apps.menu.popup.position').stdout,'center\n')
        self.assertEqual(self.cli('get','apps.menu.popup.colors.bg').stdout,'null\n')
        self.cli('set','apps.menu.popup.position','left','--no-refresh')
        self.assertEqual(self.cli('get','apps.menu.popup.position',native=True).stdout,'left\n')
        self.cli('unset','apps.menu.popup.position','--no-refresh')
        self.assertEqual(self.cli('get','apps.menu.popup.position').stdout,'center\n')
        for key,value in [('apps.menu.popup.position','top,50%'),('apps.menu.popup.position','$(touch BAD)'),
                          ('apps.menu.popup.border','bad'),('apps.menu.popup.colors.border','red:bold'),
                          ('apps.menu.popup.colors.bg','#(touch BAD)'),('formatting.apps.tmux.position','center')]:
            self.cli('set',key,value,'--no-refresh',code=1)
        inventory=Inventory(self.root,self.platform)
        draft=Draft(inventory,inventory.find('apps.menu.popup.border')).prepare('double')
        self.assertIn('next popup',draft.review())
        with patch('config_refresh.refresh',side_effect=AssertionError('popup save must not publish a theme')):
            result=draft.save()
        self.assertEqual(result['refresh']['consumers'],[dict(app='menu',status='next popup')])
        self.assertEqual(self.cli('get','apps.menu.popup.border').stdout,'double\n')
        same=Draft(Inventory(self.root,self.platform),inventory.find('apps.menu.popup.border')).prepare('double')
        inactive=next(p for p in ('termux','linux','wsl','windows') if p!=self.platform)
        other=Inventory(self.root,inactive)
        later=Draft(other,other.find('apps.menu.popup.border')).prepare('sharp')
        with patch('config_refresh.refresh',side_effect=AssertionError('inactive/no-op popup save must not publish')):
            self.assertEqual(same.save()['refresh']['status'],'unchanged')
            self.assertEqual(later.save()['refresh']['status'],'unchanged')
        data=json.loads(self.cli('explain','apps.menu.popup.position','--json').stdout)
        self.assertEqual(data['activation'],'next popup')
        self.assertFalse((self.home/'BAD').exists())

    def test_fzf_border_and_colors_override_shell_defaults_without_changing_protocol(self):
        self.configure(dict(position='right',border='double',colors={'border':'#123456','bg':'#112233'}))
        result=subprocess.CompletedProcess([],0,b'0\tliteral\0')
        with patch('interaction.subprocess.run',return_value=result) as run:
            self.assertEqual(RichSelector(backend='fzf').fzf('Popup',['literal'],False,None,True,True,
                'border:#ffffff,fg:#abcdef,bg:#000000',popup='center,38,12'),[0])
        argv=run.call_args.args[0]
        self.assertEqual([v for v in argv if v.startswith('--border')],['--border=double'])
        self.assertEqual(argv[argv.index('--popup')+1],'right,38,12')
        colors=next(v[8:] for v in argv if v.startswith('--color='))
        self.assertEqual(dict(v.split(':',1) for v in colors.split(','))['border'],'#123456')
        self.assertTrue(colors.endswith('bg:#112233'),colors)
        self.assertIn('--read0',argv);self.assertIn('--print0',argv)
        self.assertEqual(run.call_args.kwargs['env']['FZF_DEFAULT_OPTS'],'')
        from fzf_config import picker_options,shell_options
        options={'default_opts':['--border=none','--no-border']}
        self.assertIn('--border=none',shell_options(options))
        self.assertEqual(picker_options(options)[0],[])
        for position in ('center','top','bottom','left','right'):
            self.assertEqual(geometry('center,40,12',dict(position=position)),position+',40,12')
        with patch('menu_popup.colors',side_effect=AssertionError('plain palette read')), \
             patch('interaction.subprocess.run',return_value=subprocess.CompletedProcess([],130,b'')) as run:
            with self.assertRaises(SelectionEnded):
                RichSelector(backend='fzf').fzf('Popup',['literal'],False,None,False,False,'',popup=False)
        self.assertIn('--color=bw',run.call_args.args[0]);self.assertIn('--no-unicode',run.call_args.args[0])
        self.assertIn('--border=double',run.call_args.args[0])

    def test_native_host_uses_local_position_and_color_flags(self):
        self.configure(dict(position='top',border='double',colors={'border':'#123456','fg':'#abcdef','bg':'#112233'}))
        context=TmuxContext('/tool/tmux','/private/socket','/dev/pts/7',123,'%2','$1',str(self.home))
        with patch.object(TmuxContext,'verify',return_value=(80,24)), \
             patch('menu_tmux.subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            self.assertEqual(context.popup(['fixture'],size=(24,10)),0)
        argv=run.call_args.args[0]
        self.assertIn('-xC',argv);self.assertIn('-y10',argv)
        self.assertIn('double',argv);self.assertIn('fg=#123456,bg=#112233',argv)
        self.assertIn('fg=#abcdef,bg=#112233',argv)
        self.assertEqual(argv[argv.index('-c')+1],context.client)
        self.assertEqual(argv[-1],'fixture')
        for position,xy in [('left',['-x0','-yC']),('right',['-xR','-yC']),('bottom',['-xC','-y24'])]:
            self.assertEqual(tmux_flags(dict(position=position),10,24,color=False)[:2],xy)
        self.assertIn('-B',tmux_flags(dict(border='none'),10,24,color=False))
        with patch('menu_popup.colors',side_effect=AssertionError('plain host palette read')):
            plain=tmux_flags(dict(border='rounded'),10,24,color=False,icons=False)
        self.assertEqual(plain[plain.index('-b')+1],'simple')
        self.assertEqual(plain[plain.index('-s')+1],'fg=default,bg=default')
        self.assertEqual(plain[plain.index('-S')+1],'fg=default,bg=default')

    def test_allowed_values_dialogs_and_completion(self):
        from config_menu import Inventory, details, input_value
        for key, choices in [('apps.menu.popup.border',['rounded','sharp','double','bold','none']),
                             ('apps.menu.popup.position',['center','top','bottom','left','right']),
                             ('formatting.apps.todo.list_type',['tree','regular']),
                             ('apps.nvim.options.wrap',[True,False])]:
            data=json.loads(self.cli('explain',key,'--json',native=True).stdout)
            self.assertEqual(data['constraints']['choices'],choices)
            row=Inventory(self.root,self.platform).find(key)
            self.assertIn('Allowed',details(row))
            with patch('config_menu.select',return_value=json.dumps(choices[0])) as select, \
                 patch('config_menu.prompt',side_effect=AssertionError('finite choice used text input')):
                self.assertEqual(input_value(row,'',None),json.dumps(choices[0]))
            self.assertEqual([json.loads(v[0]) for v in select.call_args.args[1]],choices)
        row=Inventory(self.root,self.platform).find('apps.menu.popup.width')
        self.assertIn('90%',details(row))
        with patch('config_menu.select',return_value='__custom__'), patch('config_menu.prompt',return_value='83%'):
            self.assertEqual(input_value(row,'auto',None),'83%')
        with patch('config_menu.select',return_value=None): self.assertIsNone(input_value(row,'auto',None))
        for shell in ('bash','zsh','fish'):
            command=[str(self.root/'bin/dots'),'__complete',shell,'4','--','dots','config','set','apps.menu.popup.border','']
            result=subprocess.run(command,env=self.env,text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual([line.split('\t')[1] for line in result.stdout.splitlines()],['rounded','sharp','double','bold','none'])
        result=subprocess.run([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete','config','set','apps.menu.popup.width',''],env=self.env,text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('candidate\tfit\t',result.stdout);self.assertIn('candidate\t90%\t',result.stdout)
        from config_values import candidates
        self.assertEqual(candidates(self.root,'apps..popup'),[])
        self.assertEqual(candidates(self.root,'apps.fzf.bindings.position'),[])
        dynamic=json.loads(self.cli('explain','apps.nvim.highlights["Normal"].bold','--json').stdout)
        self.assertEqual(dynamic['constraints']['choices'],[True,False])

    def test_size_validation_bounds_and_inline_fallback(self):
        from config_values import read_defaults,validate_value
        defaults=read_defaults(self.root)
        for value in ('auto','fit','fill','1%','90%','100%',1,10000):
            validate_value(defaults,('apps','menu','popup','width'),value)
        for value in ('0%','101%','90%; touch BAD','50%,30%','80','-2%',0,-1,True,1.5,{},[],10001):
            with self.assertRaises(ValueError):validate_value(defaults,('apps','menu','popup','height'),value)
        self.cli('set','apps.menu.popup.width','90%')
        self.assertEqual(self.cli('get','apps.menu.popup.width').stdout,'90%\n')
        self.cli('unset','apps.menu.popup.width')
        self.assertEqual(self.cli('get','apps.menu.popup.width').stdout,'auto\n')
        self.assertEqual(dimensions({'width':'90%','height':'50%'},(35,10),(80,30)),(72,15))
        self.assertEqual(dimensions({'width':'fill','height':'fill'},(35,10),(40,12)),(40,12))
        self.assertEqual(dimensions({'width':10000,'height':1},(35,10),(20,4)),(20,4))
        self.assertEqual(geometry('center,35,10',{'width':'fit','height':'fit'},size=(80,30),content=(40,9)),'center,40,9')
        self.assertEqual(geometry('center,35,10',{'width':'fit','height':'fit'},size=(80,30)),'center,35,10')
        self.assertEqual(content_size(['\x1b[31m界界\x1b[0m'],'','',(80,30),{'width':'fit'}),(10,6))
        self.configure({'width':'90%','height':'50%'})
        with patch('interaction.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'0\tONE\0')) as run:
            RichSelector(backend='fzf').fzf('Fixture',['ONE'],False,None,False,False,'',popup=False,
                environment={'DOTS_MENU_COLUMNS':'40','DOTS_MENU_LINES':'30'})
        self.assertIn('--height=15',run.call_args.args[0]);self.assertNotIn('--popup',run.call_args.args[0])
        with patch('interaction.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'0\tONE\0')) as run:
            RichSelector(backend='fzf').fzf('Fixture',['ONE'],False,('inert-preview',None,{}),False,False,'',
                popup='center,35,28',preview_position='down',preview_lines=22,header='Enter: choose',
                environment={'DOTS_MENU_COLUMNS':'40','DOTS_MENU_LINES':'30'})
        self.assertIn('--preview-window=down,7',run.call_args.args[0])
        from menu_pager import report_size
        report=self.home/'report.txt';report.write_text('x'*60+'\n')
        self.assertEqual(report_size(report,(40,30)),(36,6))
        context=TmuxContext('/tool/tmux','/private/socket','/dev/pts/7',123,'%2','$1',str(self.home))
        with patch.object(TmuxContext,'verify',return_value=(40,30)), \
             patch('menu_tmux.subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            context.popup(['fixture'],size=(35,10))
        self.assertIn('-w36',run.call_args.args[0]);self.assertIn('-h15',run.call_args.args[0])


class NativePopup(NativeMenuFixture):
    terminal_features = 'xterm-256color:RGB'

    def test_real_frame_colors_and_placement_at_three_widths(self):
        root=Path(self.env['DOTS']);root.mkdir()
        shutil.copytree(fixtures.ROOT/'default',root/'default')
        for profile in ('termux','linux','wsl','windows'):
            path=root/'profiles'/profile;path.mkdir(parents=True)
            (path/'profile.json').write_text(json.dumps(dict(schema=1,id=profile)))
        palette=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme';palette.mkdir(parents=True)
        (palette/'palette.json').write_text(json.dumps(dict(colors=dict(accent='#123456'))))
        code='''import os,json,subprocess
from unittest.mock import patch
from interaction import RichSelector
from menu_tmux import TmuxContext
ctx=TmuxContext.capture(client=os.environ['CLIENT'])
with ctx.selector_environment() as env:
    with patch('interaction.subprocess.run',wraps=subprocess.run) as run:
        chosen=RichSelector(backend='fzf').fzf('Popup fixture',['ONE','TWO'],False,None,True,True,
            'fg:#abcdef,bg:'+os.environ['BG'],popup='center,30,10',environment=env)
    args=run.call_args.args[0]
print(json.dumps([chosen,args[args.index('--popup')+1]]))
'''
        for width,position,background,sizes,expected in ((40,'center','#111111',('90%','50%'),'center,36,15'),
                (80,'top','#eeeeee',('fit','fit'),'top,32,8'),(120,'right','#111111',('fill','fill'),'right,120,30')):
            defaults=root/'default/config.json';doc=json.loads(defaults.read_text())
            doc['apps']['menu']['popup'].update(position=position,width=sizes[0],height=sizes[1]);defaults.write_text(json.dumps(doc))
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,width,0,0))
            time.sleep(.15);self.drain(self.first[1]);self.drain(self.second[1])
            worker=self.worker(code,BG=background)
            data=self.receive(self.first[1],b'ONE')
            self.assertIn('╭'.encode(),data)
            self.assertIn(b'38;2;18;52;86',data)
            self.assertNotIn(b'ONE',self.drain(self.second[1]))
            os.write(self.first[1],b'\r');out,err=worker.communicate(timeout=10)
            self.assertEqual(worker.returncode,0,err);self.assertEqual(json.loads(out),[[0],expected])


if __name__=='__main__':unittest.main()
