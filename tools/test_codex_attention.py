#!/usr/bin/env python3
"""Private topology fixtures: identity, expiry, aggregation and exact tab cells."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import subprocess
import time
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
import codex_attention as attention
import menu_sessions

spec = importlib.util.spec_from_file_location('tabs', ROOT / 'config/tmux/termux-status.py')
tabs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tabs)
THREAD = '01234567-1234-1234-1234-0123456789ab'


class Attention(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-attention-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, HOME=str(self.root), XDG_STATE_HOME=str(self.root / 'state'))
        env.start()
        self.addCleanup(env.stop)
        self.proc = self.root / 'proc'
        self.process(10, 100)
        self.process(20, 200)
        self.sock = self.root / 'socket space ü'
        self.sock.touch()
        self.server = dict(key=attention.socket_key(str(self.sock)), socket=str(self.sock), updated=time.time(),
            tabs=[dict(pid=10, started=100, tty='pts/1'), dict(pid=20, started=200, tty='pts/2')],
            clients=[dict(session='$1', tty='pts/1'), dict(session='$2', tty='pts/2')],
            panes=[dict(pane='%1', window='@1', sessions=[dict(id='$1', created=10)],
                        state='working', thread='-', attention=False),
                   dict(pane='%2', window='@2', sessions=[dict(id='$2', created=20)],
                        state='waiting', thread=THREAD, attention=True)])

    def process(self, pid, started):
        p = self.proc / str(pid)
        p.mkdir(parents=True, exist_ok=True)
        fields = ['S', '1', str(pid), str(pid), '34817'] + ['0'] * 14 + [str(started)]
        (p / 'stat').write_text(f'{pid} (shell (name)) ' + ' '.join(fields))

    def publish(self, servers=None):
        attention.root().mkdir(parents=True, mode=0o700, exist_ok=True)
        path = attention.root() / 'overview.json'
        path.write_text(json.dumps(dict(schema=1, time=time.time(), servers=servers or [self.server])))
        path.chmod(0o600)
        return path

    def test_identity_expiry_and_malformed_snapshots(self):
        path = self.publish()
        self.assertEqual(len(attention.load()), 1)
        self.server['updated'] = time.time() - 16
        self.publish()
        self.assertEqual(attention.load(), [])
        self.server['updated'] = time.time()
        self.publish()
        replacement = self.root / 'replacement'
        replacement.touch()
        os.replace(replacement, self.sock)
        self.assertEqual(attention.load(), [])
        for data in ('[]', '{', '{"schema":1,"time":0,"servers":[]}', 'x' * (attention.MAX_BYTES + 1)):
            path.write_text(data)
            self.assertEqual(attention.load(), [])
        path.unlink()
        path.symlink_to(self.sock)
        self.assertEqual(attention.load(), [])

    def test_tabs_sessions_linked_panes_and_pid_reuse(self):
        state, count = attention.tab_states([self.server], self.proc)
        self.assertEqual(count, 0)
        self.assertEqual(state[(20, 200, 'pts/2')], dict(state='waiting', attention=True))
        self.server['panes'][1]['sessions'].append(dict(id='$3', created=30))
        state, count = attention.tab_states([self.server], self.proc)
        self.assertEqual(count, 1)
        self.process(20, 201)
        state, count = attention.tab_states([self.server], self.proc)
        self.assertEqual(count, 2)
        self.assertNotIn((20, 200, 'pts/2'), state)
        other = copy.deepcopy(self.server)
        other['key'] = 'other'
        self.assertEqual(attention.tab_states([self.server, other], self.proc)[1], 4)

    def test_full_labels_and_alert_overflow(self):
        snapshot = dict(count=10, sessions=[dict(pid=i * 10, tty=f'pts/{i}') for i in range(1, 11)])
        states = {(20, 200, 'pts/2'): dict(state='waiting', attention=True),
                  (100, 1000, 'pts/10'): dict(state='idle', attention=True)}
        colors = ['#111111', '#aaaaaa', '#222222', '#ff8800']
        for width in (22, 30, 40):
            result = tabs.render_attention_tabs(snapshot, 'pts/1', colors, width, '#555555', '#111111',
                                                states, 2, '#ff0000', '#101010')
            plain = re.sub(r'#\[[^]]*\]', '', result)
            self.assertLessEqual(len(plain), width)
            self.assertIn(' 1 ', plain)
            self.assertIn('[ 2]', plain)
            self.assertIn('[2 ]', plain)
            self.assertIn('fg=#ff0000,bold,nounderscore,noreverse,nodim]>#[default]', result)
            self.assertIn('fg=#ff0000,bold,nounderscore,noreverse,nodim][2 ]#[default]', result)
        one = dict(count=1, sessions=[dict(pid=10, tty='pts/1')])
        result = tabs.render_attention_tabs(one, 'pts/1', colors, 22, '#555555', '#111111', {}, 1, 'brightred', 'black')
        self.assertEqual(re.sub(r'#\[[^]]*\]', '', result), '[ 1]')
        self.assertEqual(tabs.render_attention_tabs(one, 'pts/1', colors, 22, '#555555', '#111111', {}, 0, 'brightred', 'black'), '')

    def test_menu_overlay_preserves_data_and_names(self):
        self.publish()
        server = menu_sessions.Server('/fixture/tmux', str(self.sock), 42)
        record = menu_sessions.Session('$2', 'literal #[name]', 1, 1, False, 20)
        overlay = menu_sessions.with_attention(server, (record,))[0]
        self.assertEqual(overlay.attention, 1)
        self.assertEqual(record.document(), overlay.document())
        changed = menu_sessions.Session('$2', 'reused', 1, 0, False, 99)
        self.assertEqual(menu_sessions.with_attention(server, (changed,))[0].attention, 0)

    def test_menu_attention_width_and_independent_styles(self):
        from files.catalog import Presentation
        from menu_projects import Project, Row
        import menu_session_ui as ui
        from resources import cells
        record = menu_sessions.Session('$2', '日本語' * 12, 2, 1, True, 20, 1,
                                       (self.server['panes'][1],))
        rows = (Row('project', record.name, Project(self.root, record.name), (record,)),)
        for width in (40, 80, 120):
            for mode in ('always', 'never'):
                with patch.dict(os.environ, DOTS_COLOR=mode, DOTS_ICONS=mode):
                    labels, previews = ui.render(rows, Presentation(terminal=True), width)
                self.assertLessEqual(cells(ui.ANSI.sub('', labels[0])), width)
                self.assertIn('@2 / %2 · waiting', ui.ANSI.sub('', previews[0]))
                if mode == 'always':
                    self.assertTrue(labels[0].endswith('\x1b[1;91m ·  1\x1b[0m'))
                    count = '[1]' if width < 52 else '1 session'
                    self.assertIn('\x1b[38;5;208m' + count + '\x1b[0m', labels[0])
                else:
                    self.assertNotIn('\x1b', labels[0])
                    self.assertTrue(labels[0].endswith(' · Codex 1'))

    def test_alert_menu_acknowledges_only_selected_target_and_refuses_drift(self):
        from menus import Entry
        self.publish()
        record = menu_sessions.Session('$2', 'literal name', 1, 0, False, 20)
        choices = [Entry('0', 'selected'), Entry('ack', 'acknowledge'), None]
        with patch.object(menu_sessions, 'choose', side_effect=choices), \
                patch.object(menu_sessions, 'observe', return_value=subprocess.CompletedProcess([], 0, '42\n', '')), \
                patch.object(menu_sessions.Server, 'sessions', return_value=(record,)), \
                patch.object(menu_sessions.Server, 'read', return_value='%2\n'), \
                patch.object(menu_sessions, 'acknowledge_alert') as ack:
            self.assertFalse(menu_sessions.browse_attention().selected)
            ack.assert_called_once_with(str(self.sock), self.server['panes'][1])
        replacement = menu_sessions.Session('$2', 'reused', 1, 0, False, 99)
        with patch.object(menu_sessions, 'choose', side_effect=choices), \
                patch.object(menu_sessions, 'observe', return_value=subprocess.CompletedProcess([], 0, '42\n', '')), \
                patch.object(menu_sessions.Server, 'sessions', return_value=(replacement,)), \
                patch.object(menu_sessions, 'show_message'), patch.object(menu_sessions, 'acknowledge_alert') as ack:
            self.assertFalse(menu_sessions.browse_attention().selected)
            ack.assert_not_called()

    def test_other_server_menu_offers_explicit_new_tab_not_switch(self):
        from menus import Entry
        self.publish()
        context = Mock(socket='/another/socket')
        menus = []
        answers = iter([Entry('0', 'select'), None, None])
        def choose(menu, **kwargs):
            menus.append(menu)
            return next(answers)
        with patch.object(menu_sessions, 'choose', side_effect=choose), \
                patch('menu_session_host.is_termux', return_value=True), \
                patch.object(menu_sessions.Server, 'select') as select:
            self.assertFalse(menu_sessions.browse_attention(context).selected)
        self.assertEqual([e.id for e in menus[1].entries], ['termux', 'ack'])
        select.assert_not_called()

    def test_alert_menu_escape_returns_and_ctrl_c_exits(self):
        from interaction import SelectionEvent, SelectionEnded
        from menus import Entry
        self.publish()
        for choices in ([SelectionEvent('back')],
                        [Entry('0', 'select'), SelectionEvent('back'), SelectionEvent('back')]):
            with patch.object(menu_sessions, 'choose', side_effect=choices):
                self.assertFalse(menu_sessions.browse_attention().selected)
        with patch.object(menu_sessions, 'choose', side_effect=SelectionEnded(130)):
            with self.assertRaises(SelectionEnded):
                menu_sessions.browse_attention()


if __name__ == '__main__':
    unittest.main()
