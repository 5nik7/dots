#!/usr/bin/env python3
"""Preference migration/import acceptance; exclusively owned roots and stores."""
import copy
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import test_profile_config as fixtures
from profile_config import context, settings
from config_values import Controls
from config_cli import ControlPlan
from config_transfer import TransferPlan
from style_config import Styles
from transactions import Store
from preference_files import controls


class Preferences(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        self.environ=patch.dict(os.environ,self.env,clear=True)
        self.environ.start();self.addCleanup(self.environ.stop)

    def cli(self,*args,**kwargs):
        return fixtures.ProfileConfig.run_config(self,*args,profile_scope=False,native=kwargs.pop('native',os.name=='nt'),**kwargs)

    def legacy_preferences(self):
        doc=json.loads(self.path.read_text())
        doc.update(settings={'DOTS_INIT_COLORS':'0'},apps={'cli':{'logo_gradient':'installer'},'fzf':{'colors':{'prompt':'accent','fg+':'blue'}},'bak':{'store':'~/private backups'},'fonts':{'menu_descriptions':False}},formatting={'apps':{'cli':{'indent':3}}},colors={'apps':{'menu':{'popup':{'border':{'fg':'blue'}}}}})
        doc['environment']={'FOO':'literal'}
        self.path.write_text(json.dumps(doc));return doc

    def test_layout_equivalence_undo_repeat_and_literal_toml(self):
        old=self.legacy_preferences();scope=context(self.root)
        before=Controls(self.root,scope).values
        plan=TransferPlan(self.root,scope,all_profiles=True)
        self.assertFalse((self.home/'state').exists())
        saved=plan.apply('migrate-layout')
        self.assertEqual(Controls(self.root).values,before)
        self.assertEqual(json.loads(self.path.read_text()),{k:v for k,v in old.items() if k not in ('settings','apps','formatting','colors')})
        self.assertEqual(settings(self.root)['DOTS_INIT_COLORS']['value'],'0')
        self.assertEqual(Controls(self.root).resolve('apps.fzf.colors["fg+"]')['value'],'blue')
        self.assertEqual(controls(self.path.parent/'colors.toml')['apps.fzf.colors.prompt'],'accent')
        import tomllib
        for filename in ('colors.toml','icons.toml'):
            path=self.root/'default'/filename;tomllib.loads(path.read_text())
        self.assertEqual(TransferPlan(self.root,context(self.root),all_profiles=True).operations,[])
        store=Store(self.home/'state/dots');ops,guards,catalogs=store.inverse(saved['id'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertEqual(json.loads(self.path.read_text()),old)

    def test_default_explicit_profile_settings_and_typed_colors(self):
        self.cli('set','formatting.apps.cli.indent','5','--no-refresh')
        self.assertEqual(json.loads((self.root/'default/config.json').read_text())['formatting']['apps']['cli']['indent'],5)
        self.cli('set','formatting.apps.cli.indent','1','--profile',self.platform,'--no-refresh')
        self.assertEqual(Controls(self.root).resolve('formatting.apps.cli.indent')['value'],1)
        self.cli('set','DOTS_INIT_COLORS','0')
        self.assertEqual(settings(self.root)['DOTS_INIT_COLORS']['source'],str(self.root/'default/config.json'))
        self.cli('set','colors.apps.menu.popup.border.fg','blue','--no-refresh')
        self.assertEqual(controls(self.root/'default/colors.toml')['colors.apps.menu.popup.border.fg'],'blue')
        self.cli('set','apps.nvim.icons["diagnostics.Error"]','雪','--no-refresh')
        self.assertEqual(controls(self.root/'default/icons.toml')['apps.nvim.icons["diagnostics.Error"]'],'雪')
        self.assertNotIn('apps',json.loads(self.path.read_text()))
        self.assertEqual(self.cli('get','colors.apps.menu.popup.border.fg').stdout,'blue\n')
        self.cli('unset','colors.apps.menu.popup.border.fg','--no-refresh')
        self.assertIsNone(controls(self.root/'default/colors.toml')['colors.apps.menu.popup.border.fg'])

    def test_import_merge_exclusions_and_idempotence(self):
        self.legacy_preferences()
        (self.path.parent/'colors.toml').write_text('[ui.heading]\nfg="yellow"\n')
        target='windows' if self.platform!='windows' else 'linux'
        p=self.root/'profiles'/target/'config.json'
        p.write_text(json.dumps({'schema':1,'apps':{'cli':{'logo_gradient':'classic'},'bak':{'mode':'copy'}},'formatting':{'apps':{'cli':{'label_gap':4}}}}))
        before=json.loads((p.parent/'profile.json').read_text())
        self.cli('import',self.platform,'--profile',target,'--json',native=True)
        self.assertFalse((self.home/'state').exists())
        result=json.loads(self.cli('import',self.platform,'--profile',target,'--apply','--yes','--json').stdout)
        self.assertEqual(result['status'],'complete')
        c=Controls(self.root,context(self.root,target))
        self.assertEqual(c.resolve('apps.cli.logo_gradient')['value'],'installer')
        self.assertEqual(c.resolve('apps.bak.mode')['value'],'copy')
        self.assertFalse(c.resolve('apps.fonts.menu_descriptions')['value'])
        self.assertEqual(c.resolve('apps.bak.store')['value'],'~/.bakstore')
        self.assertEqual(c.resolve('formatting.apps.cli.label_gap')['value'],4)
        self.assertEqual(settings(self.root,context(self.root,target)),{})
        after=json.loads((p.parent/'profile.json').read_text())
        self.assertEqual({k:v for k,v in before.items() if k!='settings'},after)
        self.assertEqual(TransferPlan(self.root,context(self.root,target),source=self.platform).operations,[])

    def test_check_validates_separated_shell_settings(self):
        self.cli('check','--json')
        path=self.path.parent/'config.json'
        path.write_text(json.dumps({'schema':1,'settings':{'DOTS_INIT_COLORS':'invalid'}}))
        failed=self.cli('check','--json',code=1)
        self.assertIn('invalid Dots setting: DOTS_INIT_COLORS',failed.stderr)
        self.assertFalse((self.home/'state').exists())

    def test_stale_plan_refuses_and_promotion_preserves_effective_appearance(self):
        old=self.legacy_preferences();scope=context(self.root)
        plan=TransferPlan(self.root,scope,all_profiles=True)
        self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaises((ValueError,RuntimeError)):plan.apply()
        self.assertEqual(json.loads(self.path.read_text()),old)
        before=Controls(self.root).values
        plan=TransferPlan(self.root,context(self.root),source=self.platform,defaults=True,promote=True)
        plan.apply('promote')
        self.assertEqual(Controls(self.root).values,before)
        self.assertEqual(Controls(self.root).resolve('apps.cli.logo_gradient')['source'],str(self.root/'default/config.json'))
        self.assertEqual(Controls(self.root).resolve('apps.bak.store')['value'],'~/private backups')
        self.assertEqual(settings(self.root)['DOTS_INIT_COLORS']['value'],'0')

    def test_failed_layout_publication_rolls_back_every_preference_file(self):
        from transactions import digest
        import transactions
        self.legacy_preferences()
        before=Controls(self.root).values
        plan=TransferPlan(self.root,context(self.root),all_profiles=True)
        originals={path:digest(Path(path)) for path in plan.guards}
        rename=transactions.os.rename;failed=[]
        def fail(source,destination):
            if Path(destination)==self.path and '.dots-new-' in str(source) and not failed:
                # Inject after earlier preference files have been published.
                failed.append(True)
                raise OSError('injected preference publication failure')
            return rename(source,destination)
        with patch.object(transactions.os,'rename',side_effect=fail):
            with self.assertRaisesRegex(OSError,'injected preference'):plan.apply('migrate-layout')
        self.assertTrue(failed)
        self.assertEqual({path:digest(Path(path)) for path in originals},originals)
        self.assertEqual(Controls(self.root).values,before)


    def test_import_review_cancel_and_source_validation(self):
        from config_transfer import review
        from config_menu import select
        self.legacy_preferences()
        target='windows' if self.platform!='windows' else 'linux'
        plan=TransferPlan(self.root,context(self.root,target),source=self.platform)
        with patch('config_menu.select',return_value='cancel') as choose:
            self.assertFalse(review(plan))
            self.assertEqual(choose.call_args.args[1],[('cancel','Cancel'),('save','Save')])
        self.assertFalse((self.home/'state').exists())
        invalid=self.path.parent/'config.json'
        invalid.write_text(json.dumps({'schema':1,'formatting':{'apps':{'unknown':{'indent':2}}}}))
        with self.assertRaises(ValueError):TransferPlan(self.root,context(self.root,target),source=self.platform)


    def test_browser_destinations_and_style_write_preserves_typed(self):
        from config_menu import Inventory,Draft
        self.cli('migrate','--layout','--all-profiles','--apply','--yes','--json')
        inventory=Inventory(self.root,'defaults',no_refresh=True)
        self.assertEqual(inventory.find('colors.apps.menu.popup.border.fg').destination,str(self.root/'default/colors.toml'))
        draft=Draft(inventory,inventory.find('settings.DOTS_INIT_COLORS')).prepare('0')
        draft.plan.apply('set')
        self.assertEqual(settings(self.root)['DOTS_INIT_COLORS']['value'],'0')
        typed=controls(self.root/'default/colors.toml')
        self.cli('set','colors.ui.heading.fg','green','--no-refresh')
        self.assertEqual(controls(self.root/'default/colors.toml'),typed)


if __name__=='__main__':unittest.main()
