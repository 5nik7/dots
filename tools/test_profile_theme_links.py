"""Real profile-driven publication with an isolated home, catalog and tool PATH."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_themes as fixture


class ProfileThemeLinks(unittest.TestCase):
    setUp = fixture.Themes.setUp
    shell = fixture.Themes.shell
    dots = fixture.Themes.dots
    engine = fixture.Themes.engine
    generation = fixture.Themes.generation

    def run_command(self, argv, code=0, env=None):
        result = subprocess.run(argv, env=env or self.env, cwd=self.home,
                                text=True, capture_output=True, timeout=180)
        if code is not None:
            self.assertEqual(result.returncode, code, (argv, result.stdout, result.stderr))
        return result

    def mappings(self):
        profiles = self.repo / 'profiles/linux'
        profiles.mkdir(parents=True)
        config = self.home / 'config'
        owner = self.repo/'config/yazi'
        (owner/'flavors').mkdir(parents=True)
        config.mkdir()
        (config/'yazi').symlink_to(owner, target_is_directory=True)
        self.active = self.home/'state/dots/current/theme'
        self.flavor = owner/'flavors/dots.yazi'
        self.custom = self.home/'custom color.conf'
        rows = [dict(id='yazi', app='yazi', category='config', strategy='directory-link',
                     source='${DOTS}/config/yazi', target='${CONFIG}/yazi')]
        rows.append(dict(id='yazi', app='yazi', category='theme', strategy='directory-link',
                         source='${THEME}/yazi', target='${CONFIG}/yazi/flavors/dots.yazi'))
        rows.append(dict(id='custom', app='custom', category='theme', strategy='link',
                         source='${THEME}/kitty.conf', target='${HOME}/custom color.conf'))
        self.profile = profiles/'profile.json'
        self.profile.write_text(json.dumps(dict(schema=1,id='linux',files=rows)))
        metadata = self.repo/'.dots'
        metadata.mkdir()
        (metadata/'sources.json').write_text(json.dumps(dict(schema=2,sources=[
            dict(id='dots',path='.',platforms=['linux'],roots=['config'])])))
        (metadata/'files.json').write_text(json.dumps(dict(schema=3, resources=[], renames={})))
        return rows

    def split_yazi(self):
        self.flavor.mkdir()
        for name in ('flavor.toml','tmtheme.xml'):
            (self.flavor/name).symlink_to(self.active/'yazi'/name)

    def test_directory_and_custom_across_generations_undo_and_stash(self):
        rows = self.mappings()
        self.flavor.parent.rmdir()  # a configured Yazi app need not already have flavors/
        self.dots('theme','set','nord')
        self.assertEqual(self.flavor.readlink(), self.active/'yazi')
        for name in ('flavor.toml','tmtheme.xml'):
            self.assertTrue(self.flavor.joinpath(name).is_file())
            self.assertFalse(self.flavor.joinpath(name).is_symlink())
        self.assertEqual(self.custom.readlink(), self.active/'kitty.conf')
        self.assertEqual(self.custom.read_bytes(), (self.active/'kitty.conf').read_bytes())
        generation = self.generation()
        self.dots('theme','set','nord')
        self.assertEqual(self.generation(), generation)
        self.flavor.unlink()
        self.split_yazi()
        self.dots('theme','set','catppuccin-mocha')
        current = self.generation()
        self.assertEqual(self.flavor.readlink(), self.active/'yazi')
        self.assertFalse((current/'yazi/flavor.toml').is_symlink())
        self.engine('dt_restore "' + str(current) + '"')
        self.assertFalse(self.flavor.is_symlink())
        self.assertEqual((self.flavor/'flavor.toml').readlink(), self.active/'yazi/flavor.toml')
        self.assertEqual(self.generation(), generation)
        self.custom.unlink()
        rows[-1]['enabled'] = False
        self.profile.write_text(json.dumps(dict(schema=1,id='linux',files=rows)))
        self.dots('theme','set','catppuccin-mocha')
        self.assertFalse(self.custom.exists())
        self.assertEqual(self.flavor.readlink(), self.active/'yazi')

    def test_checkout_setup_converts_old_yazi_and_restores_on_uninstall(self):
        rows = self.mappings()
        rows.append(dict(id='directory', app='custom', category='theme', strategy='directory-link',
                         source='${THEME}/yazi', target='${HOME}/custom directory'))
        directory = self.home/'custom directory'
        self.profile.write_text(json.dumps(dict(schema=1,id='linux',files=rows)))
        self.split_yazi()
        self.custom.write_bytes(b'old custom colors\n')
        command = [sys.executable, '-B', str(self.repo/'lib/dots/files/install.py')]
        opts = ['--component', 'files', '--component', 'themes', '--json']
        preview = json.loads(self.run_command(command + ['install', '--dry-run', *opts]).stdout)
        self.assertEqual(preview['status'], 'preview')
        self.assertFalse(self.flavor.is_symlink())
        self.run_command(command + ['install', '--yes', *opts])
        self.assertEqual(self.flavor.readlink(), self.active/'yazi')
        self.assertTrue((self.flavor/'flavor.toml').is_file())
        self.assertEqual(self.custom.readlink(), self.active/'kitty.conf')
        self.assertEqual((self.active/'status').read_bytes(), b'committed\n')
        self.assertTrue(directory.is_dir())
        self.assertEqual(directory.readlink(), self.active/'yazi')
        repeated = json.loads(self.run_command(command + ['install', '--yes', *opts]).stdout)
        self.assertEqual(repeated['status'], 'unchanged', repeated['items'])
        self.run_command(command + ['uninstall', '--component', 'files', '--resource', 'theme:directory', '--yes', '--json'])
        self.assertFalse(directory.is_symlink())
        self.assertTrue(self.active.is_symlink())
        selected = ['--component', 'files', '--resource', 'theme:directory', '--yes', '--json']
        self.run_command(command + ['install', *selected])
        self.assertEqual(directory.readlink(), self.active/'yazi')
        self.run_command(command + ['uninstall', '--yes', *opts])
        self.assertFalse(self.flavor.is_symlink())
        self.assertEqual((self.flavor/'tmtheme.xml').readlink(), self.active/'yazi/tmtheme.xml')
        self.assertEqual(self.custom.read_bytes(), b'old custom colors\n')
        self.assertFalse(directory.is_symlink())

    def test_reject_unsafe_destinations_and_stale_profile(self):
        rows = self.mappings()
        sys.path.insert(0, str(fixture.REPO/'lib/dots/themes'))
        import connector_paths
        from transactions import Store, digest
        with patch.dict(os.environ, self.env, clear=True):
            checkout = self.home/'other project'
            (checkout/'.git').mkdir(parents=True)
            for template in ('${HOME}/other project/config', '${HOME}/.git/config', '${HOME}/state/dots/selection'):
                rows[-1]['target'] = template
                self.profile.write_text(json.dumps(dict(schema=1,id='linux',files=rows)))
                with self.assertRaises(ValueError):
                    connector_paths.plan(self.repo, 'linux')
            rows[-1]['target'] = '${HOME}/custom color.conf'
            self.profile.write_text(json.dumps(dict(schema=1,id='linux',files=rows)))
            links, guards = connector_paths.plan(self.repo, 'linux')
            for target in connector_paths.targets(links):
                guards[str(target)] = digest(target)
            self.profile.write_text(self.profile.read_text() + '\n')
            with tempfile.TemporaryDirectory(dir=self.root) as work:
                ops = connector_paths.operations(links, self.active, Path(work), guards, self.repo)
                with self.assertRaisesRegex(ValueError, 'changed after preview'):
                    Store(self.active.parents[1]).apply('theme-set', ops, guards)
            self.assertFalse(self.custom.is_symlink())
            self.assertFalse(self.flavor.exists())

    def test_native_migration_undo_keeps_receipt_baseline(self):
        self.mappings()
        self.split_yazi()
        sys.path.insert(0,str(fixture.REPO/'lib/dots/themes'))
        import connector_paths
        from transactions import Store, digest
        with patch.dict(os.environ, self.env, clear=True):
            state = self.active.parents[1]
            state.mkdir(parents=True)
            receipt = state / 'installation.json'
            baseline = dict(id='theme:yazi', before=None, after=digest(self.flavor),
                            backup='first', index=7, catalog_ids=['theme:yazi-flavor','theme:yazi-syntax'])
            receipt.write_text(json.dumps(dict(schema=1,root=str(self.repo),
                                               entries={str(self.flavor):baseline})))
            links, guards = connector_paths.plan(self.repo, 'linux')
            for target in connector_paths.targets(links): guards[str(target)] = digest(target)
            with tempfile.TemporaryDirectory(dir=self.root) as work:
                ops = connector_paths.operations(links, self.active, Path(work), guards, self.repo)
                store = Store(state)
                done = store.apply('theme-set', ops, guards, retain=True)
            new = json.loads(receipt.read_text())['entries'][str(self.flavor)]
            self.assertEqual((new['backup'],new['index'],new['before']), ('first',7,None))
            self.assertEqual(new['catalog_ids'], ['theme:yazi'])
            self.assertEqual(new['after'], digest(self.flavor))
            inverse, guards, catalogs = store.inverse(done['id'])
            store.apply('undo', inverse, guards, catalogs=catalogs, retain=True)
            self.assertFalse(self.flavor.is_symlink())
            self.assertEqual((self.flavor/'tmtheme.xml').readlink(), self.active/'yazi/tmtheme.xml')
            self.assertEqual(json.loads(receipt.read_text())['entries'][str(self.flavor)], baseline)
            for name in ('flavor.toml', 'tmtheme.xml'):
                (self.flavor/name).unlink()
            self.flavor.rmdir()
            self.flavor.symlink_to(self.active/'yazi', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                connector_paths.plan(self.repo, 'linux')

    def test_directory_migration_preserves_foreign_or_edited_children(self):
        self.mappings()
        self.split_yazi()
        sys.path.insert(0, str(fixture.REPO/'lib/dots/themes'))
        import connector_paths
        from transactions import Store, digest
        with patch.dict(os.environ, self.env, clear=True):
            extra = self.flavor/'custom.toml'
            extra.write_text('# private flavor settings\n')
            with self.assertRaisesRegex(ValueError, 'unmanaged Yazi'):
                connector_paths.plan(self.repo, 'linux')
            self.assertEqual(extra.read_text(), '# private flavor settings\n')
            extra.unlink()
            flavor = self.flavor/'flavor.toml'
            flavor.unlink()
            flavor.write_text('custom\n')
            with self.assertRaisesRegex(ValueError, 'unmanaged Yazi'):
                connector_paths.plan(self.repo, 'linux')
            self.assertEqual(flavor.read_text(), 'custom\n')
            flavor.unlink()
            flavor.symlink_to(self.home/'my-flavor.toml')
            with self.assertRaisesRegex(ValueError, 'unmanaged Yazi'):
                connector_paths.plan(self.repo, 'linux')
            self.assertEqual(flavor.readlink(), self.home/'my-flavor.toml')
            flavor.unlink()
            flavor.symlink_to(self.active/'yazi/flavor.toml')
            links, guards = connector_paths.plan(self.repo, 'linux')
            for path in connector_paths.targets(links):
                guards.setdefault(str(path), digest(path))
            extra.write_text('added after review\n')
            with tempfile.TemporaryDirectory(dir=self.root) as work:
                ops = connector_paths.operations(links, self.active, Path(work), guards, self.repo)
                with self.assertRaisesRegex(ValueError, 'changed after preview'):
                    Store(self.active.parents[1]).apply('theme-set', ops, guards)
            self.assertEqual(extra.read_text(), 'added after review\n')

    def test_native_publisher_sets_and_reuses_whole_flavor(self):
        self.mappings()
        self.split_yazi()
        command = [sys.executable, '-B', str(self.repo/'lib/dots/themes/theme_cli.py'), 'set', 'nord']
        self.run_command(command + ['--dry-run'])
        self.assertFalse(self.flavor.is_symlink())
        self.run_command(command)
        self.assertEqual(self.flavor.readlink(), self.active/'yazi')
        before = self.generation()
        self.run_command(command)
        self.assertEqual(self.generation(), before)

    def test_child_receipt_survives_switch_and_undo(self):
        self.mappings()
        self.split_yazi()
        sys.path.insert(0, str(fixture.REPO/'lib/dots/themes'))
        import connector_paths
        from transactions import Store, digest
        with patch.dict(os.environ, self.env, clear=True):
            state = self.active.parents[1]
            state.mkdir(parents=True)
            receipt = state/'installation.json'
            logical = self.home/'config/yazi/flavors/dots.yazi/flavor.toml'
            baseline = dict(id='theme:yazi-flavor', before=None, after=digest(self.flavor/'flavor.toml'),
                            backup='1'*32, index=7)
            receipt.write_text(json.dumps(dict(schema=1, root=str(self.repo), entries={str(logical): baseline})))
            links, guards = connector_paths.plan(self.repo, 'linux')
            for target in connector_paths.targets(links):
                guards[str(target)] = digest(target)
            with tempfile.TemporaryDirectory(dir=self.root) as work:
                ops = connector_paths.operations(links, self.active, Path(work), guards, self.repo)
                store = Store(state)
                done = store.apply('theme-set', ops, guards, retain=True)
            entries = json.loads(receipt.read_text())['entries']
            self.assertEqual(set(entries), {str(self.flavor)})
            self.assertEqual(entries[str(self.flavor)]['yazi_children'], {'flavor.toml': baseline})
            self.assertEqual(entries[str(self.flavor)]['yazi_unowned'], {'tmtheme.xml': str(self.active/'yazi/tmtheme.xml')})
            inverse, guards, catalogs = store.inverse(done['id'])
            store.apply('undo', inverse, guards, catalogs=catalogs, retain=True)
            self.assertEqual(json.loads(receipt.read_text())['entries'], {str(logical): baseline})
            self.assertFalse(self.flavor.is_symlink())
            missing_backup = dict(baseline, before='1'*64)
            receipt.write_text(json.dumps(dict(schema=1, root=str(self.repo), entries={str(logical): missing_backup})))
            with self.assertRaises(ValueError):
                connector_paths.plan(self.repo, 'linux')
            self.assertEqual((self.flavor/'flavor.toml').readlink(), self.active/'yazi/flavor.toml')
            receipt.write_text(json.dumps(dict(schema=1, root=str(self.repo), entries={str(logical): baseline})))
            (self.flavor/'flavor.toml').unlink()
            (self.flavor/'tmtheme.xml').unlink()
            self.flavor.rmdir()
            self.flavor.symlink_to(self.active/'yazi', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'original split directory'):
                connector_paths.plan(self.repo, 'linux')


if __name__ == '__main__':
    unittest.main()
