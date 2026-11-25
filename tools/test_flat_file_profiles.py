#!/usr/bin/env python3
"""Flat profile declarations, inheritance, public sources and legacy groups in owned roots."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
from catalog import Catalog
from profile_views import selected
from transactions import Store, digest
from file_platform import state_root


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def mapping(name, source, target):
    return dict(id=name, source=source, target=target, strategy='link', app='example', category='config')


class FlatProfiles(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dots-flat-files-')
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.root = self.home / '-checkout ü'
        env = dict(HOME=str(self.home), DOTS=str(self.root), XDG_STATE_HOME=str(self.home/'state'),
                   XDG_CONFIG_HOME=str(self.home/'config'), XDG_CACHE_HOME=str(self.home/'cache'),
                   XDG_DATA_HOME=str(self.home/'data'))
        self.environment = patch.dict(os.environ, env)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.all_platforms = ['termux', 'linux', 'wsl', 'windows']
        write(self.root/'.dots/sources.json', dict(schema=2, sources=[
            dict(id='dots', path='.', roots=['config'], platforms=self.all_platforms),
            dict(id='nvim', path='config/nvim', roots=['.'], platforms=self.all_platforms),
            dict(id='private', path='private', roots=[], excluded=True, platforms=self.all_platforms)]))
        write(self.root/'.dots/files.json', dict(schema=3, resources=[
            dict(id='dots:reserved', platforms=self.all_platforms)], renames={'dots:old': 'dots:reserved'}))
        self.base = self.root/'profiles/linux'
        self.child = self.base/'distros/example'
        self.shared = mapping('same', '${DOTS}/outside/ü', '${CONFIG}/shared')
        self.local = mapping('same', '${PROFILE}/custom/a', '${CONFIG}/local')
        self.profile(self.base, 'linux', [self.shared, self.local])
        self.profile(self.child, 'linux/example', [])
        for path in (self.root/'outside/ü', self.base/'custom/a', self.child/'custom/new', self.root/'config/nvim/init.lua'):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('contents')

    def profile(self, root, identity, files):
        write(root/'profile.json', dict(schema=1, id=identity, files=files))

    def catalog(self, identity='linux/example'):
        context = selected(self.root, identity)
        return Catalog(self.root, context['facts']['platform'], profile=context)

    def test_unregistered_rows_and_distinct_owners(self):
        reader = self.catalog()
        rows = {r['id']: r for r in reader.records()}
        self.assertEqual(set(rows), {'dots:same', 'linux:same'})
        self.assertEqual(rows['linux:same']['source'], str(self.base/'custom/a'))
        self.assertEqual(rows['dots:same']['source_spec'], self.shared['source'])
        self.assertEqual(reader.profile_owner()['id'], 'linux-example')
        self.assertEqual(reader.source_owner(reader.resolve_source('${DOTS}/config/nvim/init.lua'))['id'], 'nvim')
        self.assertEqual(reader.mapping_layers['linux','same']['id'], 'linux')
        self.assertFalse(state_root().exists())

    def test_child_override_keeps_parent_position_and_new_ids_append(self):
        from profile_config import file_rows
        extra = dict(self.shared, id='extra', target='${CONFIG}/extra')
        override = dict(self.shared, target='${CONFIG}/changed')
        self.profile(self.child, 'linux/example', [extra, override])
        rows = [(key, layer['id'], row['target']) for key, layer, row in
                file_rows(self.root, selected(self.root, 'linux/example'))]
        self.assertEqual(rows, [('dots:same', 'linux/example', '${CONFIG}/changed'),
                                ('linux:same', 'linux', '${CONFIG}/local'),
                                ('dots:extra', 'linux/example', '${CONFIG}/extra')])

    def test_overrides_remove_inherited_and_metadata_undo(self):
        reader = self.catalog()
        source = reader.profile_owner(reader.profile['layers'][0])
        doc = reader.manifest(source)
        doc['resources'] = []
        ops = reader.updates({'linux': doc})
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]['data']['files'], [dict(self.local, source='${DOTS}/profiles/linux/custom/a', enabled=False)])
        guards = {str(p): digest(p) for p in reader.input_paths()}
        result = Store(state_root()).apply('test-flat', ops, guards, retain=True, catalogs=reader.lock_paths())
        self.assertEqual({r['id']:r['status'] for r in self.catalog().records()}['linux:same'], 'stashed')
        store = Store(state_root())
        ops, guards, locks = store.inverse(result['id'])
        store.apply('undo', ops, guards, catalogs=locks)
        self.assertEqual(json.loads((self.child/'profile.json').read_text())['files'], [])

    def test_child_edit_preserves_parent_and_skips_unrelated_rows(self):
        reader = self.catalog()
        owner = reader.source_owner(self.root/'outside/ü')
        doc = reader.manifest(owner)
        doc['resources'][0]['target'] = '${CONFIG}/moved'
        ops = reader.updates({'dots': doc})
        updated = next(op['data'] for op in ops if op['path'] == str(self.child/'profile.json'))
        self.assertEqual(updated['files'], [dict(self.shared, target='${CONFIG}/moved')])
        self.assertEqual(json.loads((self.base/'profile.json').read_text())['files'], [self.shared, self.local])

    def test_old_groups_replace_new_rows_merge_and_reserved_names(self):
        self.profile(self.child, 'linux/example', {'dots': []})
        self.assertEqual([r['id'] for r in self.catalog().records()], ['linux:same'])
        self.profile(self.child, 'linux/example', [dict(self.shared, id='old')])
        with self.assertRaisesRegex(ValueError, 'renamed'):
            self.catalog().records()
        self.profile(self.child, 'linux/example', [self.shared, self.shared])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.catalog().records()

    def test_sources_reject_traversal_private_and_undeclared_repositories(self):
        reader = self.catalog()
        (self.root/'outside/nested/.git').mkdir(parents=True)
        for source in ('${DOTS}/private/key', '${DOTS}/.dots/store', '${DOTS}/outside/nested/file',
                       '${PROFILE}/../config', '${THEME}/status', '${THEME}/../../secret',
                       '${HOME}/other', '${DOTS}/D:/escape', '${THEME}/x/y/z'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                reader.resolve_source(source)

    def test_symlink_cannot_relabel_an_excluded_or_nested_source(self):
        reader = self.catalog()
        (self.root/'outside/alias').symlink_to(self.root, target_is_directory=True)
        (self.root/'outside/loop').symlink_to(self.root/'outside/loop')
        for source in ('${DOTS}/outside/alias/private/file', '${DOTS}/outside/alias/config/nvim/init.lua',
                       '${DOTS}/outside/alias/.dots/files.json', '${DOTS}/outside/loop'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                reader.resolve_source(source)

    def test_shipped_flat_profiles_use_portable_sources_and_canonical_ids(self):
        import shutil
        from profile_config import file_rows
        from config_namespace import Namespace, resolve_request
        from config_menu import Inventory, tree_rows
        for name in ('sources.json', 'files.json'):
            shutil.copyfile(ROOT/'.dots'/name, self.root/'.dots'/name)
        for platform in self.all_platforms:
            profile = self.root/'profiles'/platform/'profile.json'
            profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/'profiles'/platform/'profile.json', profile)
        for platform in self.all_platforms:
            reader = self.catalog(platform)
            rows = {r['id']:r for r in reader.records()}
            self.assertIn('nvim:nvim', rows)
            flavors = [r for r in rows.values() if r['app'] == 'yazi' and r['repository'] == 'theme']
            flavor, = flavors
            base = '${APP_CONFIG:yazi}' if platform == 'windows' else '${CONFIG}/yazi'
            self.assertEqual((flavor['id'], flavor['strategy'], flavor['source_spec'], flavor['target_spec']),
                             ('theme:yazi', 'directory-link', '${THEME}/yazi', base + '/flavors/dots.yazi'))
            self.assertEqual(Path(flavor['target']), Path(rows['dots:yazi']['target']) / 'flavors/dots.yazi')
            if platform == 'termux':
                for name in ('dots:gitmux', 'dots:television', 'termux:termux', 'theme:bat'):
                    self.assertIn(name, rows)
                self.assertNotIn('dots:vivid', rows)
                self.assertNotIn('dots:file-config-eza-themes-catppuccin-mocha-mauve-yml', rows)
                profile = selected(self.root, platform)
                mappings = {key: spec for key, _, spec in file_rows(self.root, profile)}
                inventory = Namespace((), files=mappings.items())
                labels = {'termux:config-json': 'pkgs', 'termux:config': 'codex-termux',
                          'termux:config-toml': 'mise', 'termux:method': 'zsh-system-clipboard'}
                for key, app in labels.items():
                    spelling = f'apps.{app}.files["{key}"]'
                    previous = f'apps.config.files["{key}"]'
                    self.assertEqual(mappings[key]['app'], app)
                    self.assertEqual(inventory.forms[spelling], 'files.' + key)
                    self.assertEqual(inventory.forms[previous], 'files.' + key)
                    self.assertEqual(inventory.view_key('files.' + key, 'apps'), spelling)
                    self.assertEqual(inventory.query_key('files.' + key, previous), previous)
                result = resolve_request(self.root, profile, 'files.config', 'get')[1]['value']
                self.assertEqual(result, [row for key, row in mappings.items()
                                          if row['app'] == 'config' or key in labels])
                key = 'termux:config-toml'
                for group in ('apps.mise.files', 'config.files', 'files.apps.config'):
                    owner, report = resolve_request(self.root, profile, f'{group}["{key}"]', 'explain')
                    self.assertEqual((owner, report['value']), ('files.' + key, mappings[key]))
                    self.assertEqual(Path(report['source']), self.root/'profiles/termux/profile.json')
                shutil.copytree(ROOT/'default', self.root/'default')
                browser = Inventory(self.root, platform)
                for group in ('apps.config.files', 'apps.mise.files', 'files.apps.config', 'files.apps.mise'):
                    self.assertIn(f'{group}["{key}"]', [row.key for row in tree_rows(browser, group)])
            if platform == 'wsl':
                inherited = {key: spec for key, _, spec in file_rows(self.root, selected(self.root, 'linux'))}
                local = {'dots:vivid', 'dots:file-config-eza-themes-catppuccin-mocha-mauve-yml'}
                wsl = {key: (layer['id'], spec) for key, layer, spec in file_rows(self.root, selected(self.root, 'wsl'))}
                self.assertEqual(list(wsl), list(inherited))
                self.assertEqual({key for key, (layer, _) in wsl.items() if layer == 'wsl'}, local)
                for key, spec in inherited.items():
                    self.assertEqual(wsl[key], ('wsl', dict(spec, enabled=False)) if key in local else ('linux', spec))
            self.assertFalse(any(r['status']=='conflict' for r in rows.values()))
            self.assertFalse(state_root().exists())

    def test_foreign_profiles_inspection_only_and_legacy_registry(self):
        win = self.root/'profiles/windows'
        other = mapping('foreign', '${PROFILE}/custom/win', '${HOME}/win')
        self.profile(win, 'windows', [other])
        self.assertNotIn('windows:foreign', {r['id'] for r in self.catalog().records()})
        row = next(r for r in self.catalog().records(include_inactive=True) if r['id']=='windows:foreign')
        self.assertFalse(row['applicable'])
        self.assertEqual(row['mapping_profile'], 'windows')
        self.profile(win, 'windows', {'dots': []})
        write(self.root/'.dots/files.json', dict(schema=3, renames={}, resources=[
            dict(id='linux-example:child', platforms=['linux']),
            dict(id='theme:colors', platforms=self.all_platforms)]))
        self.assertEqual(self.catalog('windows').records(), [])

    def test_completion_is_metadata_only_and_reports_rooted_profile_sources(self):
        from catalog import completion_ids
        from profile_views import manifests
        theme = mapping('colors', '${THEME}/palette.json', '${CONFIG}/colors')
        self.profile(self.base, 'linux', [self.shared, self.local, theme])
        self.profile(self.root/'profiles/windows', 'windows', [dict(self.local,id='elsewhere')])
        with patch.object(Catalog, 'records', side_effect=AssertionError('observed live targets')), \
                patch.object(Catalog, 'validate_source_boundary', side_effect=AssertionError('walked source paths')):
            names = completion_ids(self.root, 'file-resource', 'linux')
            self.assertEqual(names, ['dots:same', 'linux:same', 'theme:colors'])
            self.assertIn('windows:elsewhere', completion_ids(self.root, 'file-resource', 'linux', True))
        details = {r['id']:r for r in manifests(self.root, selected(self.root, 'linux/example'))}
        self.assertEqual(details['theme:colors']['source_spec'], theme['source'])
        self.assertEqual(details['linux:same']['source_spec'], self.local['source'])
        self.assertFalse(state_root().exists())

    def test_bash_and_native_resource_completion_with_explicit_platform(self):
        import shutil
        import subprocess
        if not shutil.which('bash') or os.name == 'nt':
            self.skipTest('requires POSIX Bash and shared native bridge')
        shutil.copytree(ROOT/'lib/dots', self.root/'lib/dots', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.root/'bin').mkdir()
        for name in ('dots', 'dots-files', 'dots-files-edit'):
            shutil.copy2(ROOT/'bin'/name, self.root/'bin'/name)
        self.profile(self.root/'profiles/windows', 'windows', [dict(self.local,id='elsewhere')])
        args = ['files', 'edit', '--platform', 'linux', '']
        env = dict(os.environ, DOTS_PROFILE_CHECKOUT=str(self.root), DOTS_PROFILE_BIN_PATHS='')
        for cmd in ([str(self.root/'bin/dots'),'__complete','bash','5','--','dots',*args],
                    [sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete',*args]):
            proc = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('candidate\tdots:same\t', proc.stdout)
            self.assertIn('candidate\tlinux:same\t', proc.stdout)
            self.assertNotIn('windows:elsewhere', proc.stdout)
        self.assertFalse(state_root().exists())

    def test_unpublished_and_pinned_theme_links_and_owned_children(self):
        from file_platform import state_root
        theme = mapping('colors', '${THEME}/yazi/flavor.toml', '${CONFIG}/yazi/colors')
        directory = dict(mapping('app', '${DOTS}/config/nvim', '${CONFIG}/yazi'), strategy='directory-link')
        theme_directory = dict(mapping('flavor-dir', '${THEME}/yazi', '${HOME}/custom-flavor'), strategy='directory-link')
        self.profile(self.base, 'linux', [theme, directory, theme_directory])
        reader = self.catalog()
        row = next(r for r in reader.records() if r['repository'] == 'theme')
        self.assertEqual(row['status'], 'theme-unavailable')
        self.assertFalse(state_root().exists())
        gen = state_root()/'themes/generations/g.test'
        artifact = gen/'yazi/flavor.toml'
        artifact.parent.mkdir(parents=True)
        artifact.write_text('palette')
        (gen/'status').write_text('committed')
        (state_root()/'themes/current').write_text(gen.name)
        reader.theme_root.parent.mkdir()
        reader.theme_root.symlink_to(gen, target_is_directory=True)
        target = Path(row['target'])
        target.parent.mkdir(parents=True)
        target.symlink_to(artifact)
        self.assertEqual(next(r['status'] for r in reader.records() if r['repository']=='theme'), 'linked-elsewhere')
        target.unlink()
        target.symlink_to(reader.theme_root/'yazi/flavor.toml')
        observed = {r['id']:r for r in reader.records()}
        self.assertEqual(observed['theme:colors']['status'], 'linked')
        self.assertEqual(observed['theme:flavor-dir']['status'], 'missing')
        Path(observed['theme:flavor-dir']['target']).symlink_to(reader.theme_root/'yazi', target_is_directory=True)
        self.assertEqual(next(r['status'] for r in reader.records() if r['id']=='theme:flavor-dir'), 'linked')


if __name__ == '__main__':
    unittest.main()
