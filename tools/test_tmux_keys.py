#!/usr/bin/env python3
"""Isolated tmux reference tests: fake tools plus optional native tmux/less PTYs."""
import fcntl
import os
from pathlib import Path
import pty
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time
import unittest

import test_bash_dots as framework

REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
TMUX = shutil.which('tmux')
LESS = shutil.which('less')


def quoted(value):
    """Fixture equivalent of tmux q|a, using double quotes for all strings."""
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
    value = value.replace('\n', '\\n').replace('\t', '\\t').replace('\x1b', '\\033')
    return '"' + value + '"'


class TmuxKeysTests(unittest.TestCase):
    setUpFixture = framework.DotsFixture.setUp
    run_dots = framework.DotsFixture.run_dots

    def setUp(self):
        self.setUpFixture()
        self.command = self.repo / 'bin/dots-menu-tmux-keys'
        shutil.copy2(REPO / 'bin/dots-menu-tmux-keys', self.command)
        self.fake = self.root / 'fake'
        self.fake.mkdir()
        self.env.update(PATH=str(self.fake) + os.pathsep + self.env['PATH'], DOTS_ICONS='never')
        self.records = self.home / 'records'
        self.rows([('prefix', 'x', 'Kill pane'), ('root', 'M-1', 'Switch to window 1'),
                   ('copy-mode-vi', 'y', 'Copy selection'), ('copy-mode', 'z', ''),
                   ('z custom', ';', 'Unicode café'), ('a custom', '"', 'Quoted key')])
        self.tool('tmux', r'''printf '%s\n' "$*" >> "$HOME/tmux-calls"
[[ $1 == -N && $2 == -u ]] || exit 77
shift 2
case $1 in
  list-keys)
    [[ $2 == -F && $3 == *'#{q|a:key_string}'* ]] || exit 78
    [[ ! ${TMUX_FAIL:-} ]] || exit 1
    while IFS= read -r row; do printf '%s\n' "$row"; done < "$HOME/records"
    ;;
  show-options)
    [[ ! ${PREFIX_FAIL:-} ]] || exit 1
    if [[ ${@: -1} == prefix ]]; then printf '%s\n' "${PREFIX_ONE:-C-Space}"
    else printf '%s\n' "${PREFIX_TWO:-C-b}"; fi
    ;;
  *) exit 79 ;;
esac
''')
        self.tool('less', r'''printf '%s\n' "args=$* LESS=$LESS LESSOPEN=$LESSOPEN LESSCLOSE=$LESSCLOSE LESSSECURE=$LESSSECURE" > "$HOME/pager-call"
if [[ ${PAGER_EARLY:-} ]]; then exit 0; fi
while IFS= read -r line; do printf '%s\n' "$line"; done
exit "${PAGER_STATUS:-0}"
''')

    def tool(self, name, body):
        path = self.fake / name
        path.write_text('#!' + BASH + '\n' + body)
        path.chmod(0o700)
        return path

    def rows(self, rows):
        self.records.write_text(''.join('dots-tmux-keys-v1\t' + '\t'.join(map(quoted, row)) + '\n'
                                        for row in rows))

    def run_view(self, *args, env=None, code=0):
        p = subprocess.run([str(self.command), *args], env=env or self.env, cwd=self.home,
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        return p

    def tty_view(self, args=(), env=None, width=80):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
        p = subprocess.Popen([str(self.command), *args], env=env or self.env, cwd=self.home,
                             stdin=slave, stdout=slave, stderr=subprocess.PIPE, start_new_session=True)
        os.close(slave)
        output = bytearray()
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    try:
                        data = os.read(master, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    output.extend(data)
                elif p.poll() is not None:
                    break
            p.wait(timeout=2)
            return p.returncode, output.decode(), p.stderr.read().decode()
        finally:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
            p.stderr.close()
            os.close(master)

    def test_routes_order_and_no_undescribed_commands(self):
        direct = self.run_view().stdout
        routed = self.run_dots('menu', 'tmux', 'keys').stdout
        self.assertEqual(direct, routed)
        self.assertIn('Tmux keybindings (5)', direct)
        self.assertIn('C-Space or C-b', direct)
        positions = [direct.index(s) for s in ('prefix (Prefix + key)', 'root (no prefix)',
                                              'copy-mode-vi', 'a custom', 'z custom')]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('\x1b', direct)
        self.assertFalse((self.home / 'pager-call').exists())

    def test_help_metadata_and_all_completion_protocols_are_static(self):
        self.run_view('--help')
        for args in [('menu', 'tmux', 'keys', '--help'), ('commands', '--check'), ('help', 'menu')]:
            self.run_dots(*args)
        for shell in ('bash', 'zsh', 'fish'):
            for words, expected in [(('menu', ''), 'tmux'), (('menu', 'tmux', ''), 'keys'),
                                    (('menu', 'tmux', 'keys', '--'), '--print')]:
                output = self.run_dots('__complete', shell, str(len(words)), '--', 'dots', *words).stdout
                self.assertIn(expected, output)
        self.assertFalse((self.home / 'tmux-calls').exists())
        self.assertFalse((self.home / 'pager-call').exists())

    def test_unknown_arguments_are_safe_and_do_not_query(self):
        p = self.run_view('--bad\x1b[31m', code=2)
        self.assertEqual(p.stdout, '')
        self.assertIn(r'\x1b', p.stderr)
        self.assertNotIn('\x1b', p.stderr)
        self.assertFalse((self.home / 'tmux-calls').exists())

    def test_safe_literal_values_and_control_characters(self):
        self.rows([('-$(touch marker) " ü', "'", 'space $() `touch marker` #{shell} "quote" \\path\nline\ttab\x1b[31m'),
                   ('prefix', '\\', 'backslash'), ('prefix', ';', 'semicolon')])
        out = self.run_view().stdout
        for literal in ['-$(touch marker) " ü', '`touch marker`', '"quote"', '\\path', '\\nline', '\\ttab', '\\033[31m']:
            self.assertIn(literal, out)
        self.assertNotIn('\x1b', out)
        self.assertFalse((self.home / 'marker').exists())

    def test_raw_control_characters_are_sanitized(self):
        self.records.write_text('dots-tmux-keys-v1\tprefix\tx\t"note\x1b[31m\x7f"\n')
        out = self.run_view().stdout
        self.assertIn(r'\x1b[31m\x7f', out)
        self.assertNotIn('\x1b', out)

    def test_unicode_and_c1_controls_in_c_locale(self):
        self.rows([('unicode → table', 'é', 'Arrow → emoji 🧭 combining e\u0301 日本語; C1 \u0085 end')])
        for locale in ('C', 'C.UTF-8'):
            out = self.run_view(env=dict(self.env, LC_ALL=locale)).stdout
            self.assertIn('unicode → table', out)
            self.assertIn('Arrow → emoji 🧭 combining e\u0301 日本語', out)
            self.assertIn(r'C1 \x85 end', out)
            self.assertNotIn('\u0085', out)

    def test_empty_results_and_disabled_prefixes(self):
        self.rows([('prefix', 'x', '')])
        code, out, _ = self.tty_view(env=dict(self.env, PREFIX_ONE='None', PREFIX_TWO='None'))
        self.assertEqual(code, 0)
        self.assertIn('No described tmux keybindings found', out)
        self.assertIn('None (disabled)', out)
        self.assertFalse((self.home / 'pager-call').exists())

    def test_context_and_duplicate_prefixes(self):
        out = self.run_view(env=dict(self.env, TMUX_PANE='%42', PREFIX_TWO='C-Space')).stdout
        self.assertNotIn(' or ', out)
        self.assertIn('-N -u show-options -v -t %42 prefix', (self.home / 'tmux-calls').read_text())

    def test_query_and_parse_failures_have_no_partial_output(self):
        for name in ('TMUX_FAIL', 'PREFIX_FAIL'):
            self.assertEqual(self.run_view(env=dict(self.env, **{name: '1'}), code=1).stdout, '')
        for value in ['bad', 'dots-tmux-keys-v1\t\tkey\tnote',
                      'dots-tmux-keys-v1\tprefix\tx\t"unterminated',
                      'dots-tmux-keys-v1\tprefix\tx\tnote\textra']:
            self.records.write_text(value + '\n')
            self.assertEqual(self.run_view(code=1).stdout, '')

    def test_missing_tmux(self):
        (self.fake / 'bash').symlink_to(BASH)
        (self.fake / 'tmux').unlink()
        p = self.run_view(env=dict(self.env, PATH=str(self.fake)), code=1)
        self.assertIn('tmux is required', p.stderr)

    def test_redirected_and_forced_color(self):
        self.assertNotIn('\x1b', self.run_view('--print', env=dict(self.env, NO_COLOR='1')).stdout)
        p = self.run_dots('--color=always', '--icons=never', 'menu', 'tmux', 'keys', '--print',
                          env=dict(self.env, NO_COLOR='1'))
        self.assertIn('\x1b', p.stdout)

    def test_explicit_icons_and_long_rows(self):
        p = self.run_view('--bad', env=dict(self.env, DOTS_ICONS='always', DOTS_COLOR='never'), code=2)
        self.assertIn('', p.stderr)
        self.assertNotIn('\x1b', p.stderr)
        key = 'C-' + 'LongKey' * 8
        note = 'Complete long description with Unicode 日本語 and spaces ' * 4
        self.rows([('custom table with a long name', key, note)])
        _, out, _ = self.tty_view(args=('--print',), env=dict(self.env, DOTS_COLOR='never'), width=40)
        self.assertIn(key, out)
        self.assertIn(note, out)
        self.assertIn(key + '  ' + note, out)
        self.assertNotIn('\r\n      Complete long', out)

    def test_pager_and_tty_color_policy_at_three_widths(self):
        for width in (40, 80, 120):
            code, out, err = self.tty_view(width=width, env=dict(self.env, LESS='-F', LESSOPEN='bad', LESSCLOSE='bad'))
            self.assertEqual((code, err), (0, ''))
            self.assertIn('\x1b', out)
            self.assertIn('/ search | n next | q close', out)
            self.assertIn('args=-R LESS= LESSOPEN= LESSCLOSE= LESSSECURE=1',
                          (self.home / 'pager-call').read_text())
            plain = re.sub(r'\x1b\[[0-9;]*m', '', out)
            self.assertIn('  x  Kill pane\r\n', plain)
            self.assertIn('  Prefix  C-Space or C-b\r\n', plain)
        for additions in ({'NO_COLOR': '1'}, {'DOTS_COLOR': 'never'}):
            _, out, _ = self.tty_view(env=dict(self.env, **additions))
            self.assertNotIn('\x1b', out)
        _, out, _ = self.tty_view(env=dict(self.env, NO_COLOR='1', DOTS_COLOR='always'))
        self.assertIn('\x1b', out)

    def test_compact_rows_in_phone_sized_popup(self):
        self.rows([('prefix', 'Space', 'Select next layout'),
                   ('prefix', '$', 'Rename current session'),
                   ('root', 'VeryLongKeyName', 'Full description')])
        code, out, err = self.tty_view(width=50, env=dict(self.env, DOTS_COLOR='never'))
        self.assertEqual((code, err), (0, ''))
        self.assertIn('  Prefix  C-Space or C-b\r\n', out)
        self.assertIn('  Space  Select next layout\r\n', out)
        self.assertIn('  $      Rename current session\r\n', out)
        self.assertIn('  VeryLongKeyName  Full description\r\n', out)

    def test_print_dumb_and_missing_less_fallback(self):
        self.tty_view(args=('--print',))
        self.assertFalse((self.home / 'pager-call').exists())
        self.tty_view(env=dict(self.env, TERM='dumb'))
        self.assertFalse((self.home / 'pager-call').exists())
        (self.fake / 'less').unlink()
        (self.fake / 'bash').symlink_to(BASH)
        code, out, err = self.tty_view(env=dict(self.env, PATH=str(self.fake)))
        self.assertEqual(code, 0)
        self.assertIn('Kill pane', out)
        self.assertIn('less is unavailable', err)
        self.assertNotIn('\x1b', err)  # stderr is redirected independently of stdout

    def test_pager_failure_interruption_and_early_exit(self):
        for status, expected in [('19', 1), ('130', 130)]:
            code, _, err = self.tty_view(env=dict(self.env, PAGER_STATUS=status))
            self.assertEqual(code, expected)
            self.assertNotIn('\x1b', err)
        self.assertEqual(self.tty_view(env=dict(self.env, PAGER_EARLY='1'))[0], 0)

    @unittest.skipUnless(TMUX, 'native tmux unavailable')
    def test_native_format_and_session_prefixes(self):
        socket = self.root / 'owned.socket'
        native_env = dict(self.env)
        native_env.pop('TMUX', None)
        native_env.pop('TMUX_PANE', None)

        def tmux(*args):
            p = subprocess.run([TMUX, '-S', str(socket), *args], env=native_env, cwd=self.home,
                               input='', capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
            return p.stdout

        try:
            tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'fixture', 'sleep 60')
            tmux('set-option', '-t', 'fixture', 'prefix', 'C-a')
            for table, key, note in [('z custom', r'\;', 'space ü "quote" \\slash'),
                                     ('-$(touch marker)', "'", 'note\nline\ttab\x1b[31m'),
                                     ('prefix', 'x', 'Kill test pane')]:
                tmux('bind-key', '-T', table, '-N', note, key, 'display-message', 'not executed')
            self.tool('tmux', 'exec ' + shlex.quote(TMUX) + ' -S ' + shlex.quote(str(socket)) + ' "$@"\n')
            pane = tmux('display-message', '-p', '-t', 'fixture', '#{pane_id}').strip()
            out = self.run_view(env=dict(self.env, TMUX_PANE=pane)).stdout
            self.assertIn('C-a', out)
            self.assertIn('z custom', out)
            self.assertIn('space ü "quote" \\slash', out)
            self.assertIn('-$(touch marker)', out)
            self.assertIn(r'note\nline\ttab\033[31m', out)
            self.assertFalse((self.home / 'marker').exists())
        finally:
            subprocess.run([TMUX, '-S', str(socket), 'kill-server'], env=native_env,
                           capture_output=True, timeout=10)
        # A read must not start a replacement server.
        self.run_view(code=1)
        check = subprocess.run([TMUX, '-N', '-S', str(socket), 'list-sessions'],
                               env=native_env, capture_output=True, timeout=10)
        self.assertNotEqual(check.returncode, 0)

    @unittest.skipUnless(TMUX and LESS, 'native tmux/less unavailable')
    def test_native_popup_from_repository_binding(self):
        # Copy only the requested binding, not personal startup/configuration.
        binding = next(line for line in (REPO / 'config/tmux/tmux.conf').read_text().splitlines()
                       if 'Show Tmux keybindings' in line)
        self.assertIn('"dots-menu-tmux-keys"', binding)
        self.assertIn('-S "fg=blue"', binding)
        self.assertIn('#[fg=cyan,bold]Tmux keybindings#[default]', binding)
        cfg = self.root / 'tmux.conf'
        cfg.write_text('set -g default-shell ' + shlex.quote(BASH) + '\n' + binding +
                       '\nbind D display-message -d 1000 DOTS_POPUP_CLOSED\n')
        socket = self.root / 'popup.socket'
        (self.fake / 'less').unlink()
        (self.fake / 'tmux').unlink()
        self.tool('dots-menu-tmux-keys', 'printf "%s\\n" "$PWD" > "$HOME/popup-cwd"\nexec ' +
                  shlex.quote(str(self.command)) + ' "$@"\n')
        base = [TMUX, '-S', str(socket)]
        env = dict(self.env, SHELL=BASH)
        started = subprocess.run(base + ['-f', str(cfg), 'new-session', '-d', '-s', 'fixture',
                                         '-c', str(self.home), 'sleep 60'],
                                 env=env, cwd=self.home, capture_output=True, text=True, timeout=10)
        self.assertEqual(started.returncode, 0, started.stderr)
        pid, master = pty.fork()
        if pid == 0:
            os.chdir(self.home)
            os.execve(TMUX, base + ['attach-session', '-t', 'fixture'], env)
        reaped = False
        output = bytearray()

        def receive_until(needle, timeout=10):
            deadline = time.monotonic() + timeout
            while needle not in output and time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    try:
                        output.extend(os.read(master, 65536))
                    except OSError:
                        break
            self.assertIn(needle, output)

        try:
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 100, 0, 0))
            receive_until(b'fixture')
            os.write(master, b'\x02?')
            receive_until(b'Tmux keybindings')
            receive_until(b'/ search')
            # Viewer rows use bright ANSI colors; these ordinary blue/cyan
            # colors come from the tmux-owned border and title respectively.
            self.assertRegex(bytes(output), rb'\x1b\[(?:[0-9;]*;)?34m')
            self.assertRegex(bytes(output), rb'\x1b\[(?:[0-9;]*;)?36m')
            self.assertEqual((self.home / 'popup-cwd').read_text().strip(), str(self.home))
            os.write(master, b'q')
            # A prefix binding can run only after the popup has closed.
            time.sleep(.15)
            output.clear()
            os.write(master, b'\x02D')
            receive_until(b'DOTS_POPUP_CLOSED')
            subprocess.run(base + ['detach-client', '-s', 'fixture'], env=env,
                           capture_output=True, timeout=10, check=True)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                got, status = os.waitpid(pid, os.WNOHANG)
                if got:
                    reaped = True
                    self.assertEqual(os.waitstatus_to_exitcode(status), 0)
                    break
                time.sleep(.05)
            self.assertTrue(reaped)
        finally:
            if not reaped:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            os.close(master)
            subprocess.run(base + ['kill-server'], env=env, capture_output=True, timeout=10)

    @unittest.skipUnless(LESS, 'native less unavailable')
    def test_native_less_short_list_waits_searches_and_quits(self):
        (self.fake / 'less').unlink()
        self.rows([('prefix', 'x', 'Searchable unique description')])
        # fork provides a controlling terminal, needed by less's /dev/tty input.
        pid, master = pty.fork()
        if pid == 0:
            os.chdir(self.home)
            os.execve(str(self.command), [str(self.command)], self.env)
        output = bytearray()
        reaped = False
        try:
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
            deadline = time.monotonic() + 10
            while b'Searchable unique description' not in output and time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    output.extend(os.read(master, 65536))
            self.assertIn(b'Searchable unique description', output)
            self.assertEqual(os.waitpid(pid, os.WNOHANG), (0, 0))
            os.write(master, b'/unique\n')
            time.sleep(.1)
            os.write(master, b'q')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                got, status = os.waitpid(pid, os.WNOHANG)
                if got:
                    reaped = True
                    self.assertEqual(os.waitstatus_to_exitcode(status), 0)
                    break
                time.sleep(.05)
            self.assertTrue(reaped, 'less did not exit on q')
        finally:
            if not reaped:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            os.close(master)


if __name__ == '__main__':
    unittest.main()
