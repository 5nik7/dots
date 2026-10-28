"""Storage aliases are intentional; redirects beneath storage are not."""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from unittest.mock import patch

from test_blastoff import ROOT, Harness, core

OLD = '[directory]\nstyle="old"\n'
NEW = '[directory]\nstyle="new"\n'


@unittest.skipUnless(os.name == 'posix', 'POSIX symlink fixtures; native Windows gate separate')
class StorageLinks(Harness):
    def setUp(self):
        super().setUp()
        self.real = self.home/'dots/config/blastoff'
        self.real.mkdir(parents=True)
        self.store.symlink_to(self.real, target_is_directory=True)
        self.write(self.config, OLD)

    def test_default_root_and_relative_chain(self):
        self.store.unlink()
        self.store.symlink_to('dots/config/blastoff', target_is_directory=True)
        default = self.home/'.config/blastoff'
        default.parent.mkdir()
        default.symlink_to('../store', target_is_directory=True)
        del self.env['BLASTOFF_HOME']
        result = json.loads(self.invoke('theme', 'save', 'saved', '--json').stdout)
        self.assertEqual(result['path'], str(self.real/'themes/saved.toml'))
        doctor = json.loads(self.invoke('doctor', '--json').stdout)
        self.assertEqual(doctor['blastoff_home'], str(self.real))
        self.assertEqual(doctor['themes'], str(self.real/'themes'))
        self.assertEqual(doctor['modules'], str(self.real/'modules'))
        self.assertEqual(os.readlink(default), '../store')
        self.assertEqual(os.readlink(self.store), 'dots/config/blastoff')

    def test_linked_ancestor_with_missing_ordinary_suffix(self):
        alias = self.home/'alias'
        alias.symlink_to(self.real.parent, target_is_directory=True)
        self.env['BLASTOFF_HOME'] = str(alias/'new-store')
        self.invoke('module', 'list')
        self.assertFalse((self.real.parent/'new-store').exists())
        self.invoke('theme', 'save', 'saved')
        self.assertEqual((self.real.parent/'new-store/themes/saved.toml').read_text(), OLD)

    def test_all_storage_mutations_and_recovery(self):
        self.invoke('theme', 'save', 'saved')
        self.invoke('theme', 'copy', 'saved', 'copied')
        external = self.write(self.home/'external.toml', NEW)
        self.invoke('theme', 'import', str(external), 'imported')
        self.invoke('theme', 'save', 'saved', code=1)
        self.write(self.config, NEW)
        self.invoke('theme', 'save', 'saved', '--force')
        self.assertIn(OLD, [p.read_text() for p in self.snapshots()])
        stored_meta = [json.loads(p.read_text()) for p in (self.real/'backups').glob('*.json')]
        self.assertEqual(stored_meta[0]['source'], str(self.real/'themes/saved.toml'))
        self.invoke('theme', 'apply', 'copied')
        self.assertEqual(self.config.read_text(), OLD)
        self.invoke('module', 'save', 'directory', 'saved-module')
        self.write(self.config, NEW + '\n[character]\nsuccess_symbol="keep"\n')
        self.invoke('module', 'load', 'saved-module')
        self.assertIn('style="old"', self.config.read_text())
        self.assertIn('success_symbol="keep"', self.config.read_text())
        before = self.config.read_bytes()
        ident = json.loads(self.invoke('backup', 'create', '--json').stdout)['backup']
        self.write(self.config, NEW)
        self.invoke('backup', 'restore', ident)
        self.assertEqual(self.config.read_bytes(), before)
        self.invoke('theme', 'delete', 'copied', '--force')
        self.invoke('module', 'delete', 'saved-module', '--force')
        self.assertFalse((self.real/'themes/copied.toml').exists())
        self.assertFalse((self.real/'modules/saved-module.toml').exists())
        legacy = self.home/'legacy'
        self.write(legacy/'migrated.toml', NEW)
        self.invoke('migrate', str(legacy))
        self.assertEqual((self.real/'themes/migrated.toml').read_text(), NEW)
        self.assertEqual((legacy/'migrated.toml').read_text(), NEW)
        self.assertTrue(self.store.is_symlink())
        self.assertFalse((self.real/'.operation.lock').exists())

    def test_aliases_share_lock_and_never_break_stale_lock(self):
        with patch.dict(os.environ, self.env, clear=True):
            app = core.App(core.cli_module().parse(['theme', 'save', 'saved'], core.VERSION))
            with app.mutate():
                for root in (self.store, self.real):
                    self.env['BLASTOFF_HOME'] = str(root)
                    self.assertIn('stale lock', self.invoke('theme', 'save', 'saved', code=1).stderr)
                    self.assertTrue((self.real/'.operation.lock').is_dir())
        self.assertFalse((self.real/'.operation.lock').exists())
        self.assertFalse((self.real/'themes').exists())

    def test_alias_retarget_does_not_redirect_pinned_app(self):
        other = self.home/'other'; other.mkdir()
        with patch.dict(os.environ, self.env, clear=True):
            app = core.App(core.cli_module().parse(['theme', 'save', 'saved'], core.VERSION))
            self.store.unlink()
            self.store.symlink_to(other, target_is_directory=True)
            with app.mutate():
                app.stored_write(app.themes/'saved.toml', OLD.encode())
        self.assertEqual((self.real/'themes/saved.toml').read_text(), OLD)
        self.assertEqual(list(other.iterdir()), [])

    def test_bad_roots_fail_without_creating_targets(self):
        self.store.unlink()
        missing = self.home/'missing'
        regular = self.write(self.home/'file', OLD)
        for target in (missing, regular, self.store):
            with self.subTest(target=target):
                self.store.symlink_to(target)
                result = self.invoke('theme', 'save', 'saved', '--json', code=1)
                self.assertEqual(json.loads(result.stderr)['code'], 1)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse(missing.exists())
                self.assertEqual(list(self.real.iterdir()), [])
                self.assertEqual(self.config.read_text(), OLD)
                self.store.unlink()
        # A dangling ancestor cannot be hidden by a nonexistent suffix.
        self.store.symlink_to(missing, target_is_directory=True)
        self.env['BLASTOFF_HOME'] = str(self.store/'new-store')
        self.invoke('theme', 'save', 'saved', code=1)
        self.assertFalse(missing.exists())

    def test_children_leaf_and_lock_links_still_refused(self):
        outside = self.home/'outside'; outside.mkdir()
        for child, command in (
            ('themes', ['theme', 'save', 'saved']),
            ('modules', ['module', 'save', 'directory']),
            ('backups', ['backup', 'create']),
            ('.operation.lock', ['theme', 'save', 'saved']),
        ):
            with self.subTest(child=child):
                link = self.real/child
                link.symlink_to(outside, target_is_directory=True)
                self.invoke(*command, code=1)
                self.assertTrue(link.is_symlink())
                self.assertEqual(list(outside.iterdir()), [])
                link.unlink()
        leaf = self.write(outside/'saved.toml', NEW)
        (self.real/'themes').mkdir()
        (self.real/'themes/saved.toml').symlink_to(leaf)
        self.invoke('theme', 'save', 'saved', '--force', code=1)
        self.assertEqual(leaf.read_text(), NEW)

    def test_active_config_parent_and_leaf_protections(self):
        real_config = self.home/'real-config'; real_config.mkdir()
        linked_config = self.home/'linked-config'
        linked_config.symlink_to(real_config, target_is_directory=True)
        self.theme()
        self.env['STARSHIP_CONFIG'] = str(linked_config/'starship.toml')
        self.invoke('theme', 'apply', 'purple', code=1)
        self.assertEqual(list(real_config.iterdir()), [])
        self.env['STARSHIP_CONFIG'] = str(self.config)
        self.config.unlink()
        target = self.write(real_config/'starship.toml', OLD)
        self.config.symlink_to(target)
        self.invoke('theme', 'apply', 'purple', '--replace-link')
        self.assertFalse(self.config.is_symlink())
        self.assertEqual(target.read_text(), OLD)

    def test_delete_uses_file_identity_across_path_spellings(self):
        target = self.theme('saved', OLD)
        self.env['STARSHIP_CONFIG'] = str(self.store/'themes/saved.toml')
        # Model Windows namespace aliases whose resolved spellings can differ
        # (C:\\... versus \\\\?\\C:\\...) while they identify the same file.
        with patch.dict(os.environ, self.env, clear=True), \
             patch.object(Path, 'resolve', autospec=True, side_effect=lambda p: p):
            with self.assertRaisesRegex(core.Failure, 'active config'):
                core.run(['theme', 'delete', 'saved', '--force'])
        self.assertEqual(target.read_text(), OLD)
        self.assertFalse((self.real/'backups').exists())

    def test_read_only_and_static_commands(self):
        before = sorted(self.real.iterdir())
        for command in [('module', 'list'), ('backup', 'list'), ('list', '--json'),
                        ('current', '--json'), ('doctor', '--json')]:
            self.invoke(*command)
        self.assertEqual(sorted(self.real.iterdir()), before)
        self.store.unlink()
        self.store.symlink_to(self.home/'missing')
        for command in [('--help',), ('--version',), ('completion', 'bash'),
                        ('completion', 'zsh'), ('completion', 'fish')]:
            self.invoke(*command)
        self.assertFalse((self.home/'missing').exists())

    @unittest.skipUnless(shutil.which('bash'), 'Bash unavailable')
    def test_bash_wrapper_uses_shared_resolution(self):
        env = dict(self.env, PATH=os.environ.get('PATH', ''))
        result = subprocess.run([shutil.which('bash'), str(ROOT/'bin/blastoff'),
                                 'theme', 'save', 'bash-saved', '--json'],
                                env=env, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['path'], str(self.real/'themes/bash-saved.toml'))


@unittest.skipUnless(os.name == 'nt', 'Requires native Windows junctions')
class WindowsStorageLinks(Harness):
    def test_junction_mutation_and_shared_lock(self):
        real = self.home/'real store'; real.mkdir()
        cmd = str(Path(os.environ['SystemRoot'])/'System32/cmd.exe')
        result = subprocess.run([cmd, '/d', '/c', 'mklink', '/J', str(self.store), str(real)],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(lambda: os.rmdir(self.store) if os.path.lexists(self.store) else None)
        self.write(self.config, OLD)
        self.invoke('theme', 'save', 'saved')
        self.assertEqual((real/'themes/saved.toml').read_text(), OLD)
        self.assertTrue(self.store.lstat().st_file_attributes & 0x400)
        (real/'.operation.lock').mkdir()
        for root in (self.store, real):
            self.env['BLASTOFF_HOME'] = str(root)
            self.assertIn('stale lock', self.invoke('theme', 'save', 'blocked', code=1).stderr)
        self.assertTrue((real/'.operation.lock').is_dir())
        (real/'.operation.lock').rmdir()
        self.env['BLASTOFF_HOME'] = str(self.store)
        self.env['STARSHIP_CONFIG'] = str(real/'themes/saved.toml')
        self.invoke('theme', 'delete', 'saved', '--force', code=1)
        self.assertEqual((real/'themes/saved.toml').read_text(), OLD)


class StorageResolution(unittest.TestCase):
    def test_windows_directory_link_targets_including_roots(self):
        # Windows path grammar/reparse fixtures, NOT native filesystem evidence.
        for tag in (0xA000000C, 0xA0000003):
            for target in ('\\\\?\\C:\\data', '\\\\?\\UNC\\server\\share\\data',
                           '\\\\?\\Z:\\', '\\\\?\\UNC\\offline\\share\\'):
                for available in (False, True):
                    with self.subTest(tag=tag, target=target, available=available):
                        directory = SimpleNamespace(st_mode=0o40700, st_file_attributes=0)
                        mapping = {'C:\\alias': SimpleNamespace(st_mode=0o40700,
                                   st_file_attributes=0x400, st_reparse_tag=tag)}
                        target_path = PureWindowsPath(target)
                        if available:
                            for part in (target_path, *target_path.parents):
                                mapping[str(part)] = directory

                        class WindowsPath(PureWindowsPath):
                            def lstat(self, _mapping=mapping):
                                if str(self) not in _mapping:
                                    raise FileNotFoundError(str(self))
                                return _mapping[str(self)]

                        with patch.object(core, 'Path', WindowsPath), \
                             patch.object(os, 'readlink', return_value=target):
                            if available:
                                self.assertEqual(core.storage_root(WindowsPath('C:/alias')), target_path)
                            else:
                                with self.assertRaises((core.Failure, FileNotFoundError)):
                                    core.storage_root(WindowsPath('C:/alias'))

    def test_inaccessible_component_propagates_without_mkdir(self):
        with patch.object(Path, 'lstat', side_effect=PermissionError('denied')), \
             patch.object(Path, 'mkdir') as mkdir:
            with self.assertRaises(PermissionError):
                core.storage_root(Path.cwd()/'store')
            mkdir.assert_not_called()

    def test_unsupported_reparse_point_is_not_followed(self):
        info = SimpleNamespace(st_mode=0o40700, st_file_attributes=0x400, st_reparse_tag=123)
        with patch.object(Path, 'lstat', return_value=info), patch.object(os, 'readlink') as follow:
            with self.assertRaisesRegex(core.Failure, 'Unsupported storage directory reparse'):
                core.storage_root(Path.cwd()/'store')
            follow.assert_not_called()
