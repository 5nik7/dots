#!/usr/bin/env python3
"""Real todo FZF previews/events on private tmux servers and owned roots."""
import os
import json
import shutil
from pathlib import Path
import time
import unittest

from test_menus import NativeMenuFixture


class TodoPopup(NativeMenuFixture):
    def prepare(self):
        from todo_core import Goals, scope
        Path(self.env['DOTS']).mkdir()
        return Goals(scope()).mutate('add', title='Phone layouts ü', alias='phone-layouts', priority='high', notes='Preview evidence',
                                     acceptance=['Readable narrow popup'])['goals'][0]

    def test_real_previews_widths_and_exact_client(self):
        goal = self.prepare()
        code = '''import os
from todo_core import Goals,scope
from todo_menu import pick
from menu_tmux import TmuxContext
c=TmuxContext.capture(client=os.environ['CLIENT'])
s=Goals(scope())
g=pick(s,s.goals,{},c)
print('selected:'+g['id'])
'''
        for width, height in ((40, 14), (80, 24), (120, 30)):
            self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', height, width, 0, 0))
            time.sleep(.2)
            self.drain(self.first[1]); self.drain(self.second[1])
            worker = self.worker(code)
            capture = self.receive(self.first[1], b'Subgoals')
            self.assertIn(b'todo', capture)
            self.assertNotIn(b'Subgoals', self.drain(self.second[1]))
            os.write(self.first[1], b'\r')
            out, err = worker.communicate(timeout=15)
            self.assertEqual(worker.returncode, 0, err)
            self.assertEqual(out.strip(), 'selected:' + goal['id'])
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_empty_search_new_event_and_cancel_do_not_write(self):
        Path(self.env['DOTS']).mkdir()
        code = '''import os
from todo_core import Goals,scope
from todo_menu import pick
from menu_tmux import TmuxContext
from interaction import SelectionEvent
c=TmuxContext.capture(client=os.environ['CLIENT'])
try: pick(Goals(scope()),[],{},c)
except SelectionEvent as event: print('event:'+event.action+':'+str(event.index))
'''
        worker = self.worker(code)
        self.receive(self.first[1], b'Alt-N')
        os.write(self.first[1], b'no-match');time.sleep(.2);os.write(self.first[1], b'\x1bn')
        out, err = worker.communicate(timeout=15)
        self.assertEqual(worker.returncode,0,err);self.assertEqual(out.strip(),'event:new:None')
        self.assertFalse((Path(self.env['DOTS'])/'.dots').exists())

    def test_new_alias_note_and_complete_use_separate_input_popup(self):
        if not shutil.which('gum'): self.skipTest('native Gum input unavailable')
        Path(self.env['DOTS']).mkdir()
        code = '''import os,sys
from todo_core import scope
from todo_commands import parser
from todo_menu import browse
from menu_tmux import TmuxContext
from interaction import SelectionEnded
try:
 sys.exit(browse(scope(),parser().parse_args(['--client',os.environ['CLIENT']])))
except SelectionEnded as error: sys.exit(error.status)
'''
        worker = self.worker(code)
        self.receive(self.first[1], b'Alt-N')
        os.write(self.first[1], b'\x1bn')
        self.receive(self.first[1], b'title')
        os.write(self.first[1], b'Created from popup\r')
        # The preview proves the saved goal has replaced the input host.
        # Typed title text can also appear in Gum before the transaction ends.
        self.receive(self.first[1], b'Subgoals')
        path = Path(self.env['DOTS'])/'.dots/todo.json'
        self.assertTrue(path.exists())

        def wait_record(field, value):
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                try:
                    if json.loads(path.read_text())['goals'][0][field]==value: return
                except FileNotFoundError:
                    pass  # The transaction retains the previous file before replacement.
                time.sleep(.05)
            self.fail('popup did not save '+field+': '+repr(json.loads(path.read_text())['goals'][0].get(field))+
                      ' screen='+repr(self.drain(self.first[1])[-2000:]))

        os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'actions')
        os.write(self.first[1],b'edit');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'todo\xc2\xb7edit')
        os.write(self.first[1],b'alias');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Edit alias')
        os.write(self.first[1],b'popup-goal\r')
        wait_record('alias','popup-goal')
        self.assertEqual(json.loads(path.read_text())['goals'][0]['tags'],[Path(self.env['DOTS']).name])
        self.receive(self.first[1],b'Alt-N')
        os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'actions')
        os.write(self.first[1],b'edit');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'todo\xc2\xb7edit')
        os.write(self.first[1],b'tags');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Edit tags')
        os.write(self.first[1],b'\x01\x0b\x1b[200~custom-tag\x1b[201~')
        self.receive(self.first[1],b'custom-tag')
        os.write(self.first[1],b'\r')
        wait_record('tags',['custom-tag',Path(self.env['DOTS']).name])
        self.receive(self.first[1],b'Alt-N')
        os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'actions')
        os.write(self.first[1],b'add note');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Add note')
        os.write(self.first[1],b'\x1b[200~Progress from popup\nSecond line\x1b[201~')
        self.receive(self.first[1],b'Second')
        os.write(self.first[1],b'\r')  # Gum 2: Enter submits, Ctrl-J inserts a newline.
        wait_record('notes','Progress from popup\nSecond line')
        self.receive(self.first[1],b'Alt-N')
        os.write(self.first[1],b'\r')
        self.receive(self.first[1], b'actions')
        os.write(self.first[1], b'complete');time.sleep(.2);os.write(self.first[1],b'\r')
        wait_record('status','done')
        record=json.loads(path.read_text())['goals'][0]
        self.assertEqual((record['title'],record['status']),('Created from popup','done'))
        self.receive(self.first[1], b'Alt-N')
        os.write(self.first[1],b'\x03')
        _,err=worker.communicate(timeout=15)
        self.assertEqual(worker.returncode,130,err)
        self.assertFalse(list(self.base.glob('dots-menu-*')))


if __name__ == '__main__':unittest.main()
