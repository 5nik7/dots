#!/usr/bin/env python3
"""Clipboard controls and private terminal checks; never use the live clipboard."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from test_menus import NativeMenuFixture, ROOT
import test_profile_config as fixtures


class Configuration(unittest.TestCase):
    run_config=fixtures.ProfileConfig.run_config

    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(ROOT/'default',self.root/'default')
        self.environment=patch.dict(os.environ,self.env,clear=True)
        self.environment.start();self.addCleanup(self.environment.stop)
        from config_values import current
        current.cache_clear();self.addCleanup(current.cache_clear)
        from style_config import current
        current.cache_clear();self.addCleanup(current.cache_clear)

    def test_capture_controls_inheritance_reset_and_activation(self):
        from clipboard_history import preferences
        from config_values import validate_value
        from config_refresh import effective, after_save
        from config_menu import Inventory, Draft
        self.assertFalse(preferences()['record_copies'])
        self.run_config('set','apps.clipboard.max_entries','12','--defaults','--no-refresh')
        self.run_config('set','apps.clipboard.max_entries','3','--no-refresh')
        self.assertEqual(preferences()['max_entries'],3)
        self.run_config('unset','apps.clipboard.max_entries','--no-refresh')
        self.assertEqual(preferences()['max_entries'],12)
        for key,value in [('max_entries','0'),('max_entry_bytes','0'),('poll_seconds','11'),('record_copies','yes')]:
            self.run_config('set','apps.clipboard.'+key,value,'--no-refresh',code=1)
        row=Inventory(self.root,self.platform).find('apps.clipboard.record_copies')
        before=effective(self.root)
        draft=Draft(Inventory(self.root,self.platform),row).prepare('true');draft.plan.apply('set')
        with patch('config_refresh.refresh',side_effect=AssertionError('must not publish')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='clipboard',status='next invocation or watcher poll')])
        self.assertTrue(preferences()['record_copies'])
        self.assertFalse((self.home/'state/dots/clipboard').exists())

    def test_semantic_colors_icons_nullable_styles_and_human_output(self):
        from clipboard_cli import ClipboardPresentation
        from style_config import current
        from config_refresh import effective, after_save
        before=effective(self.root)
        self.run_config('set','colors.apps.clipboard.heading.fg','#123456','--no-refresh')
        self.run_config('set','colors.apps.clipboard.heading.bg','#654321','--no-refresh')
        self.run_config('set','icons.menu.clipboard','CLIP','--no-refresh')
        with patch('config_refresh.refresh',side_effect=AssertionError('must not publish')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='clipboard',status='next invocation or popup')])
        current.cache_clear()
        with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='always'):
            stream=io.StringIO();ui=ClipboardPresentation(stream,terminal=True);ui.heading('Stored text')
            output=stream.getvalue()
            self.assertIn('38;2;18;52;86',output);self.assertIn('48;2;101;67;33',output);self.assertIn('CLIP',output)
            for width in (40,80,120):
                ui.width=width;ui.detail('Text','x\x1b[31m\n雪 '+('long '*30))
            self.assertNotIn('\x1b[31m',stream.getvalue())
        self.run_config('set','colors.apps.clipboard.heading.bg','null','--json-value','--no-refresh')
        self.assertEqual(self.run_config('get','colors.apps.clipboard.heading.bg').stdout,'null\n')


class Popup(NativeMenuFixture):
    def setUp(self):
        super().setUp()
        repo=Path(self.env['DOTS']);repo.mkdir()
        shutil.copytree(ROOT/'default',repo/'default')
        for name in ('termux','linux','wsl','windows'):
            path=repo/'profiles'/name;path.mkdir(parents=True)
            (path/'profile.json').write_text(json.dumps(dict(schema=1,id=name)))
        from clipboard_history import History
        self.history=History();self.row=self.history.add('fixture 雪\nsecond line\n')

    def test_popup_widths_short_height_actions_and_client_ownership(self):
        code='''import os,json
from clipboard_history import History
from clipboard_menu import picker
from menu_tmux import TmuxContext
h=History();frame={}
a,r=picker(h.rows(),h.settings,frame,TmuxContext.capture(client=os.environ['CLIENT']))
print(json.dumps(dict(action=a,id=r['id'] if r else None,query=frame.get('query'))))
'''
        for width,height,key,action in [(40,30,b'\x1bp','print'),(80,30,b'\x1bs','pin'),(120,30,b'\r','copy'),(40,10,b'\x1b','back')]:
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',height,width,0,0))
            time.sleep(.1);self.drain(self.first[1]);self.drain(self.second[1])
            p=self.worker(code)
            self.receive(self.first[1],b'clipboard')
            self.assertNotIn(b'clipboard',self.drain(self.second[1]))
            if action!='back':os.write(self.first[1],b'fixture');time.sleep(.2)
            os.write(self.first[1],key)
            out,err=p.communicate(timeout=15)
            self.assertEqual(p.returncode,0,err)
            result=json.loads(out);self.assertEqual(result['action'],action)
            if action!='back':self.assertEqual(result['id'],self.row['id']);self.assertEqual(result['query'],'fixture')
            self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_browser_refresh_remove_review_and_selection_handoff(self):
        import argparse
        import clipboard_menu
        from menus import Entry
        args=argparse.Namespace(action='pick',json=True)
        frames=[]
        def action(rows,settings,frame,context,selecting):
            frames.append(frame)
            if len(frames)==1:
                frame['query']='fixture';frame['selected']=rows[0]['id']
                return 'pin',rows[0]
            self.assertEqual(frame['query'],'fixture')
            self.assertEqual(frame['selected'],rows[0]['id'])
            return 'insert',rows[0]
        output=io.StringIO()
        with patch('clipboard_menu.rich_fzf_available',return_value=True), patch('sys.stderr.isatty',return_value=True), patch('clipboard_menu.context_for',return_value=None), patch('clipboard_menu.picker',side_effect=action), patch('sys.stdout',output):
            self.assertEqual(clipboard_menu.browse(self.history,args,selecting=True),0)
        self.assertTrue(self.history.get(self.row['id'])['pinned'])
        self.assertEqual(json.loads(output.getvalue())['text'],self.row['text'])
        # A deletion reviewed before a concurrent update must be refused.
        def choice(*a,**kw):
            self.history.add(self.row['text'])
            return Entry('remove','Remove')
        calls=[]
        def remove(rows,settings,frame,context,selecting):
            calls.append(frame.copy())
            return ('remove',rows[0]) if len(calls)==1 else ('back',None)
        with patch('clipboard_menu.rich_fzf_available',return_value=True), patch('sys.stderr.isatty',return_value=True), patch('clipboard_menu.context_for',return_value=None), patch('clipboard_menu.picker',side_effect=remove), patch('menus.choose',side_effect=choice):
            clipboard_menu.browse(self.history,args)
        self.assertIn('changed',calls[-1]['notice'])
        self.assertEqual(len(self.history.rows()),1)

    def test_multiline_insertion_stays_in_verified_editor_buffer(self):
        from clipboard_menu import insert
        from menu_tmux import TmuxContext
        # This is a private idle Bash prompt; no keystrokes target a user pane.
        self.control('send-keys','-t',self.pane,"bind 'set enable-bracketed-paste on'",'Enter')
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if self.control('display-message','-p','-t',self.pane,'#{bracket_paste_flag}').strip()=='1':break
            time.sleep(.1)
        context=TmuxContext.capture(client=self.first[2])
        target=self.base/'never-executed'
        text='printf dangerous > '+str(target)+'\nprintf 雪\n'
        insert(text,context)
        time.sleep(.2)
        self.assertFalse(target.exists())
        screen=self.control('capture-pane','-p','-t',self.pane)
        self.assertIn('printf dangerous',screen)
        self.assertEqual(self.control('list-buffers'), '')
        self.control('send-keys','-t',self.pane,'C-c')
        time.sleep(.1)
        # A running foreground process does not accept insertion.
        self.control('send-keys','-t',self.pane,'sleep 5','Enter');time.sleep(.2)
        with self.assertRaises(ValueError):insert('never',context)
        self.control('send-keys','-t',self.pane,'C-c')


if __name__=='__main__':unittest.main()
