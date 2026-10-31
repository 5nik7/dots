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
        self.assertEqual([tmux('show-option','-gqv','status-format['+str(i)+']') for i in (0,1)],before)
        config=self.defaults['formatting']['apps']['tmux'];config.update(position='bottom',main_row=0,termux_row=1,main_left=['windows','session'],main_right=['git','indicators'])
        self.publish(tmux)
        self.assertEqual(tmux('show-option','-gqv','status-position'),'bottom')
        row=tmux('show-option','-gqv','status-format[0]')
        self.assertLess(row.index('#{W:'),row.index('@dots-session-visible'))
        self.assertIn('align=right',row)
        for width in (40,80,120):
            tmux('set-option','-g','default-size',str(width)+'x24')
            self.assertNotIn('invalid',tmux('display-message','-p','#{E:status-format[0]}').lower())
        with self.assertRaises(ValueError):validate_layout(dict(rows=1,main_row=1),'termux')
        with self.assertRaises(ValueError):validate_layout(dict(rows=2,main_row=0,termux_row=0),'termux')

if __name__=='__main__':unittest.main()
