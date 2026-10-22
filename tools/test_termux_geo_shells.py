#!/usr/bin/env python3
"""Termux-local completion discovery in native shells, using disposable roots."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import test_shell_init

REPO = Path(__file__).resolve().parents[1]


class LocalCompletions(unittest.TestCase):
    def setUp(self):
        self.fixture = test_shell_init.InitTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.repo, self.home, self.env = (
            getattr(self.fixture, n) for n in ('root', 'repo', 'home', 'env'))
        self.env['DOTS_TERMUX_AUTOSTART'] = '0'
        self.env['TERMUX_VERSION'] = 'fixture'
        android = self.repo / 'androidots'
        (android / 'bin').mkdir(parents=True)
        shutil.copy2(REPO / 'androidots/bin/termux-geo', android / 'bin/termux-geo')
        shutil.copytree(REPO / 'androidots/lib/termux_geo', android / 'lib/termux_geo')
        p = subprocess.run([str(android / 'bin/termux-geo'), 'completion', '--all', '--install'],
                           env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        # Fail visibly if any shell/completion tries to run the command.
        (android / 'bin/termux-geo').write_text('#!/bin/sh\necho BAD_GEO_EXECUTION >&2\nexit 99\n')
        self.fixture.minimal_tools()
        self.env['PATH'] += ':' + str(android / 'bin')
        self.env['TMPDIR'] = str(self.root)

    def shell(self, name, code, interactive=True):
        p = self.fixture.shell(name, code, interactive)
        self.assertNotIn('BAD_GEO_EXECUTION', p.stdout + p.stderr)
        return p

    def test_bash_local_base_preserves_user_paths_and_autoloads(self):
        p = self.shell('bash', r'''
DOTS_PLATFORM=termux
source "$DOTS/bin/lib/common.sh"
declare -A dots_options
BASH_COMPLETION_USER_DIR="$HOME/custom one:$HOME/custom two"
source "$DOTS/shells/bash/core/completion.bash"
source "$DOTS/shells/bash/core/completion.bash"
[[ $BASH_COMPLETION_USER_DIR == "$DOTS/androidots/shells/bash:$HOME/custom one:$HOME/custom two" ]] || exit 1
_dots_bash_tool_completion termux-geo || exit 2
complete -p termux-geo || exit 3
COMP_WORDS=(termux-geo --provider g); COMP_CWORD=2
_termux_geo
[[ ${COMPREPLY[*]} == gps ]] || exit 4
''')
        self.assertIn('_termux_geo', p.stdout)

    def test_bash_default_fallback_and_non_termux(self):
        self.shell('bash', r'''
DOTS_PLATFORM=termux
source "$DOTS/bin/lib/common.sh"
declare -A dots_options
source "$DOTS/shells/bash/core/completion.bash"
[[ $BASH_COMPLETION_USER_DIR == "$DOTS/androidots/shells/bash:$XDG_DATA_HOME/bash-completion" ]] || exit 1
DOTS_PLATFORM=linux
BASH_COMPLETION_USER_DIR="$HOME/custom"
_dots_bash_local_completion_path
[[ $BASH_COMPLETION_USER_DIR == "$HOME/custom" ]]
''')
        self.shell('bash', r'''
DOTS_PLATFORM=termux
source "$DOTS/bin/lib/common.sh"
declare -A dots_options
BASH_COMPLETION_USER_DIR="$HOME/custom"
source "$DOTS/shells/bash/core/completion.bash"
[[ $BASH_COMPLETION_USER_DIR == "$HOME/custom" ]]
''', interactive=False)

    def test_zsh_registered_before_compinit_and_unique(self):
        self.shell('zsh', r'''
source "$DOTS/shells/zsh/platforms/termux.zsh"
source "$DOTS/shells/zsh/platforms/termux.zsh"
[[ ${fpath[1]} == "$DOTS/androidots/shells/zsh/completions" ]] || exit 1
local -a matches=("${(@M)fpath:#$DOTS/androidots/shells/zsh/completions}")
(( ${#matches} == 1 )) || exit 2
autoload -Uz compinit
compinit -D
[[ ${_comps[termux-geo]} == _termux-geo ]] || exit 3
autoload +X _termux-geo || exit 4
''')

    def test_fish_local_discovery_and_idempotence(self):
        p = self.shell('fish', r'''
source "$DOTS/shells/fish/init.fish"
source "$DOTS/shells/fish/init.fish"
test "$fish_complete_path[1]" = "$DOTS/androidots/shells/fish/completions"; or exit 1
test (count (string match -- "$DOTS/androidots/shells/fish/completions" $fish_complete_path)) -eq 1; or exit 2
complete -C 'termux-geo get post'
''')
        self.assertIn('postcode', p.stdout)

    def test_fish_non_termux_and_noninteractive_exclusion(self):
        self.env.pop('TERMUX_VERSION', None)
        self.env.pop('TERMUX__PREFIX', None)
        self.env['PREFIX'] = str(self.root / 'linux')
        for interactive in (True, False):
            self.shell('fish', r'''
source "$DOTS/shells/fish/init.fish"
not contains -- "$DOTS/androidots/shells/fish/completions" $fish_complete_path
''', interactive=interactive)

    def test_missing_androidots_does_not_register_paths(self):
        shutil.rmtree(self.repo / 'androidots')
        self.shell('zsh', r'''
source "$DOTS/shells/zsh/platforms/termux.zsh"
[[ ${fpath[(Ie)$DOTS/androidots/shells/zsh/completions]} == 0 ]]
''')
        self.shell('fish', r'''
source "$DOTS/shells/fish/init.fish"
not contains -- "$DOTS/androidots/shells/fish/completions" $fish_complete_path
''')


if __name__ == '__main__':
    unittest.main()
