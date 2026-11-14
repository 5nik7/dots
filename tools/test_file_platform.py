#!/usr/bin/env python3
"""Native file durability regressions in disposable roots only."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib/dots/files'))
import file_platform
from transactions import Store, copy_object, digest


class FilePlatformTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots durability ü ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '-source ü'
        self.source.write_bytes(b'original\r\n\x00bytes\n')

    def test_link_target_identity_preserves_original_digest_and_literal_text(self):
        link = self.root / 'owned link'
        try:
            link.symlink_to(self.source)
        except OSError as error:
            self.skipTest('native symbolic links unavailable: ' + str(error))
        before = digest(link)
        original = os.readlink(link)
        self.assertTrue(file_platform.link_target_matches(link, self.source))
        self.assertFalse(file_platform.link_target_matches(link, self.root / 'different'))
        self.assertFalse(file_platform.link_target_matches(self.source, self.source))
        self.assertEqual(os.readlink(link), original)
        self.assertEqual(digest(link), before)
        link.unlink()
        link.symlink_to(self.source.name)
        self.assertTrue(file_platform.link_target_matches(link, self.source.name))
        self.assertFalse(file_platform.link_target_matches(link, self.source))

    def test_windows_readlink_normalization_is_bounded(self):
        normalize = lambda value: file_platform.native_link_text(value, windows=True)
        self.assertEqual(normalize('\\\\?\\C:\\owned\\target'), 'C:\\owned\\target')
        self.assertEqual(normalize('\\\\?\\UNC\\server\\share\\target'), '\\\\server\\share\\target')
        for value in ('\\\\?\\GLOBALROOT\\Device\\target', '\\\\.\\C:\\owned',
                      '..\\relative', 'C:\\owned\\..\\target'):
            with self.subTest(value=value):
                self.assertEqual(normalize(value), value)
        original = '\\\\?\\C:\\owned\\target'
        self.assertEqual(file_platform.native_link_text(original, windows=False), original)

    def test_legacy_payload_layout_and_rejected_suffix(self):
        target = self.root / 'legacy'
        target.write_bytes(b'before')
        before = digest(target)
        store = Store(self.root / 'state')
        result = store.apply('fixture', [{'path': str(target), 'text': 'after'}],
                             {str(target): before}, retain=True)
        entry = result['operations'][0]
        self.assertNotIn('payload_suffix', entry)
        self.assertEqual(store.payload(result['id'], 0, 'before').name, '0-before')
        operations, guards, catalogs = store.inverse(result['id'])
        store.apply('undo', operations, guards, catalogs=catalogs)
        self.assertEqual(digest(target), before)
        for suffix in ('/../../outside', '.exe/child', '.ps1', None):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'payload suffix'):
                store.payload(result['id'], 0, 'before', dict(entry, payload_suffix=suffix))

    @unittest.skipUnless(os.name == 'nt', 'Windows filename-derived executable mode')
    def test_native_executable_backups_undo_and_drift(self):
        for suffix in file_platform.WINDOWS_EXECUTABLE_SUFFIXES:
            with self.subTest(suffix=suffix):
                target = self.root / ('original' + suffix)
                source = self.root / ('replacement' + suffix)
                target.write_bytes(b'original executable')
                source.write_bytes(b'replacement executable')
                before, after = digest(target), digest(source)
                store = Store(self.root / ('state' + suffix))
                result = store.apply('fixture', [{'path': str(target), 'source': str(source)}],
                                     {str(target): before, str(source): after}, retain=True)
                self.assertEqual(digest(target), after)
                self.assertEqual(result['operations'][0]['payload_suffix'], suffix)
                self.assertEqual(digest(store.payload(result['id'], 0, 'before')), before)
                target.write_bytes(b'changed after apply')
                with self.assertRaisesRegex(ValueError, 'drift blocks undo'):
                    store.inverse(result['id'])
                target.write_bytes(b'replacement executable')
                operations, guards, catalogs = store.inverse(result['id'])
                store.apply('undo', operations, guards, catalogs=catalogs)
                self.assertEqual(digest(target), before)
                self.assertEqual(digest(source), after)

    @unittest.skipUnless(os.name == 'nt', 'Windows filename-derived executable mode')
    def test_native_executable_failed_publication_rolls_back(self):
        targets = [self.root / name for name in ('first.exe', 'second.cmd')]
        for target in targets:
            target.write_bytes(b'original')
        guards = {str(path): digest(path) for path in targets}
        store = Store(self.root / 'state')
        save = store.save
        failed = False
        def fail_after_first(doc):
            nonlocal failed
            save(doc)
            if not failed and doc['status'] == 'applying' and any(e['phase'] == 'done' for e in doc['operations']):
                failed = True
                raise OSError('injected publication failure')
        with patch.object(store, 'save', side_effect=fail_after_first):
            with self.assertRaisesRegex(OSError, 'injected publication failure'):
                store.apply('fixture', [{'path': str(path), 'text': 'replacement'} for path in targets], guards)
        self.assertEqual({str(path): digest(path) for path in targets}, guards)
        self.assertEqual(store.records()[0]['status'], 'rolled-back')
        self.assertFalse(list(self.root.glob('*.dots-*')))

    def test_copy_readonly_file_and_directory_preserves_metadata(self):
        self.source.chmod(0o444)
        before = digest(self.source)
        direct = self.root / 'direct'
        copy_object(self.source, direct)
        self.assertEqual(digest(direct), before)
        directory = self.root / 'tree'
        directory.mkdir()
        copy_object(self.source, directory / 'readonly')
        tree_copy = self.root / 'tree copy'
        copy_object(directory, tree_copy)
        self.assertEqual(digest(directory), digest(tree_copy))
        self.assertEqual(digest(self.source), before)
        # Cleanup must also work on Windows with read-only attributes.
        for path in (self.source, direct, directory / 'readonly', tree_copy / 'readonly'):
            path.chmod(stat.S_IREAD | stat.S_IWRITE)

    def test_sync_owned_file_preserves_contents(self):
        before = digest(self.source)
        file_platform.sync_file(self.source)
        self.assertEqual(digest(self.source), before)

    def test_copy_flush_error_propagates_without_changing_source(self):
        before = digest(self.source)
        with patch.object(file_platform.os, 'fsync', side_effect=OSError('injected flush failure')):
            with self.assertRaisesRegex(OSError, 'injected flush failure'):
                copy_object(self.source, self.root / 'failed copy')
        self.assertEqual(digest(self.source), before)

    def test_backup_flush_failure_prevents_live_replacement(self):
        store = Store(self.root / 'state')
        before = digest(self.source)
        # Fail only a copied payload flush; journal writes must still succeed.
        real_copy = file_platform.copy_file
        def failing_copy(source, dest):
            with patch.object(file_platform.os, 'fsync', side_effect=OSError('injected payload flush failure')):
                return real_copy(source, dest)
        with patch('transactions.copy_file', side_effect=failing_copy):
            with self.assertRaisesRegex(OSError, 'injected payload flush failure'):
                store.apply('fixture', [{'path': str(self.source), 'text': 'replacement'}],
                            {str(self.source): before}, retain=True)
        self.assertEqual(digest(self.source), before)
        self.assertFalse(list(self.root.glob('*.dots-*')))

    @unittest.skipIf(os.name == 'nt', 'POSIX permission and umask contract')
    def test_text_prediction_matches_transaction_and_undo_under_umasks(self):
        for mask in (0o22, 0o77):
            with self.subTest(umask=oct(mask)):
                old_mask = os.umask(mask)
                try:
                    target = self.root / ('target-' + str(mask))
                    target.write_text('before\n')
                    target.chmod(0o600)
                    before = digest(target)
                    prepared = self.root / ('prepared-' + str(mask))
                    file_platform.prepare_text(prepared, 'after ü\n', target)
                    store = Store(self.root / ('state-' + str(mask)))
                    result = store.apply('fixture', [{'path': str(target), 'text': 'after ü\n'}],
                                         {str(target): before}, retain=True)
                    self.assertEqual(digest(target), digest(prepared))
                    self.assertEqual(target.stat().st_mode & 0o777, 0o600)
                    target.chmod(0o640)
                    with self.assertRaisesRegex(ValueError, 'drift blocks undo'):
                        store.inverse(result['id'])
                    target.chmod(0o600)
                    operations, guards, catalogs = store.inverse(result['id'])
                    store.apply('undo', operations, guards, catalogs=catalogs)
                    self.assertEqual(digest(target), before)
                finally:
                    os.umask(old_mask)


if __name__ == '__main__':
    unittest.main(verbosity=2)
