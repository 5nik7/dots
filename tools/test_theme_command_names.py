#!/usr/bin/env python3
"""Shortcut allocation with owned PATH fixtures, including Windows semantics."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib/dots/themes'))
from command_names import allocate


class CommandNames(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='dots-command-names ü ')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.bin = self.root / 'external bin'; self.bin.mkdir()
        self.owned = self.root / 'owned bin'; self.owned.mkdir()

    def program(self, name, directory=None):
        path = (directory or self.bin) / name
        path.write_text('Never execute a discovery candidate.\n')
        path.chmod(0o700)
        return path

    def allocate(self, names, **kwargs):
        return allocate(names, self.owned, search_path=str(self.bin), **kwargs)

    def test_suffix_skip_canonical_reservation_and_reserved_names(self):
        self.assertEqual(self.allocate(['sample']), ({'sample': 'sample'}, []))
        self.program('sample')
        self.assertEqual(self.allocate(['sample']), ({'sample-theme': 'sample'}, []))
        self.assertEqual(self.allocate(['sample', 'sample-theme']), ({'sample-theme': 'sample-theme'}, ['sample']))
        self.program('sample-theme')
        self.assertEqual(self.allocate(['sample']), ({}, ['sample']))
        self.assertEqual(self.allocate(['set', 'theme']), ({}, []))
        self.assertEqual(self.allocate([]), ({}, []))

    def test_windows_case_extensions_and_ps1(self):
        for name in ('SAMPLE.EXE', 'SAMPLE.CMD', 'SAMPLE.PS1', 'SAMPLE.CUSTOM'):
            with self.subTest(name=name):
                path = self.program(name)
                self.assertEqual(self.allocate(['sample'], windows=True, pathext='.EXE;.CMD;.CUSTOM'), ({'sample-theme': 'sample'}, []))
                other = self.program('Sample-Theme.Ps1')
                self.assertEqual(self.allocate(['sample'], windows=True, pathext='.EXE;.CMD;.CUSTOM'), ({}, ['sample']))
                path.unlink(); other.unlink()

    def test_owned_wrappers_do_not_mask_later_external_program(self):
        self.program('sample', self.owned)
        self.program('sample-theme', self.owned)
        search = str(self.owned) + os.pathsep + str(self.bin)
        self.assertEqual(allocate(['sample'], self.owned, search_path=search), ({'sample': 'sample'}, []))
        self.program('sample')
        self.assertEqual(allocate(['sample'], self.owned, search_path=search), ({'sample-theme': 'sample'}, []))

    @unittest.skipIf(os.name == 'nt', 'POSIX executable bits and symlinks')
    def test_nonexecutables_directories_broken_links_and_symlinked_path(self):
        plain = self.program('sample'); plain.chmod(0o600)
        self.assertEqual(self.allocate(['sample']), ({'sample': 'sample'}, []))
        plain.unlink(); plain.mkdir()
        self.assertEqual(self.allocate(['sample']), ({'sample': 'sample'}, []))
        plain.rmdir(); plain.symlink_to(self.root / 'missing')
        self.assertEqual(self.allocate(['sample']), ({'sample': 'sample'}, []))
        alias = self.root / 'owned alias'; alias.symlink_to(self.owned, target_is_directory=True)
        self.program('sample', self.owned)
        self.assertEqual(allocate(['sample'], self.owned, search_path=str(alias)), ({'sample': 'sample'}, []))


if __name__ == '__main__': unittest.main(verbosity=2)
