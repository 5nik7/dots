#!/usr/bin/env python3
"""Battery/status contracts in owned homes; optional native tmux and battery source."""
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

REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
TMUX = shutil.which('tmux')
INDICATORS = '#[fg=blue]#{?pane_in_mode,COPY ,}#{?client_prefix,PREFIX ,}#{?window_zoomed_flag,ZOOM ,}'


@unittest.skipUnless(BASH, 'Bash unavailable')
class TmuxStatus(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dt-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / 'home space ü'
        self.config = self.home / 'config space ü'
        self.tmux_config = self.config / 'tmux'
        self.tmux_config.mkdir(parents=True)
        self.prefix = self.root / 'prefix'
        self.tools = self.prefix / 'bin'
        self.tools.mkdir(parents=True)
        self.battery = self.home / 'repos/battery/battery'
        self.battery.parent.mkdir(parents=True)
        self.adapter = self.tmux_config / 'battery-status.sh'
        shutil.copy2(REPO / 'config/tmux/battery-status.sh', self.adapter)
        self.env = {key: os.environ[key] for key in ('PATH', 'PREFIX', 'LD_PRELOAD', 'LD_LIBRARY_PATH') if key in os.environ}
        self.env.update(HOME=str(self.home), PREFIX=str(self.prefix), XDG_CONFIG_HOME=str(self.config),
                        XDG_CACHE_HOME=str(self.root / 'cache'), XDG_STATE_HOME=str(self.root / 'state'),
                        XDG_DATA_HOME=str(self.root / 'data'), XDG_RUNTIME_DIR=str(self.root / 'run'),
                        TMPDIR=str(self.root), SHELL=BASH, TERM='xterm-256color', LANG='C.UTF-8',
                        PATH=str(self.tools) + os.pathsep + self.env.get('PATH', ''))
        (self.root / 'run').mkdir(mode=0o700)
        self.stub()

    def stub(self):
        # Match the full interface; an accidental plain/default invocation fails.
        self.battery.write_text('''[[ $# == 7 && $1 == --format && $2 == '{color}{icon} {percent}{reset}' &&
  $3 == --color && $4 == always && $5 == --color-by && $6 == percentage && $7 == --no-newline ]] || exit 91
printf 'call\\n' >> "$HOME/calls"
[[ ${BATTERY_FAIL:-0} == 0 ]] || { printf 'backend error\\n' >&2; exit 3; }
if [[ -v BATTERY_OUTPUT ]]; then printf '%s' "$BATTERY_OUTPUT"; else printf '\\033[32m󰁹 80%%\\033[0m'; fi
''')

    def run_adapter(self, **env):
        with subprocess.Popen([BASH, str(self.adapter)], env=dict(self.env, **env), cwd=self.home,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              start_new_session=True) as process:
            try:
                out, err = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise
        self.assertEqual(process.returncode, 0, err)
        self.assertEqual(err, '')
        self.assertNotIn('\x1b', out)
        return out

    def test_colors_icons_and_single_call(self):
        for code, color, icon, percentage in [(31, 'red', '󰁺', 10), (33, 'yellow', '󰁼', 30),
                                               (32, 'green', '󰁹', 100), (32, 'green', '󰂊', 80)]:
            with self.subTest(color=color, icon=icon):
                (self.home / 'calls').unlink(missing_ok=True)
                output = self.run_adapter(BATTERY_OUTPUT=f'\x1b[{code}m{icon} {percentage}%\x1b[0m',
                                          NO_COLOR='1', BATTERY_COLOR_BY='health')
                self.assertEqual(output, f'#[fg={color}]{icon} {percentage}%#[default]\n')
                self.assertEqual((self.home / 'calls').read_text(), 'call\n')
        self.assertIn('󰁹 80%', self.run_adapter(LC_ALL='C'))

    def test_failure_and_missing_checkout_clear_old_result(self):
        self.assertEqual(self.run_adapter(BATTERY_FAIL='1'), '\n')
        self.battery.unlink()
        self.assertEqual(self.run_adapter(), '\n')
        self.assertEqual((self.home / 'calls').read_text(), 'call\n')

    def test_malformed_or_unsafe_output_is_not_forwarded(self):
        for output in ['', '80%', '\x1b[36m󰁹 80%\x1b[0m', '\x1b[32m󰁹 101%\x1b[0m',
                       '\x1b[32m󰁹 -1%\x1b[0m', '\x1b[32m󰁹 80%',
                       '\x1b[32m#(touch BAD) 80%\x1b[0m', '\x1b[32m#[x] 80%\x1b[0m',
                       '\x1b[32m󰁹\t80%\x1b[0m', '\x1b[32m󰁹\n80%\x1b[0m',
                       '\x1b[32m\x1b]title 80%\x1b[0m']:
            with self.subTest(output=repr(output)):
                self.assertEqual(self.run_adapter(BATTERY_OUTPUT=output), '\n')
        self.assertFalse((self.home / 'BAD').exists())

    @unittest.skipUnless(os.environ.get('DOTS_TEST_BATTERY_SOURCE'), 'optional battery source not supplied')
    def test_upstream_thresholds_icons_and_one_mock_api_request(self):
        # Copy source, never execute the real checkout/config/API against live HOME.
        shutil.copyfile(os.environ['DOTS_TEST_BATTERY_SOURCE'], self.battery)
        # Upstream prefers PREFIX/bin over PATH: both must point at owned tools.
        self.assertEqual(self.tools, Path(self.env['PREFIX']) / 'bin')
        backend = self.tools / 'termux-battery-status'
        backend.write_text('#!' + BASH + '''
printf 'api\\n' >> "$HOME/api-calls"
printf '{"percentage":%s,"status":"%s","plugged":"UNPLUGGED","health":"GOOD","present":true}\\n' "$TEST_PERCENT" "${TEST_STATE:-DISCHARGING}"
''')
        backend.chmod(0o700)
        battery_config = self.config / 'battery/config'
        battery_config.parent.mkdir()
        battery_config.write_text("BATTERY_OPTS=(--critical 20 --low 45 --color never --color-by health --format 'overridden')\n")
        for percent, color in [(0, 'red'), (20, 'red'), (21, 'yellow'), (45, 'yellow'), (46, 'green'), (100, 'green')]:
            (self.home / 'api-calls').unlink(missing_ok=True)
            output = self.run_adapter(BATTERY_BACKEND='wrapper', TEST_PERCENT=str(percent))
            self.assertRegex(output, rf'^#\[fg={color}\].+ {percent}%#\[default\]\n$')
            self.assertEqual((self.home / 'api-calls').read_text(), 'api\n')
        ordinary = self.run_adapter(BATTERY_BACKEND='wrapper', TEST_PERCENT='50')
        charging = self.run_adapter(BATTERY_BACKEND='wrapper', TEST_PERCENT='50', TEST_STATE='CHARGING')
        self.assertNotEqual(ordinary, charging)
        self.assertIn('#[fg=green]', charging)

    def test_layout_and_template_ownership(self):
        config = (REPO / 'config/tmux/tmux.conf').read_text()
        layout = next(line for line in config.splitlines() if line.startswith('set -g status-right '))
        self.assertIn(INDICATORS + '#[default]%H:%M  #(', layout)
        self.assertNotIn('#h', layout)
        self.assertLess(config.index('source-file -q -F'), config.index(layout))
        self.assertIn('set -g status-interval 5', config)
        template = (REPO / 'default/themed/tmux.conf.tpl').read_text()
        self.assertNotIn('status-right', template)
        self.assertIn('status-style', template)

    @unittest.skipUnless(TMUX, 'native tmux unavailable')
    def test_native_config_legacy_theme_and_async_battery(self):
        config = self.tmux_config / 'tmux.conf'
        shutil.copyfile(REPO / 'config/tmux/tmux.conf', config)
        (self.tmux_config / 'dots-theme.conf').write_text('set -g status-right "OLD_LAYOUT"\n')
        socket = self.root / 'tmux.sock'
        base = [TMUX, '-S', str(socket)]

        def tmux(*args):
            result = subprocess.run(base + list(args), env=self.env, cwd=self.home,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout

        pid = None
        master = None
        try:
            tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'fixture', 'sleep 60')
            tmux('source-file', str(config))
            layout = tmux('show-option', '-gqv', 'status-right')
            self.assertIn(INDICATORS + '#[default]%H:%M  #(', layout)
            self.assertNotIn('OLD_LAYOUT', layout)
            # Reloading config is idempotent; subsequent color-only themes leave layout alone.
            tmux('source-file', str(config))
            self.assertEqual(tmux('show-option', '-gqv', 'status-right'), layout)
            colors = self.tmux_config / 'colors.conf'
            colors.write_text('set -g status-style "bg=default,fg=white"\n')
            tmux('source-file', str(colors))
            self.assertEqual(tmux('show-option', '-gqv', 'status-right'), layout)
            pid, master = pty.fork()
            if pid == 0:
                os.chdir(self.home)
                os.execve(TMUX, base + ['attach-session', '-t', 'fixture'], self.env)
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 100, 0, 0))
            output = bytearray()
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline and '󰁹 80%'.encode() not in output:
                if select.select([master], [], [], .1)[0]:
                    output.extend(os.read(master, 65536))
            self.assertIn('󰁹 80%'.encode(), output)
            self.assertRegex(bytes(output), rb'\d\d:\d\d')
            self.assertNotIn(b'OLD_LAYOUT', output)
            self.assertNotIn(b'#[fg=', output)
            self.assertTrue((self.home / 'calls').exists())
        finally:
            subprocess.run(base + ['kill-server'], env=self.env, capture_output=True, timeout=10)
            if pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)
            if master is not None:
                os.close(master)


if __name__ == '__main__':
    unittest.main()
