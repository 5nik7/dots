#!/usr/bin/env python3
"""Opt-in native Codex handoff using an owned home and a localhost model fixture.

DOTS_TEST_CODEX_NATIVE=1 python3 -B tools/test_todo_codex_native.py
Never connects to the user's Codex server, account, hooks or conversations.
"""
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

if os.name != 'nt':
    import fcntl
    import pty
    import termios

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots'))
from todo_codex import RPC
from todo_plan import Link, prepare
from todo_core import Goals, scope


class ModelFixture(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *args): pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.calls.append(request)
        arguments = json.dumps(dict(questions=[dict(id='fixture', header='Fixture',
            question='Fixture planning question?', options=[dict(label='Yes', description='Finish the fixture.'),
            dict(label='No', description='Stop the fixture.')])]))
        item = dict(type='function_call', id='fc_fixture', call_id='call_fixture',
                    name='request_user_input', arguments=arguments, status='completed')
        if len(self.server.calls) > 1:
            text = ('<proposed_plan>\n# Fixture implementation\n\n'
                    'Save the agreed goal tree, implement it and verify acceptance.\n</proposed_plan>'
                    if len(self.server.calls) == 2 else 'Fixture implementation accepted.')
            item = dict(type='message', role='assistant', id='msg_fixture', status='completed',
                        content=[dict(type='output_text', text=text, annotations=[])])
        response = dict(id='resp_fixture', object='response', status='completed', output=[item],
                        usage=dict(input_tokens=1, output_tokens=1, total_tokens=2))
        events = [dict(type='response.created', response=dict(response, status='in_progress', output=[])),
                  dict(type='response.output_item.added', output_index=0, item=item),
                  dict(type='response.output_item.done', output_index=0, item=item),
                  dict(type='response.completed', response=response)]
        data = ''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode()
        self.send_response(200); self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)


@unittest.skipUnless(os.environ.get('DOTS_TEST_CODEX_NATIVE') == '1' and os.name != 'nt',
                     'opt-in isolated native Codex/PTY test')
class NativeCodex(unittest.TestCase):
    def test_early_question_plan_restored_and_implementation_transition(self):
        from websockets.sync.client import connect
        wrapper = shutil.which('codex-termux')
        codex = shutil.which('codex')
        if not (wrapper or codex): self.skipTest('Codex unavailable')
        prefix = [wrapper, '--wrapper-no-config', '--wrapper-no-update', 'run'] if wrapper else [codex]
        with tempfile.TemporaryDirectory(prefix='dots codex native ü ') as temporary, ExitStack() as cleanup:
            base = Path(temporary)
            home, project = base/'home', base/'project'; home.mkdir(); project.mkdir()
            env = {k: v for k, v in os.environ.items() if k in ('PATH','PREFIX','LD_PRELOAD','SystemRoot','WINDIR')}
            env.update(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home/'codex'), DOTS=str(project),
                XDG_CONFIG_HOME=str(home/'config'), XDG_STATE_HOME=str(home/'state'),
                XDG_DATA_HOME=str(home/'data'), XDG_CACHE_HOME=str(home/'cache'),
                TMPDIR=str(base), TERM='xterm-256color', CODEX_TERMUX_AUTH_NOTICE='off',
                CODEX_TERMUX_AUTO_UPDATE='off', NO_PROXY='127.0.0.1,localhost')
            Path(env['CODEX_HOME']).mkdir()
            model = ThreadingHTTPServer(('127.0.0.1', 0), ModelFixture); model.calls = []
            threading.Thread(target=model.serve_forever, daemon=True).start()
            cleanup.callback(model.server_close); cleanup.callback(model.shutdown)
            config = ('model = "gpt-6.1-sol"\nmodel_provider = "fixture"\n'
                'model_reasoning_effort = "high"\nplan_mode_reasoning_effort = "xhigh"\n'
                'approval_policy = "never"\nsandbox_mode = "read-only"\n'
                '[model_providers.fixture]\nname = "Fixture"\nwire_api = "responses"\n'
                'base_url = "http://127.0.0.1:' + str(model.server_port) + '/v1"\n'
                '[projects.' + json.dumps(str(project)) + ']\ntrust_level = "trusted"\n')
            (Path(env['CODEX_HOME'])/'config.toml').write_text(config)
            with socket.socket() as reserved:
                reserved.bind(('127.0.0.1', 0)); port = reserved.getsockname()[1]
            url = 'ws://127.0.0.1:' + str(port)
            log = (base/'server.log').open('w+')
            server = subprocess.Popen([*prefix, 'app-server', '--listen', url], cwd=project, env=env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            def stop():
                if server.poll() is None:
                    os.killpg(server.pid, signal.SIGTERM)
                    try: server.wait(timeout=5)
                    except subprocess.TimeoutExpired: os.killpg(server.pid, signal.SIGKILL); server.wait()
                log.close()
            cleanup.callback(stop)
            connection = None
            for _ in range(100):
                try:
                    connector = connect(url, proxy=None, open_timeout=.2, close_timeout=1)
                    connection = connector.__enter__(); break
                except Exception:
                    if server.poll() is not None: break
                    time.sleep(.1)
            if connection is None:
                log.flush(); log.seek(0)
                self.fail('owned Codex server did not start: ' + log.read()[-4000:])
            pending = threading.Event()
            def receive():
                raw = connection.recv()
                message = json.loads(raw)
                if message.get('method') == 'item/tool/requestUserInput': pending.set()
                return raw
            rpc = RPC(connection.send, receive, lambda: connector.__exit__(None, None, None))
            cleanup.callback(rpc.close)
            with patch.dict(os.environ, env, clear=True):
                selected = scope(); goal = Goals(selected).mutate('add', title='Native planning fixture')['goals'][0]
                link = Link(selected, goal['id'])
                backend = type('Backend', (), dict(identity='fixture-native'))()
                with link.locked(): record = prepare(Goals(selected), goal, link, backend, rpc)
                goal_bytes = Path(selected['path']).read_bytes()
            self.assertTrue(pending.wait(20), 'Codex did not produce the fixture question; model calls=' + str(len(model.calls)))
            self.assertEqual(rpc.call('thread/read', dict(threadId=record['thread']))['thread']['name'], '[project] Native planning fixture')
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
            def session():
                os.setsid(); fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
            client = subprocess.Popen([*prefix, '--remote', url, '--cd', str(project), 'resume', record['thread']],
                stdin=slave, stdout=slave, stderr=slave, cwd=project, env=env, preexec_fn=session)
            os.close(slave)
            output = bytearray()
            try:
                deadline = time.monotonic() + 20
                while b'to submit answer' not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try: chunk = os.read(master, 65536)
                        except OSError: break
                        output.extend(chunk)
                        if b'\x1b[6n' in chunk: os.write(master, b'\x1b[1;1R')
                self.assertIn(b'Fixture planning question?', output, output[-5000:].decode(errors='replace'))
                self.assertIn(b'to submit answer', output)
                self.assertIn(b'Plan', output)
                self.assertIn(b'xhigh', output)
                time.sleep(.5)
                os.write(master, b'\r')
                deadline = time.monotonic() + 10
                while len(model.calls) < 2 and time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        chunk = os.read(master, 65536); output.extend(chunk)
                        if b'\x1b[6n' in chunk: os.write(master, b'\x1b[1;1R')
                self.assertGreaterEqual(len(model.calls), 2, output[-3000:].decode(errors='replace'))
                deadline = time.monotonic() + 15
                while b'Implement this plan?' not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        chunk = os.read(master, 65536); output.extend(chunk)
                        if b'\x1b[6n' in chunk: os.write(master, b'\x1b[1;1R')
                self.assertIn(b'Implement this plan?', output, output[-5000:].decode(errors='replace'))
                self.assertEqual(Path(selected['path']).read_bytes(), goal_bytes)
                time.sleep(.3)
                os.write(master, b'\r')  # Normal TUI implementation action, not an RPC mode override.
                deadline = time.monotonic() + 15
                while b'accepted.' not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        chunk = os.read(master, 65536); output.extend(chunk)
                        if b'\x1b[6n' in chunk: os.write(master, b'\x1b[1;1R')
                self.assertTrue(b'accepted.' in output, output[-3000:].decode(errors='replace'))
                self.assertEqual(len(model.calls), 3)
                self.assertIn('Implement the plan.', json.dumps(model.calls[-1]['input']))
                resumed = rpc.call('thread/resume', dict(threadId=record['thread'], excludeTurns=True))
                self.assertEqual(resumed['collaborationMode']['mode'], 'default')
                # This fake model tests the real UI/mode handoff, not model behavior or writes.
                self.assertEqual(Path(selected['path']).read_bytes(), goal_bytes)
            finally:
                if client.poll() is None:
                    os.killpg(client.pid, signal.SIGTERM)
                    try: client.wait(timeout=5)
                    except subprocess.TimeoutExpired: os.killpg(client.pid, signal.SIGKILL); client.wait()
                os.close(master)


if __name__ == '__main__': unittest.main()
