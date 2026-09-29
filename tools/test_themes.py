#!/usr/bin/env python3
"""Theme integration tests: all mutable roots and executed commands are test owned."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from public_fixture import copy_public_tree
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
ZSH = shutil.which('zsh')
NVIM = shutil.which('nvim')


class Themes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-themes-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo space ü -dash'
        self.repo.mkdir()
        for name in ('lib/dots', 'themes', 'default'):
            copy_public_tree(REPO / name, self.repo / name, repo=REPO, fixture=self.repo)
        (self.repo / 'bin').mkdir()
        for p in [REPO / 'bin/dots', *REPO.glob('bin/dots-theme*')]:
            shutil.copy2(p, self.repo / 'bin' / p.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.env = {'HOME': str(self.home), 'DOTS': str(self.repo), 'DOTS_COLOR': 'never',
                    'PATH': str(self.repo / 'bin') + ':' + str(Path(BASH).parent) + ':/usr/bin:/bin',
                    'TMPDIR': str(self.root), 'TMUX_TMPDIR': str(self.root), 'TERM': 'xterm-256color', 'ZDOTDIR': str(self.home)}
        for kind in ('CONFIG', 'CACHE', 'STATE', 'DATA'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / kind.lower())
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
        self.state = self.home / 'state/dots/themes'
        self.lib = self.repo / 'lib/dots/themes'

    def run_command(self, argv, code=0, env=None):
        p = subprocess.run(argv, env=env or self.env, cwd=self.home, text=True,
                           capture_output=True, timeout=40)
        if code is not None:
            self.assertEqual(p.returncode, code, (argv, p.stdout, p.stderr))
        return p

    def dots(self, *args, code=0, env=None):
        return self.run_command([BASH, str(self.repo / 'bin/dots'), *args], code, env)

    def shell(self, body, executable=BASH, code=0):
        flags = ['--noprofile', '--norc'] if executable == BASH else ['-df']
        return self.run_command([executable, *flags, '-c', body], code)

    def generation(self):
        return self.state / 'generations' / (self.state / 'current').read_text().strip()

    def engine(self, body, code=0):
        return self.shell('DT_LIB="$DOTS/lib/dots/themes"; source "$DT_LIB/core.bash"; '
                          'source "$DT_LIB/../ui.bash"; source "$DT_LIB/state.bash"; ' + body, code=code)

    def test_routes_values_and_plain_output(self):
        self.assertEqual(set(self.dots('theme', 'list', '--families').stdout.split()), {'catppuccin','tokyonight','rose-pine','kanagawa','gruvbox','pywal16'})
        self.assertEqual(set(self.dots('theme', 'list', '--flavors', 'catppuccin').stdout.split()),
                         {'mocha', 'frappe', 'latte', 'macchiato'})
        self.assertEqual(self.dots('theme', 'color', 'blue', 'rgb', '--theme', 'catppuccin-mocha', '--native').stdout,
                         '137 180 250\n')
        self.assertNotIn('\x1b', self.dots('theme', 'show', 'catppuccin-mocha', '--native').stdout)
        self.assertIn('Switch application themes', self.dots('help', 'theme', 'set').stdout)
        self.dots('commands', '--check')
        self.dots('theme', 'color', code=2)
        self.dots('theme', 'color', 'missing', '--theme', 'catppuccin-mocha', '--native', code=1)
        self.dots('theme', 'show', '../bad', '--native', code=1)
        self.assertFalse(self.state.exists())
        e = {**self.env, 'DOTS_THEME_SELECTION': 'catppuccin-invalid'}
        self.dots('theme', 'init', env=e, code=1)
        self.assertFalse((self.home / 'cache').exists())

    def test_unified_routes_and_full_id_contract(self):
        self.assertFalse(list((self.repo / 'bin').glob('dots-themes*')))
        self.assertFalse((self.lib / 'cli.bash').exists())
        for args in [('themes',), ('themes', 'list'), ('help', 'themes')]:
            result = self.dots(*args, code=1)
            self.assertIn('Unknown command', result.stderr)
        self.assertNotIn('dots themes', self.dots('help').stdout)
        self.assertNotIn('dots themes', self.dots('commands').stdout)
        for shell in ('bash', 'zsh', 'fish'):
            result = self.dots('__complete', shell, '1', '--', 'dots', 'them')
            self.assertIn('candidate\ttheme\t', result.stdout)
            self.assertNotIn('candidate\tthemes\t', result.stdout)
        for action in ('set', 'show'):
            self.dots('theme', action, 'catppuccin', code=1)
            self.dots('theme', action, 'catppuccin', 'mocha', code=2)
        self.dots('theme', 'color', 'blue', '--theme', 'catppuccin', code=1)
        self.dots('theme', 'color', '', '--theme', 'catppuccin-mocha', code=1)
        self.dots('theme', 'color', 'catppuccin', 'mocha', 'blue', code=2)
        for args in [('color', 'blue', '--theme'), ('show', '--native'),
                     ('color', 'blue', '--theme='), ('show', 'nord', '--bad')]:
            self.dots('theme', *args, code=2)
        self.assertFalse(self.state.exists())

    def test_palette_filters_and_empty_catalog_are_read_only(self):
        self.assertEqual(self.dots('theme', 'list', '--flavors=catppuccin').stdout,
                         self.dots('theme', 'list', '--flavors', 'catppuccin').stdout)
        self.assertEqual(self.dots('theme', 'list', '--flavors', 'pywal16').stdout, 'current\n')
        for family in ('missing', '../catppuccin', '-invalid', 'nord'):
            result = self.dots('theme', 'list', '--flavors', family, code=1)
            self.assertEqual(result.stdout, '')
        for args in [('--families', '--flavors', 'catppuccin'), ('--flavors',), ('catppuccin',)]:
            self.dots('theme', 'list', *args, code=2)
        empty = self.root / 'empty palettes ü'
        empty.mkdir()
        env = {**self.env, 'DOTHEMES': str(empty)}
        self.assertEqual(self.dots('theme', 'list', '--families', env=env).stdout, '')
        result = self.dots('theme', 'list', '--families', env={**env, 'DOTS_COLOR': 'always'})
        self.assertIn('No entries available', result.stdout)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.home / 'cache').exists())

    def test_native_queries_distinguish_semantic_values_and_preserve_bytes(self):
        palette = self.repo / 'themes/catppuccin-mocha/colors.toml'
        palette.write_text(palette.read_text().replace('blue = "#89b4fa"', 'blue = "#123456"'))
        self.assertEqual(self.dots('theme', 'color', 'blue', '--theme', 'catppuccin-mocha').stdout, '#123456\n')
        raw = self.dots('theme', 'color', 'blue', '--theme', 'catppuccin-mocha', '--native').stdout
        self.assertEqual(raw, '#89b4fa\n')
        self.assertIn('#89b4fa', self.dots('theme', 'show', '--native', 'catppuccin-mocha').stdout)
        self.dots('theme', 'color', 'mode', '--native', '--theme', 'catppuccin-mocha', code=1)
        for fmt in ('hex', 'rgb', 'ansi-8bit-value', 'esc'):
            args = ('theme', 'color', 'blue', fmt, '--theme=catppuccin-mocha', '--native')
            plain = self.dots(*args).stdout
            forced = self.dots(*args, env={**self.env, 'DOTS_COLOR': 'always', 'DOTS_ICONS': 'always'}).stdout
            self.assertEqual(forced, plain)
        for width in ('40', '80', '120'):
            env = {**self.env, 'DOTS_COLOR': 'always', 'COLUMNS': width}
            self.assertIn('\x1b[', self.dots('theme', 'show', 'catppuccin-mocha', '--native', env=env).stdout)
            self.assertIn('Palette families', self.dots('theme', 'list', '--families', env=env).stdout)
        for controls in ({'NO_COLOR': '1', 'DOTS_COLOR': 'auto'}, {'TERM': 'dumb', 'DOTS_COLOR': 'auto'}):
            result = self.dots('theme', 'show', 'catppuccin-mocha', '--native', env={**self.env, **controls})
            self.assertNotIn('\x1b', result.stdout)
        self.assertFalse(self.state.exists())

    def test_generic_native_queries_and_selected_color_completion(self):
        self.dots('theme', 'set', 'nord')
        self.assertEqual(self.dots('theme', 'current').stdout, 'nord\n')
        for key in ('background', 'foreground', 'accent'):
            self.assertEqual(self.dots('theme', 'color', key).stdout,
                             self.dots('theme', 'color', key, '--native').stdout)
        self.assertIn('background', self.dots('theme', 'show', 'nord', '--native').stdout)
        self.assertIn('nord', self.run_command([BASH, str(self.repo / 'themes/bin/current_theme')]).stdout)
        for shell in ('bash', 'zsh', 'fish'):
            result = self.dots('__complete', shell, '3', '--', 'dots', 'theme', 'color', 'back')
            self.assertIn('candidate\tbackground\t', result.stdout)

    def test_malformed_data_is_not_executed(self):
        p = self.repo / 'themes/catppuccin/flavors/mocha.toml'
        original = p.read_text()
        for line in ['blue = "#ffffff"', 'x = "$(touch SENTINEL)"', '[table]',
                     'x = 12', 'x = "#fff"', 'x = "#ffffff" trailing', 'x = "a\\nb"']:
            p.write_text(original + '\n' + line + '\n')
            result = self.dots('theme', 'show', 'catppuccin-mocha', '--native', code=1)
            self.assertIn('mocha.toml:', result.stderr)
            self.assertFalse((self.home / 'SENTINEL').exists())
        p.write_text(original.replace('"#89b4fa"', "'#89b4fa' # literal color"))
        self.dots('theme', 'show', 'catppuccin-mocha', '--native')
        p.write_text('invalid palette\n')
        result = self.shell('source "$DOTS/themes/bin/theme"; ! has_theme catppuccin')
        self.assertEqual((result.stdout, result.stderr), ('', ''))

    def test_roles_missing_colors_and_generic_palette(self):
        p = self.repo / 'themes/catppuccin/theme.toml'
        p.write_text(p.read_text().replace('"overlay0"', '"missing"'))
        self.dots('theme', 'show', 'catppuccin-mocha', '--native', code=1)
        theme = self.repo / 'themes/example'
        (theme / 'flavors').mkdir(parents=True)
        (theme / 'theme.toml').write_text('default_flavor = "dark"\n[roles]\n' + ''.join(
            f'{r} = "ink"\n' for r in 'background foreground muted accent selection error warning info hint'.split()))
        (theme / 'flavors/dark.toml').write_text('ink = "#112233"\n')
        variant = self.repo / 'themes/example-dark'
        variant.mkdir()
        (variant / 'theme.toml').write_text('family = "example"\nflavor = "dark"\n')
        (variant / 'colors.toml').write_text('background = "#112233"\nforeground = "#eeeeee"\n')
        self.assertIn('ink', self.dots('theme', 'show', 'example-dark', '--native').stdout)
        self.dots('theme', 'set', 'example-dark', code=1)
        e = {**self.env, 'DOTS_THEME_SELECTION': 'example-dark'}
        self.assertIn('dots_palette', self.dots('theme', 'init', env=e).stdout)

    def test_preflight_validates_all_compatibility_palettes(self):
        p = self.repo / 'themes/catppuccin/flavors/latte.toml'
        p.write_text('invalid syntax\n')
        self.dots('theme', 'set', 'catppuccin-mocha', code=1)
        self.assertFalse(self.state.exists())

    def test_selection_precedence_and_compatibility(self):
        (self.repo / 'themes/.theme').write_text('catppuccin-frappe\n')
        self.assertEqual(self.dots('theme', 'current').stdout, 'catppuccin-frappe\n')
        (self.home / '.theme').write_text('catppuccin-macchiato\n')
        self.assertEqual(self.dots('theme', 'current').stdout, 'catppuccin-macchiato\n')
        self.dots('theme', 'set', 'catppuccin-latte')
        self.assertEqual(self.dots('theme', 'current').stdout, 'catppuccin-latte\n')
        result = self.run_command([BASH, str(self.repo / 'themes/bin/current_theme'), 'blue', 'hex'])
        self.assertEqual(result.stdout, '#1e66f5\n')
        self.assertEqual((self.home / '.theme').read_text(), 'catppuccin-macchiato\n')

    def test_init_legacy_digest_and_three_shell_syntax(self):
        result = self.run_command([BASH, str(self.repo / 'themes/bin/catppuccin'), 'init'])
        init = self.root / 'init.sh'
        init.write_text(result.stdout)
        script = '''source "$HOME/../init.sh"
for flavor in mocha macchiato frappe latte; do
 for color in "${catppuccin_palette[@]}"; do
  declare -n entry="${flavor}_${color}"
  for format in name hex rgb r g b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc; do
   printf '%s\\0' "$flavor" "$color" "$format" "${entry[$format]}"
  done
 done
done
'''
        actual = self.shell(script).stdout.encode()
        expected = (REPO / 'tools/fixtures/theme-legacy.sha256').read_text().strip()
        self.assertEqual(hashlib.sha256(actual).hexdigest(), expected)
        self.shell('source "$HOME/../init.sh"; [[ ${blue[hex]} == "#89b4fa" && ${latte_blue[hex]} == "#1e66f5" ]]')
        if ZSH:
            self.shell('source "$HOME/../init.sh"; [[ ${blue[hex]} == "#89b4fa" ]]', ZSH)
        fish = shutil.which('fish')
        if fish:
            init.write_text(self.dots('theme', 'init', '--shell', 'fish').stdout)
            self.run_command([fish, '--no-config', '-c', 'source "$HOME/../init.sh"; test "$dots_color_blue" = "#89b4fa"'])

    def test_cache_invalidation_same_size_and_timestamp(self):
        first = self.dots('theme', 'init').stdout
        p = self.repo / 'themes/catppuccin/flavors/mocha.toml'
        st = p.stat()
        p.write_text(p.read_text().replace('#89b4fa', '#123456'))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        second = self.dots('theme', 'init').stdout
        self.assertNotEqual(first, second)
        self.assertIn('123456', second)

    def test_atomic_generation_and_idempotence(self):
        self.dots('theme', 'set', 'catppuccin-mocha')
        first = self.generation()
        before = {str(p): (p.stat().st_mtime_ns, p.read_bytes()) for p in self.state.rglob('*') if p.is_file()}
        self.dots('theme', 'set', 'catppuccin-mocha')
        after = {str(p): (p.stat().st_mtime_ns, p.read_bytes()) for p in self.state.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.dots('theme', 'set', 'catppuccin-latte')
        current = self.generation()
        self.assertEqual((current / 'previous').read_text().strip(), first.name)
        self.assertEqual(json.loads((current / 'palette.json').read_text())['flavor'], 'latte')
        self.assertEqual((current / 'status').read_text(), 'committed\n')
        self.assertEqual((first / 'selection').read_text(), 'catppuccin-mocha\n')

    def test_published_snapshot_survives_source_edits(self):
        self.dots('theme', 'set', 'catppuccin-mocha')
        before = {s: self.dots('theme', 'init', '--shell', s).stdout for s in ('bash','zsh','fish')}
        (self.repo / 'themes/catppuccin/flavors/mocha.toml').write_text('temporarily invalid\n')
        self.assertEqual(self.dots('theme', 'current').stdout, 'catppuccin-mocha\n')
        for shell, output in before.items():
            self.assertEqual(self.dots('theme', 'init', '--shell', shell).stdout, output)
        self.assertEqual(self.run_command([BASH, str(self.repo / 'themes/bin/current_theme'), 'init']).stdout, before['bash'])
        self.dots('theme', 'set', 'catppuccin-mocha', code=1)
        self.assertEqual(self.dots('theme', 'current').stdout, 'catppuccin-mocha\n')

    def test_failed_publication_rolls_back(self):
        self.dots('theme', 'set', 'catppuccin-mocha')
        previous = (self.state / 'current').read_text()
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then return 1; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin latte''', code=1)
        self.assertEqual((self.state / 'current').read_text(), previous)
        self.assertIn('rolled-back\n', [p.read_text() for p in self.state.glob('generations/*/status')])

    def test_first_selection_rollback_and_drift_refusal(self):
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then return 1; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin latte''', code=1)
        self.assertFalse((self.state / 'current').exists())
        self.dots('theme', 'set', 'catppuccin-mocha')
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then kill -KILL "$BASHPID"; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin latte''', code=137)
        (self.state / 'current').write_text('g.externallychanged\n')
        result = self.dots('theme', 'set', 'catppuccin-frappe', code=1)
        self.assertIn('selection changed during recovery', result.stderr)
        self.assertEqual((self.state / 'current').read_text(), 'g.externallychanged\n')

    def test_failures_at_durability_boundaries(self):
        self.dots('theme', 'set', 'catppuccin-mocha')
        # Inject one failed flush at every boundary reached by this publisher.
        for boundary in range(1, 16):
            self.dots('theme', 'set', 'catppuccin-mocha')
            previous = (self.state / 'current').read_text()
            body = f'''count=0
 dt_flush() {{ (( ++count )); if (( count == {boundary} )); then return 1; fi; command sync -f "$1"; }}
 dt_set catppuccin latte
'''
            self.engine(body, code=1)
            self.assertEqual((self.state / 'current').read_text(), previous, boundary)
            self.dots('theme', 'set', 'catppuccin-mocha')

    def test_sigkill_recovery_and_lock_release(self):
        self.dots('theme', 'set', 'catppuccin-mocha')
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then kill -KILL "$BASHPID"; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin latte''', code=137)
        self.dots('theme', 'set', 'catppuccin-frappe')
        self.assertEqual(self.dots('theme', 'current').stdout, 'catppuccin-frappe\n')
        self.assertIn('rolled-back\n', [p.read_text() for p in self.state.glob('generations/*/status')])

    def test_unsafe_state_and_concurrent_switch(self):
        self.state.mkdir(parents=True)
        (self.state / 'current').symlink_to(self.root / 'missing')
        self.dots('theme', 'set', 'catppuccin-mocha', code=1)
        (self.state / 'current').unlink()
        lock = subprocess.Popen(['flock', str(self.state / 'lock'), BASH, '-c',
                                 'touch "$HOME/ready"; sleep 4'], env=self.env)
        self.addCleanup(lambda: lock.wait(timeout=6))
        for _ in range(100):
            if (self.home / 'ready').exists():
                break
            time.sleep(.02)
        result = self.dots('theme', 'set', 'catppuccin-mocha', code=1)
        self.assertIn('another theme switch', result.stderr)

    def test_completion_data_all_shells(self):
        for shell in ('bash', 'zsh', 'fish'):
            def complete(*words):
                return self.dots('__complete', shell, str(len(words)-1), '--', *words).stdout
            self.assertIn('candidate\tcatppuccin-mocha\t', complete('dots', 'theme', 'set', ''))
            self.assertIn('candidate\tcatppuccin\t', complete('dots', 'theme', 'list', '--flavors', ''))
            self.assertIn('candidate\tblue\t', complete('dots', 'theme', 'color', '--theme', 'catppuccin-mocha', '--native', ''))
            self.assertIn('candidate\trgb\t', complete('dots', 'theme', 'color', 'blue', ''))
            self.assertIn('candidate\tblue\t', complete('dots', 'theme', 'color', ''))
            self.assertNotIn('candidate\tmode\t', complete('dots', 'theme', 'color', '--native', ''))
            self.assertIn('candidate\tmode\t', complete('dots', 'theme', 'color', ''))

    def test_sourceable_bash_compatibility(self):
        self.shell('''declare -A themes; themes[root]=$DOTS/themes
source "$DOTS/themes/bin/theme"
set_theme catppuccin-latte
[[ $FLAVOR == latte && ${blue[hex]} == "#1e66f5" ]] || exit 1
set_theme catppuccin
[[ $FLAVOR == mocha ]] || exit 2
has_theme catppuccin || exit 3
''')

    @unittest.skipUnless(ZSH, 'Zsh unavailable')
    def test_zsh_refresh_status_and_hooks(self):
        self.dots('theme', 'set', 'catppuccin-mocha')
        self.shell('''typeset -A themes; themes[root]=$DOTS/themes
source "$DOTS/themes/bin/theme"
_dots_vivid_colors() { REPLY=colors:$1; }
FZF_DEFAULT_OPTS='--height=40%'
set_theme || exit 1
[[ ${blue[hex]} == '#89b4fa' ]] || exit 2
"$DOTS/bin/dots-theme-set" catppuccin-latte >/dev/null || exit 3
false
_dots_theme_precmd
[[ $? == 1 && $FLAVOR == latte && ${blue[hex]} == '#1e66f5' ]] || exit 4
before=$FZF_DEFAULT_OPTS
set_theme
[[ $FZF_DEFAULT_OPTS == $before ]] || exit 5
source "$DOTS/themes/bin/theme"
[[ ${(M)#precmd_functions:#_dots_theme_precmd} == 1 ]] || exit 6
''', ZSH)

    @unittest.skipUnless(NVIM, 'Neovim unavailable')
    def test_neovim_real_palette_and_focus_reload(self):
        from nvim_theme_fixture import install, run
        install(self)
        self.dots('theme', 'set', 'catppuccin-mocha')
        run(self, r'''vim.g.terminal_color_0 = "#010203"
bridge.startup()
assert(loads == 1 and vim.g.colors_name == "anodize")
assert(hl("Normal").bg == nil and hl("NormalFloat").bg == 0x1e1e2e)
assert(hl("Comment").fg == 0x5b6078 and hl("LineNr").fg == 0x494d64)
assert(hl("CursorLine").bg == 0x242438 and not hl("CursorLineNr").bold)
assert(hl("NormalNC").fg ~= hl("Normal").fg and hl("NormalNC").bg == nil)
assert(vim.g.terminal_color_0 == "#010203")
assert(not package.loaded.catppuccin and not package.loaded["util.dots_theme_adapters"])
local opts=bridge.options({})
assert(opts.flavour == "mocha" and opts.color_overrides.mocha.base == "#1e1e2e")
for _, flavor in ipairs({"latte", "frappe", "macchiato", "mocha"}) do
 publish("catppuccin", flavor)
 vim.api.nvim_exec_autocmds("FocusGained", {})
 assert(current("catppuccin-"..flavor))
 local p=require("anodize").get_palette()
 assert(hl("Normal").fg == tonumber(p.roles.foreground:sub(2),16))
 assert(hl("Visual").bg == tonumber(p.roles.selection:sub(2),16))
 assert(hl("NormalFloat").bg == tonumber(p.roles.background:sub(2),16))
 if flavor ~= "mocha" then assert(hl("CursorLine").bg == tonumber(p.colors.lighter_background:sub(2),16)) end
 assert(vim.g.terminal_color_0 == "#010203")
end
local previous = hl("Normal").fg
local count=0;vim.notify=function() count=count+1 end
vim.uv.fs_unlink(vim.env.XDG_STATE_HOME.."/dots/current/theme")
vim.uv.fs_symlink("invalid",vim.env.XDG_STATE_HOME.."/dots/current/theme")
bridge.reload();bridge.reload();vim.wait(150)
assert(count == 1 and hl("Normal").fg == previous)
assert(vim.fn.exists(":DotsThemeReload") == 2)
vim.cmd.colorscheme("habamax")
vim.api.nvim_exec_autocmds("FocusGained", {})
vim.cmd.DotsThemeReload();vim.wait(150)
assert(vim.g.colors_name == "habamax")
assert(bridge.reload(true) == false)
assert(not require("anodize").get_palette())
''')

    def wal_export(self, suffix=''):
        p = self.home / 'cache/wal/colors.sh'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("background='#102030'\nforeground='#eeeeee'\ncursor='#abcdef'\n" + ''.join(
            f"color{i}='#{i+32:02x}{i+48:02x}{i+64:02x}'\n" for i in range(16)) + suffix)
        return p

    def test_fixed_families_roles_selection_and_native_keys(self):
        families = {'tokyonight': ['day','moon','night','storm'], 'rose-pine': ['dawn','main','moon'],
                    'kanagawa': ['dragon','lotus','wave'], 'gruvbox': ['dark','light']}
        for theme, flavors in families.items():
            self.assertEqual(self.dots('theme', 'list', '--flavors', theme).stdout.split(), flavors)
            for flavor in flavors:
                self.dots('theme', 'set', f'{theme}-{flavor}')
                self.assertEqual(self.dots('theme', 'current').stdout, f'{theme}-{flavor}\n')
                data = json.loads((self.generation() / 'palette.json').read_text())
                self.assertEqual(len(data['roles']),9)
                self.assertRegex(data['roles']['background'], r'^#[0-9a-fA-F]{6}$')
        self.assertEqual(self.dots('theme', 'color', 'sumiInk3', '--theme', 'kanagawa-wave', '--native').stdout, '#1F1F28\n')
        self.assertEqual(self.dots('theme', 'color', '_nc', '--theme', 'rose-pine-main', '--native').stdout, '#16141f\n')
        self.dots('theme', 'set', 'rose-pine-main')
        p = self.run_command([BASH,str(self.repo/'themes/bin/current_theme'),'base','hex'])
        self.assertEqual(p.stdout, '#191724\n')
        self.dots('theme', 'set', 'kanagawa-wave')
        p = self.run_command([BASH,str(self.repo/'themes/bin/current_theme'),'lotus','lotusWhite3','hex'])
        self.assertEqual(p.stdout, '#f2ecbc\n')
        self.dots('theme', 'set', 'rose-pine-main')
        self.dots('theme', 'set', 'rose-pine-invalid', code=1)
        self.assertEqual(self.dots('theme', 'current').stdout,'rose-pine-main\n')

    def test_pywal_import_snapshot_refresh_and_missing_input(self):
        self.assertEqual(self.dots('theme', 'list', '--flavors', 'pywal16').stdout,'current\n')
        self.dots('theme', 'set', 'pywal16-current', code=1)
        self.assertFalse(self.state.exists())
        p = self.wal_export('touch "$HOME/SHOULD_NOT_EXIST"\n')
        self.dots('theme', 'set', 'pywal16-current')
        generation = self.generation()
        self.assertFalse((self.home/'SHOULD_NOT_EXIST').exists())
        self.assertEqual(self.dots('theme', 'color', 'background', '--theme', 'pywal16-current', '--native').stdout,'#102030\n')
        before = self.dots('theme', 'init').stdout
        p.write_text(p.read_text().replace('#102030','#fafafa'))
        self.assertEqual(self.dots('theme', 'init').stdout,before)
        self.dots('theme', 'set', 'pywal16-current')
        self.assertNotEqual(self.generation(),generation)
        self.assertNotEqual(self.dots('theme', 'init').stdout,before)
        p.unlink()
        self.assertEqual(self.dots('theme', 'current').stdout,'pywal16-current\n')
        self.dots('theme', 'init')

    def test_pywal_rejects_invalid_exports_without_side_effects(self):
        for suffix in ["background='#ffffff'\n", "color1=$(touch BAD)\n", "cursor='red'\n", '\0trailing', 'x'*65537]:
            self.wal_export(suffix)
            self.dots('theme', 'set', 'pywal16-current', code=1)
            self.assertFalse(self.state.exists())
            self.assertFalse((self.home/'BAD').exists())
        p = self.wal_export()
        p.write_text(p.read_text().replace("cursor='#abcdef'", 'cursor="#abcdef\''))
        self.dots('theme', 'set', 'pywal16-current', code=1)
        self.assertFalse(self.state.exists())
        p = self.wal_export()
        p.write_text(p.read_text().replace("color15='#2f3f4f'\n",''))
        self.dots('theme', 'set', 'pywal16-current', code=1)
        self.assertFalse(self.state.exists())

    def test_hyphenated_completion_and_zsh_roundtrip(self):
        for shell in ('bash','zsh','fish'):
            self.assertIn('rose-pine-dawn',self.dots('__complete',shell,'3','--','dots','theme','set','rose-').stdout)
            self.assertIn('rose-pine',self.dots('__complete',shell,'4','--','dots','theme','list','--flavors','rose-').stdout)
            self.assertIn('sumiInk3',self.dots('__complete',shell,'5','--','dots','theme','color','--theme=kanagawa-wave','--native','sumi').stdout)
        if ZSH:
            self.shell(r'''typeset -A themes; themes[root]=$DOTS/themes
source "$DOTS/themes/bin/theme"
LS_COLORS='*.custom=01;35'
set_theme catppuccin-mocha
change_theme rose-pine-dawn >/dev/null
[[ $THEME == rose-pine && $FLAVOR == dawn && ${dots_palette[base]} == '#faf4ed' ]] || exit 1
[[ $LS_COLORS == *'*.custom=01;35'* && $LS_COLORS == *'38;2;'* ]] || exit 2
before=$FZF_DEFAULT_OPTS
set_theme
[[ $FZF_DEFAULT_OPTS == $before ]] || exit 3
has_theme rose-pine || exit 4
change_theme catppuccin-mocha >/dev/null
[[ $THEME == catppuccin && ${blue[hex]} == '#89b4fa' ]] || exit 5
''',ZSH)

    @unittest.skipUnless(NVIM, 'Neovim unavailable')
    def test_neovim_all_native_families(self):
        from nvim_theme_fixture import install, run
        install(self)
        self.wal_export()
        self.dots('theme', 'set', 'tokyonight-night')
        run(self, r'''bridge.startup()
assert(vim.g.colors_name == "anodize")
local choices={
 {"tokyonight","day","light"},{"tokyonight","moon","dark"},{"tokyonight","storm","dark"},
 {"rose-pine","main","dark"},{"rose-pine","dawn","light"},{"rose-pine","moon","dark"},
 {"kanagawa","wave","dark"},{"kanagawa","lotus","light"},{"kanagawa","dragon","dark"},
 {"gruvbox","dark","dark"},{"gruvbox","light","light"},{"pywal16","current","dark"},
 {"catppuccin","mocha","dark"}
}
for _, choice in ipairs(choices) do
 publish(choice[1],choice[2])
 vim.cmd.DotsThemeReload()
 assert(current(choice[1].."-"..choice[2]))
 assert(vim.o.background==choice[3])
 local data=snapshot()
 assert(hl("Normal").fg==tonumber(data.roles.foreground:sub(2),16))
 assert(vim.deep_equal(bridge.gradient_colors(),{data.roles.info,data.roles.hint,data.roles.warning,data.roles.error,data.roles.accent}))
 if choice[1]=="pywal16" then
  local raw=bridge.pywal_colors()
  assert(raw.color0==data.palette.color0 and raw.transparent=="NONE")
 end
end
assert(not pcall(bridge.pywal_colors))
local file=vim.env.DOTS.."/themes/tokyonight-night/colors.toml"
local lines=vim.fn.readfile(file)
for i,line in ipairs(lines) do if line:match('^foreground =') then lines[i]='foreground = "#112233"' end end
vim.fn.writefile(lines,file)
publish("tokyonight","night")
assert(bridge.reload(true))
assert(hl("Normal").fg==0x112233)
assert(not package.loaded.tokyonight and not package.loaded.catppuccin)
''')


if __name__ == '__main__':
    unittest.main()
