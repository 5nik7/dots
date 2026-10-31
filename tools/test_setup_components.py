#!/usr/bin/env python3
"""Selective setup and catalog-mapped children in disposable roots."""
import json
import os
from pathlib import Path
import unittest
from unittest import mock

import test_installation as fixtures
from install import Installation
from managed_destination import physical
from transactions import digest


class SetupComponents(unittest.TestCase):
    setUp = fixtures.InstallationTests.setUp
    write = fixtures.InstallationTests.write
    receipt = fixtures.InstallationTests.receipt

    def setup(self, components, resources=None):
        value = Installation(self.repo)
        value.plan_install(components, resources)
        return value

    def termux_mapping(self):
        source = self.repo / 'config/termux'
        source.mkdir()
        self.write('.dots/files.json', dict(schema=1, repository='dots', resources=[
            dict(id='termux', app='termux', category='config', source='config/termux',
                 target='${HOME}/.termux', strategy='directory-link',
                 platforms=['termux','linux','wsl','windows'])]))
        return source, self.home / '.termux'

    def test_component_selection_does_not_remove_others(self):
        with mock.patch.dict(os.environ, self.env):
            core = self.setup(['core'])
            core.apply('install')
            self.assertFalse(self.target.exists())
            files = self.setup(['files'], ['dots:example'])
            files.apply('install')
            self.assertTrue(self.target.is_symlink())
            self.assertTrue((self.home/'.local/bin/dots').exists())
            repeat = self.setup(['files'])
            self.assertEqual(repeat.apply('install')['status'], 'unchanged')
            remove = Installation(self.repo)
            remove.plan_uninstall(['files'])
            remove.apply('uninstall')
            self.assertFalse(self.target.exists())
            self.assertTrue((self.home/'.local/bin/dots').exists())
            self.assertEqual(len(self.receipt()['entries']), 1)

    def test_unknown_or_inactive_resource_refused_before_mutation(self):
        with mock.patch.dict(os.environ, self.env):
            with self.assertRaisesRegex(ValueError, 'not enabled/applicable'):
                self.setup(['files'], ['dots:missing'])
            self.assertFalse((self.home/'.state').exists())

    def test_expected_directory_link_guard_and_foreign_refusal(self):
        source, parent = self.termux_mapping()
        parent.symlink_to(source, target_is_directory=True)
        with mock.patch.dict(os.environ, self.env):
            plan = self.setup(['files'])
            target = physical(parent/'font.ttf', plan.catalog_records, plan.guards)
            self.assertEqual(target, source/'font.ttf')
            plan.add('setup:font:termux', target, text='font fixture')
            parent.unlink()
            other = self.home/'foreign'; other.mkdir()
            parent.symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'changed after preview'):
                plan.apply('install')
            with self.assertRaisesRegex(ValueError, 'points elsewhere'):
                physical(parent/'font.ttf', plan.catalog_records, {})
            self.assertFalse(target.exists())

    def test_legacy_child_receipt_preserves_original_baseline(self):
        source, parent = self.termux_mapping()
        parent.mkdir()
        target = parent/'colors.properties'
        target.write_text('original colors\n')
        with mock.patch.dict(os.environ, self.env):
            old = Installation(self.repo)
            old.add('theme:termux', target, text='installed colors\n')
            old.apply('install')
            baseline = self.receipt()['entries'][str(target)].copy()
            target.replace(source/'colors.properties')
            parent.rmdir(); parent.symlink_to(source, target_is_directory=True)
            remove = Installation(self.repo)
            remove.plan_uninstall(['themes'])
            mapped = remove.receipt['entries'][str(target)]
            self.assertEqual(mapped['backup'], baseline['backup'])
            remove.apply('uninstall')
            self.assertEqual((source/'colors.properties').read_text(), 'original colors\n')
            self.assertTrue(parent.is_symlink())
            self.assertFalse(self.receipt()['entries'])

    def test_nested_link_is_not_followed(self):
        source, parent = self.termux_mapping()
        parent.symlink_to(source, target_is_directory=True)
        (source/'nested').symlink_to(self.home, target_is_directory=True)
        with mock.patch.dict(os.environ, self.env):
            plan = self.setup(['files'])
            with self.assertRaisesRegex(ValueError, 'symlinked parent'):
                physical(parent/'nested/font.ttf', plan.catalog_records, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
