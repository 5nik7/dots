"""Bootstrap receipt/backup integration, wholly within disposable roots."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_installation as fixture
from install import Installation
from backup_catalog import BackupPlan


class BootstrapIntegration(unittest.TestCase):
    setUp = fixture.InstallationTests.setUp
    write = fixture.InstallationTests.write
    receipt = fixture.InstallationTests.receipt

    def test_drift_backup_first_baseline_and_uninstall(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('original')
        with patch.dict(os.environ, self.env):
            first = Installation(self.repo); first.plan_install(['files']); first.apply('install')
            baseline = self.receipt()['entries'][str(self.target)]['backup_id']
            self.target.unlink(); self.target.write_text('edited')
            second = Installation(self.repo); second.plan_install(['files'])
            self.assertFalse(second.blocked)
            second.apply('install')
            backups = BackupPlan()
            self.assertEqual(len(backups.records()), 2)
            self.assertEqual(self.receipt()['entries'][str(self.target)]['backup_id'], baseline)
            with self.assertRaisesRegex(ValueError, 'required for uninstall'): backups.delete([baseline])
            repeat = Installation(self.repo); repeat.plan_install(['files'])
            self.assertEqual(repeat.apply('install')['status'], 'unchanged')
            remove = Installation(self.repo); remove.plan_uninstall(['files']); remove.apply('uninstall')
            self.assertEqual(self.target.read_text(), 'original')
            self.assertEqual({Path(r['path']).read_text() for r in BackupPlan().records()}, {'original','edited'})

    def test_restore_baseline_releases_only_its_receipt(self):
        self.target.parent.mkdir(parents=True); self.target.write_text('before')
        with patch.dict(os.environ, self.env):
            plan = Installation(self.repo); plan.plan_install(['core','files']); plan.apply('install')
            record = self.receipt()['entries'][str(self.target)]
            restore = BackupPlan(); restore.restore(record['backup_id']); restore.apply('restore')
            self.assertEqual(self.target.read_text(), 'before')
            self.assertNotIn(str(self.target), self.receipt()['entries'])
            self.assertIn(str(self.home/'.local/bin/dots'), self.receipt()['entries'])

    def test_opt_out_keeps_prior_baseline_and_reports_new_discard(self):
        self.target.parent.mkdir(parents=True); self.target.write_text('original')
        with patch.dict(os.environ, self.env):
            first = Installation(self.repo); first.plan_install(['files']); first.apply('install')
            self.target.unlink(); self.target.write_text('new edit')
            change = Installation(self.repo); change.no_backup=True; change.plan_install(['files']); change.apply('install')
            self.assertEqual(len(BackupPlan().records()),1)
            remove = Installation(self.repo); remove.plan_uninstall(['files']); remove.apply('uninstall')
            self.assertEqual(self.target.read_text(),'original')
            change = Installation(self.repo); change.no_backup=True; change.plan_install(['files']); change.apply('install')
            self.assertTrue(self.receipt()['entries'][str(self.target)]['discarded_original'])
            remove = Installation(self.repo); remove.plan_uninstall(['files'])
            self.assertIn('deliberately discarded', remove.items[0]['reason'])
            remove.apply('uninstall'); self.assertFalse(self.target.exists())

    def test_old_user_launchers_are_recoverable(self):
        (self.home/'bin').mkdir(); old=self.home/'bin/bak'; old.write_text('old utility')
        with patch.dict(os.environ,self.env):
            setup=Installation(self.repo); setup.plan_install(['core']); setup.apply('install')
            self.assertFalse(old.exists())
            remove=Installation(self.repo); remove.plan_uninstall(); remove.apply('uninstall')
            self.assertEqual(old.read_text(),'old utility')

    def test_installed_powershell_all_hosts_destinations(self):
        source=self.repo/'shells/powershell/profile.ps1'; source.parent.mkdir(parents=True); source.write_text('# fixture')
        self.write('.dots/files.json', dict(schema=1, repository='dots', resources=[dict(
            id='powershell-profile',source='shells/powershell/profile.ps1',target='${POWERSHELL_PROFILE}',
            strategy='link',app='powershell',category='shell',platforms=['windows'])]))
        paths=[self.home/'Documents'/p/'profile.ps1' for p in ('PowerShell','WindowsPowerShell')]
        env=dict(self.env,DOTS_POWERSHELL_PROFILE=str(paths[0]), DOTS_POWERSHELL_PROFILES=json.dumps([dict(path=str(p),version='7') for p in paths]))
        with patch.dict(os.environ,env), patch('install.platform',return_value='windows'):
            plan=Installation(self.repo); plan.plan_install(['files'])
            self.assertEqual({op['path'] for op in plan.operations},set(map(str,paths)))

    def test_starship_default_link_and_palette_preserve_layout(self):
        default=self.repo/'config/blastoff/themes/dots.toml'; default.parent.mkdir(parents=True)
        default.write_text('palette="dots"\nformat="custom"\n[palettes.dots]\nred="#000000"\n')
        generation=self.home/'generation';generation.mkdir();(generation/'blastoff.toml').write_text('palette="dots"\n[palettes.dots]\nred="#ff0000"\n')
        env=dict(self.env,STARSHIP_CONFIG=str(self.home/'custom starship.toml'),BLASTOFF_HOME=str(default.parent.parent))
        sys.path.insert(0,str(fixture.ROOT/'lib/dots/themes'))
        from setup_starship import plan as starship
        with patch.dict(os.environ,env):
            setup=Installation(self.repo); setup.components={'blastoff'}; setup.review_replacements=True; setup.theme_payload=generation
            starship(setup);setup.apply('install')
            active=Path(env['STARSHIP_CONFIG'])
            self.assertTrue(active.is_symlink()); self.assertEqual(active.resolve(),default)
            self.assertIn('format="custom"',default.read_text());self.assertIn('#ff0000',default.read_text())
            repeat=Installation(self.repo);repeat.components={'blastoff'};repeat.theme_payload=generation
            starship(repeat);self.assertEqual(repeat.apply('install')['status'],'unchanged')


if __name__=='__main__':unittest.main()
