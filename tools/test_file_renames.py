#!/usr/bin/env python3
"""Cross-profile identity and recovery acceptance in disposable checkouts."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_profile_backend as backend
from catalog import Catalog
from install import Installation
from mappings import MappingPlan, arguments
from profile_config import context
from transactions import Store, digest
from file_platform import state_root


class Renames(unittest.TestCase):
    setUp = backend.ProfileBackend.setUp
    write = backend.ProfileBackend.write
    files = backend.ProfileBackend.files
    undo = backend.ProfileBackend.undo
    config = backend.ProfileBackend.config

    def snapshots(self):
        return {p: p.read_bytes() for p in [self.registry, *self.root.glob('profiles/**/profile.json')]}

    def rename(self, old='app', new='renamed', *extra):
        return json.loads(self.files('edit', 'dots:'+old, '--id', new, *extra, '--yes', '--json').stdout)

    def plan(self, *extra):
        _, args = arguments(['edit','dots:app','--id','renamed',*extra,'--yes'])
        plan = MappingPlan(selected_platform=args.platform)
        plan.edit(args); plan.finish()
        return plan

    def test_all_profiles_preview_history_and_exact_undo(self):
        before = self.snapshots()
        preview = json.loads(self.files('edit','dots:app','--id','renamed','--dry-run','--json').stdout)
        self.assertEqual(preview['items'][0]['old_id'], 'dots:app')
        self.assertEqual(self.snapshots(), before)
        self.assertFalse(state_root().exists())
        saved = self.rename()
        registry = json.loads(self.registry.read_text())
        self.assertEqual(registry['schema'], 3)
        self.assertEqual(registry['renames'], {'dots:app':'dots:renamed'})
        for platform in ('termux','linux','wsl','windows'):
            self.assertEqual(Catalog(self.root,platform).records()[0]['id'],'dots:renamed')
        self.assertIn('was renamed; use dots:renamed', self.files('show','dots:app',code=2).stderr)
        second = self.rename('renamed','latest')
        self.assertEqual(json.loads(self.registry.read_text())['renames'],
                         {'dots:app':'dots:latest','dots:renamed':'dots:latest'})
        self.undo(second['transaction']); self.undo(saved['transaction'])
        self.assertEqual({p:json.loads(v) for p,v in self.snapshots().items()},
                         {p:json.loads(v) for p,v in before.items()})

    def test_inheritance_replacements_and_disabled_rows(self):
        other=copy.deepcopy(self.resource);other.update(id='replacement',source='config/other',replaces=['dots:app'])
        (self.root/'config/other').write_text('other')
        registry=json.loads(self.registry.read_text());registry['resources'].append(dict(id='dots:replacement',platforms=other['platforms']))
        self.write(self.registry,registry)
        linux=self.root/'profiles/linux/profile.json';data=json.loads(linux.read_text())
        data['files']['dots'][0]['enabled']=False
        data['files']['dots'].append({k:v for k,v in other.items() if k!='platforms'});self.write(linux,data)
        child=self.root/'profiles/linux/distros/example/profile.json';child.parent.mkdir(parents=True)
        self.write(child,dict(schema=1,id='linux/example',extends=['linux'],files={},settings={}))
        child_before=child.read_bytes()
        self.rename()
        data=json.loads(linux.read_text())
        self.assertFalse(data['files']['dots'][0]['enabled'])
        self.assertEqual(data['files']['dots'][1]['replaces'],['dots:renamed'])
        self.assertEqual(child.read_bytes(),child_before)

    def test_reserved_ids_and_invalid_names_cannot_bypass(self):
        self.rename(); before=self.snapshots()
        for name in ('app','bad:name','../escape','UPPER','-bad',''):
            self.files('edit','dots:renamed','--id='+name,'--yes',code=1)
        self.files('edit','--new','--repo','dots','--id','app','--source','config/app',
                   '--target','${CONFIG}/other','--app','app','--category','config','--yes',code=1)
        self.files('track','config/app','--repo','dots','--id','app','--target','${CONFIG}/other',
                   '--app','app','--category','config','--json',code=1)
        self.config('set','files.dots',json.dumps([{k:v for k,v in self.resource.items() if k!='platforms'}]),'--json-value',code=1)
        self.assertEqual(self.snapshots(),before)

    def test_occupied_ids_malformed_history_and_forced_json(self):
        registry=json.loads(self.registry.read_text())
        registry['resources'].append(dict(id='dots:occupied',platforms=['linux']))
        self.write(self.registry,registry);before=self.snapshots()
        self.files('edit','dots:app','--id','occupied','--yes',code=1)
        self.assertEqual(self.snapshots(),before)
        plain=self.files('edit','dots:app','--id','renamed','--dry-run','--json').stdout
        self.env.update(DOTS_COLOR='always',DOTS_ICONS='always')
        self.assertEqual(self.files('edit','dots:app','--id','renamed','--dry-run','--json').stdout,plain)
        for history in ({'dots:app':'dots:occupied'}, {'dots:old':'dots:missing'},
                        {'dots:old':'dots:older','dots:older':'dots:old'}, {'other:old':'dots:app'}):
            self.write(self.registry,dict(registry,schema=3,renames=history))
            with self.assertRaises(ValueError): Catalog(self.root,self.platform)
        self.write(self.registry,registry)

    def test_registered_only_and_missing_source_rename(self):
        for path in self.root.glob('profiles/*/profile.json'):
            data=json.loads(path.read_text());data['files']['dots']=[];self.write(path,data)
        (self.root/'config/app').unlink()
        self.rename()
        self.assertEqual(Catalog(self.root,self.platform).records(),[])
        self.assertIn('dots:renamed',Catalog(self.root,self.platform).registry.entries)

    def test_combined_mapping_scope_and_noop(self):
        self.rename('app','renamed','--platform','windows','--target','${APPDATA}/new')
        for path in self.root.glob('profiles/*/profile.json'):
            row=json.loads(path.read_text())['files']['dots'][0]
            self.assertEqual(row['id'],'renamed')
            self.assertEqual(row['target'],'${APPDATA}/new' if path.parent.name=='windows' else '${CONFIG}/app')
        before=self.snapshots()
        self.assertEqual(self.rename('renamed','renamed')['status'],'unchanged')
        self.assertEqual(self.snapshots(),before)
        if self.platform!='windows':
            self.files('edit','dots:renamed','--id','latest','--platform','windows','--apply','--yes',code=1)
            self.assertEqual(self.snapshots(),before)

    @unittest.skipIf(os.name=='nt','POSIX link fixture; native link privileges tested separately')
    def test_live_combination_baseline_receipts_repair_and_uninstall(self):
        target=Path(self.env['XDG_CONFIG_HOME'])/'app';target.parent.mkdir(parents=True)
        target.write_text('original')
        self.files('edit','dots:app','--apply','--backup','--yes')
        original=copy.deepcopy(Installation(self.root).entries[str(target)])
        saved=self.rename('app','renamed','--target','${CONFIG}/new','--apply')
        installation=Installation(self.root)
        self.assertEqual(installation.entries[str(target)]['id'],'dots:renamed')
        for key in ('before','backup','index'):
            self.assertEqual(installation.entries[str(target)][key],original[key])
        self.assertTrue((target.parent/'new').is_symlink())
        self.undo(saved['transaction'])
        self.assertTrue(target.is_symlink());self.assertFalse((target.parent/'new').exists())
        self.rename()
        # Simulate a receipt from another installation before it observes rename.
        path=Installation(self.root).receipt_path;receipt=json.loads(path.read_text())
        receipt['entries'][str(target)]['id']='dots:app';self.write(path,receipt)
        self.assertEqual(Installation(self.root).entries[str(target)]['id'],'dots:renamed')
        target.unlink()
        self.files('repair','dots:renamed','--yes','--json')
        self.assertTrue(target.is_symlink())
        self.files('uninstall','--yes')
        self.assertEqual(target.read_text(),'original')

    def test_stale_guards_new_profile_and_drift_refusal(self):
        plan=self.plan(); self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'changed after preview'): plan.apply('edit')
        plan=self.plan()
        child=self.root/'profiles/linux/distros/new/profile.json';child.parent.mkdir(parents=True)
        self.write(child,dict(schema=1,id='linux/new',extends=['linux']))
        with self.assertRaisesRegex(ValueError,'inventory changed'): plan.apply('edit')
        saved=self.rename();self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaises(ValueError): self.undo(saved['transaction'])

    def test_partial_apply_rolls_back_every_metadata_file(self):
        before=self.snapshots();plan=self.plan()
        original=os.rename;count=0
        def fail(source,target):
            nonlocal count
            if '.dots-new-' in str(source):
                count+=1
                if count==3: raise OSError('injected rename failure')
            return original(source,target)
        with patch('transactions.os.rename',side_effect=fail),self.assertRaises(OSError): plan.apply('edit')
        self.assertEqual(self.snapshots(),before)
        self.assertTrue(all(row['status']=='rolled-back' for row in Store(state_root()).records()))

    def test_interrupted_rollback_retains_recoverable_batch(self):
        before=self.snapshots();plan=self.plan();original=os.rename;count=0
        def interrupt(source,target):
            nonlocal count
            if '.dots-new-' in str(source):
                count+=1
                if count==3: raise KeyboardInterrupt()
            return original(source,target)
        with patch('transactions.os.rename',side_effect=interrupt), \
             patch.object(Store,'rollback',side_effect=OSError('rollback unavailable')), \
             self.assertRaises(KeyboardInterrupt): plan.apply('edit')
        store=Store(state_root());record=store.records()[0]
        self.assertEqual(record['status'],'recovery-required')
        store.recover(record['id'])
        self.assertEqual(self.snapshots(),before)


if __name__=='__main__': unittest.main()
