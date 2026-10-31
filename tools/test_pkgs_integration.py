#!/usr/bin/env python3
"""Pkgs config/menu/setup integration in disposable Dots checkouts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_bundled_apps as bundled_fixture
ROOT = bundled_fixture.ROOT
sys.path.insert(0,str(ROOT/'lib/dots'))
sys.path.insert(0,str(ROOT/'plugins/pkgs'))
from pkgs_lib import manifests  # Keep fixture imports bound to the durable source tree.


class PackageIntegration(unittest.TestCase):
    setUp = bundled_fixture.BundledApps.setUp
    write = bundled_fixture.BundledApps.write
    receipt = bundled_fixture.BundledApps.receipt
    call = bundled_fixture.BundledApps.call
    surfaces = bundled_fixture.BundledApps.surfaces

    def cli(self, *args):
        return json.loads(bundled_fixture.BundledApps.cli(self, *args).stdout)

    def document(self, packages=()):
        path=self.home/'-packages ü.json'
        path.write_text(json.dumps({'schema':1,'groups':[{'manager':'npm','scope':'global','packages':[{'name':p} for p in packages]}]}))
        return path

    def fake_npm(self):
        path=self.repo/'bin/npm'
        db=self.home/'npm.json';db.write_text('{}')
        self.env.update(TEST_DB=str(db),TEST_CONFIG=str(self.target))
        path.write_text('#!'+sys.executable+'\n'+'''import os,json,sys
from pathlib import Path
p=Path(os.environ['TEST_DB']);data=json.loads(p.read_text());a=sys.argv[1:]
if a[0]=='ls':print(json.dumps({'dependencies':{k:{'version':v} for k,v in data.items()}}))
elif a[0]=='install':
    if Path(os.environ['TEST_CONFIG']).exists():raise SystemExit('configuration applied before packages')
    data.update({n:'1' for n in a[a.index('--')+1:]});p.write_text(json.dumps(data))
    if os.environ.get('TEST_DRIFT'):
        target=Path(os.environ['TEST_CONFIG']);target.parent.mkdir(parents=True,exist_ok=True);target.write_text('changed during packages')
else:raise SystemExit(9)
''');path.chmod(0o755)
        return db

    def config_fixture(self):
        shutil.copytree(ROOT/'default',self.repo/'default',symlinks=True)
        for name in ('termux','linux','wsl','windows'):
            path=self.repo/'profiles'/name;path.mkdir(parents=True)
            (path/'profile.json').write_text(json.dumps({'schema':1,'id':name,'settings':{},'files':{}}))

    def test_manifest_surfaces_and_static_completion(self):
        path=self.document(['hello'])
        outputs=[self.call(argv)[0] for argv in self.surfaces('pkgs',['manifest',str(path),'--json'])]
        self.assertTrue(all(o==outputs[0] for o in outputs))
        for words,expected in [(['pkgs','--manager','g'],'go'),(['pkgs','res'],'restore'),
                               (['pkgs','export','--up'],'--update'),(['git','publish','--up'],'--update-packages'),
                               (['pkgs','u'],'upls'),(['pkgs','up','--l'],'--list'),(['pkgs','upgrade','l'],'ls')]:
            data=self.call([sys.executable,'-B',self.repo/'lib/dots/cli.py','__complete',*words])[0]
            self.assertIn(expected.encode(),data)
            if os.name!='nt':
                self.assertIn(expected.encode(),self.call([self.repo/'bin/dots','__complete','bash',str(len(words)),'--','dots',*words])[0])

    @unittest.skipIf(os.name=='nt','POSIX npm executable fixture; native WinGet has separate fixtures')
    def test_setup_packages_precede_configuration_and_repeat_is_noop(self):
        db=self.fake_npm();path=self.document(['hello'])
        before=self.cli('install','--packages',str(path),'--dry-run','--json')
        self.assertEqual(before['packages']['status'],'preview')
        self.assertEqual(db.read_text(),'{}');self.assertFalse(self.target.exists())
        result=self.cli('install','--packages',str(path),'--yes','--json')
        self.assertEqual(result['packages']['status'],'complete')
        self.assertEqual(json.loads(db.read_text()),{'hello':'1'});self.assertTrue(self.target.is_symlink())
        again=self.cli('install','--packages',str(path),'--yes','--json')
        self.assertEqual(again['packages']['groups'][0]['status'],'unchanged')

    @unittest.skipIf(os.name=='nt','POSIX npm executable fixture; native WinGet has separate fixtures')
    def test_missing_prerequisite_does_not_apply_configuration(self):
        path=self.document(['hello']);self.env['PATH']=''
        result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/install.py'),'install','--packages',str(path),'--yes','--json'],env=self.env,text=True,capture_output=True)
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertEqual(json.loads(result.stdout)['packages']['status'],'incomplete')
        self.assertFalse(self.target.exists())

    def test_configuration_drift_preserves_completed_packages(self):
        db=self.fake_npm();path=self.document(['hello']);self.env['TEST_DRIFT']='1'
        result=bundled_fixture.BundledApps.cli(self,'install','--packages',str(path),'--yes','--json',ok=False)
        self.assertEqual(json.loads(db.read_text()),{'hello':'1'})
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(self.target.read_text(),'changed during packages')
        self.assertIn('changed',result.stderr.lower())

    @unittest.skipIf(os.name=='nt','POSIX scripts; PowerShell adapter is checked by installation suites')
    def test_setup_entrypoint_options(self):
        self.fake_npm();path=self.document(['hello'])
        commands=[[shutil.which('bash'),str(self.repo/'install.sh')],
                  [shutil.which('bash'),str(self.repo/'bin/dots'),'init','--setup'],
                  [sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),'files','install']]
        for command in commands:
            result=self.call([*command,'--packages',str(path),'--dry-run','--json'])[0]
            self.assertEqual(json.loads(result)['packages']['status'],'preview')
        self.assertFalse(self.target.exists())

    def test_source_update_reexec_preserves_manifest(self):
        import install
        path=self.document()
        with patch.dict(os.environ,self.env,clear=True),patch.object(sys,'argv',['install','install','--update','--yes','--packages',str(path)]), \
             patch.object(install,'source_plan',return_value=[{'status':'update'}]),patch.object(install,'display'), \
             patch.object(install,'update_sources') as update,patch.object(install.os,'execv',side_effect=SystemExit) as reexec:
            with self.assertRaises(SystemExit):install.main()
        update.assert_called_once()
        argv=reexec.call_args.args[1]
        self.assertEqual(argv[argv.index('--packages')+1],str(path.absolute()))

    def test_config_cli_and_popup_share_native_file(self):
        self.config_fixture()
        route=[sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),'config']
        result=json.loads(self.call([*route,'set','apps.pkgs.output','styled','--json'])[0])
        self.assertIn('transaction',result)
        self.assertEqual(self.call([*route,'get','apps.pkgs.output'])[0],b'styled\n')
        data=json.loads(self.call([*route,'explain','apps.pkgs.output','--json'])[0])
        self.assertEqual(data['constraints']['choices'],['auto','styled','raw'])
        with patch.dict(os.environ,self.env,clear=True):
            from config_menu import Inventory,Draft
            from profile_config import context
            inventory=Inventory(self.repo,context(self.repo)['current'])
            row=inventory.find('apps.pkgs.output');self.assertEqual(row.kind,'pkgs')
            Draft(inventory,row).prepare('raw').save()
        self.assertEqual(self.call([*route,'get','apps.pkgs.output'])[0],b'raw\n')

    def test_menu_requires_successful_review_and_run_choice(self):
        import menu_cli
        self.config_fixture()
        filename=str(self.document())
        for name in ('upgrade','export','restore','update-manifest'):
            action=next(a for a in menu_cli.FAMILIES['pkgs'] if a.id==name)
            for reviewed,choice,expected in [(True,'cancel',False),(False,'apply',False),(True,'apply',True)]:
                with patch.dict(os.environ,self.env,clear=True),patch('menu_input.prompt',return_value=filename), \
                     patch.object(menu_cli,'review_output',return_value=SimpleNamespace(code=0,reviewed=reviewed)), \
                     patch.object(menu_cli,'choose',return_value=SimpleNamespace(id=choice)), \
                     patch.object(menu_cli,'run_action',return_value=0) as run:
                    menu_cli.invoke(self.repo,action,None)
                    if expected:
                        self.assertIn('export' if name=='update-manifest' else name,run.call_args.args[0]);self.assertIn('--yes',run.call_args.args[0])
                        if name=='update-manifest':self.assertIn('--update',run.call_args.args[0])
                        if name!='upgrade':self.assertIn(filename,run.call_args.args[0])
                    else:run.assert_not_called()

    def test_package_prompt_escape_returns_to_same_menu_and_profile_default(self):
        import menu_cli
        from interaction import SelectionEnded,SelectionEvent
        self.config_fixture()
        for event in (SelectionEvent('back'),SelectionEnded(130)):
            calls=[]
            def choose(menu,**kwargs):
                calls.append((menu.id,kwargs['query']))
                if len(calls)==1:
                    kwargs['navigation']['query']='export'
                    return next(e for e in menu.entries if e.id=='export')
                raise SelectionEvent('back')
            with patch.dict(os.environ,self.env,clear=True),patch.object(menu_cli,'choose',side_effect=choose), \
                 patch('menu_input.prompt',side_effect=event) as prompt,patch.object(menu_cli,'review_output') as preview, \
                 patch.object(menu_cli,'run_action') as run:
                self.assertEqual(menu_cli.main(['pkgs','--browse']),130)
                expected=manifests.default_path(self.repo)
            self.assertEqual(prompt.call_args.args[0],str(expected))
            self.assertEqual(calls,[('dots:pkgs',''),('dots:pkgs','export')])
            preview.assert_not_called();run.assert_not_called()
            self.assertFalse(expected.exists())

    def test_windows_backend_boundary(self):
        from package_setup import Stage
        path=self.document()
        with patch.dict(os.environ,self.env,clear=True),patch('pkgs_lib.manifests.platform',return_value='windows'):
            stage=Stage(self.repo,path)
            self.assertEqual(stage.document_preview()['groups'][0]['status'],'skipped')
        import menu_cli
        rows={e.id:e for e in menu_cli.launcher(self.repo,family='pkgs',windows=True).entries}
        self.assertTrue(rows['manifest'].available);self.assertTrue(rows['configuration'].available)
        self.assertFalse(rows['restore'].available);self.assertFalse(rows['upgrade'].available)
        self.assertFalse(rows['upgradable'].available);self.assertFalse(rows['cleanup'].available)
        with patch('menu_cli.shutil.which',return_value='fixture-winget.exe'):
            rows={e.id:e for e in menu_cli.launcher(self.repo,family='pkgs',windows=True).entries}
        for name in ('restore','upgrade','upgradable','cleanup'):self.assertTrue(rows[name].available)

    def test_update_list_alias_surfaces_and_menu_routes(self):
        fake=self.repo/'bin/npm'
        fake.write_text('#!'+sys.executable+'\n'+'''import json,sys
if sys.argv[1]=='ls':print('{"dependencies":{"hello":{"version":"1.0"}}}')
elif sys.argv[1]=='outdated':print('{"hello":{"current":"1.0","wanted":"2.0"}}');sys.exit(1)
else:sys.exit(99)
''');fake.chmod(0o755)
        outputs=[]
        for alias in (['upls'],['upgrade','ls'],['upgrade','--list']):
            for command in self.surfaces('pkgs',[*alias,'--manager','npm','--global','--json']):
                outputs.append(self.call(command)[0])
        self.assertTrue(all(value==outputs[0] for value in outputs))
        self.assertEqual(json.loads(outputs[0])['groups'][0]['packages'][0]['candidate'],'2.0')
        import menu_cli
        actions={a.id:a for a in menu_cli.FAMILIES['pkgs']}
        self.assertEqual(actions['upgradable'].route,('pkgs','upgrade'))
        self.assertEqual(actions['upgradable'].options,('--list',))
        self.assertEqual(actions['cleanup'].kind,'terminal')


if __name__=='__main__':unittest.main()
