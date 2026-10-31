#!/usr/bin/env python3
"""Config popup contracts in owned checkouts, homes and terminals."""
from contextlib import redirect_stdout, redirect_stderr
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from test_menus import NativeMenuFixture
import config_cli
import config_menu as menu
import menu_input
from interaction import SelectionEvent, SelectionEnded
from menu_tmux import request_file, read_request
from style_config import current
from transactions import Store
ROOT = fixtures.ROOT


class ConfigMenu(unittest.TestCase):
    def run_config(self, *args, native=False, **kwargs):
        return fixtures.ProfileConfig.run_config(self, *args, native=native or os.name == 'nt', **kwargs)

    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        self.env.update(USERPROFILE=str(self.home), APPDATA=str(self.home/'Roaming'),
                        LOCALAPPDATA=str(self.home/'Local'), TMPDIR=str(self.home), TMP=str(self.home), TEMP=str(self.home))
        shutil.copytree(ROOT/'default', self.root/'default')
        self.environ = patch.dict(os.environ, self.env, clear=True)
        self.environ.start(); self.addCleanup(self.environ.stop)
        current.cache_clear(); self.addCleanup(current.cache_clear)

    def inventory(self, scope=None): return menu.Inventory(self.root, scope or self.platform)

    def args(self, **kwargs):
        return argparse.Namespace(profile=None, defaults=False, client=None, query='', action='browse', **kwargs)

    def undo(self, identity):
        store = Store(config_cli.state_root())
        operations, guards, catalogs = store.inverse(identity)
        return store.apply('undo', operations, guards, retain=True, catalogs=catalogs)

    def test_reviewed_setting_undo_noop_and_drift(self):
        inventory = self.inventory(); row = inventory.find('settings.DOTS_COLOR')
        before = self.path.read_bytes()
        draft = menu.Draft(inventory, row).prepare('always')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertIn('auto', draft.review()); self.assertIn('always', draft.review())
        result = draft.save()
        self.assertEqual(json.loads(self.path.read_bytes())['settings']['DOTS_COLOR'], 'always')
        self.undo(result['id']); self.assertEqual(json.loads(self.path.read_bytes()), json.loads(before))
        inventory = self.inventory()
        stale = menu.Draft(inventory, inventory.find(row.key)).prepare('never')
        self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaises(ValueError): stale.save()
        self.assertEqual(json.loads(self.path.read_bytes())['settings'], {})
        inventory = self.inventory()
        unchanged = menu.Draft(inventory, inventory.find(row.key)).prepare(reset=True).save()
        self.assertFalse(unchanged.get('id'))

    def test_inheritance_reset_empty_icons_and_app_override(self):
        parent = self.root/'profiles/linux/profile.json'
        doc = json.loads(parent.read_text()); doc['settings']['DOTS_COLOR'] = 'never'
        parent.write_text(json.dumps(doc))
        child = self.root/'profiles/linux/distros/fixture'
        child.mkdir(parents=True)
        (child/'profile.json').write_text(json.dumps(dict(schema=1,id='linux/fixture',extends=['linux'],settings={'DOTS_COLOR':'always'})))
        inventory = self.inventory('linux/fixture')
        row = inventory.find('settings.DOTS_COLOR')
        self.assertTrue(row.local)
        draft = menu.Draft(inventory, row).prepare(reset=True)
        self.assertEqual(draft.proposed, 'never'); draft.save()
        inventory = self.inventory('linux/fixture')
        self.assertFalse(inventory.find(row.key).local)
        icon = inventory.find('icons.git.branch')
        app = inventory.app_row(icon, 'gitmux')
        self.assertEqual(app.key, 'icons.apps.gitmux.git.branch')
        draft = menu.Draft(inventory, app).prepare(''); self.assertEqual(draft.proposed, '')
        saved = draft.save()
        inventory = self.inventory('linux/fixture')
        local = inventory.find(app.key); self.assertTrue(local.local)
        reset = menu.Draft(inventory, local).prepare(reset=True)
        self.assertEqual(reset.proposed, icon.value)
        self.undo(saved['id'])

    def test_types_invalid_input_defaults_and_cancel(self):
        inventory = self.inventory()
        for key, value, expected in [('settings.files.backup','false',False), ('settings.DOTS_INIT_THEME','0','0'),
                                     ('colors.ui.heading.bold','false',False), ('colors.ui.heading.fg','#123abc','#123abc')]:
            draft = menu.Draft(inventory, inventory.find(key)).prepare(value)
            self.assertEqual(draft.proposed, expected)
        draft = menu.Draft(inventory, inventory.find('colors.ui.heading.fg'))
        with self.assertRaises(ValueError): draft.prepare('not-a-role')
        self.assertEqual(draft.prepare('blue').proposed, 'blue')
        defaults = self.inventory('defaults')
        self.assertEqual({r.group for r in defaults.rows}, {'icons','colors','formatting','apps'})
        with self.assertRaises(ValueError): menu.Draft(defaults, defaults.find('icons.git.branch')).prepare(reset=True)
        before = self.path.read_bytes()
        with patch.object(menu,'input_value',return_value='never'), patch.object(menu,'select',return_value='cancel'):
            self.assertEqual(menu.edit(inventory, inventory.find('settings.DOTS_COLOR'), None), '')
        self.assertEqual(self.path.read_bytes(), before)
        with patch.object(menu,'input_value',side_effect=SelectionEvent('back')):
            self.assertEqual(menu.edit(inventory, inventory.find('settings.DOTS_COLOR'), None), '')
        with patch.object(menu,'input_value',side_effect=SelectionEnded(130)), self.assertRaises(SelectionEnded):
            menu.edit(inventory, inventory.find('settings.DOTS_COLOR'), None)

    def test_secrets_redacted_in_review_snapshots_and_input(self):
        doc=json.loads(self.path.read_text()); doc['environment']={'API_KEY':'legacy-sensitive-literal'}
        self.path.write_text(json.dumps(doc))
        inventory=self.inventory(); row=inventory.find('environment.API_KEY')
        self.assertNotIn('legacy-sensitive-literal', menu.details(row))
        def select(*args,**kwargs):
            snapshot=read_request(Path(args[3][2]['DOTS_CONFIG_PREVIEW']))
            self.assertNotIn('legacy-sensitive-literal',json.dumps(snapshot))
            return [0]
        with patch.object(menu.RichSelector,'fzf',side_effect=select):
            menu.pick(inventory,'environment',{'mode':'get'},None)
        with patch.dict(os.environ,API_KEY='process-sensitive-literal'):
            self.assertNotIn('process-sensitive-literal',menu.details(row))
        draft=menu.Draft(inventory,row)
        with self.assertRaises(ValueError): draft.prepare('new-sensitive-literal')
        draft.prepare('${EXTERNAL_KEY}')
        self.assertNotIn('EXTERNAL_KEY', draft.review()); self.assertIn('[redacted]',draft.review())
        with patch.object(menu,'input_value',return_value=None) as input_value:
            menu.edit(inventory,row,None)
            self.assertEqual(input_value.call_args.args[1], '')
        with patch.object(menu,'input_value',side_effect=['sensitive-literal','${EXTERNAL_KEY}']) as input_value, \
             patch.object(menu,'show'),patch.object(menu,'select',return_value='cancel'):
            menu.edit(inventory,row,None)
            self.assertTrue(all(call.args[1] == '' for call in input_value.call_args_list))
        with patch.dict(os.environ,DOTS_COLOR='always'):
            details=menu.details(inventory.find('settings.DOTS_COLOR'))
            self.assertIn('auto',details);self.assertIn('always (not saved)',details)

    def test_stale_selection_reload_and_validation_retry(self):
        inventory=self.inventory();row=inventory.find('settings.DOTS_COLOR')
        with patch.object(menu,'input_value',side_effect=['bad-value','never']), \
             patch.object(menu,'show') as error, patch.object(menu,'select',return_value='save'):
            notice=menu.edit(inventory,row,None)
        self.assertIn('dots files undo',notice); error.assert_called_once()
        inventory=self.inventory();row=inventory.find('settings.DOTS_COLOR')
        def change(*args):
            self.path.write_text(self.path.read_text()+'\n'); return 'always'
        with patch.object(menu,'input_value',side_effect=change), self.assertRaisesRegex(ValueError,'changed'):
            menu.edit(inventory,row,None)

    def test_data_help_completion_and_explicit_list_do_not_browse(self):
        with patch.object(menu.TmuxContext,'from_environment',side_effect=AssertionError('tmux probed')), \
             patch.object(menu,'browser_available',side_effect=AssertionError('tools probed')), \
             patch('interaction.terminal',return_value=True):
            for args in (['--json'], ['browse','--json'], ['list','--json'], ['list'], ['get','DOTS_COLOR','--json']):
                # The fixture has no saved DOTS_COLOR until explicitly set.
                if args[0]=='get': continue
                with redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(config_cli.main(args),0)
                    if '--json' in args: self.assertEqual(json.loads(output.getvalue())['schema'],1)
        for native in ((True,) if os.name == 'nt' else (False,True)):
            listed=json.loads(self.run_config('list','--json',native=native).stdout)
            self.assertEqual(json.loads(self.run_config('browse','--json',native=native).stdout),listed)
            self.assertIn('--query',self.run_config('browse','--help',native=native).stdout)
            front=[sys.executable,'-B',str(self.root/'lib/dots/cli.py')] if native else [str(self.root/'bin/dots')]
            prefix=['__complete'] if native else ['__complete','bash','3','--','dots']
            result=subprocess.run([*front,*prefix,'config','browse','--q'],env=self.env,text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--query',result.stdout)
        from command_metadata import read
        options=read(self.root/'bin/dots-config-browse')['option']
        self.assertTrue(any('--profile' in str(option) for option in options))
        with patch.object(menu,'browse',return_value=0) as browser, patch('interaction.terminal',return_value=True), patch.dict(os.environ,TERM='xterm'):
            config_cli.main([]);browser.assert_called_once()
        with patch.object(menu,'browse',side_effect=AssertionError('unexpected browser')), patch('interaction.terminal',return_value=False),redirect_stdout(io.StringIO()):
            config_cli.main([])

    def test_safe_file_handoff_and_missing_tools(self):
        doc=json.loads(self.path.read_text());doc['files']={'dots':[self.resource]};self.path.write_text(json.dumps(doc))
        inventory=self.inventory();row=inventory.find('files.dots:app')
        with patch.object(menu,'run_action',return_value=0) as run:
            menu.file_action(self.root,self.platform,row,'mapping',None)
            self.assertEqual(run.call_args.args[0][-3:],['files','edit','dots:app'])
            self.assertEqual(run.call_args.kwargs['kind'],'terminal')
            self.assertNotIn('--yes',run.call_args.args[0]);self.assertNotIn('--apply',run.call_args.args[0])
            menu.file_action(self.root,self.platform,row,'rename',None,'new-id')
            self.assertEqual(run.call_args.args[0][-5:],['files','edit','dots:app','--id','new-id'])
            self.assertEqual(run.call_args.kwargs['kind'],'terminal')
            self.assertNotIn('--yes',run.call_args.args[0]);self.assertNotIn('--apply',run.call_args.args[0])
            with self.assertRaises(ValueError):menu.file_action(self.root,'defaults',row,'mapping',None)
        with patch.object(menu.TmuxContext,'from_environment',return_value=None),patch.object(menu,'terminal',return_value=True), \
             patch.object(menu,'browser_available',return_value=False),redirect_stdout(io.StringIO()) as output,redirect_stderr(io.StringIO()) as error:
            self.assertEqual(menu.browse(self.root,inventory.selected,self.args()),0)
            self.assertIn('Dots config',output.getvalue());self.assertIn('listing',error.getvalue())

    def test_query_focus_scopes_and_cancel(self):
        seen=[]
        def pick(inventory,category,frame,context):
            seen.append((inventory.scope,category,dict(frame)))
            if len(seen)==1:
                frame.update(query='git.branch',selected='icons.git.branch');raise SelectionEvent('scope')
            if len(seen)==2:raise SelectionEvent('scope')
            raise SelectionEvent('back')
        with patch.object(menu.TmuxContext,'from_environment',return_value=None),patch.object(menu,'terminal',return_value=True), \
             patch.object(menu,'browser_available',return_value=True),patch.object(menu,'pick',side_effect=pick), \
             patch.object(menu,'select',side_effect=['list','defaults',self.platform,None]):
            self.assertEqual(menu.browse(self.root,self.inventory().selected,self.args()),0)
        self.assertEqual(seen[2][2]['query'],'git.branch')
        self.assertEqual(seen[2][2]['selected'],'icons.git.branch')
        with patch.object(menu.TmuxContext,'from_environment',return_value=None),patch.object(menu,'terminal',return_value=True), \
             patch.object(menu,'browser_available',return_value=True),patch.object(menu,'pick',side_effect=SelectionEnded(130)), \
             patch.object(menu,'select',return_value='list'):
            self.assertEqual(menu.browse(self.root,self.inventory().selected,self.args()),130)

    def test_list_get_and_set_actions_and_categories(self):
        row=self.inventory().find('icons.git.branch')
        for mode in ('list','get','set'):
            choices=[mode]+([] if mode=='list' else ['icons'])+[None]+([] if mode=='list' else [None])
            with patch.object(menu,'terminal',return_value=True),patch.object(menu,'browser_available',return_value=True), \
                 patch.object(menu,'select',side_effect=choices) as select, \
                 patch.object(menu,'pick',side_effect=[row,SelectionEvent('back')]), \
                 patch.object(menu,'show') as show,patch.object(menu,'actions',return_value='Saved') as actions:
                self.assertEqual(menu.browse(self.root,self.inventory().selected,self.args()),0)
            self.assertEqual(actions.call_count,int(mode=='set'))
            self.assertEqual(show.call_count,int(mode!='set'))
            self.assertEqual([key for key,_ in select.call_args_list[0].args[1]],['list','get','set','refresh'])
            if mode!='list':
                self.assertEqual([key for key,_ in select.call_args_list[1].args[1]],
                                 ['all','icons','colors','formatting','apps','files','profile','settings','environment'])

    def test_guided_empty_calls_and_incomplete_data_errors(self):
        for action in ('get','set'):
            with patch.object(menu,'browse',return_value=0) as browser,patch('interaction.terminal',return_value=True),patch.dict(os.environ,TERM='xterm'):
                self.assertEqual(config_cli.main([action]),0)
                self.assertEqual(browser.call_args.args[2].action,action)
            with patch.object(menu,'browse',side_effect=AssertionError('data must not browse')),redirect_stderr(io.StringIO()):
                for operands in ([action,'--json'],[action,'--dry-run']):
                    with self.assertRaises(SystemExit): config_cli.main(operands)
                with self.assertRaises(SystemExit): config_cli.main(['set','DOTS_COLOR'])

    def test_key_only_set_goes_directly_to_the_typed_editor(self):
        shutil.copytree(ROOT/'config/wttr',self.root/'config/wttr')
        keys = [('DOTS_COLOR','settings.DOTS_COLOR','style'),
                ('colors.todo.field.acceptance.value.fg','colors.todo.field.acceptance.value.fg','color'),
                ('icons.git.branch','icons.git.branch','text'),
                ('formatting.apps.cli.label_width','formatting.apps.cli.label_width','json'),
                ('apps.wttr.days','apps.wttr.days','native'),
                ('environment.NEW_LABEL','environment.NEW_LABEL','text')]
        with patch('interaction.terminal',return_value=True),patch.object(menu,'terminal',return_value=True), \
             patch.dict(os.environ,TERM='xterm'),patch.object(menu,'browser_available',return_value=True), \
             patch.object(menu,'select',side_effect=AssertionError('no navigation before the editor')), \
             patch.object(menu,'edit',return_value='') as edit:
            for key,canonical,kind in keys:
                self.assertEqual(config_cli.main(['set',key]),0)
                self.assertEqual(edit.call_args.args[1].key,canonical)
                self.assertEqual(edit.call_args.args[1].kind,kind)
            for scope in ('defaults','windows'):
                self.assertEqual(config_cli.main(['set','icons.git.branch','--defaults'] if scope=='defaults' else
                                                ['set','icons.git.branch','--profile',scope]),0)
                self.assertEqual(edit.call_args.args[0].scope,scope)
            edit.side_effect=SelectionEnded(130)
            self.assertEqual(config_cli.main(['set','DOTS_COLOR']),130)

    def test_key_editor_theme_colors_save_only_cancel_and_stale_guard(self):
        theme=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme';theme.mkdir(parents=True)
        (theme/'palette.json').write_text(json.dumps(dict(colors={'accent':'#123456','blue':'#112233','same_hex':'#abcdef','invalid':'not a color'},
                                                        palette={'fixture_extra':'#abcdef','blue':'#aaaabb','rosewater':'#f5e0dc'})))
        current.cache_clear()
        key='colors.todo.field.acceptance.value.fg'
        destination=self.path.parent/'colors.toml'
        seen=[]
        def choose(title,items,context=None,review=None):
            seen.append((title,items,review))
            if title=='Color':return next(token for token,label in items if label.startswith('fixture_extra ·'))
            self.assertEqual(title,'Review change');self.assertEqual(items[0][0],'cancel')
            self.assertIn('automatic refresh disabled',review)
            return 'save'
        with patch('interaction.terminal',return_value=True),patch.object(menu,'terminal',return_value=True), \
             patch.dict(os.environ,TERM='xterm'),patch.object(menu,'browser_available',return_value=True), \
             patch.object(menu,'select',side_effect=choose),patch('config_refresh.after_save',side_effect=AssertionError('no refresh')), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(config_cli.main(['set',key,'--no-refresh']),0)
        self.assertIn('undo: dots files undo',output.getvalue())
        from style_config import read
        self.assertEqual(read(destination)['todo.field.acceptance.value.fg'],'#abcdef')
        labels=dict(seen[0][1]);self.assertIn('accent · #123456',labels.values())
        self.assertIn('same_hex · #abcdef',labels.values());self.assertNotIn('invalid',labels.values())
        self.assertIn('rosewater · #f5e0dc',labels.values());self.assertIn('blue (native) · #aaaabb',labels.values())
        self.assertIn('blue · #112233',labels.values())
        self.assertIn('custom',labels);self.assertEqual(len(labels),len(seen[0][1]))
        self.undo(output.getvalue().split('undo: dots files undo ')[1].split()[0])
        self.assertFalse(destination.exists())
        inventory=self.inventory();row=inventory.find(key)
        with patch.object(menu,'select',return_value=None):self.assertEqual(menu.edit(inventory,row,None),'')
        with patch.object(menu,'select',side_effect=['blue','cancel']):self.assertEqual(menu.edit(inventory,row,None),'')
        self.assertFalse(destination.exists())
        def drift(*args):
            self.path.write_text(self.path.read_text()+'\n')
            return 'save'
        with patch.object(menu,'input_value',return_value='blue'),patch.object(menu,'select',side_effect=drift):
            with self.assertRaises(ValueError):menu.edit(inventory,row,None)
        self.assertFalse(destination.exists())

    def test_key_editor_data_unknown_keys_and_missing_tools_are_inert(self):
        key='colors.todo.field.acceptance.value.fg'
        with patch.object(menu,'browse',side_effect=AssertionError('data must not browse')), \
             patch('interaction.terminal',return_value=True),patch.dict(os.environ,TERM='xterm'),redirect_stderr(io.StringIO()):
            for flag in ('--json','--dry-run','--json-value','--yes','--apply'):
                with self.assertRaises(SystemExit):config_cli.main(['set',key,flag])
        for native in (False,True):
            result=self.run_config('set',key,native=native,code=2)
            self.assertEqual(result.stdout,'')
        with patch('interaction.terminal',return_value=True),patch.object(menu,'terminal',return_value=True), \
             patch.dict(os.environ,TERM='xterm'),patch.object(menu,'edit',side_effect=AssertionError('must not edit')):
            with patch.object(menu,'browser_available',return_value=False):
                with self.assertRaisesRegex(ValueError,'supply an explicit value'):config_cli.main(['set',key])
            with patch.object(menu,'browser_available',return_value=True):
                with self.assertRaisesRegex(ValueError,'unknown or noneditable'):config_cli.main(['set','colors.no_such_key.fg'])
        self.assertFalse((self.path.parent/'colors.toml').exists())

    def test_private_preview_numeric_identity_and_widths(self):
        from resources import cells
        inventory=self.inventory()
        row=menu.Row('environment.LONG_VALUE','界 café '+('long '*100),str(self.path),str(self.path))
        for width in (40,80,120):
            text=menu.details(row,width=width)
            self.assertTrue(all(cells(line)<=width for line in text.splitlines()))
        with request_file(dict(schema=1,previews=['first','second'])) as path:
            with redirect_stdout(io.StringIO()) as output:menu.preview(str(path),'0')
            self.assertEqual(output.getvalue(),'first')
            with self.assertRaises(ValueError):menu.preview(str(path),'0;touch bad')
        self.assertFalse(path.exists())
        frame={'query':'branch','selected':'icons.git.branch'}
        def select(*args,**kwargs):
            self.assertEqual(kwargs['query'],'branch')
            self.assertIsNotNone(kwargs['focus_index'])
            path=Path(args[3][2]['DOTS_CONFIG_PREVIEW'])
            self.assertEqual(read_request(path)['rows'][kwargs['focus_index']]['key'],'icons.git.branch')
            with redirect_stdout(io.StringIO()) as output:menu.preview(str(path),str(kwargs['focus_index']))
            self.assertIn('Saved',output.getvalue())
            return [kwargs['focus_index']]
        with patch.object(menu.RichSelector,'fzf',side_effect=select):
            self.assertEqual(menu.pick(inventory,'icons',frame,None).key,'icons.git.branch')

    def test_shared_input_escape_interrupt_and_todo_compatibility(self):
        import todo_input
        self.assertIs(todo_input.prompt,menu_input.prompt)
        with patch.object(menu_input,'terminal',return_value=True),patch.object(menu_input.shutil,'which',return_value='gum'),patch.dict(os.environ,TERM='xterm'):
            for code,exception in ((1,SelectionEvent),(130,SelectionEnded)):
                with patch.object(menu_input.subprocess,'run',return_value=subprocess.CompletedProcess([],code,stdout='')),self.assertRaises(exception):
                    menu_input.input_text('','Value',back=True)
            with patch.object(menu_input.subprocess,'run',return_value=subprocess.CompletedProcess([],1,stdout='')),self.assertRaises(ValueError):
                menu_input.input_text('','Todo legacy')
        with patch.object(menu_input,'terminal',return_value=True),patch.object(menu_input.shutil,'which',return_value=None), \
             patch('builtins.input',return_value='/cancel'),redirect_stdout(io.StringIO()),self.assertRaises(SelectionEvent):
            menu_input.input_text('','Value',back=True)


class NativeConfig(NativeMenuFixture):
    def setUp(self):
        super().setUp()
        self.root=Path(self.env['DOTS']);self.root.mkdir()
        (self.root/'.dots').mkdir();(self.root/'config').mkdir()
        (self.root/'.dots/sources.json').write_text(json.dumps(dict(schema=1,sources=[dict(id='dots',path='.',roots=['config'],platforms=['termux','linux','wsl','windows'])])))
        (self.root/'.dots/files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[])))
        for name in ('termux','linux','wsl','windows'):
            path=self.root/'profiles'/name;path.mkdir(parents=True)
            (path/'profile.json').write_text(json.dumps(dict(schema=1,id=name,environment={'TEST_LABEL':'界 café value'},settings={})))
        (self.root/'default').mkdir()
        for name in ('icons','colors'):shutil.copy2(ROOT/'default'/(name+'.toml'),self.root/'default'/(name+'.toml'))
        self.platform=menu.profile_context(self.root)['layers'][-1]['id']

    def review_screen(self,columns,lines):
        """Replay a full client redraw in an owned tmux terminal for cell capture."""
        import time
        self.drain(self.first[1]);self.control('refresh-client','-t',self.first[2])
        redraw=self.receive(self.first[1],b'Cancel')+self.drain(self.first[1])
        capture=self.home/'review-capture';capture.write_bytes(redraw)
        replay='import os,sys;from pathlib import Path;os.write(1,Path(sys.argv[1]).read_bytes());sys.stdin.buffer.read()'
        pane=self.control('new-session','-d','-P','-F','#{pane_id}','-s','review-replay','-x',str(columns),'-y',str(lines),
                          sys.executable,'-B','-c',replay,str(capture)).strip()
        try:
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                screen=self.control('capture-pane','-p','-t',pane)
                if screen.strip():return screen
                time.sleep(.05)
            self.fail('review redraw did not reach the replay terminal')
        finally:self.control('kill-session','-t','review-replay')

    def test_review_choices_visible_together_after_popup_sizing(self):
        import time
        defaults=self.root/'default/config.json';shutil.copy2(ROOT/'default/config.json',defaults)
        code="""import os
from config_menu import select
from menu_tmux import TmuxContext
print(select('Review change',[('cancel','Cancel'),('save','Save')],TmuxContext.capture(client=os.environ['CLIENT']),'REVIEW_BODY\\n'*60))
"""
        cases=((40,30,'auto','auto'),(80,24,'fit','50%'),(120,30,'90%',14),(40,14,'auto','fit'),(80,20,'auto',6))
        for number,(columns,lines,width,height) in enumerate(cases):
            with self.subTest(columns=columns,lines=lines,height=height):
                doc=json.loads(defaults.read_text());doc['apps']['menu']['popup'].update(width=width,height=height)
                defaults.write_text(json.dumps(doc))
                self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',lines,columns,0,0))
                time.sleep(.1);self.drain(self.first[1]);self.drain(self.second[1])
                p=self.worker(code,DOTS_COLOR='never' if number==0 else 'always',DOTS_ICONS='never')
                try:
                    initial=self.receive(self.first[1],b'Cancel')
                    if number < 3 and b'REVIEW_BODY' not in initial:self.receive(self.first[1],b'REVIEW_BODY')
                    screen=self.review_screen(columns,lines)
                    self.assertRegex(screen,r'\bCancel\b',screen)
                    self.assertRegex(screen,r'\bSave\b',screen)
                    self.assertNotIn(b'REVIEW_BODY',self.drain(self.second[1]))
                    if number==1:
                        os.write(self.first[1],b'\x1b[B');time.sleep(.1)
                    os.write(self.first[1],b'\r')
                    out,err=p.communicate(timeout=10)
                    self.assertEqual(p.returncode,0,out+err)
                    self.assertEqual(out.strip(),'save' if number==1 else 'cancel')
                finally:
                    if p.poll() is None:
                        os.write(self.first[1],b'\x1b');p.communicate(timeout=10)

    def test_key_only_set_opens_color_picker_in_both_frontends(self):
        import shlex,time
        shutil.copytree(ROOT/'lib/dots',self.root/'lib/dots',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (self.root/'bin').mkdir()
        for source in [ROOT/'bin/dots',*ROOT.glob('bin/dots-config*')]:shutil.copy2(source,self.root/'bin'/source.name)
        theme=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme';theme.mkdir(parents=True)
        runner=self.home/'edit-key.py'
        runner.write_text('''import os,subprocess,sys
from dataclasses import asdict
from pathlib import Path
from menu_tmux import TmuxContext,request_file
root=Path(os.environ['DOTS'])
os.environ['DOTS_COLOR']='never' if sys.argv[3]=='40' else 'always'
os.environ['DOTS_ICONS']='never'
cmd=[sys.executable,'-B',str(root/'lib/dots/cli.py')] if sys.argv[1]=='native' else [str(root/'bin/dots')]
context=TmuxContext.capture(client=sys.argv[4])
with request_file(dict(schema=1,context=asdict(context))) as path:
    code=subprocess.call([*cmd,'config','set','colors.todo.field.acceptance.value.fg','--no-refresh'],env=dict(os.environ,DOTS_MENU_CONTEXT=str(path)))
Path(sys.argv[2]).write_text(str(code))
''')
        destination=self.root/'profiles'/self.platform/'colors.toml'
        for width,frontend in ((40,'bash'),(80,'native'),(120,'bash')):
            (theme/'palette.json').write_text(json.dumps(dict(palette={'fixture_extra':'#abcdef'},colors={'accent':'#123456',
                'foreground':'#202020' if width==120 else '#cdd6f4','background':'#fafafa' if width==120 else '#181825'})))
            before=destination.read_bytes() if destination.exists() else None
            status=self.home/('key-status-'+str(width))
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,width,0,0))
            time.sleep(.1);self.drain(self.first[1]);self.drain(self.second[1])
            self.control('send-keys','-t',self.pane,'-l',shlex.join([sys.executable,'-B',str(runner),frontend,str(status),str(width),self.first[2]]))
            self.control('send-keys','-t',self.pane,'Enter')
            self.receive(self.first[1],b'fixture_extra')
            self.assertNotIn(b'fixture_extra',self.drain(self.second[1]))
            if width==120:os.write(self.first[1],b'\x03')
            else:
                os.write(self.first[1],b'fixture_extra');time.sleep(.15);os.write(self.first[1],b'\r')
                self.receive(self.first[1],b'Proposed')
                if width==80:os.write(self.first[1],b'Save');time.sleep(.15)
                os.write(self.first[1],b'\r')
            deadline=time.monotonic()+10
            while not status.exists() and time.monotonic()<deadline:
                self.drain(self.first[1]);time.sleep(.02)
            self.assertTrue(status.exists());self.assertEqual(status.read_text(),'130' if width==120 else '0')
            if width==80:
                from style_config import read
                self.assertEqual(read(destination)['todo.field.acceptance.value.fg'],'#abcdef')
            else:self.assertEqual(destination.read_bytes() if destination.exists() else None,before)

    def test_standalone_terminal_and_shared_input_handoff(self):
        import select, signal, time
        pid, master=self.pty.fork()
        if pid == 0:
            os.chdir(self.home)
            os.execve(sys.executable,[sys.executable,'-B','-c','import config_cli;raise SystemExit(config_cli.main([]))'],self.env)
        self.fcntl.ioctl(master,self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,80,0,0))
        status=None;data=bytearray();sent=False;deadline=time.monotonic()+12
        try:
            while time.monotonic()<deadline:
                if select.select([master],[],[],.05)[0]:
                    try:chunk=os.read(master,65536)
                    except OSError:chunk=b''
                    data.extend(chunk)
                    if b'\x1b[6n' in chunk:os.write(master,b'\x1b[1;1R')
                    if not sent and b'config' in data:
                        time.sleep(.15);os.write(master,b'\x1b');sent=True
                ended,code=os.waitpid(pid,os.WNOHANG)
                if ended:status=code;break
            self.assertIsNotNone(status,bytes(data[-2000:]))
            self.assertEqual(os.waitstatus_to_exitcode(status),0,bytes(data[-2000:]))
        finally:
            os.close(master)
            if status is None:
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
                os.waitpid(pid,0)
        if not shutil.which('gum'):return
        for key,expected in ((b'\x1b',0),(b'\x03',130)):
            p=self.worker("""import os
from menu_input import prompt
from menu_tmux import TmuxContext
from interaction import SelectionEvent,SelectionEnded
try:prompt('literal','Input fixture',TmuxContext.capture(client=os.environ['CLIENT']),back=True)
except SelectionEvent:raise SystemExit(0)
except SelectionEnded as e:raise SystemExit(e.status)
""")
            self.receive(self.first[1],b'fixture');os.write(self.first[1],key)
            out,err=p.communicate(timeout=10);self.assertEqual(p.returncode,expected,out+err)

    def test_widths_exact_client_preview_cleanup_and_empty_back(self):
        import time
        code="""import os
import config_cli
raise SystemExit(config_cli.main(['browse','--client',os.environ['CLIENT'],'--query',os.environ['QUERY']]))
"""
        for width in (40,80,120):
            theme=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme';theme.mkdir(parents=True,exist_ok=True)
            bg,fg=('#fafafa','#202020') if width==120 else ('#181825','#cdd6f4')
            (theme/'palette.json').write_text(json.dumps(dict(colors=dict(background=bg,foreground=fg,blue='#0088cc',cyan='#00aaaa'))))
            (theme/'fzf.sh').write_text('export _FZF_COLORS_="fg:'+fg+',bg:'+bg+',header:#0088cc"\n')
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,width,0,0))
            time.sleep(.1);self.drain(self.first[1]);self.drain(self.second[1])
            before=set(self.base.iterdir())
            p=self.worker(code,QUERY='environment.TEST_LABEL',DOTS_COLOR='never' if width==40 else 'always',
                          DOTS_ICONS='always' if width==80 else 'never')
            self.receive(self.first[1],b'List');time.sleep(.1);os.write(self.first[1],b'\r')
            try:self.receive(self.first[1],b'TEST_LABEL')
            except AssertionError:
                if p.poll() is not None:
                    out,err=p.communicate();self.fail(out+err)
                raise
            self.assertNotIn(b'config',self.drain(self.second[1]))
            # Empty-result Escape is still a navigation event.
            os.write(self.first[1],b'\x15no-match-unique')
            time.sleep(.1);os.write(self.first[1],b'\x1b')
            self.receive(self.first[1],b'List');time.sleep(.1);os.write(self.first[1],b'\x1b')
            out,err=p.communicate(timeout=10)
            self.assertEqual(p.returncode,0,out+err)
            self.assertFalse([path for path in set(self.base.iterdir())-before if path.is_dir() and path.name.startswith('dots-menu')])

    def test_native_save_and_default_cancel(self):
        import time
        code="""import os
import config_cli
raise SystemExit(config_cli.main(['browse','--client',os.environ['CLIENT'],'--query','settings.DOTS_COLOR']))
"""
        p=self.worker(code)
        self.receive(self.first[1],b'List');time.sleep(.1);os.write(self.first[1],b'Set');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Icons');time.sleep(.1);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'settings.DOTS_COLOR')
        time.sleep(.15);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Edit value')
        os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'always')
        os.write(self.first[1],b'never');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Proposed')
        os.write(self.first[1],b'\r')  # The initial review choice is Cancel.
        self.receive(self.first[1],b'DOTS_COLOR')
        path=self.root/'profiles'/self.platform/'profile.json'
        self.assertEqual(json.loads(path.read_text())['settings'],{})
        os.write(self.first[1],b'\r');self.receive(self.first[1],b'Edit value')
        os.write(self.first[1],b'\r');self.receive(self.first[1],b'always')
        os.write(self.first[1],b'never');time.sleep(.2);os.write(self.first[1],b'\r');self.receive(self.first[1],b'Proposed')
        os.write(self.first[1],b'\x1b[B\r')
        self.receive(self.first[1],b'undo')
        self.assertEqual(json.loads(path.read_text())['settings']['DOTS_COLOR'],'never')
        os.write(self.first[1],b'\x03')
        out,err=p.communicate(timeout=10);self.assertEqual(p.returncode,130,out+err)


if __name__ == '__main__': unittest.main()
