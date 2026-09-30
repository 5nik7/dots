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

    def tmux_stub(self):
        # No real tmux executable/server is ever used. Each invocation is logged
        # as NUL-separated argv with an empty record terminator.
        self.env['TMUX_LOG'] = str(self.root / 'tmux.log')
        self.env['TMUX_CHECKS'] = str(self.root / 'tmux.checks')
        self.stub('tmux', r'''printf '%s\0' "$@" >> "$TMUX_LOG"
printf '\0' >> "$TMUX_LOG"
case $1 in
  has-session)
    count=0
    [[ ! -f $TMUX_CHECKS ]] || read -r count < "$TMUX_CHECKS"
    count=$((count + 1))
    printf '%s\n' "$count" > "$TMUX_CHECKS"
    case $TMUX_CASE in
      existing|switch-error) exit 0 ;;
      race) (( count > 1 )) && exit 0 ;;
    esac
    exit 1 ;;
  new-session)
    case $TMUX_CASE in
      race) printf 'duplicate session\n' >&2; exit 1 ;;
      create-error) printf 'create denied\n' >&2; exit 23 ;;
      attach-error) printf 'attach denied\n' >&2; exit 24 ;;
    esac ;;
  switch-client)
    if [[ $TMUX_CASE == switch-error ]]; then
      printf 'switch denied\n' >&2; exit 25
    fi ;;
  *) printf 'unexpected tmux command\n' >&2; exit 99 ;;
esac
''')

    def tmux_run(self, shell, invocation='t', *, inside=False, case='existing',
                 status=0, prefix=''):
        self.env['TMUX'] = 'fixture-server,123,0' if inside else ''
        self.env['TMUX_CASE'] = case
        for name in ('tmux.log', 'tmux.checks'):
            (self.root / name).unlink(missing_ok=True)
        proc = self.shell(shell, self.shared() + prefix + '\n' + invocation +
                          f'\nresult=$?\n[[ $result == {status} ]] || '
                          '{ printf "unexpected status: %s\\n" "$result" >&2; exit 90; }\n')
        log = self.root / 'tmux.log'
        calls = []
        if log.exists():
            calls = [record.decode().split('\0')
                     for record in log.read_bytes().split(b'\0\0') if record]
        return proc, calls

    def test_tmux_outside_default_names_and_quoting(self):
        self.tmux_stub()
        for shell in ('bash', 'zsh'):
            for session in (None, 'Work', 'Work other', '-dash', 'équipe 日本',
                            'quote\' " $HOME $(touch injected) * ? [x] ;'):
                with self.subTest(shell=shell, session=session):
                    self.env['SESSION_NAME'] = session or ''
                    proc, calls = self.tmux_run(
                        shell, 't' if session is None else 't "$SESSION_NAME"')
                    self.assertEqual(calls, [['new-session', '-A', '-s',
                                             session or 'Work', '-c', str(self.home)]])
                    self.assertEqual(proc.stdout + proc.stderr, '')
                    self.assertFalse((self.home / 'injected').exists())

    def test_tmux_infers_project_root_and_explicit_name_skips_git(self):
        self.tmux_stub()
        self.stub('git', '''printf 'git\\n' >> "$HOME/git-calls"
[[ $* == 'rev-parse --show-toplevel' ]] || exit 90
printf '%s\\n' "$TEST_PROJECT_ROOT"
''')
        for shell in ('bash', 'zsh'):
            for folder, session in [('dots', 'dots'), ('my.project:ü', 'my-project-ü'),
                                    ('space project', 'space project'), ('-dash', '-dash')]:
                project = self.home / folder
                nested = project / 'src/nested'
                nested.mkdir(parents=True, exist_ok=True)
                self.env.update(TEST_PROJECT_ROOT=str(project), TEST_NESTED=str(nested))
                for inside in (False, True):
                    (self.home / 'git-calls').unlink(missing_ok=True)
                    proc, calls = self.tmux_run(shell, inside=inside, case='missing',
                                                prefix='builtin cd -- "$TEST_NESTED"')
                    if inside:
                        expected = [['has-session', '-t', '=' + session],
                                    ['new-session', '-d', '-s', session, '-c', str(project)],
                                    ['switch-client', '-t', '=' + session]]
                    else:
                        expected = [['new-session', '-A', '-s', session, '-c', str(project)]]
                    self.assertEqual(calls, expected)
                    self.assertEqual(proc.stdout + proc.stderr, '')
                    self.assertEqual((self.home / 'git-calls').read_text(), 'git\n')
                (self.home / 'git-calls').unlink()
                _, calls = self.tmux_run(shell, 't custom', prefix='builtin cd -- "$TEST_NESTED"')
                self.assertEqual(calls, [['new-session', '-A', '-s', 'custom', '-c', str(nested)]])
                self.assertFalse((self.home / 'git-calls').exists())

    def test_tmux_non_repository_falls_back_without_git_diagnostics(self):
        self.tmux_stub()
        self.stub('git', "printf 'fatal: not a repository\\n' >&2; exit 128\n")
        for shell in ('bash', 'zsh'):
            proc, calls = self.tmux_run(shell)
            self.assertEqual(calls, [['new-session', '-A', '-s', 'Work', '-c', str(self.home)]])
            self.assertEqual(proc.stdout + proc.stderr, '')
        # The fixture PATH contains no Git once the mock is removed.
        (self.root / 'tools/git').unlink()
        for shell in ('bash', 'zsh'):
            proc, calls = self.tmux_run(shell)
            self.assertEqual(calls, [['new-session', '-A', '-s', 'Work', '-c', str(self.home)]])
            self.assertEqual(proc.stdout + proc.stderr, '')

    def test_tmux_rejects_invalid_arguments_before_execution(self):
        self.tmux_stub()
        for shell in ('bash', 'zsh'):
            invalid = ['', 'a:b', 'a.b'] + [f'a{chr(n)}b' for n in (*range(1, 32), 127)]
            for session in invalid:
                with self.subTest(shell=shell, session=repr(session)):
                    self.env['SESSION_NAME'] = session
                    proc, calls = self.tmux_run(shell, 't "$SESSION_NAME"', status=2)
                    self.assertEqual(calls, [])
                    self.assertEqual(proc.stdout, '')
                    self.assertIn('Usage: t [session-name]', proc.stderr)
            proc, calls = self.tmux_run(shell, 't first second', status=2)
            self.assertEqual(calls, [])
            self.assertEqual(proc.stdout, '')
            self.assertIn('Usage: t [session-name]', proc.stderr)

    def test_tmux_inside_exact_existing_and_new_sessions(self):
        self.tmux_stub()
        for shell in ('bash', 'zsh'):
            for session in ('Work', '-dash', 'space ü', 'Work*', '=literal'):
                for case in ('existing', 'missing'):
                    with self.subTest(shell=shell, session=session, case=case):
                        self.env['SESSION_NAME'] = session
                        proc, calls = self.tmux_run(shell, 't "$SESSION_NAME"',
                                                    inside=True, case=case)
                        expected = [['has-session', '-t', '=' + session]]
                        if case == 'missing':
                            expected += [['new-session', '-d', '-s', session,
                                          '-c', str(self.home)]]
                        expected += [['switch-client', '-t', '=' + session]]
                        self.assertEqual(calls, expected)
                        self.assertEqual(proc.stdout + proc.stderr, '')
            _, calls = self.tmux_run(shell, inside=True)
            self.assertEqual(calls, [['has-session', '-t', '=Work'],
                                     ['switch-client', '-t', '=Work']])

    def test_tmux_failures_and_concurrent_creation(self):
        self.tmux_stub()
        has = ['has-session', '-t', '=Work']
        create = ['new-session', '-d', '-s', 'Work', '-c', str(self.home)]
        switch = ['switch-client', '-t', '=Work']
        for shell in ('bash', 'zsh'):
            for case, inside, status, diagnostic, expected in (
                ('attach-error', False, 24, 'attach denied',
                 [['new-session', '-A', '-s', 'Work', '-c', str(self.home)]]),
                ('switch-error', True, 25, 'switch denied', [has, switch]),
                ('create-error', True, 23, 'create denied', [has, create, has]),
                ('race', True, 0, 'duplicate session', [has, create, has, switch]),
            ):
                with self.subTest(shell=shell, case=case):
                    proc, calls = self.tmux_run(shell, inside=inside, case=case, status=status)
                    self.assertEqual(calls, expected)
                    self.assertEqual(proc.stdout, '')
                    self.assertIn(diagnostic, proc.stderr)

    def test_tmux_missing_command_and_old_alias_reload(self):
        for shell in ('bash', 'zsh'):
            # Empty PATH makes the missing-tool case independent of host tools.
            proc = self.shell(shell, self.shared() + '''
PATH=''
t > "$HOME/t-out" 2> "$HOME/t-err"
[[ $? == 127 ]] || exit 1
[[ ! -s $HOME/t-out ]] || exit 2
''')
            self.assertIn('tmux not found', (self.home / 't-err').read_text())
        self.tmux_stub()
        for shell in ('bash', 'zsh'):
            enable = 'setopt aliases' if shell == 'zsh' else 'shopt -s expand_aliases'
            prefix = enable + '\n'
            for _ in range(3):
                prefix += '''alias t='printf LEGACY; false'
source "$DOTS/shells/shared/functions.sh" || exit 1
source "$DOTS/shells/shared/aliases.sh" || exit 2
alias t >/dev/null 2>&1 && exit 3
typeset -f t >/dev/null || exit 4
'''
            proc, calls = self.tmux_run(shell, "eval 't'", prefix=prefix)
            self.assertEqual(calls, [['new-session', '-A', '-s', 'Work', '-c', str(self.home)]])
            self.assertEqual(proc.stdout + proc.stderr, '')

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
