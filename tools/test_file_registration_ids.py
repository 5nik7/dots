#!/usr/bin/env python3
"""Automatic Files identities across imports, links and reviewed discovery."""
import json
import os
import unittest
from unittest.mock import patch

import test_file_path_workflows as workflows


class RegistrationIds(unittest.TestCase):
    setUp = workflows.PathWorkflows.setUp
    write = workflows.PathWorkflows.write
    files = workflows.PathWorkflows.files
    run_json = workflows.PathWorkflows.run_json
    rows = workflows.PathWorkflows.rows

    def test_inactive_registry_and_historical_names_remain_reserved(self):
        inactive = next(path for path in self.root.glob('profiles/*/profile.json') if path != self.path)
        profile = json.loads(inactive.read_text())
        sample = dict(self.resource)
        del sample['platforms']
        profile['files'] = [dict(sample, id='defaults-ini', source='${DOTS}/config/other',
                                 target='${CONFIG}/other'),
                            dict(sample, id='stable-shared', source='${DOTS}/config/shared.ini',
                                 target='${CONFIG}/shared'),
                            dict(sample, id='other-platform', source='${DOTS}/config/other-platform',
                                 target='${CONFIG}/foreign')]
        self.write(inactive, profile)
        registry = json.loads(self.registry.read_text())
        registry.update(schema=3, renames={'dots:config-beta-defaults-ini': 'dots:app'})
        registry['resources'].append(dict(id='dots:beta-defaults-ini', platforms=self.resource['platforms']))
        registry['resources'].append(dict(id='dots:other-platform', platforms=[inactive.parent.name]))
        self.write(self.registry, registry)
        source = self.root/'config/beta/defaults.ini'
        source.parent.mkdir()
        source.write_text('data')
        (self.config/'custom').symlink_to(source)
        (self.root/'config/shared.ini').write_text('shared')
        (self.config/'shared').symlink_to(self.root/'config/shared.ini')
        (self.root/'config/other-platform').write_text('foreign')
        (self.config/'foreign').symlink_to(self.root/'config/other-platform')
        preview = self.run_json('fd', '--dry-run')['items']
        self.assertEqual([row['id'] for row in preview],
                         ['dots:config-beta-defaults-ini-at-config-custom', 'dots:config-other-platform',
                          'dots:stable-shared'])
        self.run_json('find', '--yes')
        self.assertEqual(self.run_json('fd')['items'], [])

    def test_batch_keeps_approved_names_when_only_second_link_is_selected(self):
        import find_links
        import manage
        import sys
        for name in ('alpha', 'beta'):
            source = self.root/'config'/name/'.prefs.ini'
            source.parent.mkdir()
            source.write_text(name)
            (self.config/name).symlink_to(source)
        preview = self.run_json('fd')['items']
        self.assertEqual([r['id'] for r in preview], ['dots:prefs-ini', 'dots:beta-prefs-ini'])
        with patch.object(sys, 'argv', ['files', 'find', '--yes', '--json']), \
                patch.object(find_links, 'review', return_value=[preview[1]]), \
                patch('sys.stdout'), patch('sys.stderr'):
            manage.main()
        self.assertEqual([row['id'] for row in self.rows()], ['beta-prefs-ini'])
        self.assertEqual(self.run_json('fd')['items'][0]['id'], 'dots:prefs-ini')

    def test_normalized_path_and_target_collisions_have_a_stable_fallback(self):
        from manage import Manager
        from registration import Registration
        names = Registration(Manager()).names
        source = self.root/'config/123.rc'
        target = '${CONFIG}/app-file'
        occupied = {}
        expected = ['dots:file-123-rc', 'dots:config-123-rc', 'dots:config-123-rc-at-config-app-file']
        for identity in expected:
            self.assertEqual(names.choose('dots', source, target, occupied), identity)
            occupied[identity] = self.root/'another', target
        final = names.choose('dots', source, target, occupied)
        self.assertRegex(final, '^dots:config-123-rc-at-config-app-file-[a-f0-9]{12}$')
        self.assertEqual(names.choose('dots', source, target, occupied), final)
        occupied[final] = self.root/'other', target
        self.assertEqual(names.choose('dots', source, target, occupied), final + '-2')

    def test_mixed_import_and_registration_share_reservations(self):
        source = self.path.parent/'config/beta/project.toml'
        source.parent.mkdir(parents=True)
        source.write_text('beta')
        beta = self.config/'beta'
        beta.symlink_to(source)
        alpha = self.config/'alpha/project.toml'
        alpha.parent.mkdir()
        alpha.write_text('alpha')
        result = self.run_json('add', str(beta), str(alpha), '--dry-run')
        self.assertEqual({r['id'] for r in result['items']},
                         {self.platform+':project-toml', self.platform+':beta-project-toml'})
        self.run_json('add', str(alpha), str(beta), '--yes')
        self.assertEqual(self.run_json('add', str(beta), str(alpha), '--yes')['status'], 'unchanged')

    def test_wsl_keeps_registered_linux_mapping_and_effective_eligibility(self):
        from catalog import Catalog
        from manage import Manager
        from registration import Registration
        source_file = self.root/'.dots/sources.json'
        sources = json.loads(source_file.read_text())
        sources['sources'].append(dict(id='linux', path='profiles/linux', profile='linux', roots=['config'],
                                       platforms=['linux', 'wsl']))
        self.write(source_file, sources)
        linux = self.root/'profiles/linux'
        source = linux/'config/reader.ini'
        source.parent.mkdir()
        source.write_text('reader')
        manifest = linux/'profile.json'
        sample = dict(self.resource, id='reader', source='${PROFILE}/config/reader.ini', target='${CONFIG}/reader')
        del sample['platforms']
        self.write(manifest, dict(json.loads(manifest.read_text()), files=[sample]))
        registry = json.loads(self.registry.read_text())
        registry['resources'].append(dict(id='linux:reader', platforms=['linux']))
        self.write(self.registry, registry)
        manager = Manager(Catalog(self.root, 'wsl'))
        registration = Registration(manager)
        row = registration.candidate(source, target='${CONFIG}/reader')
        registration.assign_ids([row])
        self.assertEqual((row['id'], row['status']), ('linux:reader', 'register-and-link'))
        self.assertIn('wsl', row['platforms'])

    @unittest.skipIf(os.name == 'nt', 'Termux fixture')
    def test_prefix_etc_file_uses_basename_and_is_configuration(self):
        prefix = self.home/'usr'
        self.env.update(PREFIX=str(prefix), TERMUX__PREFIX=str(prefix), TERMUX_VERSION='fixture')
        source = self.root/'profiles/termux/system/etc/os-release'
        source.parent.mkdir(parents=True)
        source.write_text('ID=termux\n')
        target = prefix/'etc/os-release'
        target.parent.mkdir(parents=True)
        preview, = self.run_json('ln', '${PROFILE}/system/etc/os-release', '${PREFIX}/etc/os-release',
                                 '--dry-run')['items']
        self.assertEqual((preview['id'], preview['category']), ('termux:os-release', 'config'))
        self.run_json('ln', str(source), str(target), '--yes')
        self.assertEqual(self.run_json('find', str(target))['items'], [])
        self.assertEqual(self.run_json('ln', str(source), str(target), '--yes')['status'], 'unchanged')


if __name__ == '__main__':
    unittest.main(verbosity=2)
