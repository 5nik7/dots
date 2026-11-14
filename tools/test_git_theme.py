#!/usr/bin/env python3
"""Git/Delta consumers in private HOME/config/state/cache and Git repositories."""
import json
import os
from pathlib import Path
import re
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
        # Only this native-consumer fixture needs bat publication and Delta.
        for name in ('bat', 'delta'):
            (self.tools / name).symlink_to(os.path.abspath(shutil.which(name)))
        self.config=Path(self.env['XDG_CONFIG_HOME'])/'git';self.config.mkdir(parents=True)
        # Model the documented include chain without importing personal settings
        # or requiring the optional gitppuccin source to be installed.
        (self.config/'gitconfig').write_text('''[user]
 name = Fixture
 email = fixture@example.invalid
[color]
 ui = auto
[color "status"]
 added = green bold
 changed = yellow bold
[include]
 path = gitaliases
 path = gitppuccin
[delta]
 navigate = true
 side-by-side = false
 line-numbers = true
 true-color = always
 features = catppuccin-mocha
[include]
 path = dots-theme.gitconfig
''')
        (self.config/'gitppuccin').write_text('''[delta "catppuccin-mocha"]
 minus-style = red
 plus-style = green
''')
        (self.config/'gitaliases').write_text('[alias]\n fixture = status\n')
        (self.config/'config').write_text('[include]\n path = gitconfig\n path = gitplatform\n')
        (self.config/'termux').write_text('[fixture]\n platform = termux\n[color "branch"]\n remote = magenta bold\n[credential]\n helper = !touch SHOULD_NOT_RUN\n')
        (self.config/'gitplatform').symlink_to('termux')
        self.env.update(GIT_CONFIG_GLOBAL=str(self.config/'config'),GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',DELTA_PAGER='cat')
        # Exercise the actual shipped cache/fallback commands, selecting only
        # these two inert values from the public file, without following includes.
        for key in ('core.pager', 'interactive.diffFilter'):
            value = self.run_command(['git', 'config', '--file', str(REPO/'config/git/gitconfig'),
                                      '--no-includes', '--get', key]).stdout.rstrip('\n')
            self.run_command(['git', 'config', '--file', str(self.config/'gitconfig'), key, value])
        self.original={p.name:p.read_bytes() for p in self.config.iterdir() if p.is_file() and not p.is_symlink()}
        self.normal_cache=Path(self.env['XDG_CACHE_HOME'])/'bat';self.normal_cache.mkdir(parents=True)
        (self.normal_cache/'sentinel').write_text('keep my cache')
        self.assert_include_contract(published=False)

    def assert_include_contract(self, *, published):
        def values(key):
            return self.run_command(['git', 'config', '--get-all', key]).stdout.splitlines()
        self.assertEqual(values('include.path'),
                         ['gitconfig', 'gitaliases', 'gitppuccin', 'dots-theme.gitconfig', 'gitplatform'])
        self.assertEqual(values('delta.features'), ['catppuccin-mocha', 'dots'] if published else ['catppuccin-mocha'])
        self.assertEqual(values('color.branch.remote')[-1], 'magenta bold')
        self.assertEqual(values('fixture.platform'), ['termux'])
        self.assertEqual(values('alias.fixture'), ['status'])
        self.assertEqual(values('user.name'), ['Fixture'])
        self.assertEqual(values('user.email'), ['fixture@example.invalid'])
        if not published:
            self.assertEqual(values('color.status.changed'), ['yellow bold'])
        self.assertEqual((self.config/'gitplatform').readlink(), Path('termux'))
        for name, data in self.original.items():
            self.assertEqual((self.config/name).read_bytes(), data)

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
            self.assert_include_contract(published=True)
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
            self.assert_include_contract(published=True)
        self.assertNotEqual(*seen)
        # Removing only this fixture's generated include restores source fallback.
        rendered.unlink()
        self.assert_include_contract(published=False)
        self.assertEqual((self.normal_cache/'sentinel').read_text(),'keep my cache')
        self.assertFalse((fixture/'SHOULD_NOT_RUN').exists())

    def test_role_overrides_reset_and_missing_cache(self):
        self.prepare()
        overlay=Path(self.env['XDG_CONFIG_HOME'])/'dots/file-colors.toml';overlay.parent.mkdir(parents=True)
        overlay.write_text('[git.modified]\nfg = "#123456"\n[git.added]\nfg = "reset"\n')
        self.dots('theme','set','nord')
        self.assert_include_contract(published=True)
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
        # Syntax highlighting may put SGR boundaries between every token.
        # Keep raw styling checks separate from assertions about visible text.
        self.assertRegex(result.stdout, r'\x1b\[[0-9;:]+m')
        self.assertIn('\x1b[0m', result.stdout)
        visible = re.sub(r'\x1b\[[0-9;:]*m', '', result.stdout)
        self.assertIn('x=1', visible)
        self.assertIn('x=2', visible)
        self.assert_include_contract(published=True)
        self.assertEqual((self.normal_cache/'sentinel').read_text(),'keep my cache')

if __name__=='__main__':unittest.main()
