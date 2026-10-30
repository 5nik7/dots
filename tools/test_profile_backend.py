#!/usr/bin/env python3
"""Registry/profile ownership and generated environments in disposable roots."""
import argparse
import copy
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
ROOT = fixtures.ROOT
from profile_environment import Model
from profile_config import context
from catalog import Catalog
from transactions import Store, digest
from file_platform import state_root
from config_cli import Plan
from native_environment import document


class ProfileBackend(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        self.environ = patch.dict(os.environ,self.env,clear=True)
        self.environ.start(); self.addCleanup(self.environ.stop)
        self.registry = self.root/'.dots/files.json'
        self.write(self.registry, dict(schema=2,resources=[dict(id='dots:app',platforms=self.resource['platforms'])]))
        sources=self.root/'.dots/sources.json';data=json.loads(sources.read_text());data['schema']=2;self.write(sources,data)
        for path in self.root.glob('profiles/*/profile.json'):
            data=json.loads(path.read_text());data['files']['dots']=[{k:v for k,v in self.resource.items() if k!='platforms'}]
            self.write(path,data)
        self.write(self.root/'profiles/windows/profile.json',dict(json.loads((self.root/'profiles/windows/profile.json').read_text()),alias='WINDOTS'))

    def write(self,path,data): path.write_text(json.dumps(data))

    def config(self,*args,**kwargs): return fixtures.ProfileConfig.run_config(self,*args,**kwargs)

    def files(self,*args,code=0):
        result=subprocess.run([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'files',*args],env=self.env,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return result

    def undo(self,identity):
        store=Store(state_root());ops,guards,catalogs=store.inverse(identity)
        return store.apply('undo',ops,guards,retain=True,catalogs=catalogs)

    def test_join_and_registered_without_mapping(self):
        self.assertEqual(Catalog(self.root,self.platform).records()[0]['id'],'dots:app')
        data=json.loads(self.path.read_text());data['files']['dots']=[];self.write(self.path,data)
        self.assertEqual(Catalog(self.root,self.platform).records(),[])
        self.assertIn('needs a mapping',self.files('show','dots:app',code=1).stderr)
        self.registry.unlink()
        with self.assertRaisesRegex(ValueError,'registry is required'): Catalog(self.root,self.platform)

    def test_strict_registry_and_mapping_contract(self):
        original=self.registry.read_bytes()
        for entry in [dict(id='missing:app',platforms=['linux']),dict(id='dots:app',platforms=[]),dict(id='dots:app',platforms=['linux'],source='x')]:
            self.write(self.registry,dict(schema=2,resources=[entry]))
            with self.assertRaises(ValueError): Catalog(self.root,self.platform).records()
        self.registry.write_bytes(original)
        data=json.loads(self.path.read_text());data['files']['dots'][0]['platforms']=['linux'];self.write(self.path,data)
        with self.assertRaisesRegex(ValueError,'platforms belong'): Catalog(self.root,self.platform).records()

    def test_track_journals_registry_and_profile_and_undo(self):
        (self.root/'config/new').write_text('new')
        before={p:p.read_bytes() for p in (self.registry,self.path)}
        result=json.loads(self.files('track','config/new','--repo','dots','--id','new','--app','app','--category','config','--target','${CONFIG}/new','--json').stdout)
        identity=result['resources'][0]['transaction']
        journal=Store(state_root()).load(identity)
        self.assertEqual({op['path'] for op in journal['operations']},{str(p) for p in before})
        self.assertNotIn('platforms',json.loads(self.path.read_text())['files']['dots'][-1])
        again=json.loads(self.files('track','config/new','--repo','dots','--id','new','--app','app','--category','config','--target','${CONFIG}/new','--json').stdout)
        self.assertNotIn('transaction',again['resources'][0])
        self.undo(identity)
        for path,value in before.items(): self.assertEqual(json.loads(path.read_bytes()),json.loads(value))

    @unittest.skipIf(os.name=='nt','adoption is a POSIX workflow')
    def test_adopt_remove_and_undo_keep_registry_identity(self):
        self.write(self.root/'.dots/file-locations.json',dict(schema=1,repository='dots',locations=[
            dict(id='config',kind='root',target='${CONFIG}',source='config',platforms=self.resource['platforms'])]))
        target=Path(self.env['XDG_CONFIG_HOME'])/'example ü/settings';target.parent.mkdir(parents=True)
        target.write_text('application configuration\n')
        result=json.loads(self.files('add',str(target),'--yes','--json').stdout)
        self.assertTrue(target.is_symlink())
        row=next(row for row in Catalog(self.root,self.platform).records() if row['target']==str(target))
        self.assertIn(row['id'],{r['id'] for r in json.loads(self.registry.read_text())['resources']})
        removed=json.loads(self.files('remove',row['id'],'--yes','--json').stdout)
        self.assertFalse(target.is_symlink());self.assertEqual(target.read_text(),'application configuration\n')
        self.assertIn(row['id'],{r['id'] for r in json.loads(self.registry.read_text())['resources']})
        self.undo(removed['id']);self.assertTrue(target.is_symlink())
        self.undo(result['id']);self.assertFalse(target.is_symlink())

    def test_mapping_platform_edits_base_profile_and_registry_eligibility(self):
        before=self.path.read_bytes()
        result=json.loads(self.files('edit','dots:app','--platform','windows','--target','${APPDATA}/moved','--yes','--json').stdout)
        windows=json.loads((self.root/'profiles/windows/profile.json').read_text())['files']['dots'][0]
        self.assertEqual(windows['target'],'${APPDATA}/moved');self.assertNotIn('targets',windows)
        if self.platform!='windows': self.assertEqual(self.path.read_bytes(),before)
        self.undo(result['transaction'])
        self.files('edit','dots:app','--platforms','linux','wsl','--yes','--json')
        self.assertEqual(json.loads(self.registry.read_text())['resources'][0]['platforms'],['linux','wsl'])

    def test_new_profile_mapping_preserves_existing_registry_eligibility(self):
        self.write(self.registry,dict(schema=2,resources=[dict(id='dots:app',platforms=['linux'])]))
        data=json.loads(self.path.read_text());data['files']['dots']=[];self.write(self.path,data)
        before=self.registry.read_bytes()
        self.files('track','config/app','--repo','dots','--id','app','--app','app','--category','config','--target','${CONFIG}/app','--json')
        self.assertEqual(self.registry.read_bytes(),before)
        self.write(self.path,data)
        self.files('edit','--new','--repo','dots','--id','app','--source','config/app','--app','app','--category','config','--target','${CONFIG}/app','--yes','--json')
        self.assertEqual(self.registry.read_bytes(),before)

    def test_alias_cli_popup_reset_collisions_and_guard(self):
        from config_menu import Inventory, Draft, details
        from resources import cells
        shutil.copytree(ROOT/'default',self.root/'default')
        before=self.path.read_bytes()
        self.config('set','profile.alias','MYDOTS','--dry-run');self.assertEqual(self.path.read_bytes(),before)
        inventory=Inventory(self.root,self.platform);row=inventory.find('profile.alias')
        draft=Draft(inventory,row).prepare('MYDOTS')
        self.assertEqual(draft.proposed,'MYDOTS');draft.save()
        self.assertEqual(self.config('get','profile.alias').stdout,'MYDOTS\n')
        for native in (False,True):
            front=[sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete'] if native else [str(self.root/'bin/dots'),'__complete','bash','3','--','dots']
            completed=subprocess.run([*front,'config','get','profile.'],env=self.env,text=True,capture_output=True,timeout=20)
            self.assertEqual(completed.returncode,0,completed.stderr);self.assertIn('profile.alias',completed.stdout)
        self.assertEqual(Model(self.root).scalars['MYDOTSBIN'],str(self.path.parent/'bin'))
        inventory=Inventory(self.root,self.platform)
        for width in (40,80,120):
            self.assertTrue(all(cells(line)<=width for line in details(inventory.find('profile.alias'),width=width).splitlines()))
        for alias in ('HOME','PROFILE','DOTSWINDOWS','WINDOTS','DOT','BASHOPTS','path','bad-name'):
            if self.platform=='windows' and alias=='WINDOTS': continue
            self.config('set','profile.alias',alias,code=1)
        stale=Plan(self.root,context(self.root));stale.edit('profile.alias','MYDOTS2');stale.finish()
        other=self.root/'profiles/linux/profile.json';other.write_text(other.read_text()+'\n')
        with self.assertRaises(ValueError): stale.apply('set')
        inventory=Inventory(self.root,self.platform)
        reset=Draft(inventory,inventory.find('profile.alias')).prepare(reset=True)
        self.assertIsNone(reset.proposed);reset.save()
        self.assertNotIn('MYDOTS',Model(self.root).scalars)

    def test_all_profiles_standard_directories_and_namespace_validation(self):
        m=Model(self.root)
        self.assertEqual(m.scalars['WINDOTSBIN'],str(self.root/'profiles/windows/bin'))
        self.assertEqual(m.maps['profile']['configs'],str(self.path.parent/'config'))
        self.assertFalse((self.path.parent/'fonts').exists());self.assertIn('PROFILEFONTS',m.scalars)
        self.assertEqual(m.scalars['DOTFONTS'],str(self.root/'fonts'))
        self.assertFalse((self.root/'fonts').exists())
        extra=self.path.parent/'extra-dir';extra.mkdir()
        (extra/'nested').mkdir();(self.path.parent/'.hidden').mkdir()
        m=Model(self.root);self.assertIn('PROFILEEXTRA_DIR',m.scalars)
        self.assertNotIn('PROFILENESTED',m.scalars);self.assertNotIn('PROFILE_HIDDEN',m.scalars)
        (self.path.parent/'extra_dir').mkdir()
        with self.assertRaisesRegex(ValueError,'collision'): Model(self.root)

    def test_distro_namespaces_aliases_and_base_profile_selection(self):
        from mappings import MappingPlan, arguments
        from platform_info import detect
        env={k:v for k,v in self.env.items() if k not in ('PREFIX','TERMUX_VERSION','TERMUX__PREFIX','WSL_INTEROP','WSL_DISTRO_NAME')}
        with patch.dict(os.environ,env,clear=True):
            facts=detect()
            if facts['platform']!='linux': self.skipTest('Linux-context fixture requires a POSIX host')
            identity='linux/'+facts['distro']
            child=self.root/'profiles/linux/distros'/facts['distro'];child.mkdir(parents=True)
            self.write(child/'profile.json',dict(schema=1,id=identity))
            parent=self.root/'profiles/linux/profile.json';data=json.loads(parent.read_text());data['alias']='MYLINUX';self.write(parent,data)
            model=Model(self.root)
            self.assertEqual(model.scalars['PROFILE'],str(child))
            self.assertEqual(model.scalars['MYLINUX'],str(parent.parent))
            self.assertEqual(model.maps['linux_'+facts['distro']]['root'],str(child))
            _,args=arguments(['edit','dots:app','--target','${CONFIG}/base','--platform','linux','--yes'])
            base=MappingPlan(selected_platform='linux');base.edit(args);base.finish()
            self.assertIn(str(parent),base.catalogs);self.assertNotIn(str(child/'profile.json'),base.catalogs)
            args.apply=True
            with self.assertRaisesRegex(ValueError,'another platform'): MappingPlan(selected_platform='linux').edit(args)
            args.platform=None;args.apply=False
            leaf=MappingPlan();leaf.edit(args);leaf.finish()
            self.assertIn(str(child/'profile.json'),leaf.catalogs)

    def test_application_templates_and_generated_cleanup_document(self):
        self.config('set','environment.APP_CONFIG','${PROFILECONFIGS}/app')
        self.config('set','environment.PROFILEBIN','bad',code=1)
        self.config('set','environment.DOTFONTS','bad',code=1)
        self.config('set','profile.alias','MYDOTS')
        old=document(self.root,self.env)
        self.assertEqual(old['exports']['APP_CONFIG'],str(self.path.parent/'config/app'))
        self.assertEqual(old['exports']['DOTFONTS'],str(self.root/'fonts'))
        inherited=dict(self.env,**old['exports'])
        self.config('unset','profile.alias')
        new=document(self.root,inherited)
        self.assertIn('MYDOTSBIN',new['unset']);self.assertIn('PROFILEBIN',new['exports'])
        inherited['DOTS_GENERATED_PATHS']=json.dumps({'HOME':inherited['HOME'],'PATH':inherited['PATH']})
        self.assertEqual(document(self.root,inherited)['unset'],[])

    def test_native_generated_maps_reload_and_literals(self):
        self.config('set','profile.alias','MYDOTS');first=Model(self.root)
        self.config('unset','profile.alias');second=Model(self.root)
        for shell,flags,check in [('bash',['--noprofile','--norc'], 'test "${profile[bin]}" = "$PROFILEBIN" && test "${windots[configs]}" = "$WINDOTSCONFIGS" && test -z "${MYDOTSBIN-}"'),
                                  ('zsh',['-df'],'[[ $profile[bin] == $PROFILEBIN && $windots[configs] == $WINDOTSCONFIGS && -z ${MYDOTSBIN-} ]]'),
                                  ('fish',['--no-config'],'test "$profile_bin" = "$PROFILEBIN"; and test "$windots_configs" = "$WINDOTSCONFIGS"; and not set -q MYDOTSBIN')]:
            if not shutil.which(shell): continue
            result=subprocess.run([shell,*flags,'-c',first.shell(shell)+second.shell(shell)+check],env=self.env,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,shell+': '+result.stderr)
        powershell=second.shell('powershell')
        self.assertIn('$global:DotsProfile = @{',powershell)
        self.assertNotIn('$global:profile =',powershell)
        self.assertIn('$env:PROFILE =',powershell)
        self.assertIn('$env:DOTFONTS =',powershell)

    def test_shared_fonts_checkout_switch_exports_all_native_maps(self):
        first=Model(self.root)
        other=self.root/'other checkout ü'
        shutil.copytree(self.root/'profiles',other/'profiles')
        second=Model(other)
        for shell,flags in [('bash',['--noprofile','--norc']),('zsh',['-df']),('fish',['--no-config'])]:
            if not shutil.which(shell):continue
            script=first.shell(shell)+second.shell(shell)+'test "$DOTFONTS" = '+shlex.quote(str(other/'fonts'))
            result=subprocess.run([shell,*flags,'-c',script],env=self.env,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,shell+': '+result.stderr)
        self.assertEqual(second.scalars['DOTFONTS'],str(other/'fonts'))
        self.assertFalse((other/'fonts').exists())

    def test_combined_write_rollback_and_post_apply_drift(self):
        from mappings import MappingPlan, arguments
        import transactions
        (self.root/'config/new').write_text('source')
        _,args=arguments(['edit','--new','--repo','dots','--id','new','--source','config/new',
                          '--target','${CONFIG}/new','--app','app','--category','config','--yes'])
        plan=MappingPlan();plan.edit(args);plan.finish()
        before={p:digest(p) for p in (self.registry,self.path)}
        rename=transactions.os.rename
        injected = False
        def fail_second(source,destination):
            nonlocal injected
            if not injected and Path(destination)==self.path and '.dots-new-' in str(source):
                injected = True
                raise OSError('injected second replacement failure')
            return rename(source,destination)
        with patch.object(transactions.os,'rename',side_effect=fail_second), self.assertRaises(OSError): plan.apply('edit')
        for path,value in before.items(): self.assertEqual(digest(path),value)
        self.assertEqual(Store(state_root()).records()[-1]['status'],'rolled-back')
        plan=MappingPlan();plan.edit(args);plan.finish();result=plan.apply('edit')
        self.registry.write_text(self.registry.read_text()+'\n')
        with self.assertRaises(ValueError): Store(state_root()).inverse(result['id'])

    def test_inactive_profile_cache_invalidation_and_failed_reload(self):
        from debug.fixtures import fixture
        for shell in ('bash','zsh'):
            if not shutil.which(shell): continue
            with fixture(ROOT) as (root,env,base):
                path=root/'profiles/windows/profile.json'
                data=json.loads(path.read_text());data['alias']='MYWIN';self.write(path,data)
                changed=dict(data,alias='OTHERWIN');invalid=dict(data,alias='HOME')
                source='source "$DOTS/lib/dots/shell/init.'+shell+'"'
                script=source+' || exit 10\n'
                script+='test "$DOTFONTS" = "$DOTS/fonts" || exit 16\n'
                script+='test "$MYWINBIN" = '+shlex.quote(str(path.parent/'bin'))+' || exit 11\n'
                script+='printf %s '+shlex.quote(json.dumps(changed))+' > '+shlex.quote(str(path))+'\n'
                script+='mkdir '+shlex.quote(str(path.parent/'extra'))+'\n'
                script+=source+' || exit 12\n'
                script+='test -z "${MYWINBIN-}" && test "$OTHERWINEXTRA" = '+shlex.quote(str(path.parent/'extra'))+' || exit 13\n'
                script+='printf %s '+shlex.quote(json.dumps(invalid))+' > '+shlex.quote(str(path))+'\n'
                script+=source+' && exit 14\n'
                script+='test "$OTHERWINEXTRA" = '+shlex.quote(str(path.parent/'extra'))+' || exit 15\n'
                result=subprocess.run([shell,'-c',script],env=env,text=True,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,shell+': '+result.stderr)


if __name__=='__main__': unittest.main()
