#!/usr/bin/env python3
"""Owned notification queues, inert Android tools and private tmux consumers."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import test_codex_status as codex
import configure_codex_notifications as setup

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('alerts', ROOT / 'config/tmux/codex-alerts.py')
alerts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(alerts)
THREAD = '00000000-0000-4000-a000-000000000001'
OTHER = '00000000-0000-4000-a000-000000000002'


def event(kind='PreToolUse', request='request-1', **extra):
    return dict(session_id=THREAD, turn_id='turn-1', hook_event_name=kind,
                tool_name='request_user_input', tool_use_id=request,
                tool_input={'questions': [{'question': 'Which option?', 'options': []}]}, **extra)


def complete(thread=THREAD, turn='turn-1', message='Finished the work.'):
    return {'type': 'agent-turn-complete', 'thread-id': thread, 'turn-id': turn, 'last-assistant-message': message}


class Portable(unittest.TestCase):
    def test_observational_event_shapes_and_toml_preservation(self):
        prefs = alerts.preferences()
        self.assertEqual(alerts.normalize(complete(), prefs)['kind'], 'complete')
        self.assertEqual(alerts.normalize(event(), prefs)['kind'], 'choice')
        self.assertIsNone(alerts.normalize({'type': 'agent-turn-failed', 'thread-id': THREAD}, prefs))
        self.assertIsNone(alerts.normalize(event() | {'session_id': '../bad'}, prefs))
        original = '# user comment\n[tui]\nstatus_line = ["model"]\nterminal_title = ["thread-id", "project-name"]\n'
        changed = setup.merge_config(original, ['python', 'bridge.py', 'notify'])
        self.assertIn('# user comment', changed)
        self.assertIn('status_line = ["model"]', changed)
        parsed = setup.tomllib.loads(changed)
        self.assertEqual(parsed['tui']['terminal_title'][-1], 'thread-id')
        self.assertTrue(parsed['features']['hooks'])


@unittest.skipIf(os.name == 'nt', 'private runtime queue is a Unix/tmux adapter')
class Queue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-alert-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home space ü'
        self.home.mkdir()
        self.env = {key: os.environ[key] for key in ('PATH', 'PREFIX', 'LD_PRELOAD', 'LD_LIBRARY_PATH') if key in os.environ}
        self.env.update(HOME=str(self.home), CODEX_HOME=str(self.home / '.codex'),
                        XDG_STATE_HOME=str(self.root / 'state'), XDG_CONFIG_HOME=str(self.root / 'config'),
                        XDG_CACHE_HOME=str(self.root / 'cache'), XDG_DATA_HOME=str(self.root / 'data'),
                        XDG_RUNTIME_DIR=str(self.root / 'run'), TERMUX_VERSION='fixture')
        self.environment = patch.dict(os.environ, self.env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.prefs = alerts.preferences()

    def panes(self, focused=False, state='waiting', socket='socket-a', thread=THREAD, window='@2', pane='%2'):
        with alerts.database() as db:
            db.execute('INSERT OR REPLACE INTO sockets VALUES (?,?,?)', (socket, '/unused/' + socket, time.time()))
            db.execute('INSERT OR REPLACE INTO panes VALUES (?,?,?,?,?,?)', (socket, pane, window, thread, state, focused))

    def run_events(self, deliver=True):
        with alerts.database() as db:
            return alerts.reconcile(db, self.prefs, time.time(), deliver)[0]

    def phases(self):
        with alerts.database() as db:
            return [dict(row) for row in db.execute('SELECT * FROM events ORDER BY created,id')]

    def test_choice_focus_ack_reload_dedup_and_erasure(self):
        alerts.record(event(), self.prefs)
        self.panes()
        self.assertEqual(self.run_events(), ['Codex needs input: Which option?'])
        self.assertEqual(self.phases()[0]['message'], '')
        self.assertEqual(self.phases()[0]['phase'], 'alert')
        alerts.record(event(), self.prefs)
        self.assertEqual(self.run_events(), [])
        self.panes(focused=True)
        self.assertEqual(self.run_events(deliver=False), [])
        self.assertEqual(self.phases()[0]['phase'], 'ack')
        self.panes()
        self.assertEqual(self.run_events(), [])
        alerts.record(event(request='request-2'), self.prefs)
        self.assertEqual(len(self.run_events()), 1)

    def test_focused_events_never_alert_when_later_unfocused(self):
        self.panes(focused=True)
        for payload in (event(), complete()):
            alerts.record(payload, self.prefs)
        self.assertEqual(self.run_events(), [])
        self.panes()
        self.assertEqual(self.run_events(), [])
        self.assertTrue(all(row['phase'] == 'ack' for row in self.phases()))

    def test_completion_is_event_not_idle_and_new_prompt_clears(self):
        self.panes(state='idle')
        self.assertEqual(self.run_events(), [])
        alerts.record(complete(), self.prefs)
        self.assertEqual(self.run_events(), ['Codex finished: Finished the work.'])
        alerts.record(event('UserPromptSubmit'), self.prefs)
        self.assertEqual(self.phases()[0]['phase'], 'ack')
        alerts.record(event('UserPromptSubmit') | {'turn_id': 'turn-2'}, self.prefs)
        alerts.record(complete(), self.prefs)
        self.assertEqual(self.run_events(), [])
        alerts.record(complete(turn='turn-2'), self.prefs)
        self.assertEqual(len(self.run_events()), 1)

    def test_approval_must_reach_waiting_and_resolution_clears(self):
        payload = event('PermissionRequest') | {'tool_name': 'Bash', 'tool_input': {'description': 'Allow the command?'}}
        alerts.record(payload, self.prefs)
        self.panes(state='working')
        self.assertEqual(self.run_events(), [])
        self.panes(state='waiting')
        self.assertEqual(self.run_events(), ['Codex needs approval: Allow the command?'])
        self.panes(state='working')
        self.assertEqual(self.run_events(), [])
        self.assertEqual(self.phases()[0]['phase'], 'ack')

    def test_auto_approval_cannot_alert_for_a_later_choice(self):
        payload = event('PermissionRequest') | {'tool_name': 'Bash', 'tool_input': {'command': 'true', 'description': 'Run?'}}
        alerts.record(payload, self.prefs)
        self.panes(state='working')
        self.assertEqual(self.run_events(), [])
        alerts.record(payload | {'hook_event_name': 'PostToolUse', 'tool_input': {'command': 'true'}}, self.prefs)
        alerts.record(event(), self.prefs)
        self.panes(state='waiting')
        self.assertEqual(self.run_events(), ['Codex needs input: Which option?'])

    def test_repeated_identical_approval_after_resolution_is_new_event(self):
        payload = event('PermissionRequest') | {'tool_name': 'Bash', 'tool_input': {'command': 'true', 'description': 'Run?'}}
        self.panes()
        alerts.record(payload, self.prefs)
        self.assertEqual(len(self.run_events()), 1)
        alerts.record(payload, self.prefs)
        self.assertEqual(self.run_events(), [])
        alerts.record(payload | {'hook_event_name': 'PostToolUse'}, self.prefs)
        alerts.record(payload, self.prefs)
        self.assertEqual(len(self.run_events()), 1)

    def test_focus_at_receipt_is_acknowledged_even_before_worker_tick(self):
        self.panes()
        with patch.object(alerts, 'snapshot', return_value=[{'thread': THREAD, 'focused': True}]):
            alerts.record(complete(), self.prefs)
        self.assertEqual(self.phases()[0]['phase'], 'ack')
        self.assertEqual(self.run_events(), [])

    def test_async_acceptance_is_not_answer_and_same_pane_waiting_wins(self):
        payload = event() | {'tool_name': 'functions.request_user_input_async',
                             'tool_input': {'questions': [{'title': 'A or B?'}]}}
        alerts.record(payload, self.prefs)
        alerts.record(payload | {'hook_event_name': 'PostToolUse'}, self.prefs)
        self.panes(state='waiting')
        self.assertEqual(self.run_events(), ['Codex needs input: A or B?'])
        rows = alerts.parse_inventory(f'@2 %2 123 1 1 {THREAD}\n'.encode())
        self.assertEqual(rows[0]['state'], 'waiting')

    def test_multiple_panes_sockets_one_delivery_and_shared_focus(self):
        self.panes()
        self.panes(socket='socket-b', pane='%3', window='@8')
        self.panes(socket='socket-a', pane='%4', window='@2', thread=OTHER, state='working')
        alerts.record(event(), self.prefs)
        self.assertEqual(len(self.run_events()), 1)
        for key in ('socket-a', 'socket-b'):
            self.assertTrue(json.loads((alerts.status.alert_root() / (key + '.json')).read_text())['windows'])
        self.panes(socket='socket-b', pane='%3', window='@8', focused=True)
        self.assertEqual(self.run_events(False), [])
        self.assertEqual(self.phases()[0]['phase'], 'ack')
        self.assertEqual(json.loads((alerts.status.alert_root() / 'socket-a.json').read_text())['windows'], [])

    def test_cancel_answer_exit_and_unmatched_expiry(self):
        self.panes()
        alerts.record(event(), self.prefs)
        alerts.record(event('PostToolUse'), self.prefs)
        self.assertEqual(self.run_events(), [])
        alerts.record(event('Interrupt'), self.prefs)
        alerts.record(complete(), self.prefs)
        self.assertEqual(self.run_events(), [])
        self.assertEqual(len(self.phases()), 1)
        alerts.record(event('UserPromptSubmit') | {'turn_id': 'turn-2'}, self.prefs)
        alerts.record(complete(turn='turn-2'), self.prefs)
        self.run_events()
        with alerts.database() as db:
            db.execute('DELETE FROM panes')
        self.run_events()
        self.assertTrue(all(row['phase'] == 'ack' for row in self.phases()))
        alerts.record(complete(thread=OTHER), self.prefs)
        with alerts.database() as db:
            alerts.reconcile(db, self.prefs, time.time() + 601)
        self.assertTrue(all(row['message'] == '' for row in self.phases()))

    def test_notification_arguments_palette_message_and_failure(self):
        binary = self.root / 'bin'
        binary.mkdir()
        log = self.root / 'calls'
        for name in ('termux-toast', 'termux-vibrate'):
            script = binary / name
            script.write_text('#!' + sys.executable + '\nimport json,sys\n'
                              f'with open({str(log)!r}, "a") as out: out.write(json.dumps(sys.argv[1:])+"\\n")\n'
                              + ('sys.exit(1)\n' if name.endswith('vibrate') else ''))
            script.chmod(0o700)
        os.environ['PATH'] = str(binary) + os.pathsep + os.environ['PATH']
        palette = Path(self.env['XDG_STATE_HOME']) / 'dots/current/theme/palette.json'
        palette.parent.mkdir(parents=True)
        palette.write_text(json.dumps({'colors': {'dark_background': '#123456', 'warning': '#abcdef'}}))
        message = alerts.excerpt('choice', '\x1b[31mWhich\noption? $(touch NEVER) #{x}\x00', 240)
        alerts.notify_device(message, self.prefs)
        calls = [json.loads(row) for row in log.read_text().splitlines()]
        self.assertEqual(calls, [['-d', '300', '-f'],
                                ['-b', '#123456', '-c', '#abcdef', '-g', 'middle', '-s', '--', message]])
        self.assertNotIn('\x1b', message)
        self.assertNotIn('\n', message)
        self.assertFalse((self.home / 'NEVER').exists())
        self.assertEqual(len(alerts.excerpt('complete', 'ü' * 300, 240)), 240)
        palette.write_text('{"colors": {"warning": "#bad"}}')
        self.assertEqual(alerts.colors(self.prefs), ('#000000', '#ffff00'))
        del os.environ['TERMUX_VERSION']
        alerts.notify_device('not Android', self.prefs)
        self.assertEqual(len(log.read_text().splitlines()), 2)

    def test_bounded_subprocess_and_unsafe_runtime(self):
        start = time.monotonic()
        with self.assertRaises((TimeoutError, subprocess.SubprocessError)):
            alerts.bounded([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=.05)
        self.assertLess(time.monotonic() - start, 1)
        with self.assertRaises(ValueError):
            alerts.bounded([sys.executable, '-c', 'print("x"*200000)'])
        root = alerts.status.alert_root()
        root.parent.mkdir(parents=True)
        root.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(ValueError), alerts.database():
            pass

    def test_setup_preview_preserves_config_hooks_notify_and_undo(self):
        home = Path(self.env['CODEX_HOME'])
        home.mkdir()
        original = '# preserved\nmodel = "private-model"\nnotify = ["old-notifier", "--flag"]\n[tui]\nstatus_line = ["model"]\n'
        (home / 'config.toml').write_text(original)
        original_hooks = {'hooks': {'PermissionRequest': [{'hooks': [{'type': 'command', 'command': 'my-existing-hook'}]}]}}
        (home / 'hooks.json').write_text(json.dumps(original_hooks))
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        operations, guards = setup.plan(home)
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))
        self.assertEqual((home / 'config.toml').read_text(), original)
        store = setup.Store(Path(self.env['XDG_STATE_HOME']) / 'dots')
        result = store.apply('codex-notifications-setup', operations, guards, retain=True)
        text = (home / 'config.toml').read_text()
        self.assertIn('# preserved', text)
        self.assertIn('model = "private-model"', text)
        marker = json.loads((home / 'dots-notifications.json').read_text())
        self.assertEqual(marker['previous_notify'], ['old-notifier', '--flag'])
        handlers = json.loads((home / 'hooks.json').read_text())['hooks']['PermissionRequest']
        self.assertEqual(handlers[0], original_hooks['hooks']['PermissionRequest'][0])
        self.assertEqual(setup.plan(home)[0], [])
        ops, undo_guards, catalogs = store.inverse(result['id'])
        store.apply('codex-notifications-undo', ops, undo_guards, retain=True, catalogs=catalogs)
        self.assertEqual((home / 'config.toml').read_text(), original)
        self.assertFalse((home / 'dots-notifications.json').exists())

    def test_setup_guards_drift_and_linked_configs(self):
        home = Path(self.env['CODEX_HOME'])
        home.mkdir()
        config = home / 'config.toml'
        config.write_text('model = "first"\n')
        operations, guards = setup.plan(home)
        config.write_text('model = "changed"\n')
        store = setup.Store(Path(self.env['XDG_STATE_HOME']) / 'dots')
        with self.assertRaises(ValueError):
            store.apply('codex-notifications-setup', operations, guards, retain=True)
        self.assertFalse((home / 'hooks.json').exists())
        config.unlink()
        config.symlink_to(self.home / 'missing')
        with self.assertRaises(ValueError):
            setup.plan(home)

    def test_hook_cli_is_silent_and_existing_notify_survives_queue_failure(self):
        home = Path(self.env['CODEX_HOME'])
        home.mkdir()
        log = self.root / 'forwarded'
        previous = self.root / 'previous.py'
        previous.write_text('import pathlib,sys\n' + f'pathlib.Path({str(log)!r}).write_text(sys.argv[1])\n')
        marker = dict(schema=1, owner='dots-codex-alerts', bridge=str(ROOT / 'config/tmux/codex-alerts.py'),
                      previous_notify=[sys.executable, str(previous)])
        (home / 'dots-notifications.json').write_text(json.dumps(marker))
        root = alerts.status.alert_root()
        root.parent.mkdir(parents=True)
        root.symlink_to(self.home, target_is_directory=True)
        raw = json.dumps(complete())
        run = subprocess.run([sys.executable, '-B', marker['bridge'], 'notify', raw],
                             env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, '', ''))
        self.assertEqual(log.read_text(), raw)
        run = subprocess.run([sys.executable, '-B', marker['bridge'], 'hook'], input='not json',
                             env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, '', ''))


@unittest.skipUnless(codex.status.TMUX and sys.platform in ('linux', 'android'), 'native tmux/procfs required')
class Native(unittest.TestCase):
    setUp = codex.Native.setUp
    command = codex.Native.command
    pid = codex.Native.pid
    view = codex.Native.view
    color = codex.Native.color

    def test_real_inventory_attention_brackets_focus_and_expiry(self):
        pane = self.inner('new-window', '-d', '-P', '-F', '#{pane_id}', '-n', 'agent', self.command('alert'))
        self.pid('alert')
        self.inner('select-pane', '-t', pane, '-T', f'Waiting | Working | {THREAD}')
        self.view()
        self.inner('select-window', '-t', ':0')
        socket = self.base[self.base.index('-S') + 1]
        prefs = alerts.preferences()
        with patch.dict(os.environ, self.env, clear=True), patch.object(alerts, 'notify_device') as device:
            rows = alerts.snapshot(socket)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['thread'], THREAD)
            self.assertEqual(rows[0]['state'], 'waiting')
            self.assertFalse(rows[0]['focused'])
            alerts.record(event(), prefs)
            alerts.tick(socket, prefs)
            device.assert_called_once()
            row = self.color('[1 agent ]', (255, 85, 85))
            for part in ('[', '1', 'agent', '', ']'):
                style = self.fixture.colors_at(row, part)
                self.assertEqual(style['fg'], (255, 85, 85))
                self.assertTrue(self.fixture.bold_at(row, part))
            # Exact interior spaces retain the same alert attributes.
            self.assertTrue(self.fixture.bold_at(row, '1 agent', 1))
            for width in (40, 80, 120):
                self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
                alerts.tick(socket, prefs)
                row = self.color('[1 agent ]', (255, 85, 85))
                self.assertIn('│[1 agent ]', self.fixture.plain(row))
                self.assertNotIn(' [1 agent ] ', self.fixture.plain(row))
            self.inner('select-window', '-t', pane)
            alerts.tick(socket, prefs, deliver=False)
            self.assertEqual(alerts.status.attention(socket, '|@1:waiting|'), '')
            self.inner('select-window', '-t', ':0')
            alerts.tick(socket, prefs)
            device.assert_called_once()
            alerts.atomic_snapshot(alerts.status.socket_key(socket), ['@1'], time.time() - 16)
            self.assertEqual(alerts.status.attention(socket, '|@1:waiting|'), '')
            self.inner('select-pane', '-t', pane, '-T', f'Ready | {THREAD}')
            alerts.record(complete(), prefs)
            alerts.tick(socket, prefs)
            self.color('[1 agent]', (255, 85, 85))
            self.assertEqual(device.call_count, 2)
            session = self.inner('display-message', '-p', '#{session_name}')
            self.inner('rename-window', '-t', pane, session)
            self.color('[1]', (255, 85, 85))

    def test_native_worker_exclusive_lock_callback_and_snapshot(self):
        pane = self.inner('new-window', '-d', '-P', '-F', '#{pane_id}', '-n', 'agent', self.command('worker'))
        self.pid('worker')
        self.inner('select-pane', '-t', pane, '-T', f'Waiting | {THREAD}')
        socket = self.base[self.base.index('-S') + 1]
        env = dict(self.env, CODEX_HOME=str(self.fixture.home / '.codex'), TERMUX_VERSION='fixture')
        home = Path(env['CODEX_HOME'])
        home.mkdir()
        bridge = str(ROOT / 'config/tmux/codex-alerts.py')
        (home / 'dots-notifications.json').write_text(json.dumps(dict(schema=1, owner='dots-codex-alerts', bridge=bridge)))
        calls = self.root / 'android-calls'
        for name in ('termux-toast', 'termux-vibrate'):
            tool = self.fixture.tools / name
            tool.write_text('#!' + sys.executable + '\nimport pathlib\n'
                            + f'with pathlib.Path({str(calls)!r}).open("a") as f:f.write({name!r}+"\\n")\n')
            tool.chmod(0o700)
        hook = subprocess.run([sys.executable, '-B', bridge, 'hook'], input=json.dumps(event()),
                              env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual((hook.returncode, hook.stdout, hook.stderr), (0, '', ''))
        worker = subprocess.Popen([sys.executable, '-B', bridge, 'watch', '--socket', socket], env=env,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def stop():
            worker.terminate()
            worker.wait(timeout=3)
        self.addCleanup(stop)
        deadline = time.monotonic() + 4
        while not calls.exists() or len(calls.read_text().splitlines()) != 2:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.05)
        duplicate = subprocess.run([sys.executable, '-B', bridge, 'watch', '--socket', socket], env=env,
                                   capture_output=True, timeout=3)
        self.assertEqual(duplicate.returncode, 0)
        with patch.dict(os.environ, env, clear=True):
            self.assertIn(':attention|', alerts.status.status(socket))


if __name__ == '__main__':
    unittest.main()
