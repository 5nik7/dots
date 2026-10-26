#!/usr/bin/env python3
"""Session menu data, routing and private native server/client behavior."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch

from test_menus import MenuFixture, NativeMenuFixture, ROOT
import menu_sessions as sessions
from interaction import SelectionEnded, SelectionEvent
from menu_projects import Row
from menu_tmux import TmuxContext, request_file
from dataclasses import asdict


class SessionContracts(MenuFixture):
    def setUp(self):
        super().setUp()
        self.record = sessions.Session('$12', '-café\t$(touch sentinel);\n', 3, 2, True, 123)
        self.server = sessions.Server('/fixture/tmux', '/fixture/socket', 456)
        patch('menu_projects.discover', return_value=()).start()
        patch('menu_projects.inventory', side_effect=lambda server, items, projects: tuple(Row(s.id, s.name, sessions=(s,)) for s in items)).start()

    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = sessions.main(list(args))
        return code, output.getvalue(), error.getvalue()

    def test_data_modes_filter_typed_records_without_selection(self):
        server = Mock(); server.sessions.return_value = (self.record,)
        with patch.object(sessions.Server, 'discover', return_value=server), \
                patch('menus.shutil.which', side_effect=AssertionError('FZF probe')), \
                patch.object(sessions.TmuxContext, 'capture', side_effect=AssertionError('client capture')), \
                patch('menu_sessions.terminal', return_value=False):
            for flags in ([], ['--print'], ['--json']):
                code, out, err = self.invoke(*flags)
                self.assertEqual((code, err), (0, '')); self.assertNotIn('\x1b', out)
                if flags == ['--json']:
                    doc = json.loads(out)
                    self.assertEqual(doc, dict(schema=1, menu='tmux-sessions', title='Tmux sessions', items=[self.record.document()]))
                    self.assertIs(type(doc['items'][0]['current']), bool)
                    self.assertIs(type(doc['items'][0]['windows']), int)
                else:
                    self.assertIn('current', out); self.assertIn('3 windows', out)
            self.assertEqual(json.loads(self.invoke('--json', '--query', 'missing')[1])['items'], [])
        server.select.assert_not_called()

    def test_empty_server_and_inventory_succeed_without_terminal(self):
        for server in (None, Mock(sessions=Mock(return_value=()))):
            with patch.object(sessions.Server, 'discover', return_value=server), patch('menu_sessions.terminal', return_value=False):
                self.assertEqual(self.invoke('--print')[0], 0)
                self.assertEqual(json.loads(self.invoke('--json')[1])['items'], [])

    def test_windows_and_missing_tmux_refuse_without_wsl_or_fzf(self):
        with patch('menu_sessions.native_windows', return_value=True), patch('subprocess.run', side_effect=AssertionError), patch('shutil.which', side_effect=AssertionError):
            code, out, err = self.invoke('--json')
        self.assertEqual((code, out), (2, '')); self.assertIn('native Windows', err)
        with patch('menu_sessions.native_windows', return_value=False), patch('shutil.which', return_value=None):
            self.assertIn('tmux is unavailable', self.invoke('--print')[2])

    def test_absent_server_is_distinct_from_permission_and_command_failures(self):
        for error, empty in [('no server running on /fixture/socket\n', True),
                             ('error connecting to /fixture/socket (No such file or directory)\n', True),
                             ('error connecting to /fixture/socket (Permission denied)\n', False),
                             ('server exited unexpectedly\n', False)]:
            with patch('menu_sessions.observe', return_value=subprocess.CompletedProcess([], 1, '', error)), patch('shutil.which', return_value='/fixture/tmux'):
                code, out, err = self.invoke('--json')
                self.assertEqual(code, 0 if empty else 2)
                if empty: self.assertEqual(json.loads(out)['items'], [])
                else: self.assertIn(error.strip(), err)

    def test_cancel_failure_and_missing_fzf_never_switch(self):
        server = Mock(); server.sessions.return_value = (self.record,)
        with patch.object(sessions.Server, 'discover', return_value=server), patch('menu_sessions.terminal', return_value=True), patch('menus.terminal', return_value=True), patch('menu_session_ui.terminal', return_value=True):
            for failure in (SelectionEnded(130), SelectionEnded(2)):
                with patch('menu_session_ui.pick', side_effect=failure):
                    self.assertEqual(self.invoke('--browse')[0], failure.status)
            with patch('menus.shutil.which', return_value=None):
                code, out, err = self.invoke('--browse')
                self.assertEqual(code, 0); self.assertIn('FZF unavailable', err)
                self.assertIn('café', out)
        server.select.assert_not_called()

    def test_server_restart_and_stale_id_refuse_without_action(self):
        for values in (['999\n'], ['456\n', '$13\t123\n'], ['456\n', '$12\t999\n']):
            with patch.object(sessions.Server, 'read', side_effect=values), patch('subprocess.call', side_effect=AssertionError('attach')):
                with self.assertRaisesRegex(ValueError, 'changed'): self.server.select(self.record)

    def test_attach_literal_id_and_status_no_detach(self):
        with patch.object(sessions.Server, 'read', side_effect=['456\n', '$12\t123\n']), patch('menu_sessions.terminal', return_value=True), patch('subprocess.call', return_value=7) as call:
            self.assertEqual(self.server.select(self.record), 7)
        self.assertEqual(call.call_args.args[0], ['/fixture/tmux', '-u', '-N', '-S', '/fixture/socket', 'attach-session', '-t', '$12'])

    def test_inherited_context_consumed_and_client_mismatch_refused(self):
        server = Mock(); server.sessions.return_value = (self.record,)
        context = TmuxContext('/fixture/tmux', '/fixture/socket', '/dev/pts/one', 12, '%1', '$1', str(self.home))
        server.select.return_value = 0
        with request_file(dict(schema=1, context=asdict(context))) as path, patch.dict(os.environ, DOTS_MENU_CONTEXT=str(path)), \
                patch.object(sessions.Server, 'discover', return_value=server), patch.object(TmuxContext, 'verify', return_value=(80, 24)), \
                patch('menu_session_ui.pick', return_value=Row(self.record.id, self.record.name, sessions=(self.record,))):
            self.assertEqual(self.invoke('--browse')[0], 0)
            server.select.assert_called_once_with(self.record, context)
            self.assertIn('differs', self.invoke('--browse', '--client', 'wrong')[2])

    def test_help_and_both_frontend_metadata_completion_do_not_execute(self):
        tools = self.base / 'tools'; tools.mkdir()
        marker = self.base / 'unexpected'
        for tool in ('tmux', 'fzf'):
            path = tools / tool
            path.write_text('#!' + shutil.which('bash') + '\n: > "' + str(marker) + '"\nexit 99\n'); path.chmod(0o700)
        env = dict(self.env, DOTS=str(ROOT), PATH=str(tools) + os.pathsep + self.env['PATH'])
        fronts = [[str(ROOT / 'bin/dots')], [sys.executable, '-B', str(ROOT / 'lib/dots/cli.py')]]
        for front in fronts:
            p = subprocess.run([*front, 'menu', 'tmux', 'sessions', '--help'], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(p.returncode, 0, p.stderr); self.assertIn('--client', p.stdout)
            for option in ('--client', '--query', '--json', '--print', '--browse'):
                completion = ['__complete', 'bash', '4', '--', 'dots'] if len(front) == 1 else ['__complete']
                p = subprocess.run([*front, *completion, 'menu', 'tmux', 'sessions', option[:4]], env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(p.returncode, 0, p.stderr); self.assertIn(option, p.stdout)
        self.assertFalse(marker.exists())


class NativeSessions(NativeMenuFixture):
    def seed(self, name):
        return self.control('new-session', '-d', '-P', '-F', '#{session_id}', '-s', name, shutil.which('bash'), '--noprofile', '--norc').strip()

    def picker(self, query='', client=True):
        code = "import os,sys; from menu_sessions import main; sys.exit(main(['--browse','--query',os.environ['QUERY']] + (['--client',os.environ['CLIENT']] if os.environ['EXPLICIT']=='yes' else [])))"
        return self.worker(code, QUERY=query, EXPLICIT='yes' if client else 'no')

    def test_inventory_names_counts_current_and_both_dispatchers(self):
        # tmux rejects control characters in session names;
        # the portable data contract above still treats these as inert strings.
        strange = '-日本語 $(touch sentinel);literal'
        ident = self.seed(strange)
        for front in ([str(ROOT / 'bin/dots')], [sys.executable, '-B', str(ROOT / 'lib/dots/cli.py')]):
            p = subprocess.run([*front, 'menu', 'tmux', 'sessions', '--json'], env=dict(os.environ, DOTS=str(ROOT)), capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
            items = json.loads(p.stdout)['items']; item = next(s for s in items if s['id'] == ident)
            self.assertEqual((item['name'], item['windows'], item['attached_clients'], item['current']), (strange, 1, 0, False))
            self.assertEqual([(s['label'], s['attached_clients']) for s in items if s['current']], [('fixture', 2)])
        self.assertFalse((self.home / 'sentinel').exists())

    def test_popup_switches_only_explicit_client_using_id(self):
        ident = self.seed('Work'); self.seed('Work-long')
        p = self.picker('^Work !Work-long')
        self.receive(self.first[1], b'dots'); self.assertNotIn(b'dots', self.drain(self.second[1]))
        time.sleep(.3); os.write(self.first[1], b'\r')
        out, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 0, err)
        rows = self.control('list-clients', '-F', '#{client_name}\t#{session_id}').splitlines()
        self.assertTrue(all(len(row.split('\t')) == 2 for row in rows), repr(rows))
        clients = dict(row.split('\t') for row in rows)
        self.assertEqual(clients[self.first[2]], ident); self.assertEqual(clients[self.second[2]], '$0')

    def test_current_selection_is_noop_and_ambiguous_client_refuses(self):
        p = self.picker('fixture'); self.receive(self.first[1], b'dots'); os.write(self.first[1], b'\r')
        out, err = p.communicate(timeout=15); self.assertEqual(p.returncode, 0, err)
        self.assertEqual(self.control('list-clients', '-F', '#{session_id}').splitlines(), ['$0', '$0'])
        p = self.picker(client=False); out, err = p.communicate(timeout=10)
        self.assertEqual(p.returncode, 2); self.assertIn('ambiguous', err)

    def test_escape_and_ctrl_c_preserve_130(self):
        for key in (b'\x1b', b'\x03'):
            p = self.picker(); self.receive(self.first[1], b'dots'); os.write(self.first[1], key)
            out, err = p.communicate(timeout=15); self.assertEqual(p.returncode, 130, err)
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_vanished_session_and_client_refuse(self):
        ident = self.seed('temporary')
        server = sessions.Server.discover(); record = next(s for s in server.sessions() if s.id == ident)
        context = TmuxContext.capture(client=self.first[2])
        self.control('kill-session', '-t', ident)
        with self.assertRaises(ValueError): server.select(record, context)
        record = server.sessions()[0]
        self.control('detach-client', '-t', self.first[2])
        with self.assertRaisesRegex(ValueError, 'changed'): server.select(record, context)


class ExternalSessions(MenuFixture):
    def setUp(self):
        super().setUp()
        if os.name == 'nt' or not shutil.which('tmux') or not shutil.which('fzf'):
            self.skipTest('native POSIX tmux/FZF unavailable')
        self.tmux = shutil.which('tmux')
        self.runtime = self.base / 'runtime'; self.runtime.mkdir(mode=0o700)
        os.environ['TMUX_TMPDIR'] = str(self.runtime)
        self.socket = self.runtime / ('tmux-' + str(os.getuid())) / 'default'
        self.socket.parent.mkdir(mode=0o700)
        self.children = []
        self.addCleanup(self.cleanup_server)

    def control(self, *args):
        p = subprocess.run([self.tmux, '-u', '-S', str(self.socket), '-f', os.devnull, *args], capture_output=True, text=True, timeout=5)
        self.assertEqual(p.returncode, 0, p.stderr); return p.stdout

    def cleanup_server(self):
        import signal
        subprocess.run([self.tmux, '-N', '-S', str(self.socket), 'kill-server'], capture_output=True, timeout=5)
        for pid, master in self.children:
            try: os.kill(pid, signal.SIGTERM)
            except ProcessLookupError: pass
            os.waitpid(pid, 0); os.close(master)

    def test_no_server_is_empty_and_does_not_start_one(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(sessions.main(['--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['items'], [])
        self.assertFalse(self.socket.exists())

    def test_explicit_creation_can_start_owned_default_server(self):
        server, session = sessions.create_session(None, 'first-explicit', str(self.home))
        self.assertEqual(server.socket, str(self.socket))
        self.assertEqual(session.name, 'first-explicit')
        self.assertEqual(server.read('display-message', '-p', '-t', session.id, '#{session_path}').strip(), str(self.home))

    def test_managed_creation_on_cold_server_preserves_literal_project(self):
        project = self.home / '-café #{literal};'; project.mkdir()
        subprocess.run(['git', 'init', '-q', str(project)], check=True)
        server, session = sessions.create_session(None, None, str(project))
        self.assertTrue(session.name.startswith(project.name + '-'), session.name)
        self.assertRegex(session.name.rsplit('-', 1)[1], r'^[0-9a-f]{12}$')
        self.assertEqual(server.read('display-message', '-p', '-t', session.id, '#{pane_current_path}').strip(), str(project))
        from tmux_workspaces import Workspaces
        data = Workspaces(server.executable, server.socket).metadata(session.id)
        self.assertTrue(data['auto'])
        self.assertEqual(data['projects'], [str(project)])

    def test_running_server_without_sessions_is_empty(self):
        self.control('new-session', '-d', '-s', 'temporary', shutil.which('bash'), '--noprofile', '--norc')
        self.control('set-option', '-s', 'exit-empty', 'off')
        self.control('kill-session', '-t', 'temporary')
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(sessions.main(['--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['items'], [])

    def test_external_tty_selects_and_attaches_to_pinned_default_server(self):
        import pty, fcntl, termios, struct
        self.control('new-session', '-d', '-s', '-café;literal', shutil.which('bash'), '--noprofile', '--norc')
        self.control('set-option', '-g', 'status', 'off')
        # Keep a separate client attached while the menu attaches another.
        other_pid, other_master = pty.fork()
        if other_pid == 0:
            os.execve(self.tmux, [self.tmux, '-u', '-S', str(self.socket), 'attach-session', '-t', '$0'], dict(os.environ))
        self.children.append((other_pid, other_master))
        deadline = time.monotonic() + 5; existing = ''
        while time.monotonic() < deadline:
            NativeMenuFixture.drain(self, other_master)
            existing = self.control('list-clients', '-F', '#{client_name}').strip()
            if existing: break
            time.sleep(.05)
        self.assertTrue(existing)
        pid, master = pty.fork()
        if pid == 0:
            os.execve(sys.executable, [sys.executable, '-B', str(ROOT / 'lib/dots/menu_sessions.py'), '--browse'], dict(os.environ))
        self.children.append((pid, master))
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 100, 0, 0))
        NativeMenuFixture.receive(self, master, b'dots')
        os.write(master, b'\r')
        deadline = time.monotonic() + 10; clients = ''
        while time.monotonic() < deadline:
            NativeMenuFixture.drain(self, master)
            clients = self.control('list-clients', '-F', '#{client_name}\t#{session_id}').splitlines()
            if len(clients) == 2: break
            time.sleep(.05)
        self.assertEqual(len(clients), 2)
        targets = dict(row.split('\t') for row in clients)
        self.assertEqual(targets.pop(existing), '$0')
        client, ident = next(iter(targets.items())); self.assertEqual(ident, '$0')
        self.control('detach-client', '-t', client)
        _, result = os.waitpid(pid, 0); self.children.remove((pid, master)); os.close(master)
        self.assertEqual(os.waitstatus_to_exitcode(result), 0)
        self.assertEqual(self.control('list-clients', '-F', '#{client_name}').strip(), existing)

    def test_replaced_server_cannot_reuse_a_selected_id(self):
        self.control('new-session', '-d', '-s', 'original', shutil.which('bash'), '--noprofile', '--norc')
        original = sessions.Server.discover(); selected = original.sessions()[0]
        self.control('kill-server')
        self.control('new-session', '-d', '-s', 'replacement', shutil.which('bash'), '--noprofile', '--norc')
        replacement = sessions.Server.discover()
        self.assertNotEqual(original.pid, replacement.pid)
        self.assertEqual(replacement.sessions()[0].id, selected.id)
        with self.assertRaisesRegex(ValueError, 'server changed'): original.select(selected)
        self.assertEqual(self.control('list-clients'), '')

    drain = NativeMenuFixture.drain


if __name__ == '__main__':
    unittest.main()
