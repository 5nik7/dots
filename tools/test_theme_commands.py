#!/usr/bin/env python3
"""Unified theme commands; every mutation stays in a disposable public fixture."""
import os
from pathlib import Path
import subprocess
import shutil
import unittest
from test_themes import Themes, BASH, ZSH

class ThemeCommands(unittest.TestCase):
    setUp = Themes.setUp
    run_command = Themes.run_command
    dots = Themes.dots
    shell = Themes.shell
    engine = Themes.engine
    generation = Themes.generation

    def palette(self, name='sample', data='blue = "#123456"\n', metadata=''):
        path = self.repo / 'themes' / name
        path.mkdir()
        (path / 'palette.toml').write_text(data)
        if metadata:
            (path / 'theme.toml').write_text(metadata)
        return path

    def registry(self):
        return self.state / 'commands/current'

    def test_equivalent_routes_native_queries_and_generated_wrappers(self):
        for args in [('list',), ('catppuccin','mocha','blue','hex'), ('catppuccin','--help'), ('rose-pine','moon','show')]:
            one=self.dots('theme',*args)
            two=self.run_command([BASH,str(self.repo/'bin/theme'),*args])
            self.assertEqual((one.stdout,one.stderr),(two.stdout,two.stderr))
        self.assertEqual(self.dots('theme','catppuccin','mocha','blue','rgb').stdout,'137 180 250\n')
        self.dots('theme','refresh','--commands-only')
        self.assertFalse((self.state/'current').exists())
        names=(self.registry()/'names').read_text().split()
        self.assertIn('catppuccin',names)
        self.assertIn('nord',names)
        self.assertNotIn('catppuccin-mocha',names)
        self.assertEqual(self.run_command([str(self.registry()/'bin/catppuccin'),'mocha','blue','hex']).stdout,'#89b4fa\n')
        old=self.registry().readlink()
        self.dots('theme','refresh','--commands-only')
        self.assertEqual(old,self.registry().readlink())
        self.dots('theme','catppuccin','mocha','set')
        self.assertEqual(self.dots('theme','current').stdout,'catppuccin-mocha\n')
        override={**self.env,'DOTS_THEME_SELECTION':'catppuccin-latte'}
        self.assertEqual(self.dots('theme','current',env=override).stdout,'catppuccin-latte\n')
        self.assertEqual(self.dots('theme','color','blue',env=override).stdout,'#1e66f5\n')

    def test_palette_only_native_and_activation(self):
        p=self.palette()
        self.assertIn('sample',self.dots('theme','list').stdout)
        self.assertEqual(self.dots('theme','sample','blue','hex').stdout,'#123456\n')
        self.dots('theme','sample','set',code=1)
        self.assertFalse((self.state/'current').exists())
        (p/'palette.toml').write_text('blue = "#123456"\nbg = "#101010"\nfg = "#eeeeee"\n')
        (p/'theme.toml').write_text('[roles]\nbackground = "bg"\nforeground = "fg"\n')
        self.dots('theme','sample','set')
        self.assertEqual(self.dots('theme','color','hint').stdout,'#123456\n')
        self.assertEqual(self.dots('theme','current').stdout,'sample\n')
        self.assertIn('sample',self.dots('theme','init').stdout)
        (p/'colors.toml').write_text('background = "#202020"\nforeground = "#dddddd"\nblue = "#abcdef"\n')
        self.assertEqual(self.dots('theme','color','blue','--theme','sample').stdout,'#abcdef\n')
        self.assertEqual(self.dots('theme','sample','blue').stdout,'#123456\n')
        (p/'palette.toml').write_text('blue = "#123456"\nblue = "#ffffff"\n')
        self.dots('theme','sample','show',code=1)

    def test_metadata_grouping_default_and_exact_selection_id(self):
        for name,flavor in [('arbitrary-one','dark'),('arbitrary-two','light')]:
            self.palette(name,'background = "#101010"\nforeground = "#eeeeee"\n',f'family = "custom-family"\nflavor = "{flavor}"\n')
        self.dots('theme','custom-family','show',code=1)
        self.dots('theme','custom-family','dark','set')
        self.assertEqual(self.dots('theme','current').stdout,'arbitrary-one\n')
        self.dots('theme','refresh')
        self.dots('theme','init')
        self.assertEqual(set(self.dots('theme','list','--flavors','custom-family').stdout.split()),{'dark','light'})

    def test_logo_usage_plain_and_data_boundaries(self):
        self.palette('sample')
        (self.repo/'themes/sample/logo.txt').write_text('\x1b[31mSAMPLE ART\x1b[0m\n')
        self.assertTrue(self.dots('theme','sample','--help').stdout.startswith('SAMPLE ART\n'))
        # Incomplete palettes keep readable help; valid palettes recolor artwork.
        (self.repo/'themes/sample/palette.toml').write_text('blue = "#123456"\nbackground = "#101010"\nforeground = "#eeeeee"\n')
        styled=self.dots('theme','sample','--help',env={**self.env,'DOTS_COLOR':'always'}).stdout
        self.assertIn('SAMPLE ART',styled)
        self.assertIn('\x1b[48;2;',styled)
        self.assertNotIn('\x1b[31m',styled)
        for args in [('show',),('blue','hex'),('--raw',),('--array',)]:
            self.assertNotIn('SAMPLE ART',self.dots('theme','sample',*args).stdout)
        self.assertEqual(self.dots('help','theme','sample').stdout,self.dots('theme','sample','--help').stdout)

    def test_completion_shared_reader_and_native_shell_adapters(self):
        self.dots('theme','refresh','--commands-only')
        for shell in ('bash','zsh','fish'):
            for words in [('dots','theme','catppuccin','mocha','bl'),('theme','catppuccin','mocha','bl'),('catppuccin','mocha','bl')]:
                data=self.dots('__complete',shell,str(len(words)-1),'--',*words).stdout
                self.assertIn('candidate\tblue\t',data)
        self.assertIn('candidate\thex\t',self.dots('__complete','bash','3','--','catppuccin','mocha','blue','h').stdout)
        self.assertIn('catppuccin',self.shell('source "$DOTS/lib/dots/completion/bash"; complete -p catppuccin').stdout)
        if ZSH:
            self.assertIn('_dots',self.shell('autoload -Uz compinit; compinit -D; source "$DOTS/lib/dots/completion/zsh"; print -r -- $_comps[catppuccin]',ZSH).stdout)

    def test_registry_rollback_interruption_and_drift(self):
        self.dots('theme','set','nord')
        old=self.registry().readlink()
        self.palette()
        self.engine('dt_commands_publish() { return 1; }; dt_set catppuccin-mocha',code=1)
        self.assertEqual(self.registry().readlink(),old)
        self.assertEqual(self.dots('theme','current').stdout,'nord\n')
        # Simulate abrupt death after publishing a prepared command-only journal.
        self.engine('dt_commands_lock; j=$(mktemp -d "$DT_COMMANDS/generations/c.XXXXXXXX"); dt_commands_prepare "$j"; dt_commands_record "$j" prepared; dt_commands_publish "$j"')
        self.assertNotEqual(self.registry().readlink(),old)
        self.engine('dt_commands_lock')
        self.assertEqual(self.registry().readlink(),old)
        command=self.registry()/'bin/nord'
        command.write_text(command.read_text()+'# owner edit\n')
        self.dots('theme','refresh','--commands-only',code=1)
        self.assertIn('# owner edit',command.read_text())

    def test_palette_only_import_and_failed_command_publication(self):
        remote=self.root/'native import'
        remote.mkdir()
        (remote/'palette.toml').write_text('blue = "#123456"\n')
        (remote/'logo.txt').write_text('IMPORTED ART\n')
        for args in [('init','-q'),('add','.'),('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Palette')]:
            self.run_command(['git','-C',str(remote),*args])
        env={**self.env,'DOTS_TEST_LOCAL_GIT':'always'}
        self.dots('theme','install',str(remote),'--name','native-import',env=env)
        self.assertEqual(self.dots('theme','native-import','blue').stdout,'#123456\n')
        self.assertIn('IMPORTED ART',self.dots('theme','native-import','--help').stdout)
        self.assertTrue((self.registry()/'bin/native-import').is_file())
        old=self.registry().readlink()
        body='''DT_LIB="$DOTS/lib/dots/themes"; source "$DT_LIB/core.bash"; source "$DT_LIB/install.bash"
dt_commands_publish() { return 1; }
dt_git_theme remove native-import
'''
        self.run_command([BASH,'-c',body],code=1,env=env)
        self.assertTrue((self.home/'config/dots/themes/native-import/palette.toml').is_file())
        self.assertEqual(self.registry().readlink(),old)
        self.dots('theme','remove','native-import',env=env)
        self.assertFalse((self.registry()/'bin/native-import').exists())

    @unittest.skipUnless(ZSH, 'native Zsh unavailable')
    def test_published_zsh_startup_and_prompt_command_refresh(self):
        import zsh_fixture
        try:
            root, repo, env = zsh_fixture.fixture()
        except RuntimeError as error:
            self.skipTest(str(error))
        self.addCleanup(shutil.rmtree, root)
        env['DOTS_COLOR'] = 'never'
        proc = subprocess.run([BASH, str(repo/'bin/dots'), 'theme', 'set', 'catppuccin-mocha'],
                              env=env, cwd=env['HOME'], text=True, capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        code = r'''[[ ${blue[hex]} == '#89b4fa' && ${#rst} == 4 && $rst == $RST ]] || exit 21
[[ ${commands[catppuccin]} == $XDG_STATE_HOME/dots/themes/commands/current/bin/catppuccin ]] || exit 22
[[ ${_comps[catppuccin]} == _dots ]] || exit 23
fast-theme --show
_dots_theme_precmd
rlcs
[[ ${_comps[catppuccin]} == _dots && ${_comps[theme]} == _dots ]] || exit 27
mkdir -p "$DOTS/themes/newpalette"
printf 'blue = "#123456"\n' > "$DOTS/themes/newpalette/palette.toml"
command dots theme refresh --commands-only || exit 24
_dots_theme_precmd
[[ ${_comps[newpalette]} == _dots ]] || exit 25
[[ $(newpalette blue hex) == '#123456' ]] || exit 26
print -r -- STARTUP_OK
'''
        result=zsh_fixture.run(env,code)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('STARTUP_OK',result.stdout)
        import re
        plain=re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '',result.stdout)
        self.assertIn('Currently active theme: dots',plain)
        self.assertIn('Main theme (loaded at startup of a session): dots',plain)

    @unittest.skipUnless(ZSH, 'native Zsh unavailable')
    def test_native_zle_family_completion(self):
        import zsh_fixture
        from zsh_interactive import Session
        try:
            root, repo, env = zsh_fixture.fixture()
        except RuntimeError as error:
            self.skipTest(str(error))
        self.addCleanup(shutil.rmtree, root)
        proc=subprocess.run([BASH,str(repo/'bin/dots'),'theme','refresh','--commands-only'],
                            env=env,cwd=env['HOME'],text=True,capture_output=True,timeout=60)
        self.assertEqual(proc.returncode,0,proc.stderr)
        rc=repo/'shells/zsh/zshrc'
        rc.write_text(rc.read_text()+'''
autoload -Uz add-zle-hook-widget
_dots_test_ready() { print -r -- __DOTS_INPUT_READY__; }
add-zle-hook-widget line-init _dots_test_ready
''')
        session=Session(env,env['HOME'])
        self.addCleanup(session.close)
        session.wait()
        session.send('catppuccin moc\t')
        session.wait(marker=b'mocha',timeout=30)
        session.send('blue he\t')
        session.wait(marker=b'hex',timeout=30)
        session.send('\r')
        self.assertIn(b'#89b4fa',session.wait())
        session.send('theme rose-pine da\t')
        session.wait(marker=b'dawn',timeout=30)
        session.send('base hex\r')
        self.assertIn(b'#faf4ed',session.wait())
        self.assertFalse((Path(env['XDG_STATE_HOME'])/'dots/themes/current').exists())

    def test_missing_logo_reserved_command_and_duplicate_family(self):
        self.palette('set')
        self.dots('theme','refresh','--commands-only')
        self.assertFalse((self.registry()/'bin/set').exists())
        self.assertIn('set',self.dots('theme','show','set','--native').stdout)
        self.palette('another','blue = "#ffffff"\n','family = "nord"\nflavor = "default"\n')
        self.dots('theme','refresh','--commands-only',code=1)

if __name__=='__main__': unittest.main(defaultTest='ThemeCommands', verbosity=2)
