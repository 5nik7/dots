#!/usr/bin/env python3
"""Native weather edits never touch the developer's config or weather provider."""
import copy
import json
import os
import shutil
import unittest
from unittest.mock import patch
import test_profile_config as fixtures
from config_wttr import Native,NativePlan
from profile_config import context
from transactions import Store

class WeatherConfig(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'config/wttr',self.root/'config/wttr')
        self.environ=patch.dict(os.environ,self.env,clear=True);self.environ.start();self.addCleanup(self.environ.stop)
        self.run_config=lambda *a,**kw:fixtures.ProfileConfig.run_config(self,*a,**kw)

    def test_active_file_comments_native_keys_validation_and_undo(self):
        native=Native(self.root);path=native.path
        path.write_text(path.read_text()+'\n[extra]\nkeep = "unchanged" # personal\n')
        before=path.read_text()
        self.run_config('set','apps.wttr.icons["113"]','TEST','--dry-run')
        self.assertEqual(path.read_text(),before)
        result=json.loads(self.run_config('set','apps.wttr.icons["113"]','TEST','--json').stdout)
        self.assertIn('# personal',path.read_text());self.assertIn('# sunny / clear',path.read_text())
        self.assertEqual(self.run_config('get','apps.wttr.icons["113"]').stdout,'TEST\n')
        store=Store(self.home/'state/dots');ops,guards,catalogs=store.inverse(result['transaction'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertEqual(path.read_text(),before)
        self.run_config('set','apps.wttr.days','99',code=1)
        self.assertEqual(path.read_text(),before)
        self.run_config('set','apps.wttr.icon_colors["113"].bg','#123456')
        self.assertEqual(self.run_config('get','apps.wttr.icon_colors["113"].fg').stdout,'yellow\n')
        self.assertEqual(self.run_config('get','apps.wttr.icon_colors["113"].bg').stdout,'#123456\n')
        self.run_config('set','apps.wttr.icon_colors["113"].bg','null','--json-value')
        self.assertEqual(self.run_config('get','apps.wttr.icon_colors["113"].bg').stdout,'null\n')
        user=self.home/'config/wttr';user.mkdir(parents=True)
        shutil.copy2(path,user/'config.toml')
        stale=NativePlan(self.root,context(self.root));stale.edit('apps.wttr.units','metric')
        (user/'config.toml').write_text((user/'config.toml').read_text()+'\n')
        with self.assertRaises(ValueError):stale.apply('set')
        self.assertEqual(Native(self.root).path,user/'config.toml')
        self.run_config('get','apps.wttr.extra.keep',code=1)
        other='windows' if self.platform!='windows' else 'linux'
        self.run_config('set','apps.wttr.units','metric','--profile',other,code=1)

if __name__=='__main__':unittest.main()
