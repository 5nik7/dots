#!/usr/bin/env python3
"""Profile configuration, catalog edits and migration in exclusively owned roots."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
from platform_info import detect
from config_cli import Plan
from profile_config import context, config_path
from files.catalog import Catalog
from transactions import Store


class ProfileConfig(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-profile-config-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / '-checkout space ü'
        self.root.mkdir()
        shutil.copytree(ROOT / 'lib/dots', self.root / 'lib/dots', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.root / 'bin').mkdir()
        for file in [ROOT / 'bin/dots', *ROOT.glob('bin/dots-config*'), *ROOT.glob('bin/dots-files*')]:
            shutil.copy2(file, self.root / 'bin' / file.name)
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH','PREFIX','TERMUX_VERSION','TERMUX__PREFIX','SYSTEMROOT','SystemRoot','LD_PRELOAD')}
        self.env.update(HOME=str(self.home), DOTS=str(self.root), TERM='dumb', DOTS_COLOR='never', DOTS_ICONS='never')
        for kind in ('CONFIG','STATE','CACHE','DATA'): self.env['XDG_'+kind+'_HOME'] = str(self.home / kind.lower())
        self.platform = detect(env=self.env)['platform']
        for name in ('termux','linux','wsl','windows'):
            directory = self.root / 'profiles' / name
            directory.mkdir(parents=True)
            (directory / 'profile.json').write_text(json.dumps(dict(schema=1,id=name,settings={},files={})))
        self.path = self.root / 'profiles' / self.platform / 'profile.json'
        (self.root / '.dots').mkdir()
        (self.root / 'config').mkdir()
        (self.root / 'config/app').write_text('source\n')
        self.resource = dict(id='app',source='config/app',target='${CONFIG}/app',strategy='link',app='app',category='config',platforms=['termux','linux','wsl','windows'])
        (self.root / '.dots/sources.json').write_text(json.dumps(dict(schema=1,sources=[dict(id='dots',path='.',roots=['config'],platforms=self.resource['platforms'])])))
        (self.root / '.dots/files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[self.resource])))
        self.legacy = self.home / 'config/dots'

    def run_config(self, *args, code=0, native=False, **env):
        command = [sys.executable, '-B', str(self.root / 'lib/dots/cli.py'), 'config'] if native else [shutil.which('bash'), str(self.root / 'bin/dots'), 'config']
        result = subprocess.run([*command, *args], env=dict(self.env, **env), text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def plan(self): return Plan(self.root, context(self.root))

    def test_cli_settings_native_and_exact_data(self):
        before = self.path.read_bytes()
        self.run_config('set','DOTS_COLOR','always','--dry-run','--json')
        self.assertEqual(self.path.read_bytes(), before)
        result = json.loads(self.run_config('set','DOTS_COLOR','always','--json').stdout)
        self.assertEqual(self.run_config('get','DOTS_COLOR',DOTS_COLOR='always',DOTS_ICONS='always').stdout, 'always\n')
        self.assertEqual(self.run_config('get','DOTS_COLOR',native=True).stdout, 'always\n')
        with patch.dict(os.environ,self.env,clear=True):
            from environment import settings
            self.assertEqual(settings(self.root)['DOTS_COLOR']['value'], 'never')
            with patch.dict(os.environ, DOTS_COLOR=''):
                self.assertEqual(settings(self.root)['DOTS_COLOR']['source'], 'profile:'+self.platform)
            store = Store(Path(self.env['XDG_STATE_HOME'])/'dots')
            operations, guards, catalogs = store.inverse(result['transaction'])
            store.apply('undo', operations, guards, retain=True, catalogs=catalogs)
        self.assertEqual(json.loads(self.path.read_bytes()), json.loads(before))

    def test_invalid_and_sensitive_values_preserve_manifest(self):
        before = self.path.read_bytes()
        self.run_config('set','DOTS_COLOR','$(touch bad)','--json',code=1)
        result = self.run_config('set','environment.API_KEY','sensitive-literal','--json',code=1)
        self.assertNotIn('sensitive-literal',result.stderr)
        self.assertEqual(self.path.read_bytes(),before)
        self.run_config('set','environment.API_KEY','${EXTERNAL_KEY}')
        self.assertEqual(self.run_config('get','environment.API_KEY').stdout,'[redacted]\n')

    def test_migration_preserves_themes_and_undo(self):
        self.legacy.mkdir(parents=True)
        (self.legacy/'themes').mkdir()
        marker=self.legacy/'themes/keep';marker.write_text('theme')
        (self.legacy/'file-colors.toml').write_text('[type.dir]\nfg="blue"\n')
        (self.legacy/'git.conf').write_text('[dots-git]\nowner=example.test/me\n')
        (self.legacy/'theme-plugins.json').write_text('{"schema":1,"enabled":{}}\n')
        (self.legacy/'config.env').write_text('DOTS_INIT_COLORS=0\n')
        (self.legacy/'files.json').write_text('{"schema":1,"backup":true}\n')
        (self.legacy/'hooks/theme-set.d').mkdir(parents=True)
        (self.legacy/'hooks/theme-set.d/10-custom.sh').write_text('#!/bin/sh\nexit 0\n')
        original={p.relative_to(self.legacy):p.read_bytes() for p in self.legacy.rglob('*') if p.is_file()}
        theme_stat=marker.stat()
        with patch.dict(os.environ,self.env,clear=True):
            plan=self.plan();plan.migrate();plan.finish()
            self.assertFalse((self.home/'state').exists())
            result=plan.apply('migrate')
            self.assertEqual(list(self.legacy.iterdir()),[self.legacy/'themes'])
            self.assertEqual(config_path('git.conf'), self.path.parent/'git.conf')
            self.assertTrue(json.loads(self.path.read_text())['settings']['files.backup'])
            again=self.plan();again.migrate();again.finish()
            self.assertEqual(again.operations,[])
            self.assertEqual(marker.stat().st_mtime_ns,theme_stat.st_mtime_ns)
            store = Store(Path(self.env['XDG_STATE_HOME'])/'dots')
            operations, guards, catalogs = store.inverse(result['id'])
            store.apply('undo', operations, guards, retain=True, catalogs=catalogs)
        self.assertEqual({p.relative_to(self.legacy):p.read_bytes() for p in self.legacy.rglob('*') if p.is_file()},original)

    def test_migration_conflicts_special_objects_and_stale_preview(self):
        self.legacy.mkdir(parents=True)
        source=self.legacy/'git.conf';source.write_text('original')
        target=self.path.parent/'git.conf';target.write_text('different')
        with patch.dict(os.environ,self.env,clear=True):
            plan=self.plan()
            with self.assertRaisesRegex(ValueError,'conflict'):plan.migrate()
            target.unlink()
            plan=self.plan();plan.migrate();plan.finish()
            source.write_text('changed')
            with self.assertRaisesRegex(ValueError,'changed'):plan.apply('migrate')
            source.unlink();source.symlink_to(self.home/'missing')
            with self.assertRaises(ValueError):self.plan().migrate()
        self.assertFalse(target.exists())

    def test_profile_file_overrides_and_mapping_editor(self):
        original=(self.root/'.dots/files.json').read_bytes()
        self.run_config('set','files.dots',json.dumps([dict(self.resource,target='${CONFIG}/different')]),'--json-value')
        with patch.dict(os.environ,self.env,clear=True):
            self.assertEqual(Catalog(self.root,self.platform).records()[0]['target'],str(self.home/'config/different'))
            other='windows' if self.platform!='windows' else 'termux'
            self.assertEqual(Catalog(self.root,other).records()[0]['target'],str(self.home/'config/app'))
        result=subprocess.run([shutil.which('bash'),str(self.root/'bin/dots'),'files','edit','dots:app','--target','${CONFIG}/third','--yes','--json'],env=self.env,text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads(self.path.read_text())['files']['dots'][0]['target'],'${CONFIG}/third')
        self.assertEqual((self.root/'.dots/files.json').read_bytes(),original)

    def test_inheritance_and_profile_selection(self):
        self.run_config('set','DOTS_COLOR','always','--profile','linux')
        self.assertEqual(self.run_config('get','DOTS_COLOR','--profile','wsl').stdout,'always\n')
        self.run_config('set','DOTS_COLOR','never','--profile','wsl')
        self.assertEqual(self.run_config('get','DOTS_COLOR','--profile','linux').stdout,'always\n')
        self.run_config('unset','DOTS_COLOR','--profile','wsl')
        self.assertEqual(self.run_config('get','DOTS_COLOR','--profile','wsl').stdout,'always\n')

    def test_failed_migration_rolls_back_and_undo_detects_drift(self):
        self.legacy.mkdir(parents=True)
        source=self.legacy/'git.conf';source.write_text('original')
        target=self.path.parent/'git.conf'
        import transactions
        rename=transactions.os.rename
        failed=False
        def fail_once(left, right):
            nonlocal failed
            if Path(left)==source and not failed:
                failed=True
                raise OSError('injected replacement failure')
            return rename(left,right)
        with patch.dict(os.environ,self.env,clear=True):
            plan=self.plan();plan.migrate();plan.finish()
            with patch.object(transactions.os,'rename',side_effect=fail_once):
                with self.assertRaises(OSError):plan.apply('migrate')
            self.assertEqual(source.read_text(),'original')
            self.assertFalse(target.exists())
            plan=self.plan();plan.migrate();plan.finish();result=plan.apply('migrate')
            target.write_text('later user edit')
            with self.assertRaisesRegex(ValueError,'drift'):
                Store(Path(self.env['XDG_STATE_HOME'])/'dots').inverse(result['id'])

    def test_profile_values_in_native_shells_and_completion(self):
        self.run_config('set','DOTS_INIT_COLORS','0')
        for shell in ('bash','zsh','fish'):
            if not shutil.which(shell): continue
            if shell=='fish':
                code='python3 -B "$DOTS/lib/dots/native_startup.py" fish "$XDG_CACHE_HOME/environment.fish"; source "$XDG_CACHE_HOME/environment.fish"; source "$DOTS/lib/dots/shell/config.fish"; _dots_config_load; printf "%s|%s|%s" $_dots_option_DOTS_INIT_COLORS $_dots_source_DOTS_INIT_COLORS $_DOTS_CONFIG_PATH'
            else:
                code='source "$DOTS/lib/dots/shell/config.bash"; _dots_config_load; printf "%s|%s|%s" "${dots_options[DOTS_INIT_COLORS]}" "${dots_option_sources[DOTS_INIT_COLORS]}" "$_DOTS_CONFIG_PATH"'
            result=subprocess.run([shell,'-c',code],env=self.env,text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,'0|profile:'+self.platform+'|'+str(self.path))
        from shell.runtime import settings
        with patch.dict(os.environ,self.env,clear=True):
            values, origins, path=settings(self.root,self.env)
        self.assertEqual((values['DOTS_INIT_COLORS'],origins['DOTS_INIT_COLORS'],path),('0','profile:'+self.platform,str(self.path)))
        for native in (False,True):
            command=[sys.executable,'-B',str(self.root/'lib/dots/cli.py')] if native else [shutil.which('bash'),str(self.root/'bin/dots')]
            words=['__complete','config','set','DOTS_INIT_C'] if native else ['__complete','bash','3','--','dots','config','set','DOTS_INIT_C']
            result=subprocess.run([*command,*words],env=self.env,text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('DOTS_INIT_COLORS',result.stdout)

    def test_human_widths_and_redacted_json(self):
        self.run_config('set','environment.API_KEY','${EXTERNAL_KEY}')
        for width in (40,80,120):
            output=self.run_config('list',COLUMNS=str(width),DOTS_COLOR='always',DOTS_ICONS='always').stdout
            self.assertIn('[redacted]',output)
            self.assertNotIn('EXTERNAL_KEY',output)
        if os.name == 'posix':
            import errno
            import fcntl
            import pty
            import re
            import struct
            import termios
            self.run_config('set','environment.EDITOR','nano café')
            for width in (40,80,120):
                reader, writer = pty.openpty()
                try:
                    fcntl.ioctl(writer,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                    process=subprocess.Popen([shutil.which('bash'),str(self.root/'bin/dots'),'config','list'],
                                             env=dict(self.env,TERM='xterm-256color',COLUMNS=str(width),DOTS_COLOR='auto',DOTS_ICONS='auto'),
                                             stdout=writer,stderr=writer)
                    os.close(writer); writer=None
                    chunks=[]
                    while True:
                        try: chunk=os.read(reader,4096)
                        except OSError as error:
                            if error.errno != errno.EIO: raise
                            break
                        if not chunk: break
                        chunks.append(chunk)
                    self.assertEqual(process.wait(timeout=20),0)
                    text=b''.join(chunks).decode()
                    self.assertIn('\x1b[',text)
                    self.assertIn('nano café',text)
                    self.assertNotIn('EXTERNAL_KEY',text)
                    self.assertTrue(all(len(line)<=width for line in re.sub(r'\x1b\[[0-9;]*m','',text).splitlines()),text)
                finally:
                    os.close(reader)
                    if writer is not None: os.close(writer)
        data=json.loads(self.run_config('list','--json',DOTS_COLOR='always',DOTS_ICONS='always').stdout)
        self.assertEqual(data['config']['environment']['API_KEY'],'[redacted]')

    def test_copy_install_update_drift_and_uninstall(self):
        self.run_config('set','files.dots',json.dumps([dict(self.resource,strategy='copy')]),'--json-value')
        (self.root/'lib/dots/themes').rename(self.root/'lib/dots/unused-themes')
        target=self.home/'config/app';target.parent.mkdir(exist_ok=True);target.write_text('original user config')
        source=self.root/'config/app'
        from install import Installation
        with patch.dict(os.environ,self.env,clear=True):
            plan=Installation(self.root);plan.plan_install();self.assertFalse(plan.blocked)
            item=next(row for row in plan.items if row['id']=='dots:app')
            self.assertEqual(item['strategy'],'copy');self.assertEqual(item['reason'],'copy regular file')
            plan.apply('install')
            self.assertFalse(target.is_symlink());self.assertEqual(target.read_text(),'source\n')
            plan=Installation(self.root);plan.plan_install();self.assertEqual(plan.operations,[])
            source.write_text('updated source')
            plan=Installation(self.root);plan.plan_install();plan.apply('install')
            self.assertEqual(target.read_text(),'updated source')
            target.write_text('user drift')
            plan=Installation(self.root);plan.plan_install();self.assertTrue(plan.blocked)
            with self.assertRaises(ValueError):plan.apply('install')
            target.write_text('updated source')
            plan=Installation(self.root);plan.plan_uninstall();plan.apply('uninstall')
            self.assertEqual(target.read_text(),'original user config')


if __name__ == '__main__': unittest.main()
