#!/usr/bin/env python3
"""Consumer progress boundaries; only temporary transaction and cleanup roots."""
from fractions import Fraction
from contextlib import redirect_stdout
import importlib.util
import io
import json
from types import SimpleNamespace
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'lib/dots'), str(ROOT / 'lib/dots/files')]
import progress
import transactions
from cleanup import engine
from cleanup.termux import Termux
from cleanup.receipts import Receipts


class ConsumerProgress(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='dots progress consumers 雪 ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scopes = []
        original = progress.sequence
        def sequence(*args, **kwargs):
            scope = original(*args, **kwargs)
            self.scopes.append(scope)
            return scope
        self.sequence = sequence
        self.addCleanup(patch.stopall)
        patch.object(progress, 'eligible', return_value=False).start()
        patch.object(transactions, 'sequence', side_effect=sequence).start()
        patch.object(engine, 'sequence', side_effect=sequence).start()

    def test_transaction_reserves_completion_until_durable_finalization(self):
        store = transactions.Store(self.root / 'state')
        target = self.root / 'target'
        observed = []
        cleanup = store.cleanup
        def finalize(record):
            scope = next(s for s in self.scopes if s.label == 'File transaction')
            observed.append((record['status'], scope.meter.overall[0]))
            cleanup(record)
        with patch.object(store, 'cleanup', side_effect=finalize):
            result = store.apply('fixture', [dict(path=str(target), text='fixture')], {str(target): None})
        scope = self.scopes[0]
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(observed, [('complete', Fraction(3, 4))])
        self.assertEqual(scope.meter.overall[0], 1)
        self.assertEqual(target.read_text(), 'fixture')

    def test_failed_apply_recovers_without_crediting_remaining_work(self):
        store = transactions.Store(self.root / 'state')
        target = self.root / 'target'
        target.write_text('original')
        real_notify = store.notify
        def notify(label, *args, **kwargs):
            if label == 'Updated': raise RuntimeError('injected after replacement')
            real_notify(label, *args, **kwargs)
        with patch.object(store, 'notify', side_effect=notify), self.assertRaises(RuntimeError):
            store.apply('fixture', [dict(path=str(target), text='replacement')],
                        {str(target): transactions.digest(target)})
        scope = next(s for s in self.scopes if s.label == 'File transaction')
        recovery = next(s for s in self.scopes if s.label == 'File recovery')
        self.assertTrue(recovery.recovery)
        self.assertEqual(scope.meter.overall[0], Fraction(1, 2))
        self.assertEqual(target.read_text(), 'original')
        self.assertEqual(store.records()[0]['status'], 'rolled-back')

    def test_recursive_status_preserves_query_order_without_extra_discovery(self):
        spec = importlib.util.spec_from_file_location('progress_native_git', ROOT / 'lib/dots/git/cli.py')
        git = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(git)
        root, child = self.root / 'repo', self.root / 'repo/child'
        calls = []
        def record(name, path, result):
            calls.append((name, path))
            return result
        def text(path, *args, **kwargs):
            return record('branch' if args[0] == 'symbolic-ref' else 'counts', path,
                          'main' if args[0] == 'symbolic-ref' else '0 0')
        workflow = git.Workflow.__new__(git.Workflow)
        workflow.root, workflow.wiki, workflow.failed = root, None, False
        workflow.args = SimpleNamespace(json=True)
        output = io.StringIO()
        with patch.object(git, 'root', side_effect=lambda p: record('root', p, p)), \
             patch.object(git, 'text', side_effect=text), \
             patch.object(git, 'status_files', side_effect=lambda p: record('files', p, [])), \
             patch.object(git, 'upstream', side_effect=lambda p: record('upstream', p, ('main', 'origin', 'refs/heads/main', 'origin/main'))), \
             patch.object(git, 'children', side_effect=lambda p: record('children', p, [('child', 'abc')] if p == root else [])), \
             patch.object(git, 'child_name', side_effect=lambda p, name: record('child-name', p / name, None)), \
             redirect_stdout(output):
            workflow.status()
        expected = [(name, root) for name in ('root', 'branch', 'files', 'upstream', 'counts', 'children')]
        expected += [('child-name', child)]
        expected += [(name, child) for name in ('root', 'branch', 'files', 'upstream', 'counts', 'children')]
        self.assertEqual(calls, expected)
        self.assertEqual([row['path'] for row in json.loads(output.getvalue())['repositories']],
                         [str(root), str(child)])

    def cleanup_fixture(self):
        home = self.root / 'com.termux/files/home'
        prefix = self.root / 'com.termux/files/usr'
        home.mkdir(parents=True); prefix.mkdir(parents=True)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('TERMUX', 'XDG_', 'GO', 'UV_', 'CARGO', 'DOTS'))}
        env.update(HOME=str(home), PREFIX=str(prefix), XDG_CACHE_HOME=str(home / '.cache'),
                   XDG_STATE_HOME=str(home / 'state'))
        target = home / '.npm/_cacache/keep'
        target.parent.mkdir(parents=True); target.write_text('fixture')
        adapter = Termux(env)
        targets, issues = adapter.candidates(('downloads',), 30)
        return adapter, targets, issues, Receipts(home / 'state/cleanup'), target

    def test_cleanup_stop_freezes_progress_and_preserves_files(self):
        adapter, targets, issues, store, target = self.cleanup_fixture()
        result = engine.run(adapter, targets, ('downloads',), issues, store, lambda *_: 'stop',
                            inspect=lambda _: ([], []))
        scope = next(s for s in self.scopes if s.label == 'Cleanup run')
        self.assertEqual(result['status'], 'stopped')
        self.assertTrue(scope.meter.cancelled)
        self.assertLess(scope.meter.overall[0], 1)
        self.assertTrue(target.exists())
        self.assertFalse(store.directory.exists())


if __name__ == '__main__':
    unittest.main()
