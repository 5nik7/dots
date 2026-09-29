#!/usr/bin/env python3
"""Exercise sourceable utilities in disposable Bash/Zsh homes, without startup files."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SHELLS = {name: shutil.which(name) for name in ('bash', 'zsh')}


class CommonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-common-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo space ü'
        (self.repo / 'bin/lib').mkdir(parents=True)
        (self.repo / 'lib/dots').mkdir(parents=True)
        shutil.copy2(REPO / 'bin/lib/common.sh', self.repo / 'bin/lib/common.sh')
        (self.repo / 'scripts').mkdir()
        shutil.copy2(REPO / 'scripts/dirout', self.repo / 'scripts/dirout')
        shutil.copy2(REPO / 'lib/dots/ui.bash', self.repo / 'lib/dots/ui.bash')
        self.fake = self.root / 'tools'
        self.fake.mkdir()
        self.env = dict(HOME=str(self.root), DOTS=str(self.repo),
                        ZDOTDIR=str(self.root), TMPDIR=str(self.root),
                        PATH=str(self.fake), TERM='dumb', LC_ALL='C.UTF-8',
                        DOTS_COLOR='never', DOTS_ICONS='never')
        for kind in ('CONFIG', 'DATA', 'STATE', 'CACHE'):
            self.env[f'XDG_{kind}_HOME'] = str(self.root / kind.lower())
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']

    def run_shell(self, shell, script, **env):
        executable = SHELLS[shell]
        if not executable:
            self.skipTest(f'{shell} unavailable')
        flags = ['--noprofile', '--norc', '-c'] if shell == 'bash' else ['-dfc']
        return subprocess.run([executable, *flags, 'source "$DOTS/bin/lib/common.sh"\n' + script],
                              cwd=self.root, env=self.env | env, text=True,
                              capture_output=True, timeout=20)

    def both(self, script, stdout='', stderr='', code=0, **env):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                p = self.run_shell(shell, script, **env)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                self.assertEqual(p.stdout, stdout)
                self.assertEqual(p.stderr, stderr)

    def stub(self, name, body):
        path = self.fake / name
        path.write_text(f'#!{SHELLS["bash"]}\n{body}\n')
        path.chmod(0o755)
        return path

    def test_source_is_quiet_and_needs_no_tools(self):
        self.both('source "$DOTS/bin/lib/common.sh"; typeset -f so >/dev/null', PATH='')

    def test_path_membership_is_literal_and_idempotent(self):
        for name in ('space ü', 'literal[1]*', '-dash'):
            (self.root / name).mkdir()
        (self.root / 'file').touch()
        (self.root / 'broken').symlink_to('absent')
        self.both('''set -eu
PATH="$HOME/space ü"
prepath "$HOME/literal[1]*"
extpath "$HOME/-dash"
expected="$HOME/literal[1]*:$HOME/space ü:$HOME/-dash"
[[ $PATH == "$expected" ]]
prepath "$HOME/-dash"
extpath "$HOME/literal[1]*"
[[ $PATH == "$expected" ]]
for name in missing file broken; do
  if prepath "$HOME/$name"; then exit 10; fi
done
[[ $PATH == "$expected" ]]
if prepath; then exit 11; else [[ $? == 2 ]]; fi
if extpath "$HOME" extra; then exit 12; else [[ $? == 2 ]]; fi
PATH=''; extpath "$HOME/-dash"; [[ $PATH == "$HOME/-dash" ]]
unset PATH; prepath "$HOME/space ü"; [[ $PATH == "$HOME/space ü" ]]
''')

    def test_chcmd_executes_once_with_original_streams_and_status(self):
        self.both('''calls=0
once() { calls=$((calls+1)); printf 'out\n'; printf 'err\n' >&2; return 7; }
chcmd once
rc=$?
[[ $rc == 7 && $calls == 1 ]] || exit 10
if chcmd; then exit 11; else [[ $? == 2 ]]; fi
''', stdout='out\n', stderr='err\n')

    def test_so_keeps_arguments_and_source_effects(self):
        (self.root / 'one ü').write_text('result="${result:-}one"\n')
        (self.root / '-two').write_text('result="${result:-}two"\n')
        (self.root / 'empty').touch()
        self.both('''set -eu
so missing empty 'one ü' -two
[[ $result == onetwo ]]
result=''; so --first missing 'one ü' -two; [[ $result == one ]]
if so missing empty; then exit 12; else [[ $? == 1 ]]; fi
''')

    def test_so_returns_first_source_failure_and_continues(self):
        (self.root / 'bad').write_text('seen=bad; return 7\n')
        (self.root / 'good').write_text('seen="${seen:-}good"\n')
        self.both('''so bad good; rc=$?
[[ $rc == 7 && $seen == badgood ]] || exit 10
seen=''; so --first bad good; rc=$?
[[ $rc == 7 && $seen == bad ]] || exit 11
so --verbose bad; rc=$?; [[ $rc == 7 ]]
''', stderr='[x] source failed (7) | ./bad\n')

    def test_so_uses_checked_relative_file_not_path_shadow(self):
        (self.root / 'load').write_text('seen=local\n')
        (self.fake / 'load').write_text('seen=wrong\n')
        self.both('so load; [[ $seen == local ]]')

    def test_shellmod_uses_running_shell_and_keeps_alias(self):
        for shell in SHELLS:
            directory = self.repo / 'shells' / shell
            directory.mkdir(parents=True)
            (directory / f'fixture.{shell}').write_text(f'seen={shell}\n')
            with self.subTest(shell=shell):
                p = self.run_shell(shell, f'''shellmod fixture
[[ $seen == {shell} ]] || exit 10
alias zieces
''', SHELL='/other/shell')
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn('shellmod', p.stdout)

    def test_checks_any_match_first_and_verbose_alias(self):
        (self.root / 'file').touch()
        (self.root / 'dir').mkdir()
        (self.root / 'broken').symlink_to('absent')
        self.both('''set -e
check missing file
checkdir file dir
if check broken; then exit 10; fi
if checkdir file; then exit 11; fi
check --verbose --first file ignored
check --verboss file
''', stdout='[+] found | file\n[+] found | file\n')

    def test_addir_creates_only_requested_directories_and_is_idempotent(self):
        mkdir = shutil.which('mkdir')
        (self.fake / 'mkdir').symlink_to(mkdir)
        self.both('''set -e
addir 'nested/space ü' --literal
addir 'nested/space ü' --literal
[[ -d 'nested/space ü' && -d --literal ]]
''')
        (self.root / 'file').write_text('keep')
        (self.root / 'broken').symlink_to('missing')
        self.both('addir file broken; [[ $? == 1 ]]',
                  stderr='[x] Not a directory: file\n[x] Not a directory: broken\n')
        self.assertEqual((self.root / 'file').read_text(), 'keep')
        self.assertTrue((self.root / 'broken').is_symlink())

    def test_addir_propagates_mkdir_failure(self):
        self.stub('mkdir', 'exit 9')
        self.both('addir --verbose missing; [[ $? == 9 ]]')
        self.assertFalse((self.root / 'missing').exists())

    def test_plain_filename_and_dirname_match_system_oracles(self):
        paths = ['', '/', '///', 'a', 'a/', 'a//b//', '/a//b/', 'a b/ü', '-dash', 'a/line\nnext']
        import shlex
        args = ' '.join(map(shlex.quote, paths))
        basename = shutil.which('basename')
        dirname = shutil.which('dirname')
        def oracle(command):
            return ''.join(subprocess.check_output([command, '--', p], text=True) for p in paths)
        self.both('filename ' + args, stdout=oracle(basename))
        self.both('dirout -r -- ' + args, stdout=oracle(dirname))

    def test_raw_paths_and_case_conversion_use_no_tools(self):
        self.both('''pathout -r -- '-n' 'space ü' $'line\nnext'
upper '-n' 'a\\b'
lower '-N' 'A\\B'
''', stdout='-n\nspace ü\nline\nnext\n-N A\\B\n-n a\\b\n',
                  PATH='', DOTS_COLOR='always', DOTS_ICONS='always')
        self.both('pathout "$HOME" "$HOME/a" "${HOME}suffix/a"',
                  stdout=f'~\n~/a\n{self.root}suffix/a\n')
        self.both('BLUE=B RST=R; dirout -r -j -c a/b', stdout='a/\n')

    def test_optional_eza_is_guarded_and_failure_falls_back(self):
        self.stub('eza', '''[[ $4 == --color=always && $5 == -- && $6 == '-dash' ]] || exit 20
case $3 in --icons=always) printf 'ICON -dash\n';; *) printf '\\033[31m-dash\\033[0m\n';; esac''')
        self.both('filename -dash; fileicon -dash', stdout='\x1b[31m-dash\x1b[0m\nICON\n')
        self.stub('eza', 'exit 1')
        self.both('filename a/b; fileicon a/b', stdout='b\n\n')

    def dirout_tools(self):
        for name in ('dirname', 'readlink'):
            (self.fake / name).symlink_to(shutil.which(name))

    def test_dirout_shared_policy_and_plain_data_for_both_entry_points(self):
        self.dirout_tools()
        for command in ('dirout', '"$BASH_EXE" "$DOTS/scripts/dirout"'):
            for mode in ('auto', 'never', 'always'):
                with self.subTest(command=command, mode=mode):
                    prefix, reset = ('\x1b[94m', '\x1b[0m') if mode == 'always' else ('', '')
                    env = dict(BASH_EXE=SHELLS['bash'], DOTS_COLOR=mode,
                               BLUE='wrong', RST='wrong', NO_COLOR='1', TERM='dumb')
                    self.both(command + ' -r -j -c a/b "space ü/file"',
                              stdout=f'{prefix}a/{reset}\n{prefix}space ü/{reset}\n', **env)
                    self.both(command + ' -r -j a/b "space ü/file"',
                              stdout='a/\nspace ü/\n', **env)
                    self.both(command + ' "$HOME/file" "$HOME/space ü/file" ./-dash/file',
                              stdout='~\n~/space ü\n./-dash\n', **env)
                    self.both(command, stdout=str(self.root.parent) + '\n', **env)

    def test_dirout_symlinked_script_and_missing_renderer_fallback(self):
        self.dirout_tools()
        (self.root / 'relative link').symlink_to(self.repo.relative_to(self.root) / 'scripts/dirout')
        (self.root / 'linked-dirout').symlink_to('relative link')
        command = '"$BASH_EXE" "$HOME/linked-dirout" -r -c a/b'
        env = dict(BASH_EXE=SHELLS['bash'], DOTS_COLOR='always')
        self.both(command, stdout='\x1b[94ma\x1b[0m\n', **env)
        foreign = self.root / 'foreign'
        (foreign / 'lib/dots').mkdir(parents=True)
        (foreign / 'lib/dots/ui.bash').write_text('printf wrong-renderer\n')
        p = subprocess.run([SHELLS['bash'], str(self.root / 'linked-dirout'), '-r', '-c', 'a/b'],
                           cwd=self.root, env=self.env | env | {'DOTS': str(foreign)},
                           text=True, capture_output=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, '\x1b[94ma\x1b[0m\n', ''))
        (self.repo / 'lib/dots/ui.bash').unlink()
        self.both(command, stdout='a\n', **env)
        self.both('dirout -r -c a/b', stdout='a\n', **env)

    @unittest.skipUnless(os.name == 'posix', 'requires a native Unix PTY')
    def test_dirout_terminal_policy_for_helpers_and_standalone(self):
        import fcntl
        import pty
        import struct
        import termios
        self.dirout_tools()
        for shell, executable in SHELLS.items():
            if not executable:
                continue
            flags = ['--noprofile', '--norc', '-c'] if shell == 'bash' else ['-dfc']
            for command in ('dirout', '"$BASH_EXE" "$DOTS/scripts/dirout"'):
                for columns in (40, 120):
                    for mode, term, no_color, colored in (
                        ('auto', 'xterm-256color', '', True),
                        ('auto', 'xterm-256color', '1', False),
                        ('auto', 'dumb', '', False),
                        ('never', 'xterm-256color', '', False),
                        ('always', 'dumb', '1', True),
                    ):
                        with self.subTest(shell=shell, command=command, columns=columns, mode=mode, term=term, no_color=no_color):
                            master, slave = pty.openpty()
                            try:
                                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, columns, 0, 0))
                                env = self.env | dict(BASH_EXE=SHELLS['bash'], DOTS_COLOR=mode, TERM=term,
                                                      NO_COLOR=no_color, BLUE='wrong', RST='wrong')
                                code = 'source "$DOTS/bin/lib/common.sh"; ' + command + ' -c -r "space ü/file"'
                                p = subprocess.run([executable, *flags, code], cwd=self.root, env=env,
                                                   stdout=slave, stderr=slave, timeout=10)
                                output = os.read(master, 8192).decode()
                                self.assertEqual(p.returncode, 0, output)
                                expected = '\x1b[94mspace ü\x1b[0m\r\n' if colored else 'space ü\r\n'
                                self.assertEqual(output, expected)
                            finally:
                                os.close(master)
                                os.close(slave)

    def test_messages_use_shared_policy_and_correct_streams(self):
        self.both('ok "done|path"; warn warning; err error',
                  stdout='[+] done | path\n', stderr='[!] warning\n[x] error\n')
        for shell in SHELLS:
            with self.subTest(shell=shell):
                p = self.run_shell(shell, 'ok done; err failed', DOTS_COLOR='always', DOTS_ICONS='always')
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn('\x1b[92m', p.stdout)
                self.assertIn('\x1b[91m', p.stderr)
                self.assertIn('', p.stdout)
                p = self.run_shell(shell, "err $'bad\\e[2J\\nline'", DOTS_COLOR='never')
                self.assertNotIn('\x1b', p.stderr)
                self.assertEqual(len(p.stderr.splitlines()), 1)
        self.both('ok done', stdout='[+] done\n', DOTS_COLOR='auto', DOTS_ICONS='auto', NO_COLOR='1')
        (self.repo / 'lib/dots/ui.bash').unlink()
        self.both('ok done; err failed', stdout='[+] done\n', stderr='[x] failed\n', DOTS_COLOR='always')

    @unittest.skipUnless(os.name == 'posix', 'requires a native Unix PTY')
    def test_terminal_message_policy_at_narrow_and_wide_widths(self):
        import fcntl
        import pty
        import struct
        import termios
        for shell, executable in SHELLS.items():
            if not executable:
                continue
            flags = ['--noprofile', '--norc', '-c'] if shell == 'bash' else ['-dfc']
            for columns in (40, 120):
                for mode, term, no_color, colored, icons in (
                    ('auto', 'xterm-256color', '', True, True),
                    ('auto', 'xterm-256color', '1', False, True),
                    ('auto', 'dumb', '', False, False),
                    ('never', 'xterm-256color', '', False, False),
                    ('always', 'dumb', '1', True, True),
                ):
                    with self.subTest(shell=shell, columns=columns, mode=mode, term=term, no_color=no_color):
                        master, slave = pty.openpty()
                        try:
                            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, columns, 0, 0))
                            env = self.env | dict(DOTS_COLOR=mode, DOTS_ICONS=mode, TERM=term,
                                                  NO_COLOR=no_color, COLUMNS=str(columns))
                            script = 'source "$DOTS/bin/lib/common.sh"; ok "done|space ü/-dash"; warn warning; err failed'
                            p = subprocess.run([executable, *flags, script], cwd=self.root, env=env,
                                               stdout=slave, stderr=slave, timeout=10)
                            output = os.read(master, 8192).decode()
                            self.assertEqual(p.returncode, 0, output)
                            self.assertEqual('\x1b[' in output, colored)
                            self.assertEqual('' in output, icons)
                            self.assertIn('done | space ü/-dash', output)
                            self.assertIn('warning', output)
                            self.assertIn('failed', output)
                        finally:
                            os.close(master)
                            os.close(slave)

    def test_has_accepts_functions_and_checks_every_command(self):
        self.both('''present() { :; }
has present 'printf argument' || exit 10
if has present absent; then exit 11; fi
if has; then exit 12; fi
has -v absent; [[ $? == 1 ]]
''', stderr='[x] absent not found\n')

    def test_installed_status_uses_only_fixture_package_database(self):
        self.stub('dpkg-query', '''[[ $1 == -W && $2 == '-f=${db:Status-Status}' && $3 == -- ]] || exit 10
case $4 in installed|held) printf 'installed';; removed) printf 'config-files';; *) exit 1;; esac''')
        self.both('''is_installed installed || exit 10
is_installed held || exit 14
if is_installed removed; then exit 11; fi
if is_installed missing; then exit 12; fi
if is_installed; then exit 13; else [[ $? == 2 ]]; fi
''')
        self.both('if is_installed installed; then exit 10; fi', PATH='')


    def test_loading_defines_helpers_without_initializing_arrays_or_styles(self):
        self.both('''set -eu
[[ ! ${FG+x} && ! ${BG+x} && ! ${COLOR+x} && ! ${DOTS_UI_RESET+x} ]]
[[ ! ${RED+x} && ! ${SETUP_COLORS_COMPLETE+x} ]]
trap ':' INT
before=$(trap)
source "$DOTS/bin/lib/common.sh"
[[ $(trap) == "$before" ]]
[[ ! ${FG+x} && ! ${DOTS_UI_RESET+x} ]]
for helper in has so color_array fg_array bg_array build_color_arrays setup_colors log_info fmt_title_border spinner run_with_spinner; do
  typeset -f "$helper" >/dev/null
done
''', PATH='')

    def test_arrays_are_exact_global_repeatable_and_do_not_leak_counters(self):
        self.both(r'''set -eu
j=17; i=sentinel; ESC=sentinel
build_color_arrays
for ((n=0; n<256; n++)); do
  [[ ${FG[$n]} == $'\e'"[38;5;${n}m" ]] || exit 10
  [[ ${BG[$n]} == $'\e'"[48;5;${n}m" ]] || exit 11
  [[ ${COLOR[$n]} == $'\e'"[38;5;${n}mcolor $n" ]] || exit 12
done
[[ ${#FG[@]} == 256 && ${#BG[@]} == 256 && ${#COLOR[@]} == 256 ]]
FG[extra]=bad; BG[extra]=bad; COLOR[extra]=bad
build_color_arrays
[[ ${#FG[@]} == 256 && ${#BG[@]} == 256 && ${#COLOR[@]} == 256 ]]
[[ $j == 17 && $i == sentinel && $ESC == sentinel ]]
[[ ! ${_common_index+x} ]]
''', PATH='', DOTS_COLOR='always', DOTS_ICONS='always')

    def test_common_neither_creates_nor_overwrites_legacy_globals(self):
        self.both('''set -eu
build_color_arrays
setup_colors
source "$DOTS/bin/lib/common.sh"
[[ ! ${RED+x} && ! ${BLUE+x} && ! ${BOLD+x} && ! ${RST+x} && ! ${COLORS+x} ]]
RED=red BLUE=blue BOLD=bold RST=reset COLORS=caller
source "$DOTS/bin/lib/common.sh"
build_color_arrays
setup_colors
[[ $RED == red && $BLUE == blue && $BOLD == bold && $RST == reset && $COLORS == caller ]]
''', PATH='')

    def test_compatibility_profiles_build_arrays_without_color_globals_or_tools(self):
        (self.repo / 'shells').mkdir()
        for name in ('profile', '.profile'):
            shutil.copy2(REPO / 'shells' / name, self.repo / 'shells' / name)
            with self.subTest(profile=name):
                self.both('''set -eu
source "$DOTS/shells/$PROFILE"
[[ ${#FG[@]} == 256 && ${#BG[@]} == 256 && ${#COLOR[@]} == 256 ]]
[[ ! ${RED+x} && ! ${BLUE+x} && ! ${BOLD+x} && ! ${RST+x} && ! ${COLORS+x} ]]
RED=red BLUE=blue BOLD=bold RST=reset COLORS=caller
source "$DOTS/shells/$PROFILE"
[[ $RED == red && $BLUE == blue && $BOLD == bold && $RST == reset && $COLORS == caller ]]
''', PATH='', PROFILE=name)

    def test_logging_and_formatting_share_policy_and_preserve_named_colors(self):
        self.both('''RED=red BLUE=blue BOLD=bold RESET=reset
log_info info; log_success success; log_warning warning; log_error error
fmt_key key; fmt_value value; fmt_cmd cmd; fmt_path path; printf '\n'
fmt_title title; fmt_title_underline underline; fmt_title_border box
[[ $RED == red && $BLUE == blue && $BOLD == bold && $RESET == reset ]]
''', stdout='[i] info\n[+] success\nkeyvaluecmdpath\n title \nunderline\n+-----+\n| box |\n+-----+\n',
                  stderr='[!] warning\n[x] error\n')
        (self.repo / 'lib/dots/ui.bash').unlink()
        self.both('log_info info; fmt_path path', stdout='[i] info\npath', DOTS_COLOR='always')

    def test_spinner_commands_run_once_and_preserve_status_streams_and_traps(self):
        self.both('''trap ':' INT TERM
before=$(trap)
run_with_spinner 'printf out; printf err >&2; return 7' 1 work
rc=$?
[[ $rc == 7 ]] || exit 10
[[ $(trap) == "$before" ]] || exit 11
run_with_spinner 'printf x >> "$HOME/count"' 19 done 1
if run_with_spinner; then exit 12; else [[ $? == 2 ]]; fi
if spinner invalid; then exit 13; else [[ $? == 2 ]]; fi
spinner 99999999 1 quiet
''', stdout='out[+] Success!\n', stderr='err', DOTS_PROGRESS='never', PATH='')
        self.assertEqual((self.root / 'count').read_text(), 'xx')
        self.both("run_with_spinner 'return 9' 1 failure 1; [[ $? == 9 ]]", stderr='[x] Failed!\n')

    @unittest.skipUnless(os.name == 'posix', 'requires a native Unix PTY')
    def test_spinner_terminal_animation_and_disabled_fallback(self):
        import pty
        (self.fake / 'sleep').symlink_to(shutil.which('sleep'))
        for shell, executable in SHELLS.items():
            if not executable:
                continue
            flags = ['--noprofile', '--norc', '-c'] if shell == 'bash' else ['-dfc']
            for progress in ('auto', 'never'):
                with self.subTest(shell=shell, progress=progress):
                    master, slave = pty.openpty()
                    try:
                        env = self.env | dict(DOTS_PROGRESS=progress, TERM='xterm-256color', COLUMNS='40')
                        script = 'source "$DOTS/bin/lib/common.sh"; run_with_spinner "sleep 0.8" 19 "working"; printf DONE'
                        p = subprocess.run([executable, *flags, script], cwd=self.root, env=env,
                                           stdout=slave, stderr=slave, timeout=10)
                        output = os.read(master, 8192).decode()
                        self.assertEqual(p.returncode, 0, output)
                        self.assertIn('DONE', output)
                        self.assertEqual('working' in output, progress == 'auto')
                        self.assertNotIn('\x1b', output)
                        self.assertNotIn('⏳', output)  # Explicit ASCII icons.
                    finally:
                        os.close(master)
                        os.close(slave)

    @unittest.skipUnless(os.name == 'posix', 'requires process signals')
    def test_foreground_spinner_signals_restore_traps_and_return_status(self):
        import signal
        import time
        self.stub('job', 'printf "%s" "$$" > "$HOME/child"\nexec ' + shutil.which('sleep') + ' 30')
        for shell, executable in SHELLS.items():
            if not executable:
                continue
            for sig, expected in ((signal.SIGINT, 130), (signal.SIGTERM, 143)):
                with self.subTest(shell=shell, signal=sig):
                    pidfile = self.root / 'child'
                    pidfile.unlink(missing_ok=True)
                    script = '''source "$DOTS/bin/lib/common.sh"
trap 'printf unexpected-signal' INT TERM
trap 'printf caller-exit' EXIT
before=$(trap)
run_with_spinner 'exec job' 1 work
rc=$?
[[ $rc == "$EXPECTED" ]] || exit 10
[[ $(trap) == "$before" ]] || exit 11
printf returned
'''
                    flags = ['--noprofile', '--norc', '-c'] if shell == 'bash' else ['-dfc']
                    p = subprocess.Popen([executable, *flags, script], cwd=self.root,
                                         env=self.env | {'EXPECTED': str(expected)},
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, start_new_session=True)
                    try:
                        deadline = time.monotonic() + 5
                        while not (pidfile.exists() and pidfile.read_text()):
                            if time.monotonic() > deadline:
                                self.fail('command did not start')
                            time.sleep(0.02)
                        child = int(pidfile.read_text())
                        os.kill(p.pid, sig)
                        out, err = p.communicate(timeout=5)
                        self.assertEqual(p.returncode, 0, out + err)
                        self.assertEqual(out, 'returnedcaller-exit')
                        with self.assertRaises(ProcessLookupError):
                            os.kill(child, 0)
                    finally:
                        try:
                            os.killpg(p.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        p.communicate(timeout=5)

    @unittest.skipUnless(os.name == 'posix', 'requires process signals')
    def test_spinner_interruption_reaps_owned_command_and_keeps_caller_trap(self):
        import signal
        import time
        self.stub('job', 'exec ' + shutil.which('sleep') + ' 30')
        for shell, executable in SHELLS.items():
            if not executable:
                continue
            with self.subTest(shell=shell):
                ready = self.root / 'ready'
                ready.unlink(missing_ok=True)
                pidfile = self.root / 'child'
                pidfile.unlink(missing_ok=True)
                self.stub('job', 'printf "%s" "$$" > "$HOME/child"\nexec ' + shutil.which('sleep') + ' 30')
                script = '''source "$DOTS/bin/lib/common.sh"
trap 'printf caller-exit' EXIT
run_with_spinner 'exec job' 1 work &
helper=$!
printf '%s' "$helper" > "$HOME/ready"
wait "$helper"; rc=$?
[[ $rc == 143 ]] || exit 10
printf returned
'''
                flags = ['--noprofile', '--norc', '-c'] if shell == 'bash' else ['-dfc']
                p = subprocess.Popen([executable, *flags, script], cwd=self.root, env=self.env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     start_new_session=True)
                try:
                    deadline = time.monotonic() + 5
                    while not (ready.exists() and pidfile.exists() and ready.read_text() and pidfile.read_text()):
                        if time.monotonic() > deadline:
                            self.fail('command did not start')
                        time.sleep(0.02)
                    child = int(pidfile.read_text())
                    os.kill(int(ready.read_text()), signal.SIGTERM)
                    out, err = p.communicate(timeout=5)
                    self.assertEqual(p.returncode, 0, out + err)
                    self.assertEqual(out, 'returnedcaller-exit')
                    with self.assertRaises(ProcessLookupError):
                        os.kill(child, 0)
                finally:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    p.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
