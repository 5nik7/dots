#!/usr/bin/env python3
"""Aligned rows, mode selection and previews in owned FZF sessions."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import test_keys

ROOT = test_keys.ROOT
FZF = shutil.which('fzf')
POWERSHELL = shutil.which('pwsh') or shutil.which('powershell')
from keys import browser
from keys.model import record
from keys.presentation import binding_label, binding_prompt, column_widths, fit, styles
from resources import cells
from files.catalog import Presentation
from interaction import RichSelector, SelectionEvent, SelectionEnded
import keys_cli


class Browser(unittest.TestCase):
    setUp = test_keys.Keys.setUp
    cli = test_keys.Keys.cli

    def data(self):
        return dict(rows=[
            record('tmux', 'zeta', 'C-z', 'needle-zeta', description='needle target zeta', status='unverified'),
            record('tmux', 'alpha', 'C-x', 'different', description='different', status='unverified'),
            record('tmux', 'alpha', 'C-y', 'needle-alpha', description='needle target alpha', status='unverified'),
        ], coverage=[dict(app='tmux',count=3,live=False,notes=[])])


    def test_interactive_initial_mode_does_not_discard_other_modes(self):
        with patch('keys_cli.collect', return_value=self.data()) as collect, \
             patch('keys_cli.picker_ui', side_effect=lambda ui: ui), patch('keys_cli.browse') as browse, \
             patch('keys_cli.shutil.which', return_value='/fixture/fzf'):
            keys_cli.main(['tmux', '--browse', '--mode', 'alpha'])
            self.assertEqual(len(browse.call_args.args[1]['rows']), 3)
            self.assertEqual(browse.call_args.kwargs, dict(app='tmux', mode='alpha'))
            collect.assert_called_once()
            self.assertEqual(collect.call_args.args[1], 'tmux')
        for flag in ('--json', '--print'):
            with patch('keys_cli.collect', return_value=self.data()), patch('sys.stdout', io.StringIO()) as out:
                keys_cli.main(['tmux', flag, '--mode', 'alpha'])
                self.assertNotIn('needle-zeta', out.getvalue())
                if flag == '--json': self.assertEqual(len(json.loads(out.getvalue())['rows']), 2)


    def test_counted_menu_reuses_filtered_live_snapshot_and_legacy_apps(self):
        from keys.presentation import menu_rows
        live = [record('zsh', mode, '^G', mode, evidence='live') for mode in ('viins', 'vicmd')]
        for route in ([], ['apps']):
            data = dict(version=1, rows=[*live, record('zsh','main','x','configured'),
                record('codex','editor','x','default', default=True)], coverage=[
                    dict(app=app,count=99,live=False,notes=[]) for app in ('zsh','codex','kitty')])
            def choose(ui, coverage, **kwargs):
                expected = ['all','zsh'] if not route else ['zsh']
                self.assertEqual([r[0] for r in menu_rows(ui,coverage,**kwargs)], expected)
                self.assertEqual([c['count'] for c in coverage], [2,0,0])
                return 'zsh'
            with patch.dict(os.environ, DOTS_KEYS_TARGET_PANE='%7'), \
                 patch('keys.zsh_bridge.capture',return_value=(live,'fixture')) as capture, \
                 patch('keys_cli.collect',return_value=data) as collect, \
                 patch('keys_cli.choose_category',side_effect=choose) as category, \
                 patch('keys_cli.picker_ui',side_effect=lambda ui:ui), \
                 patch('keys_cli.shutil.which',return_value='/fixture/fzf'), patch('keys_cli.browse') as browse:
                keys_cli.main([*route,'--browse','--source','live','--no-defaults','--mode','viins','--query','missing'])
                capture.assert_called_once_with('%7');collect.assert_called_once();category.assert_called_once()
                self.assertIsNone(collect.call_args.args[1])
                self.assertEqual(collect.call_args.args[2], live)
                self.assertEqual(browse.call_args.args[1]['rows'], live)
                self.assertEqual(browse.call_args.args[2], 'missing')
                self.assertEqual(browse.call_args.kwargs, dict(app='zsh',mode='viins'))

    def test_empty_menu_and_data_coverage_keep_zero_apps(self):
        data = dict(version=1,rows=[],coverage=[dict(app='tmux',count=0,live=False,notes=[])])
        with patch('keys_cli.collect',return_value=data), patch('keys_cli.picker_ui',side_effect=lambda ui:ui), \
             patch('keys_cli.shutil.which',return_value='/fixture/fzf'), patch('keys_cli.choose_category') as category, \
             patch('keys_cli.browse') as browse, patch('sys.stdout',io.StringIO()) as output:
            self.assertEqual(keys_cli.main(['--browse']), 0)
            self.assertIn('No matching keybindings', output.getvalue())
            category.assert_not_called();browse.assert_not_called()
        with patch('keys_cli.collect',return_value=data), patch('keys_cli.picker_ui',side_effect=AssertionError), \
             patch('sys.stdout',io.StringIO()) as output:
            keys_cli.main(['apps','--json'])
            self.assertEqual(json.loads(output.getvalue()),data)

    def test_menu_counts_keep_muted_color_and_visible_width_in_both_palettes(self):
        from keys.presentation import menu_rows, menu_dimensions
        ui = Presentation(io.StringIO());ui.icons = False
        ui.resources.root = self.base / 'count-palette';ui.resources.root.mkdir()
        coverage = [dict(app='tmux',count=47),dict(app='zsh',count=123456789012345),dict(app='kitty',count=0)]
        for muted in ('#667788','#99aabb'):
            (ui.resources.root/'palette.json').write_text(json.dumps(dict(colors=dict(muted=muted))))
            ui.color = True
            colored = menu_rows(ui,coverage)
            code = styles(ui)[0]
            self.assertIn('tmux\x1b['+code+'m · [47]\x1b[0m',colored[1][1])
            ui.color = False
            plain = menu_rows(ui,coverage)
            self.assertEqual([r[0] for r in plain],['all','tmux','zsh'])
            self.assertEqual(plain[0][1], 'All · [123456789012392]')
            for width in (40,80,120):
                self.assertEqual(menu_dimensions([r[1] for r in plain],size=(width,24)),
                                 menu_dimensions([r[1] for r in colored],size=(width,24)))

    def test_prompts_columns_unicode_and_stable_identities(self):
        ui = Presentation(io.StringIO()); ui.color = False
        for icons in (False, True):
            ui.icons = icons; prefix = '󰌆 ' if icons else ''
            for app, mode, expected in ((None,None,''),('tmux',None,'tmux'),('zsh','viins','zsh·viins'),(None,'viins','all·viins')):
                self.assertEqual(binding_prompt(ui,app,mode),prefix+expected)
        rows = self.data()['rows']
        rows[0].update(app='application-long', mode='very-long-mode-name', display='e\u0301界'*18)
        for columns in (40,80,120):
            labels, indices, position = browser.view(ui, rows, None, None, columns)
            self.assertEqual(indices,[0,1,2]); self.assertEqual(position,'right' if columns==120 else 'down')
            widths = [[cells(field) for field in label.split(' · ')[:3]] for label in labels]
            self.assertTrue(all(width == widths[0] for width in widths))
            self.assertTrue(all(width <= cap for width,cap in zip(widths[0],(12,18,16))))
            self.assertIn('…',labels[0]); self.assertNotIn('\x1b',labels[0])
            labels, indices, _ = browser.view(ui, rows, 'tmux', 'alpha', columns)
            self.assertEqual(indices,[1,2])
            self.assertTrue(all(labels[i].startswith(rows[i]['display']) for i in indices))
            self.assertTrue(all(len(labels[i].split(' · '))==3 for i in indices))
        self.assertEqual(fit('e\u0301界abc',4),'e\u0301界…')
        self.assertEqual(fit('界',1),'…')
        self.assertEqual(fit('a',4),'a   ')
        self.assertEqual(column_widths(ui,rows,500),dict(app=12,mode=18,display=16))
        labels,indices,_=browser.view(ui,rows,None,'unknown',80)
        self.assertEqual(indices,[])
        self.assertEqual(rows[0]['display'],'e\u0301界'*18)

    def test_palette_colors_and_preview_order_wrapping(self):
        ui=Presentation(io.StringIO());ui.icons=False
        ui.resources.root=self.base/'preview-palette';ui.resources.root.mkdir()
        row=record('zsh','viins','^G','fixture',description='Move across café 日本語 ' * 8,
                   source=self.home/'literal file.py',line=7,status='unverified')
        for muted,orange in (('#667788','#dd7700'),('#aabbcc','#ff9933')):
            (ui.resources.root/'palette.json').write_text(json.dumps(dict(colors=dict(muted=muted,orange=orange,bright_magenta='#ff88cc'))))
            for width in (13,40,80,120):
                for color in (False,True):
                    ui.width=width;ui.color=color;ui.stream=io.StringIO()
                    keys_cli.preview_details(ui,row)
                    text=ui.stream.getvalue();plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                    self.assertTrue(plain.startswith('Keys'))
                    self.assertNotIn('zsh keybinding',plain)
                    self.assertLess(plain.index('Keys'),plain.index('Action'))
                    self.assertLess(plain.index('Action'),plain.index('Mode'))
                    self.assertTrue(all(cells(line)<=width for line in plain.splitlines()))
                    if width>13:
                        self.assertIn('Mode        viins',plain)
                        self.assertIn('Keys        Ctrl+G',plain)
                        action=plain.split('Action      ',1)[1].split('\nMode',1)[0]
                        self.assertEqual(action.replace('\n'+' '*12,''),row['description'])
                    if color:
                        muted_code,key,mode=styles(ui)
                        self.assertIn('\x1b['+key+'m',text);self.assertIn('\x1b['+mode+'mviins',text)
                        self.assertIn('\x1b['+muted_code+'m',text)
                        label=binding_label(ui,row,styles(ui))
                        self.assertIn('\x1b['+mode+'mviins',label)
                    else:self.assertNotIn('\x1b',text)
        self.assertNotIn('Zsh:',keys_cli.binding_header())
        self.assertNotIn('Mode:',keys_cli.binding_header())
        self.assertIn('Alt-M: mode',keys_cli.binding_header())
        path=self.base/'preview.json';path.write_text(json.dumps([row]))
        self.env.update(FZF_PREVIEW_COLUMNS='40',DOTS_COLOR='never',DOTS_ICONS='never')
        out=self.cli('--preview',str(path),'0').stdout
        self.assertTrue(out.startswith('Keys'))
        self.assertTrue(all(cells(line)<=40 for line in out.splitlines()))
        ui.stream=io.StringIO();keys_cli.details(ui,row)
        self.assertIn('zsh keybinding',ui.stream.getvalue())

    def test_selector_custom_events_preserve_query_and_defaults(self):
        calls=[]
        def run(argv,**kwargs):
            calls.append((argv,kwargs))
            return subprocess.CompletedProcess(argv,1,'café query\0alt-m\0'.encode())
        with patch('interaction.subprocess.run',side_effect=run):
            state={}
            with self.assertRaises(SelectionEvent) as event:
                RichSelector(backend='fzf').fzf('tmux', ['first'], False, None, False, False, '',
                    navigation=state,navigation_keys={'alt-m':'mode'},initial_indices=[],hscroll=False)
            self.assertEqual(event.exception.action,'mode');self.assertEqual(state['query'],'café query')
            self.assertIn('--expect=alt-m',calls[0][0]);self.assertIn('--no-hscroll',calls[0][0])
            self.assertIn('esc:abort',','.join(calls[0][0]));self.assertEqual(calls[0][1]['input'],b'')
        with patch('interaction.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'2\tthird\0')) as run:
            self.assertEqual(RichSelector().fzf('Other',['first','second','third'],False,None,False,False,'',initial_indices=[2]),[2])
            self.assertEqual(run.call_args.kwargs['input'],b'2\tthird\0')
            self.assertNotIn('--print-query',run.call_args.args[0]);self.assertNotIn('--no-hscroll',run.call_args.args[0])
        for event in ('alt-m)+execute(evil)', 'ctrl-c', 'enter'):
            with self.assertRaises(ValueError):
                RichSelector().fzf('Bad',['one'],False,None,False,False,'',navigation={},navigation_keys={event:'mode'})
        with patch('interaction.subprocess.run',return_value=subprocess.CompletedProcess([],130,b'')):
            with self.assertRaises(SelectionEnded):
                RichSelector().fzf('tmux',[],False,None,False,False,'',navigation={},navigation_keys={'alt-m':'mode'})

    def test_mode_chooser_order_focus_cancel_and_literal_labels(self):
        ui=Presentation(io.StringIO());ui.color=False;ui.icons=False
        rows=self.data()['rows']+[record('tmux','unsafe\x1b\n$(touch sentinel)','x','fixture')]
        with patch('interaction.RichSelector.fzf',return_value=[1]) as fzf:
            self.assertEqual(browser.choose_mode(ui,rows,'zeta'),'alpha')
            self.assertEqual(fzf.call_args.args[0],'modes')
            self.assertEqual(fzf.call_args.args[1][:2],['all','alpha'])
            self.assertNotIn('\x1b',fzf.call_args.args[1][2])
            self.assertEqual(fzf.call_args.kwargs['bindings'],['load:pos(4)'])
            self.assertNotIn('query',fzf.call_args.kwargs)
            self.assertLess(fzf.call_args.kwargs['height'],24)
        with patch('interaction.RichSelector.fzf',side_effect=SelectionEvent('back')):
            self.assertEqual(browser.choose_mode(ui,rows,'zeta'),'zeta')
        with patch('interaction.RichSelector.fzf',side_effect=SelectionEnded(130)):
            with self.assertRaises(SelectionEnded):browser.choose_mode(ui,rows,'zeta')
        self.assertFalse((self.home/'sentinel').exists())

    def test_navigation_retains_snapshot_query_and_cleans_preview(self):
        ui=Presentation(io.StringIO());ui.color=False;ui.icons=False
        calls=[];paths=[]
        def select(*args,**kwargs):
            calls.append((args,kwargs))
            if args[3] is None:
                self.assertEqual(args[0],'modes')
                if len(calls)==2:return [1]
                raise SelectionEvent('back')
            path=Path(args[3][2]['DOTS_KEYS_DATA']);paths.append(path)
            self.assertEqual(json.loads(path.read_text()),self.data()['rows'])
            if len(calls)==1:
                self.assertEqual(kwargs['initial_indices'],[])
                self.assertEqual(args[0],'tmux·missing')
                kwargs['navigation']['query']='needle';raise SelectionEvent('mode')
            self.assertEqual(kwargs['query'],'needle')
            self.assertEqual(kwargs['initial_indices'],[1,2]);self.assertEqual(args[0],'tmux·alpha')
            self.assertTrue(args[1][2].startswith('Ctrl+Y'))
            if len(calls)==3:raise SelectionEvent('mode')
            return [2]
        with patch('interaction.RichSelector.fzf',side_effect=select),patch('keys_cli.collect',side_effect=AssertionError),patch('keys_cli.details') as details:
            keys_cli.browse(ui,self.data(),'initial',app='tmux',mode='missing')
            self.assertEqual(details.call_args.args[1]['action'],'needle-alpha')
        self.assertEqual(len(calls),5);self.assertEqual(len(set(paths)),1)
        self.assertFalse(paths[0].exists())
        def cancel(*args,**kwargs):
            paths.append(Path(args[3][2]['DOTS_KEYS_DATA']));raise SelectionEnded(130)
        with patch('interaction.RichSelector.fzf',side_effect=cancel),self.assertRaises(SelectionEnded):
            keys_cli.browse(ui,self.data(),'',app='tmux')
        self.assertFalse(paths[-1].exists())
        with patch('interaction.RichSelector.fzf',return_value=[0]) as fzf:
            keys_cli.choose_category(ui,self.data()['coverage'])
            self.assertEqual(fzf.call_args.kwargs['info'],'inline-right');self.assertEqual(fzf.call_args.args[0],'')

    @unittest.skipUnless(POWERSHELL,'Native PowerShell unavailable')
    def test_native_powershell_preview(self):
        path=self.base/'preview ü.json';path.write_text(json.dumps(self.data()['rows']))
        env=dict(self.env,DOTS_KEYS_PYTHON=sys.executable,DOTS_KEYS_HELPER=str(ROOT/'lib/dots/keys_cli.py'),
                 DOTS_KEYS_DATA=str(path),FZF_PREVIEW_COLUMNS='40',DOTS_COLOR='never')
        command='[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); & $env:DOTS_KEYS_PYTHON -B $env:DOTS_KEYS_HELPER --preview $env:DOTS_KEYS_DATA 2'
        result=subprocess.run([POWERSHELL,'-NoLogo','-NoProfile','-NonInteractive','-Command',command],env=env,cwd=self.home,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(b'Keys        Ctrl+Y',result.stdout)
        self.assertNotIn(b'tmux keybinding',result.stdout)

    @unittest.skipUnless(FZF and os.name!='nt','Native Unix FZF required')
    def test_native_mode_menu_retains_query_and_identity_at_three_widths(self):
        import fcntl,struct,termios
        from zsh_interactive import Session
        tool=self.base/'commands/fzf'
        if tool.exists() or tool.is_symlink():tool.unlink()
        tool.symlink_to(FZF)
        source=self.base/'data.json';source.write_text(json.dumps(self.data()))
        code='''
import json,os,sys
from pathlib import Path
sys.path.insert(0,os.environ['DOTS']+'/lib/dots')
from files.catalog import Presentation
from interaction import RichSelector
import keys_cli
original=RichSelector.fzf
log=Path(os.environ['FIXTURE_LOG'])
def observe(self,*args,**kwargs):
    with log.open('a') as stream:
        stream.write(json.dumps(dict(title=args[0],labels=args[1],indices=kwargs.get('initial_indices'),query=kwargs.get('query',''),preview=bool(args[3])))+'\\n')
    return original(self,*args,**kwargs)
RichSelector.fzf=observe
keys_cli.details=lambda ui,row: Path(os.environ['FIXTURE_RESULT']).write_text(json.dumps(row))
data=json.loads(Path(os.environ['FIXTURE_DATA']).read_text())
ui=Presentation(terminal=True)
assert keys_cli.choose_category(ui,data['coverage'])=='tmux'
keys_cli.browse(ui,data,'needle',app='tmux',mode='missing')
'''
        for width in (40,80,120):
            with self.subTest(width=width):
                result=self.base/f'result-{width}';log=self.base/f'log-{width}'
                env=dict(self.env,FIXTURE_DATA=str(source),FIXTURE_RESULT=str(result),FIXTURE_LOG=str(log),
                         DOTS_COLOR='never' if width==40 else 'always',DOTS_ICONS='never' if width==40 else 'always')
                session=Session(env,str(self.home),[sys.executable,'-B','-c',code])
                try:
                    fcntl.ioctl(session.master,termios.TIOCSWINSZ,struct.pack('HHHH',30,width,0,0))
                    session.wait(b'[3]',timeout=15)
                    session.send('tmux');time.sleep(.2);session.send('\r')
                    session.wait('tmux·missing:'.encode(),timeout=15);time.sleep(.2)
                    for wanted, marker in (('alpha','tmux·alpha:'.encode()),('all',b'tmux:'),('zeta','tmux·zeta:'.encode()),('alpha','tmux·alpha:'.encode())):
                        session.send('\x1bm');session.wait(b'modes:',timeout=15);time.sleep(.15)
                        session.send(wanted);time.sleep(.15);session.send('\r')
                        session.wait(marker,timeout=15);time.sleep(.15)
                        events=[json.loads(line) for line in log.read_text().splitlines()]
                        event=events[-1]
                        self.assertEqual(event['query'],'needle')
                        self.assertEqual(event['indices'],[0,1,2] if wanted=='all' else [0] if wanted=='zeta' else [1,2])
                        labels=[re.sub(r'\x1b\[[0-9;]*m','',label) for label in event['labels']]
                        self.assertEqual(labels[2].split(' · ')[0].strip(),'alpha' if wanted=='all' else 'Ctrl+Y')
                    # Enter without a query keeps the initially focused current mode.
                    session.send('\x1bm');session.wait(b'modes:',timeout=15);time.sleep(.2);session.send('\r')
                    session.wait('tmux·alpha:'.encode(),timeout=15);time.sleep(.15)
                    # Escape returns from the chooser, retaining the selected mode.
                    session.send('\x1bm');session.wait(b'modes:',timeout=15);time.sleep(.15);session.send('\x1b')
                    session.wait('tmux·alpha:'.encode(),timeout=15);time.sleep(.2);session.send('\r')
                    session.process.wait(timeout=10)
                    self.assertEqual(session.process.returncode,0)
                    self.assertEqual(json.loads(result.read_text())['action'],'needle-alpha')
                    self.assertFalse(list(Path(env['TMPDIR']).glob('dots-keys-*')))
                finally:session.close()


if __name__=='__main__':unittest.main(verbosity=2)
