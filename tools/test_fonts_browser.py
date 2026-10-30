#!/usr/bin/env python3
"""Real font selectors in private tmux clients, without font or clipboard changes."""
import os
from pathlib import Path
import sys
import time
import unittest

from test_menus import NativeMenuFixture, ROOT


class FontBrowsers(NativeMenuFixture):
    def setUp(self):
        super().setUp()
        self.env['DOTS']=str(ROOT)

    def icons(self,copy=False):
        return self.worker('''import os,sys
from types import SimpleNamespace
from fonts.browser import icons
from fonts.commands import parser
from menu_tmux import TmuxContext
from unittest.mock import patch
row=dict(name='test-fixture',collection='test',glyph='\ue000',codepoint='U+E000')
library=SimpleNamespace(families={},catalog=dict(glyph_version='v1.0.0',glyphs={'v1.0.0':[row]}))
context=TmuxContext.capture(client=os.environ['CLIENT'])
with patch('fonts.browser.copy',side_effect=lambda glyph:print('copied:'+glyph)):
    sys.exit(icons(library,parser().parse_args(['icons']),context=context))
''')

    def test_font_popup_at_40_80_120_columns_pins_client_and_goes_back(self):
        for width in (40,80,120):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',24,width,0,0))
            time.sleep(.15)
            self.drain(self.first[1]);self.drain(self.second[1])
            p=self.worker('''import os
from fonts.browser import picker
from menu_tmux import TmuxContext
from interaction import SelectionEvent
context=TmuxContext.capture(client=os.environ['CLIENT'])
try:picker([dict(id='nerd:Fixture',name='Fixture Mono')],[dict(text='Fixture font metadata')],{},context)
except SelectionEvent as event:print('event:'+event.action)
''')
            self.receive(self.first[1],b'Fixture')
            time.sleep(.15)
            self.assertNotIn(b'Fixture',self.drain(self.second[1]))
            os.write(self.first[1],b'\x1b')
            deadline=time.monotonic()+15
            while p.poll() is None and time.monotonic()<deadline:self.drain(self.first[1])
            out,err=p.communicate(timeout=15)
            self.assertEqual((p.returncode,out.strip()),(0,'event:back'),err)

    def test_icon_alt_p_prints_exact_glyph_and_closes(self):
        p=self.icons();self.receive(self.first[1],b'test-fixture')
        os.write(self.first[1],b'\x1bp')
        out,err=p.communicate(timeout=15)
        self.assertEqual((p.returncode,out),(0,'\ue000'),err)

    def test_font_alt_d_requests_directory_chooser_in_origin_client(self):
        p=self.worker('''import os
from fonts.browser import picker
from menu_tmux import TmuxContext
from interaction import SelectionEvent
context=TmuxContext.capture(client=os.environ['CLIENT'])
try:picker([dict(id='nerd:Fixture',name='Fixture Mono')],[dict(text='Stored v1')],dict(notice='Directory: DOTFONTS'),context)
except SelectionEvent as event:print('event:'+event.action)
''')
        self.receive(self.first[1],b'Fixture');os.write(self.first[1],b'\x1bd')
        out,err=p.communicate(timeout=15)
        self.assertEqual((p.returncode,out.strip()),(0,'event:directory'),err)
        self.assertNotIn(b'Fixture',self.drain(self.second[1]))

    def test_main_font_actions_at_40_80_120_columns_cancel_without_handoff(self):
        for width in (40,80,120):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',24,width,0,0))
            time.sleep(.15);self.drain(self.first[1]);self.drain(self.second[1])
            p=self.worker('''import os
from fonts.menus import home
from fonts.commands import parser
from menu_tmux import TmuxContext
from unittest.mock import patch
context=TmuxContext.capture(client=os.environ['CLIENT'])
with patch('fonts.menus.context_for',return_value=context),patch('fonts.menus.invoke',side_effect=AssertionError('unexpected mutation')):
    print('result:'+str(home(parser().parse_args([]))))
''')
            self.receive(self.first[1],b'Installed fonts');time.sleep(.15)
            self.assertNotIn(b'Installed fonts',self.drain(self.second[1]));os.write(self.first[1],b'\x1b')
            deadline=time.monotonic()+15
            while p.poll() is None and time.monotonic()<deadline:self.drain(self.first[1])
            out,err=p.communicate(timeout=15)
            self.assertEqual((p.returncode,out.strip()),(0,'result:0'),err)

    def test_icon_enter_and_alt_y_copy_and_close(self):
        for key in (b'\r',b'\x1by'):
            p=self.icons();self.receive(self.first[1],b'test-fixture');os.write(self.first[1],key)
            out,err=p.communicate(timeout=15)
            self.assertEqual((p.returncode,out),(0,'copied:\ue000\n'),err)

    def test_icon_inserts_into_origin_without_enter(self):
        p=self.icons();self.receive(self.first[1],b'test-fixture');os.write(self.first[1],b'\x1bi')
        out,err=p.communicate(timeout=15)
        self.assertEqual((p.returncode,out),(0,''),err)
        time.sleep(.15)
        text=self.control('capture-pane','-p','-t',self.pane)
        self.assertIn('\ue000',text);self.assertNotIn('command not found',text)
        self.control('send-keys','-t',self.pane,'C-u')


if __name__=='__main__':unittest.main(verbosity=2)
