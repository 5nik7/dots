#!/usr/bin/env python3
"""Real todo FZF previews/events on private tmux servers and owned roots."""
import os
import json
import shutil
from pathlib import Path
import time
import unittest
import sys
import threading
from unittest.mock import patch

from test_menus import MenuFixture, NativeMenuFixture


class TodoLayout(MenuFixture):
    def test_numeric_geometry_and_visibility(self):
        from todo_layout import preview_rows, action
        for lines, matches, popup, notice, expected in (
                (20, 1, True, 0, 12), (20, 5, True, 0, 8), (20, 9, True, 0, 4),
                (20, 20, True, 0, 4), (20, 0, True, 0, 4), (20, 1, True, 1, 11),
                (10, 1, True, 0, 2), (10, 1, True, 1, 1),
                (22, 1, False, 0, 14), (12, 20, False, 0, 2)):
            with self.subTest(lines=lines, matches=matches, popup=popup, notice=notice):
                self.assertEqual(preview_rows(lines, matches, popup=popup, notice=notice), expected)
        env = dict(FZF_LINES='20', FZF_MATCH_COUNT='1', FZF_PREVIEW_LINES='4',
                   DOTS_TODO_LAYOUT_NOTICE='0', DOTS_TODO_LAYOUT_POPUP='1')
        self.assertEqual(action('update', env), 'change-preview-window(down,12,wrap)')
        self.assertEqual(action('toggle', env), 'change-preview-window(hidden)')
        env['FZF_PREVIEW_LINES'] = '12'
        self.assertEqual(action('update', env), '')
        env.pop('FZF_PREVIEW_LINES')
        self.assertEqual(action('update', env), '')
        self.assertEqual(action('toggle', env), 'change-preview-window(down,12,wrap)')
        for value in ('', '-1', '10000001', '1)+execute(touch bad)', '１２'):
            env['FZF_MATCH_COUNT'] = value
            self.assertEqual(action('update', env), '')
            self.assertEqual(action('toggle', env), 'toggle-preview')

    def test_capability_fallback_and_native_bindings(self):
        from todo_layout import bindings
        with patch('subprocess.run') as run:
            run.return_value.returncode = 2
            self.assertEqual(bindings(popup=True, notice=0), ([], {}))
            run.side_effect = OSError('missing')
            self.assertEqual(bindings(popup=True, notice=0), ([], {}))
            run.side_effect = None
            run.return_value.returncode = 1
            for native, prefix in (('posix', '"$DOTS_TODO_PYTHON"'), ('nt', '& $env:DOTS_TODO_PYTHON')):
                with patch('todo_layout.os.name', native):
                    keys, env = bindings(popup=True, notice=1)
                self.assertEqual(len(keys), 3)
                self.assertTrue(all(prefix in key for key in keys))
                self.assertFalse(any('{q}' in key or '{}' in key for key in keys))
                self.assertEqual(env['DOTS_TODO_LAYOUT_NOTICE'], '1')
            self.assertEqual(run.call_args.kwargs['env']['FZF_DEFAULT_OPTS'], '')
            self.assertEqual(run.call_args.kwargs['input'], b'')


class TodoPopup(NativeMenuFixture):
    def prepare(self):
        from todo_core import Goals, scope
        Path(self.env['DOTS']).mkdir()
        return Goals(scope()).mutate('add', title='Phone layouts ü', alias='phone-layouts', priority='high', notes='Preview evidence',
                                     acceptance=['Readable narrow popup'])['goals'][0]

    def test_tree_ancestors_counts_and_context_selection(self):
        from todo_core import Goals,scope
        parent=self.prepare()
        child=Goals(scope()).mutate('add',title='Needle child',parent=parent['id'])['goals'][0]
        code = """import os,json
from todo_core import Goals,scope
from todo_menu import pick
from menu_tmux import TmuxContext
s=Goals(scope());child=next(g for g in s.goals if g['title']=='Needle child')
g=pick(s,[child],dict(list_type='tree'),TmuxContext.capture(client=os.environ['CLIENT']))
print(json.dumps(dict(id=g['id'],context=g.get('_todo_context'))))
"""
        for width,height in ((40,14),(80,24),(120,30)):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',height,width,0,0))
            time.sleep(.2);self.drain(self.first[1]);self.drain(self.second[1])
            worker=self.worker(code)
            capture=self.receive(self.first[1],b'matching')
            self.assertIn(b'matching',capture)
            os.write(self.first[1],b'Needle');time.sleep(.4)
            os.write(self.first[1],b'\r')
            out,err=worker.communicate(timeout=15)
            self.assertEqual(worker.returncode,0,err)
            self.assertEqual(json.loads(out),dict(id=parent['id'],context=True))
            self.assertNotIn(b'matching',self.drain(self.second[1]))

    def test_real_previews_widths_and_exact_client(self):
        goal = self.prepare()
        code = '''import os,json
from todo_core import Goals,scope
from todo_menu import pick
from menu_tmux import TmuxContext
from interaction import RichSelector
original=RichSelector.fzf
def inspect(self,*args,**kwargs):
    print(json.dumps({key:kwargs[key] for key in ('popup','height','preview_lines')}),flush=True)
    return original(self,*args,**kwargs)
RichSelector.fzf=inspect
c=TmuxContext.capture(client=os.environ['CLIENT'])
s=Goals(scope())
g=pick(s,s.goals,dict(notice=os.environ.get('NOTICE',''),list_type='regular'),c)
print('selected:'+g['id'])
'''
        cases = ((40, 14, 2, ''), (80, 24, 4, ''), (120, 30, 4, ''),
                 (40, 14, 1, 'Copied complete brief'), (80, 24, 4, 'Copied complete brief'), (120, 30, 4, ''))
        for index, (width, height, preview, notice) in enumerate(cases):
            if index == 3:
                from todo_core import Goals, scope
                for number in range(7):
                    Goals(scope()).mutate('add', title='Additional goal ' + str(number))
            self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', height, width, 0, 0))
            time.sleep(.2)
            self.drain(self.first[1]); self.drain(self.second[1])
            worker = self.worker(code, NOTICE=notice)
            capture = self.receive(self.first[1], b'Copied' if notice else b'Subgoals')
            self.assertIn(b'todo', capture)
            self.assertNotIn(b'Subgoals', self.drain(self.second[1]))
            # The smaller preview still exposes all notes through its existing scroll keys.
            scrolled = bytes(capture)
            for _ in range(24):
                if b'evidence' in scrolled: break
                os.write(self.first[1], b'\x1bj')
                time.sleep(.05)
                scrolled += self.drain(self.first[1])
            self.assertIn(b'evidence', scrolled)
            os.write(self.first[1], b'\x1bp'); time.sleep(.1)
            os.write(self.first[1], b'\x1bp'); time.sleep(.1)
            os.write(self.first[1], b'\r')
            out, err = worker.communicate(timeout=15)
            self.assertEqual(worker.returncode, 0, err)
            geometry, selected = out.splitlines()
            self.assertEqual(json.loads(geometry), dict(popup=f'center,{width-2},{height-2}',
                height=height-2, preview_lines=preview))
            self.assertEqual(selected, 'selected:' + goal['id'])
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_live_preview_counts_hidden_toggle_and_rapid_queries(self):
        from todo_core import Goals, scope
        goal = self.prepare()
        Goals(scope()).mutate('edit', goal['id'], alias='zzzz')
        for index in range(19):
            Goals(scope()).mutate('add', title=('Phone extra ' if index < 4 else 'Other goal ') + str(index))
        probe, log = self.base/'layout probe.py', self.base/'layout.jsonl'
        probe.write_text('''import json,os,sys
from todo_layout import action
result=action(sys.argv[1],os.environ)
with open(os.environ['LAYOUT_LOG'],'a') as stream:
    stream.write(json.dumps(dict(mode=sys.argv[1],count=os.environ.get('FZF_MATCH_COUNT'),
        preview=os.environ.get('FZF_PREVIEW_LINES'),lines=os.environ.get('FZF_LINES'),
        action=result))+'\\n')
sys.stdout.write(result)
''')
        code = '''import os
from todo_core import Goals,scope
from todo_menu import pick
from menu_tmux import TmuxContext
import todo_layout
original=todo_layout.bindings
def observed(**kwargs):
    bindings,env=original(**kwargs)
    assert bindings
    env['DOTS_TODO_LAYOUT']=os.environ['LAYOUT_PROBE']
    bindings.append('ctrl-g:transform:"$DOTS_TODO_PYTHON" -B "$DOTS_TODO_LAYOUT" probe')
    return bindings,env
todo_layout.bindings=observed
c=TmuxContext.capture(client=os.environ['CLIENT'])
s=Goals(scope())
g=pick(s,s.goals,{'list_type':'regular'},c)
print(g['id'])
'''
        for width, height, compact, single, five in ((40,14,2,2,2), (80,24,4,12,8), (120,30,4,18,14)):
            with self.subTest(width=width, height=height):
                self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', height, width, 0, 0))
                time.sleep(.2)
                self.drain(self.first[1]); self.drain(self.second[1])
                log.write_text('')
                worker = self.worker(code, LAYOUT_PROBE=str(probe), LAYOUT_LOG=str(log))
                self.receive(self.first[1], b'Alt-C')

                def state(count, preview):
                    deadline = time.monotonic() + 12
                    seen = []
                    while time.monotonic() < deadline:
                        before = len(log.read_text().splitlines())
                        os.write(self.first[1], b'\x07')
                        # Keep one observation in flight. Flooding synchronous
                        # transforms delays the query we are trying to observe.
                        while time.monotonic() < deadline:
                            time.sleep(.05)
                            self.drain(self.first[1])
                            try: seen = [json.loads(line) for line in log.read_text().splitlines()]
                            except json.JSONDecodeError: continue
                            probes = [r for r in seen[before:] if r['mode'] == 'probe']
                            if not probes: continue
                            if any(r['count'] == str(count) and int(r['preview'] or 0) == preview for r in probes): return
                            break
                    self.fail('layout did not settle: ' + repr(seen[-5:]))

                def query(text, count, preview):
                    os.write(self.first[1], b'\x15' + text.encode())
                    state(count, preview)

                state(20, compact)
                query('Phone', 5, five)
                query('zzzz', 1, single)
                os.write(self.first[1], b'\x1bp'); state(1, 0)
                query('Phone', 5, 0)
                os.write(self.first[1], b'\x1bp'); state(5, five)
                query('no-match-unique', 0, compact)
                query('', 20, compact)
                for text in ('zzzz', 'no-match-unique', 'Phone', 'zzzz'):
                    os.write(self.first[1], b'\x15' + text.encode())
                    time.sleep(.01)
                state(1, single)
                os.write(self.first[1], b'\r')
                out, err = worker.communicate(timeout=15)
                self.assertEqual(worker.returncode, 0, err)
                self.assertEqual(out.strip(), goal['id'])
                self.assertNotIn(b'Alt-C', self.drain(self.second[1]))

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
        for width, height in ((40, 14), (80, 24), (120, 30)):
            self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', height, width, 0, 0))
            time.sleep(.2)
            self.drain(self.first[1])
            worker = self.worker(code)
            self.receive(self.first[1], b'Alt-N')
            os.write(self.first[1], b'no-match');time.sleep(.2);os.write(self.first[1], b'\x1bn')
            out, err = worker.communicate(timeout=15)
            self.assertEqual(worker.returncode,0,err);self.assertEqual(out.strip(),'event:new:None')
        self.assertFalse((Path(self.env['DOTS'])/'.dots').exists())

    def test_brief_copy_print_from_list_and_reader_at_three_widths(self):
        from todo_core import Goals, scope
        from todo_brief import brief
        goal = self.prepare()
        Goals(scope()).mutate('add', title='Attached child', parent=goal['id'])
        expected = brief(Goals(scope()), goal)
        clipboard = self.base/'clipboard.txt'
        code = '''import os
from pathlib import Path
from todo_core import scope
from todo_commands import parser
from todo_menu import browse,Handoff
import clipboard
clipboard.copy=lambda text: Path(os.environ['CLIPBOARD']).write_text(text)
r=browse(scope(),parser().parse_args(['browse','--client',os.environ['CLIENT']]))
assert isinstance(r,Handoff) and r.code==0
'''
        for width in (40, 80, 120):
            self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', 30, width, 0, 0))
            time.sleep(.15)
            for reader in (False, True):
                with self.subTest(width=width, reader=reader):
                    self.drain(self.first[1]); self.drain(self.second[1])
                    worker = self.worker(code, CLIPBOARD=str(clipboard))
                    self.receive(self.first[1], b'Alt-C')
                    os.write(self.first[1], b'phone')
                    time.sleep(.15)
                    if reader:
                        os.write(self.first[1], b'\r')
                        self.receive(self.first[1], b'actions:')
                        os.write(self.first[1], b'agent brief')
                        time.sleep(.3)
                        os.write(self.first[1], b'\r')
                        self.receive(self.first[1], b'Alt-Y')
                        os.write(self.first[1], b'Acceptance')
                        time.sleep(.15)
                    os.write(self.first[1], b'\x1by')
                    self.receive(self.first[1], b'Copied')
                    self.assertEqual(clipboard.read_text(), expected)
                    self.assertNotIn(b'Copied', self.drain(self.second[1]))
                    os.write(self.first[1], b'\x1bo')
                    out, err = worker.communicate(timeout=15)
                    self.assertEqual(worker.returncode, 0, err)
                    self.assertEqual(out, expected)
        self.assertFalse(list(self.base.glob('dots-output-*')))
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_codex_new_window_owns_input_and_retains_goal_association(self):
        from platform_info import detect
        if detect()['platform'] != 'termux': self.skipTest('Termux runit adapter fixture')
        try:
            from websockets.sync.server import serve
        except ImportError:
            self.skipTest('optional websockets unavailable')
        from test_todo_plan import FakeCodex
        from todo_plan import Link, thread_name
        from todo_core import scope
        goal = self.prepare()
        fixture = FakeCodex()
        def handler(ws):
            for raw in ws:
                request = json.loads(raw)
                if 'id' not in request: continue
                result = {} if request['method'] == 'initialize' else fixture.call(request['method'], request.get('params'))
                ws.send(json.dumps(dict(id=request['id'], result=result)))
        server = serve(handler, '127.0.0.1', 0)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.socket.getsockname()[1]
        token_dir = self.home/'.local/share/codex-remote'; token_dir.mkdir(parents=True, mode=0o700)
        token = token_dir/'token'; token.write_text('a'*64); token.chmod(0o600)
        stub = self.base/'commands'; stub.mkdir()
        capture = self.base/'codex-arguments.json'
        executable = stub/'codex-termux'
        executable.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
            'if "manage" in sys.argv:\n print("runit_port=' + str(port) + '")\n'
            'else:\n from pathlib import Path\n Path(os.environ["CAPTURE"]).write_text(json.dumps(dict('
            'argv=sys.argv[1:],cwd=os.getcwd(),pane=os.environ.get("TMUX_PANE"))))\n'
            ' print("CODEX_FIXTURE_READY",flush=True)\n sys.stdin.readline()\n')
        executable.chmod(0o700)
        code = '''import os
from todo_core import scope
from todo_commands import parser
from todo_menu import browse,Handoff
import style_config
original=style_config.icon
def icon(name, fallback='', app=None):
    if name=='status.todo' and app=='tmux' and os.environ.get('FIXTURE_ICON'):
        return os.environ['FIXTURE_ICON']
    return original(name,fallback,app)
style_config.icon=icon
r=browse(scope(),parser().parse_args(['browse','--client',os.environ['CLIENT']]))
assert isinstance(r,Handoff) and r.code==0
'''
        for width, height, custom in ((40,14,''), (80,24,'✓'), (120,30,'#{session_name}')):
            with self.subTest(width=width, icon=custom):
                self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', height, width, 0, 0))
                time.sleep(.2)
                self.drain(self.first[1])
                worker = self.worker(code, PATH=str(stub)+os.pathsep+self.env['PATH'],
                                     CAPTURE=str(capture), FIXTURE_ICON=custom)
                self.receive(self.first[1], b'Alt-C')
                os.write(self.first[1], b'\x1bc')
                self.receive(self.first[1], b'CODEX_FIXTURE_READY')
                out, err = worker.communicate(timeout=15)
                self.assertEqual(worker.returncode, 0, err)
                data = json.loads(capture.read_text())
                self.assertNotEqual(data['pane'], self.pane)
                self.assertEqual(data['cwd'], self.env['DOTS'])
                self.assertIn('resume', data['argv'])
                self.assertEqual(data['argv'][-1], Link(scope(), goal['id']).read()['thread'])
                label = self.control('display-message','-p','-t',data['pane'],'#{window_name}').strip()
                self.assertEqual(label, custom or '󰄬')
                self.assertEqual(self.control('show-options','-wv','-t',data['pane'],'automatic-rename').strip(),'off')
                names = [p['name'] for m,p in fixture.calls if m=='thread/name/set']
                self.assertTrue(names)
                self.assertEqual(names[-1], thread_name(scope(), goal))
                # Exit through the fixture's input so the RPC connection closes normally.
                os.write(self.first[1], b'\r')
                deadline = time.monotonic() + 5
                while data['pane'] in self.control('list-panes','-a','-F','#{pane_id}').splitlines():
                    self.assertLess(time.monotonic(), deadline, 'fixture window did not close')
                    time.sleep(.05)
        self.assertEqual(len([m for m,p in fixture.calls if m == 'turn/start']), 1)
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_print_brief_exits_containing_dots_launcher(self):
        from test_menus import ROOT
        from todo_core import Goals, scope
        from todo_brief import brief
        goal = self.prepare()
        directory = Path(self.env['DOTS'])/'bin'; directory.mkdir()
        shutil.copy2(ROOT/'bin/dots-todo-browse', directory/'dots-todo-browse')
        code = '''import os
from menu_cli import main
assert main(['--browse','--client',os.environ['CLIENT']])==0
'''
        worker = self.worker(code)
        self.receive(self.first[1], b'dots:')
        os.write(self.first[1], b'todo')
        time.sleep(.2)
        os.write(self.first[1], b'\r')
        self.receive(self.first[1], b'Alt-C')
        os.write(self.first[1], b'\x1bo')
        out, err = worker.communicate(timeout=15)
        self.assertEqual(worker.returncode, 0, err)
        self.assertEqual(out, brief(Goals(scope()), goal))

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
