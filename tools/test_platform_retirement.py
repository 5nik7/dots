#!/usr/bin/env python3
"""Retired environment and file identities, with disposable homes and receipts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots'))
sys.path.insert(0, str(ROOT/'lib/dots/files'))
from debug.fixtures import fixture
from catalog import Catalog
from identities import canonical
from install import Installation
from transactions import Store
import test_installation as fixtures


class EnvironmentRetirement(unittest.TestCase):
    def test_native_shell_reload(self):
        scripts = {
            'bash': (['--noprofile','--norc'], 'source "$DOTS/lib/dots/shell/init.bash"; source "$DOTS/lib/dots/shell/init.bash"; python3 -B "$HOME/report.py"'),
            'zsh': (['-df'], 'source "$DOTS/lib/dots/shell/init.bash"; source "$DOTS/lib/dots/shell/init.bash"; python3 -B "$HOME/report.py"'),
            'fish': (['--no-config'], 'source "$DOTS/lib/dots/shell/init.fish"; source "$DOTS/lib/dots/shell/init.fish"; python3 -B "$HOME/report.py"'),
            'nu': (['-n'], 'source "$DOTS/lib/dots/shell/init.nu"; source "$DOTS/lib/dots/shell/init.nu"; ^python3 -B ($env.HOME | path join report.py)'),
            'pwsh': (['-NoLogo','-NoProfile'], '. "$env:DOTS/lib/dots/shell/init.ps1"; . "$env:DOTS/lib/dots/shell/init.ps1"; python3 -B "$env:HOME/report.py"'),
        }
        for shell,(flags,code) in scripts.items():
            executable = shutil.which(shell)
            if not executable: continue
            with self.subTest(shell=shell), fixture(ROOT) as (root,env,base):
                previous = base/'old checkout ü'
                retired = [root/'ruby/completion', previous/'ruby/completion', Path(env['HOME'])/'dots/ruby/completion']
                kept = [base/'other/ruby/completion', base/'ruby/bin']
                env.update(DOTRUBY='retired', RUBYCOMP='retired', DOTS_PROFILE_CHECKOUT=str(previous),
                           DOTS_ENV_HOOKS='DOTRUBY:old:0:set;RUBYCOMP:old:0:set;KEEP:local:0:set;',
                           DOTS_ENV_ORIGINS='DOTRUBY|old;RUBYCOMP|old;KEEP|local;', KEEP='yes')
                env['PATH'] = os.pathsep.join([str(p)+'/' for p in retired]+list(map(str,kept))+[env['PATH']])
                Path(env['HOME'],'report.py').write_text('import json,os;print(json.dumps(dict(os.environ)))')
                if shell in ('bash','zsh'):
                    code = 'typeset -gA _DOTS_ENV_APPLIED _DOTS_ENV_ORIGINS _DOTS_HOOK_RECORDS; _DOTS_ENV_APPLIED[DOTRUBY]=old; _DOTS_ENV_ORIGINS[RUBYCOMP]=old; _DOTS_HOOK_RECORDS[DOTRUBY]=old; ' + code
                    code = code.replace('python3 -B', '[[ -z ${_DOTS_ENV_APPLIED[DOTRUBY]+set} && -z ${_DOTS_ENV_ORIGINS[RUBYCOMP]+set} && -z ${_DOTS_HOOK_RECORDS[DOTRUBY]+set} ]] || exit 90; python3 -B')
                if shell == 'nu': code=code.replace('"$DOTS/lib/dots/shell/init.nu"', "'"+str(root/'lib/dots/shell/init.nu')+"'")
                result=subprocess.run([executable,*flags,('-Command' if shell=='pwsh' else '-c'),code], env=env, cwd=base, capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stderr,'')
                data=json.loads(result.stdout)
                for key in ('DOTRUBY','RUBYCOMP'): self.assertNotIn(key,data)
                entries=data['PATH'].split(os.pathsep)
                for path in retired: self.assertNotIn(str(path),[p.rstrip('/') for p in entries])
                for path in kept: self.assertIn(str(path),entries)
                for key in ('DOTS_ENV_HOOKS','DOTS_ENV_ORIGINS'):
                    self.assertNotIn('DOTRUBY',data.get(key,'')); self.assertNotIn('RUBYCOMP',data.get(key,''))
                self.assertEqual(data['KEEP'],'yes')

    def test_retired_profile_declarations_and_provenance(self):
        from profiles import definition
        from environment import clean_metadata
        with fixture(ROOT) as (root,env,base):
            for key in ('DOTRUBY','RUBYCOMP'):
                (root/'profiles/termux/profile.json').write_text(json.dumps(dict(schema=1,id='termux',environment={key:'old'})))
                with self.assertRaisesRegex(ValueError,'environment declaration'): definition(root,'termux')
        self.assertEqual(clean_metadata('DOTRUBY|old;KEEP|local;RUBYCOMP|old;'),'KEEP|local;')
        self.assertEqual(clean_metadata('DOTRUBY:old:0:set;KEEP:local:0:set;RUBYCOMP:old:0:set;'),'KEEP:local:0:set;')

    def test_setup_completion_both_controllers(self):
        with fixture(ROOT) as (root,env,base):
            for command in ('dots-files-install','dots-env'):
                shutil.copy2(ROOT/'bin'/command,root/'bin'/command)
            for route in (['files','install'],['init','--setup']):
                words=[*route,'--with-source','']
                commands=[([str(root/'bin/dots'),'__complete','bash',str(len(words)),'--','dots',*words]),
                          ([sys.executable,'-B',str(root/'lib/dots/cli.py'),'__complete',*words])]
                for command in commands:
                    result=subprocess.run(command,env=env,cwd=base,text=True,capture_output=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    candidates={line.split('\t')[1] for line in result.stdout.splitlines() if line.startswith('candidate\t')}
                    self.assertEqual(candidates,{'termux','windows','nvim'})

    def test_environment_completion_excludes_stale_hook_names(self):
        with fixture(ROOT) as (root,env,base):
            shutil.copy2(ROOT/'bin/dots-env',root/'bin/dots-env')
            env.update(DOTRUBY='old',RUBYCOMP='old',DOTS_ENV_HOOKS='DOTRUBY:hook:0:set;RUBYCOMP:hook:0:set;')
            commands=[[str(root/'bin/dots'),'__complete','bash','2','--','dots','env',''],
                      [sys.executable,'-B',str(root/'lib/dots/cli.py'),'__complete','env','']]
            for command in commands:
                result=subprocess.run(command,env=env,cwd=base,text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('DOTS',result.stdout)
                self.assertNotIn('DOTRUBY',result.stdout);self.assertNotIn('RUBYCOMP',result.stdout)

    def test_environment_report_and_native_data(self):
        from native_environment import exports
        with fixture(ROOT) as (root,env,base):
            env.update(DOTRUBY='old',RUBYCOMP='old',DOTS_PROFILE_CHECKOUT=str(base/'previous'),
                       DOTS_ENV_HOOKS='DOTRUBY:hook:0:set;RUBYCOMP:hook:0:set;')
            env['PATH'] += os.pathsep+str(base/'previous/ruby/completion')+'/'
            with patch.dict(os.environ,env,clear=True):
                data=exports(root,env)
                self.assertNotIn(str(base/'previous/ruby/completion'),data['PATH'])
                result=subprocess.run([sys.executable,'-B',str(root/'lib/dots/environment.py'),'--json'],env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            values=json.loads(result.stdout)['values']
            for key in ('DOTRUBY','RUBYCOMP'):
                self.assertNotIn(key,data); self.assertNotIn(key,values)


class FileIdentityRetirement(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.InstallationTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.repo,self.home,self.target=self.f.repo,self.f.home,self.f.target
        self.env=self.f.env
        self.patch=patch.dict(os.environ,self.env,clear=True);self.patch.start();self.addCleanup(self.patch.stop)
        self.owner=self.repo/'profiles/termux';(self.owner/'.dots').mkdir(parents=True)
        (self.owner/'config').mkdir();self.source=self.owner/'config/example';self.source.write_text('managed')
        self.f.write('.dots/files.json',dict(schema=1,repository='dots',resources=[]))
        self.f.write('.dots/sources.json',dict(schema=1,sources=[dict(id='androidots',path='profiles/termux',roots=['config'],platforms=['termux','linux','wsl','windows'])]))
        self.doc=dict(schema=1,repository='androidots',resources=[dict(id='example',source='config/example',target='${CONFIG}/example/settings',strategy='link',app='example',category='config',platforms=['termux','linux','wsl','windows'])])
        (self.owner/'.dots/files.json').write_text(json.dumps(self.doc))

    def legacy_install(self):
        self.target.parent.mkdir(parents=True);self.target.write_text('original baseline')
        self.f.cli('install','--yes')
        path=self.home/'.state/dots/installation.json';data=json.loads(path.read_text())
        data['entries'][str(self.target)]['id']='androidots:example';path.write_text(json.dumps(data))
        return path,path.read_bytes(),data['entries'][str(self.target)].copy()

    def test_readonly_noop_and_uninstall_preserve_legacy_baseline(self):
        path,raw,entry=self.legacy_install()
        install=Installation(self.repo)
        self.assertEqual(install.entries[str(self.target)]['id'],'termux:example')
        self.assertEqual(install.receipt['entries'][str(self.target)]['id'],'androidots:example')
        self.assertEqual(Catalog(self.repo,install.platform).records()[0]['id'],'termux:example')
        self.assertEqual(path.read_bytes(),raw)
        self.assertEqual(json.loads(self.f.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.assertEqual(path.read_bytes(),raw)
        self.f.cli('uninstall','--yes');self.assertEqual(self.target.read_text(),'original baseline')

    def test_stash_undo_preserves_raw_receipt_and_backup(self):
        path,raw,entry=self.legacy_install()
        proc=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/mappings.py'),'stash','termux:example','--yes','--json'],env=self.env,text=True,capture_output=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        after=json.loads(path.read_text())['entries'][str(self.target)]
        self.assertEqual(after['id'],'termux:example')
        for key in ('before','backup','index'): self.assertEqual(after[key],entry[key])
        store=Store(self.home/'.state/dots');ops,guards,catalogs=store.inverse(json.loads(proc.stdout)['transaction']);store.apply('undo',ops,guards,catalogs=catalogs)
        self.assertEqual(json.loads(path.read_text()),json.loads(raw))
        self.assertTrue(self.target.is_symlink())
        self.f.cli('uninstall','--yes');self.assertEqual(self.target.read_text(),'original baseline')

    def test_edit_target_preserves_both_baselines(self):
        path,raw,entry=self.legacy_install()
        target=self.home/'.config/new destination';target.write_text('new baseline')
        result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/mappings.py'),'edit','termux:example','--target',str(target),'--apply','--backup','--yes'],env=self.env,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(target.is_symlink());self.assertFalse(self.target.exists())
        self.f.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'original baseline');self.assertEqual(target.read_text(),'new baseline')

    def test_interrupted_legacy_stash_recovers(self):
        path,raw,entry=self.legacy_install()
        script="""import sys,os
sys.path.insert(0,sys.argv[1])
import mappings,transactions
p=mappings.MappingPlan();p.stash(['termux:example']);p.finish()
original=transactions.os.rename
def crash(a,b):
 original(a,b)
 os._exit(77)
transactions.os.rename=crash
p.apply('stash')
"""
        result=subprocess.run([sys.executable,'-B','-c',script,str(ROOT/'lib/dots/files')],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,77,result.stderr)
        store=Store(self.home/'.state/dots')
        pending=next(r for r in store.records() if r['status']=='applying')
        store.recover(pending['id'])
        self.assertEqual(json.loads(path.read_text()),json.loads(raw))
        self.assertTrue(self.target.is_symlink())
        self.f.cli('uninstall','--yes');self.assertEqual(self.target.read_text(),'original baseline')

    def test_legacy_drift_is_protected(self):
        path,raw,entry=self.legacy_install();self.target.unlink();self.target.write_text('user change')
        self.f.cli('uninstall','--yes',ok=False)
        self.assertEqual(self.target.read_text(),'user change')
        self.assertEqual(json.loads(path.read_text())['entries'][str(self.target)]['backup'],entry['backup'])

    def test_old_cli_inputs_rejected_with_replacements(self):
        cases=[('catalog.py',['show','androidots:example'],'termux:example'),
               ('catalog.py',['list','--repo','windots'],'windows'),
               ('manage.py',['link','androidots:example'],'termux:example'),
               ('mappings.py',['edit','windots:example'],'windows:example'),
               ('install.py',['install','--with-source','androidots'],'termux')]
        for script,args,replacement in cases:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files'/script),*args],env=self.env,text=True,capture_output=True)
            self.assertEqual(result.returncode,2,result.stderr);self.assertIn('use '+replacement,result.stderr);self.assertEqual(result.stdout,'')
        self.assertFalse((self.home/'.state').exists())

    def test_windows_identity_and_replacement_references(self):
        self.assertEqual(canonical('windots:editor'), 'windows:editor')
        self.doc['resources'][0]['replaces']=['windots:example']
        (self.owner/'.dots/files.json').write_text(json.dumps(self.doc))
        reader=Catalog(self.repo,'termux')
        self.assertEqual(reader.manifest(reader.sources[0])['resources'][0]['replaces'],['windows:example'])

    def test_duplicate_legacy_and_current_owners_rejected(self):
        data=json.loads((self.repo/'.dots/sources.json').read_text());data['sources'].append(dict(data['sources'][0],id='termux'))
        self.f.write('.dots/sources.json',data)
        with self.assertRaisesRegex(ValueError,'duplicate'): Catalog(self.repo,'termux')


if __name__=='__main__': unittest.main()
