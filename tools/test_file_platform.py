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
