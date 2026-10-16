#!/usr/bin/env python3
"""Small native integration cases; never load the owner's shell configuration."""
import json
import os
from pathlib import Path
import shutil
import subprocess
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
