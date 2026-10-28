"""Default-path and pinned active-file alias contracts in disposable homes."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from test_blastoff import Harness, core


class ActiveConfig(Harness):
    def setUp(self):
        super().setUp()
        self.env.pop('STARSHIP_CONFIG')
        self.config = self.home / '.config/starship.toml'
        self.real = self.write(self.home / 'dots/config/starship/starship.toml', 'x=1\n')
        self.config.parent.mkdir()
        try:
            self.config.symlink_to('../dots/config/starship/starship.toml')
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows file symlink privilege unavailable')
            raise
        self.theme(content='x=2\n')

    def run_core(self, *args):
        with patch.dict(os.environ, self.env, clear=True), redirect_stdout(io.StringIO()):
            return core.run(list(args))

    def test_default_apply_backup_noop_restore_and_read_only(self):
        before = self.real.read_bytes(), os.readlink(self.config)
        result = json.loads(self.invoke('doctor', '--json').stdout)
        self.assertEqual(result['config'], str(self.config))
        self.assertEqual(result['resolved_config'], str(self.real))
        self.invoke('theme', 'apply', 'purple', '--dry-run')
        self.assertEqual((self.real.read_bytes(), os.readlink(self.config)), before)
        self.assertFalse((self.store/'backups').exists())
        self.invoke('theme', 'apply', 'purple')
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(self.real.read_text(), 'x=2\n')
        saved = self.snapshots()[0]
        meta = json.loads(saved.with_suffix('.json').read_text())
        self.assertEqual(meta['source'], str(self.real))
        self.assertEqual(meta['configured_config'], str(self.config))
        self.assertEqual(meta['active_links'][0]['target'], before[1])
        inode = self.real.stat().st_ino
        self.invoke('theme', 'apply', 'purple')
        self.assertEqual(self.real.stat().st_ino, inode)
        self.assertEqual(len(self.snapshots()), 1)
        self.invoke('backup', 'restore', saved.stem)
        self.assertEqual(self.real.read_text(), 'x=1\n')
        self.assertEqual(os.readlink(self.config), before[1])

    def test_chain_module_load_save_and_physical_lock(self):
        second = self.home / '.config/second.toml'
        second.symlink_to(self.real)
        self.config.unlink(); self.config.symlink_to('second.toml')
        self.write(self.store/'modules/directory.toml', '[directory]\nstyle="red"\n')
        self.invoke('module', 'load', 'directory')
        self.invoke('theme', 'save', 'saved')
        self.assertIn('style="red"', (self.store/'themes/saved.toml').read_text())
        lock = self.real.parent / ('.'+self.real.name+'.blastoff.lock')
        lock.mkdir()
        self.assertIn('lock', self.invoke('theme', 'apply', 'purple', code=1).stderr)
        self.env['STARSHIP_CONFIG'] = str(second)
        self.invoke('theme', 'apply', 'purple', code=1)
        self.assertTrue(second.is_symlink())

    def test_retarget_before_atomic_preserves_both_targets(self):
        other = self.write(self.home/'other.toml', 'x=99\n')
        original = core.atomic
        def replace(path, data, expected=None, **kwargs):
            if path == self.real:
                self.config.unlink(); self.config.symlink_to(other)
            return original(path, data, expected, **kwargs)
        with patch.object(core, 'atomic', side_effect=replace):
            with self.assertRaisesRegex(core.Failure, 'link changed'):
                self.run_core('theme', 'apply', 'purple')
        self.assertEqual(self.real.read_text(), 'x=1\n')
        self.assertEqual(other.read_text(), 'x=99\n')

    def test_retarget_after_lock_refuses_before_writes(self):
        original = core.locks
        from contextlib import contextmanager
        @contextmanager
        def changed(paths):
            with original(paths):
                self.config.unlink(); self.config.symlink_to(self.home/'missing.toml')
                yield
        with patch.object(core, 'locks', changed):
            with self.assertRaisesRegex(core.Failure, 'link changed'):
                self.run_core('theme', 'apply', 'purple')
        self.assertEqual(self.real.read_text(), 'x=1\n')
        self.assertFalse((self.store/'backups').exists())

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO only')
    def test_fifo_target_refused_without_reading(self):
        fifo = self.home/'pipe'; os.mkfifo(fifo)
        self.config.unlink(); self.config.symlink_to(fifo)
        self.invoke('theme','apply','purple',code=1)
        self.assertFalse((self.store/'backups').exists())

    def test_external_target_edit_refuses_publication(self):
        original = core.atomic
        def replace(path, data, expected=None, **kwargs):
            if path == self.real: path.write_text('external=true\n')
            return original(path, data, expected, **kwargs)
        with patch.object(core, 'atomic', side_effect=replace):
            with self.assertRaisesRegex(core.Failure, 'changed during operation'):
                self.run_core('theme', 'apply', 'purple')
        self.assertEqual(self.real.read_text(), 'external=true\n')
        self.assertTrue(self.config.is_symlink())

    def test_unsafe_targets_and_parents_are_refused(self):
        for target in (self.home/'missing.toml', self.config, self.store/'themes/purple.toml'):
            self.config.unlink(); self.config.symlink_to(target)
            self.invoke('theme', 'apply', 'purple', code=1)
        linked = self.home/'linked-parent'
        linked.symlink_to(self.real.parent, target_is_directory=True)
        self.config.unlink(); self.config.symlink_to(linked/self.real.name)
        self.invoke('theme', 'apply', 'purple', code=1)
        self.assertEqual(self.real.read_text(), 'x=1\n')
        self.assertFalse((self.store/'backups').exists())

    def test_library_reads_remain_safe_but_direct_writes_refuse_even_with_flag(self):
        library = self.store/'themes/purple.toml'
        self.env['STARSHIP_CONFIG'] = str(library)
        self.invoke('backup', 'create')
        self.invoke('theme', 'save', 'copy')
        self.assertEqual((self.store/'themes/copy.toml').read_text(), 'x=2\n')
        self.theme('different', 'x=3\n')
        self.invoke('theme', 'apply', 'different', '--replace-link', code=1)
        self.assertEqual(library.read_text(), 'x=2\n')

    def test_canonical_provenance_survives_override_removal(self):
        self.env['STARSHIP_CONFIG'] = str(self.real)
        self.invoke('theme', 'apply', 'purple')
        self.env.pop('STARSHIP_CONFIG')
        current = json.loads(self.invoke('current', '--json').stdout)
        self.assertEqual(current['provenance']['origin'], 'local:purple')
        self.assertEqual(current['config'], str(self.config))
        self.assertTrue(current['symlink'])

    def test_legacy_alias_record_is_read_then_archived_on_write(self):
        self.invoke('theme', 'apply', 'purple')
        canonical = next((self.store/'state/provenance').glob('*.json'))
        doc = json.loads(canonical.read_text()); doc['config'] = os.path.normcase(str(self.config))
        alias = canonical.parent/(hashlib.sha256(os.path.normcase(str(self.config)).encode()).hexdigest()+'.json')
        alias.write_text(json.dumps(doc)); canonical.unlink()
        before = alias.read_bytes()
        self.assertEqual(json.loads(self.invoke('current','--json').stdout)['provenance']['origin'], 'local:purple')
        self.assertFalse(canonical.exists())
        self.invoke('theme','apply','purple')
        self.assertTrue(canonical.exists()); self.assertFalse(alias.exists())
        archived = next(alias.parent.glob(alias.stem+'.legacy-*.json'))
        self.assertEqual(archived.read_bytes(), before)

    def test_conflicting_alias_and_pending_records_are_not_authority(self):
        self.invoke('theme', 'apply', 'purple')
        canonical = next((self.store/'state/provenance').glob('*.json'))
        doc = json.loads(canonical.read_text()); doc['config'] = os.path.normcase(str(self.config))
        doc['active_sha256'] = '0'*64
        alias = canonical.parent/(hashlib.sha256(os.path.normcase(str(self.config)).encode()).hexdigest()+'.json')
        alias.write_text(json.dumps(doc))
        self.assertIn('conflicting', json.loads(self.invoke('current','--json').stdout)['provenance']['status'])
        result = json.loads(self.invoke('theme','save','--dry-run','--json').stdout)
        self.assertIn('local destination name', result['unresolved'])
        alias.with_suffix('.pending').write_text('{}')
        self.assertIn('incomplete', json.loads(self.invoke('current','--json').stdout)['provenance']['status'])
        self.invoke('theme','apply','purple')
        self.assertEqual(json.loads(self.invoke('current','--json').stdout)['provenance']['origin'], 'local:purple')


class LinkSpelling(unittest.TestCase):
    def test_windows_extended_drive_and_unc(self):
        helper = core.ui_module('active_config')
        self.assertEqual(str(helper.link_target(r'\\?\C:\Users\n\starship.toml', True)), r'C:\Users\n\starship.toml')
        self.assertEqual(str(helper.link_target(r'\\?\UNC\server\share\starship.toml', True)), r'\\server\share\starship.toml')


if __name__ == '__main__': unittest.main()
