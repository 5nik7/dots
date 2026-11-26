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

    @unittest.skipIf(os.name=='nt','Termux pkg fixture; Windows retains its native managers')
    def test_termux_bulk_upgrade_aliases_and_mirror_output_on_all_surfaces(self):
        calls = self.home/'pkg-calls.jsonl'
        self.env.update(TERMUX_VERSION='fixture', TERMUX_APP_PACKAGE_MANAGER='apt',
                        PREFIX=str(self.home/'prefix'), TEST_PKG_CALLS=str(calls),
                        DOTS_MENU_CAPTURE='1', TERMUX_PKG_NO_MIRROR_SELECT='')
        config = Path(self.env['XDG_CONFIG_HOME'])/'pkgs/config.json'
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({'upgrade': {'managers': ['apt']}}))
        script = '#!'+sys.executable+'\n'+'''import json,os,sys
from pathlib import Path
if Path(sys.argv[0]).name=='dpkg-query': pass
elif Path(sys.argv[0]).name=='pkg':
    args=sys.argv[1:]
    assert args==['--check-mirror','upgrade','--fix-missing','-y'], args
    with open(os.environ['TEST_PKG_CALLS'],'a') as f: f.write(json.dumps(args)+'\\n')
    print('Testing the available mirrors:')
    print('[*] (1) https://fixture.invalid: ok')
    print('Picking mirror: (0) /fixture/mirror')
    print('Hit:1 https://fixture.invalid stable InRelease')
    print('All packages are up to date.')
else: raise SystemExit('unexpected manager invocation')
'''
        for name in ('pkg','apt','apt-cache','dpkg-query'):
            path=self.repo/'bin'/name;path.write_text(script);path.chmod(0o755)
        for alias in ('up','upgrade'):
            results = [self.call(argv) for argv in self.surfaces('pkgs',[alias,'--dry-run'])]
            self.assertTrue(all(result == results[0] for result in results))
            self.assertIn(b'pkg --check-mirror upgrade --fix-missing -y', results[0][0])
        self.assertFalse(calls.exists())
        for width in (40,80,120):
            self.env['COLUMNS']=str(width)
            for alias in ('up','upgrade'):
                results = [self.call(argv) for argv in self.surfaces('pkgs',[alias])]
                self.assertTrue(all(result == results[0] for result in results))
                out,err,_=results[0]
                self.assertIn(b'complete',out)
                self.assertNotIn(b'fixture.invalid',out+err)
                self.assertNotIn(b'Picking mirror',out+err)
        before = len(calls.read_text().splitlines())
        self.assertEqual(before,18)
        for mode in ('raw','redirect'):
            if mode=='redirect': self.env.pop('DOTS_MENU_CAPTURE')
            results = [self.call(argv) for argv in self.surfaces('pkgs',['up',*(['--raw'] if mode=='raw' else [])])]
            self.assertTrue(all(result == results[0] for result in results))
            self.assertIn(b'[*] (1) https://fixture.invalid: ok',results[0][0])

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

    @unittest.skipIf(os.name=='nt','Termux uv fixture; native Windows keeps its existing build policy')
    def test_termux_uv_wheel_policy_on_all_surfaces(self):
        calls=self.home/'uv-calls.jsonl'
        self.env={k:v for k,v in self.env.items() if not k.upper().startswith('UV_')}
        self.env.update(TERMUX_VERSION='fixture',PREFIX=str(self.home/'prefix'),
                        TEST_UV_CALLS=str(calls),DOTS_MENU_CAPTURE='1')
        config=Path(self.env['XDG_CONFIG_HOME'])/'pkgs/config.json'
        config.parent.mkdir(parents=True,exist_ok=True)
        config.write_text(json.dumps({'upgrade':{'managers':['uv-tool']}}))
        hardlink_notice = (
            'warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.\n'
            '         If the cache and target directories are on different filesystems, hardlinking may not be supported.\n'
            '         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.'
        )
        self.env['TEST_UV_NOTICE'] = hardlink_notice
        fake=self.repo/'bin/uv'
        fake.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
a=sys.argv[1:]
if a==['tool','list']: print('typer v0.29.2\\n- typer')
elif a[:2]==['tool','upgrade']:
    with open(os.environ['TEST_UV_CALLS'],'a') as f:f.write(json.dumps(a)+'\\n')
    print(os.environ['TEST_UV_NOTICE'],file=sys.stderr)
    if os.environ.get('TEST_UV_FAIL'):
        print('error: Failed to upgrade typer',file=sys.stderr);sys.exit(1)
    print('No changes')
else: raise SystemExit('unexpected uv invocation')
''');fake.chmod(0o755)
        for alias in ('up','upgrade'):
            for argv in self.surfaces('pkgs',[alias,'--dry-run']):
                out,_,_=self.call(argv)
                self.assertIn(b'uv tool upgrade typer --no-build',out)
        self.assertFalse(calls.exists())
        for width in (40,80,120):
            self.env['COLUMNS']=str(width)
            results=[self.call(argv) for argv in self.surfaces('pkgs',['up'])]
            self.assertTrue(all(result==results[0] for result in results))
            self.assertIn(b'complete',results[0][0])
            self.assertIn(b'none',results[0][0])
            self.assertEqual(results[0][1],b'')
        self.assertTrue(all(json.loads(line)==['tool','upgrade','typer','--no-build']
                            for line in calls.read_text().splitlines()))
        self.env['TEST_UV_FAIL']='1'
        for argv in self.surfaces('pkgs',['up','--manager','uv-tool']):
            out,err,_=self.call(argv,code=1)
            self.assertIn(b'failed',out)
            self.assertIn(b'Failed to upgrade typer',err)
            self.assertNotIn(b'hardlink',err)
        self.env.pop('TEST_UV_FAIL')
        for mode in ('raw','redirect'):
            if mode=='redirect': self.env.pop('DOTS_MENU_CAPTURE')
            for argv in self.surfaces('pkgs',['up',*(['--raw'] if mode=='raw' else [])]):
                out,err,_=self.call(argv)
                self.assertIn(b'No changes',out)
                self.assertIn(hardlink_notice.encode()+b'\n',err)
        for argv in self.surfaces('pkgs',['up','--manager','uv-tool','typer']): self.call(argv)
        self.assertEqual(json.loads(calls.read_text().splitlines()[-1]),['tool','upgrade','typer'])

    @unittest.skipIf(os.name=='nt','POSIX npm fixture; WinGet uses package-core fixtures')
    def test_compact_install_alias_on_all_entry_points(self):
        db = self.fake_npm()
        self.env['DOTS_MENU_CAPTURE'] = '1'
        results = [self.call(argv) for argv in self.surfaces('pkgs', ['in','--manager','npm','--global','hello'])]
        self.assertTrue(all(result == results[0] for result in results))
        out, err, _ = results[0]
        self.assertIn(b'Install packages', out)
        self.assertEqual(out.count(b'complete'), 1)
        self.assertIn(b'Installed', out)
        self.assertIn(b'hello', out)
        self.assertNotIn(b'Command', out)
        self.assertNotIn(b'npm install', out)
        self.assertEqual(json.loads(db.read_text()), {'hello':'1'})

    @unittest.skipIf(os.name=='nt','POSIX npm fixture; WinGet uses package-core fixtures')
    def test_compact_remove_alias_on_all_entry_points(self):
        db = self.fake_npm()
        fake = self.repo/'bin/npm'
        fake.write_text(fake.read_text().replace("else:raise SystemExit(9)", """elif a[0]=='uninstall':
    for name in a[a.index('--')+1:]:data.pop(name,None)
    p.write_text(json.dumps(data));print('Removed packages')
else:raise SystemExit(9)"""))
        self.env['DOTS_MENU_CAPTURE'] = '1'
        results = []
        for argv in self.surfaces('pkgs', ['remove','--manager','npm','--global','hello','--yes']):
            db.write_text('{"hello":"1"}')
            results.append(self.call(argv))
            self.assertEqual(json.loads(db.read_text()), {})
        self.assertTrue(all(result == results[0] for result in results))
        out, err, _ = results[0]
        self.assertIn(b'Uninstall packages', out)
        self.assertEqual(out.count(b'complete'), 1)
        self.assertIn(b'Removed', out)
        self.assertIn(b'hello', out)
        self.assertNotIn(b'Removed packages', out)
        self.assertNotIn(b'npm uninstall', out)

    @unittest.skipIf(os.name=='nt','POSIX npm fixture; WinGet has separate adapter tests')
    def test_compact_upgrade_names_on_all_entry_points(self):
        db = self.fake_npm()
        self.env['DOTS_MENU_CAPTURE'] = '1'
        results = []
        for argv in self.surfaces('pkgs', ['up','--manager','npm','--global','hello','current']):
            db.write_text('{"hello":"0","current":"1"}')
            results.append(self.call(argv))
        self.assertTrue(all(result == results[0] for result in results))
        out, err, _ = results[0]
        self.assertIn(b'Updated', out)
        names = out.split(b'Updated',1)[1]
        self.assertIn(b'hello', names)
        self.assertNotIn(b'current', names)

    @unittest.skipIf(os.name=='nt','POSIX npm executable fixture; shared planner is platform independent')
    def test_automatic_npm_upgrade_skips_current_on_all_entry_points(self):
        db = self.fake_npm()
        calls = self.home/'npm-calls.jsonl'
        self.env.update(TEST_NPM_CALLS=str(calls), DOTS_MENU_CAPTURE='1')
        fake = self.repo/'bin/npm'
        fake.write_text(fake.read_text().replace("if a[0]=='ls':", """with open(os.environ['TEST_NPM_CALLS'],'a') as f:f.write(json.dumps(a)+'\\n')
if a[0]=='outdated':
    assert a==['outdated','--json','--global','--','hello','current'],a
    if os.environ.get('TEST_QUERY_FAILURE'):raise SystemExit('fixture query failure')
    print(json.dumps({n:{'current':data[n],'wanted':'1'} for n in a[a.index('--')+1:] if data[n]!='1'}))
elif a[0]=='ls':"""))
        config = Path(self.env['XDG_CONFIG_HOME'])/'pkgs/config.json'
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({'upgrade': {'managers': ['npm']}, 'policies': {'npm': {'skip': ['held']}}}))
        for width in (40,80,120):
            self.env['COLUMNS'] = str(width)
            for alias in ('up','upgrade'):
                for argv in self.surfaces('pkgs',[alias]):
                    db.write_text('{"hello":"0","current":"1","held":"0"}');calls.write_text('')
                    preview=self.call([*argv,'--dry-run'])
                    self.assertIn(b'npm install --global -- hello',preview[0])
                    self.assertFalse(any(json.loads(line)[0]=='install' for line in calls.read_text().splitlines()))
                    changed=self.call(argv);current=self.call(argv)
                    self.assertIn(b'Updated',changed[0]);self.assertIn(b'hello',changed[0])
                    self.assertIn(b'unchanged',current[0]);self.assertNotIn(b'Scripts',current[0]+current[1])
                    installs=[json.loads(line) for line in calls.read_text().splitlines() if json.loads(line)[0]=='install']
                    self.assertEqual(installs,[['install','--global','--','hello']])
                    self.assertEqual(json.loads(db.read_text()),{'hello':'1','current':'1','held':'0'})
        for mode in ('raw','redirect','failure'):
            if mode=='redirect':self.env.pop('DOTS_MENU_CAPTURE')
            if mode=='failure':self.env['TEST_QUERY_FAILURE']='1'
            calls.write_text('')
            for argv in self.surfaces('pkgs',['up',*(['--raw'] if mode=='raw' else [])]):
                out,err,_=self.call(argv,1 if mode=='failure' else 0)
                if mode=='failure':self.assertIn(b'fixture query failure',out+err)
                else:self.assertIn(b'No package changes needed',out)
            self.assertFalse(any(json.loads(line)[0]=='install' for line in calls.read_text().splitlines()))

    @unittest.skipIf(os.name=='nt','native Windows pkgs supports WinGet only')
    def test_pip_partial_upgrade_on_all_entry_points(self):
        module=self.home/'fake python';module.mkdir()
        db=self.home/'pip.json'
        (module/'pip.py').write_text('''import json,os,sys
from pathlib import Path
p=Path(os.environ['TEST_PIP_DB']);data=json.loads(p.read_text());a=sys.argv[1:]
if a[0]=='--version':print('pip fixture')
elif a[0]=='list':print(json.dumps([{'name':n,'version':v} for n,v in data.items()]))
elif a[0]=='install':
    name=a[-1]
    if name=='w3lib':print('error: fixture build failed',file=sys.stderr);sys.exit(4)
    print("ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.",file=sys.stderr)
    print('dataclasses-json 0.6.7 requires marshmallow<4,>=3.18, but you have marshmallow 4.4.0 which is incompatible.',file=sys.stderr)
    data[name]='2';p.write_text(json.dumps(data))
else:sys.exit(99)
''')
        self.env.update(PYTHONPATH=str(module),TEST_PIP_DB=str(db),DOTS_MENU_CAPTURE='1')
        results=[]
        for argv in self.surfaces('pkgs',['up','--manager','pip','marshmallow','pyppeteer','w3lib','good']):
            db.write_text('{"marshmallow":"1","pyppeteer":"1","w3lib":"1","good":"1"}')
            results.append(self.call(argv,code=4))
            self.assertEqual(json.loads(db.read_text()),{'marshmallow':'2','pyppeteer':'2','w3lib':'1','good':'2'})
        self.assertTrue(all(result==results[0] for result in results))
        out,err,_=results[0]
        self.assertRegex(out,rb'Updated\s+good, marshmallow, pyppeteer')
        self.assertRegex(out,rb'Failed\s+w3lib \(exit 4\)')
        self.assertIn(b'w3lib: fixture build failed',err)
        self.assertEqual(err.count(b'dependency conflicts;'),1)
        self.assertNotIn(b'does not currently',err)
        self.assertNotIn(b'more diagnostic',err)
        raw=next(self.surfaces('pkgs',['up','--manager','pip','marshmallow','w3lib','good','--raw']))
        out,err,_=self.call(raw,code=4)
        self.assertIn(b"pip's dependency resolver does not currently",err)
        self.assertIn(b'which is incompatible.',err)
        self.assertIn(b'error: fixture build failed',err)
        self.assertNotIn(b'Updated',out)

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

    @unittest.skipIf(os.name=='nt','native Windows pkgs supports WinGet only')
    def test_empty_user_gems_still_update_rubygems_on_all_surfaces(self):
        state=self.home/'rubygems-version';calls=self.home/'gem-calls'
        config=Path(self.env['XDG_CONFIG_HOME'])/'pkgs/config.json';config.parent.mkdir(parents=True,exist_ok=True)
        config.write_text('{"upgrade":{"managers":["gem"]}}')
        self.env.update(TEST_GEM_STATE=str(state),TEST_GEM_CALLS=str(calls),TEST_GEM_HOME=str(self.home/'gems'),DOTS_MENU_CAPTURE='1')
        self.env.update(TERMUX_VERSION='fixture', TEST_GEM_WARNINGS=str(self.home/'gem-warnings'))
        self.env.pop('BUNDLE_GEMFILE', None)
        files = ['MIT.txt', 'bundler.gemspec', *(f'lib/bundler/file_{i}.rb' for i in range(343))]
        warnings = ''.join(f'WARNING:  {name} is not world-readable\n' for name in files)
        warnings += 'WARNING:  See https://guides.rubygems.org/specification-reference/ for help\n'
        Path(self.env['TEST_GEM_WARNINGS']).write_bytes(warnings.encode())
        ruby=self.repo/'bin/ruby'
        ruby.write_text('#!'+sys.executable+'\nimport os,sys\nprint(os.environ["TEST_GEM_HOME"] if "Gem.user_dir" in sys.argv[-1] else "[]")\n');ruby.chmod(0o755)
        gem=self.repo/'bin/gem'
        gem.write_text('#!'+sys.executable+'\n'+'''import os,sys,json
from pathlib import Path
state=Path(os.environ['TEST_GEM_STATE']);args=sys.argv[1:]
with open(os.environ['TEST_GEM_CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
if args==['--version']:print(state.read_text())
elif args==['update','--system','--no-document']:
    sys.stderr.buffer.write(Path(os.environ['TEST_GEM_WARNINGS']).read_bytes())
    sys.stderr.buffer.flush()
    if os.environ.get('TEST_GEM_FAIL'):print('ERROR: distribution protection',file=sys.stderr);sys.exit(23)
    state.write_text('4.0.2');print('RubyGems system software updated')
else:sys.exit(99)
''');gem.chmod(0o755)
        for width in (40, 80, 120):
            self.env['COLUMNS'] = str(width)
            outputs = []
            for argv in self.surfaces('pkgs', ['up']):
                state.write_text('4.0.1')
                calls.write_text('')
                outputs.append(self.call(argv))
                self.assertEqual(state.read_text(), '4.0.2')
                recorded = [json.loads(line) for line in calls.read_text().splitlines()]
                self.assertEqual(recorded.count(['update','--system','--no-document']), 1)
            self.assertTrue(all(output == outputs[0] for output in outputs))
            out, err, _ = outputs[0]
            self.assertRegex(out, rb'Updated\s+RubyGems')
            self.assertEqual(err, b'')
            self.assertNotIn(b'diagnostic lines', out)
        for args in (['up', '--raw'], ['up']):
            if '--raw' not in args:
                self.env.pop('DOTS_MENU_CAPTURE')
            for argv in self.surfaces('pkgs', args):
                _, err, _ = self.call(argv)
                self.assertEqual(err, warnings.encode())
        self.env['DOTS_MENU_CAPTURE'] = '1'
        self.env['TEST_GEM_FAIL']='1'
        out,err,_=self.call(next(self.surfaces('pkgs',['up'])),code=1)
        self.assertIn(b'failed (exit 23)',out);self.assertIn(b'distribution protection',err)
        config.write_text('{"upgrade":{"managers":["gem"],"gem_system":false}}');calls.write_text('')
        self.call(next(self.surfaces('pkgs',['up'])))
        self.assertNotIn('update',calls.read_text())

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
        self.call([*route,'set','apps.pkgs.upgrade.gem_system','false','--json'])
        self.assertEqual(self.call([*route,'get','apps.pkgs.upgrade.gem_system'])[0],b'false\n')
        controls=json.loads(self.call([*route,'explain','apps.pkgs.upgrade.gem_system','--json'])[0])
        self.assertEqual(controls['constraints']['choices'],[True,False])
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
