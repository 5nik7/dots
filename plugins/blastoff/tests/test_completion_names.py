import os
import unittest
from release_support import ReleaseHarness,core
helper=core.ui_module('completion_names')
@unittest.skipUnless(os.name == "posix", "Unix-only legacy completion helper")
class LegacyCompletionNames(ReleaseHarness):
    def test_regular_names_and_pairs_without_reading_contents(self):
        self.theme('alpha','not TOML')
        self.theme('CON','not TOML')
        (self.store/'themes/link.toml').symlink_to('alpha.toml')
        os.mkfifo(self.store/'themes/pipe.toml')
        before=self.tree_without_fifo()
        self.assertEqual(helper.names(str(self.store),'themes'),['alpha'])
        self.write(self.store/'backups/pair.toml','not TOML');self.write(self.store/'backups/pair.json','not JSON')
        self.write(self.store/'backups/orphan.toml','x')
        self.assertEqual(helper.names(str(self.store),'backups'),['pair'])
        self.assertEqual(before,{k:v for k,v in self.tree_without_fifo().items() if 'backups' not in k})
    def tree_without_fifo(self):
        return {str(p.relative_to(self.store)):(p.lstat().st_mode,p.lstat().st_mtime_ns) for p in self.store.rglob('*')}
    def test_linked_children_are_refused_and_root_alias_works(self):
        self.theme()
        alias=self.home/'alias';alias.symlink_to(self.store,target_is_directory=True)
        self.assertEqual(helper.names(str(alias),'themes'),['purple'])
        self.store.joinpath('modules').symlink_to(self.store/'themes',target_is_directory=True)
        with self.assertRaises(Exception):helper.names(str(self.store),'modules')
