#!/usr/bin/env python3
"""Owned native attention queues; no Codex hooks, UI or notification delivery."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots'))
import codex_attention as attention
import codex_attention_native as native
SPEC = importlib.util.spec_from_file_location('native_alert_fixture', ROOT/'config/tmux/codex-alerts.py')
alerts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(alerts)
THREAD = '00000000-0000-4000-a000-000000000001'
OTHER = '00000000-0000-4000-a000-000000000002'


def completed(turn='turn-1'):
    return {'type':'agent-turn-complete', 'thread-id':THREAD, 'turn-id':turn,
            'last-assistant-message':'fixture private excerpt must not enter pending output'}


def preferences():
    return alerts.preferences(dict(schema=1, enabled=True, poll_seconds=5,
        unfocused_only=True, clear_on_view=True,
        events=dict(choices=True, approvals=True, completion=True),
        termux=dict(enabled=True, focus_policy='conservative', excerpt_chars=240)))


class Context(unittest.TestCase):
    def test_inherited_terminal_hints_never_prove_a_pane_thread_or_focus(self):
        class Observer:
            def identity(self, pid): return {'pid':pid, 'started':123}
        doc = native.context({'WT_SESSION':THREAD, 'WEZTERM_PANE':'17'}, Observer())
        self.assertEqual(doc['terminal_hints'], {'windows_terminal':True, 'wezterm':True})
        for key in ('pane_identity','thread_identity','focused'): self.assertIsNone(doc[key])
        self.assertFalse(doc['automatic_acknowledgement'])
        self.assertEqual(doc['delivery'], 'none-record-only')
        self.assertNotIn(THREAD, json.dumps(doc))

    @unittest.skipUnless(os.name == 'nt', 'private event inspection requires native Windows')
    def test_shared_exact_event_contract_uses_one_noncreating_queue(self):
        with tempfile.TemporaryDirectory(prefix='dots event contract ') as directory:
            home = Path(directory)
            env = dict(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home/'codex'),
                       XDG_STATE_HOME=str(home/'state'), XDG_CONFIG_HOME=str(home/'config'),
                       XDG_CACHE_HOME=str(home/'cache'), XDG_DATA_HOME=str(home/'data'),
                       LOCALAPPDATA=str(home/'local'), APPDATA=str(home/'roaming'))
            with patch.dict(os.environ, env), patch.object(alerts, 'focused_at_receipt', return_value=False), patch.object(
                    alerts, 'notify_device', side_effect=AssertionError('no delivery during record/inspect/ack')):
                self.assertEqual(alerts.pending(), [])
                self.assertFalse(attention.root().exists())
                alerts.record(completed(), preferences())
                alerts.record(completed(), preferences())
                alerts.record(completed('second'), preferences())
                rows = alerts.pending()
                self.assertEqual(len(rows), 2)
                with self.assertRaises(ValueError): alerts.acknowledge_event(OTHER, rows[0]['id'])
                self.assertTrue(alerts.acknowledge_event(THREAD, rows[0]['id']))
                self.assertFalse(alerts.acknowledge_event(THREAD, rows[0]['id']))
                self.assertEqual([row['id'] for row in alerts.pending()], [rows[1]['id']])

    @unittest.skipIf(os.name == 'nt', 'POSIX refusal boundary')
    def test_posix_private_inspection_refuses_before_sqlite_or_sidecar_changes(self):
        with tempfile.TemporaryDirectory(prefix='dots posix event inspection ') as directory:
            root = Path(directory)/'queue'
            with patch.object(alerts.status, 'alert_root', return_value=root):
                with self.assertRaisesRegex(ValueError, 'native Windows'):
                    alerts.pending()
                self.assertFalse(root.exists())
                root.mkdir(mode=0o700)
                database = root/'events.sqlite3'
                writer = sqlite3.connect(database)
                try:
                    self.assertEqual(writer.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
                    writer.execute('CREATE TABLE fixture (value TEXT)'); writer.commit()
                    before = {path.name:path.read_bytes() for path in root.iterdir()}
                    with patch.object(alerts.sqlite3, 'connect', side_effect=AssertionError('must not open SQLite')):
                        with self.assertRaisesRegex(ValueError, 'native Windows'):
                            alerts.pending()
                        with self.assertRaisesRegex(ValueError, 'native Windows'):
                            alerts.acknowledge_event(THREAD, 'a'*64)
                    self.assertEqual({path.name:path.read_bytes() for path in root.iterdir()}, before)
                finally:
                    writer.close()


@unittest.skipUnless(os.name == 'nt', 'requires actual native Windows handles and ACLs')
class WindowsAttention(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots native attention ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base/'home'; self.home.mkdir()
        self.env = {key: value for key,value in os.environ.items() if key.upper() in
                    ('SYSTEMROOT','SYSTEMDRIVE','WINDIR','COMSPEC','PATHEXT')}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), CODEX_HOME=str(self.home/'codex'),
                        XDG_CONFIG_HOME=str(self.home/'config'), XDG_STATE_HOME=str(self.home/'state'),
                        XDG_CACHE_HOME=str(self.home/'cache'), XDG_DATA_HOME=str(self.home/'data'),
                        APPDATA=str(self.home/'roaming'), LOCALAPPDATA=str(self.home/'local'),
                        PATH='', DOTS=str(ROOT), PYTHONDONTWRITEBYTECODE='1',
                        PYTHONUTF8='1', PYTHONIOENCODING='utf-8', TEMP=str(self.base), TMP=str(self.base))
        self.environment = patch.dict(os.environ, self.env, clear=True)
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.api = native.Windows()

    def marker(self):
        path = Path(self.env['CODEX_HOME'])
        self.api.mkdir(path)
        (path/'dots-notifications.json').write_text(json.dumps(dict(
            schema=1, owner='dots-codex-alerts', bridge=str(ROOT/'config/tmux/codex-alerts.py'),
            previous_notify=[sys.executable,'-c',
                'from pathlib import Path; Path('+repr(str(self.home/'notifier-ran'))+').write_text("bad")'])), encoding='utf-8')

    def command(self, *args, input=None):
        return subprocess.run([sys.executable,'-B',str(ROOT/'config/tmux/codex-alerts.py'),*args],
                              cwd=self.home, env=self.env, input=input, text=True,
                              capture_output=True, encoding='utf-8', timeout=15)

    def test_native_process_creation_identity_and_exit_are_rechecked(self):
        current = self.api.identity(os.getpid())
        self.assertTrue(self.api.matches(current))
        self.assertFalse(self.api.matches(dict(current, started=current['started']+1)))
        child = subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'],
                                 cwd=self.home, env=self.env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            identity = self.api.identity(child.pid)
            self.assertTrue(self.api.matches(identity))
        finally:
            child.terminate(); child.wait(timeout=5)
        self.assertFalse(self.api.matches(identity))

    def test_context_help_and_absent_pending_create_no_state(self):
        before = set(self.home.rglob('*'))
        for args in (('context',), ('pending',), ('--help',)):
            result = self.command(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            if args == ('context',):
                self.assertIsNone(json.loads(result.stdout)['focused'])
            elif args == ('pending',): self.assertEqual(json.loads(result.stdout)['events'], [])
        self.assertEqual(set(self.home.rglob('*')), before)

    def test_native_shared_queue_exact_ack_lifecycle_and_no_delivery(self):
        self.marker()
        self.assertEqual(alerts.installation()['owner'], 'dots-codex-alerts')
        result = self.command('notify', json.dumps(completed()))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0,'',''))
        result = self.command('notify', json.dumps(completed('turn-2')))
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = alerts.pending()
        self.assertEqual(len(rows), 2)
        with alerts.database(read_only=True) as db:
            self.assertEqual([row[0] for row in db.execute('SELECT message FROM events')], ['', ''])
        self.assertNotIn('fixture private excerpt', json.dumps(rows))
        self.assertNotIn('message', rows[0])
        result = self.command('pending')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['events'], rows)
        result = self.command('ack-event', '--thread', OTHER, '--event', rows[0]['id'])
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('fixture private excerpt', result.stderr)
        self.assertEqual(len(alerts.pending()), 2)
        result = self.command('ack-event', '--thread', THREAD, '--event', rows[0]['id'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['changed'])
        self.assertFalse(alerts.acknowledge_event(THREAD, rows[0]['id']))
        self.assertEqual([r['id'] for r in alerts.pending()], [rows[1]['id']])
        with alerts.database(read_only=True) as db:
            self.assertEqual(db.execute('SELECT message FROM events WHERE id=?',(rows[0]['id'],)).fetchone()[0], '')
        alerts.record({'hook_event_name':'Interrupt','session_id':THREAD,'turn_id':'turn-2'}, preferences())
        self.assertEqual(alerts.pending(), [])
        self.assertFalse((self.home/'notifier-ran').exists())

    def test_native_observational_hooks_require_owned_marker(self):
        result = self.command('notify', json.dumps(completed()))
        self.assertEqual((result.returncode,result.stdout,result.stderr), (0,'',''))
        self.assertFalse(attention.root().exists())
        self.marker()
        marker = Path(self.env['CODEX_HOME'])/'dots-notifications.json'
        doc = json.loads(marker.read_text()); doc['owner'] = 'foreign'
        marker.write_text(json.dumps(doc))
        result = self.command('notify', json.dumps(completed()))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(attention.root().exists())

    def test_native_pending_is_noncreating_and_denies_writers_and_sidecars(self):
        alerts.record(completed(), preferences())
        root = attention.root()
        before = {p.name:p.read_bytes() for p in root.iterdir() if p.is_file()}
        self.assertEqual(len(alerts.pending()), 1)
        self.assertEqual({p.name:p.read_bytes() for p in root.iterdir() if p.is_file()}, before)
        with alerts.database() as writer:
            writer.execute("UPDATE events SET message='writer fixture'")
            with self.assertRaises((OSError,ValueError)): alerts.pending()
        (root/'events.sqlite3-wal').write_text('fixture')
        with self.assertRaisesRegex(ValueError, 'busy'): alerts.pending()

    def test_native_pins_block_other_process_replacement_and_writes_without_sqlite(self):
        root = attention.root()
        for path in (root.parent.parent, root.parent, root): self.api.mkdir(path)
        database = root/'events.sqlite3'; database.write_bytes(b'original fixture')
        replacement = root/'replacement'; replacement.write_bytes(b'replacement fixture')
        child_code = '''import json,os,sys
from pathlib import Path
try:
    operation,source,target=sys.argv[1:]
    if operation=='rename': Path(source).rename(target)
    elif operation=='replace': os.replace(source,target)
    elif operation=='write': Path(source).write_bytes(b'child changed fixture')
    else: raise ValueError('unknown owned fixture action')
except OSError as error:
    print(json.dumps({'blocked':True,'winerror':error.winerror,'errno':error.errno}))
else: print(json.dumps({'blocked':False}))
'''
        def attempt(operation, source, target=''):
            result = subprocess.run([sys.executable,'-I','-c',child_code,operation,str(source),str(target)],
                                    cwd=self.base, env=self.env, stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)
        # Prove the same user and paths permit these operations before pinning.
        moved = root.parent/'moved'
        self.assertFalse(attempt('rename',root,moved)['blocked']); moved.rename(root)
        self.assertFalse(attempt('write',database)['blocked']); database.write_bytes(b'original fixture')
        moved_parent = root.parent.parent/'moved-parent'
        self.assertFalse(attempt('rename',root.parent,moved_parent)['blocked']); moved_parent.rename(root.parent)
        with self.api.runtime(root, create=False):
            for operation,source,target in (
                ('rename',root,moved), ('rename',root.parent,moved_parent),
                ('replace',replacement,database), ('write',database,'')):
                with self.subTest(operation=operation,source=source.name):
                    result=attempt(operation,source,target)
                    self.assertTrue(result['blocked'],result)
                    self.assertTrue(result['winerror'] in (5,32) or result['errno'] == 13,result)
            self.assertEqual(database.read_bytes(),b'original fixture')
            self.assertEqual(replacement.read_bytes(),b'replacement fixture')

    def test_native_wal_reopen_journal_privacy_and_failed_write_rollback(self):
        alerts.record(completed(), preferences())
        root = attention.root()
        with self.api.runtime(root) as path:
            connection = sqlite3.connect(path)
            try: self.assertEqual(connection.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
            finally: connection.close()
        alerts.record(completed('turn-2'), preferences())
        self.assertEqual(len(alerts.pending()), 2)
        with self.assertRaisesRegex(RuntimeError, 'owned interruption'):
            with alerts.database() as db:
                db.execute("UPDATE events SET message='rollback fixture'")
                for suffix in ('-wal','-shm'):
                    self.assertTrue(Path(str(root/'events.sqlite3')+suffix).is_file())
                    with self.api.opened(Path(str(root/'events.sqlite3')+suffix), private=True, writable=True):
                        pass
                with self.assertRaises((OSError,ValueError)): alerts.pending()
                raise RuntimeError('owned interruption')
        with alerts.database(read_only=True) as db:
            self.assertNotIn('rollback fixture', [row[0] for row in db.execute('SELECT message FROM events')])
        self.assertEqual(len(alerts.pending()), 2)

    def test_native_reparse_database_refuses_without_following_target(self):
        root = attention.root()
        self.api.mkdir(root.parent.parent)
        self.api.mkdir(root.parent)
        self.api.mkdir(root)
        victim = self.home/'unrelated'; victim.write_text('keep')
        try: (root/'events.sqlite3').symlink_to(victim)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('native symlink privilege unavailable; reparse acceptance pending')
            raise
        with self.assertRaises(ValueError):
            with alerts.database(): pass
        self.assertEqual(victim.read_text(), 'keep')

    def test_native_existing_unsafe_acl_and_hardlink_refuse_without_changes(self):
        root = attention.root(); root.mkdir(parents=True)
        with self.assertRaises(ValueError):
            with alerts.database(): pass
        self.assertFalse((root/'events.sqlite3').exists())
        root.rmdir()  # Empty, test-owned fixture only.
        alerts.record(completed(), preferences())
        victim = self.home/'unrelated'; victim.write_text('keep')
        os.link(victim, root/'events.sqlite3-journal')
        with self.assertRaises(ValueError): alerts.record(completed('new'), preferences())
        self.assertEqual(victim.read_text(), 'keep')

    def test_expired_identity_refuses_and_pending_omits_it(self):
        alerts.record(completed(), preferences())
        row = alerts.pending()[0]
        later = row['created'] + alerts.EXPIRE + 1
        self.assertEqual(alerts.pending(now=later), [])
        self.assertEqual(alerts.pending(now=row['created']-1), [])
        with self.assertRaises(ValueError): alerts.acknowledge_event(THREAD, row['id'], now=later)
        with patch.object(alerts.time, 'time', return_value=later):
            alerts.record(completed('later'), preferences())
            self.assertEqual(len(alerts.pending()), 1)
        with alerts.database(read_only=True) as db:
            self.assertEqual(db.execute('SELECT phase FROM events WHERE id=?',(row['id'],)).fetchone()[0], 'ack')


if __name__ == '__main__': unittest.main(verbosity=2)
