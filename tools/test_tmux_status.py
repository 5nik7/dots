#!/usr/bin/env python3
"""Battery/status contracts in owned homes; optional native tmux and battery source."""
from datetime import datetime
import os
import json
import runpy
import sys
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
TMUX = shutil.which('tmux')
INDICATORS = '#[fg=#{@dots-indicator-fg},bg=#{@dots-indicator-bg},bold]#{?pane_in_mode, COPY ,}#[default]#[fg=#{@dots-prefix-fg},bg=#{@dots-prefix-bg},bold]#{?client_prefix, PREFIX ,}#[default]#[fg=#{@dots-indicator-fg},bg=#{@dots-indicator-bg},bold]#{?window_zoomed_flag, ZOOM ,}'
ANDROID_ICONS = dict(notification='\U000f009a', volume='\U000f0580', location='\U000f0f08', wifi='\U000f0928', cell='\U000f08fa')


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
                        TMPDIR=str(self.root), SHELL=BASH, TERM='xterm-256color', LANG='C.UTF-8', TZ='UTC',
                        PATH=str(self.tools) + os.pathsep + self.env.get('PATH', ''))
        (self.root / 'run').mkdir(mode=0o700)
        self.stub()
        self.repo = self.root / 'repo space ü'
        source = self.repo / 'config/tmux/termux-status.py'
        source.parent.mkdir(parents=True)
        shutil.copyfile(REPO / 'config/tmux/termux-status.py', source)
        self.termux_adapter = self.tmux_config / 'termux-status.py'
        self.termux_adapter.symlink_to(source)
        self.sessions_script = self.repo / 'androidots/bin/termux-sessions'
        self.sessions_script.parent.mkdir(parents=True)
        self.sessions_script.write_text("""import os, pathlib, sys, time
assert sys.argv[1:] == ['--json']
home = pathlib.Path(os.environ['HOME'])
with (home / 'session-calls').open('a') as stream: stream.write('call\\n')
if (home / 'session-delay').exists(): time.sleep(2)
print((home / 'sessions.json').read_text())
""")
        self.snapshot([])
        android_source = source.with_name('android-status.py')
        shutil.copyfile(REPO / 'config/tmux/android-status.py', android_source)
        self.android_adapter = self.tmux_config / android_source.name
        self.android_adapter.symlink_to(android_source)
        self.android_scripts = {}
        for module in ANDROID_ICONS:
            script = self.sessions_script.with_name('termux-' + module + '-status')
            self.android_scripts[module] = script
            script.write_text('import os, pathlib, sys, time\n' +
                              'assert sys.argv[1:] == ["--json"]\n' +
                              f'module = {module!r}\n' + '''home = pathlib.Path(os.environ['HOME'])
with (home / (module + '-calls')).open('a') as stream: stream.write('call\\n')
print('PRIVATE provider stderr', file=sys.stderr)
if (home / (module + '-fail')).exists(): sys.exit(1)
if (home / (module + '-delay')).exists(): time.sleep(10)
print((home / (module + '.json')).read_text())
''')
            self.android_snapshot(module)

        weather_source = source.with_name('weather-status.py')
        shutil.copyfile(REPO / 'config/tmux/weather-status.py', weather_source)
        (self.tmux_config / weather_source.name).symlink_to(weather_source)
        self.weather_script = self.repo / 'lib/dots/wttr/cli.py'
        self.weather_script.parent.mkdir(parents=True)
        self.weather_script.write_text("import os, pathlib, sys, time\nassert sys.argv[1:] == ['--daylight']\nhome = pathlib.Path(os.environ['HOME'])\nwith (home / 'weather-calls').open('a') as stream: stream.write('call\\n')\nprint('PRIVATE weather stderr', file=sys.stderr)\nif (home / 'weather-delay').exists(): time.sleep(10)\nif (home / 'weather-fail').exists(): sys.exit(1)\nprint((home / 'daylight').read_text())\n")
        self.weather_stub()

    def weather_stub(self, value='day'):
        (self.home / 'daylight').write_text(value)

    def android_snapshot(self, module, icon=None, stale=False, count=3, connected=True,
                         data_enabled=True, data_state="connected", device_stale=None):
        icon = (icon or ANDROID_ICONS[module]) + ('~' if stale else '')
        state = dict(wifi='connected', cell='registered', notification='active', location='unknown', volume='medium')[module]
        data = dict(module=module, icon=icon, stale=stale, state=state,
                    data={'count': count, 'level': 4, 'connected': connected,
                          'data_enabled': data_enabled, 'data_state': data_state,
                          'device_stale': stale if device_stale is None else device_stale}, error='PRIVATE error', text='PRIVATE label')
        (self.home / (module + '.json')).write_text(json.dumps(data))

    def android_text(self, stale=False, network='wifi'):
        return ANDROID_ICONS[network] + ('~' if stale else ' ')

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

    def snapshot(self, terminals):
        data = {'count': len(terminals), 'sessions': [
            {'pid': 900 + index, 'tty': tty.removeprefix('/dev/'), 'command': '#(touch BAD)'}
            for index, tty in enumerate(terminals)]}
        (self.home / 'sessions.json').write_text(json.dumps(data))

    def run_sessions(self, tty='/dev/pts/2', colors=None):
        colors = colors or ['#112233', '#445566', '#abcdef', '#010203']
        result = subprocess.run([sys.executable, '-B', str(self.termux_adapter), '--tty=' + tty, *colors],
                                cwd=self.home, env=self.env, capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def test_session_snapshot_order_client_selection_and_removal(self):
        self.assertEqual(self.run_sessions(), '\n')
        self.snapshot(['pts/9', 'pts/2', 'pts/4'])
        calls = self.home / 'session-calls'
        calls.unlink()
        first = self.run_sessions()
        self.assertEqual(calls.read_text(), 'call\n')
        self.assertEqual(re.sub(r'#\[[^]]*\]', '', first), ' 1  2  3 \n')
        self.assertIn('#[list=focus,bg=#abcdef,fg=#010203,nobold,nounderscore] 2 ', first)
        self.assertIn('#[list=focus,bg=#abcdef,fg=#010203,nobold,nounderscore] 3 ',
                      self.run_sessions('/dev/pts/4'))
        self.assertNotIn('list=focus', self.run_sessions('/dev/pts/999'))
        self.assertNotIn('touch', first)
        self.assertFalse((self.home / 'BAD').exists())
        self.snapshot(['pts/4'])
        output = self.run_sessions('/dev/pts/4')
        self.assertIn('] 1 ', output)
        self.assertNotIn('] 3 ', output)

    def test_bounded_session_numbers(self):
        render = runpy.run_path(str(self.termux_adapter))['render']
        snapshot = {'count': 60, 'sessions': [dict(tty=f'pts/{i}', pid=i+1) for i in range(60)]}
        colors = ['#445566', '#aabbcc', '#aabbcc', '#010203']
        for width in (10, 20, 30):
            for current in (0, 30, 59):
                result = render(snapshot, f'/dev/pts/{current}', colors, width)
                plain = re.sub(r'#\[[^]]*\]', '', result)
                self.assertLessEqual(len(plain), width)
                self.assertIn(f' {current+1} ', plain)
                self.assertNotIn('list=', result)
                self.assertIn('bg=#aabbcc,fg=#010203', result)
                if current == 30:
                    self.assertTrue(plain.startswith('<') and plain.endswith('>'), plain)
        result = render(snapshot, '/dev/pts/999', colors, 10)
        self.assertIn(' 1 ', result)
        self.assertNotIn('bg=#aabbcc', result)
        small = {'count': 2, 'sessions': snapshot['sessions'][:2]}
        self.assertEqual(re.sub(r'#\[[^]]*\]', '', render(small, 'pts/0', colors, 20)), ' 1  2 ')
        self.assertEqual(render(small, 'pts/0', colors, 0), '')
        with self.assertRaises(ValueError):
            render(small, 'pts/0', colors, -1)

    def test_split_numbers_keep_order_and_combined_width(self):
        render = runpy.run_path(str(self.termux_adapter))['render']
        snapshot = {'count': 3, 'sessions': [dict(tty=f'pts/{i}', pid=i+1) for i in range(3)]}
        colors = ['#445566', '#aabbcc', '#aabbcc', '#010203']
        for tty, before, after in [('pts/0', ' 1 ', ' 2  3 '),
                                   ('pts/1', ' 1  2 ', ' 3 '),
                                   ('pts/2', ' 1  2  3 ', ''),
                                   ('pts/99', ' 1  2  3 ', '')]:
            result = render(snapshot, tty, colors, 20, split_current=True)
            self.assertEqual(re.sub(r'#\[[^]]*\]', '', result), before + '|' + after)
            self.assertNotIn('list=', result)
        for width in (0, 3, 6, 8):
            result = re.sub(r'#\[[^]]*\]', '', render(snapshot, 'pts/1', colors, width, True))
            self.assertEqual(result.count('|'), 1)
            self.assertLessEqual(len(result.replace('|', '')), width)
            if width >= 3:
                self.assertIn(' 2 |', result)

    def test_session_failures_clear_output(self):
        invalid = ['not json', '{}', '[]', '{"count":true,"sessions":[]}',
                   '{"count":2,"sessions":[]}',
                   '{"count":1,"sessions":[{"pid":1,"tty":"pts/2#[bad]"}]}',
                   '{"count":1,"sessions":[{"pid":true,"tty":"pts/2"}]}',
                   '{"count":2,"sessions":[{"pid":1,"tty":"pts/2"},{"pid":2,"tty":"pts/2"}]}']
        for data in invalid:
            with self.subTest(data=data):
                (self.home / 'sessions.json').write_text(data)
                self.assertEqual(self.run_sessions(), '\n')
        self.snapshot(['pts/2'])
        self.assertEqual(self.run_sessions(colors=['#000000]#(bad)', 'white', 'cyan', 'black']), '\n')
        (self.home / 'session-delay').touch()
        started = time.monotonic()
        self.assertEqual(self.run_sessions(), '\n')
        self.assertLess(time.monotonic() - started, 2)
        (self.home / 'session-delay').unlink()
        self.sessions_script.unlink()
        self.assertEqual(self.run_sessions(), '\n')

    def test_split_badge_keeps_numbers_and_padding_separate(self):
        render = runpy.run_path(str(self.termux_adapter))['render']
        snapshot = {'count': 3, 'sessions': [dict(tty=f'pts/{i}', pid=i+1) for i in range(3)]}
        colors = ['#112233', '#aabbcc', '#aabbcc', '#010203']
        for tty, expected in [('pts/0', '|1| 2  3 '),
                              ('pts/1', ' 1 |2| 3 '),
                              ('pts/2', ' 1  2 |3|'),
                              ('pts/99', ' 1  2  3 ||')]:
            output = render(snapshot, tty, colors, 20, split_badge=True)
            self.assertEqual(re.sub(r'#\[[^]]*\]', '', output), expected)
            self.assertNotIn('list=', output)
            self.assertNotIn('nobold', output)
        for width in range(11):
            output = re.sub(r'#\[[^]]*\]', '', render(snapshot, 'pts/1', colors, width, split_badge=True))
            before, current, after = output.split('|')
            # The current number's two spaces are supplied by the tmux badge.
            self.assertLessEqual(len(before + current + after) + (2 if current else 0), width)
            if width >= 3:
                self.assertEqual(current, '2')
        with self.assertRaises(ValueError):
            render(snapshot, 'pts/1', colors, split_current=True, split_badge=True)

    def test_layout_and_template_ownership(self):
        config = (REPO / 'config/tmux/tmux.conf').read_text()
        left = next(line for line in config.splitlines() if line.startswith('set -g status-left '))
        right = next(line for line in config.splitlines() if line.startswith('set -g status-right '))
        self.assertIn(INDICATORS, right)
        self.assertNotIn('battery', right)
        self.assertNotIn('%', left)
        self.assertLess(config.index('source-file -q -F'), config.index(left))
        self.assertIn('set -g status-interval 5', config)
        self.assertIn('set -g detach-on-destroy on', config.split("if-shell -F '#{!=:#{TERMUX_VERSION},}'")[1])
        template = (REPO / 'default/themed/tmux.conf.tpl').read_text()
        for option in ['status-right', 'set -g status-left ', 'set -g status-format', 'set -g status 2']:
            self.assertNotIn(option, template)
        self.assertIn('nounderscore', template)

    def server(self, name, termux=True):
        base = [TMUX, '-S', str(self.root / (name + '.sock'))]
        env = dict(self.env)
        if termux:
            env['TERMUX_VERSION'] = 'fixture'
        def tmux(*args):
            result = subprocess.run(base + list(args), env=env, cwd=self.home,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.rstrip('\n')
        tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'fixture', 'sleep 120')
        self.addCleanup(lambda: subprocess.run(base + ['kill-server'], env=env,
                                               capture_output=True, timeout=10))
        return tmux, base

    def write_config(self):
        config = self.tmux_config / 'tmux.conf'
        shutil.copyfile(REPO / 'config/tmux/tmux.conf', config)
        return config

    def write_theme(self, accent='#abcdef', background='#112233', dark_background='#223344'):
        palette = dict(background=background, foreground='#eeeeee', accent=accent,
                       muted='#888888', light_foreground='#ccddee', info='#123456', selection='#654321',
                       dark_background=dark_background, lighter_background='#445566', dark_foreground='#778899',
                       blue='#0000ff', hint='#aabbcc', darker_background='#010203', red='#ff0000', yellow='#ffff00', green='#00ff00')
        template = (REPO / 'default/themed/tmux.conf.tpl').read_text()
        path = self.tmux_config / 'dots-theme.conf'
        path.write_text(re.sub(r'\{\{ (\w+) \}\}', lambda m: palette[m[1]], template))
        return path

    def test_weather_adapter_bounds_and_recovery(self):
        adapter=self.tmux_config / 'weather-status.py'
        def read():
            started=time.monotonic()
            result=subprocess.run([sys.executable,'-B',str(adapter)],env=self.env,capture_output=True,text=True,timeout=3)
            self.assertLess(time.monotonic()-started,2)
            self.assertEqual((result.returncode,result.stderr),(0,''))
            return result.stdout
        for value,expected in [('day','day'),('night','night'),('unknown','unknown'),
                               ('#[fg=red]BAD','unknown'),('x'*100000,'unknown')]:
            self.weather_stub(value)
            self.assertEqual(read(),expected+'\n')
        self.weather_stub('day')
        for failure in ('weather-fail','weather-delay'):
            (self.home/failure).touch()
            self.assertEqual(read(),'unknown\n')
            (self.home/failure).unlink()
            self.assertEqual(read(),'day\n')
        self.weather_script.unlink()
        self.assertEqual(read(),'unknown\n')

    @unittest.skipUnless(TMUX, 'native tmux unavailable')
    def test_native_layout_reload_theme_and_platform_gate(self):
        config = self.write_config()
        (self.tmux_config / 'dots-theme.conf').write_text(
            'set -g status-right "OLD_LAYOUT"\nset -g status-left "OLD_LEFT"\n'
            'set -g window-status-current-style underscore\n')
        tmux, _ = self.server('layout')
        tmux('source-file', str(config))
        self.assertEqual(tmux('show-option', '-gqv', 'status'), '2')
        self.assertIn('#[fg=black,bg=green,bold]', tmux('display-message', '-p', '#{E:status-right}'))
        rows = tmux('show-option', '-g', 'status-format')
        self.assertIn('termux-status.py', tmux('show-option', '-gqv', '@dots-termux-numbers'))
        self.assertNotIn('OLD_LAYOUT', tmux('display-message', '-p', '#{E:@dots-tmux-row}'))
        self.assertNotIn('OLD_LEFT', tmux('show-option', '-gqv', 'status-left'))
        clock = re.search(r'%[^ ]+', tmux('show-option', '-gqv', 'status-format[0]')).group()
        for hour, minute, expected in [(0, 0, '12:00'), (6, 30, '6:30'),
                                       (12, 0, '12:00'), (18, 30, '6:30')]:
            self.assertEqual(datetime(2026, 10, 14, hour, minute).strftime(clock), expected)
        tmux('source-file', str(config))
        self.assertEqual(tmux('show-option', '-g', 'status-format'), rows)
        tmux('set-option', '-t', '=fixture:', '@dots-termux-default', '1')
        self.assertEqual(re.sub(r'#\[[^]]*\]', '', tmux('display-message', '-p', '#{E:status-left}')), '')
        tmux('source-file', str(config))
        self.assertEqual(re.sub(r'#\[[^]]*\]', '', tmux('display-message', '-p', '#{E:status-left}')), '')
        tmux('set-option', '-u', '-t', '=fixture:', '@dots-termux-default')
        self.assertIn('fixture', tmux('display-message', '-p', '#{E:status-left}'))
        for accent in ['#abcdef', '#fedcba']:
            tmux('source-file', str(self.write_theme(accent)))
            self.assertIn(f'#[fg={accent},bg=#223344,bold]', tmux('display-message', '-p', '#{E:status-right}'))
            self.assertEqual(tmux('show-option', '-g', 'status-format'), rows)
            self.assertIn('bg=#aabbcc', tmux('display-message', '-p', '#{E:status-left}'))
            self.assertEqual(tmux('show-option', '-gqv', '@dots-termux-current-bg'), '#aabbcc')
            self.assertEqual(tmux('show-option', '-gqv', '@dots-termux-bg'), '#112233')
            self.assertEqual(tmux('show-option', '-gqv', '@dots-termux-inactive-bg'), '#112233')
            self.assertEqual(tmux('show-option', '-gqv', '@dots-termux-inactive-fg'), '#aabbcc')
            self.assertIn('fg=#123456,bold,nounderscore',
                          tmux('show-option', '-gqv', 'window-status-current-format'))
            self.assertEqual(tmux('show-option', '-gwqv', 'window-status-current-style'), 'nounderscore')
            self.assertEqual(tmux('show-option', '-gqv', 'pane-active-border-style'), 'fg=#654321')
            self.assertIn('bg=#445566', tmux('display-message', '-p', '#{E:window-status-current-format}'))
        tmux('set-option', '-t', '=fixture:', '@dots-termux-default', '1')
        tmux('source-file', str(self.write_theme()))
        self.assertEqual(re.sub(r'#\[[^]]*\]', '', tmux('display-message', '-p', '#{E:status-left}')), '')
        tmux('set-option', '-u', '-t', '=fixture:', '@dots-termux-default')
        tmux('set-environment', '-gu', 'TERMUX_VERSION')
        tmux('source-file', str(config))
        self.assertEqual(tmux('show-option', '-gqv', 'status'), 'on')
        row = tmux('show-option', '-gqv', 'status-format[0]')
        self.assertNotIn('termux-status', row)
        self.assertNotIn('android-status', row)
        self.assertNotIn('battery', row)
        self.assertNotIn('%', tmux('show-option', '-gqv', 'status-left'))
        other, _ = self.server('nontermux', termux=False)
        other('source-file', str(config))
        self.assertEqual(other('show-option', '-gqv', 'status'), 'on')
        self.assertIn('#[fg=#abcdef,bg=#223344,bold]', other('display-message', '-p', '#{E:status-right}'))
        self.assertIn('bg=#445566', other('display-message', '-p', '#{E:window-status-current-format}'))
        other('set-option', '-gw', 'automatic-rename', 'off')
        other('rename-window', 'fixture')
        self.assertIn(' 0:fixture ', other('display-message', '-p', '#{E:window-status-current-format}'))

    @unittest.skipUnless(TMUX, 'native tmux unavailable')
    def test_native_daylight_and_recovery(self):
        config = self.write_config()
        self.write_theme()
        inner, base = self.server('weather')
        inner('source-file', str(config))
        inner('set-option', '-g', 'status-interval', '1')
        outer, _ = self.server('weather-view', termux=False)
        outer('set-option', '-g', 'status', 'off')
        outer('set-option', '-g', 'default-terminal', 'tmux-256color')
        attach = shlex.join(['env', '-u', 'TMUX', '-u', 'TMUX_PANE', *base, 'attach-session', '-t', 'fixture'])
        outer('new-session', '-d', '-s', 'view', '-x', '80', '-y', '24', attach)
        deadline = time.monotonic() + 5
        while not inner('list-clients', '-F', '#{client_tty}'):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.05)
        for width in (40, 80, 120):
            outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
            for value, color in [('day', (255,255,0)), ('night', (0,0,255)),
                                 ('unknown', (238,238,238)), ('#[fg=red]BAD', (238,238,238)),
                                 ('day', (255,255,0))]:
                self.weather_stub(value)
                deadline = time.monotonic() + 6
                inner('refresh-client', '-S')
                while True:
                    rows = outer('capture-pane', '-p', '-e', '-t', 'view').splitlines()
                    if rows and '80%' in rows[0] and self.colors_at(rows[0], ':').get('fg') == color:
                        break
                    self.assertLess(time.monotonic(), deadline, rows)
                    time.sleep(.1)
                top = self.plain(rows[0])
                self.assertRegex(top, r'^ (?:[1-9]|1[0-2]):[0-5][0-9] ')
                self.assertEqual(self.colors_at(rows[0], ':')['bg'], (34,51,68))
                self.assertLessEqual(len(top), width)
                self.assertNotIn('PRIVATE', '\n'.join(rows))
                self.assertNotIn('BAD', top)
                for icon in ANDROID_ICONS.values(): self.assertNotIn(icon, top)
            for _ in range(2):
                inner('source-file', str(config))
                inner('set-option', '-g', 'status-interval', '1')
                self.await_screen(outer, 'view', lambda rows: bool(rows) and '80%' in rows[0])
        # Actual helper failure, deadline and disappearance all clear day color.
        for failure in ('weather-fail', 'weather-delay', 'missing'):
            if failure == 'missing': self.weather_script.unlink()
            else: (self.home / failure).touch()
            deadline = time.monotonic() + 6
            while True:
                rows = outer('capture-pane', '-p', '-e', '-t', 'view').splitlines()
                if rows and self.colors_at(rows[0], ':').get('fg') == (238,238,238): break
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.1)
            (self.home / failure).unlink(missing_ok=True)
        for module in ANDROID_ICONS:
            self.assertFalse((self.home / (module + '-calls')).exists())

    @unittest.skipUnless(TMUX, 'native tmux unavailable')
    def test_native_grouped_numbers_share_one_job(self):
        self.write_theme()
        inner, base = self.server('shared-job')
        inner('source-file', str(self.write_config()))
        inner('set-option', '-g', 'status-interval', '60')
        inner('rename-window', '-t', 'fixture:0', 'window')
        inner('set-option', '-gw', 'automatic-rename', 'off')
        job = inner('show-option', '-gqv', '@dots-termux-numbers')
        inner('set-option', '-g', '@dots-termux-numbers', job.replace('--tty=#{q:client_tty}', '--tty=/dev/pts/1'))
        self.snapshot(['pts/1', 'pts/2'])
        calls = self.home / 'session-calls'
        calls.unlink(missing_ok=True)
        outer, _ = self.server('shared-view', termux=False)
        outer('set-option', '-g', 'status', 'off')
        attach = shlex.join(['env', '-u', 'TMUX', '-u', 'TMUX_PANE', *base, 'attach-session', '-t', 'fixture'])
        outer('new-session', '-d', '-s', 'view', '-x', '80', '-y', '24', attach)
        lines = self.await_screen(outer, 'view', lambda rows:
            len(rows) > 1 and ' 1:fixture ' in rows[1] and '0:window' in rows[1] and ' 2 ' in rows[1])
        row = self.plain(lines[1])
        self.assertLess(row.index(' 1:fixture '), row.index('fixture'))
        self.assertLess(row.index('0:window'), row.index(' 2 '))
        self.assertEqual(calls.read_text(), 'call\n')
        self.assertRegex(row, r'^ 1:fixture  0:window  2 *$')
        self.assertEqual(self.colors_at(lines[1], ' 2 '),
                         {'fg': (170, 187, 204), 'bg': (17, 34, 51)})

    @staticmethod
    def plain(text):
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    @unittest.skipUnless(TMUX, 'native tmux unavailable')
    def test_native_compact_badges_names_and_padding(self):
        self.write_theme()
        inner, base = self.server('compact')
        config = self.write_config()
        inner('source-file', str(config))
        inner('set-option', '-g', 'status-interval', '1')
        inner('set-option', '-gw', 'automatic-rename', 'off')
        inner('set-option', '-g', 'renumber-windows', 'off')
        inner('rename-session', 'dots')
        inner('rename-window', '-t', 'dots:0', 'dots')
        inner('new-window', '-d', '-t', 'dots:1', '-n', 'shell', 'sleep 120')
        outer, _ = self.server('compact-view', termux=False)
        outer('set-option', '-g', 'status', 'off')
        attach = shlex.join(['env', '-u', 'TMUX', '-u', 'TMUX_PANE', *base, 'attach-session', '-t', 'dots'])
        outer('new-session', '-d', '-s', 'view', '-x', '80', '-y', '24', attach)
        tty = outer('display-message', '-p', '-t', 'view', '#{pane_tty}')
        self.snapshot([tty, 'pts/99999'])

        def row_equals(expected):
            return self.await_screen(outer, 'view', lambda rows:
                len(rows) > 1 and rows[1].rstrip() == expected.rstrip())

        for width in (40, 80, 120):
            outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
            rows = row_equals(' 1:dots  0  1:shell  2 ')
            self.assertEqual(self.colors_at(rows[1], '1:dots'),
                             {'fg': (1, 2, 3), 'bg': (170, 187, 204)})
            self.assertEqual(self.colors_at(rows[1], ' 0 '),
                             {'fg': (18, 52, 86), 'bg': (68, 85, 102)})
            self.assertEqual(self.colors_at(rows[1], '1:shell'),
                             {'fg': (204, 221, 238), 'bg': (34, 51, 68)})
            self.assertEqual(self.colors_at(rows[1], ' 2 '),
                             {'fg': (170, 187, 204), 'bg': (17, 34, 51)})
            clock = re.search(r'[0-9]+:[0-9]{2}', self.plain(rows[0]))[0]
            self.assertEqual(self.colors_at(rows[0], clock),
                             {'fg': (255, 255, 0), 'bg': (34, 51, 68)})
            self.assertNotIn('\x1b[4m', rows[1])
            inner('select-window', '-t', 'dots:1')
            row_equals(' 1:dots  0  1:shell  2 ')
            inner('rename-window', '-t', 'dots:0', 'Dots')
            row_equals(' 1:dots  0:Dots  1:shell  2 ')
            inner('set-option', '-t', 'dots', '@dots-termux-default', '1')
            row_equals(' 1  0:Dots  1:shell  2 ')
            inner('rename-window', '-t', 'dots:0', 'dots')
            row_equals(' 1  0  1:shell  2 ')
            inner('set-option', '-u', '-t', 'dots', '@dots-termux-default')
            inner('select-window', '-t', 'dots:0')
            for _ in range(2):
                inner('source-file', str(config))
                inner('set-option', '-g', 'status-interval', '1')
                row_equals(' 1:dots  0  1:shell  2 ')
            inner('source-file', str(self.write_theme()))
            row_equals(' 1:dots  0  1:shell  2 ')
            self.snapshot(['pts/99999', tty])
            row_equals(' 1  2:dots  0  1:shell ')
            self.snapshot([tty, 'pts/99999'])
        # Names stay literal and comparisons precede clipping; neither a pipe
        # nor tmux-format punctuation is part of the numeric helper protocol.
        outer('resize-window', '-t', 'view', '-x', '120', '-y', '24')
        for name in ('猫项目', 'a|b', 'a,b', '#[fg=red]', '#{pane_id}', '#(touch BAD)', '$(touch BAD)'):
            inner('rename-session', '#{l:' + name + '}')
            inner('rename-window', '-t', ':0', '#{l:' + name + '}')
            row_equals(f' 1:{name}  0  1:shell  2 ')
            self.assertFalse((self.home / 'BAD').exists())
            inner('rename-window', '-t', ':1', '#{l:' + name + '}')
            row_equals(f' 1:{name}  0  1  2 ')
            inner('rename-window', '-t', ':1', 'shell')
        inner('rename-session', 'project-long-name-that-will-be-clipped')
        inner('rename-window', '-t', ':0', 'project-long-name-that-will-be-clipped')
        outer('resize-window', '-t', 'view', '-x', '40', '-y', '24')
        row_equals(' 1:projec  0  1:shell  2 ')
        inner('set-option', '-g', '@dots-termux-badge-width', '3')
        row_equals(' 1  0  1:shell  2 ')

    @staticmethod
    def colors_at(text, needle):
        colors = {'fg': None, 'bg': None}
        for match in re.finditer(r'\x1b\[([0-9;]*)m', text[:text.index(needle)]):
            codes = [int(code or '0') for code in match[1].split(';')]
            index = 0
            while index < len(codes):
                code = codes[index]
                if code == 0:
                    colors = {'fg': None, 'bg': None}
                elif code in (38, 48) and codes[index + 1:index + 2] == [2]:
                    colors['fg' if code == 38 else 'bg'] = tuple(codes[index + 2:index + 5])
                    index += 4
                elif 30 <= code <= 37:
                    colors['fg'] = code - 30
                elif code in (39, 49):
                    colors['fg' if code == 39 else 'bg'] = None
                index += 1
        return colors

    def await_screen(self, outer, target, predicate):
        deadline = time.monotonic() + 8
        screen = ''
        while time.monotonic() < deadline:
            screen = outer('capture-pane', '-p', '-e', '-t', target)
            if predicate(self.plain(screen).splitlines()):
                return screen.splitlines()
            time.sleep(.1)
        self.fail('status did not render: ' + repr(screen))

    @staticmethod
    def bold_at(text, needle):
        bold = False
        for match in re.finditer(r'\x1b\[([0-9;]*)m', text[:text.index(needle)]):
            codes = [int(code or '0') for code in match[1].split(';')]
            index = 0
            while index < len(codes):
                code = codes[index]
                if code in (0, 22):
                    bold = False
                elif code == 1:
                    bold = True
                elif code in (38, 48):
                    if codes[index + 1:index + 2] == [2]:
                        index += 4
                    elif codes[index + 1:index + 2] == [5]:
                        index += 2
                index += 1
        return bold

    @unittest.skipUnless(TMUX, 'native tmux unavailable')
    def test_native_two_clients_widths_colors_and_failure_clearing(self):
        config = self.write_config()
        self.write_theme()
        inner, base = self.server('inner')
        inner('source-file', str(config))
        inner('set-option', '-g', 'status-interval', '1')
        inner('rename-window', '-t', 'fixture:0', 'window')
        inner('set-option', '-gw', 'automatic-rename', 'off')
        outer, _ = self.server('viewers', termux=False)
        outer('set-option', '-g', 'status', 'off')
        outer('set-option', '-g', 'default-terminal', 'tmux-256color')
        attach = shlex.join(['env', '-u', 'TMUX', '-u', 'TMUX_PANE', *base, 'attach-session', '-t', 'fixture'])
        terminals = []
        for name in ['one', 'two']:
            outer('new-session', '-d', '-s', name, '-x', '80', '-y', '24', attach)
            terminals.append(outer('display-message', '-p', '-t', name, '#{pane_tty}'))
        self.snapshot(['pts/9999', *terminals])
        deadline = time.monotonic() + 5
        while len(inner('list-clients', '-F', '#{client_tty}').splitlines()) != 2:
            self.assertLess(time.monotonic(), deadline, 'both fixture clients must finish attaching')
            time.sleep(.05)
        for width in [40, 80, 120]:
            for index, name in enumerate(['one', 'two'], 2):
                badge_name = 'fixture'[:min(width // 4, 30) - 4]
                outer('resize-window', '-t', name, '-x', str(width), '-y', '24')
                inner('refresh-client', '-S')
                lines = self.await_screen(outer, name, lambda rows:
                    len(rows) > 1 and f' {index}:{badge_name} ' in rows[1] and '80%' in rows[0]
                    and badge_name in rows[1])
                top, bottom = map(self.plain, lines[:2])
                self.assertRegex(top, r'^ (?:[1-9]|1[0-2]):[0-5][0-9] ')
                self.assertRegex(top, r' (?:[1-9]|1[0-2]):[0-5][0-9] ')
                self.assertLess(bottom.index(f' {index}:{badge_name} '), bottom.index(badge_name))
                self.assertLess(bottom.index(badge_name), bottom.index('0:window'))
                if index == 2:
                    self.assertLess(bottom.index('0:window'), bottom.index(' 3 '))
                else:
                    self.assertLess(bottom.index(' 2 '), bottom.index(' 3:'))
                self.assertNotIn('|', bottom)
                self.assertNotIn('80%', bottom)
                self.assertNotIn(self.android_text(), top)
                self.assertNotIn(self.android_text(), bottom)
                self.assertIn('0:window', bottom)
                self.assertEqual(self.colors_at(lines[1], '0:window')['bg'], (68, 85, 102))
                # Capture through an outer fixture tmux: real rendered cells and attributes.
                self.assertIn('48;2;68;85;102', lines[1])
                self.assertIn('48;2;17;34;51', lines[0])
                self.assertIn('38;2;170;187;204', lines[1])
                self.assertEqual(self.colors_at(lines[0], '80%'),
                                 {'fg': (0, 255, 0), 'bg': (17, 34, 51)})
                self.assertIn('38;2;1;2;3', lines[1])
                self.assertIn('48;2;170;187;204', lines[1])
                active = re.search(rf'38;2;1;2;3[^m]*m(?:\x1b\[[0-9;]*m)* ([0-9]+):{badge_name} ', lines[1])
                self.assertIsNotNone(active, lines[0])
                self.assertEqual(int(active[1]), index)
                self.assertNotIn('\x1b[4m', lines[1])
                inner('set-option', '-t', '=fixture:', '@dots-termux-default', '1')
                self.await_screen(outer, name, lambda rows:
                    len(rows) > 1 and '80%' in rows[0] and '0:window' in rows[1]
                    and ':fixt' not in rows[1])
                inner('set-option', '-u', '-t', '=fixture:', '@dots-termux-default')
        # Verify native mouse targets beside the number strip and badge.
        # The fixture predates config loading and starts at window zero.
        inner('set-option', '-g', 'renumber-windows', 'off')
        inner('new-window', '-d', '-t', 'fixture', '-n', 'other', 'sleep 120')
        inner('set-option', '-w', '-t', 'fixture:1', 'automatic-rename', 'off')
        for width in (40, 80, 120):
            outer('resize-window', '-t', 'one', '-x', str(width), '-y', '24')
            lines = self.await_screen(outer, 'one', lambda rows:
                len(rows) > 1 and '0:window' in rows[1] and '1:other' in rows[1])
            self.assertEqual(self.colors_at(lines[1], '0:window'),
                             {'fg': (18, 52, 86), 'bg': (68, 85, 102)})
            self.assertEqual(self.colors_at(lines[1], '1:other'),
                             {'fg': (204, 221, 238), 'bg': (34, 51, 68)})
            x = self.plain(lines[1]).index('1:other') + 1
            time.sleep(.5)  # Separate clicks, not double/triple-click gestures.
            outer('send-keys', '-t', 'one', '-l', f'\x1b[<0;{x};2M\x1b[<0;{x};2m')
            deadline = time.monotonic() + 3
            while inner('display-message', '-p', '-t', 'fixture', '#{window_index}') != '1':
                self.assertLess(time.monotonic(), deadline, 'window mouse target moved with prefix')
                time.sleep(.05)
            inner('select-window', '-t', 'fixture:0')
        inner('kill-window', '-t', 'fixture:1')
        # Long project badges are bounded by each client's current width.
        long_name = 'project-' + 'x' * 60
        inner('rename-session', '-t', 'fixture', long_name)
        for width in (40, 80, 120):
            outer('resize-window', '-t', 'one', '-x', str(width), '-y', '24')
            label = long_name[:min(width // 4, 30) - 4]
            lines = self.await_screen(outer, 'one', lambda rows:
                len(rows) > 1 and label + ' ' in rows[1] and '0:window' in rows[1]
                and long_name[:len(label)+1] not in rows[1])
            self.assertLessEqual(len(self.plain(lines[1])), width)
        inner('rename-session', '-t', long_name, 'fixture')
        # COPY/ZOOM use green; PREFIX independently uses accent on dark_background.
        original_right = inner('show-option', '-gqv', 'status-right')
        inner('set-option', '-g', 'status-right', original_right + 'DOTS_RESET')
        def assert_indicator(lines, label):
            self.assertNotIn(label, self.plain(lines[0]))
            expected = ({'fg': (171, 205, 239), 'bg': (34, 51, 68)} if label == 'PREFIX'
                        else {'fg': (1, 2, 3), 'bg': (0, 255, 0)})
            padded = ' ' + label + ' '
            self.assertIn(padded, self.plain(lines[1]))
            self.assertEqual(self.colors_at(lines[1], padded),
                             expected)
            self.assertEqual(self.colors_at(lines[1], label),
                             expected)
            self.assertTrue(self.bold_at(lines[1], label))
            self.assertEqual(self.colors_at(lines[1], 'DOTS_RESET')['bg'], (17, 34, 51))
            self.assertFalse(self.bold_at(lines[1], 'DOTS_RESET'))

        main_pane = inner('display-message', '-p', '-t', 'fixture:0', '#{pane_id}')
        inner('copy-mode', '-t', main_pane)
        lines = self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and 'COPY' in rows[1])
        assert_indicator(lines, 'COPY')
        inner('send-keys', '-X', '-t', main_pane, 'cancel')
        outer('send-keys', '-t', 'one', 'C-Space')
        lines = self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and 'PREFIX' in rows[1])
        assert_indicator(lines, 'PREFIX')
        outer('send-keys', '-t', 'one', 'Escape')
        extra_pane = inner('split-window', '-d', '-P', '-F', '#{pane_id}', '-t', 'fixture:0', 'sleep 120')
        inner('resize-pane', '-Z', '-t', main_pane)
        lines = self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and 'ZOOM' in rows[1])
        assert_indicator(lines, 'ZOOM')
        # All three may be active together; PREFIX must not recolor its neighbors.
        inner('copy-mode', '-t', main_pane)
        outer('send-keys', '-t', 'one', 'C-Space')
        lines = self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and
                                  all(label in rows[1] for label in ('COPY', 'PREFIX', 'ZOOM')))
        for label in ('COPY', 'PREFIX', 'ZOOM'):
            assert_indicator(lines, label)
        outer('send-keys', '-t', 'one', 'Escape')
        inner('send-keys', '-X', '-t', main_pane, 'cancel')
        inner('resize-pane', '-Z', '-t', main_pane)
        inner('kill-pane', '-t', extra_pane)
        inner('set-option', '-g', 'status-right', original_right)
        # A larger list scrolls around each client's current Termux entry.
        self.snapshot([f'pts/{10000+i}' for i in range(30)] + terminals +
                      [f'pts/{11000+i}' for i in range(30)])
        outer('resize-window', '-t', 'one', '-x', '40', '-y', '24')
        lines = self.await_screen(outer, 'one', lambda rows:
            len(rows) > 1 and ' 31:fixtu ' in rows[1] and '80%' in rows[0] and ('<' in rows[1] or '>' in rows[1]))
        self.assertLessEqual(len(self.plain(lines[0])), 40)
        # Both independent selections survive simultaneous number/window overflow.
        for index in range(1, 8):
            inner('new-window', '-d', '-t', f'fixture:{index}', '-n', f'window{index}', 'sleep 120')
        inner('select-window', '-t', 'fixture:7')
        lines = self.await_screen(outer, 'one', lambda rows:
            len(rows) > 1 and ' 31:fixtu ' in rows[1] and '7:window7' in rows[1]
            and ('<' in rows[1] or '>' in rows[1]))
        for index in range(7, 0, -1):
            inner('kill-window', '-t', f'fixture:{index}')
        self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and '0:window' in rows[1])
        # Theme-only refresh changes the full top-row background without replacing rows.
        inner('source-file', str(self.write_theme(background='#334455')))
        self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and ' 31:fixtu ' in rows[1])
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            colored = outer('capture-pane', '-p', '-e', '-t', 'one').splitlines()[0]
            if '48;2;51;68;85' in colored:
                break
            time.sleep(.1)
        self.assertIn('48;2;51;68;85', colored)
        for width in [40, 80, 120]:
            outer('resize-window', '-t', 'one', '-x', str(width), '-y', '24')
            lines = self.await_screen(outer, 'one', lambda rows:
                len(rows) > 1 and ' 31:fixt' in rows[1] and '󰁹 80%' in rows[0]
                and rows[0].index('󰁹') == width - 7)
            top = self.plain(lines[0])
            self.assertTrue(all(icon not in top for icon in ANDROID_ICONS.values()))
        battery_position = top.index('󰁹')
        for percent in (1, 100, 80):
            inner('set-environment', '-g', 'BATTERY_OUTPUT', f'\x1b[32m󰁹 {percent}%\x1b[0m')
            lines = self.await_screen(outer, 'one', lambda rows:
                bool(rows) and f'󰁹 {percent}%' in rows[0])
            self.assertEqual(self.plain(lines[0]).index('󰁹'), battery_position)
        inner('set-environment', '-g', 'BATTERY_FAIL', '1')
        lines = self.await_screen(outer, 'one', lambda rows: bool(rows) and '󰂑 ?%' in rows[0])
        self.assertEqual(self.plain(lines[0]).index('󰂑'), battery_position)
        inner('set-environment', '-gu', 'BATTERY_FAIL')
        # Reloading twice must preserve the cluster and both layouts.
        for _ in range(2):
            inner('source-file', str(config))
            inner('set-option', '-g', 'status-interval', '1')
            self.await_screen(outer, 'one', lambda rows:
                len(rows) > 1 and '80%' in rows[0] and '0:window' in rows[1])
        for module in ANDROID_ICONS:
            self.assertFalse((self.home / (module + '-calls')).exists())
        (self.home / 'sessions.json').write_text('broken')
        self.await_screen(outer, 'one', lambda rows:
            len(rows) > 1 and not re.search(r' 3[12]:', rows[1]) and '80%' in rows[0])
        self.snapshot([terminals[0]])
        self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and ' 1:fixture ' in rows[1] and '80%' in rows[0])
        # Simulate an unavailable Python command: the status job still clears its cache.
        python_stub = self.tools / 'python3'
        python_stub.write_text('#!' + BASH + '\nexit 127\n')
        python_stub.chmod(0o700)
        self.await_screen(outer, 'one', lambda rows: len(rows) > 1 and ' 1:fixture ' not in rows[1]
                          and all(ANDROID_ICONS[m] not in rows[0] for m in ('wifi', 'cell')) and '80%' in rows[0])
        # Outside Termux the only visible row is the tmux session/window row.
        inner('set-environment', '-gu', 'TERMUX_VERSION')
        inner('source-file', str(config))
        lines = self.await_screen(outer, 'one', lambda rows:
            bool(rows) and 'fixture' in rows[0] and '0:window' in rows[0])
        self.assertNotRegex(self.plain(lines[0]), r'[0-9]+:[0-9]{2}')
        self.assertNotIn('80%', self.plain(lines[0]))
        for module in ('wifi', 'cell'):
            self.assertNotIn(ANDROID_ICONS[module], self.plain(lines[0]))


if __name__ == '__main__':
    unittest.main()
