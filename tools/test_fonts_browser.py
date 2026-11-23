#!/usr/bin/env python3
"""Real font selectors in private tmux clients, without font or clipboard changes."""
import os
import json
import shutil
import shlex
from pathlib import Path
import sys
import time
import unittest

from test_menus import NativeMenuFixture, ROOT


class FontBrowsers(NativeMenuFixture):
    def setUp(self):
        super().setUp()
        root=Path(self.env['DOTS']);root.mkdir()
        shutil.copytree(ROOT/'default',root/'default')
        for name in ('termux','linux','wsl','windows'):
            path=root/'profiles'/name;path.mkdir(parents=True)
            (path/'profile.json').write_text(json.dumps(dict(schema=1,id=name)))

    def test_configured_catalog_preview_and_styles_keep_selection_at_40_80_120(self):
        path=Path(self.env['DOTS'])/'default/config.json'
        doc=__import__('config_keys').document(json.loads(path.read_text()),public=False)
        doc['formatting']['apps']['menu'].update(indent=1,label_width='25%',label_gap=2)
        doc['apps']['menu']['popup'].update(width='90%',height='90%')
        for width,position,enabled in ((40,'down',True),(80,'right',True),(120,'down',False)):
            doc['apps']['menu']['popup'].update(width='90%' if enabled else 'fit',height='90%' if enabled else 'fit')
            doc['apps']['fonts']['preview'].update(enabled=enabled,sample=False,position=position,size=25)
            path.write_text(json.dumps(doc))
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,width,0,0))
            time.sleep(.15);self.drain(self.first[1]);self.drain(self.second[1])
            p=self.worker('''import os
from fonts.browser import picker
from menu_tmux import TmuxContext
row=dict(id='local:Fixture',name='Font with spaces')
result=picker([row],[dict(report=dict(items=[row]))],{},TmuxContext.capture(client=os.environ['CLIENT']))
print(result['id'])
''')
            self.receive(self.first[1],b'Fixture');time.sleep(.2)
            self.assertNotIn(b'Fixture',self.drain(self.second[1]))
            os.write(self.first[1],b'\r')
            out,err=p.communicate(timeout=15)
            self.assertEqual((p.returncode,out.strip()),(0,'local:Fixture'),err)

    def icons(self):
        # Both the controller and the private popup inherit the fixture provider.
        provider = self.base / 'termux-clipboard-set'
        provider.write_text('#!' + shutil.which('bash') + '\n'
                            '[[ ! -e "$HOME/fail-copy" ]] || exit 1\ncat > "$HOME/copied"\n')
        provider.chmod(0o700)
        for key, value in dict(PATH=str(self.base) + os.pathsep + self.env['PATH'],
                               TERMUX__PREFIX='/data/data/com.termux/files/usr').items():
            self.env[key] = value
            self.control('set-environment', '-t', 'fixture', key, value)
        return self.worker('''import os,sys
from types import SimpleNamespace
from fonts.browser import icons
from fonts.commands import parser
from menu_tmux import TmuxContext
rows=[dict(name=name,collection='test',glyph=chr(point),codepoint=f'U+{point:04X}')
      for name,point in [('test-fixture',0xE000),('second-fixture',0xE001)]]
library=SimpleNamespace(families={},catalog=dict(glyph_version='v1.0.0',glyphs={'v1.0.0':rows}))
context=TmuxContext.capture(client=os.environ['CLIENT'])
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
        for keys, expected in [(b'', '\ue000'), (b'\x1b[B\t\t', '\ue001\ue000')]:
            p=self.icons();self.receive(self.first[1],b'test-fixture')
            os.write(self.first[1],keys + b'\x1bp')
            out,err=p.communicate(timeout=15)
            self.assertEqual((p.returncode,out),(0,expected),err)

    def test_large_batch_pastes_exact_bytes_and_preserves_existing_tmux_buffer(self):
        from fonts.browser import insert
        from menu_tmux import TmuxContext
        context = TmuxContext.capture(client=self.first[2])
        glyphs = '\U000f0001\ue001' * 7000
        expected = glyphs.encode('utf-8')
        sink = self.home / 'received'
        reader = self.home / 'reader.py'
        reader.write_text('from pathlib import Path\nimport sys, tty\n'
                          'tty.setraw(0)\nPath(sys.argv[1]).touch()\n'
                          'Path(sys.argv[2]).write_bytes(sys.stdin.buffer.read(int(sys.argv[3])))\n')
        ready = self.home / 'ready'
        self.control('set-buffer', '-b', 'fixture', 'keep')
        self.control('send-keys', '-t', self.pane, '-l', '--',
                     shlex.join([sys.executable, str(reader), str(ready), str(sink), str(len(expected))]))
        self.control('send-keys', '-t', self.pane, 'Enter')
        def wait_for(path):
            deadline = time.monotonic() + 10
            while not path.exists():
                self.assertLess(time.monotonic(), deadline, str(path))
                time.sleep(.05)
        wait_for(ready)
        insert(glyphs, context)
        wait_for(sink)
        self.assertEqual(sink.read_bytes(), expected)
        self.assertEqual(self.control('list-buffers', '-F', '#{buffer_name}').splitlines(), ['fixture'])
        self.assertEqual(self.control('show-buffer', '-b', 'fixture'), 'keep')

    def test_config_icon_selection_returns_glyph_without_external_effects(self):
        p=self.worker('''import os
from types import SimpleNamespace
from unittest.mock import patch
from fonts.browser import select_icon
from menu_tmux import TmuxContext
row=dict(name='select-fixture',collection='test',glyph='\\ue000',codepoint='U+E000')
library=SimpleNamespace(families={},catalog=dict(glyph_version='v1.0.0',glyphs={'v1.0.0':[row]}))
with patch('fonts.model.Library',return_value=library), patch('fonts.browser.copy',side_effect=AssertionError('clipboard effect')):
    print(select_icon(TmuxContext.capture(client=os.environ['CLIENT'])),end='')
''')
        self.receive(self.first[1],b'select-fixture')
        self.assertNotIn(b'select-fixture',self.drain(self.second[1]))
        os.write(self.first[1],b'\r')
        out,err=p.communicate(timeout=15)
        self.assertEqual((p.returncode,out),(0,'\ue000'),err)
        self.assertNotIn('\ue000',self.control('capture-pane','-p','-t',self.pane))

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
            deadline=time.monotonic()+15
            while p.poll() is None and time.monotonic()<deadline:
                self.drain(self.first[1])
            out,err=p.communicate(timeout=5)
            self.assertEqual((p.returncode,out),(0,''),err)
            self.assertEqual((self.home/'copied').read_bytes(),'\ue000'.encode())

    def test_glyph_stays_visible_with_long_suffix_match(self):
        path=Path(self.env['DOTS'])/'default/config.json'
        doc=json.loads(path.read_text());doc['apps']['fonts']['preview']['enabled']=False
        path.write_text(json.dumps(doc))
        for width in (40,80,120):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',24,width,0,0))
            p=self.worker('''import os
from fonts.browser import picker
from menu_tmux import TmuxContext
from interaction import SelectionEvent
row=dict(name='nf-'+'abcdefghij'*24+'needle',glyph=chr(0xE001),codepoint='U+E001')
try:picker([row],[],{},TmuxContext.capture(client=os.environ['CLIENT']),icons=True)
except SelectionEvent:pass
''')
            self.receive(self.first[1], '\ue001'.encode())
            os.write(self.first[1], b'needle')
            time.sleep(.25);self.drain(self.first[1])
            self.control('refresh-client','-t',self.first[2])
            screen=self.receive(self.first[1], '\ue001'.encode())
            self.assertIn(b'needle',screen)
            self.assertNotIn('\ue001'.encode(), self.drain(self.second[1]))
            os.write(self.first[1],b'\x1b')
            p.communicate(timeout=10)
            self.assertEqual(p.returncode,0)

    def test_icon_inserts_into_origin_without_enter(self):
        p=self.icons();self.receive(self.first[1],b'test-fixture')
        os.write(self.first[1], b'second')
        self.receive(self.first[1], b'second-fixture')
        # Mark B while filtered, then mark A. Focus moves back to B.
        os.write(self.first[1], b'\t\x15')
        time.sleep(.2)
        os.write(self.first[1], b'\t\x1bi')
        def wait_for(text):
            deadline=time.monotonic()+8
            while text not in self.control('capture-pane','-p','-t',self.pane):
                self.assertLess(time.monotonic(),deadline,repr(self.drain(self.first[1])[-600:]))
                time.sleep(.05)
        wait_for('\ue001\ue000')
        self.assertIsNone(p.poll())
        os.write(self.first[1], b'\x1bi')
        wait_for('\ue001\ue000\ue001')
        os.write(self.first[1], b'\x1b')
        out,err=p.communicate(timeout=15)
        self.assertEqual((p.returncode,out),(0,''),err)
        self.assertNotIn('command not found',self.control('capture-pane','-p','-t',self.pane))
        self.control('send-keys','-t',self.pane,'C-u')

    def test_foreground_nf_leaves_inserted_text_in_originating_editor(self):
        root=Path(self.env['DOTS'])
        (root/'lib').symlink_to(ROOT/'lib',target_is_directory=True)
        (root/'bin').symlink_to(ROOT/'bin',target_is_directory=True)
        cache=Path(self.env['XDG_CACHE_HOME'])/'dots/fonts/catalog.json'
        cache.parent.mkdir(parents=True)
        rows=[dict(name='foreground-fixture',glyph='\ue000',collection='fixture',codepoint='U+E000')]
        cache.write_text(json.dumps(dict(schema=1,families={},glyph_version='v',glyphs={'v':rows})))
        bind=shlex.quote('"\\C-g":printf %s "$READLINE_LINE" > "$HOME/nf-buffer"')
        command='bind -x '+bind+' && '+shlex.join([str(root/'bin/nf'),'--client',self.first[2]])
        self.control('send-keys','-t',self.pane,'-l','--',command)
        self.control('send-keys','-t',self.pane,'Enter')
        self.receive(self.first[1],b'foreground-fixture')
        os.write(self.first[1],b'\x1bi')
        deadline=time.monotonic()+10
        while '\ue000' not in self.control('capture-pane','-p','-t',self.pane):
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        os.write(self.first[1],b'\x1bi')
        while '\ue000\ue000' not in self.control('capture-pane','-p','-t',self.pane):
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        os.write(self.first[1],b'\x1b')
        self.receive(self.first[1],b'bash-')
        self.control('send-keys','-t',self.pane,'C-g')
        path=self.home/'nf-buffer'
        while not path.exists():
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        self.assertEqual(path.read_text(),'\ue000\ue000')

    def test_failed_batch_copy_keeps_marks_for_retry(self):
        (self.home/'fail-copy').touch()
        p=self.icons();self.receive(self.first[1],b'test-fixture')
        os.write(self.first[1], b'\x1b[B\t\t\r')
        self.receive(self.first[1], b'Copy failed')
        self.assertFalse((self.home/'copied').exists())
        (self.home/'fail-copy').unlink()
        os.write(self.first[1], b'\x1by')
        out,err=p.communicate(timeout=15)
        self.assertEqual((p.returncode,out),(0,''),err)
        self.assertEqual((self.home/'copied').read_bytes(),'\ue001\ue000'.encode())


if __name__=='__main__':unittest.main(verbosity=2)
