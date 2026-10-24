#!/usr/bin/env python3
"""Owned-fixture acceptance for profiles, environment, bundles and bootstrap."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib/dots'))
from platform_info import detect
from profiles import resolve, available
from bootstrap import acquire


class Profiles(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='dots-profiles-test-');self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name);self.root=self.home/'checkout space'
        self.root.mkdir()
        self.env={k:v for k,v in os.environ.items() if k in ('PATH','PREFIX','TERMUX_VERSION','TERMUX__PREFIX','SYSTEMROOT','SystemRoot')}
        self.env.update(HOME=str(self.home),DOTS=str(self.root),XDG_CONFIG_HOME=str(self.home/'config'),XDG_STATE_HOME=str(self.home/'state'),XDG_CACHE_HOME=str(self.home/'cache'),XDG_DATA_HOME=str(self.home/'data'),DOTS_INIT_THEME='0',DOTS_INIT_COMPLETION='0',DOTS_TERMUX_AUTOSTART='0')

    def profile(self,name,**fields):
        platform,_,distro=name.partition('/')
        path=self.root/'profiles'/platform
        if distro:path=path/'distros'/distro
        path.mkdir(parents=True,exist_ok=True)
        (path/'profile.json').write_text(json.dumps(dict(schema=1,id=name,**fields)))
        return path

    def public(self):
        for name in ('lib/dots','shells/shared','shells/bash','shells/zsh'):
            shutil.copytree(ROOT/name,self.root/name,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (self.root/'bin/lib').mkdir(parents=True)
        shutil.copy2(ROOT/'bin/lib/common.sh',self.root/'bin/lib/common.sh')
        (self.root/'bin/dots').write_text('# fixture\n')
        for name in ('termux','linux','windows','wsl'):self.profile(name)

    def run_shell(self,shell,code,**overrides):
        return subprocess.run([shell,'-c',code],env=dict(self.env,**overrides),text=True,capture_output=True,timeout=30)

    def test_detection(self):
        osr=self.home/'os-release';osr.write_text('ID=ubuntu\nID_LIKE="debian"\nVERSION_ID="24.04"\n')
        base=dict(env={},system='Linux',release='6.0',machine='arm64',release_file=osr)
        self.assertEqual(detect(**base)['distro'],'ubuntu')
        self.assertEqual(detect(**dict(base,release='microsoft-standard-WSL2'))['platform'],'wsl')
        self.assertEqual(detect(**dict(base,env={'TERMUX_VERSION':'1','PREFIX':'/data/data/com.termux/files/usr'}))['platform'],'termux')
        self.assertEqual(detect(**dict(base,system='Windows',env={'WSL_DISTRO_NAME':'Ubuntu','TERMUX_VERSION':'1','PREFIX':'/usr'}))['platform'],'windows')

    def test_inheritance_and_fallback(self):
        self.profile('linux');self.profile('linux/debian');self.profile('linux/ubuntu',extends=['linux/debian']);self.profile('wsl');self.profile('wsl/ubuntu')
        facts=dict(platform='wsl',distro='ubuntu',family=['debian'])
        self.assertEqual([r['id'] for r in resolve(self.root,facts)['layers']],['linux','linux/debian','linux/ubuntu','wsl','wsl/ubuntu'])
        facts['distro']='mint'
        self.assertEqual([r['id'] for r in resolve(self.root,facts)['layers']],['linux','linux/debian','wsl'])

    def test_cycles_and_escape_refused(self):
        self.profile('linux',extends=['linux/a']);self.profile('linux/a',extends=['linux'])
        with self.assertRaises(ValueError):available(self.root)
        self.profile('linux',path=['../../escape'])
        with self.assertRaises(ValueError):resolve(self.root,dict(platform='linux',distro='unknown',family=[]))

    def test_wsl_catalog_inherits_explicit_linux_replacement(self):
        from files.catalog import Catalog
        linux=self.profile('linux');self.profile('wsl')
        (self.root/'.dots').mkdir()
        (self.root/'config').mkdir();(self.root/'config/app').write_text('universal')
        (linux/'config').mkdir();(linux/'config/app').write_text('linux')
        (linux/'.dots').mkdir()
        (self.root/'.dots/sources.json').write_text(json.dumps(dict(schema=1,sources=[dict(id='dots',path='.',platforms=['linux','wsl'],roots=['config'])])))
        resource=dict(id='app',app='app',category='config',source='config/app',target='${CONFIG}/app',strategy='link',platforms=['linux','wsl'])
        (self.root/'.dots/files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[resource])))
        override=dict(resource,platforms=['linux'],replaces=['dots:app'])
        (linux/'.dots/files.json').write_text(json.dumps(dict(schema=1,repository='profile-linux',resources=[override])))
        with patch.dict(os.environ,self.env,clear=True): rows=Catalog(self.root,'wsl').records()
        universal=next(r for r in rows if r['id']=='dots:app')
        inherited=next(r for r in rows if r['id']=='profile-linux:app')
        self.assertEqual(universal['replaced_by'],'profile-linux:app');self.assertTrue(inherited['applicable'])
        self.assertEqual(inherited['target'],str(self.home/'config/app'))
        self.assertFalse((self.home/'config').exists())

    def test_fish_native_environment_cache(self):
        if not shutil.which('fish'):self.skipTest('Fish unavailable')
        self.public()
        code='source "$DOTS/lib/dots/shell/init.fish"; printf "%s|%s" "$DOTS_PROFILE" "$EDITOR"'
        cold=subprocess.run(['fish','--no-config','-c',code],env=dict(self.env,EDITOR='custom'),text=True,capture_output=True,timeout=30)
        self.assertEqual(cold.returncode,0,cold.stderr)
        commands=self.home/'fish-commands';commands.mkdir()
        shim=commands/'python3';shim.write_text('#!'+shutil.which('sh')+'\nprintf PYTHON_WAS_CALLED >&2\nexit 99\n');shim.chmod(0o700)
        warm=subprocess.run(['fish','--no-config','-c',code],env=dict(self.env,EDITOR='custom',PATH=str(commands)+os.pathsep+self.env['PATH']),text=True,capture_output=True,timeout=30)
        self.assertEqual(warm.returncode,0,warm.stderr);self.assertEqual(warm.stdout,cold.stdout)
        self.assertNotIn('PYTHON_WAS_CALLED',warm.stderr)
        self.assertTrue(cold.stdout.endswith('|custom'))

    def test_native_environment_uses_shell_values_and_removes_old_paths(self):
        from native_environment import exports
        self.public()
        profile = self.root/'profiles/termux'
        (profile/'bin').mkdir()
        env = dict(self.env, TERMUX_VERSION='fixture', PREFIX='/data/data/com.termux/files/usr', EDITOR='shell editor',
                   DOTS_PROFILE_PATHS='/old/profile/bin', PATH='/old/profile/bin:/usr/bin')
        values = exports(self.root, env)
        self.assertEqual(values['EDITOR'], 'shell editor')
        self.assertEqual(values['DOTS_PROFILE'], 'termux')
        self.assertEqual(values['PATH'], str(profile/'bin')+':/usr/bin')
        self.assertEqual(values['DOTS_PROFILE_PATHS'], str(profile/'bin'))

    def test_native_bundles_and_invalidation(self):
        self.public()
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            code='source "$DOTS/lib/dots/shell/init.'+shell+'"; printf "%s|%s\\n" "$EDITOR" "$BAT_CONFIG_PATH"'
            p=self.run_shell(shell,code,EDITOR='custom editor');self.assertEqual(p.returncode,0,p.stderr);self.assertNotIn('preparation unavailable',p.stderr)
            self.assertEqual(p.stdout.strip(),'custom editor|'+str(self.root/'config/bat/bat.conf'))
            p=self.run_shell(shell,code,EDITOR='custom editor');self.assertNotIn('preparation unavailable',p.stderr)
            manifest=list((self.home/'cache/dots/startup').glob(shell+'-*/current'))[0]
            before=manifest.read_text()
            registry=self.root/'lib/dots/shell/environment.json';data=json.loads(registry.read_text());data['defaults']['DOCS']='${HOME}/Changed '+shell;registry.write_text(json.dumps(data))
            p=self.run_shell(shell,code);self.assertNotIn('preparation unavailable',p.stderr)
            self.assertNotEqual(before,manifest.read_text())

    def test_warm_startup_does_not_launch_python(self):
        self.public()
        for shell in ('bash','zsh'):
            if not shutil.which(shell): continue
            code='source "$DOTS/lib/dots/shell/init.'+shell+'"; printf "%s" "$DOTS_PROFILE"'
            cold=self.run_shell(shell,code);self.assertEqual(cold.returncode,0,cold.stderr)
            commands=self.home/('commands-'+shell);commands.mkdir()
            shim=commands/'python3';shim.write_text('#!'+shutil.which('sh')+'\nprintf PYTHON_WAS_CALLED >&2\nexit 99\n');shim.chmod(0o700)
            warm=self.run_shell(shell,code,PATH=str(commands)+os.pathsep+self.env['PATH'])
            self.assertEqual(warm.returncode,0,warm.stderr);self.assertEqual(warm.stdout,cold.stdout)
            self.assertNotIn('PYTHON_WAS_CALLED',warm.stderr)

    def test_failed_prepare_and_concurrent_startup(self):
        self.public()
        code='source "$DOTS/lib/dots/shell/init.bash"; printf "%s" "$DOTS_PROFILE"'
        processes=[subprocess.Popen(['bash','-c',code],env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
        outcomes=[p.communicate(timeout=30) for p in processes]
        self.assertTrue(all(p.returncode==0 for p in processes),outcomes)
        self.assertEqual(outcomes[0][0],outcomes[1][0])
        (self.root/'shells/bash/interactive.bash').write_text('if then invalid fixture\n')
        failed=self.run_shell('bash',code)
        self.assertEqual(failed.returncode,0,failed.stderr)
        self.assertIn('minimal integration',failed.stderr)
        self.assertIn('failed native syntax validation',failed.stderr)

    def test_inherited_profile_paths_are_not_duplicated(self):
        self.public()
        from platform_info import detect
        platform=detect(env=self.env)['platform']
        directory=self.root/'profiles'/platform/'bin';directory.mkdir()
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            code='source "$DOTS/lib/dots/shell/init.'+shell+'"; printf "%s" "$PATH"'
            result=self.run_shell(shell,code,PATH=str(directory)+os.pathsep+self.env['PATH'],DOTS_PROFILE_PATHS=str(directory),DOTS_PROFILE_CHECKOUT=str(self.root))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.split(os.pathsep).count(str(directory)),1)
            self.assertFalse((self.home/'.local/bin').exists())

    def test_private_hook_and_nested_tracking(self):
        self.public();secret=self.home/'private.sh';secret.write_text('export ARBITRARY_PRIVATE_VALUE="hidden value"\n')
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            code='source "$DOTS/lib/dots/shell/init.'+shell+'"; _dots_hook_snapshot; _dots_hook_source "$HOME/private.sh" private 1; _dots_hook_record tools; python3 -B "$DOTS/lib/dots/environment.py" ARBITRARY_PRIVATE_VALUE --json'
            p=self.run_shell(shell,code);self.assertEqual(p.returncode,0,p.stderr);self.assertNotIn('hidden value',p.stdout+p.stderr)
            self.assertTrue(json.loads(p.stdout)['values']['ARBITRARY_PRIVATE_VALUE']['sensitive'])
            for cache in (self.home/'cache').rglob('*'):
                if cache.is_file():self.assertNotIn(b'hidden value',cache.read_bytes())

    def test_profile_reports_redact_credentials(self):
        from profiles import public_report
        data=dict(layers=[dict(environment={'API_KEY':'private literal','PUBLIC_ALIAS':'${PRIVATE_TOKEN}','NORMAL':'literal'})])
        report=public_report(data)
        self.assertNotIn('private literal',json.dumps(report))
        self.assertEqual(report['layers'][0]['environment']['NORMAL'],'literal')
        self.assertEqual(report['layers'][0]['environment']['PUBLIC_ALIAS'],'[redacted]')

    def test_bootstrap_local_and_existing(self):
        source=self.home/'source';source.mkdir()
        for relative in ('bin/dots','bin/dots.ps1','lib/dots/shell/startup.bash'):
            p=source/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# fixture\n')
        env=dict(self.env,GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1')
        for args in (['init','-b','main'],['add','.'],['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture']):
            subprocess.run(['git','-C',str(source),*args],check=True,env=env,capture_output=True)
        destination=self.home/'installed checkout'
        self.assertEqual(acquire(destination,str(source)),destination)
        self.assertEqual(acquire(destination,'https://invalid.invalid/never-fetched'),destination)
        occupied=self.home/'occupied';occupied.mkdir();(occupied/'keep').write_text('keep')
        with self.assertRaises(ValueError):acquire(occupied,str(source))
        self.assertEqual((occupied/'keep').read_text(),'keep')
        with self.assertRaises(ValueError):acquire(self.home/'bad','https://user:secret@example.invalid/repo')


if __name__=='__main__':unittest.main()
