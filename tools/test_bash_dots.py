#!/usr/bin/env python3
"""Owned-root tests for the Bash dispatcher; never execute installed extensions."""
import json
import os
import pty
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
ZSH = shutil.which('zsh')
FISH = shutil.which('fish')


class DotsFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-bash-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo space ü'
        (self.repo / 'bin').mkdir(parents=True)
        shutil.copy2(REPO / 'bin/dots', self.repo / 'bin/dots')
        shutil.copytree(REPO / 'lib/dots', self.repo / 'lib/dots')
        self.home = self.root / 'home'
        self.home.mkdir()
        self.env = {'HOME': str(self.home), 'DOTS': str(self.repo),
                    'PATH': str(self.repo / 'bin') + os.pathsep + str(Path(BASH).parent) + ':/usr/bin:/bin',
                    'TERM': 'xterm-256color', 'TMPDIR': str(self.root),
                    'XDG_CACHE_HOME': str(self.home / 'cache'),
                    'XDG_CONFIG_HOME': str(self.home / 'config'),
                    'XDG_DATA_HOME': str(self.home / 'data'),
                    'XDG_STATE_HOME': str(self.home / 'state'), 'ZDOTDIR': str(self.home)}
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']

    def command(self, name='themes', header='', body=None, directory=None):
        directory = directory or self.repo / 'bin'
        directory.mkdir(parents=True, exist_ok=True)
        p = directory / ('dots-' + name)
        p.write_text('#!' + BASH + '\n' + header + '\n' + (body or 'printf "<%s>\\n" "$@"\n'))
        p.chmod(0o700)
        return p

    def run_dots(self, *args, code=0, env=None):
        p = subprocess.run([str(self.repo / 'bin/dots'), *args], cwd=self.home,
                           env=env or self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(p.returncode, code, (args, p.stdout, p.stderr))
        return p

    def shell(self, executable, code):
        flags = ['--noprofile', '--norc'] if executable == BASH else ['-df'] if executable == ZSH else ['--no-config']
        p = subprocess.run([executable, *flags, '-c', code], cwd=self.home,
                           env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return p

    def complete(self, *words):
        p = self.run_dots('__complete', 'bash', str(len(words)), '--', 'dots', *words)
        return [line.split('\t') for line in p.stdout.splitlines()]

    def hints(self):
        return self.command(header='''# dots:summary=Manage themes
# dots:usage=[OPTIONS] DIRECTORY
# dots:example=dots themes --flavor mocha .
# dots:option=--flavor|-f|choice:mocha,latte|Palette flavor
# dots:option=--output|-o|file|Destination file
# dots:option=--verbose|-v|flag|Verbose output
# dots:option=--pick||choice:two words,evil$(touch marker)|Literal choice
# dots:argument=1|directory|Theme directory
# dots:argument=*|choice:yes,no|Extra choices''')

    def test_legacy_help_directory_and_inferred_root(self):
        self.assertIn('Usage', self.run_dots('--help').stdout)
        self.assertEqual(self.run_dots('--raw', '--dir').stdout.strip(), str(self.repo))
        env = dict(self.env, DOTS=str(self.home / 'dots'))
        self.assertEqual(self.run_dots('--dir', env=env).stdout, '~/dots\n')
        env.pop('DOTS')
        self.assertEqual(self.run_dots('--dir', env=env).stdout.strip(), str(self.repo))
        link = self.root / 'linked-dots'
        link.symlink_to(self.repo / 'bin/dots')
        p = subprocess.run([str(link), '--raw', '--dir'], env=env, text=True, capture_output=True)
        self.assertEqual(p.stdout.strip(), str(self.repo))

    def test_longest_route_literal_argv_streams_and_exit(self):
        self.command('themes')
        self.command('themes-apply', body='printf "<%s>\\n" "$@"; printf error >&2; exit 23')
        p = self.run_dots('themes', 'apply', 'two words', '', '*', '$(touch nope)', '--', '--help', code=23)
        self.assertEqual(p.stdout, '<two words>\n<>\n<*>\n<$(touch nope)>\n<-->\n<--help>\n')
        self.assertEqual(p.stderr, 'error')
        self.assertFalse((self.home / 'nope').exists())

    def test_root_discovery_duplicates_and_explicit_root(self):
        self.command('themes', directory=self.repo / 'local/bin')
        self.assertEqual(self.run_dots('themes', 'ok').stdout, '<ok>\n')
        self.command('themes')
        self.run_dots('themes', code=1)
        self.run_dots('commands', '--check', code=1)
        (self.repo / 'bin/dots-themes').unlink()
        extra = self.root / 'extra space'
        self.command('hello', directory=extra)
        self.assertEqual(self.run_dots('--command-dir', str(extra), 'hello', 'x').stdout, '<x>\n')
        self.run_dots('hello', code=1)
        self.run_dots('--command-dir', 'relative', code=2)
        self.run_dots('--command-dir', str(self.repo / 'local/bin'), 'themes')

    def test_symlink_and_broken_or_nonexecutable_deeper_route(self):
        target = self.command('source')
        (self.repo / 'bin/dots-themes').symlink_to(target)
        self.run_dots('themes')
        deep = self.command('themes-apply')
        deep.chmod(0o600)
        self.run_dots('themes', 'apply', code=1)
        deep.unlink(); deep.symlink_to(self.root / 'missing')
        self.run_dots('themes', 'apply', code=1)

    def test_no_execution_during_discovery_help_and_completion(self):
        self.command('themes', '# dots:summary=Theme manager', 'touch "$HOME/executed"')
        for args in [('help',), ('commands',), ('commands', '--check'), ('themes', '--help'), ('help', 'themes')]:
            self.run_dots(*args)
        self.complete('th')
        self.assertFalse((self.home / 'executed').exists())

    def test_malformed_metadata_does_not_block_direct_execution(self):
        self.command('themes', '# dots:unknown=x')
        self.run_dots('themes', 'ok')
        self.run_dots('themes', '--help', code=1)
        self.run_dots('commands', '--check', code=1)
        p = self.run_dots('__complete', 'bash', '1', '--', 'dots', '', code=1)
        self.assertEqual((p.stdout, p.stderr), ('', ''))

    def test_header_limits_control_characters_and_duplicate_options(self):
        for header in ['# dots:summary=x\n# dots:summary=y', '# dots:summary=bad\x1btext',
                       '# dots:summary=' + 'x' * 17000,
                       '# dots:option=--x||flag|X\n# dots:option=--x||flag|X',
                       '# dots:argument=2|file|File', '# dots:hidden=maybe',
                       '# dots:option=--x||flag|X|', '# dots:argument=1|file|X|']:
            self.command('themes', header)
            self.run_dots('commands', '--check', code=1)

    def test_hidden_group_and_reserved_routes(self):
        self.command('themes-list', '# dots:summary=List themes')
        self.command('themes-secret', '# dots:hidden=true')
        p = self.run_dots('themes')
        self.assertIn('themes list', p.stdout)
        self.assertNotIn('themes secret', p.stdout)
        self.run_dots('themes', 'secret')
        self.assertIn('themes', str(self.complete('th')))
        self.assertNotIn('secret', str(self.complete('themes', '')))
        self.command('apply')
        self.run_dots('apply', code=1)
        self.run_dots('commands', '--check', code=1)

    def test_metadata_is_literal_and_help_never_intercepts_after_separator(self):
        self.command('themes', '# dots:summary=$(touch "$HOME/pwned")')
        self.assertIn('$(touch', self.run_dots('help', 'themes').stdout)
        self.assertFalse((self.home / 'pwned').exists())
        self.assertEqual(self.run_dots('themes', '--', '--help').stdout, '<-->\n<--help>\n')

    def test_exec_keeps_pid_and_delivers_signals(self):
        self.command('waiter', body='trap "exit 42" TERM; printf "%s\\n" "$$"; read -r line')
        process = subprocess.Popen([str(self.repo / 'bin/dots'), 'waiter'], env=self.env,
                                   cwd=self.home, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(int(process.stdout.readline().strip()), process.pid)
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 42)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_sourceable_helpers_nounset_and_narrow_help(self):
        p = self.shell(BASH, '''set -u
source "$DOTS/lib/dots/ui.bash"
dots::heading 'Heading'
dots::row 'Label' 'Value'
dots::warning 'Warning'
dots::error 'Error'
''')
        self.assertIn('Label                      Value', p.stdout)
        self.assertEqual(p.stderr, '[!] Warning\n[x] Error\n')
        self.assertIn('\n      ', self.run_dots('--help', env=dict(self.env, COLUMNS='40')).stdout)

    def test_all_completion_emission_and_builtin_help(self):
        for shell in ('bash', 'zsh', 'fish'):
            self.assertEqual(self.run_dots('completion', shell).stdout,
                             (self.repo / 'lib/dots/completion' / shell).read_text())
        for route in ('commands', 'completion'):
            self.assertIn('Usage', self.run_dots(route, '--help').stdout)

    def test_styles_and_machine_output(self):
        self.hints()
        self.assertNotIn('\x1b', self.run_dots('help').stdout)
        self.assertIn('\x1b', self.run_dots('--color=always', 'help').stdout)
        self.assertNotIn('\x1b', self.run_dots('--color=never', 'help').stdout)
        self.assertNotIn('\x1b', self.run_dots('--color=always', '--dir').stdout)
        self.assertNotIn('\x1b', self.run_dots('--color=always', 'completion', 'bash').stdout)
        self.assertIn('', self.run_dots('--icons=always', 'commands', '--check').stdout)
        self.assertIn('[+]', self.run_dots('--icons=never', 'commands', '--check').stdout)
        self.run_dots('--color=wrong', code=2)
        self.assertNotIn('\x1b', self.run_dots('help', env=dict(self.env, NO_COLOR='1')).stdout)
        self.assertIn('\x1b', self.run_dots('--color=always', 'help', env=dict(self.env, NO_COLOR='1')).stdout)

    def test_automatic_styles_evaluate_stdout_and_stderr_independently(self):
        self.command('style', body='source "$DOTS_LIB_DIR/ui.bash"; dots::success Hello; dots::error Failure')
        for extra, colored in [({}, True), ({'NO_COLOR': '1'}, False), ({'TERM': 'dumb'}, False)]:
            master, slave = pty.openpty()
            try:
                p = subprocess.run([str(self.repo / 'bin/dots'), 'style'],
                                   env=dict(self.env, **extra), cwd=self.home,
                                   stdout=slave, stderr=subprocess.PIPE, timeout=5)
                os.close(slave); slave = None
                data = b''
                while True:
                    try: chunk = os.read(master, 4096)
                    except OSError: break
                    if not chunk: break
                    data += chunk
                self.assertEqual(b'\x1b[' in data, colored)
                self.assertEqual(p.stderr, b'[x] Failure\n')
                self.assertEqual(p.returncode, 0)
            finally:
                if slave is not None: os.close(slave)
                os.close(master)

    def test_completion_routes_options_values_and_new_commands(self):
        self.hints()
        self.assertIn(['candidate', 'themes', 'Manage themes'], self.complete('th'))
        self.assertIn(['candidate', '--flavor', 'Palette flavor'], self.complete('themes', '--f'))
        self.assertIn(['candidate', 'mocha', ''], self.complete('themes', '--flavor', 'm'))
        self.assertIn(['candidate', '--flavor=mocha', ''], self.complete('themes', '--flavor=m'))
        self.assertIn(['directory', '', ''], self.complete('themes', ''))
        self.assertIn(['directory', '', ''], self.complete('themes', '--', '--f'))
        self.assertIn(['candidate', 'yes', ''], self.complete('themes', 'path', 'y'))
        self.command('themes-list')
        self.assertIn(['candidate', 'list', 'Run themes list'], self.complete('themes', 'l'))
        self.assertIn(['candidate', '--color=always', ''], self.complete('--color=a'))
        self.assertIn(['candidate', 'fish', ''], self.complete('completion', 'f'))

    def test_completion_extra_roots_cursor_and_silent_errors(self):
        extra = self.root / 'external'; self.command('other', directory=extra)
        self.assertIn('other', str(self.complete('--command-dir', str(extra), 'oth')))
        self.assertNotIn('other', str(self.complete('oth')))
        p = self.run_dots('__complete', 'bash', '1', '--', 'dots', 'oth', 'ignored')
        self.assertEqual(p.stdout, '')
        self.run_dots('__complete', 'bash', 'bad', '--', 'dots', '', code=2)

    def test_bash_adapter_candidates_equal_wordbreaks_and_files(self):
        self.hints()
        (self.home / 'folder with spaces').mkdir()
        p = self.shell(BASH, '''source "$DOTS/lib/dots/completion/bash"
COMP_WORDS=(dots themes --flavor = m); COMP_CWORD=4
_dots_complete_bash; printf '<%s>\\n' "${COMPREPLY[@]}"
COMP_WORDS=(dots themes 'folder'); COMP_CWORD=2
_dots_complete_bash; printf '<%s>\\n' "${COMPREPLY[@]}"
''')
        self.assertEqual(p.stdout, '<mocha>\n<folder with spaces>\n')

    def test_fish_adapter_choices_paths_and_live_updates(self):
        self.hints()
        (self.home / 'folder with spaces').mkdir()
        p = self.shell(FISH, '''source "$DOTS/lib/dots/completion/fish"
complete -C 'dots themes --flavor m'
complete -C 'dots themes folder'
''')
        self.assertIn('mocha', p.stdout)
        self.assertIn('folder', p.stdout)
        self.assertEqual(p.stderr, '')

    def test_zsh_adapter_loads_without_reinitializing_completion(self):
        self.hints()
        p = self.shell(ZSH, '''autoload -Uz compinit; compinit -D
source "$DOTS/lib/dots/completion/zsh"
[[ $_comps[dots] == _dots ]] || exit 1
# Unit capture for literal arrays; real ZLE is covered by the PTY acceptance.
compadd() { print -rl -- "${candidates[@]}"; }
words=(dots themes --flavor m); CURRENT=4
_dots
typeset -A compstate=(context command)
PREFIX=m
words=(dots themes --flavor not_the_cursor_prefix)
_dots
''')
        self.assertEqual(p.stdout, 'mocha\nmocha\n')
        self.assertEqual(p.stderr, '')

    def test_real_tab_in_bash_zsh_and_fish(self):
        from bash_dots_pty import exercise
        header = self.hints().read_text().split('\n', 1)[1].rsplit('printf', 1)[0]
        self.command('themes', header, 'printf "%s\\n" "$@" > "$HOME/args"; printf "EXECUTED\\n"')
        (self.home / 'folder with spaces').mkdir()
        for executable in (BASH, ZSH, FISH):
            with self.subTest(shell=executable):
                exercise(self, executable)
                (self.repo / 'bin/dots-fresh').unlink()

    def test_missing_optional_programs_and_direct_path_does_not_read_catalog(self):
        self.command('hello', body='printf yes')
        self.command('broken', '# dots:unknown=bad')
        env = dict(self.env, PATH=str(self.repo / 'bin'))
        # Invoke Bash explicitly to test dispatcher dependencies, not env's shebang lookup.
        p = subprocess.run([BASH, str(self.repo / 'bin/dots'), 'hello'], cwd=self.home,
                           env=env, capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, 'yes'))


if __name__ == '__main__':
    unittest.main()
