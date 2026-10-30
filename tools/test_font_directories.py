#!/usr/bin/env python3
"""Font directory lifecycle in owned repositories; no real installs or reloads."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_fonts as fixtures
ROOT,font=fixtures.ROOT,fixtures.font
from fonts.model import Library, Plan, metadata, digest
from fonts import operations as ops
from fonts.commands import parser
from fonts.destinations import Destinations
from fonts_cli import plan_action, mutate
from transactions import Store


class FontDirectories(unittest.TestCase):
    def setUp(self):
        fixtures.Fonts.setUp(self)
        self.root=self.home/'-checkout ü'
        for name in ('linux','wsl','termux','windows'):
            directory=self.root/'profiles'/name;directory.mkdir(parents=True)
            data=dict(schema=1,id=name)
            if name in ('windows','termux'):data['alias']='WINDOTS' if name=='windows' else 'DROIDOTS'
            (directory/'profile.json').write_text(json.dumps(data))
        # Native and Bash frontends run the same source in this owned checkout.
        for name in ('lib','bin'):
            shutil.copytree(ROOT/name,self.root/name,ignore=shutil.ignore_patterns('__pycache__'))
        os.environ['DOTS']=self.environment['DOTS']=str(self.root)
        self.registry.clear()
        patch('fonts.operations.refresh',return_value=[]).start()

    def library(self,platform=None,directory=None):return Library(platform=platform,directory=directory)

    imported=fixtures.Fonts.imported
    execute=fixtures.Fonts.execute

    def action(self,*argv,directory='DOTFONTS',platform=None):
        args=parser().parse_args([*argv,'--directory',directory,'--yes'])
        return mutate(self.library(platform,directory),args)

    def seed(self,version='v1.0.0',directory=None,platform=None):
        identity='nerd:Fixture'
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            payload=Path(tmp)/'payload';payload.mkdir()
            font(payload/'-Fixture.ttf','Fixture Nerd Font Mono',version='Version '+version)
            (payload/'OFL.txt').write_text('Fixture license')
            record=dict(fonts=[metadata(payload/'-Fixture.ttf')],licenses=['OFL.txt'],provider='nerd',
                        fingerprint=version,provenance=dict(source='official fixture',revision=version,upstream_version=version))
            plan=Plan(self.library(platform,directory));ops.stage(plan,identity,version,payload,record,'Fixture');plan.finish();plan.apply('seed')
        return identity,version

    def catalog(self,versions):
        library=self.library();catalog=deepcopy(library.catalog)
        catalog['families']['nerd:Fixture']=dict(name='Fixture',provider='nerd',latest=versions[-1],
            versions={v:dict(fingerprint=v,provider='nerd',revision=v) for v in versions})
        plan=Plan(library);plan.put(library.catalog_path,data=catalog);plan.apply('fixture-catalog')

    def test_directories_resolve_backend_aliases_without_creating_paths(self):
        destinations=Destinations()
        self.assertNotIn('SDOTSFONTS',destinations.names)
        root=self.root/'fonts'
        for name in ('DOTFONTS','$DOTFONTS','${DOTFONTS}','$env:DOTFONTS',str(root)):
            self.assertEqual(destinations.resolve(name)[0],root)
        self.assertEqual(destinations.resolve('DOTSWINDOWSFONTS')[0],destinations.resolve('WINDOTSFONTS')[0])
        with patch.dict(os.environ,DOTFONTS=str(self.home/'not a backend path')):
            self.assertEqual(Destinations().resolve('DOTFONTS')[0],root)
        for invalid in ('$(touch nope)','FONTS',str(self.home/'arbitrary')):
            with self.assertRaises(ValueError):destinations.resolve(invalid)
        for platform in ('termux','linux','wsl','windows'):
            self.assertEqual(self.library(platform,'DOTFONTS').directory,root)
        self.assertFalse(root.exists());self.assertFalse(self.library().path.exists())
        root.symlink_to(self.source,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'link'):destinations.resolve('DOTFONTS')
        root.unlink();root.symlink_to(self.home/'missing',target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'link'):destinations.resolve('DOTFONTS')

    def test_install_is_storage_only_idempotent_and_scoped(self):
        identity,version=self.seed()
        before=digest(self.library().folder(identity,version))
        result=self.action('install',identity,'--version',version)
        self.assertEqual(result['status'],'complete')
        self.assertIn('fonts-directory-',Store(self.library().state).load(result['transaction'])['action'])
        selected=self.library(directory='DOTFONTS')
        self.assertTrue(selected.version(identity,version)[1]['available'])
        self.assertEqual(before,digest(selected.folder(identity,version)))
        self.assertEqual(self.action('install',identity,'--version',version)['status'],'unchanged')
        self.assertFalse(ops.install_root(self.library()).exists());self.assertFalse((self.home/'.termux').exists())
        self.assertIsNone(self.library().families[identity]['installed'])
        self.action('install',identity,'--version',version,directory='DOTSLINUXFONTS')
        self.assertEqual(len(self.library().collection['directories']),2)
        self.assertEqual(self.library(directory='DOTFONTS').active(),[])
        self.assertEqual(self.registry,{})

    def test_versions_update_uninstall_reinstall_preserve_history_and_other_scope(self):
        identity,first=self.seed();_,second=self.seed('v2.0.0');self.catalog([first,second])
        for scope in ('DOTFONTS','DOTSLINUXFONTS'):self.action('install',identity,'--version',first,directory=scope)
        self.action('update',identity,'--version',second)
        selected=self.library(directory='DOTFONTS');record=deepcopy(selected.families[identity]['versions'][first])
        self.assertEqual(len(selected.families[identity]['versions']),2)
        self.assertEqual(len(self.library(directory='DOTSLINUXFONTS').families[identity]['versions']),1)
        self.assertIsNone(self.library().families[identity]['installed'])
        self.action('uninstall',identity,'--version',first)
        selected=self.library(directory='DOTFONTS');self.assertFalse(selected.folder(identity,first).exists())
        self.assertEqual(selected.families[identity]['versions'][first],dict(record,available=False))
        self.assertTrue(self.library(directory='DOTSLINUXFONTS').folder(identity,first).exists())
        self.assertTrue(self.library().folder(identity,first).exists())
        self.assertEqual(self.action('uninstall',identity,'--version',first)['status'],'unchanged')
        self.action('install',identity,'--version',first)
        self.assertEqual(self.library(directory='DOTFONTS').families[identity]['versions'][first],record)
        self.action('pin',identity,'--version',first)
        self.assertEqual(self.action('upgrade',identity)['items'][0]['action'],'skip pinned')
        with self.assertRaisesRegex(ValueError,'pinned'):self.action('uninstall',identity,'--version',first)
        self.action('unpin',identity)
        for version in (first,second):self.action('uninstall',identity,'--version',version)
        selected=self.library(directory='DOTFONTS')
        self.assertEqual(selected.rows()[0]['stored_versions'],[])
        self.assertEqual(self.action('upgrade')['items'][0]['action'],'skip uninstalled')
        self.assertEqual(self.library(directory='DOTFONTS').rows()[0]['stored_versions'],[])
        from fonts.browser import previews
        self.assertNotIn('font',previews(selected,selected.rows())[0])

    def test_explicit_use_activation_origin_switches_and_survives_directory_uninstall(self):
        identity,first=self.seed(directory='DOTFONTS');_,second=self.seed('v2.0.0',directory='DOTFONTS')
        self.assertFalse(self.library().families)
        used=self.action('use',identity,'--version',first)
        self.assertEqual(self.action('use',identity,'--version',first)['status'],'unchanged')
        selected=self.library(directory='DOTFONTS');user=self.library()
        self.assertEqual(selected.active()[0]['version'],first)
        installed=deepcopy(user.families[identity]['installed'])
        self.action('uninstall',identity,'--version',first)
        self.assertEqual(self.library().families[identity]['installed'],installed)
        for item in installed['files']:self.assertTrue(Path(item['path']).is_file())
        self.action('install',identity,'--version',first,directory='DOTSLINUXFONTS')
        self.action('use',identity,'--version',first,directory='DOTSLINUXFONTS')
        self.assertEqual(self.library(directory='DOTFONTS').active(),[])
        self.assertEqual(len(self.library(directory='DOTSLINUXFONTS').active()),1)
        self.action('use',identity,'--version',second)
        self.action('install',identity,'--version',first)
        self.action('rollback',identity,'--version',first)
        self.assertEqual(self.library().families[identity]['installed']['version'],first)
        self.assertTrue(self.library(directory='DOTFONTS').folder(identity,second).is_dir())
        self.assertIsNotNone(used['transaction'])

    def test_termux_set_rollback_and_desktop_set_remain_explicit(self):
        identity,first=self.seed(directory='DOTFONTS',platform='termux')
        _,second=self.seed('v2.0.0',directory='DOTFONTS',platform='termux')
        self.action('set',identity,'--version',first,'--target','termux',platform='termux')
        self.assertIsNone(self.library('termux').families[identity]['installed'])
        self.action('rollback',identity,'--version',second,platform='termux')
        self.assertEqual(self.library('termux').document['targets']['termux']['version'],second)
        self.assertIsNone(self.library('termux').families[identity]['installed'])
        config=self.home/'kitty.conf';config.write_text('font_size 14\nfont_family Old\n')
        self.action('set',identity,'--version',second,'--target','kitty','--config',str(config),platform='termux')
        self.assertIn('font_size 14',config.read_text());self.assertIn('Fixture Nerd Font Mono',config.read_text())
        self.assertEqual({r['selection'] for r in self.library('termux','PROFILEFONTS').active()},{'termux','kitty','user-fonts'})

    def test_windows_storage_has_no_registration_and_explicit_use_is_journaled(self):
        if os.name!='nt':
            # Exercise the native lifecycle on owned POSIX paths. The separate font
            # suite verifies the real PureWindowsPath validator with Windows paths.
            base=ops.install_root(self.library('windows'))
            def validate(spec):
                self.assertEqual(set(spec),{'name','before','after'})
                for value in (spec['before'],spec['after']):
                    if value is not None:self.assertEqual(Path(value).parent,base)
            patch('font_registry.validate',side_effect=validate).start()
        identity,version=self.seed(directory='DOTFONTS',platform='windows')
        self.assertEqual(self.registry,{})
        result=self.action('use',identity,'--version',version,platform='windows')
        self.assertEqual(len(self.registry),1)
        operations=Store(self.library('windows').state).load(result['transaction'])['operations']
        self.assertTrue(any('font_registry' in operation for operation in operations))
        self.action('undo',result['transaction'],platform='windows')
        self.assertEqual(self.registry,{})
        self.assertEqual(self.library('windows','DOTFONTS').active(),[])

    def test_undo_is_scoped_and_checks_later_other_directory_changes(self):
        identity,version=self.seed()
        result=self.action('install',identity,'--version',version)
        with self.assertRaisesRegex(ValueError,'scope'):self.action('undo',result['transaction'],directory='DOTSLINUXFONTS')
        args=parser().parse_args(['undo',result['transaction'],'--yes'])
        with tempfile.TemporaryDirectory() as tmp,self.assertRaisesRegex(ValueError,'scope'):plan_action(self.library(),args,tmp)
        self.action('undo',result['transaction'])
        self.assertEqual(self.library(directory='DOTFONTS').families,{})
        result=self.action('install',identity,'--version',version)
        self.action('install',identity,'--version',version,directory='DOTSLINUXFONTS')
        before=digest(self.library().path)
        with self.assertRaises(ValueError):self.action('undo',result['transaction'])
        self.assertEqual(digest(self.library().path),before)

    def test_drift_collision_stale_manifest_and_preflight_do_not_mutate(self):
        identity,version=self.seed();args=parser().parse_args(['install',identity,'--version',version,'--directory','DOTFONTS'])
        with tempfile.TemporaryDirectory() as tmp:
            selected=self.library(directory='DOTFONTS');plan=plan_action(selected,args,tmp)
            manifest=self.root/'profiles/linux/profile.json';manifest.write_text(manifest.read_text()+'\n')
            with self.assertRaises(ValueError):plan.apply('install')
            self.assertFalse(selected.folder(identity,version).exists())
            plan=plan_action(self.library(directory='DOTFONTS'),args,tmp)
            self.action('install',identity,'--version',version,directory='DOTSLINUXFONTS')
            with self.assertRaises(ValueError):plan.apply('install')
            self.assertFalse(selected.folder(identity,version).exists())
            plan=plan_action(self.library(directory='DOTFONTS'),args,tmp)
            (self.library().folder(identity,version)/'unowned.txt').write_text('drift')
            with self.assertRaises(ValueError):plan.apply('install')
            self.assertFalse(selected.folder(identity,version).exists())
        folder=self.library(directory='DOTFONTS').folder(identity,version);folder.mkdir(parents=True)
        (folder/'personal').write_text('preserve')
        # Restore only our own fixture drift to reach the independent collision check.
        (self.library().folder(identity,version)/'unowned.txt').unlink()
        with self.assertRaisesRegex(ValueError,'occupied'):self.action('install',identity,'--version',version)
        self.assertEqual((folder/'personal').read_text(),'preserve')
        shutil.rmtree(folder);self.action('install',identity,'--version',version)
        (folder/'unowned.txt').write_text('preserve')
        with self.assertRaisesRegex(ValueError,'changed'):self.action('uninstall',identity,'--version',version)
        with self.assertRaisesRegex(ValueError,'changed'):self.action('use',identity,'--version',version)

    def test_failed_inventory_write_rolls_back_payload_in_reverse_order(self):
        import transactions
        identity,version=self.seed();selected=self.library(directory='DOTFONTS')
        before=digest(selected.path);rename=transactions.os.rename;injected=False
        def fail(source,destination):
            nonlocal injected
            if not injected and Path(destination)==selected.path and '.dots-new-' in str(source):
                injected=True;raise OSError('fixture inventory failure')
            return rename(source,destination)
        with patch.object(transactions.os,'rename',side_effect=fail),self.assertRaises(OSError):
            self.action('install',identity,'--version',version)
        self.assertFalse(selected.folder(identity,version).exists());self.assertEqual(digest(selected.path),before)
        self.assertEqual(Store(selected.state).records()[-1]['status'],'rolled-back')
        self.assertEqual(self.action('install',identity,'--version',version)['status'],'complete')

    def test_download_dry_run_then_explicit_update_keeps_both_versions(self):
        self.catalog(['v1.0.0','v2.0.0']);identity='nerd:Fixture'
        before=digest(self.library().path)
        with patch('fonts.providers.download',side_effect=AssertionError('dry-run used network')):
            result=self.action('install',identity,'--version','v1.0.0','--dry-run')
        self.assertEqual(result['status'],'preview');self.assertEqual(digest(self.library().path),before)
        self.assertFalse((self.root/'fonts').exists())
        def download(identity,spec,payload,**kwargs):
            payload.mkdir();font(payload/'Remote.ttf',version=spec['revision'])
            (payload/'OFL.txt').write_text('Fixture license')
            return dict(fonts=[metadata(payload/'Remote.ttf')],licenses=['OFL.txt'],fingerprint=spec['fingerprint'],
                        provenance=dict(revision=spec['revision'],source='official fixture'))
        with patch('fonts.providers.download',side_effect=download):
            self.action('install',identity,'--version','v1.0.0')
            self.action('update',identity)
        self.assertEqual(set(self.library(directory='DOTFONTS').families[identity]['versions']),{'v1.0.0','v2.0.0'})
        self.assertFalse(self.library().families)

    def test_cli_completion_metadata_and_exact_scope_output(self):
        identity,version=self.seed();self.action('install',identity,'--version',version)
        for argv in (('directories','--json'),('list','--directory','DOTFONTS','--json'),
                     ('versions',identity,'--directory','DOTFONTS','--json')):
            first=self.execute(*argv).stdout
            self.assertEqual(first,self.execute(*argv,bash=True).stdout)
            self.assertEqual(first,self.execute(*argv,native=True).stdout)
        for frontend in ({},{'bash':True},{'native':True}):
            for action in ('install','use','directories'):
                self.assertIn('--directory',self.execute(action,'--help',**frontend).stdout)
        row=json.loads(self.execute('list','--installed','--directory','DOTFONTS','--json').stdout)['items'][0]
        self.assertEqual(row['stored_versions'],[version]);self.assertFalse(row['installed'])
        path=self.execute('path',identity,'--directory','DOTFONTS','--color','always').stdout
        self.assertEqual(path,str(self.library(directory='DOTFONTS').folder(identity,version)/'-Fixture.ttf')+'\n')
        command=[sys.executable,'-B',str(ROOT/'lib/dots/fonts/completion.py')]
        before=digest(self.library().path)
        for arguments,expected in ((['install','--directory','D'],'DOTFONTS'),
                                   (['use','--directory','DOTFONTS','nerd:'],'nerd:Fixture'),
                                   (['use',identity,'--directory','DOTFONTS','--version','v'],version)):
            result=subprocess.run([*command,*arguments],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn(expected,result.stdout)
        self.assertEqual(digest(self.library().path),before)
        for front in ([str(self.root/'bin/dots'),'__complete','bash','4','--','dots'],
                      [sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete']):
            result=subprocess.run([*front,'fonts','install','--directory','D'],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('DOTFONTS',result.stdout)
        self.execute('uninstall',identity,'--directory','DOTFONTS','--yes',code=1)
        self.execute('use',identity,'--yes',code=1)
        self.execute('install',identity,'--directory','DOTFONTS','--variant','mono','--yes',code=1)

    def test_browser_directory_choice_preserves_scope_and_requires_review(self):
        from fonts.browser import browse,family_actions,invoke
        identity,version=self.seed(directory='DOTFONTS')
        library=self.library(directory='DOTFONTS')
        with patch('fonts.browser.select',side_effect=['use',version,'mono']),patch('fonts.browser.run_action') as run:
            family_actions(library,library.rows()[0],None)
        argv=run.call_args.args[0]
        self.assertIn('--directory',argv);self.assertIn(str(self.root/'fonts'),argv);self.assertNotIn('--yes',argv)
        self.assertEqual(run.call_args.kwargs['kind'],'terminal')
        with patch('fonts.browser.run_action') as run:
            invoke(['update',identity],None,library)
        self.assertEqual(run.call_args.kwargs['kind'],'terminal')
        seen=[]
        def choose(title,pairs,context):
            seen.append(title)
            return 'directory' if title=='Fonts' else str(self.root/'fonts')
        from interaction import SelectionEvent
        with patch('fonts.browser.context_for',return_value=None),patch('fonts.browser.select',side_effect=choose),\
             patch('fonts.browser.picker',side_effect=SelectionEvent('back')) as picker:
            self.assertEqual(browse(parser().parse_args(['browse'])),0)
        self.assertEqual(seen,['Fonts','Directory'])
        self.assertIn(str(self.root/'fonts'),picker.call_args.args[2]['notice'])
        local_id,local_version,_=self.imported()
        native_row=next(r for r in self.library().rows() if r['id']==local_id)
        with patch('fonts.browser.select',return_value='show'),patch('fonts.browser.show_message') as show:
            family_actions(self.library(directory='DOTFONTS'),native_row,None)
        self.assertIn('Personal library copy available to store',show.call_args.args[0])

    def test_directory_import_export_and_reinstall_retain_originals(self):
        before=digest(self.source)
        result=self.action('import',str(self.source));identity=result['items'][0]['id'];version=result['items'][0]['version']
        self.assertEqual(self.action('import',str(self.source))['status'],'unchanged')
        output=self.home/'export ü'
        self.action('export',identity,'--version',version,'--output',str(output))
        self.assertEqual(digest(output),before)
        self.action('uninstall',identity,'--version',version)
        self.action('import',str(self.source))
        self.assertEqual(digest(self.source),before)
        self.assertTrue(self.library(directory='DOTFONTS').version(identity,version)[1]['available'])


if __name__=='__main__':unittest.main(verbosity=2)
