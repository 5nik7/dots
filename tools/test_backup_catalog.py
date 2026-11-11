#!/usr/bin/env python3
"""User backup lifecycle and failure safety in owned filesystem roots."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
from backup_catalog import BackupPlan, physical
from transactions import Store, digest


class Backups(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-bak-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'; self.home.mkdir()
        self.state = self.home / '.state/dots'
        self.storage = self.home / '.bakstore'
        self.env = mock.patch.dict(os.environ, {'HOME': str(self.home),
            'XDG_CONFIG_HOME': str(self.home / '.config'), 'XDG_STATE_HOME': str(self.home / '.state'),
            'XDG_CACHE_HOME': str(self.home / '.cache'), 'DOTS_PROGRESS': 'never'})
        self.env.start(); self.addCleanup(self.env.stop)

    def plan(self, **kw):
        return BackupPlan(self.state, self.storage, **kw)

    def file(self, name='file', data='original'):
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def backup(self, path, **kw):
        plan = self.plan(); plan.create([path], **kw); plan.apply('bak-create')
        return plan.items[0]

    def test_plan_reads_do_not_create_state_or_move_input(self):
        source = self.file('-雪 source')
        plan = self.plan(); plan.create([source])
        self.assertEqual(source.read_text(), 'original')
        self.assertFalse(self.state.exists()); self.assertFalse(self.storage.exists())
        self.assertEqual(plan.report()['status'], 'planned')

    def test_move_restore_retains_backup_and_backs_up_conflict(self):
        source = self.file('with spaces/雪')
        record = self.backup(source)
        payload = Path(record['path'])
        self.assertFalse(source.exists()); self.assertEqual(payload.read_text(), 'original')
        source.write_text('new content')
        restore = self.plan(); restore.restore(record['id']); restore.apply('bak-restore')
        self.assertEqual(source.read_text(), 'original'); self.assertEqual(payload.read_text(), 'original')
        other = next(r for r in self.plan().records() if r['id'] != record['id'])
        self.assertEqual(Path(other['path']).read_text(), 'new content')

    def test_copy_and_adjacent_unique_names(self):
        source = self.file()
        for _ in range(2):
            plan = self.plan(location='adjacent'); plan.create([source], copy=True); plan.apply('bak-create')
        records = self.plan().records()
        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0]['path'], records[1]['path'])
        self.assertTrue(all(Path(r['path']).parent == source.parent and r['path'].endswith('.bak') for r in records))
        self.assertEqual(source.read_text(), 'original')

    def test_directory_and_broken_symlink_are_objects(self):
        directory = self.home / 'directory'; directory.mkdir()
        (directory / 'file').write_text('tree')
        (directory / 'link').symlink_to('../absent')
        record = self.backup(directory)
        restore = self.plan(); restore.restore(record['id']); restore.apply('bak-restore')
        self.assertEqual((directory / 'file').read_text(), 'tree')
        self.assertEqual(os.readlink(directory / 'link'), '../absent')
        link = self.home / 'broken'; link.symlink_to('missing')
        row = self.backup(link)
        self.assertTrue(Path(row['path']).is_symlink())
        restored = self.plan(); restored.restore(row['id']); restored.apply('bak-restore')
        self.assertEqual(os.readlink(link), 'missing')

    def test_same_basename_and_import_unknown_original(self):
        a, b = self.file('a/file', 'a'), self.file('b/file', 'b')
        plan = self.plan(); plan.create([a, b]); plan.apply('bak-create')
        self.assertEqual(len({r['path'] for r in plan.items}), 2)
        legacy = self.file('old.bak.2025', 'legacy')
        imported = self.plan(); imported.import_backup([legacy]); imported.apply('bak-import')
        ident = imported.items[0]['id']
        self.assertEqual(legacy.read_text(), 'legacy')
        with self.assertRaisesRegex(ValueError, 'unknown; supply --to'):
            self.plan().restore(ident)
        restore = self.plan(); restore.restore(ident, destination=self.home / 'restored'); restore.apply('bak-restore')
        self.assertEqual((self.home / 'restored').read_text(), 'legacy')

    def test_missing_member_and_overlap_leave_batch_untouched(self):
        first = self.file('dir/file')
        plan = self.plan()
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            plan.create([first, self.home / 'absent'])
        self.assertTrue(first.exists()); self.assertFalse(self.storage.exists())
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            self.plan().create([first.parent, first])
        with self.assertRaisesRegex(ValueError, 'metadata|inside the source'):
            self.plan().create([self.home])

    def test_catalog_and_source_guards_detect_concurrent_changes(self):
        source = self.file()
        pending = self.plan(); pending.create([source])
        source.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            pending.apply('bak-create')
        self.assertEqual(source.read_text(), 'changed')
        first, second = self.plan(), self.plan()
        first.create([source], copy=True); second.create([source], copy=True)
        first.apply('bak-create')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            second.apply('bak-create')

    def test_linked_parent_pinned_and_broken_parent_refused(self):
        directory = self.home / 'real'; directory.mkdir()
        alias = self.home / 'alias'; alias.symlink_to('real', target_is_directory=True)
        (directory / 'file').write_text('owned')
        plan = self.plan(); plan.create([alias / 'file'])
        other = self.home / 'other'; other.mkdir()
        alias.unlink(); alias.symlink_to('other', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            plan.apply('bak-create')
        self.assertEqual((directory / 'file').read_text(), 'owned')
        alias.unlink(); alias.symlink_to('absent')
        with self.assertRaisesRegex(ValueError, 'parent link'):
            physical(alias / 'file', {})

    def test_rollback_restores_moved_inputs_and_catalog(self):
        source = self.file()
        plan = self.plan(); plan.create([source])
        rename = os.rename
        def fail(a, b):
            if Path(b) == plan.index:
                raise OSError('injected catalog publication failure')
            return rename(a, b)
        with mock.patch('transactions.os.rename', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'injected'):
                plan.apply('bak-create')
        self.assertEqual(source.read_text(), 'original')
        self.assertFalse(Path(plan.items[0]['path']).exists())
        self.assertFalse(plan.index.exists())
        self.assertEqual(Store(self.state).records()[-1]['status'], 'rolled-back')

    def test_modified_payload_refused_and_no_backup_restore(self):
        source = self.file(); row = self.backup(source)
        payload = Path(row['path']); payload.write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            self.plan().restore(row['id'])
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            self.plan().delete([row['id']])
        payload.write_text('original'); source.write_text('discard me')
        restore = self.plan(); restore.restore(row['id'], backup=False); restore.apply('bak-restore')
        self.assertEqual(source.read_text(), 'original')
        self.assertEqual(len(self.plan().records()), 1)

    def test_delete_cleans_owned_container_and_missing_payload(self):
        for missing in (False, True):
            row = self.backup(self.file(), copy=True)
            payload = Path(row['path'])
            if missing: payload.unlink()
            plan = self.plan(); plan.delete([row['id']]); plan.apply('bak-delete')
            self.assertFalse(payload.parent.exists())
            self.assertTrue(self.storage.is_dir())
            self.assertNotIn(row['id'], self.plan().document['entries'])

    def test_delete_preserves_extra_files_adjacent_and_import_parents(self):
        row = self.backup(self.file(), copy=True)
        payload = Path(row['path']); extra = payload.parent / 'keep'
        extra.write_text('keep')
        plan = self.plan(); plan.delete([row['id']]); plan.apply('bak-delete')
        self.assertEqual(extra.read_text(), 'keep'); self.assertFalse(payload.exists())
        plan = self.plan(location='adjacent'); plan.create([self.file()], copy=True); plan.apply('bak-create')
        row = plan.items[0]
        plan = self.plan(); plan.delete([row['id']]); plan.apply('bak-delete')
        self.assertTrue(self.home.is_dir())
        path = self.file('import-parent/old.bak')
        plan = self.plan(); plan.import_backup([path]); plan.apply('bak-import')
        row = plan.items[0]
        plan = self.plan(); plan.delete([row['id']]); plan.apply('bak-delete')
        self.assertTrue(path.parent.is_dir())

    def test_container_race_refuses_and_failure_rolls_back(self):
        row = self.backup(self.file(), copy=True); payload = Path(row['path'])
        plan = self.plan(); plan.delete([row['id']])
        extra = payload.parent / 'new'; extra.write_text('new')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            plan.apply('bak-delete')
        self.assertTrue(payload.exists()); extra.unlink()
        plan = self.plan(); plan.delete([row['id']])
        rename = os.rename
        failed = []
        def fail(a, b):
            if Path(b) == plan.index and not failed:
                failed.append(True)
                raise OSError('injected catalog failure')
            return rename(a, b)
        with mock.patch('transactions.os.rename', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'injected'): plan.apply('bak-delete')
        self.assertEqual(payload.read_text(), 'original')
        self.assertIn(row['id'], self.plan().document['entries'])

    def test_uuid_shape_without_creation_evidence_does_not_own_parent(self):
        row = self.backup(self.file(), copy=True); payload = Path(row['path'])
        index = self.plan().index
        document = json.loads(index.read_text())
        document['entries'][row['id']]['transaction'] = '0'*32
        index.write_text(json.dumps(document))
        plan = self.plan(); plan.delete([row['id']]); plan.apply('bak-delete')
        self.assertFalse(payload.exists())
        self.assertTrue(payload.parent.is_dir())

    def test_prune_is_explicit_and_protects_uninstall_baseline(self):
        source = self.file()
        first = self.backup(source, copy=True)
        source.write_text('second'); second = self.backup(source, copy=True)
        self.state.mkdir(parents=True, exist_ok=True)
        receipt = {'schema': 1, 'entries': {str(source): {'backup_id': first['id']}}, 'transactions': []}
        (self.state / 'installation.json').write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'requires'):
            self.plan().prune()
        with self.assertRaisesRegex(ValueError, 'required for uninstall'):
            self.plan().delete([first['id']])
        plan = self.plan(); plan.prune(keep=0); plan.apply('bak-prune')
        self.assertTrue(Path(first['path']).exists()); self.assertFalse(Path(second['path']).exists())
        restore = self.plan(); restore.restore(first['id']); restore.apply('bak-restore')
        self.assertEqual(source.read_text(), 'original')
        self.assertNotIn(str(source), json.loads((self.state / 'installation.json').read_text())['entries'])
        self.assertFalse(next(r for r in self.plan().records() if r['id'] == first['id'])['protected'])


if __name__ == '__main__':
    unittest.main()
