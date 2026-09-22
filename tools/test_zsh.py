#!/usr/bin/env python3
"""Isolated regression checks for the public Zsh configuration (no downloads)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
ZSH = shutil.which('zsh')


class ZshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-zsh-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo space ü'
        for name in ('shells/zsh', 'bin', 'themes'):
            if name == 'shells/zsh':
                shutil.copytree(REPO / name, self.repo / name)
            else:
                (self.repo / name).mkdir(parents=True, exist_ok=True)
        for name in ('bin/util', 'bin/colors.env'):
            shutil.copy2(REPO / name, self.repo / name)
        self.env = {'HOME': str(self.root), 'ZDOTDIR': str(self.root),
                    'DOTS': str(self.repo), 'XDG_CACHE_HOME': str(self.root / 'cache'),
                    'XDG_CONFIG_HOME': str(self.root / 'config'),
                    'XDG_DATA_HOME': str(self.root / 'data'),
                    'XDG_STATE_HOME': str(self.root / 'state'), 'TMPDIR': str(self.root),
                    'TERM': 'xterm-256color', 'PATH': str(Path(ZSH).parent) + ':/usr/bin:/bin'}
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']

    def shell(self, text, check=True):
        p = subprocess.run([ZSH, '-dfc', text], env=self.env, cwd=self.root,
                           text=True, capture_output=True, timeout=30)
        if check:
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return p

    def test_paths_preserve_precedence_literal_names_and_missing(self):
        for name in ('first', 'space ü', '-dash', 'literal[1]'):
            (self.root / name).mkdir()
        self.shell('''source "$DOTS/bin/util"
path=("$HOME/first" "$HOME/space ü")
prepath "$HOME/space ü"
[[ $path[1] == "$HOME/first" ]] || exit 1
prepath "$HOME/literal[1]"
extpath "$HOME/-dash"
[[ $path[1] == "$HOME/literal[1]" && $path[-1] == "$HOME/-dash" ]] || exit 2
before=$PATH
prepath "$HOME/missing" && exit 3
[[ $PATH == $before ]] || exit 4
''')

    def test_completion_dump_loads_literal_bracket_function_in_fresh_shell(self):
        providers = self.root / 'completions'
        providers.mkdir()
        (providers / '_uu-[').write_text('#compdef uu-[\nreturn 0\n')
        setup = '''fpath=("$HOME/completions" $fpath)
source "$DOTS/shells/zsh/core/completion.zsh"
(( ${+functions[_setup]} && ${+functions[_complete]} )) || exit 1
[[ ${_comps[uu-\\[]:-} == '_uu-[' ]] || exit 2
autoload +X _setup _complete || exit 3
[[ -o glob && -o badpattern ]] || exit 4
'''
        for attempt in range(3):
            p = self.shell(setup)
            self.assertEqual(p.stderr, '')
            if attempt == 0:
                # Reproduce a dump written before the repair existed.
                dump = next((self.root / 'cache').rglob('zcompdump'))
                dump.write_text(dump.read_text().replace('\nnoglob autoload -Uz ',
                                                        '\nautoload -Uz '))

    def test_platform_context_and_distribution_are_separate(self):
        (self.root / 'os-release').write_text('NAME="Ubuntu Linux"\nID=ubuntu\n')
        for osname, kernel, expected in [('linux-gnu', '6.1-linux', 'linux:false'),
                                         ('linux-gnu', '6.1-microsoft-standard-WSL2', 'wsl:true'),
                                         ('msys', 'unused', 'msys:false')]:
            (self.root / 'kernel').write_text(kernel + '\n')
            p = self.shell(f'''source "$DOTS/shells/zsh/platforms/detect.zsh"
_dots_detect_platform {osname} "$HOME/os-release" "$HOME/kernel" "$HOME/missing"
print -r -- "$DOTS_PLATFORM:$is_wsl:$distro"
''')
            self.assertEqual(p.stdout.strip(), expected + ':ubuntu')
        self.shell('''TERMUX_VERSION=fixture
source "$DOTS/shells/zsh/platforms/detect.zsh"
[[ $DOTS_PLATFORM == termux && $is_termux == true && $distro == termux ]]
''')

    def test_color_arrays_and_terminal_capabilities(self):
        self.shell('''source "$DOTS/bin/colors.env"
(( ${#FG} == 256 && ${#BG} == 256 && ${#COLOR} == 256 )) || exit 1
for i in {0..255}; do
  [[ $FG[$i] == $'\\e'"[38;5;${i}m" ]] || exit 2
  [[ $BG[$i] == $'\\e'"[48;5;${i}m" ]] || exit 3
  [[ $COLOR[$i] == $'\\e'"[38;5;${i}mcolor $i" ]] || exit 4
done
[[ $BOLD == "$(tput bold)" && $rst == "$(tput sgr0)" ]] || exit 5
names=(BLACK RED GREEN YELLOW BLUE MAGENTA CYAN GREY BRIGHTBLACK BRIGHTRED BRIGHTGREEN BRIGHTYELLOW BRIGHTBLUE BRIGHTMAGENTA BRIGHTCYAN WHITE)
for i in {1..16}; do [[ ${(P)names[$i]} == "$(tput setaf $((i-1)))" ]] || exit 6; done
before=$RED
source "$DOTS/bin/colors.env"
[[ $RED == $before ]]
''')

    def generator(self, content):
        p = self.root / 'generator'
        p.write_text('#!' + ZSH + '\n' + content)
        p.chmod(0o700)
        return p

    def test_generated_cache_reuses_and_invalidates_arguments(self):
        self.generator('print run >> "$HOME/count"\nprint -r -- "typeset -g fixture_value=${1:-one}"\n')
        self.shell('''source "$DOTS/shells/zsh/core/cache.zsh"
_dots_source_generated test "$HOME/generator" one
[[ $fixture_value == one ]] || exit 1
_dots_source_generated test "$HOME/generator" one
[[ $(<"$HOME/count") == run ]] || exit 2
_dots_source_generated test "$HOME/generator" two
[[ $fixture_value == two ]] || exit 3
[[ $(<"$HOME/count") == $'run\\nrun' ]] || exit 4
''')

    def test_failed_generator_does_not_publish_or_evaluate_partial_output(self):
        self.generator('print "typeset -g should_not_exist=yes"\nexit 1\n')
        self.shell('''source "$DOTS/shells/zsh/core/cache.zsh"
_dots_source_generated test "$HOME/generator" && exit 1
[[ -z ${should_not_exist:-} ]] || exit 2
files=("$XDG_CACHE_HOME"/dots/zsh/**/*(N.))
(( ${#files} == 0 ))
''')

    def test_cache_executable_replacement_and_unwritable_location(self):
        self.generator('print "typeset -g fixture_value=one"\n')
        self.shell('source "$DOTS/shells/zsh/core/cache.zsh"; _dots_source_generated test "$HOME/generator"')
        self.generator('print "typeset -g fixture_value=replaced"\n')
        self.shell('''source "$DOTS/shells/zsh/core/cache.zsh"
_dots_source_generated test "$HOME/generator"
[[ $fixture_value == replaced ]] || exit 1
print blocked > "$HOME/blocked"
XDG_CACHE_HOME="$HOME/blocked/child"
_dots_source_generated test "$HOME/generator"
[[ $fixture_value == replaced ]]
''')

    def test_noninteractive_startup_has_no_external_command_dependency(self):
        self.shell('''path=()
source "$DOTS/shells/zsh/zshenv"
[[ -n $DOTS_PLATFORM && -n $distro && -n ${functions[is_wsl]} ]]
''')

    def test_shellmod_uses_running_shell_and_corrected_alias(self):
        self.shell('''source "$DOTS/bin/util"
SHELL=/bin/bash
# Minimal prerequisites, with optional tool probes absent.
has() { return 1; }
typeset -A dot shells
shellmod aliases
[[ $aliases[ll] == 'ls -la' && $aliases[rl] == rlp ]]
''')

    def test_invalid_generated_syntax_is_not_evaluated(self):
        self.generator('print "typeset -g should_not_exist=yes; if"\n')
        self.shell('''source "$DOTS/shells/zsh/core/cache.zsh"
_dots_source_generated test "$HOME/generator" && exit 1
[[ -z ${should_not_exist:-} ]]
''')

    def test_vivid_cache_tracks_theme_and_file_changes(self):
        exe = self.root / 'vivid'
        exe.write_text('#!' + ZSH + '\nprint run >> "$HOME/vivid.calls"\nprint -r -- "colors:$2"\n')
        exe.chmod(0o700)
        self.shell('''path=("$HOME" $path)
source "$DOTS/shells/zsh/core/cache.zsh"
_dots_vivid_colors mocha
[[ $REPLY == colors:mocha ]] || exit 1
_dots_vivid_colors mocha
[[ $(<"$HOME/vivid.calls") == run ]] || exit 2
mkdir -p "$XDG_CONFIG_HOME/vivid/themes"
print changed > "$XDG_CONFIG_HOME/vivid/themes/mocha.yml"
_dots_vivid_colors mocha
[[ $(<"$HOME/vivid.calls") == $'run\\nrun' ]] || exit 3
_dots_vivid_colors latte
[[ $REPLY == colors:latte ]]
''')

    def test_cache_does_not_replace_standard_file_commands(self):
        self.shell('''source "$DOTS/shells/zsh/core/cache.zsh"
(( ! ${+builtins[rm]} && ! ${+builtins[mv]} && ! ${+builtins[mkdir]} ))
''')

    def test_nvm_default_and_integration_readiness(self):
        nvm = self.root / '.nvm'
        nvm.mkdir()
        (nvm / 'nvm.sh').write_text('typeset -g NVM_FIXTURE_READY=yes\n')
        self.shell('''source "$DOTS/bin/util"
has() { return 1; }
source "$DOTS/shells/zsh/integrations/tools.zsh"
[[ $NVM_DIR == "$HOME/.nvm" && $NVM_FIXTURE_READY == yes ]]
''')

    def test_startup_without_optional_tools_or_plugins(self):
        from zsh_fixture import fixture, run
        root, repo, env = fixture(plugins=False)
        self.addCleanup(shutil.rmtree, root)
        relocated = root / '- dotfiles ü'
        repo.rename(relocated)
        repo = relocated
        env['DOTS'] = str(repo)
        for name in ('zshenv', 'zshrc'):
            link = Path(env['HOME']) / ('.' + name)
            link.unlink()
            link.symlink_to(repo / 'shells/zsh' / name)
        minimal = root / 'minimal-bin'
        minimal.mkdir()
        for name in ('zsh', 'mkdir', 'rm', 'mv'):
            exe = shutil.which(name)
            (minimal / name).symlink_to(exe)
        env['PATH'] = str(minimal)
        for name in ('batpipe', 'batman'):
            (repo / 'scripts' / name).unlink()
        (Path(env['HOME']) / '.fzf.zsh').unlink()
        p = run(env, '''[[ $aliases[ll] == 'ls -la' ]] || exit 1
[[ -n ${functions[reload-completions]} && -n ${functions[is_termux]} ]] || exit 2
[[ ${_DOTS_COMPINIT_READY:-} == 1 ]] || exit 3
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('command not found', p.stderr)

    def test_plugin_paths_keep_prefix_and_appended_provider_order(self):
        self.shell('''source "$DOTS/shells/zsh/integrations/plugins.zsh"
typeset -U fpath
fpath=(core system)
_dots_plugin_setup() { fpath=(cache manager $fpath); }
_dots_load_plugin() { fpath+=(provider); }
_dots_completion_plugins
before="${(j.:.)fpath}"
fpath=(core $fpath)
_dots_completion_plugins
[[ "${(j.:.)fpath}" == "$before" ]]
''')

    def test_theme_switch_and_repeat_preserve_palette_and_fzf_options(self):
        shutil.copytree(REPO / 'lib/dots', self.repo / 'lib/dots')
        for command in (REPO / 'bin').glob('dots-themes*'):
            shutil.copy2(command, self.repo / 'bin' / command.name)
        shutil.copytree(REPO / 'themes/catppuccin/flavors', self.repo / 'themes/catppuccin/flavors')
        shutil.copy2(REPO / 'themes/catppuccin/theme.toml', self.repo / 'themes/catppuccin/theme.toml')
        (self.repo / 'themes/bin').mkdir()
        shutil.copy2(REPO / 'themes/bin/theme', self.repo / 'themes/bin/theme')
        src = self.repo / 'themes/catppuccin/src'
        src.mkdir(parents=True)
        (src / 'fzf.zsh').write_text('FZF_DEFAULT_OPTS+=" --color=$FLAVOR"\n')
        (self.repo / 'themes/.default').write_text('catppuccin-mocha\n')
        self.shell('''source "$DOTS/bin/util"
typeset -A themes
themes[root]="$DOTS/themes"
source "$DOTS/themes/bin/theme"
source "$DOTS/shells/zsh/fzf.zsh"
current_theme() { print -r -- "typeset -g PALETTE_FLAVOR=$FLAVOR"; }
_dots_vivid_colors() { REPLY="colors:$1"; }
ok() { :; }
set_theme
[[ $catppuccin_flavor == mocha && $LS_COLORS == colors:catppuccin-mocha ]] || exit 1
before=$FZF_DEFAULT_OPTS
set_theme
[[ $FZF_DEFAULT_OPTS == $before ]] || exit 2
set_theme catppuccin-latte
[[ $catppuccin_flavor == latte && $LS_COLORS == colors:catppuccin-latte ]] || exit 3
[[ $FZF_DEFAULT_OPTS != *mocha* && $FZF_DEFAULT_OPTS == *latte* ]]
''')

    def test_syntax(self):
        files = list((self.repo / 'shells/zsh').rglob('*.zsh'))
        files += [self.repo / 'shells/zsh/zshenv', self.repo / 'shells/zsh/zshrc',
                  self.repo / 'bin/colors.env', self.repo / 'bin/util']
        for file in files:
            p = subprocess.run([ZSH, '-dfn', str(file)], env=self.env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, str(file) + p.stderr)


if __name__ == '__main__':
    unittest.main()
