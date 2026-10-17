#!/usr/bin/env python3
"""Bounded Git selector lifecycle in disposable installation roots."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_installation as fixtures
from install import Installation
from catalog import Catalog
from transactions import Store, digest
import mappings
from manage import Manager


class GitPlatform(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.InstallationTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.repo, self.home = self.f.repo, self.f.home
        self.env = dict(self.f.env, DOTS_PROGRESS='never')
        self.env.update(XDG_CACHE_HOME=str(self.home/'.cache'), XDG_DATA_HOME=str(self.home/'.data'))
        self.patch = patch.dict(os.environ,self.env); self.patch.start(); self.addCleanup(self.patch.stop)
        self.git = self.repo/'config/git'; self.git.mkdir()
        (self.git/'config').write_text('[include]\n  path = gitconfig\n  path = gitplatform\n')
        (self.git/'gitconfig').write_text('[fixture]\n common = true\n')
        for name in ('termux','linux','wsl','windows'):
            (self.git/name).write_text('[fixture]\n platform = '+name+'\n')
        self.selector = self.git/'gitplatform'
        self.target = self.home/'.config/git'
        self.row = dict(id='git',source='config/git',target='${CONFIG}/git',strategy='directory-link',app='git',category='config',platforms=['termux','linux','wsl','windows'])
        self.f.write('.dots/files.json',dict(schema=1,repository='dots',resources=[self.row]))

    def test_platforms_install_noop_and_uninstall(self):
        for selected in ('termux','linux','wsl','windows'):
            with self.subTest(platform=selected), patch('install.platform',return_value=selected):
                before = list(self.home.rglob('*'))
                plan=Installation(self.repo); plan.plan_install()
                self.assertEqual(before,list(self.home.rglob('*')))
                self.assertFalse(self.selector.is_symlink())
                plan.apply('install')
                self.assertEqual(self.selector.readlink(),Path(selected))
                self.assertEqual(self.target.resolve(),self.git)
                again=Installation(self.repo); again.plan_install()
                self.assertEqual(again.apply('install')['status'],'unchanged')
                end=Installation(self.repo); end.plan_uninstall(); end.apply('uninstall')
                self.assertFalse(self.selector.is_symlink())
                self.assertTrue((self.git/selected).is_file())
                # A new platform represents a separate installation/state root.
                import shutil
                shutil.rmtree(self.home/'.state')

    def test_existing_correct_link_is_not_owned(self):
        from catalog import platform
        self.selector.symlink_to(platform())
        plan=Installation(self.repo);plan.plan_install();plan.apply('install')
        self.assertNotIn(str(self.selector),json.loads(plan.receipt_path.read_text())['entries'])
        end=Installation(self.repo);end.plan_uninstall();end.apply('uninstall')
        self.assertTrue(self.selector.is_symlink())

    def test_known_replacement_backup_undo_and_drift(self):
        from catalog import platform
        previous='windows' if platform()!='windows' else 'linux'
        self.selector.symlink_to(previous)
        plan=Installation(self.repo);plan.plan_install();result=plan.apply('install')
        self.assertNotEqual(self.selector.readlink(),Path(previous))
        store=plan.store;ops,guards,catalogs=store.inverse(result['id'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertEqual(self.selector.readlink(),Path(previous))
        plan=Installation(self.repo);plan.plan_install();plan.apply('install')
        self.selector.unlink();self.selector.symlink_to(previous)
        with self.assertRaisesRegex(ValueError,'selector changed'):
            Installation(self.repo).plan_install()

    def test_unrelated_files_links_missing_sources_and_race(self):
        for kind in ('file','link','directory'):
            if kind=='file': self.selector.write_text('mine')
            elif kind=='link': self.selector.symlink_to('elsewhere')
            else:self.selector.mkdir()
            with self.assertRaises(ValueError):Installation(self.repo).plan_install()
            self.assertFalse(self.target.is_symlink())
            self.selector.rmdir() if kind=='directory' else self.selector.unlink()
        from catalog import platform
        overlay=self.git/platform();overlay.unlink()
        with self.assertRaisesRegex(ValueError,'regular file'):Installation(self.repo).plan_install()
        overlay.write_text('# restored\n')
        plan=Installation(self.repo);plan.plan_install();overlay.write_text('# concurrent edit\n')
        with self.assertRaisesRegex(ValueError,'changed after preview'):plan.apply('install')
        self.assertFalse(self.selector.is_symlink())

    def test_direct_link_receipt_and_stash_restore(self):
        from catalog import platform
        args=argparse.Namespace(action='link',values=['dots:git'],backup=True)
        manager=Manager();ops,guards,catalogs,views=manager.plan(args)
        self.assertTrue(any(v.get('id')=='dots:git-platform' for v in views))
        manager.link_installation.apply('link',catalogs=catalogs)
        self.assertEqual(self.selector.readlink(),Path(platform()))
        self.assertIn(str(self.selector),json.loads(manager.link_installation.receipt_path.read_text())['entries'])
        import subprocess
        result=subprocess.run([sys.executable,'-B',str(fixtures.ROOT/'lib/dots/files/manage.py'),'link','dots:git','--yes','--json'],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),dict(schema=1,status='unchanged',operations=[]))
        plan=mappings.MappingPlan();plan.stash(['dots:git']);plan.finish();plan.apply('stash')
        self.assertTrue(self.selector.is_symlink());self.assertFalse(self.target.is_symlink())
        plan=mappings.MappingPlan();plan.stash(['dots:git'],restore=True);plan.finish();plan.apply('restore')
        self.assertTrue(self.target.is_symlink())
        end=Installation(self.repo);end.plan_uninstall();end.apply('uninstall')
        self.assertFalse(self.selector.is_symlink())

    def test_failure_rolls_back_selector_and_directory_link(self):
        plan=Installation(self.repo);plan.plan_install()
        original=os.rename;failed=False
        def fail(src,dest,*args,**kwargs):
            nonlocal failed
            if not failed and str(dest)==str(self.target) and '.dots-new-' in str(src):
                failed=True;raise OSError('fixture failure')
            return original(src,dest,*args,**kwargs)
        with patch.object(os,'rename',fail),self.assertRaises(OSError):plan.apply('install')
        self.assertFalse(self.selector.is_symlink());self.assertFalse(self.target.is_symlink())
        self.assertFalse(plan.receipt_path.exists())

if __name__=='__main__':unittest.main()
