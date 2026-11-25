#!/usr/bin/env python3
"""Round-trip and owner boundaries for unified preferences in disposable roots."""
import json
import os
import shutil
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from config_cli import ControlPlan, StylePlan
from preference_files import combined, preference_path, style_layers, unified_document, unified_values
from profile_config import context


class UnifiedPreferences(unittest.TestCase):
    run_config = fixtures.ProfileConfig.run_config

    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default', self.root/'default')
        self.environment = patch.dict(os.environ, self.env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.prefs = self.path.with_name('config.json')

    def test_shipped_documents_are_sparse_and_roundtrip(self):
        files = {fixtures.ROOT/'default/config.json', *(fixtures.ROOT/'profiles').glob('*/config.json')}
        self.assertEqual({p.parent.name for p in files}, {'default','linux','termux'})
        for path in files:
            raw = json.loads(path.read_bytes())
            self.assertEqual(raw['schema'], 2)
            self.assertEqual(unified_document(*unified_values(raw)), raw)
            self.assertFalse(any(path.with_name(name).exists() for name in ('colors.toml','icons.toml')))
        raw = json.loads((fixtures.ROOT/'default/config.json').read_bytes())
        self.assertEqual(raw['apps']['nvim']['icons'], {})
        self.assertIsNone(raw['apps']['fzf']['colors']['bg+'])
        self.assertEqual(raw['apps']['fzf']['colors']['fg+'], 'accent')
        self.assertIn('cursor', raw['apps']['fzf']['colors']['ui'])

    def test_first_write_and_cli_readers_preserve_each_owner(self):
        before = self.path.read_bytes()
        for key, value, native in [('settings.fzf.preview_window','down:22%',False),
                ('colors.fzf["fg+"]','blue:bold',True), ('fzf.colors.ui.cursor.fg','red',False),
                ('icons.nvim["diagnostics.Error"]','雪',True),
                ('nvim.colors.highlights["@lsp.type.class"].fg','blue',False),
                ('icons.navigation.separator','»',True), ('settings.files.backup','false',False)]:
            self.assertEqual(self.run_config('path',key,'--profile',self.platform).stdout.strip(),str(self.prefs))
            self.run_config('set',key,value,'--no-refresh',native=native)
            self.assertEqual(self.run_config('get',key,native=not native).stdout.strip(),value, key)
        result=json.loads(self.prefs.read_bytes())
        self.assertEqual(result['schema'],2)
        self.assertEqual(result['apps']['fzf'], dict(settings={'preview_window':'down:22%'},
            colors={'fg+':'blue:bold','ui':{'cursor':{'fg':'red'}}}))
        self.assertEqual(result['apps']['nvim']['icons'], {'diagnostics.Error':'雪'})
        self.assertEqual(result['apps']['nvim']['colors']['highlights'], {'@lsp.type.class':{'fg':'blue'}})
        self.assertEqual(result['settings'], {'files.backup':False})
        self.assertEqual(result['icons']['navigation']['separator'],'»')
        self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(self.path.with_name('colors.toml').exists())
        self.assertFalse(self.path.with_name('icons.toml').exists())

    def test_conflicts_drift_and_literal_legacy_inputs(self):
        for names in [('navigation.codex','applications.codex'),
                      ('apps.tmux.navigation.codex','apps.tmux.applications.codex')]:
            same = unified_document({}, {'icons':dict.fromkeys(names, 'x')})
            self.assertEqual(list(unified_values(same)[1]['icons'].values()), ['x'])
            with self.assertRaisesRegex(ValueError, 'conflicting'):
                unified_document({}, {'icons': dict(zip(names, ('x','y')))})
        selection = context(self.root)
        style = StylePlan(self.root, selection, 'icons')
        style.edit('navigation.separator', 'x')
        ctrl = ControlPlan(self.root, selection)
        ctrl.edit('apps.fzf.preview_window', 'down:22%')
        ctrl.apply('set')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            style.apply('set')
        self.assertNotIn('icons',json.loads(self.prefs.read_bytes()))

        self.prefs.write_text('{"schema":1,"apps":{"fzf":{"preview_window":"down:13%"}}}', encoding='utf-8')
        colors = self.prefs.with_name('colors.toml')
        colors.write_text('[apps.fzf.ui.cursor]\nfg = "blue"\n', encoding='utf-8')
        self.run_config('set','colors.fzf["fg+"]','red','--no-refresh')
        self.assertEqual(json.loads(self.prefs.read_bytes())['schema'],1)
        self.assertEqual(combined(self.prefs.parent)['apps']['fzf']['colors']['fg+'],'red')
        self.assertEqual(style_layers(self.prefs.parent,'colors')[0][1],{'apps.fzf.ui.cursor.fg':'blue'})
        self.assertEqual(preference_path(self.prefs.parent,'icons.navigation.separator',self.root),
                         self.prefs.with_name('icons.toml'))

    def test_edit_keeps_unrelated_empty_map_null_and_false(self):
        raw={'schema':2,'apps':{'nvim':{'icons':{}, 'settings':{'options':{'wrap':False}}},
                                'fzf':{'colors':{'fg+':None}}}}
        self.prefs.write_text(json.dumps(raw),encoding='utf-8')
        change=ControlPlan(self.root,context(self.root))
        change.edit('apps.fzf.preview_window','down:21%')
        change.apply('set')
        raw['apps']['fzf']['settings']={'preview_window':'down:21%'}
        self.assertEqual(json.loads(self.prefs.read_bytes()),raw)

    def test_last_unset_restores_sparse_profile_and_invalidates_consumers(self):
        from config_values import current as controls
        from style_config import current as styles
        from files.transactions import Store
        selection=context(self.root)
        for key, value, plan, observe in (
                ('apps.fzf.preview_window','down:22%',lambda: ControlPlan(self.root,selection),
                 lambda: controls().resolve('apps.fzf.preview_window')['value']),
                ('navigation.separator','SEP',lambda: StylePlan(self.root,selection,'icons'),
                 lambda: styles().icon('navigation.separator'))):
            default=observe()
            changed=plan()
            changed.edit(key,value)
            changed.apply('set')
            self.assertEqual(observe(),value)
            original=self.prefs.read_bytes()
            cleared=plan()
            cleared.edit(key,None,unset=True)
            result=cleared.apply('unset')
            self.assertFalse(self.prefs.exists())
            self.assertEqual(observe(),default)
            store=Store(self.home/'state/dots')
            ops,guards,catalogs=store.inverse(result['id'])
            store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
            self.assertEqual(self.prefs.read_bytes(),original)
            self.prefs.unlink()

    def test_last_unset_does_not_reactivate_shadowed_legacy_inputs(self):
        self.prefs.write_text('{"schema":2,"icons":{"navigation":{"separator":"current"}}}',encoding='utf-8')
        hidden=self.prefs.with_name('icons.toml')
        hidden.write_text('[navigation]\nseparator="old"\n',encoding='utf-8')
        original=hidden.read_bytes()
        changed=StylePlan(self.root,context(self.root),'icons')
        changed.edit('navigation.separator',None,unset=True)
        changed.apply('unset')
        self.assertEqual(json.loads(self.prefs.read_bytes()),{'schema':2})
        self.assertEqual(hidden.read_bytes(),original)
        self.assertEqual(style_layers(self.prefs.parent,'icons'),[(self.prefs,{})])
        manifest=json.loads(self.path.read_bytes())
        manifest['settings']={'DOTS_COLOR':'always'}
        self.path.write_text(json.dumps(manifest),encoding='utf-8')
        saved=json.loads(self.run_config('list','--json').stdout)['config']['settings']
        self.assertEqual(saved['DOTS_COLOR'],self.run_config('get','settings.DOTS_COLOR').stdout.strip())
        self.assertNotEqual(saved['DOTS_COLOR'],'always')

    def test_reverting_edits_in_a_review_leaves_an_empty_profile_untouched(self):
        from preference_files import SettingsPlan
        selected=context(self.root)
        for plan,key,value in ((SettingsPlan(self.root,selected),'DOTS_COLOR','never'),
                               (ControlPlan(self.root,selected),'apps.cli.progress','none'),
                               (StylePlan(self.root,selected,'icons'),'navigation.separator','x')):
            plan.edit(key,value)
            self.assertTrue(plan.operations)
            plan.edit(key,None,unset=True)
            self.assertEqual(plan.operations,[])
            self.assertEqual(plan.apply('set')['status'],'unchanged')
            self.assertFalse(self.prefs.exists())


if __name__ == '__main__':
    unittest.main()
