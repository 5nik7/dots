#!/usr/bin/env python3
"""User-local completion discovery and precedence in disposable native shells."""
from pathlib import Path
import unittest
import test_shell_init


class LocalCompletions(unittest.TestCase):
    def setUp(self):
        self.fixture = test_shell_init.InitTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.minimal_tools()
        self.repo, self.home, self.env = (
            getattr(self.fixture, name) for name in ('repo', 'home', 'env'))
        self.env['DOTS_TERMUX_AUTOSTART'] = '0'
        self.env['DOTS_ZSH_SUGGESTIONS'] = 'none'
        self.env['XDG_DATA_HOME'] = str(self.home / '-data space ü [1]')
        self.env['XDG_CONFIG_HOME'] = str(self.home / '-config space ü [1]')

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def shell(self, name, code, interactive=True):
        return self.fixture.shell(name, code, interactive)

    def test_zsh_local_discovery_precedence_export_and_reload(self):
        local = Path(self.env['XDG_DATA_HOME']) / 'zsh/site-functions'
        repo = self.repo / 'shells/zsh/completions'
        for directory, value in ((local, 'local'), (repo, 'repository')):
            self.write(directory / '_dots_local_probe',
                       '#compdef dots-local-probe\nprint -r -- ' + value + '\n')
        self.write(repo / '_dots_fallback_probe',
                   '#compdef dots-fallback-probe\nprint -r -- fallback\n')
        self.shell('zsh', r'''
source "$DOTS/shells/zsh/zshrc"
[[ $fpath[1] == "$XDG_DATA_HOME/zsh/site-functions" ]] || exit 1
[[ $_comps[dots-local-probe] == _dots_local_probe ]] || exit 2
autoload +X _dots_local_probe _dots_fallback_probe
[[ $(_dots_local_probe) == local && $(_dots_fallback_probe) == fallback ]] || exit 3
[[ $(bash --noprofile --norc -c 'printf %s "$FPATH"') == "$FPATH" ]] || exit 4
[[ ${path[(Ie)$ZSHCOMP]} == 0 && ${path[(Ie)$HOME/.local/bin]} != 0 ]] || exit 5
source "$DOTS/shells/zsh/zshrc"
local count=0 entry
for entry in "${fpath[@]}"; do
  [[ $entry != "$XDG_DATA_HOME/zsh/site-functions" ]] || (( ++count ))
done
(( count == 1 )) || exit 6
fpath=("$ZSHCOMP" "${fpath[@]}")
_dots_zsh_reload_completions
[[ $fpath[1] == "$XDG_DATA_HOME/zsh/site-functions" ]] || exit 7
''')

    def test_zsh_home_fallback_missing_and_noninteractive(self):
        local = self.home / '.local/share/zsh/site-functions'
        local.mkdir(parents=True)
        self.shell('zsh', r'''
unset XDG_DATA_HOME
source "$DOTS/shells/zsh/core/completion.zsh"
[[ $fpath[1] == "$HOME/.local/share/zsh/site-functions" ]] || exit 1
''')
        self.shell('zsh', r'''
before=$FPATH
source "$DOTS/shells/zsh/core/completion.zsh"
[[ $FPATH == "$before" ]]
''')
        self.shell('zsh', r'''
unset XDG_DATA_HOME
before=$FPATH
source "$DOTS/shells/zsh/zshenv"
[[ $FPATH == "$before" ]]
''', interactive=False)
        self.assertFalse((Path(self.env['XDG_DATA_HOME']) / 'zsh').exists())

    def bash_setup(self):
        return r'''
source "$DOTS/bin/lib/common.sh"
declare -A dots_options
source "$DOTS/shells/bash/core/completion.bash"
'''

    def test_bash_custom_local_android_order_and_lazy_loading(self):
        local = Path(self.env['XDG_DATA_HOME']) / 'bash-completion'
        android = self.repo / 'androidots/shells/bash'
        custom = self.home / 'custom space ü [1]'
        for directory, value in ((custom, 'custom'), (local, 'local'), (android, 'android')):
            self.write(directory / 'completions/dots-local-probe.bash',
                       '_dots_local_probe() { COMPREPLY=(' + value + '); }\n'
                       'complete -F _dots_local_probe dots-local-probe\n')
        self.shell('bash', r'''
DOTS_PLATFORM=termux
BASH_COMPLETION_USER_DIR="$DOTS/androidots/shells/bash:$HOME/custom space ü [1]:$HOME/custom space ü [1]"
''' + self.bash_setup() + r'''
before=$BASH_COMPLETION_USER_DIR
source "$DOTS/shells/bash/core/completion.bash"
[[ $BASH_COMPLETION_USER_DIR == "$HOME/custom space ü [1]:$XDG_DATA_HOME/bash-completion:$DOTS/androidots/shells/bash" ]] || exit 1
[[ $BASH_COMPLETION_USER_DIR == "$before" ]] || exit 2
_dots_bash_tool_completion dots-local-probe || exit 3
_dots_local_probe; [[ ${COMPREPLY[*]} == custom ]] || exit 4
unset BASH_COMPLETION_USER_DIR
_dots_bash_local_completion_path
complete -r dots-local-probe; unset -f _dots_local_probe
_dots_bash_tool_completion dots-local-probe || exit 5
_dots_local_probe; [[ ${COMPREPLY[*]} == local ]] || exit 6
''')

    def test_bash_linux_home_fallback_missing_loader_and_noninteractive(self):
        self.shell('bash', 'DOTS_PLATFORM=linux\nunset XDG_DATA_HOME\n' + self.bash_setup() + r'''
[[ $BASH_COMPLETION_USER_DIR == "$HOME/.local/share/bash-completion" ]] || exit 1
''')
        self.shell('bash', self.bash_setup() + r'''
before=$PATH
PREFIX="$HOME/no-prefix"
unset _DOTS_BASH_COMPLETION_BASE_READY
_dots_bash_completion_base || exit 1
[[ $PATH == "$before" ]] || exit 2
''')
        self.shell('bash', 'BASH_COMPLETION_USER_DIR="$HOME/custom"\n' + self.bash_setup() + r'''
[[ $BASH_COMPLETION_USER_DIR == "$HOME/custom" ]]
''', interactive=False)
        self.assertFalse((self.home / '.local/share/bash-completion').exists())

    def test_fish_discovery_user_config_vendor_repository_order(self):
        config = Path(self.env['XDG_CONFIG_HOME']) / 'fish/completions'
        vendor = Path(self.env['XDG_DATA_HOME']) / 'fish/vendor_completions.d'
        android = self.repo / 'androidots/shells/fish/completions'
        repo = self.repo / 'shells/fish/completions'
        for directory, value in ((config, 'config'), (vendor, 'vendor'),
                                 (android, 'android'), (repo, 'repository')):
            for name in ('dots-local-probe', 'dots-vendor-probe'):
                if directory == config and name == 'dots-vendor-probe':
                    continue
                self.write(directory / (name + '.fish'),
                           f'complete -c {name} -f -a {value}\n')
        self.env['TERMUX_VERSION'] = 'fixture'
        for name in ('dots-local-probe', 'dots-vendor-probe'):
            command = self.repo / 'bin' / name
            self.write(command, '#!/bin/sh\nexit 0\n')
            command.chmod(0o700)
        p = self.shell('fish', r'''
set -g fish_complete_path "$HOME/system completions" "$HOME/system completions"
source "$DOTS/shells/fish/init.fish"
set -l before $fish_complete_path
source "$DOTS/shells/fish/init.fish"
test (count $fish_complete_path) -eq 5; or exit 1
test "$fish_complete_path[1]" = "$XDG_CONFIG_HOME/fish/completions"; or exit 2
test "$fish_complete_path[2]" = "$XDG_DATA_HOME/fish/vendor_completions.d"; or exit 3
test "$fish_complete_path[3]" = "$DOTS/androidots/shells/fish/completions"; or exit 4
test "$fish_complete_path[4]" = "$DOTS/shells/fish/completions"; or exit 5
test "$fish_complete_path[5]" = "$HOME/system completions"; or exit 6
test (string join : -- $fish_complete_path) = (string join : -- $before); or exit 7
complete -C 'dots-local-probe '
complete -C 'dots-vendor-probe '
''')
        self.assertEqual(p.stdout.splitlines(), ['config', 'vendor'])

    def test_fish_home_fallback_missing_and_noninteractive(self):
        (self.home / '.local/share/fish/vendor_completions.d').mkdir(parents=True)
        self.env['XDG_DATA_HOME'] = ''
        self.shell('fish', r'''
set -gx XDG_DATA_HOME ''
source "$DOTS/shells/fish/init.fish"
set -l local_index (contains -i -- "$HOME/.local/share/fish/vendor_completions.d" $fish_complete_path)
set -l repo_index (contains -i -- "$DOTS/shells/fish/completions" $fish_complete_path)
test -n "$local_index"; and test "$local_index" -lt "$repo_index"
''')
        self.shell('fish', r'''
set -g fish_complete_path "$HOME/existing"
source "$DOTS/shells/fish/init.fish"
test (count $fish_complete_path) -eq 1; or exit 1
test "$fish_complete_path[1]" = "$HOME/existing"
''', interactive=False)


if __name__ == '__main__':
    unittest.main()
