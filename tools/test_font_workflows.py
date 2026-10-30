#!/usr/bin/env python3
"""Installed-font transfers, app archives and preferences in owned fixtures."""
from copy import deepcopy
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_font_directories as directory_fixtures
from test_fonts import font
from fonts.model import Library,Plan,metadata,digest
from fonts import operations as ops
from fonts.commands import parser
from fonts_cli import mutate,plan_action
from fonts.workspace import Workspace
from fonts.payloads import retain
from fonts.inventory import snapshot
from fonts.defaults import rows as defaults


class Workflows(unittest.TestCase):
    setUp=directory_fixtures.FontDirectories.setUp
    library=directory_fixtures.FontDirectories.library
    seed=directory_fixtures.FontDirectories.seed
    imported=directory_fixtures.FontDirectories.imported
    execute=directory_fixtures.FontDirectories.execute
    catalog=directory_fixtures.FontDirectories.catalog

    def action(self,*argv,platform='termux'):
        args=parser().parse_args([*argv,'--yes','--no-reload'] if argv[0] in ('set','install','migrate','restore','uninstall','rollback','upgrade') else [*argv,'--yes'])
        return mutate(Library(platform=platform,directory=args.directory),args)

    def family(self,version='v1.0.0'):
        identity='nerd:Fixture'
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            payload=Path(tmp)/'payload';payload.mkdir()
            for filename,name,style in [('mono.ttf','Fixture Nerd Font Mono','Regular'),('bold.ttf','Fixture Nerd Font Mono','Bold'),('propo.ttf','Fixture Nerd Font Propo','Regular')]:
                font(payload/filename,name,style,version)
            (payload/'OFL.txt').write_text('Fixture license')
            record=dict(fonts=[metadata(p) for p in sorted(payload.glob('*.ttf'))],licenses=['OFL.txt'],
                provider='nerd',fingerprint=version,provenance=dict(revision=version,source='fixture'))
            plan=Plan(self.library('termux'));ops.stage(plan,identity,version,payload,record,'Fixture');plan.finish();plan.apply('fixture')
        return identity,version

    def external(self,system=False):
        path=(self.home/'system-fonts' if system else ops.install_root(self.library('termux')).parent)/'External.ttf'
        path.parent.mkdir(parents=True,exist_ok=True);font(path,'External Mono')
        found=[dict(path=str(path),name='External Mono',source='system' if system else 'fontconfig')]
        patch('fonts_cli.system_fonts',return_value=found).start()
        return path,snapshot(self.library('termux'))[0][0]['id']

    def test_termux_archives_single_face_previous_custom_and_preferences(self):
        identity,version=self.family()
        previous=self.home/'.termux/font.ttf';previous.parent.mkdir();font(previous,'Previous Mono')
        original=previous.read_bytes()
        result=self.action('set',identity,'--target','termux','--face','mono.ttf')
        archive=self.library('termux','PROFILEFONTS')
        record=archive.families[identity]['versions'][version]
        self.assertEqual([f['file'] for f in record['fonts']],['mono.ttf']);self.assertTrue(record['partial'])
        self.assertTrue(any(k.startswith('local:') for k in archive.families))
        self.assertIsNone(self.library('termux').families[identity]['installed'])
        pref=defaults(self.library('termux'));self.assertEqual(pref['items'][0]['face'],'mono.ttf')
        self.assertEqual(self.action('set',identity,'--target','termux','--face','mono.ttf')['status'],'unchanged')
        self.action('set',identity,'--target','termux','--face','bold.ttf')
        archive=self.library('termux','PROFILEFONTS')
        self.assertEqual({f['file'] for f in archive.families[identity]['versions'][version]['fonts']},{'mono.ttf','bold.ttf'})
        self.action('restore','termux')
        self.assertEqual(defaults(self.library('termux'))['items'][0]['face'],'bold.ttf')
        self.assertTrue(result['transaction']);self.assertNotEqual(previous.read_bytes(),original)

    def test_reselect_legacy_termux_backfills_archive_and_preferences_without_rewriting_font(self):
        from fonts.config import configure
        identity,version=self.family()
        plan=Plan(self.library('termux'))
        face=next(f for f in plan.document['families'][identity]['versions'][version]['fonts'] if f['file']=='mono.ttf')
        configure(plan,identity,version,face,'termux');plan.finish();plan.apply('legacy-set')
        active=self.home/'.termux/font.ttf';before=active.stat();checksum=digest(active)
        self.assertEqual(defaults(self.library('termux'))['items'],[])
        self.assertEqual(self.library('termux','PROFILEFONTS').families,{})
        args=parser().parse_args(['set',identity,'--version',version,'--face','mono.ttf','--target','termux','--dry-run'])
        preview=mutate(self.library('termux'),args)
        paths={operation['path'] for operation in preview['operations']}
        self.assertTrue(paths);self.assertNotIn(str(active),paths)
        self.assertEqual(self.library('termux','PROFILEFONTS').families,{})
        result=self.action('set',identity,'--version',version,'--face','mono.ttf','--target','termux')
        self.assertEqual(result['status'],'complete')
        archive=self.library('termux','PROFILEFONTS')
        record=archive.families[identity]['versions'][version]
        self.assertEqual([f['file'] for f in record['fonts']],['mono.ttf'])
        self.assertEqual(digest(archive.file(identity,version,record['fonts'][0])),checksum)
        pref=defaults(self.library('termux'))['items'][0]
        self.assertEqual((pref['id'],pref['version'],pref['face']),(identity,version,'mono.ttf'))
        self.assertEqual((active.stat().st_ino,active.stat().st_mtime_ns),(before.st_ino,before.st_mtime_ns))
        self.assertEqual(self.action('set',identity,'--version',version,'--face','mono.ttf','--target','termux')['status'],'unchanged')
        self.action('undo',result['transaction'])
        self.assertEqual(defaults(self.library('termux'))['items'],[])
        self.assertEqual(self.library('termux','PROFILEFONTS').families,{})
        self.assertEqual(digest(active),checksum)

    def test_desktop_retains_variant_registers_and_shared_preferences(self):
        identity,version=self.family()
        path=self.home/'settings.json';path.write_text('{"editor.fontSize": 17}')
        self.action('set',identity,'--target','vscode-editor','--config',str(path),'--face','mono.ttf')
        self.action('set',identity,'--target','vscode-terminal','--config',str(path),'--face','mono.ttf')
        record=self.library('termux','PROFILEFONTS').families[identity]['versions'][version]
        self.assertEqual({f['file'] for f in record['fonts']},{'mono.ttf','bold.ttf'})
        self.assertEqual(len(self.library('termux').families[identity]['installed']['files']),2)
        self.assertEqual(len(defaults(self.library('termux'))['items']),2)
        self.assertEqual(self.action('restore')['status'],'unchanged')
        self.assertEqual(json.loads(path.read_text())['editor.fontSize'],17)

    def test_exact_face_infers_variant_and_default_set_preserves_installed_variant(self):
        identity,version=self.family();config=self.home/'settings.json';config.write_text('{}')
        self.action('set',identity,'--target','vscode-editor','--config',str(config),'--face','propo.ttf')
        self.assertEqual(self.library('termux').families[identity]['installed']['variant'],'propo')
        self.action('set',identity,'--target','vscode-editor','--config',str(config))
        self.assertEqual(defaults(self.library('termux'))['items'][0]['face'],'propo.ttf')

    def test_batch_copy_between_stores_and_idempotence(self):
        first,_=self.family();second,_,_=self.imported('termux')
        self.action('install',first,second,'--directory','DOTFONTS')
        self.action('install',first,second,'--from','DOTFONTS','--directory','PROFILEFONTS')
        self.assertEqual(len(self.library('termux','PROFILEFONTS').families),2)
        self.assertIsNone(self.library('termux').families[first]['installed'])
        self.assertEqual(self.action('install',first,second,'--from','DOTFONTS','--directory','PROFILEFONTS')['status'],'unchanged')
        with self.assertRaisesRegex(ValueError,'one family'):self.action('install',first,second,'--version','v1')

    def test_late_batch_conflict_leaves_earlier_payload_unwritten(self):
        identity,version=self.family();second,_,_=self.imported('termux')
        destination=self.library('termux','DOTFONTS');occupied=destination.folder(second,next(iter(self.library('termux').families[second]['versions'])))
        occupied.mkdir(parents=True);(occupied/'keep').write_text('mine')
        with self.assertRaisesRegex(ValueError,'occupied'):self.action('install',identity,second,'--directory','DOTFONTS')
        self.assertFalse(destination.folder(identity,version).exists());self.assertEqual((occupied/'keep').read_text(),'mine')

    def test_copy_and_migrate_keep_lookup_undo_and_drift(self):
        original,identity=self.external();before=original.read_bytes()
        self.action('copy',identity,'--directory','DOTFONTS')
        self.assertFalse(original.is_symlink());self.assertEqual(original.read_bytes(),before)
        result=self.action('migrate',identity,'--directory','DOTFONTS')
        self.assertTrue(original.is_symlink());self.assertEqual(original.read_bytes(),before)
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            args=parser().parse_args(['undo',result['transaction'],'--directory','DOTFONTS'])
            self.assertIn('fonts',plan_action(self.library('termux','DOTFONTS'),args,tmp).refresh)
        row=snapshot(self.library('termux'))[0][0]
        self.assertEqual(row['ownership'],'managed')
        self.assertEqual(self.action('migrate',identity,'--directory','DOTFONTS')['status'],'unchanged')
        local=row['managed_id'];version=row['version']
        with self.assertRaisesRegex(ValueError,'cannot remove'):self.action('remove',local,'--version',version)
        self.action('undo',result['transaction'],'--directory','DOTFONTS')
        self.assertFalse(original.is_symlink());self.assertEqual(original.read_bytes(),before)
        self.action('migrate',identity,'--directory','DOTFONTS')
        original.unlink();original.write_bytes(before+b'drift')
        with self.assertRaisesRegex(ValueError,'changed'):self.action('uninstall',local)

    def test_migrated_font_native_install_replaces_alias_and_uninstall(self):
        path,identity=self.external()
        self.action('migrate',identity,'--directory','DOTFONTS')
        local=next(iter(self.library('termux').families))
        self.action('install',local)
        self.assertFalse(path.exists());self.assertEqual(self.library('termux').document.get('adoptions'),{})
        self.action('uninstall',local)
        self.assertIsNone(self.library('termux').families[local]['installed'])

    def test_system_fonts_copy_only_and_missing_inventory_notice(self):
        path,identity=self.external(system=True)
        rows,_=snapshot(self.library('termux'));self.assertFalse(rows[0]['migratable'])
        with self.assertRaisesRegex(ValueError,'copy-only'):self.action('migrate',identity,'--directory','DOTFONTS')
        self.assertEqual(self.library('termux').families,{})
        self.action('copy',identity,'--directory','DOTFONTS');self.assertTrue(path.is_file())
        with patch('fonts_cli.system_fonts',side_effect=ValueError('fc-list unavailable')):
            _,notices=snapshot(self.library('termux'));self.assertIn('fc-list',notices[0])

    def test_set_installed_copies_family_styles_without_deleting_source(self):
        path,identity=self.external();bold=path.with_name('Bold.ttf');font(bold,'External Mono','Bold')
        patch('fonts_cli.system_fonts',return_value=[dict(path=str(p),name='External Mono',source='fontconfig') for p in (path,bold)]).start()
        config=self.home/'kitty.conf';config.write_text('font_family Old\nfont_size 12\n')
        self.action('set',identity,'--target','kitty','--config',str(config))
        record=next(iter(self.library('termux','PROFILEFONTS').families.values()))
        self.assertEqual(len(next(iter(record['versions'].values()))['fonts']),2)
        self.assertFalse(path.is_symlink());self.assertTrue(bold.exists())

    def test_failed_app_preflight_leaves_all_scopes_unchanged(self):
        identity,_=self.family();before=digest(self.library('termux').path)
        config=self.home/'settings.json';config.write_text('invalid json')
        with self.assertRaises(ValueError):self.action('set',identity,'--target','vscode-editor','--config',str(config))
        self.assertEqual(digest(self.library('termux').path),before)
        self.assertFalse(self.library('termux','PROFILEFONTS').data.exists())

    def test_partial_expansion_validates_conflicts_and_completes_family(self):
        identity,version=self.family()
        self.action('set',identity,'--target','termux','--face','mono.ttf')
        self.action('install',identity,'--from','personal','--directory','PROFILEFONTS')
        record=self.library('termux','PROFILEFONTS').families[identity]['versions'][version]
        self.assertEqual(len(record['fonts']),3);self.assertFalse(record['partial'])
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            source=self.library('termux');workspace=Workspace(source,tmp)
            archive=workspace.store('PROFILEFONTS')
            workspace.user.document['families'][identity]['versions'][version]['fonts'][0]['family']='Conflicting'
            with self.assertRaisesRegex(ValueError,'metadata'):retain(workspace.user,archive,identity,version,tmp,faces=['bold.ttf'])

    def test_offline_dry_run_and_failed_download_leave_no_store(self):
        self.catalog(['v1.0.0'])
        args=parser().parse_args(['set','nerd:Fixture','--target','termux','--dry-run'])
        with patch('fonts.providers.download',side_effect=AssertionError('network')):
            result=mutate(self.library('termux'),args)
        self.assertIn('download',result['items'][0]['action']);self.assertEqual(self.library('termux').families,{})
        with patch('fonts.providers.download',side_effect=ValueError('network unavailable')):
            with self.assertRaisesRegex(ValueError,'network'):self.action('set','nerd:Fixture','--target','termux')
        self.assertFalse((self.home/'.termux/font.ttf').exists())

    def test_remote_set_and_restore_exact_version_after_catalog_and_state_loss(self):
        self.catalog(['v1.0.0','v2.0.0']);calls=[]
        def download(identity,spec,payload,**kwargs):
            calls.append(spec['revision']);payload.mkdir()
            # Use a retained fixture, avoiding generated font timestamp changes.
            shutil.copy2(self.source/'-Fixture Regular.ttf',payload/'Remote.ttf')
            (payload/'OFL.txt').write_text('Fixture license')
            return dict(fonts=[metadata(payload/'Remote.ttf')],licenses=['OFL.txt'],fingerprint=spec['fingerprint'],
                provenance=dict(revision=spec['revision'],source='official fixture'))
        with patch('fonts.providers.download',side_effect=download):
            self.action('set','nerd:Fixture','--version','v1.0.0','--target','termux')
            library=self.library('termux');archive=self.library('termux','PROFILEFONTS')
            shutil.rmtree(library.data);shutil.rmtree(archive.data)
            library.path.unlink();library.catalog_path.unlink()
            self.action('restore','termux')
        self.assertEqual(calls,['v1.0.0','v1.0.0'])
        self.assertEqual(self.library('termux').document['targets']['termux']['version'],'v1.0.0')

    def test_missing_local_default_refuses_without_changing_preferences(self):
        identity,_,_=self.imported('termux')
        self.action('set',identity,'--target','termux')
        library=self.library('termux');archive=self.library('termux','PROFILEFONTS')
        pref=Path(defaults(library)['path']);before=digest(pref)
        library.path.unlink();shutil.rmtree(library.data);shutil.rmtree(archive.data)
        with self.assertRaisesRegex(ValueError,'import its original'):self.action('restore','termux')
        self.assertEqual(digest(pref),before)

    def test_preference_failure_rolls_back_app_archive_and_collection(self):
        import transactions
        identity,version=self.family();library=self.library('termux');before=digest(library.path)
        old=self.home/'.termux/font.ttf';old.parent.mkdir();font(old,'Previous Mono');old_digest=digest(old)
        pref=Path(defaults(library)['path']);rename=transactions.os.rename;failed=False
        def fail(source,destination):
            nonlocal failed
            if not failed and Path(destination)==pref and '.dots-new-' in str(source):
                failed=True;raise OSError('fixture preference failure')
            return rename(source,destination)
        with patch.object(transactions.os,'rename',side_effect=fail),self.assertRaisesRegex(OSError,'preference'):
            self.action('set',identity,'--target','termux','--face','mono.ttf')
        self.assertEqual(digest(old),old_digest);self.assertEqual(digest(library.path),before)
        self.assertFalse(pref.exists());self.assertFalse(self.library('termux','PROFILEFONTS').folder(identity,version).exists())
        self.assertEqual(transactions.Store(library.state).records()[-1]['status'],'rolled-back')

    def test_windows_migration_registry_and_native_install_are_journaled(self):
        library=self.library('windows');base=ops.install_root(library)
        if os.name!='nt':
            def validate(spec):
                for value in (spec['before'],spec['after']):
                    if value is not None:self.assertEqual(Path(value).parent,base)
            patch('font_registry.validate',side_effect=validate).start()
        path=base/'External.ttf';path.parent.mkdir(parents=True);font(path,'External Mono')
        self.registry['External Mono Regular (TrueType)']=str(path)
        patch('fonts_cli.system_fonts',return_value=[dict(path=str(path),name='External Mono',source='user')]).start()
        identity=snapshot(library)[0][0]['id']
        result=self.action('migrate',identity,'--directory','DOTFONTS',platform='windows')
        self.assertEqual(self.registry['External Mono Regular (TrueType)'],str(path));self.assertFalse(path.is_symlink())
        local=next(iter(self.library('windows').families))
        self.action('install',local,platform='windows')
        registered=Path(self.registry['External Mono Regular (TrueType)']);self.assertTrue(registered.is_file())
        self.assertNotEqual(registered,path);self.assertFalse(path.exists())
        self.action('uninstall',local,platform='windows');self.assertEqual(self.registry,{})
        self.assertTrue(result['transaction'])

    def test_menu_routes_and_machine_output(self):
        from fonts.menus import HOME_ACTIONS,home,set_menu
        self.assertTrue({'installed','set','downloaded','defaults'}<={k for k,_ in HOME_ACTIONS})
        with patch('fonts.menus.select',return_value=None),patch('fonts.menus.context_for',return_value=None):
            self.assertEqual(home(parser().parse_args([])),0)
            self.assertEqual(set_menu(parser().parse_args(['set'])),0)
        for argv in [('defaults','--json'),('browse','--downloaded','--json'),('installed','--json')]:
            first=json.loads(self.execute(*argv).stdout)
            self.assertEqual(first,json.loads(self.execute(*argv,native=True).stdout))
            self.assertEqual(first,json.loads(self.execute(*argv,bash=True).stdout))


if __name__=='__main__':unittest.main(verbosity=2)
