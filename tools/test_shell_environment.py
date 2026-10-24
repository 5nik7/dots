#!/usr/bin/env python3
"""Small native integration cases; never load the owner's shell configuration."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class ShellEnvironment(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-environment-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home space ü'
        self.home.mkdir()
        self.env = {'HOME': str(self.home), 'DOTS': str(REPO), 'PATH': os.environ['PATH'],
                    'TERM': 'dumb', 'ZDOTDIR': str(self.home), 'TMPDIR': str(self.root)}
        for key in ('CONFIG', 'STATE', 'CACHE', 'DATA'):
            self.env[f'XDG_{key}_HOME'] = str(self.home / key.lower())
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
        self.config = self.home / 'config/dots/config.env'
        self.config.parent.mkdir(parents=True)
        self.config.write_text('DOTS_INIT_THEME=0\nDOTS_INIT_COMMANDS=0\n')

    def run_shell(self, shell, script, interactive=False):
        exe = shutil.which(shell)
        if not exe:
            self.skipTest(f'{shell} unavailable')
        flags = {'bash': ['--noprofile', '--norc'], 'zsh': ['-df'],
                 'fish': ['--no-config'], 'nu': ['-n']}[shell]
        if interactive:
            flags += ['-i']
        return subprocess.run([exe, *flags, '-c', script], cwd=self.home, env=self.env,
                              text=True, capture_output=True, timeout=15)

    def env_command(self, *args, env=None, native=False):
        command = ([sys.executable, '-B', str(REPO / 'lib/dots/environment.py'), *args[1:]] if native
                   else [str(REPO / 'bin/dots'), *args])
        result = subprocess.run(command, env=env or self.env,
                                cwd=self.home, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def env_terminal(self, columns, env, native=False):
        import errno
        import fcntl
        import pty
        import select
        import struct
        import termios
        import time
        master, slave = pty.openpty()
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, columns, 0, 0))
            command = ([sys.executable, '-B', str(REPO / 'lib/dots/environment.py')] if native
                       else [str(REPO / 'bin/dots'), 'env'])
            with subprocess.Popen(command, env=env, cwd=self.home,
                                  stdout=slave, stderr=subprocess.PIPE) as process:
                os.close(slave); slave = None
                output = b''; deadline = time.monotonic() + 15
                while True:
                    if not select.select([master], [], [], max(0, deadline - time.monotonic()))[0]:
                        process.kill(); process.communicate()
                        self.fail('Timed out waiting for dots env PTY')
                    try: chunk = os.read(master, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO: break
                        raise
                    if not chunk: break
                    output += chunk
                _, error = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, error)
                return output.decode().replace('\r\n', '\n')
        finally:
            os.close(master)
            if slave is not None: os.close(slave)

    def test_environment_presentation_and_data_contracts(self):
        data = json.loads(self.env_command('env', '--json'))
        self.assertEqual(data['version'], 1)
        expected = ''.join(f"{key}={entry['value']} [{entry['source']}]\n" for key, entry in data['values'].items())
        self.assertEqual(self.env_command('env'), expected)
        forced = {**self.env, 'DOTS_COLOR':'always', 'DOTS_ICONS':'always', 'COLUMNS':'120', 'PRIVATE_SENTINEL':'not-for-display'}
        output = self.env_command('env', env=forced)
        for heading in ('Dots environment', 'Current theme', 'Settings', 'Paths'):
            self.assertIn(heading, output)
        self.assertIn('0 (disabled)', output)
        self.assertIn('1 (enabled)', output)
        self.assertIn('\x1b[95m', output)
        self.assertIn('\x1b[2m', output)
        self.assertNotIn('not-for-display', output)
        raw = self.env_command('env', '--json', env=forced)
        self.assertNotIn('\x1b', raw)
        forced_data = json.loads(raw)
        for key, entry in forced_data['values'].items():
            self.assertEqual(self.env_command('env',key,env=forced), entry['value'] + '\n')
            if key not in ('DOTS_COLOR', 'DOTS_ICONS'):
                self.assertEqual(entry, data['values'][key])
        one = json.loads(self.env_command('env','DOTS_THEME_DEFAULT','--json',env=forced))
        self.assertEqual(one, {'version':1, 'values':{'DOTS_THEME_DEFAULT':data['values']['DOTS_THEME_DEFAULT']}})
        for controls in ({'DOTS_COLOR':'never'}, {'DOTS_COLOR':'auto','NO_COLOR':'1'}, {'DOTS_COLOR':'auto','TERM':'dumb'}):
            plain = self.env_command('env',env={**forced,**controls})
            self.assertNotIn('\x1b', plain)
            self.assertIn('Dots environment', plain)
        self.assertNotIn('\x1b', self.env_command('--color=none','env',env=forced))
        self.assertIn('\x1b', self.env_command('--color=always','env',env={**forced,'NO_COLOR':'1'}))
        invalid = subprocess.run([str(REPO/'bin/dots'),'env','UNKNOWN'],env=forced,text=True,capture_output=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(invalid.stdout, '')
        self.assertIn('unknown name', invalid.stderr)
        self.assertFalse((self.home/'state').exists())
        self.assertFalse((self.home/'cache').exists())

    def test_home_abbreviation_is_display_only_in_both_controllers(self):
        cases = [
            (str(self.home), str(self.home / 'state ü'), '~/state ü/dots'),
            (str(self.home), str(self.home) + '-other', str(self.home) + '-other/dots'),
            (str(self.root / 'state/dots'), str(self.root / 'state'), '~'),
        ]
        for native in (False, True):
            for home, state, expected in cases:
                with self.subTest(native=native, home=home, state=state):
                    Path(home).mkdir(parents=True, exist_ok=True)
                    env = {**self.env, 'HOME':home, 'XDG_STATE_HOME':state,
                           'DOTS_COLOR':'never', 'DOTS_ICONS':'never', 'COLUMNS':'300'}
                    raw = self.env_command('env', '--json', env=env, native=native)
                    output = self.env_terminal(300, env, native=native)
                    row = next(line for line in output.splitlines() if 'DOTS_STATE_DIR' in line)
                    self.assertEqual(row.split('DOTS_STATE_DIR', 1)[1].removesuffix('[resolved]').strip(), expected)
                    self.assertEqual(self.env_command('env', '--json', env=env, native=native), raw)
                    values = json.loads(raw)['values']
                    self.assertEqual(values['DOTS_STATE_DIR']['value'], state + '/dots')
                    self.assertEqual(self.env_command('env', 'DOTS_STATE_DIR', env=env, native=native), state + '/dots\n')
                    listing = ''.join(f"{key}={item['value']} [{item['source']}]\n" for key, item in values.items())
                    self.assertEqual(self.env_command('env', env=env, native=native), listing)

    def test_environment_terminal_widths_and_sources(self):
        import unicodedata
        env = {**self.env, 'TERM':'xterm-256color', 'DOTS_COLOR':'auto', 'DOTS_THEME_DEFAULT':'nord',
               'XDG_STATE_HOME':str(self.home / 'state ü')}
        for columns in (40, 80, 120):
            for controls in ({}, {'NO_COLOR':'1'}):
                with self.subTest(columns=columns, controls=controls):
                    output = self.env_terminal(columns, {**env,**controls})
                    self.assertEqual('\x1b' in output, not controls)
                    plain = re.sub(r'\x1b\[[0-9;]*m', '', output)
                    for line in plain.splitlines():
                        self.assertLessEqual(sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in line), columns)
                    for source in ('default', 'config', 'environment', 'resolved', 'checkout'):
                        self.assertIn(source, plain)
                    self.assertIn('ü', plain)
                    self.assertIn('~/config/dots/config.env', plain)
                    self.assertIn('Dots environment', plain)
        published = Path(env['XDG_STATE_HOME'])/'dots/current/theme/id'
        published.parent.mkdir(parents=True)
        published.write_text('tokyonight-day\n')
        plain = self.env_terminal(80, {**env,'DOTS_COLOR':'never'})
        self.assertIn('tokyonight-day', plain)
        self.assertIn('[published]', plain)

    def test_environment_long_values_and_safe_display(self):
        state_root = str(self.home / ('界e\u0301' * 30))
        env = {**self.env, 'XDG_STATE_HOME':state_root, 'DOTS_ICONS':'always', 'COLUMNS':'40'}
        output = self.env_command('env',env=env)
        lines = output.partition('  DOTS_STATE_DIR\n')[2].partition('    Source: resolved')[0]
        self.assertEqual(''.join(line[4:] for line in lines.splitlines()).split(' ', 1)[1], '~/' + Path(state_root).name + '/dots')
        env['XDG_STATE_HOME'] = str(self.home) + '/bad\x1b[2J\n\x9bcontrol'
        output = self.env_command('env',env=env)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\x9b', output)
        self.assertIn('\\u001b', output)
        self.assertIn('\\u009b', output)
        raw = self.env_command('env','DOTS_STATE_DIR',env=env)
        self.assertEqual(raw, env['XDG_STATE_HOME'] + '/dots\n')
        self.assertEqual(json.loads(self.env_command('env','--json',env=env))['values']['DOTS_STATE_DIR']['value'], raw[:-1])

    def test_native_config_and_integration_only(self):
        scripts = {
            'bash': 'source "$DOTS/lib/dots/shell/init.bash"; printf "%s|%s|%s" "${dot[root]}" "${dots_options[DOTS_INIT_THEME]}" "${dots_option_sources[DOTS_INIT_THEME]}"; ! alias q 2>/dev/null',
            'zsh': 'source "$DOTS/lib/dots/shell/init.zsh"; printf "%s|%s|%s" "$dot[root]" "$dots_options[DOTS_INIT_THEME]" "$dots_option_sources[DOTS_INIT_THEME]"; (( ! ${+aliases[q]} ))',
            'fish': 'source "$DOTS/lib/dots/shell/init.fish"; printf "%s|%s|%s" "$dot_root" "$_dots_option_DOTS_INIT_THEME" "$_dots_source_DOTS_INIT_THEME"; not functions -q q',
            'nu': f'source "{REPO}/lib/dots/shell/init.nu"; print -n $"($env.dot.root)|($env.dots_options.DOTS_INIT_THEME)|($env.dots_option_sources.DOTS_INIT_THEME)"',
        }
        for shell, script in scripts.items():
            with self.subTest(shell=shell):
                result = self.run_shell(shell, script, True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f'{REPO}|0|config', result.stderr)
        self.assertFalse((self.home / 'state').exists())

    def test_config_reload_and_atomic_failure(self):
        for shell in ('bash', 'zsh'):
            self.config.write_text('DOTS_INIT_THEME=0\nDOTS_THEME_DEFAULT=nord\n')
            result = self.run_shell(shell, '''
source "$DOTS/lib/dots/shell/init.bash" || exit
printf 'DOTS_INIT_THEME=0\nDOTS_THEME_DEFAULT=gruvbox\n' > "$_DOTS_CONFIG_PATH"
source "$DOTS/lib/dots/shell/init.bash" || exit
[[ ${dots_options[DOTS_THEME_DEFAULT]} == gruvbox ]] || exit 3
printf 'DOTS_INIT_THEME=0\nDOTS_THEME_DEFAULT=$(touch forbidden)\n' > "$_DOTS_CONFIG_PATH"
source "$DOTS/lib/dots/shell/init.bash" && exit 4
[[ ${dots_options[DOTS_THEME_DEFAULT]} == gruvbox ]]
''')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((self.home / 'forbidden').exists())

    def test_diagnostic_sources(self):
        self.env['DOTS_THEME_DEFAULT'] = 'nord'
        result = subprocess.run([str(REPO / 'bin/dots'), 'env', '--json'], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['values']['DOTS_THEME_DEFAULT'], {'value': 'nord', 'source': 'environment'})
        self.assertEqual(data['values']['DOTS_INIT_THEME']['source'], 'config')
        self.assertNotIn('PATH', data['values'])

    def test_current_theme_default_and_read_only_completion(self):
        self.config.write_text('DOTS_THEME_DEFAULT=nord\n')
        for args, expected in [(('theme', 'current'), 'nord\n'),
                               (('env', 'DOTSCRIPTS'), str(REPO / 'scripts') + '\n')]:
            result = subprocess.run([str(REPO / 'bin/dots'), *args], env=self.env, cwd=self.home,
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)
        result = subprocess.run([str(REPO / 'bin/dots'), '__complete', 'bash', '2', '--', 'dots', 'env', 'DOTS_THEME'],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertIn('candidate\tDOTS_THEME_DEFAULT\t', result.stdout)
        self.assertFalse((self.home / 'state').exists())

    def test_native_palette_updates(self):
        self.config.write_text('DOTS_INIT_THEME=1\nDOTS_INIT_COMMANDS=0\n')
        state = self.home / 'state/dots/themes'
        generation = state / 'generations/g.fixture'
        generation.mkdir(parents=True)
        (state / 'current').write_text('g.fixture\n')
        (generation / 'shell.tsv').write_text('@theme\tid\tnord\n@theme\tfamily\tnord\n@theme\tflavor\t\n@palette\tblue\t#123456\n@role\thint\t#123456\nblue\thex\t#123456\n')
        (generation / 'ls_colors').write_text('di=38;2;1;2;3\n')
        second = state / 'generations/g.second'
        second.mkdir()
        (second / 'shell.tsv').write_text('@theme\tid\twhite\n@theme\tfamily\twhite\n@theme\tflavor\t\n@palette\tred\t#abcdef\n@role\thint\t#abcdef\nred\thex\t#abcdef\n')
        (second / 'ls_colors').write_text('di=38;2;4;5;6\n')
        for shell, script in {
            'fish': '''source "$DOTS/lib/dots/shell/init.fish"
printf "%s|%s" "$DOTS_THEME_ID" "$dots_color_blue_hex"
printf 'g.second\n' > "$_DOTS_STATE/themes/current"
false
_dots_fish_prompt
test $status -eq 1; or exit 3
set -q dots_color_blue_hex; and exit 4
test "$dots_color_red_hex" = '#abcdef'; or exit 5
test "$LS_COLORS" = 'di=38;2;4;5;6'; or exit 7
printf 'g.invalid\n' > "$_DOTS_STATE/themes/current"
_dots_fish_theme; and exit 6
test "$DOTS_THEME_ID" = white
''',
            'nu': f'''source "{REPO}/lib/dots/shell/init.nu"
print -n $"($env.DOTS_THEME_ID)|($env.dots_colors.blue.hex)"
"g.second\n" | save --force ($env.dot.state | path join 'themes/current')
do --env ($env.config.hooks.pre_prompt | last)
if 'blue' in ($env.dots_colors | columns) {{ error make {{msg: 'stale blue'}} }}
if $env.dots_colors.red.hex != '#abcdef' {{ error make {{msg: 'missing red'}} }}
if $env.LS_COLORS != 'di=38;2;4;5;6' {{ error make {{msg: 'stale file colors'}} }}
"g.invalid\n" | save --force ($env.dot.state | path join 'themes/current')
try {{ _dots-refresh-theme }}
if $env.DOTS_THEME_ID != white {{ error make {{msg: 'lost last good theme'}} }}
''',
        }.items():
            with self.subTest(shell=shell):
                (state / 'current').write_text('g.fixture\n')
                result = self.run_shell(shell, script, True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, 'nord|#123456', result.stderr)


if __name__ == '__main__':
    unittest.main()
