#!/usr/bin/env python3
"""Shared interactive command and Bash adapter contracts in disposable roots."""
from pathlib import Path
import os
import shutil
import subprocess
import unittest
import test_shell_init
import test_themes

REPO = Path(__file__).resolve().parents[1]


class SharedShells(unittest.TestCase):
    def setUp(self):
        self.fixture = test_shell_init.InitTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.minimal_tools()
        for name in ('mktemp', 'find', 'head', 'grep', 'xargs', 'diff'):
            exe = shutil.which(name)
            if exe:
                (self.fixture.root / 'tools' / name).symlink_to(exe)
        self.root, self.repo, self.home, self.env = (getattr(self.fixture, n) for n in ('root', 'repo', 'home', 'env'))
        shutil.copy2(REPO / 'scripts/mkcd', self.repo / 'scripts/mkcd')

    def shell(self, name, code, interactive=False):
        return self.fixture.shell(name, code, interactive)

    def shared(self):
        return '''source "$DOTS/shells/environment.sh"
source "$DOTS/bin/lib/common.sh"
source "$DOTS/shells/shared/functions.sh"
source "$DOTS/shells/shared/aliases.sh"
'''

    def test_function_loading_preserves_aliases_and_expansion_mode(self):
        for shell in ('bash', 'zsh'):
            for enabled in (False, True):
                with self.subTest(shell=shell, aliases=enabled):
                    if shell == 'zsh':
                        setup = 'setopt aliases' if enabled else 'unsetopt aliases'
                        check = '[[ -o aliases ]]' if enabled else '[[ ! -o aliases ]]'
                    else:
                        setup = 'shopt -s expand_aliases' if enabled else 'shopt -u expand_aliases'
                        check = 'shopt -q expand_aliases' if enabled else '! shopt -q expand_aliases'
                    self.shell(shell, setup + '''
alias ga='printf BAD' mkcd='printf BAD' eff='printf BAD'
source "$DOTS/shells/shared/functions.sh" || exit 1
source "$DOTS/shells/shared/functions.sh" || exit 2
for name in ga mkcd eff; do
  typeset -f "$name" >/dev/null || exit 3
  [[ $(alias "$name") == *BAD* ]] || exit 4
done
''' + check)

    def test_commands_reload_and_navigation(self):
        for name in ('bash', 'zsh'):
            with self.subTest(shell=name):
                self.shell(name, self.shared() + self.shared() + '''
for name in mkcd rlp gup ga gd findfiles palette fixpath y yap eff reload-completions; do
  typeset -f "$name" >/dev/null || exit 1
done
alias ff | command grep _dots_file_picker || exit 2
mkcd 'space ü/-dash' || exit 3
[[ $PWD == "$HOME/space ü/-dash" ]] || exit 4
mkcd || result=$?
[[ $result == 1 ]] || exit 5
printf file > plain
mkcd plain && exit 6
[[ -f plain ]] || exit 7
mkcd -next || exit 8
[[ $PWD == */-next ]] || exit 9
'''.replace('alias ff | command grep _dots_file_picker || exit 2', "[[ $(alias ff) == *'_dots_file_picker'* ]] || exit 2"))

    def test_optional_aliases_fallback_and_activation(self):
        for name in ('bash', 'zsh'):
            self.shell(name, self.shared() + '''
[[ $(alias ll) == *'ls -la'* ]] || exit 1
function eza { printf '%s\\n' "$@"; }
function z { builtin cd -- "$@"; }
function zoxide { :; }
source "$DOTS/shells/shared/aliases.sh"
[[ $(alias ll) == *'eza -lh'* && $(alias cd) == *z** ]] || exit 2
unset -f eza z zoxide
source "$DOTS/shells/shared/aliases.sh"
[[ $(alias ll) == *'ls -la'* ]] || exit 3
alias cd >/dev/null 2>&1 && exit 4
true
''')

    def test_path_deduplication_and_diff_status(self):
        for name in ('bash', 'zsh'):
            self.shell(name, self.shared() + '''
function tput { :; }
function diff { printf 'different\\n'; return 1; }
colordiff a b >/dev/null
[[ $? == 1 ]] || exit 1
PATH='/first:/space ü:/first:/last'
fixpath
[[ $PATH == '/first:/space ü:/last' ]] || exit 2
''')

    def stub(self, name, body):
        p = self.root / 'tools' / name
        p.write_text('#!' + shutil.which('bash') + '\n' + body)
        p.chmod(0o700)
        return p

    def test_yazi_exit_cleanup_and_editor_cancel(self):
        self.stub('yazi', '''for arg; do case $arg in --cwd-file=*) target=${arg#*=};; esac; done
printf '%s\\n' "$HOME/destination ü" >| "$target"
exit "${YAZI_RESULT:-0}"
''')
        self.stub('fzf', 'exit 130\n')
        (self.home / 'destination ü').mkdir()
        for name in ('bash', 'zsh'):
            self.shell(name, "alias eff=must_not_execute\n" + self.shared() + '''
EDITOR=must_not_execute
function must_not_execute { exit 90; }
eff
[[ $? == 130 ]] || exit 1
YAZI_RESULT=7 y
[[ $? == 7 && $PWD == "$HOME" ]] || exit 2
y || exit 3
[[ $PWD == "$HOME/destination ü" ]] || exit 4
''')
        self.assertFalse(list(self.root.glob('yazi-cwd.*')))

    def test_bash_failed_and_new_tools_retry_and_local_override(self):
        mise = self.stub('mise', "printf '%s\\n' 'SHOULD_NOT_RUN=yes'; exit 1\n")
        (self.home / '.bash_aliases').write_text("alias ll='fixture-list'\n")
        code = self.fixture.generated('bash')
        self.shell('bash', code + '''
[[ ! ${SHOULD_NOT_RUN+x} && ! ${_DOTS_BASH_TOOL_READY[mise]+x} ]] || exit 1
[[ $(alias ll) == *fixture-list* ]] || exit 2
function mise { printf '%s\\n' 'MISE_COUNT=$(( ${MISE_COUNT:-0} + 1 ))'; }
''' + code + code + '''
[[ $MISE_COUNT == 1 && ${_DOTS_BASH_TOOL_READY[mise]} == 1 ]] || exit 3
[[ $- == *i* && $(set -o) == *'vi '* ]] || exit 4
''', interactive=True)

    def test_bash_prompt_status_and_composition(self):
        for initial in ("PROMPT_COMMAND='old_prompt'", "PROMPT_COMMAND=(old_prompt ':')"):
            self.shell('bash', '''function old_prompt { OLD_STATUS=$?; }
''' + initial + '\n' + self.fixture.generated('bash') + '''
function _dots_theme_precmd { return 0; }
false
_dots_bash_prompt
[[ $? == 1 ]] || exit 1
[[ ${PROMPT_COMMAND[*]} == *old_prompt* ]] || exit 2
before=${PROMPT_COMMAND[*]}
''' + self.fixture.generated('bash') + '''
[[ ${PROMPT_COMMAND[*]} == "$before" ]] || exit 3
''', interactive=True)

    def test_platform_detection_without_external_tools(self):
        for shell in ('bash', 'zsh'):
            self.shell(shell, '''PATH=''
TERMUX_VERSION=fixture
source "$DOTS/shells/shared/platform.sh"
[[ $DOTS_PLATFORM == termux && $(is_termux -v) == true ]] || exit 1
unset TERMUX_VERSION PREFIX TERMUX__PREFIX
_dots_detect_platform msys "$HOME/missing" "$HOME/missing" "$HOME/missing"
[[ $DOTS_PLATFORM == msys && $is_wsl == false ]] || exit 2
WSL_INTEROP=fixture
_dots_detect_platform linux "$HOME/missing" "$HOME/missing" "$HOME/missing"
[[ $DOTS_PLATFORM == wsl && $(is_wsl -v) == true ]]
''')

    def test_decoding_and_dynamic_alias_paths(self):
        for name in ('bash', 'zsh'):
            self.shell(name, self.shared() + '''
[[ -z ${BASH_VERSION:-} ]] || shopt -s expand_aliases
[[ $(urldecode 'hello%20world') == 'hello world' ]] || exit 1
[[ $(htmldecode '&#x41;') == A ]] || exit 2
alias .sb >/dev/null || exit 3
eval '.sb' || exit 4
[[ $PWD == "$SHELLS/bash" ]] || exit 5
PATH=':/a:/a:/b:'
fixpath
[[ $PATH == ':/a:/b' ]] || exit 6
''')

    def test_bash_completions_retry_and_explicit_refresh(self):
        self.stub('uv', "printf '%s\\n' 'SHOULD_NOT_RUN=yes'; exit 1\n")
        code = self.fixture.generated('bash')
        self.shell('bash', code + '''
[[ ! ${SHOULD_NOT_RUN+x} && ! ${_DOTS_BASH_COMPLETION_READY[uv]+x} ]] || exit 1
function uv { printf '%s\\n' 'UV_COUNT=$(( ${UV_COUNT:-0} + 1 ))'; }
''' + code + code + '''
[[ $UV_COUNT == 1 ]] || exit 2
reload-completion uv || exit 3
[[ $UV_COUNT == 2 ]] || exit 4
reload-completion command-without-provider 2>/dev/null && exit 5
true
''', interactive=True)

    def test_bash_runtime_files_and_private_module_boundary(self):
        nvm=self.home / '.nvm'
        nvm.mkdir()
        (nvm / 'nvm.sh').write_text('NVM_COUNT=$(( ${NVM_COUNT:-0} + 1 ))\n')
        (nvm / 'bash_completion').write_text('NVM_COMPLETION=yes\n')
        cargo=self.home / '.cargo'
        cargo.mkdir()
        (cargo / 'env').write_text('export CARGO_FIXTURE=yes\n')
        rbenv=self.home / '.rbenv/bin/rbenv'
        rbenv.parent.mkdir(parents=True)
        rbenv.write_text('#!' + shutil.which('bash') + "\n[[ $* == 'init - --no-rehash bash' ]] || exit 2\nprintf '%s\\n' 'RBENV_COUNT=$(( ${RBENV_COUNT:-0} + 1 ))'\n")
        rbenv.chmod(0o700)
        private=self.repo / 'secrets'
        private.mkdir()
        for name in ('secrets.env', 'secrets.sh'):
            (private / name).write_text('PRIVATE_MUST_NOT_LOAD=yes\n')
        hook=self.fixture.generated('bash')
        self.shell('bash',hook + hook + '''
[[ $NVM_COUNT == 1 && $NVM_COMPLETION == yes && $RBENV_COUNT == 1 && $CARGO_FIXTURE == yes ]] || exit 1
[[ ! ${PRIVATE_MUST_NOT_LOAD+x} ]] || exit 2
''',interactive=True)

    def test_bash_theme_refresh_builtin_unchanged_path(self):
        theme = test_themes.Themes()
        theme.setUp()
        self.addCleanup(theme.doCleanups)
        theme.dots('theme', 'set', 'nord')
        theme.shell('''source "$DOTS/lib/dots/themes/shell.bash"
set_theme || exit 1
[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#81a1c1' ]] || exit 2
function readlink { printf 'UNEXPECTED READLINK\\n' >&2; return 99; }
false
_dots_theme_precmd
[[ $? == 1 ]] || exit 3
unset -f readlink
"$DOTS/bin/dots-theme-set" catppuccin-latte >/dev/null || exit 4
false
_dots_theme_precmd
[[ $? == 1 && $GUM_CONFIRM_PROMPT_FOREGROUND == '#1e66f5' ]] || exit 5
''')


if __name__ == '__main__':
    unittest.main()
