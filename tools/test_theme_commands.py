#!/usr/bin/env python3
"""Unified theme commands; every mutation stays in a disposable public fixture."""
import os
from pathlib import Path
import subprocess
import shutil
import unittest
import re
import hashlib
import json
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

    def external(self, name):
        directory = self.root / 'external commands ü'; directory.mkdir(exist_ok=True)
        if str(directory) not in self.env['PATH'].split(os.pathsep):
            self.env['PATH'] = str(directory) + os.pathsep + self.env['PATH']
        path = directory / name
        path.write_text('#!' + BASH + '\nprintf "external\\n"\n')
        path.chmod(0o700)
        return path

    def test_collision_suffix_skip_and_reclaim_with_exact_forwarding(self):
        self.palette('fixturepalette')
        external = self.external('fixturepalette')
        original = external.read_bytes()
        result = self.dots('theme', 'refresh', '--commands-only')
        self.assertNotIn('PATH precedence', result.stderr)
        self.assertNotIn('fixturepalette', result.stderr)
        self.assertFalse((self.registry()/'bin/fixturepalette').exists())
        self.assertIn('fixturepalette-theme\tfixturepalette\n', (self.registry()/'map.tsv').read_text())
        wrapper = self.registry()/'bin/fixturepalette-theme'
        self.assertEqual(self.run_command([str(wrapper), 'blue', 'hex']).stdout, '#123456\n')
        self.assertEqual(self.run_command([str(external)]).stdout, 'external\n')
        self.env['PATH'] += os.pathsep + str(self.registry()/'bin')
        old = self.registry().readlink()
        self.dots('theme', 'refresh', '--commands-only')
        self.assertEqual(self.registry().readlink(), old)
        for shell in ('bash', 'zsh', 'fish'):
            rows = self.dots('__complete', shell, '1', '--', 'fixturepalette-theme', 'bl').stdout
            self.assertIn('candidate\tblue\t', rows)
            self.assertEqual(self.dots('__complete', shell, '1', '--', 'fixturepalette', 'bl').stdout, '')
        occupied = self.external('fixturepalette-theme')
        result = self.dots('theme', 'refresh', '--commands-only')
        self.assertIn('Use: theme fixturepalette', result.stderr)
        self.assertFalse(wrapper.exists())
        self.assertNotIn('fixturepalette-theme-2', (self.registry()/'names').read_text())
        self.assertEqual(self.dots('theme', 'fixturepalette', 'blue', 'hex').stdout, '#123456\n')
        self.assertEqual(external.read_bytes(), original)
        external.unlink(); occupied.unlink()
        self.dots('theme', 'refresh', '--commands-only')
        self.assertTrue((self.registry()/'bin/fixturepalette').exists())
        self.assertFalse(wrapper.exists())
        self.assertFalse((self.state/'current').exists())
        # A harmless fixture dispatcher verifies literal argv and exit propagation.
        (self.repo/'bin/dots').write_text('#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(17)\n')
        args = ['', '-leading', 'two words', 'ü', '$(never-run)', "single'quote"]
        result = self.run_command([str(self.registry()/'bin/fixturepalette'), *args], code=17)
        self.assertEqual(json.loads(result.stdout), ['theme', 'fixturepalette', *args])

    def test_collision_upgrade_rollback_and_mapping_drift(self):
        self.palette('fixturepalette')
        self.dots('theme', 'refresh', '--commands-only')
        directory = self.registry().resolve()
        # Reconstruct an authentic legacy payload without the new optional map.
        (directory/'map.tsv').unlink()
        manifest = ''.join(line for line in (directory/'manifest').read_text().splitlines(keepends=True) if not line.endswith('  map.tsv\n'))
        (directory/'manifest').write_text(manifest)
        (directory/'fingerprint').write_text(hashlib.sha256(manifest.encode()).hexdigest() + '\n')
        self.assertIn('candidate\tblue\t', self.dots('__complete', 'bash', '1', '--', 'fixturepalette', 'bl').stdout)
        self.external('fixturepalette')
        self.engine('dt_commands_lock; j=$(mktemp -d "$DT_COMMANDS/generations/c.XXXXXXXX"); dt_commands_prepare "$j"; dt_commands_record "$j" prepared; dt_commands_publish "$j"')
        self.assertTrue((self.registry()/'bin/fixturepalette-theme').exists())
        self.engine('dt_commands_lock')
        self.assertEqual(self.registry().resolve(), directory)
        self.dots('theme', 'refresh', '--commands-only')
        self.assertTrue((self.registry()/'bin/fixturepalette-theme').exists())
        mapping = self.registry()/'map.tsv'
        mapping.write_text(mapping.read_text() + 'unowned\tfixturepalette\n')
        result = self.dots('theme', 'refresh', '--commands-only', code=1)
        self.assertIn('generated commands changed', result.stderr)

    def test_completion_reload_retires_only_owned_registrations(self):
        self.palette('fixturepalette')
        self.dots('theme', 'refresh', '--commands-only')
        for executable in (BASH, ZSH, shutil.which('fish')):
            if not executable: continue
            with self.subTest(shell=executable):
                external = self.root/'external commands ü/fixturepalette'
                external.parent.mkdir(exist_ok=True)
                if external.exists(): external.unlink()
                self.env['PATH'] = str(external.parent) + os.pathsep + self.env['PATH']
                self.dots('theme', 'refresh', '--commands-only')
                if executable == BASH:
                    body = r'''source "$DOTS/lib/dots/completion/bash"
complete -p fixturepalette >/dev/null || exit 11
printf '#!/usr/bin/env bash\nexit 0\n' > "$TEST_EXTERNAL"; chmod +x "$TEST_EXTERNAL"
dots theme refresh --commands-only || exit 12
source "$DOTS/lib/dots/completion/bash"
complete -p fixturepalette >/dev/null 2>&1 && exit 13
complete -p fixturepalette-theme >/dev/null || exit 14
complete -W external fixturepalette-theme
rm "$TEST_EXTERNAL"; dots theme refresh --commands-only || exit 15
source "$DOTS/lib/dots/completion/bash"
[[ $(complete -p fixturepalette-theme) == "complete -W 'external' fixturepalette-theme" ]] || exit 16
complete -p fixturepalette >/dev/null
'''
                elif executable == ZSH:
                    body = r'''autoload -Uz compinit; compinit -D
source "$DOTS/lib/dots/completion/zsh"
[[ $_comps[fixturepalette] == _dots ]] || exit 11
printf '#!/usr/bin/env bash\nexit 0\n' > "$TEST_EXTERNAL"; chmod +x "$TEST_EXTERNAL"
dots theme refresh --commands-only || exit 12
source "$DOTS/lib/dots/completion/zsh"
[[ -z $_comps[fixturepalette] && $_comps[fixturepalette-theme] == _dots ]] || exit 13
compdef _external fixturepalette-theme
rm "$TEST_EXTERNAL"; dots theme refresh --commands-only || exit 15
source "$DOTS/lib/dots/completion/zsh"
[[ $_comps[fixturepalette-theme] == _external && $_comps[fixturepalette] == _dots ]] || exit 16
'''
                else:
                    body = r'''source "$DOTS/lib/dots/completion/fish"
complete -c fixturepalette | string match -q '*__dots_complete_fish*'; or exit 11
printf '#!/usr/bin/env bash\nexit 0\n' > "$TEST_EXTERNAL"; chmod +x "$TEST_EXTERNAL"
dots theme refresh --commands-only; or exit 12
source "$DOTS/lib/dots/completion/fish"
complete -c fixturepalette | string match -q '*__dots_complete_fish*'; and exit 13
complete -c fixturepalette-theme | string match -q '*__dots_complete_fish*'; or exit 14
complete -c fixturepalette-theme -a external
rm "$TEST_EXTERNAL"; dots theme refresh --commands-only; or exit 15
source "$DOTS/lib/dots/completion/fish"
complete -c fixturepalette-theme | string match -q '*external*'; or exit 16
complete -c fixturepalette | string match -q '*__dots_complete_fish*'; or exit 17
'''
                flags = ['--noprofile', '--norc'] if executable == BASH else ['-df'] if executable == ZSH else ['--no-config']
                self.run_command([executable, *flags, '-c', body], env={**self.env, 'TEST_EXTERNAL': str(external)})

    def test_skipped_notice_shares_progress_terminal_at_all_widths(self):
        from test_progress import ProgressTests, ANSI
        body = r'''source "$DOTS/lib/dots/ui.bash"
DT_LIB=$DOTS/lib/dots/themes; DT_STATE=$XDG_STATE_HOME/dots/themes
source "$DT_LIB/command-state.bash"
DOTS_PROGRESS_HUMAN=1
dots::progress_start 'Preparing theme'
sleep 0.7
dots::progress_print dt_commands_skipped fixturepalette fixturepalette-theme
dots::progress_stop
printf 'DONE\n'
'''
        for width in (40, 80, 120):
            with self.subTest(width=width):
                env = {**self.env, 'COLUMNS': str(width), 'DOTS_COLOR': 'always', 'DOTS_ICONS': 'never'}
                code, data = ProgressTests.terminal(self, [BASH, '--noprofile', '--norc', '-c', body], env, width)
                self.assertEqual(code, 0, data)
                plain = ANSI.sub(b'', data).decode()
                self.assertIn('Skipped theme shortcut:', plain)
                self.assertIn('Use: theme fixturepalette', plain)
                self.assertNotRegex(plain, r'Preparing theme[^\r\n]*Skipped')
                self.assertLessEqual(max(map(len, plain.splitlines())), width)
                self.assertTrue(plain.endswith('DONE\r\n'))

    def test_exported_completion_without_dots_environment(self):
        self.dots('theme', 'refresh', '--commands-only')
        env = {key: value for key, value in self.env.items() if key != 'DOTS'}
        for name, shell in (('bash', BASH), ('zsh', ZSH)):
            if not shell: continue
            output = self.dots('completion', name).stdout
            native = self.run_command([shutil.which('python3'), '-B', str(self.repo/'lib/dots/cli.py'), 'completion', name]).stdout
            self.assertEqual(native, output)
            if name == 'zsh': self.assertTrue(output.startswith('#compdef dots\n'))
            exported = self.root / ('completion.' + name)
            exported.write_text(output)
            body = ('autoload -Uz compinit; compinit -D\n' if name == 'zsh' else '') + 'set -u\nsource "$TEST_COMPLETION"\n'
            body += '\ncomplete -p nord\n' if name == 'bash' else '\n[[ $_comps[nord] == _dots ]]\n'
            flags = ['--noprofile', '--norc'] if name == 'bash' else ['-df']
            self.run_command([shell, *flags, '-c', body], env={**env, 'TEST_COMPLETION': str(exported)})

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
        # The logo's own colors do not depend on a usable theme palette.
        incomplete=self.dots('theme','sample','--help',env={**self.env,'DOTS_COLOR':'always'}).stdout
        self.assertIn('\x1b[31mSAMPLE ART\x1b[0m',incomplete)
        (self.repo/'themes/sample/palette.toml').write_text('blue = "#123456"\nbackground = "#101010"\nforeground = "#eeeeee"\n')
        styled=self.dots('theme','sample','--help',env={**self.env,'DOTS_COLOR':'always'}).stdout
        self.assertIn('SAMPLE ART',styled)
        self.assertIn('\x1b[48;2;',styled)
        self.assertTrue(styled.startswith('\x1b[0m  \x1b[31mSAMPLE ART\x1b[0m\x1b[0m\n'))
        for args in [('show',),('blue','hex'),('--raw',),('--array',)]:
            self.assertNotIn('SAMPLE ART',self.dots('theme','sample',*args).stdout)
        self.assertEqual(self.dots('help','theme','sample').stdout,self.dots('theme','sample','--help').stdout)

    def test_logo_colors_width_resets_and_plain_fallback(self):
        path=self.palette('sample', 'background = "#101010"\nforeground = "#eeeeee"\nblue = "#123456"\n')
        logo=path/'logo.txt'
        env={**self.env,'DOTS_COLOR':'always','COLUMNS':'40'}
        for code in ('\x1b[31m','\x1b[104m','\x1b[38;5;123m',
                     '\x1b[38;2;123;45;67;48;2;20;30;40m','\x1b[38:2::123:45:67m'):
            with self.subTest(code=repr(code)):
                # Deliberately carry color across lines, with no authored final reset.
                logo.write_text(code+'FIRST\nSECOND\x1b[2J\x07')
                output=self.dots('theme','sample','--help',env=env).stdout
                header=output.split('\n',2)[:2]
                self.assertEqual(header,['\x1b[0m  '+code+'FIRST','  SECOND[2J\x1b[0m'])
                self.assertNotIn('\x1b[2J',output)
                self.assertNotIn('\x07',output)
                plain=self.dots('theme','sample','--help','--color=none',env=env).stdout
                self.assertNotIn('\x1b',plain)
                self.assertTrue(plain.startswith('FIRST\nSECOND[2J\n'))
        for text in ('PLAIN','\x1b[1mBOLD\x1b[0m'):
            logo.write_text(text)
            output=self.dots('theme','sample','--help',env=env).stdout
            self.assertTrue(output.startswith('\x1b[48;2;16;16;16m\x1b[38;2;'))
            self.assertIn(re.sub(r'\x1b\[[0-9;:]*m','',text),output.splitlines()[0])
        logo.write_text('\x1b[31m'+'W'*50+'\x1b[0m')
        self.assertNotIn('W'*50,self.dots('theme','sample','--help',env=env).stdout)
        for mode in ({'DOTS_COLOR':'never'}, {'DOTS_COLOR':'auto','NO_COLOR':'1'}, {'DOTS_COLOR':'auto','TERM':'dumb'}):
            self.assertNotIn('\x1b',self.dots('theme','sample','--help',env={**env,**mode}).stdout)

    def test_catppuccin_logo_keeps_authored_truecolor(self):
        logo=(self.repo/'themes/catppuccin/logo.txt').read_text()
        output=self.dots('theme','catppuccin','--help',env={**self.env,'DOTS_COLOR':'always','COLUMNS':'120'}).stdout
        for line in logo.rstrip('\n').split('\n'):
            self.assertIn('  '+line,output)
        self.assertTrue(output.startswith('\x1b[0m'))
        self.assertNotIn('\x1b',self.dots('theme','catppuccin','--help','--color=none').stdout)

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
