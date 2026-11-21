#!/usr/bin/env python3
"""Exercise hand-authored flat profiles through Config and managed-file commands."""
import json
import os
from pathlib import Path
import shutil
import unittest

import test_profile_backend as fixtures
from file_platform import state_root
from managed_destination import published_generation
from transactions import Store, digest


class FlatLifecycle(unittest.TestCase):
    write = fixtures.ProfileBackend.write
    files = fixtures.ProfileBackend.files
    config = fixtures.ProfileBackend.config
    undo = fixtures.ProfileBackend.undo

    def setUp(self):
        fixtures.ProfileBackend.setUp(self)
        for manifest in self.root.glob('profiles/*/profile.json'):
            self.write(manifest, dict(schema=1, id=manifest.parent.name, files=[]))
        self.app = self.root / 'config' / 'editor'
        self.app.mkdir()
        self.config_root = Path(self.env['XDG_CONFIG_HOME'])
        self.config_root.mkdir()
        self.directory = dict(id='editor', source='${DOTS}/config/editor', target='${CONFIG}/editor',
                              category='config', app='editor', strategy='directory-link')
        self.generated = dict(id='colors', source='${THEME}/colors.json', target='${CONFIG}/editor/colors.json',
                              category='theme', app='editor', strategy='link')
        self.rows = [self.directory, self.generated]
        self.write(self.path, dict(schema=1, id=self.platform, files=self.rows))

    def test_config_reads_and_reversible_flat_edits(self):
        before = self.registry.read_bytes()
        self.assertEqual(json.loads(self.config('get','files','--json').stdout)['value'], self.rows)
        inverse = self.rows[::-1]
        result = json.loads(self.config('set','files',json.dumps(inverse),'--json-value','--json',
                                        profile_scope=False).stdout)
        self.assertEqual(json.loads(self.path.read_text())['files'], inverse)
        self.undo(result['transaction'])
        self.assertEqual(json.loads(self.path.read_text())['files'], self.rows)
        self.assertEqual(self.registry.read_bytes(), before)
        self.files('edit','theme:colors','--id','editor-colors','--yes')
        self.assertEqual(json.loads(self.path.read_text())['files'][1]['id'],'editor-colors')
        self.assertEqual(json.loads(self.registry.read_text())['renames']['theme:colors'],'theme:editor-colors')

    def test_config_browser_keeps_path_spelling_and_profile_provenance(self):
        from config_menu import Inventory
        shutil.copytree(fixtures.ROOT / 'default', self.root / 'default', dirs_exist_ok=True)
        row = dict(self.directory, id='local', source='${DOTS}/profiles/' + self.platform + '/config/local',
                   target='${CONFIG}/local')
        self.write(self.path, dict(schema=1, id=self.platform, files=[row]))
        inventory = Inventory(self.root, self.platform)
        option = inventory.find('files.'+self.platform+':local')
        self.assertEqual(option.value, row['source'])
        self.assertEqual(option.source, str(self.path))
        self.assertTrue(option.local)

    def test_category_correction_and_rename_preserve_existing_link(self):
        source = self.path.parent/'system/etc/os-release'
        source.parent.mkdir(parents=True)
        source.write_text('ID=fixture\n')
        target = self.config_root/'os-release'
        target.symlink_to(source)
        original_link = target.lstat()
        row = dict(id='file-system-etc-os-release', source='${PROFILE}/system/etc/os-release',
                   target='${CONFIG}/os-release', category='script', app='system', strategy='link')
        self.write(self.path, dict(schema=1, id=self.platform, files=[row]))
        old = self.platform+':'+row['id']
        new = self.platform+':os-release'
        args = ['edit', old, '--id','os-release','--category','config','--json']
        preview = json.loads(self.files(*args,'--dry-run').stdout)
        self.assertEqual(preview['items'][-1]['old_category'], 'script')
        self.assertEqual(preview['items'][-1]['category'], 'config')
        self.assertFalse(state_root().exists())
        result = json.loads(self.files(*args,'--yes').stdout)
        self.assertEqual(json.loads(self.path.read_text())['files'], [dict(row, id='os-release', category='config')])
        self.assertEqual(json.loads(self.registry.read_text())['renames'][old], new)
        self.files('edit',new,'--category','../bad','--yes',code=1)
        again = json.loads(self.files('edit',new,'--category','config','--yes','--json').stdout)
        self.assertEqual(again['status'], 'unchanged')
        self.undo(result['transaction'])
        self.assertEqual(json.loads(self.path.read_text())['files'], [row])
        self.assertTrue(os.path.samestat(original_link, target.lstat()))
        self.assertEqual(target.readlink(), source)

    def test_generated_check_repair_stash_and_undo(self):
        target = self.app / 'colors.json'
        (self.config_root/'editor').symlink_to(self.app, target_is_directory=True)
        before = self.path.read_bytes()
        self.files('check','--repo','theme','--yes','--json')
        self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(state_root().exists())
        active = state_root() / 'current/theme'
        snapshot = state_root() / 'themes/generations/g.fixture'
        snapshot.mkdir(parents=True)
        (snapshot/'colors.json').write_text('{}')
        (snapshot/'status').write_text('committed\n')
        (state_root()/'themes/current').write_text(snapshot.name + '\n')
        active.parent.mkdir()
        active.symlink_to(snapshot, target_is_directory=True)
        self.files('repair','theme:colors','--yes','--json')
        self.assertEqual(os.readlink(target), str(active/'colors.json'))
        self.files('stash','theme:colors','--yes','--json')
        self.assertFalse(target.is_symlink())
        self.files('stash','theme:colors','--restore','--yes','--json')
        self.assertEqual(os.readlink(target), str(active/'colors.json'))
        self.assertEqual((snapshot/'colors.json').read_text(), '{}')

    def yazi_directory(self):
        active = state_root()/'current/theme'
        snapshot = state_root()/'themes/generations/g.fixture'
        (snapshot/'yazi').mkdir(parents=True)
        (snapshot/'status').write_text('committed\n')
        (state_root()/'themes/current').write_text(snapshot.name)
        active.parent.mkdir()
        active.symlink_to(snapshot, target_is_directory=True)
        for name in ('flavor.toml', 'tmtheme.xml'):
            (snapshot/'yazi'/name).write_text(name)
        app = self.config_root/'editor'
        app.symlink_to(self.app, target_is_directory=True)
        (self.app/'flavors').mkdir()
        row = dict(self.generated, id='yazi', app='yazi', strategy='directory-link', source='${THEME}/yazi',
                   target='${CONFIG}/editor/flavors/dots.yazi')
        self.write(self.path, dict(schema=1, id=self.platform, files=[self.directory, row]))
        return active/'yazi', app/'flavors/dots.yazi', row

    def assert_flavor_migration_required(self, source, target):
        guidance = 'dots files install --component files --resource theme:yazi --dry-run'
        for operands in [('theme:yazi',), (str(source), str(target))]:
            denied = self.files('link', *operands, '--yes', '--backup', '--json', code=1)
            self.assertIn(guidance, denied.stderr)
        repair = json.loads(self.files('repair', 'theme:yazi', '--yes', '--json', code=1).stdout)
        self.assertEqual(repair['items'][0]['repair_action'], 'unresolved')
        self.assertIn(guidance, repair['items'][0]['reason'])

    def test_unowned_split_flavor_preserved_including_extra_files(self):
        source, target, _ = self.yazi_directory()
        target.mkdir()
        for name in ('flavor.toml', 'tmtheme.xml'):
            (target/name).symlink_to(source/name)
        for extra in (False, True):
            if extra:
                (target/'my-custom-file').write_text('keep me')
            before = digest(target)
            self.assert_flavor_migration_required(source, target)
            self.assertEqual(digest(target), before)
        self.assertFalse((state_root()/'installation.json').exists())

    def test_split_flavor_preserves_child_receipts_even_when_directory_disappears(self):
        source, target, row = self.yazi_directory()
        profile = json.loads(self.path.read_text())
        names = [('flavor.toml','yazi-flavor'), ('tmtheme.xml','yazi-syntax')]
        children = [dict(row, id=name, source=row['source']+'/'+file, target=row['target']+'/'+file,
                         strategy='link') for file, name in names]
        self.write(self.path, dict(profile, files=[self.directory, *children]))
        target.mkdir()
        for file, _ in names:
            self.files('ln', str(source/file), str(target/file), '--yes', '--json')
        self.write(self.path, profile)
        receipt = state_root()/'installation.json'
        before = receipt.read_bytes()
        self.assert_flavor_migration_required(source, target)
        for file, _ in names:
            (target/file).unlink()
        target.rmdir()
        self.assert_flavor_migration_required(source, target)
        self.assertFalse(target.is_symlink())
        self.assertEqual(receipt.read_bytes(), before)

    def test_direct_flavor_link_and_repair_create_missing_and_keep_correct_directory(self):
        source, target, _ = self.yazi_directory()
        self.files('link', 'theme:yazi', '--yes', '--json')
        self.assertEqual(target.readlink(), source)
        self.files('ln', str(source), str(target), '--yes', '--json')
        correct = json.loads(self.files('repair','theme:yazi','--dry-run','--json').stdout)
        self.assertEqual(correct['items'][0]['repair_action'], 'unchanged')
        target.unlink()
        self.files('repair','theme:yazi','--yes','--json')
        self.assertEqual(target.readlink(), source)

    def test_check_all_platforms_removes_only_the_foreign_declaration(self):
        platform = 'linux' if self.platform == 'windows' else 'windows'
        manifest = self.root / 'profiles' / platform / 'profile.json'
        row = dict(self.directory, id='absent', source='${PROFILE}/config/absent')
        self.write(manifest, dict(schema=1, id=platform, files=[row]))
        before = self.path.read_bytes()
        result = json.loads(self.files('check','--all-platforms','--yes','--json').stdout)
        self.assertEqual(result['counts']['removed'], 1)
        self.assertEqual(json.loads(manifest.read_text())['files'], [])
        self.assertEqual(self.path.read_bytes(), before)

    def test_old_setup_publication_requires_its_completed_transaction(self):
        state = state_root()
        active = state / 'current/theme'
        generation = state / 'themes/generations/g.setup'
        generation.mkdir(parents=True)
        active.parent.mkdir()
        active.symlink_to(generation, target_is_directory=True)
        (generation/'status').write_text('staged\n')
        (state/'themes/current').write_text(generation.name+'\n')
        with self.assertRaises(ValueError):
            published_generation(active)

        transaction = 'a' * 32
        journal = Store(state).root / transaction / 'journal.json'
        journal.parent.mkdir(parents=True)
        self.write(journal, dict(schema=1, id=transaction, status='applying'))
        entry = dict(id='theme:active', after=digest(active))
        receipt = state / 'installation.json'
        self.write(receipt, dict(schema=1, entries={str(active):entry}, transactions=[transaction]))
        with self.assertRaises(ValueError):
            published_generation(active)
        self.write(journal, dict(schema=1, id=transaction, status='complete'))
        guards = {}
        self.assertEqual(published_generation(active, guards), generation)
        self.assertTrue({str(active),str(receipt),str(journal)} <= set(guards))
        (state/'themes/current').write_text('g.elsewhere\n')
        with self.assertRaises(ValueError):
            published_generation(active)

    def test_remove_unpublished_theme_mapping_with_absent_target(self):
        result = json.loads(self.files('remove','theme:colors','--yes','--json').stdout)
        self.assertEqual(json.loads(self.path.read_text())['files'], [self.directory])
        self.undo(result['id'])
        self.assertEqual(json.loads(self.path.read_text())['files'], self.rows)

    def test_remove_replaced_mapping_preserves_winning_link_and_receipt(self):
        from catalog import Catalog
        identity = self.platform + ':tmux'
        loser = dict(self.directory, id='tmux', app='tmux', source='${PROFILE}/config/tmux', target='${CONFIG}/tmux')
        winner = dict(loser, source='${DOTS}/config/tmux', replaces=[identity])
        sibling = dict(loser, id='other', source='${PROFILE}/config/other', target='${CONFIG}/other')
        profile = dict(schema=1, id=self.platform, files=[loser, winner, sibling])
        self.write(self.path, profile)
        registry = dict(schema=3, resources=[dict(id=name, platforms=[self.platform])
                                             for name in ('dots:tmux', identity)], renames={})
        self.write(self.registry, registry)
        source = self.root/'config/tmux'
        source.mkdir()
        (source/'tmux.conf').write_text('shared config')
        target = self.config_root/'tmux'
        self.files('ln', str(source), str(target), '--yes', '--json')
        receipt = state_root()/'installation.json'
        self.assertEqual(json.loads(receipt.read_text())['entries'][str(target)]['id'], 'dots:tmux')
        receipt_before, registry_before, link_before = receipt.read_bytes(), self.registry.read_bytes(), target.lstat()
        local = self.path.parent/'config/tmux'
        for present, action in ((False, 'rm'), (True, 'remove')):
            with self.subTest(present=present):
                if present:
                    local.mkdir(parents=True)
                before = self.path.read_bytes()
                self.files('link', identity, '--yes', '--json', code=1)
                preview = json.loads(self.files(action, identity, '--dry-run', '--json').stdout)
                self.assertEqual([(r['id'], r['status']) for r in preview['items']], [(identity, 'remove-mapping')])
                self.assertIn('dots:tmux', preview['items'][0]['reason'])
                self.assertEqual(self.path.read_bytes(), before)
                result = json.loads(self.files(action, identity, '--yes', '--json').stdout)
                self.assertEqual({r['path'] for r in result['operations']}, {str(self.path)})
                self.assertEqual(json.loads(self.path.read_text())['files'], [winner, sibling])
                effective = {r['id']: r for r in Catalog(self.root,self.platform).records()}
                self.assertNotIn(identity, effective)
                self.assertEqual(effective['dots:tmux']['status'], 'linked')
                self.assertEqual(local.exists(), present)
                self.assertEqual(target.readlink(), source)
                self.assertTrue(os.path.samestat(link_before, target.lstat()))
                self.assertEqual(receipt.read_bytes(), receipt_before)
                self.assertEqual(self.registry.read_bytes(), registry_before)
                self.undo(result['id'])
                self.assertEqual(json.loads(self.path.read_text()), profile)
                self.assertTrue(os.path.samestat(link_before, target.lstat()))

    def test_remove_inherited_missing_source_masks_only_the_selected_profile(self):
        from catalog import Catalog
        from manage import Manager
        from types import SimpleNamespace
        base = self.root/'profiles/linux/profile.json'
        child = self.root/'profiles/wsl/profile.json'
        row = dict(self.directory, id='old', source='${PROFILE}/config/old', target='${CONFIG}/old')
        self.write(base, dict(schema=1, id='linux', files=[row]))
        self.write(child, dict(schema=1, id='wsl', files=[]))
        previous = base.read_bytes(), json.loads(child.read_text()), self.registry.read_bytes()
        target = self.config_root/'old'
        target.symlink_to(base.parent/'config/old', target_is_directory=True)
        original_link = target.lstat()
        catalog = Catalog(self.root, 'wsl')
        ops, guards, locks, _ = Manager(catalog).plan(SimpleNamespace(action='remove', values=['linux:old']))
        self.assertEqual([op['path'] for op in ops], [str(child)])
        result = Store(state_root()).apply('remove', ops, guards, retain=True, catalogs=locks)
        self.assertEqual(json.loads(child.read_text())['files'], [
            dict(row, source='${DOTS}/profiles/linux/config/old', enabled=False)])
        self.assertEqual(base.read_bytes(), previous[0])
        self.assertEqual(self.registry.read_bytes(), previous[2])
        self.assertTrue(os.path.samestat(original_link, target.lstat()))
        self.undo(result['id'])
        self.assertEqual((base.read_bytes(), json.loads(child.read_text()), self.registry.read_bytes()), previous)

    def test_setup_distinguishes_pinned_and_relative_theme_links(self):
        from install import Installation
        generation = state_root()/'themes/generations/g.first'
        generation.mkdir(parents=True)
        (generation/'colors.json').write_text('{}')
        active = state_root()/'current/theme'
        active.parent.mkdir()
        active.symlink_to(generation, target_is_directory=True)
        source = active/'colors.json'
        target = self.config_root/'colors.json'
        target.symlink_to(generation/'colors.json')
        setup = Installation(self.root)
        setup.add('theme:colors', target, link=source)
        self.assertEqual(setup.items[-1]['status'], 'conflict')
        target.unlink()
        target.symlink_to(os.path.relpath(source, target.parent))
        setup = Installation(self.root)
        setup.add('theme:colors', target, link=source)
        self.assertEqual(setup.items[-1]['status'], 'unchanged')
        self.assertEqual(setup.entries, {})


if __name__ == '__main__':
    unittest.main()
