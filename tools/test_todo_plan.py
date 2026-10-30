#!/usr/bin/env python3
"""Goal planning contracts in owned roots; no live Codex or clipboard writes."""
from contextlib import redirect_stdout
import base64
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_menus import MenuFixture, ROOT
from todo_core import Goals, scope
from todo_brief import brief
from todo_plan import Link, prepare, launch, thread_name


class FakeCodex:
    def __init__(self):
        self.calls = []
        self.active = False
        self.mode = 'default'
        self.count = 0
        self.fail = None

    def call(self, method, params=None):
        self.calls.append((method, params))
        if self.fail == method: raise ValueError('injected failure')
        if method == 'collaborationMode/list':
            return dict(data=[dict(mode='plan', reasoning_effort='medium')])
        if method == 'config/read': return dict(config=dict(plan_mode_reasoning_effort='xhigh'))
        if method == 'thread/start':
            self.count += 1
            return self.session('thread-' + str(self.count))
        if method == 'thread/resume': return self.session(params['threadId'])
        if method == 'thread/name/set': return {}
        if method == 'turn/start':
            self.mode = params['collaborationMode']['mode']
            self.active = True
            return dict(turn=dict(id='turn-' + str(len(self.calls))))
        if method == 'turn/interrupt': self.active = False; return {}
        raise AssertionError(method)

    def session(self, thread):
        return dict(thread=dict(id=thread, status=dict(type='active' if self.active else 'idle')),
                    model='user-selected-model', reasoningEffort='high',
                    collaborationMode=dict(mode=self.mode))


class Planning(MenuFixture):
    def setUp(self):
        super().setUp()
        Path(self.env['DOTS']).mkdir()
        self.selected = scope()
        self.goal = Goals(self.selected).mutate('add', title='Plan café $(touch nope)', alias='my-goal',
                                               priority='high', acceptance=['Useful outcome'])['goals'][0]
        self.rpc = FakeCodex()
        self.backend = type('Backend', (), dict(identity='fixture'))()

    def prepare(self, goal=None, new=False):
        goal = goal or self.goal
        store = Goals(self.selected)
        link = Link(self.selected, goal['id'])
        with link.locked():
            result = prepare(store, goal, link, self.backend, self.rpc, new=new)
        return result, link

    def test_named_actual_plan_and_resume_busy_no_duplicate(self):
        before = Path(self.selected['path']).read_bytes()
        record, link = self.prepare()
        self.assertEqual(record['submission']['state'], 'accepted')
        self.assertEqual(link.read()['thread'], record['thread'])
        turns = [p for m, p in self.rpc.calls if m == 'turn/start']
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]['collaborationMode'], dict(mode='plan', settings=dict(
            model='user-selected-model', reasoning_effort='xhigh', developer_instructions=None)))
        self.assertIn(self.goal['id'], turns[0]['input'][0]['text'])
        self.assertFalse(turns[0]['input'][0]['text'].startswith('/plan'))
        self.prepare()
        self.assertEqual(len([m for m,p in self.rpc.calls if m == 'turn/start']), 1)
        self.rpc.active = False
        self.prepare()
        self.assertEqual(len([m for m,p in self.rpc.calls if m == 'turn/start']), 2)
        self.assertEqual(before, Path(self.selected['path']).read_bytes())

    def test_new_retains_old_and_children_own_their_threads(self):
        parent, _ = self.prepare()
        child = Goals(self.selected).mutate('add', title='Child', parent=self.goal['id'])['goals'][0]
        self.rpc.active = False
        child_record, _ = self.prepare(child)
        self.rpc.active = False
        fresh, _ = self.prepare(new=True)
        self.assertEqual(fresh['previous_thread'], parent['thread'])
        self.assertEqual(len({parent['thread'], child_record['thread'], fresh['thread']}), 3)

    def test_failed_submission_is_retained_and_not_retried(self):
        self.rpc.fail = 'turn/start'
        with self.assertRaisesRegex(ValueError, 'injected'): self.prepare()
        link = Link(self.selected, self.goal['id'])
        record = link.read()
        self.assertEqual(record['submission']['state'], 'sending')
        self.rpc.fail = None
        self.prepare()
        self.assertEqual(len([m for m,p in self.rpc.calls if m == 'turn/start']), 1)
        self.assertEqual(self.rpc.count, 1)

    def test_missing_or_unretained_plan_mode_fails_closed(self):
        with patch.object(self.rpc, 'call', return_value=dict(data=[])), \
                self.assertRaisesRegex(ValueError, 'does not expose Plan Mode'):
            self.prepare()
        link = Link(self.selected, self.goal['id'])
        self.assertIsNone(link.read())
        self.assertEqual(self.rpc.count, 0)

        session = self.rpc.session
        def without_plan(thread):
            return {**session(thread), 'collaborationMode': dict(mode='default')}
        with patch.object(self.rpc, 'session', side_effect=without_plan), \
                self.assertRaisesRegex(ValueError, 'did not retain Plan Mode'):
            self.prepare()
        record = link.read()
        self.assertEqual(record['submission']['state'], 'accepted')
        self.assertEqual([p for m, p in self.rpc.calls if m == 'turn/interrupt'],
                         [dict(threadId=record['thread'], turnId=record['submission']['turn'])])
        self.assertFalse(self.rpc.active)

    def test_link_conflict_stale_store_and_removed_goal(self):
        link = Link(self.selected, self.goal['id'])
        with link.locked():
            with self.assertRaisesRegex(ValueError, 'already being launched'):
                with Link(self.selected, self.goal['id']).locked(): pass
        store = Goals(self.selected)
        Goals(self.selected).mutate('note', self.goal['id'], note='Changed after selection')
        with link.locked(), self.assertRaisesRegex(ValueError, 'changed since selection'):
            prepare(store, self.goal, link, self.backend, self.rpc)
        Goals(self.selected).mutate('remove', self.goal['id'])
        with self.assertRaises(ValueError): self.prepare()
        self.assertEqual(self.rpc.calls, [])

    def test_invalid_links_and_backend_changes_refuse(self):
        _, link = self.prepare()
        data = link.read(); data['backend'] = 'other'
        with link.locked(): link.write(data)
        with self.assertRaisesRegex(ValueError, 'another Codex backend'): self.prepare()
        link.path.unlink()
        target = self.base / 'outside'; target.write_text('untouched')
        link.path.symlink_to(target)
        with self.assertRaises(ValueError): link.read()
        self.assertEqual(target.read_text(), 'untouched')

    def test_name_tracks_alias_title_and_global_working_directory(self):
        name = thread_name(self.selected, self.goal)
        self.assertTrue(name.startswith('[repo] my-goal — Plan café'))
        selected = scope(standalone=True, global_=True)
        goal = Goals(selected).mutate('add', title='Global') ['goals'][0]
        with patch('pathlib.Path.cwd', return_value=self.home):
            link = Link(selected, goal['id'])
            with link.locked(): record = prepare(Goals(selected), goal, link, self.backend, self.rpc)
        self.assertEqual(record['cwd'], str(self.home))
        self.rpc.active = False
        with patch('pathlib.Path.cwd', return_value=self.base):
            with link.locked(): resumed = prepare(Goals(selected), goal, link, self.backend, self.rpc)
        self.assertEqual(resumed['cwd'], str(self.home))
        self.assertEqual(thread_name(selected, goal), '[global] Global')

    def test_brief_full_tree_completed_context_save_and_implement_instructions(self):
        Goals(self.selected).mutate('note', self.goal['id'], note='Parent notes\nDetails café')
        child = Goals(self.selected).mutate('add', title='Child', parent=self.goal['id'], notes='Child notes')['goals'][0]
        grandchild = Goals(self.selected).mutate('add', title='Grandchild', parent=child['id'], notes='Completed notes')['goals'][0]
        Goals(self.selected).mutate('done', grandchild['id'])
        removed = Goals(self.selected).mutate('add', title='Removed', parent=self.goal['id'])['goals'][0]
        Goals(self.selected).mutate('remove', removed['id'])
        store = Goals(self.selected)
        from todo_brief import body
        goal = store.find(self.goal['id'])
        text = brief(store, goal)
        self.assertTrue(text.startswith('/plan '))
        self.assertEqual(text, '/plan ' + body(store, goal))
        for phrase in (child['id'], grandchild['id'], 'Status: done', 'Save these goals', '--parent',
                       '--accept', 'one to three', 'Implement the plan', 'do not create goals',
                       '$dots-todo-planning', 'If that skill is unavailable', 'Parent notes\nDetails café',
                       'Child notes', 'Completed notes'):
            self.assertIn(phrase, text)
        self.assertNotIn(removed['id'], text)
        self.assertNotIn('\x1b', text)

    def test_dry_run_and_both_dispatchers_do_not_launch_or_write(self):
        before = {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        with patch('todo_codex.Backend', side_effect=AssertionError('must stay lazy')):
            with redirect_stdout(io.StringIO()) as output:
                launch(Goals(self.selected), self.goal, dry_run=True)
            self.assertIn('Plan', output.getvalue())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        for script in ('todo_cli.py', 'todo_standalone.py'):
            args = ['--project', self.selected['root']] if script == 'todo_standalone.py' else []
            result = subprocess.run([sys.executable, '-B', str(ROOT/'lib/dots'/script),
                *args, 'plan', 'my-goal', '--dry-run'], env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('my-goal', result.stdout)
        directory = Path(self.selected['root'])/'bin'; directory.mkdir()
        shutil.copy2(ROOT/'bin/dots-todo-plan', directory/'dots-todo-plan')
        args = base64.b64encode(json.dumps(['todo', 'plan', 'my-goal', '--dry-run']).encode()).decode()
        result = subprocess.run([sys.executable, '-B', str(ROOT/'lib/dots/native.py'), 'cli', args],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('my-goal', result.stdout)
        from todo_completion import complete
        with redirect_stdout(io.StringIO()) as output: complete(['plan', 'my-'])
        self.assertIn('my-goal', output.getvalue())
        with redirect_stdout(io.StringIO()) as output: complete(['plan', 'my-goal', '--n'])
        self.assertIn('--new', output.getvalue())

    def test_save_commands_attach_tree_and_retain_recovery(self):
        def cli(*args):
            result = subprocess.run([sys.executable, '-B', str(ROOT/'lib/dots/todo_cli.py'), *args, '--json'],
                                    env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            if args[0] != 'show': self.assertTrue(data['transaction'])
            return data['goals'][0]
        child = cli('add', 'Agreed package', '--parent', self.goal['id'], '--priority', 'high',
                    '--accept', 'Package outcome works')
        grandchild = cli('add', 'Nested outcome', '--parent', child['id'], '--priority', 'high',
                         '--accept', 'Nested verification passes')
        cli('note', self.goal['id'], 'Agreed decisions; dependency: ' + child['id'])
        store = Goals(self.selected)
        self.assertEqual(store.find(child['id'])['parent'], self.goal['id'])
        self.assertEqual(store.find(grandchild['id'])['parent'], child['id'])
        self.assertEqual(store.find(grandchild['id'])['acceptance'], ['Nested verification passes'])
        self.assertTrue(all(g['status'] == 'open' for g in store.goals))

    def test_clipboard_literal_utf8_and_missing_provider(self):
        from clipboard import copy
        text = '/plan café\n$(touch must-not-run)\n'
        with patch('clipboard.detect', return_value=dict(platform='termux')), \
                patch('clipboard.shutil.which', return_value='/fixture/termux-clipboard-set'), \
                patch('clipboard.subprocess.run') as run:
            run.return_value.returncode = 0
            copy(text)
            self.assertEqual(run.call_args.kwargs['input'], text.encode())
            self.assertEqual(run.call_args.args[0], ['/fixture/termux-clipboard-set'])
        with patch('clipboard.shutil.which', return_value=None), self.assertRaisesRegex(ValueError, 'Clipboard unavailable'):
            copy(text)

    def test_popup_print_and_copy_complete_brief_and_menu_exit(self):
        from todo_commands import parser
        from todo_menu import browse, Handoff
        from interaction import SelectionEvent
        text = brief(Goals(self.selected), self.goal)
        events = [SelectionEvent('copy-brief', 0), SelectionEvent('print-brief', 0)]
        with patch('todo_menu.pick', side_effect=events), patch('clipboard.copy') as copied, \
                redirect_stdout(io.StringIO()) as output:
            result = browse(self.selected, parser().parse_args(['browse']))
        self.assertIsInstance(result, Handoff)
        copied.assert_called_once_with(text)
        self.assertEqual(output.getvalue(), text)
        import menu_cli
        with patch('menu_cli.entry') as entry, patch('todo_menu.browse', return_value=Handoff()):
            entry.return_value.available = True
            self.assertTrue(menu_cli.invoke(ROOT, next(a for a in menu_cli.ACTIONS if a.id == 'todo'), None))
        from argparse import Namespace
        from menus import Entry
        with patch('menu_cli.entry') as entry, patch('menu_cli.launcher'), \
                patch('menu_cli.choose', return_value=Entry('todo', 'todo')), \
                patch('todo_menu.browse', return_value=Handoff(130)):
            entry.return_value.available = True
            self.assertEqual(menu_cli.run(Namespace(menu_mode='browse', query='', client=None, family='')), 130)


if __name__ == '__main__': unittest.main()
