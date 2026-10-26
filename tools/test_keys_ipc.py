#!/usr/bin/env python3
"""Private ZLE IPC acceptance, with owned terminals and no personal startup."""
import io
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from keys import zsh_bridge as bridge
from zsh_interactive import Session


@unittest.skipUnless(shutil.which('zsh') and os.name != 'nt', 'Unix ZLE required')
class ZLE(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dk-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.home = self.base / 'h'; self.home.mkdir()
        self.env = dict(HOME=str(self.home), ZDOTDIR=str(self.home), DOTS=str(ROOT),
                        PATH=os.environ['PATH'], TMPDIR=str(self.base), TERM='xterm-256color',
                        TMUX='/fixture/socket,12345,0', TMUX_PANE='%7')
        for key in ('LD_PRELOAD', 'PREFIX'):
            if key in os.environ: self.env[key] = os.environ[key]
        for kind in ('CONFIG', 'STATE', 'CACHE', 'DATA'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / kind.lower())
        (self.home / '.zshrc').write_text('''
PS1='READY> '
HISTFILE=''
bindkey -v
source "$DOTS/lib/dots/shell/keys.bash"
_capture() {
  print -r -- "$BUFFER|$CURSOR|$KEYMAP" >| "$HOME/buffer"
  BUFFER=''; printf '\\036CAPTURE\\037'; zle accept-line
}
zle -N _capture
bindkey -M viins '^G' _capture
bindkey -M vicmd '^G' _capture
''')
        self.session = self.start()

    def start(self, env=None):
        session = Session(env or self.env, str(self.home))
        self.addCleanup(session.close)
        session.wait(b'READY> ', timeout=15)
        return session

    def command(self, code):
        self.session.send(code + '; printf "\\036DONE\\037"\r')
        result = self.session.wait(b'\x1eDONE\x1f', timeout=10)
        time.sleep(.08)
        return result

    def capture(self, pane='%7'):
        with patch.dict(os.environ, self.env, clear=True):
            return bridge.capture(pane)

    def test_live_maps_change_on_next_request_and_no_persistent_dump(self):
        rows, note = self.capture()
        self.assertIsNotNone(rows, note); self.assertGreater(len(rows), 100)
        self.assertIn('viins', {r['mode'] for r in rows})
        self.command('bindkey -M viins "^X^G" fixture-first')
        self.assertTrue(any(r['action'] == 'fixture-first' for r in self.capture()[0]))
        self.command('bindkey -M viins "^X^G" fixture-second')
        rows = self.capture()[0]
        self.assertTrue(any(r['action'] == 'fixture-second' for r in rows))
        self.assertFalse(any(r['action'] == 'fixture-first' for r in rows))
        runtime = self.base / ('dots-k-' + str(os.geteuid()))
        self.assertEqual([p.name for p in runtime.rglob('*') if not p.is_dir()], ['s'])
        self.assertEqual(runtime.stat().st_mode & 0o777, 0o700)

    def test_buffer_cursor_modes_and_last_status_survive(self):
        self.session.send('abcdef'); time.sleep(.1)
        self.session.send('\x1b'); time.sleep(.1)
        self.session.send('hi'); time.sleep(.1)
        self.assertIsNotNone(self.capture()[0])
        self.session.send('\x07')
        self.session.wait(b'\x1eCAPTURE\x1f'); time.sleep(.08)
        buffer, cursor, mode = (self.home / 'buffer').read_text().strip().split('|')
        self.assertEqual((buffer, cursor), ('abcdef', '4'))
        self.assertIn(mode, ('main', 'viins'))  # Native ZLE may retain the main alias.
        self.session.send('false\r'); self.session.wait(b'READY> '); time.sleep(.08)
        self.assertIsNotNone(self.capture()[0])
        self.command('print -r -- "$?" >| "$HOME/status"')
        self.assertEqual((self.home / 'status').read_text().strip(), '1')

    def test_busy_prompt_missing_wrong_pane_and_server(self):
        self.assertIsNone(self.capture('%8')[0])
        with patch.dict(os.environ, dict(self.env, TMUX='/wrong/socket,12345,0'), clear=True):
            self.assertIsNone(bridge.capture('%7')[0])
        self.session.send('sleep 1\r'); time.sleep(.12)
        start = time.monotonic()
        self.assertIsNone(self.capture()[0])
        self.assertLess(time.monotonic() - start, .4)
        self.session.wait(b'READY> ', timeout=4)
        self.assertIsNotNone(self.capture()[0])

    def test_reload_nesting_and_exit_cleanup(self):
        self.command('source "$DOTS/lib/dots/shell/keys.bash"; source "$DOTS/lib/dots/shell/keys.bash"; print -r -- "${(M)#precmd_functions:#_dots_keys_ipc_open}:${(M)#preexec_functions:#_dots_keys_ipc_close}:${(M)#zshexit_functions:#_dots_keys_ipc_close}" >| "$HOME/hooks"')
        self.assertEqual((self.home / 'hooks').read_text().strip(), '1:1:1')
        self.command('bindkey -M viins "^X^G" parent-only')
        self.session.send('zsh -di\r'); self.session.wait(b'READY> '); time.sleep(.08)
        rows = self.capture()[0]; self.assertIsNotNone(rows)
        self.assertFalse(any(r['action'] == 'parent-only' for r in rows))
        self.session.send('exit\r'); self.session.wait(b'READY> '); time.sleep(.08)
        self.assertTrue(any(r['action'] == 'parent-only' for r in self.capture()[0]))
        self.session.send('exit\r'); self.session.process.wait(timeout=5)
        self.assertFalse(list(self.base.rglob('s')))

    def test_ambiguous_and_concurrent_clients_fail_without_blocking_editor(self):
        other = self.start()
        rows, note = self.capture()
        self.assertIsNone(rows); self.assertIn('Multiple', note)
        other.send('exit\r'); other.process.wait(timeout=5)
        endpoint = next(self.base.rglob('s'))
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as idle:
            idle.connect(str(endpoint)); time.sleep(.06)
            start = time.monotonic(); self.command(':')
            self.assertLess(time.monotonic() - start, .8)
        time.sleep(.3)
        self.assertIsNotNone(self.capture()[0])

    def test_runtime_symlink_refused_and_no_registration_without_tmux(self):
        self.session.send('exit\r'); self.session.process.wait(timeout=5)
        runtime = self.base / ('dots-k-' + str(os.geteuid()))
        runtime.rmdir(); other = self.base / 'other'; other.mkdir()
        runtime.symlink_to(other, target_is_directory=True)
        shell = self.start()
        self.assertIsNone(self.capture()[0]); self.assertEqual(list(other.iterdir()), [])
        shell.send('exit\r'); shell.process.wait(timeout=5)
        env = dict(self.env); env.pop('TMUX'); env.pop('TMUX_PANE')
        plain = self.start(env)
        self.assertEqual(list(other.iterdir()), [])
        plain.send('exit\r'); plain.process.wait(timeout=5)

    def test_no_startup_or_prompt_snapshot_and_macro_redaction(self):
        self.command('functions[_fixture_snapshot]=${functions[_dots_keys_snapshot]}; _dots_keys_snapshot() { print called >> "$HOME/captures"; _fixture_snapshot; }; bindkey -M viins -s "^X^M" "private-fixture-body"')
        self.command(':'); self.command(':')
        self.assertFalse((self.home/'captures').exists())
        rows, note = self.capture(); self.assertIsNotNone(rows, note)
        self.assertEqual((self.home/'captures').read_text().splitlines(), ['called'])
        self.assertNotIn('private-fixture-body', json.dumps(rows))


@unittest.skipIf(os.name == 'nt', 'Unix sockets required')
class Transport(unittest.TestCase):
    def test_stale_and_unsafe_endpoints_are_ignored(self):
        with tempfile.TemporaryDirectory(prefix='dk-') as tmp:
            root=Path(tmp)
            stale=root/'12345-7-999999999-1';stale.mkdir(mode=0o700)
            self.assertEqual(bridge.candidates(root,'12345','%7'), [])
            live=root/f'12345-7-{os.getpid()}-2';live.mkdir(mode=0o700)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                server.bind(str(live/'s'));(live/'s').chmod(0o600)
                self.assertEqual(bridge.candidates(root,'12345','%7'), [live/'s'])
                live.chmod(0o755)
                self.assertEqual(bridge.candidates(root,'12345','%7'), [])
                live.chmod(0o700)
                (live/'s').rename(live/'real-socket');(live/'s').symlink_to(live/'real-socket')
                self.assertEqual(bridge.candidates(root,'12345','%7'), [])
                root.chmod(0o755)
                self.assertEqual(bridge.candidates(root,'12345','%7'), [])

    def response(self, reply, delay=0):
        with tempfile.TemporaryDirectory(prefix='dk-') as tmp:
            path = Path(tmp) / 's'
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(path)); server.listen(1)
                def respond():
                    conn, _ = server.accept()
                    with conn:
                        conn.recv(4096)
                        time.sleep(delay)
                        try: conn.sendall(reply)
                        except OSError: pass
                worker = threading.Thread(target=respond); worker.start()
                try:
                    return bridge.receive(path, b'fixture', time.monotonic() + .15)
                finally: worker.join(timeout=2)

    def test_framing_payload_limits_and_other_shell_refusal(self):
        valid = b'zsh\0viins\0bindkey -M viins "^H" backward-delete-char\n\0'
        frame = lambda raw: bridge.MAGIC + struct.pack('!I', len(raw)) + raw
        self.assertEqual(self.response(frame(valid))[0]['action'], 'backward-delete-char')
        for data in (b'wrong', frame(valid)[:-1], frame(valid)+b'extra', frame(b'invalid'),
                     frame(b'bash\0main\0"x": backward-char\n\0'),
                     bridge.MAGIC + struct.pack('!I', bridge.LIMIT + 1)):
            with self.subTest(data=data[:30]): self.assertIsNone(self.response(data))
        self.assertIsNone(self.response(frame(valid), .3))

    def test_worker_deadline_and_identity(self):
        script = ROOT / 'lib/dots/keys/zsh_bridge.py'
        expected = bridge.MAGIC + b'/fixture/socket,12345\0%7\0'
        for request in (b'wrong', b'', expected):
            with self.subTest(request=request):
                sender, client = socket.socketpair()
                temp = tempfile.TemporaryDirectory(prefix='dk-')
                env = dict(HOME=temp.name, ZDOTDIR=temp.name, TMPDIR=temp.name, PATH=os.environ['PATH'])
                for key in ('LD_PRELOAD', 'PREFIX'):
                    if key in os.environ: env[key] = os.environ[key]
                worker = subprocess.Popen([sys.executable, '-B', str(script), 'serve', str(sender.fileno()),
                                           '/fixture/socket,12345', '%7'], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          pass_fds=(sender.fileno(),), env=env, cwd=temp.name)
                sender.close()
                try:
                    start = time.monotonic()
                    if request: client.sendall(request)
                    # Leave stdin open: a valid peer cannot keep a worker alive
                    # indefinitely by withholding its snapshot producer's EOF.
                    worker.wait(timeout=3)
                    self.assertLess(time.monotonic()-start, 2.8)
                    self.assertEqual(worker.stdout.read(), b'')
                    self.assertEqual(worker.stderr.read(), b'')
                finally:
                    client.close()
                    if worker.poll() is None: worker.kill(); worker.wait()
                    worker.stdin.close(); worker.stdout.close(); worker.stderr.close()
                    temp.cleanup()

    def test_controller_priority_source_filter_and_visible_coverage(self):
        import keys_cli
        from keys.model import record
        live = [record('zsh', 'viins', '^X^G', 'fixture-action', evidence='live')]
        document = dict(version=1, rows=[], coverage=[dict(app='zsh', count=0, live=False, notes=[])])
        with patch.dict(os.environ, {'DOTS_KEYS_TARGET_PANE':'%7'}, clear=True), \
             patch('keys.zsh_bridge.capture', return_value=(live, 'Captured Zsh keymaps from tmux pane %7.')) as capture, \
             patch('keys_cli.collect', return_value=document) as collect, patch('sys.stdout', io.StringIO()):
            keys_cli.main(['zsh', '--json'])
            self.assertEqual(collect.call_args.args[2], live)
            self.assertEqual(collect.call_args.args[3], {'zsh'})
            capture.reset_mock()
            keys_cli.main(['zsh', '--source', 'configured', '--json']); capture.assert_not_called()
            raw = io.TextIOWrapper(io.BytesIO(b'zsh\0viins\0bindkey -M viins "^G" caller-widget\n\0'))
            with patch.dict(os.environ, {'DOTS_KEYS_CAPTURE':'shell'}), patch('sys.stdin', raw):
                keys_cli.main(['zsh', '--json']); capture.assert_not_called()
                self.assertEqual(collect.call_args.args[2][0]['action'], 'caller-widget')
        for width in (40, 80, 120):
            for active in (False, True):
                doc = dict(coverage=[dict(app='zsh', live=active)])
                header = keys_cli.binding_header()
                self.assertNotIn('Zsh:', header)
                self.assertNotIn('Mode:', header)
                self.assertIn('Alt-M: mode', header)
                self.assertTrue(all(len(line) <= width for line in header.splitlines()))


if __name__ == '__main__': unittest.main(verbosity=2)
