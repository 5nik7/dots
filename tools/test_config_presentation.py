#!/usr/bin/env python3
"""Consumer checks for independent glyph/spans and typed human layout."""
import io
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import test_profile_config as fixtures
from files.catalog import Presentation
from menus import Menu,Entry,listing,styled_label
from style_config import current
from config_values import current as controls
from resources import cells

class PresentationConfig(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        self.env.update(TERM='xterm-256color',DOTS_COLOR='always',DOTS_ICONS='always')
        self.environ=patch.dict(os.environ,self.env,clear=True);self.environ.start();self.addCleanup(self.environ.stop)
        current.cache_clear();controls.cache_clear()
        self.addCleanup(current.cache_clear);self.addCleanup(controls.cache_clear)

    def test_popup_spans_and_icon_color_with_plain_fallbacks(self):
        (self.path.parent/'colors.toml').write_text('[icons.status.todo]\nfg="#123456"\nbg="#654321"\n')
        doc=json.loads(self.path.read_text());doc['formatting']={'apps':{'menu':{'entries':{'test:one':{'label':{'fg':'#abcdef'}}}}}}
        self.path.write_text(json.dumps(doc))
        menu=Menu('test','Test',(Entry('one','Long choice 界 '*5,'Description '*5,icon='󰄬',icon_role='status.todo'),))
        ui=Presentation(io.StringIO(),terminal=True)
        rendered=styled_label(menu,menu.entries[0],ui)
        self.assertIn('38;2;18;52;86',rendered);self.assertIn('48;2;101;67;33',rendered)
        self.assertIn('38;2;171;205;239',rendered)
        for width in (40,80,120):
            stream=io.StringIO();plain=Presentation(stream,terminal=True);plain.color=False;plain.width=width
            listing(menu,menu.entries,plain)
            self.assertNotIn('\x1b',stream.getvalue());self.assertTrue(all(cells(line)<=width for line in stream.getvalue().splitlines()))
        ui.icons=False;self.assertNotIn('󰄬',styled_label(menu,menu.entries[0],ui))

    def test_formatting_applies_only_to_human_views(self):
        doc=json.loads(self.path.read_text());doc['formatting']={'apps':{'cli':{'indent':6,'label_width':5,'label_gap':2,'alignment':'right','indent_style':'tabs','tab_width':3}}}
        self.path.write_text(json.dumps(doc))
        stream=io.StringIO();ui=Presentation(stream,terminal=True);ui.color=False
        ui.detail_spans('X',[('VALUE',None)])
        self.assertEqual(stream.getvalue(),'          X  VALUE\n')
        with patch.dict(os.environ,DOTS_COLOR='never',DOTS_ICONS='never'):
            plain=io.StringIO();out=Presentation(plain);out.detail('X','VALUE')
            self.assertEqual(plain.getvalue(),'    X          VALUE\n')

if __name__=='__main__':unittest.main()
