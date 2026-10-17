#!/usr/bin/env python3
"""Git/Delta consumers in private HOME/config/state/cache and Git repositories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import test_themes as fixtures
from test_themes import REPO, BASH


@unittest.skipUnless(shutil.which('git') and shutil.which('delta') and shutil.which('bat'), 'Git, Delta and bat required')
class GitTheme(unittest.TestCase):
    setUp = fixtures.Themes.setUp
    run_command = fixtures.Themes.run_command
    dots = fixtures.Themes.dots
    generation = fixtures.Themes.generation
    shell = fixtures.Themes.shell
    engine = fixtures.Themes.engine

    def prepare(self):
        self.config=Path(self.env['XDG_CONFIG_HOME'])/'git';self.config.mkdir(parents=True)
        for name in ('gitconfig','gitppuccin'):
            shutil.copy2(REPO/'config/git'/name,self.config/name)
        (self.config/'gitaliases').write_text('[alias]\n fixture = status\n')
        (self.config/'config').write_text('[include]\n path = gitconfig\n path = gitplatform\n')
        (self.config/'termux').write_text('[fixture]\n platform = termux\n[credential]\n helper = !touch SHOULD_NOT_RUN\n')
        (self.config/'gitplatform').symlink_to('termux')
        self.env.update(GIT_CONFIG_GLOBAL=str(self.config/'config'),GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',DELTA_PAGER='cat')
        self.original={p.name:p.read_bytes() for p in self.config.iterdir() if p.is_file() and not p.is_symlink()}
        self.normal_cache=Path(self.env['XDG_CACHE_HOME'])/'bat';self.normal_cache.mkdir(parents=True)
        (self.normal_cache/'sentinel').write_text('keep my cache')

    def test_native_dark_light_diff_and_idempotence(self):
        self.prepare()
        fixture=self.home/'fixture repo ü';fixture.mkdir()
        def git(*args):
            r=subprocess.run(['git',*args],cwd=fixture,env=self.env,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);return r.stdout
        git('init','-b','fixture')
        source=fixture/'sample.py';source.write_text('value = 1\n')
        git('add','sample.py');git('-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-m','fixture')
        source.write_text('value = 2\n')
        diff=git('-c','color.ui=never','--no-pager','diff')
        scripts={key:git('config','--get',key).strip() for key in ('core.pager','interactive.diffFilter')}
        seen=[]
        for theme in ('catppuccin-mocha','catppuccin-latte'):
            self.dots('theme','set',theme)
            generation=self.generation()
            colors=json.loads((generation/'colors.json').read_text())['colors']
            rendered=self.config/'dots-theme.gitconfig'
            self.assertTrue(rendered.is_symlink())
            self.assertEqual(git('config','--get','delta.features').strip(),'dots')
            self.assertEqual(git('config','--get','color.status.changed').strip(),colors['git']['modified']+' bold')
            for key,script in scripts.items():
                result=subprocess.run([BASH,'--noprofile','--norc','-c',script],input=diff,cwd=fixture,env=self.env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stderr,'')
                self.assertIn('38;2;',result.stdout)
                self.assertIn('value',result.stdout)
                if key=='core.pager':seen.append(result.stdout)
            env=dict(self.env,XDG_CACHE_HOME=str(generation/'delta-cache'))
            listing=self.run_command(['delta','--list-syntax-themes'],env=env)
            self.assertIn('Dots',listing.stdout)
            settings=self.run_command(['delta','--show-config'],env=env)
            self.assertIn('minus-emph-style',settings.stdout)
            removed=colors['git']['deleted'];background=colors['background']
            blend='#'+''.join(f'{(int(removed[i:i+2],16)+3*int(background[i:i+2],16)+2)//4:02x}' for i in (1,3,5))
            value=git('config','--get','delta.dots.minus-emph-style').strip()
            self.assertEqual(value,'bold syntax '+blend)
            # Raw moved-line colors must match the left side of Delta's map.
            self.assertIn('bold '+colors['magenta']+' => syntax',git('config','--get','delta.dots.map-styles'))
            status=git('-c','color.ui=always','status','--short')
            self.assertIn('38;2;',status)
            self.assertIn('fixture',git('-c','color.ui=always','branch'))
            before=(rendered.lstat().st_mtime_ns,rendered.read_bytes())
            self.dots('theme','refresh')
            self.assertEqual(before,(rendered.lstat().st_mtime_ns,rendered.read_bytes()))
        self.assertNotEqual(*seen)
        for name,data in self.original.items():self.assertEqual((self.config/name).read_bytes(),data)
        self.assertEqual((self.normal_cache/'sentinel').read_text(),'keep my cache')
        self.assertFalse((fixture/'SHOULD_NOT_RUN').exists())

    def test_role_overrides_reset_and_missing_cache(self):
        self.prepare()
        overlay=Path(self.env['XDG_CONFIG_HOME'])/'dots/file-colors.toml';overlay.parent.mkdir(parents=True)
        overlay.write_text('[git.modified]\nfg = "#123456"\n[git.added]\nfg = "reset"\n')
        self.dots('theme','set','nord')
        path=self.generation()/'gitconfig'
        self.assertIn('changed = "#123456 bold"',path.read_text())
        self.assertIn('line-numbers-plus-style = "normal bold"',path.read_text())
        colors=json.loads((self.generation()/'colors.json').read_text())['colors']
        self.assertIn('plus-style = "syntax '+colors['background']+'"',path.read_text())
        result=self.run_command(['delta','--show-config'])
        self.assertEqual(result.stderr,'')
        # Remove only this test-owned generation cache, exercising the fallback.
        shutil.rmtree(self.generation()/'delta-cache')
        script=self.run_command(['git','config','--get','core.pager']).stdout.strip()
        result=subprocess.run([BASH,'--noprofile','--norc','-c',script],input='--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x=1\n+x=2\n',cwd=self.home,env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        self.assertEqual((self.normal_cache/'sentinel').read_text(),'keep my cache')

if __name__=='__main__':unittest.main()
