#!/usr/bin/env python3
"""Theme picker contracts and optional native Gum PTY checks in disposable roots."""
import importlib.util
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import struct
import termios
import fcntl
import time
import unittest

spec = importlib.util.spec_from_file_location('themes', Path(__file__).with_name('test_themes.py'))
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
NATIVE_GUM = shutil.which('gum')
NATIVE_FZF = shutil.which('fzf')
ANSI = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)')


class Picker(old.Themes):
    def setUp(self):
        super().setUp()
        self.fake = self.root / 'ui tools'
        self.fake.mkdir()
        self.env['PATH'] = str(self.fake) + ':' + self.env['PATH']
        self.env['DOTS_ICONS'] = 'never'
        self.calls = self.home / 'calls'
        self.script = '''DT_LIB="$DOTS/lib/dots/themes"
set -- help
source "$DT_LIB/commands.bash" >/dev/null || exit
# Hide installed optional UI tools unless explicitly enabled in this fixture.
command() {
  if [[ $1 == -v && ( $2 == gum || $2 == fzf ) ]]; then
    [[ :${PICKER_TOOLS:-}: == *:$2:* ]] || return 1
  fi
  builtin command "$@"
}
dt_command switcher
'''

    def fixture_ui(self, name='gum'):
        p = self.fake / name
        p.write_text('#!' + old.BASH + '''
{ printf '%q ' "$@"; printf '\\n'; } >> "$HOME/calls"
printf '%s|%s|%s|%s\\n' "${NO_COLOR:-}" "${CLICOLOR_FORCE:-}" "${GUM_FILTER_PROMPT_FOREGROUND:-}" "${FZF_DEFAULT_OPTS:-}" >> "$HOME/policy"
if [[ ${1:-} == choose ]]; then queue=$HOME/actions; else queue=$HOME/selections; fi
IFS= read -r value < "$queue" || exit 7
tail -n +2 "$queue" > "$queue.next"
mv "$queue.next" "$queue"
case $value in
  EXIT:*) exit "${value#EXIT:}" ;;
  EMPTY) exit 0 ;;
  MULTI) printf 'nord\\ncatppuccin-latte\\n'; exit 0 ;;
esac
printf '%s\\n' "$value"
''')
        p.chmod(0o700)
        self.env['PICKER_TOOLS'] = ':'.join(filter(None, (self.env.get('PICKER_TOOLS'), name)))

    def queue(self, selections=('nord',), actions=('Cancel',)):
        (self.home / 'selections').write_text('\n'.join(selections) + '\n')
        (self.home / 'actions').write_text('\n'.join(actions) + '\n')

    def terminal(self, script=None, steps=(), code=0, env=None, width=80, timeout=30):
        pid, master = pty.fork()
        if pid == 0:
            os.chdir(self.home)
            os.execve(old.BASH, [old.BASH, '--noprofile', '--norc', '-c', script or self.script], env or self.env)
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 35, width, 0, 0))
        output = bytearray()
        consumed = 0
        step = 0
        status = None
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], 0.05)
                if ready:
                    try:
                        data = os.read(master, 65536)
                    except OSError:
                        data = b''
                    if data:
                        output.extend(data)
                clean = ANSI.sub(b'', bytes(output))
                if step < len(steps):
                    marker, response = steps[step]
                    found = clean.find(marker, consumed)
                    if found >= 0:
                        # Let the terminal reader finish switching modes before input.
                        time.sleep(0.15)
                        os.write(master, response)
                        consumed = found + len(marker)
                        step += 1
                done, result = os.waitpid(pid, os.WNOHANG)
                if done:
                    status = os.waitstatus_to_exitcode(result)
                    break
            self.assertIsNotNone(status, ('PTY timeout', bytes(output)[-2000:]))
            self.assertEqual(step, len(steps), bytes(output)[-2000:])
            self.assertEqual(status, code, bytes(output)[-3000:])
            return bytes(output)
        finally:
            if status is None:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)
            os.close(master)

    def test_gum_review_back_cancel_and_policy(self):
        self.fixture_ui()
        self.queue(('nord', 'catppuccin-latte'), ('Back', 'Cancel'))
        env = dict(self.env, GUM_FILTER_PROMPT_FOREGROUND='#123456', CLICOLOR_FORCE='1')
        out = self.terminal(env=env)
        self.assertIn(b'Preview only', out)
        self.assertIn(b'Cancelled', out)
        calls = self.calls.read_text().splitlines()
        self.assertEqual([line.split()[0] for line in calls], ['filter', 'choose', 'filter', 'choose'])
        self.assertIn('--selected=Back', calls[1])
        self.assertIn('--show-help=false', calls[0])
        self.assertEqual((self.home / 'policy').read_text().splitlines(), ['1|0|#123456|'] * 4)
        self.assertFalse(self.state.exists())

    def test_apply_uses_one_publication_and_revalidates(self):
        self.fixture_ui(); self.queue(actions=('Apply',))
        self.terminal(timeout=45)
        self.assertEqual(len(list((self.state / 'generations').glob('g.*'))), 1)
        self.assertEqual(self.dots('theme', 'current').stdout.strip(), 'nord')
        self.assertEqual([x.split()[0] for x in self.calls.read_text().splitlines()], ['filter', 'choose'])
        self.assertFalse((self.state / 'background').exists())

    def test_fzf_live_preview_with_gum_review(self):
        self.fixture_ui(); self.fixture_ui('fzf')
        self.queue(('nord', 'catppuccin-latte'), ('Back', 'Cancel'))
        self.terminal()
        calls = self.calls.read_text().splitlines()
        self.assertTrue(calls[0].startswith('--no-multi '))
        self.assertTrue(calls[1].startswith('choose '))
        self.assertTrue(calls[2].startswith('--no-multi '))
        self.assertTrue(calls[3].startswith('choose '))
        self.assertFalse(self.state.exists())
        self.calls.unlink()
        self.queue(('EXIT:7',))
        self.terminal(code=1)
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)
        self.assertFalse(self.state.exists())
        self.queue(actions=('Apply',))
        self.terminal(timeout=45)
        self.assertEqual(self.dots('theme', 'current').stdout.strip(), 'nord')
        self.assertEqual(len(list((self.state / 'generations').glob('g.*'))), 1)
        self.assertFalse((self.state / 'background-current').exists())

    def test_tool_errors_and_invalid_results_never_fall_back(self):
        self.fixture_ui()
        for selection, action, code in [('EXIT:7', 'Apply', 1), ('EXIT:1', 'Apply', 1),
                                       ('EXIT:130', 'Apply', 130), ('EMPTY', 'Apply', 130),
                                       ('MULTI', 'Apply', 1), ('../bad', 'Apply', 1),
                                       ('nord', 'unknown', 1), ('nord', 'EXIT:7', 1)]:
            with self.subTest(selection=selection, action=action):
                self.calls.unlink(missing_ok=True)
                self.queue((selection,), (action,))
                self.terminal(code=code)
                self.assertFalse(self.state.exists())
                self.assertTrue(all(x.startswith(('filter ', 'choose ')) for x in self.calls.read_text().splitlines()))

    def test_empty_catalog_and_bad_preview(self):
        self.fixture_ui(); self.queue(actions=('Apply',))
        out = self.terminal(self.script.replace('dt_command switcher', 'dt_theme_ids() { :; }; dt_command switcher'), code=1)
        self.assertIn(b'no themes available', out)
        self.assertFalse(self.calls.exists())
        (self.repo / 'themes/nord/colors.toml').write_text('invalid\n')
        self.terminal(code=1)
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)
        self.assertFalse(self.state.exists())

    def test_fzf_fallback_then_plain_review(self):
        self.fixture_ui('fzf'); self.queue()
        out = self.terminal(steps=((b'Number [1]', b'3\r'),))
        self.assertIn(b'Cancelled', out)
        args = self.calls.read_text()
        self.assertIn('--preview=', args)
        self.assertIn('--no-multi', args)
        self.assertIn('--no-height', args)
        self.assertIn('--layout=reverse', args)
        self.assertIn('--preview-window=down\\,70%\\,nohidden', args)
        self.assertIn('--color=never', args)
        self.assertIn('--color=bw', args)
        self.assertIn('--no-unicode', args)
        self.assertFalse(self.state.exists())
        self.queue(('EXIT:130',))
        self.terminal(code=130)
        self.queue(('EXIT:2',))
        self.terminal(code=1)

    def test_fzf_uses_published_colors_without_sourcing_shell(self):
        self.fixture_ui('fzf')
        override = self.repo / 'themes/nord/fzf.sh'
        override.write_text('export _FZF_COLORS_="fg:#112233"\n')
        self.dots('theme', 'set', 'nord')
        generation = self.generation()
        # Unpublished edits and stale shell colors must not override the active artifact.
        override.write_text('export _FZF_COLORS_="fg:#445566"\n')
        for mode, no_color, expected in [('always', '1', '--color=fg:#112233'),
                                         ('auto', '', '--color=fg:#112233'),
                                         ('auto', '1', '--color=bw'),
                                         ('never', '', '--color=bw')]:
            with self.subTest(mode=mode, no_color=no_color):
                self.calls.unlink(missing_ok=True)
                self.queue()
                self.terminal(steps=((b'Number [1]', b'3\r'),),
                              env=dict(self.env, DOTS_COLOR=mode, NO_COLOR=no_color,
                                       FZF_DEFAULT_OPTS='--color=fg:#778899',
                                       DOTS_THEME_FZF_COLORS='fg:#778899'))
                args = self.calls.read_text()
                self.assertIn(expected, args)
                self.assertNotIn('#445566', args)
                self.assertNotIn('#778899', args)
                self.assertEqual(self.generation(), generation)
        # The parser is shared with publication and must not execute even trusted files.
        (generation / 'fzf.sh').write_text('export _FZF_COLORS_="$(touch SENTINEL)"\n')
        self.calls.unlink()
        self.queue()
        self.terminal(env=dict(self.env, DOTS_COLOR='always'), code=1)
        self.assertFalse(self.calls.exists())
        self.assertFalse((self.home / 'SENTINEL').exists())
        self.assertEqual(self.generation(), generation)

    def test_plain_menu_defaults_invalid_input_escape_and_eof(self):
        script = self.script.replace('dt_command switcher', 'dt_theme_ids() { printf "nord\\n"; }; dt_command switcher')
        out = self.terminal(script, steps=((b'Number (', b'0\r'), (b'Choose a number', b'1\r'),
                                          (b'Number [1]', b'\r'), (b'Number (', b'1\r'),
                                          (b'Number [1]', b'3\r')))
        self.assertIn(b'Cancelled', out)
        for key in (b'\x1b', b'\x04'):
            self.terminal(script, steps=((b'Number (', key),), code=130)
        self.assertFalse(self.state.exists())

    def test_plain_menu_apply(self):
        script = self.script.replace('dt_command switcher', 'dt_theme_ids() { printf "nord\\n"; }; dt_command switcher')
        self.terminal(script, steps=((b'Number (', b'1\r'), (b'Number [1]', b'2\r')), timeout=45)
        self.assertEqual(self.dots('theme', 'current').stdout.strip(), 'nord')
        self.assertEqual(len(list((self.state / 'generations').glob('g.*'))), 1)

    def test_dumb_terminal_ignores_ui_tools(self):
        self.fixture_ui(); self.fixture_ui('fzf'); self.queue()
        self.terminal(steps=((b'Number (', b'\x04'),), env=dict(self.env, TERM='dumb'), code=130)
        self.assertFalse(self.calls.exists())

    def test_color_precedence(self):
        self.fixture_ui()
        for mode, no_color, expected in [('auto', '1', '1|0'), ('always', '1', '|1'), ('never', '', '1|0'), ('auto', '', '|1')]:
            self.queue()
            (self.home / 'policy').unlink(missing_ok=True)
            self.terminal(env=dict(self.env, DOTS_COLOR=mode, NO_COLOR=no_color))
            self.assertTrue(all(x.startswith(expected + '|') for x in (self.home / 'policy').read_text().splitlines()))

    def test_noninteractive_and_data_paths_never_invoke_tools(self):
        self.fixture_ui(); self.fixture_ui('fzf'); self.queue()
        result = self.dots('theme', 'switcher', code=1)
        self.assertIn('terminal input and output', result.stderr)
        self.assertEqual(result.stdout, '')
        self.terminal('"$DOTS/bin/dots" theme switcher > "$HOME/output"', code=1)
        self.terminal('"$DOTS/bin/dots" theme switcher < /dev/null', code=1)
        for args in [('theme', 'switcher', '--help'), ('theme', 'list'),
                     ('theme', 'color', 'accent', '--theme', 'nord'),
                     ('completion', 'bash'), ('commands', '--check')]:
            self.dots(*args, env=dict(self.env, DOTS_COLOR='always'))
        self.assertIn('live palette preview', self.dots('theme', 'switcher', '--help').stdout)
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(NATIVE_GUM, 'native Gum unavailable')
    def test_native_gum_preview_and_cancel_widths(self):
        (self.fake / 'gum').symlink_to(NATIVE_GUM)
        self.env['PICKER_TOOLS'] = 'gum'
        for width in (40, 80, 120):
            with self.subTest(width=width):
                out = self.terminal(steps=((b'Type to filter', b'nord\r'),
                                           (b'Theme action', b'jj\r')), width=width)
                self.assertIn(b'nord (dark)', out)
                self.assertIn(b'Cancelled', out)
                # Cursor-control sequences are expected; color SGRs are not.
                self.assertNotRegex(out, rb'\x1b\[[0-9;]*(?:3[0-9]|4[0-9]|9[0-7]|10[0-7])[;m]')
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(NATIVE_GUM, 'native Gum unavailable')
    def test_native_gum_escape_and_interrupt(self):
        (self.fake / 'gum').symlink_to(NATIVE_GUM)
        self.env['PICKER_TOOLS'] = 'gum'
        # Gum 2.0 needs Escape to leave search, then Escape to quit.
        self.terminal(steps=((b'Type to filter', b'\x1b'), (b'', b'\x1b')), code=1)
        self.terminal(steps=((b'Type to filter', b'\x03'),), code=130)
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(NATIVE_GUM, 'native Gum unavailable')
    def test_native_gum_forced_color_and_icons(self):
        (self.fake / 'gum').symlink_to(NATIVE_GUM)
        env = dict(self.env, PICKER_TOOLS='gum', DOTS_COLOR='always', DOTS_ICONS='always',
                   NO_COLOR='1', GUM_FILTER_PROMPT_FOREGROUND='#123456')
        out = self.terminal(steps=((b'Type to filter', b'nord\r'),
                                   (b'Theme action', b'jj\r')), env=env)
        self.assertRegex(out, rb'\x1b\[[0-9;]*(?:38|34|94)[;m]')
        self.assertIn(b'Cancelled', out)
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(NATIVE_FZF, 'native FZF unavailable')
    def test_native_fzf_preview_and_cancel(self):
        (self.fake / 'fzf').symlink_to(NATIVE_FZF)
        self.env['PICKER_TOOLS'] = 'fzf'
        script = self.script.replace('dt_command switcher',
                                     'dt_theme_ids() { printf "catppuccin-frappe\\nnord\\n"; }; dt_command switcher')
        for width in (40, 80, 120):
            with self.subTest(width=width):
                out = self.terminal(script, width=width,
                                    steps=((b'Theme:', b'nord'), (b'nord (dark)', b'\x03')), code=130)
                self.assertIn(b'foreground', out)
                self.assertNotRegex(out, rb'\x1b\[[0-9;]*(?:38|48);2;')
                self.assertFalse(self.state.exists())
        out = self.terminal(script, env=dict(self.env, DOTS_COLOR='always', NO_COLOR='1'),
                            steps=((b'Theme:', b'nord'), (b'nord (dark)', b'\r'), (b'Number [1]', b'3\r')))
        self.assertRegex(out, rb'\x1b\[[0-9;]*(?:38|48);2;')
        self.assertIn(b'Cancelled', out)
        self.assertFalse(self.state.exists())


for name in dir(old.Themes):
    if name.startswith('test_') and name not in Picker.__dict__:
        setattr(Picker, name, None)

if __name__ == '__main__':
    unittest.main()
