#!/usr/bin/env python3
"""Existing-source registration, ownership and recovery in disposable profiles."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_profile_backend as backend
from catalog import Catalog
from manage import Manager
from registration import Registration, candidates
from transactions import Store, digest
from file_platform import state_root
from file_platform import native_link_text, validate_windows_path
from install import Installation
import picker


class RegistrationTests(unittest.TestCase):
    setUp = backend.ProfileBackend.setUp
    write = backend.ProfileBackend.write
    files = backend.ProfileBackend.files
    undo = backend.ProfileBackend.undo

    def prepare(self, name='example ü', directory=False, locations=True):
        source = self.root / 'config' / name
        if directory:
            source.mkdir(parents=True)
            (source / 'settings').write_text('kept\n')
        else:
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('kept\n')
        target = Path(self.env['XDG_CONFIG_HOME']) / name
        if locations:
            self.write(self.root/'.dots/file-locations.json',dict(schema=1,repository='dots',locations=[
                dict(id='config',kind='root',target='${CONFIG}',source='config',platforms=self.resource['platforms'])]))
        return source, target

    def plan(self, *values, **kwargs):
        manager = Manager()
        args = argparse.Namespace(action='add',values=list(map(str,values)),repo=None,scan=False,
                                  directory_link=False,backup=False,dry_run=False,target=None)
        for k,v in kwargs.items(): setattr(args,k,v)
        ops,guards,catalogs,rows = manager.plan(args)
        return manager,ops,guards,catalogs,rows

    def test_existing_relative_directory_link_preserves_nested_links_and_uninstall(self):
        source,target=self.prepare(directory=True)
        outside=self.home/'outside'; outside.write_text('not imported')
        (source/'shell').symlink_to(outside)
        (source/'dangling').symlink_to(self.home/'absent')
        target.parent.mkdir(); target.symlink_to(os.path.relpath(source,target.parent))
        before=(target.lstat().st_ino,os.readlink(target),digest(source),outside.read_bytes())
        result=json.loads(self.files('add',str(target),'--yes','--json').stdout)
        self.assertEqual(before,(target.lstat().st_ino,os.readlink(target),digest(source),outside.read_bytes()))
        rows=Catalog(self.root,self.platform).records()
        row=next(r for r in rows if r['target']==str(target))
        self.assertEqual((row['strategy'],row['status']),('directory-link','linked'))
        self.assertFalse((state_root()/'installation.json').exists())
        uninstall=Installation(self.root);uninstall.plan_uninstall();self.assertEqual(uninstall.operations,[])
        count=len(Store(state_root()).records())
        self.assertEqual(json.loads(self.files('add',str(source),'--yes','--json').stdout)['status'],'unchanged')
        self.assertEqual(len(Store(state_root()).records()),count)
        self.undo(result['id'])
        self.assertEqual(before,(target.lstat().st_ino,os.readlink(target),digest(source),outside.read_bytes()))

    def test_new_link_receipt_uninstall_and_registry_profile(self):
        source,target=self.prepare()
        result=json.loads(self.files('add',str(source),'--yes','--json').stdout)
        self.assertEqual(target.resolve(),source)
        receipt=json.loads((state_root()/'installation.json').read_text())
        self.assertIn(str(target),receipt['entries'])
        row=next(r for r in json.loads(self.path.read_text())['files']['dots'] if r['source']=='config/example ü')
        self.assertNotIn('platforms',row)
        self.assertIn('dots:'+row['id'],{r['id'] for r in json.loads(self.registry.read_text())['resources']})
        uninstall=Installation(self.root);uninstall.plan_uninstall();uninstall.apply('uninstall')
        self.assertFalse(target.exists());self.assertTrue(source.exists())

    def test_preview_is_read_only_and_target_required(self):
        source,target=self.prepare(locations=False)
        before=self.path.read_bytes(),self.registry.read_bytes()
        preview=json.loads(self.files('add',str(source),'--dry-run','--json').stdout)
        self.assertEqual(preview['items'][0]['status'],'needs-target')
        self.assertFalse(state_root().exists())
        self.files('add',str(source),'--yes',code=1)
        self.assertEqual(before,(self.path.read_bytes(),self.registry.read_bytes()))
        self.files('add',str(source),'--target',str(target),'--yes')
        self.assertEqual(target.resolve(),source)

    def test_explicit_source_uses_observed_link_before_location(self):
        source,target=self.prepare()
        other=target.parent/'other';other.parent.mkdir();other.symlink_to(source)
        self.files('add',str(source),'--yes')
        self.assertFalse(target.exists())
        self.assertEqual(next(r for r in Catalog(self.root,self.platform).records() if r['source']==str(source))['target'],str(other))

    def test_source_and_link_operands_deduplicate(self):
        source,target=self.prepare();target.parent.mkdir();target.symlink_to(source)
        self.files('add',str(source),str(target),'--yes')
        self.assertEqual(sum(r['source']==str(source) for r in Catalog(self.root,self.platform).records()),1)

    def test_backup_replacement_and_undo(self):
        source,target=self.prepare();target.parent.mkdir();target.write_text('original')
        self.files('add',str(source),'--yes',code=1)
        result=json.loads(self.files('add',str(source),'--backup','--yes','--json').stdout)
        self.assertTrue(target.is_symlink())
        self.undo(result['id'])
        self.assertFalse(target.is_symlink());self.assertEqual(target.read_text(),'original')
        self.assertFalse((state_root()/'installation.json').exists())

    def test_broken_chained_external_and_unrelated_links_refused(self):
        source,target=self.prepare();target.parent.mkdir()
        for dest in [self.home/'absent',self.home/'outside',self.root/'config/chain']:
            if dest.name=='outside':dest.write_text('outside')
            if dest.name=='chain':dest.symlink_to(source)
            target.symlink_to(dest)
            self.files('add',str(target),'--yes',code=1);target.unlink()
        external=self.home/'other';external.write_text('other');target.symlink_to(external)
        self.files('add',str(source),'--yes','--backup',code=1)
        self.assertEqual(target.resolve(),external)

    def test_claim_conflict_and_disabled_mapping_preserved(self):
        source,target=self.prepare(directory=True)
        data=json.loads(self.path.read_text())
        data['files']['dots'][0]['target']='${CONFIG}/example ü/settings'
        self.write(self.path,data)
        self.files('add',str(source),'--yes',code=1)
        data['files']['dots'][0].update(source='config/example ü',target='${CONFIG}/example ü',strategy='directory-link',enabled=False)
        self.write(self.path,data)
        self.files('add',str(source),'--yes',code=1)
        self.assertFalse(json.loads(self.path.read_text())['files']['dots'][0]['enabled'])

    def test_stale_source_target_location_and_profile(self):
        source,target=self.prepare()
        for kind in ('source','target','location','profile'):
            manager,ops,guards,catalogs,rows=self.plan(source)
            path={'source':source,'target':target,'location':self.root/'.dots/file-locations.json','profile':self.path}[kind]
            old=path.read_bytes() if path.exists() else None
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((old or b'')+b' ')
            with self.assertRaisesRegex(ValueError,'changed'):
                manager.link_installation.apply('add',catalogs=catalogs)
            if old is None:path.unlink()
            else:path.write_bytes(old)
            self.assertFalse(target.is_symlink())

    def test_atomic_rollback_and_interrupted_recovery(self):
        source,target=self.prepare()
        before=self.registry.read_bytes(),self.path.read_bytes()
        for interrupted in (False,True):
            manager,ops,guards,catalogs,rows=self.plan(source)
            store=manager.link_installation.store;save=store.save
            def fail(doc):
                save(doc)
                if doc['status']=='applying' and doc['operations'][0]['phase']=='done':
                    if interrupted:raise SystemExit('interrupted')
                    raise OSError('injected')
            with patch.object(store,'save',side_effect=fail):
                with self.assertRaises((OSError,SystemExit)):
                    manager.link_installation.apply('add',catalogs=catalogs)
            for journal in store.records():
                if journal['status'] in ('applying','preparing','rolling-back','recovery-required'):
                    store.recover(journal['id'])
            self.assertFalse(target.exists())
            self.assertEqual(before,(self.registry.read_bytes(),self.path.read_bytes()))

    def test_discovery_picker_and_mixed_scan(self):
        source,target=self.prepare(directory=True)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        unknown=self.root/'config'/'unmapped';unknown.mkdir();(unknown/'settings').write_text('kept')
        # Only the explicit app location is inferable.
        self.write(self.root/'.dots/file-locations.json',dict(schema=1,repository='dots',locations=[
            dict(id='example',kind='root',source='config/example ü',target='${CONFIG}/example ü',platforms=self.resource['platforms'])]))
        rows=candidates(Manager())
        self.assertEqual(sum(r.get('source')==str(source) for r in rows),1)
        self.assertTrue(any(r['status']=='needs-target' for r in rows))
        selected=picker.candidates(Manager(),'add',[str(source)])
        self.assertEqual(len(selected),1);self.assertEqual(selected[0]['strategy'],'directory-link')
        preview=json.loads(self.files('add','--scan','--dry-run','--json').stdout)
        self.assertTrue(any(r['status']=='skipped' for r in preview['items']))
        self.files('add','--scan','--yes');self.assertEqual(target.resolve(),source)
        self.assertFalse((target.parent/'unmapped').exists())

    def test_source_root_boundaries_and_special_files(self):
        source,target=self.prepare(directory=True)
        outside=self.root/'outside';outside.write_text('outside')
        self.files('add',str(outside),'--target',str(target),'--yes',code=1)
        nested=source/'nested';nested.mkdir();(nested/'.git').write_text('gitdir: elsewhere')
        self.files('add',str(source),'--yes',code=1)
        (nested/'.git').unlink()
        if hasattr(os,'mkfifo'):
            os.mkfifo(source/'fifo');self.files('add',str(source),'--yes',code=1)
        self.assertFalse(target.exists())

    def test_bash_native_json_completion_and_literal_paths(self):
        source,target=self.prepare(name='- ü$(touch should-not-exist)',locations=False)
        outputs=[]
        for prefix in ([str(self.root/'bin/dots')],[sys.executable,'-B',str(self.root/'lib/dots/cli.py')]):
            command=[*prefix,'--color=always','--icons=always','files','add',str(source),
                     '--target',str(target),'--dry-run','--json']
            result=subprocess.run(command,env=self.env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('\x1b',result.stdout);outputs.append(json.loads(result.stdout))
        self.assertEqual(outputs[0],outputs[1]);self.assertFalse(state_root().exists())
        for shell in ('bash','zsh','fish','powershell'):
            prefix=([sys.executable,'-B',str(self.root/'lib/dots/cli.py')] if shell=='powershell'
                    else [str(self.root/'bin/dots')])
            words=(['__complete','files','add','--t'] if shell=='powershell'
                   else ['__complete',shell,'3','--','dots','files','add','--t'])
            result=subprocess.run([*prefix,*words],
                                  env=self.env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('--target',result.stdout)
        self.assertFalse((self.home/'should-not-exist').exists())

    def test_windows_destination_fixture_and_excluded_owner(self):
        source,target=self.prepare(locations=False)
        with patch.dict(os.environ,APPDATA=str(self.home/'Roaming'),LOCALAPPDATA=str(self.home/'Local')):
            catalog=Catalog(self.root,'windows')
            row=Registration(Manager(catalog)).candidate(source,target='${APPDATA}/Example/settings.json')
            self.assertEqual(row['target'],str(self.home/'Roaming/Example/settings.json'))
            self.assertEqual(row['profile'],'windows')
        sources=self.root/'.dots/sources.json';doc=json.loads(sources.read_text())
        private=self.root/'config/private';private.mkdir();(private/'settings').write_text('private')
        doc['sources'].append(dict(id='private',path='config/private',roots=[],platforms=self.resource['platforms'],excluded=True))
        self.write(sources,doc)
        self.files('add',str(private/'settings'),'--target',str(target),'--yes',code=1)
        self.assertFalse(target.exists())

    def test_windows_readlink_substitutions_preserve_namespace_restrictions(self):
        self.assertEqual(native_link_text('\\\\?\\C:\\Users\\example\\config',True),'C:\\Users\\example\\config')
        self.assertEqual(native_link_text('\\\\?\\UNC\\server\\share\\config',True),'\\\\server\\share\\config')
        for value in ('\\\\?\\GLOBALROOT\\Device\\config','\\\\?\\UNC\\wsl$\\Ubuntu\\config'):
            with self.assertRaises(ValueError): validate_windows_path(native_link_text(value,True))
        self.assertEqual(native_link_text('../config',True),'../config')
        self.assertEqual(native_link_text('\\\\?\\C:\\config',False),'\\\\?\\C:\\config')

    def test_source_owner_filter_is_independent_of_location_owner(self):
        self.prepare()
        source=self.root/'sources/custom/config/moved';source.parent.mkdir(parents=True);source.write_text('kept')
        path=self.root/'.dots/sources.json';doc=json.loads(path.read_text())
        doc['sources'].append(dict(id='custom',path='sources/custom',roots=['config'],platforms=self.resource['platforms']))
        self.write(path,doc)
        target=Path(self.env['XDG_CONFIG_HOME'])/'moved';target.parent.mkdir();target.symlink_to(source)
        rows=Manager().system('custom')
        self.assertEqual([(r['repository'],r['path']) for r in rows],[('custom',str(target))])
        self.files('add',str(source),'--repo','custom','--yes')
        self.assertIn('custom',json.loads(self.path.read_text())['files'])


if __name__=='__main__': unittest.main(verbosity=2)
