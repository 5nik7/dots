#!/usr/bin/env python3
"""Theme integration tests: all mutable roots and executed commands are test owned."""
import hashlib
import json
import os
from pathlib import Path
import shutil
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
        for name in ('lib/dots', 'themes'):
            shutil.copytree(REPO / name, self.repo / name, symlinks=True)
        (self.repo / 'bin').mkdir()
        for p in [REPO / 'bin/dots', *REPO.glob('bin/dots-themes*')]:
            shutil.copy2(p, self.repo / 'bin' / p.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.env = {'HOME': str(self.home), 'DOTS': str(self.repo), 'DOTS_COLOR': 'never',
                    'PATH': str(self.repo / 'bin') + ':' + str(Path(BASH).parent) + ':/usr/bin:/bin',
                    'TMPDIR': str(self.root), 'TERM': 'xterm-256color', 'ZDOTDIR': str(self.home)}
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
        self.assertEqual(set(self.dots('themes', 'list').stdout.split()), {'catppuccin','tokyonight','rose-pine','kanagawa','gruvbox','pywal16'})
        self.assertEqual(set(self.dots('themes', 'list', 'catppuccin').stdout.split()),
                         {'mocha', 'frappe', 'latte', 'macchiato'})
        self.assertEqual(self.dots('themes', 'color', 'catppuccin', 'mocha', 'blue', 'rgb').stdout,
                         '137 180 250\n')
        self.assertNotIn('\x1b', self.dots('themes', 'show', 'catppuccin').stdout)
        self.assertIn('Switch Zsh', self.dots('help', 'themes', 'set').stdout)
        self.dots('commands', '--check')
        self.dots('themes', 'color', code=2)
        self.dots('themes', 'color', 'catppuccin', 'mocha', 'missing', code=1)
        self.dots('themes', 'show', '../bad', code=1)
        self.assertFalse(self.state.exists())
        e = {**self.env, 'DOTS_THEME_SELECTION': 'catppuccin-invalid'}
        self.dots('themes', 'init', env=e, code=1)
        self.assertFalse((self.home / 'cache').exists())

    def test_malformed_data_is_not_executed(self):
        p = self.repo / 'themes/catppuccin/flavors/mocha.toml'
        original = p.read_text()
        for line in ['blue = "#ffffff"', 'x = "$(touch SENTINEL)"', '[table]',
                     'x = 12', 'x = "#fff"', 'x = "#ffffff" trailing', 'x = "a\\nb"']:
            p.write_text(original + '\n' + line + '\n')
            result = self.dots('themes', 'show', 'catppuccin', code=1)
            self.assertIn('mocha.toml:', result.stderr)
            self.assertFalse((self.home / 'SENTINEL').exists())
        p.write_text(original.replace('"#89b4fa"', "'#89b4fa' # literal color"))
        self.dots('themes', 'show', 'catppuccin')

    def test_roles_missing_colors_and_generic_palette(self):
        p = self.repo / 'themes/catppuccin/theme.toml'
        p.write_text(p.read_text().replace('"overlay0"', '"missing"'))
        self.dots('themes', 'show', 'catppuccin', code=1)
        theme = self.repo / 'themes/example'
        (theme / 'flavors').mkdir(parents=True)
        (theme / 'theme.toml').write_text('default_flavor = "dark"\n[roles]\n' + ''.join(
            f'{r} = "ink"\n' for r in 'background foreground muted accent selection error warning info hint'.split()))
        (theme / 'flavors/dark.toml').write_text('ink = "#112233"\n')
        self.assertIn('ink', self.dots('themes', 'show', 'example').stdout)
        self.dots('themes', 'set', 'example', code=1)
        e = {**self.env, 'DOTS_THEME_SELECTION': 'example-dark'}
        self.assertIn('dots_palette', self.dots('themes', 'init', env=e).stdout)

    def test_preflight_validates_all_compatibility_palettes(self):
        p = self.repo / 'themes/catppuccin/flavors/latte.toml'
        p.write_text('invalid syntax\n')
        self.dots('themes', 'set', 'catppuccin', 'mocha', code=1)
        self.assertFalse(self.state.exists())

    def test_selection_precedence_and_compatibility(self):
        (self.repo / 'themes/.theme').write_text('catppuccin-frappe\n')
        self.assertEqual(self.dots('themes', 'current').stdout, 'catppuccin-frappe\n')
        (self.home / '.theme').write_text('catppuccin-macchiato\n')
        self.assertEqual(self.dots('themes', 'current').stdout, 'catppuccin-macchiato\n')
        self.dots('themes', 'set', 'catppuccin', 'latte')
        self.assertEqual(self.dots('themes', 'current').stdout, 'catppuccin-latte\n')
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
            init.write_text(self.dots('themes', 'init', '--shell', 'fish').stdout)
            self.run_command([fish, '--no-config', '-c', 'source "$HOME/../init.sh"; test "$dots_color_blue" = "#89b4fa"'])

    def test_cache_invalidation_same_size_and_timestamp(self):
        first = self.dots('themes', 'init').stdout
        p = self.repo / 'themes/catppuccin/flavors/mocha.toml'
        st = p.stat()
        p.write_text(p.read_text().replace('#89b4fa', '#123456'))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        second = self.dots('themes', 'init').stdout
        self.assertNotEqual(first, second)
        self.assertIn('123456', second)

    def test_atomic_generation_and_idempotence(self):
        self.dots('themes', 'set', 'catppuccin')
        first = self.generation()
        before = {str(p): (p.stat().st_mtime_ns, p.read_bytes()) for p in self.state.rglob('*') if p.is_file()}
        self.dots('themes', 'set', 'catppuccin')
        after = {str(p): (p.stat().st_mtime_ns, p.read_bytes()) for p in self.state.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.dots('themes', 'set', 'catppuccin', 'latte')
        current = self.generation()
        self.assertEqual((current / 'previous').read_text().strip(), first.name)
        self.assertEqual(json.loads((current / 'palette.json').read_text())['flavor'], 'latte')
        self.assertEqual((current / 'status').read_text(), 'committed\n')
        self.assertEqual((first / 'selection').read_text(), 'catppuccin-mocha\n')

    def test_published_snapshot_survives_source_edits(self):
        self.dots('themes', 'set', 'catppuccin')
        before = {s: self.dots('themes', 'init', '--shell', s).stdout for s in ('bash','zsh','fish')}
        (self.repo / 'themes/catppuccin/flavors/mocha.toml').write_text('temporarily invalid\n')
        self.assertEqual(self.dots('themes', 'current').stdout, 'catppuccin-mocha\n')
        for shell, output in before.items():
            self.assertEqual(self.dots('themes', 'init', '--shell', shell).stdout, output)
        self.assertEqual(self.run_command([BASH, str(self.repo / 'themes/bin/current_theme'), 'init']).stdout, before['bash'])
        self.dots('themes', 'set', 'catppuccin', code=1)
        self.assertEqual(self.dots('themes', 'current').stdout, 'catppuccin-mocha\n')

    def test_failed_publication_rolls_back(self):
        self.dots('themes', 'set', 'catppuccin')
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
        self.dots('themes', 'set', 'catppuccin')
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then kill -KILL "$BASHPID"; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin latte''', code=137)
        (self.state / 'current').write_text('g.externallychanged\n')
        result = self.dots('themes', 'set', 'catppuccin', 'frappe', code=1)
        self.assertIn('selection changed during recovery', result.stderr)
        self.assertEqual((self.state / 'current').read_text(), 'g.externallychanged\n')

    def test_failures_at_durability_boundaries(self):
        self.dots('themes', 'set', 'catppuccin')
        # Inject one failed flush at every boundary reached by this publisher.
        for boundary in range(1, 16):
            self.dots('themes', 'set', 'catppuccin', 'mocha')
            previous = (self.state / 'current').read_text()
            body = f'''count=0
 dt_flush() {{ (( ++count )); if (( count == {boundary} )); then return 1; fi; command sync -f "$1"; }}
 dt_set catppuccin latte
'''
            self.engine(body, code=1)
            self.assertEqual((self.state / 'current').read_text(), previous, boundary)
            self.dots('themes', 'set', 'catppuccin', 'mocha')

    def test_sigkill_recovery_and_lock_release(self):
        self.dots('themes', 'set', 'catppuccin')
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then kill -KILL "$BASHPID"; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin latte''', code=137)
        self.dots('themes', 'set', 'catppuccin', 'frappe')
        self.assertEqual(self.dots('themes', 'current').stdout, 'catppuccin-frappe\n')
        self.assertIn('rolled-back\n', [p.read_text() for p in self.state.glob('generations/*/status')])

    def test_unsafe_state_and_concurrent_switch(self):
        self.state.mkdir(parents=True)
        (self.state / 'current').symlink_to(self.root / 'missing')
        self.dots('themes', 'set', 'catppuccin', code=1)
        (self.state / 'current').unlink()
        lock = subprocess.Popen(['flock', str(self.state / 'lock'), BASH, '-c',
                                 'touch "$HOME/ready"; sleep 4'], env=self.env)
        self.addCleanup(lambda: lock.wait(timeout=6))
        for _ in range(100):
            if (self.home / 'ready').exists():
                break
            time.sleep(.02)
        result = self.dots('themes', 'set', 'catppuccin', code=1)
        self.assertIn('another theme switch', result.stderr)

    def test_completion_data_all_shells(self):
        for shell in ('bash', 'zsh', 'fish'):
            def complete(*words):
                return self.dots('__complete', shell, str(len(words)-1), '--', *words).stdout
            self.assertIn('candidate\tcatppuccin\t', complete('dots', 'themes', 'set', ''))
            self.assertIn('candidate\tlatte\t', complete('dots', 'themes', 'set', 'catppuccin', ''))
            self.assertIn('candidate\tblue\t', complete('dots', 'themes', 'color', 'catppuccin', 'mocha', ''))
            self.assertIn('candidate\trgb\t', complete('dots', 'themes', 'color', 'catppuccin', 'mocha', 'blue', ''))

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
        self.dots('themes', 'set', 'catppuccin')
        self.shell('''typeset -A themes; themes[root]=$DOTS/themes
source "$DOTS/themes/bin/theme"
_dots_vivid_colors() { REPLY=colors:$1; }
FZF_DEFAULT_OPTS='--height=40%'
set_theme || exit 1
[[ ${blue[hex]} == '#89b4fa' ]] || exit 2
"$DOTS/bin/dots-themes-set" catppuccin latte >/dev/null || exit 3
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
        plugin = Path(os.environ['HOME']) / '.local/share/nvim/lazy/catppuccin'
        if not (plugin / 'lua/catppuccin/init.lua').is_file():
            self.skipTest('installed public Catppuccin source unavailable')
        # Copy public source only; never start the live LazyVim configuration.
        shutil.copytree(plugin, self.root / 'catppuccin', ignore=shutil.ignore_patterns('.git'))
        lua = self.root / 'lua'
        (lua / 'util').mkdir(parents=True)
        (lua / 'config/highlights').mkdir(parents=True)
        shutil.copy2(REPO / 'configs/nvim/lua/util/dots_theme.lua', lua / 'util/dots_theme.lua')
        shutil.copy2(REPO / 'configs/nvim/lua/util/dots_theme_adapters.lua', lua / 'util/dots_theme_adapters.lua')
        shutil.copy2(REPO / 'configs/nvim/lua/config/highlights/catppuccin.lua', lua / 'config/highlights/catppuccin.lua')
        self.dots('themes', 'set', 'catppuccin')
        script = self.root / 'check.lua'
        script.write_text(r'''local root = vim.env.HOME .. "/.."
vim.opt.rtp:prepend(root)
vim.opt.rtp:prepend(root .. "/catppuccin")
local cat = require("catppuccin")
local bridge = require("util.dots_theme")
local opts = bridge.options({flavour="mocha", transparent_background=true,
  default_integrations=false, auto_integrations=false, integrations={},
  custom_highlights=require("config.highlights.catppuccin")})
cat.setup(opts)
vim.cmd.colorscheme("catppuccin-nvim")
local function hl(name) return vim.api.nvim_get_hl(0, {name=name, link=false}) end
assert(hl("Visual").bg == 0x2f4858)
assert(hl("Comment").fg == 0x5b6078)
assert(hl("CursorLine").bg == 0x242438)
local setup = cat.setup
local redundant = 0
cat.setup = function(...) redundant = redundant + 1; return setup(...) end
bridge.startup()
assert(redundant == 0, "startup must reuse the already configured Catppuccin snapshot")
cat.setup = setup
for _, flavor in ipairs({"latte", "frappe", "macchiato", "mocha"}) do
  vim.fn.system({"bash", vim.env.DOTS .. "/bin/dots-themes-set", "catppuccin", flavor})
  assert(vim.v.shell_error == 0)
  vim.api.nvim_exec_autocmds("FocusGained", {})
  assert(cat.options.flavour == flavor)
  local colors = require("catppuccin.palettes").get_palette(flavor)
  if flavor ~= "mocha" then
    assert(hl("Visual").bg == tonumber(colors.surface1:sub(2),16))
    assert(hl("CursorLine").bg == tonumber(colors.surface0:sub(2),16))
  end
  assert(cat.options.transparent_background)
end
local count = 0
vim.notify = function() count = count + 1 end
vim.fn.writefile({"invalid"}, vim.env.XDG_STATE_HOME .. "/dots/themes/current")
bridge.reload(); bridge.reload()
vim.wait(30)
assert(count == 1, "diagnostics must be bounded")
assert(cat.options.flavour == "mocha")
assert(vim.fn.exists(":DotsThemeReload") == 2)
print("NVIM_THEME_OK")
''')
        result = self.run_command([NVIM, '--headless', '-u', 'NONE', '-i', 'NONE',
                                   '-l', str(script)])
        self.assertIn('NVIM_THEME_OK', result.stdout + result.stderr)

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
            self.assertEqual(self.dots('themes','list',theme).stdout.split(), flavors)
            for flavor in flavors:
                self.dots('themes','set',theme,flavor)
                self.assertEqual(self.dots('themes','current').stdout, f'{theme}-{flavor}\n')
                data = json.loads((self.generation() / 'palette.json').read_text())
                self.assertEqual(len(data['roles']),9)
                self.assertIn(data['roles']['background'], data['palette'].values())
        self.assertEqual(self.dots('themes','color','kanagawa','wave','sumiInk3').stdout, '#1F1F28\n')
        self.assertEqual(self.dots('themes','color','rose-pine','main','_nc').stdout, '#16141f\n')
        self.dots('themes','set','rose-pine')
        p = self.run_command([BASH,str(self.repo/'themes/bin/current_theme'),'base','hex'])
        self.assertEqual(p.stdout, '#191724\n')
        self.dots('themes','set','kanagawa','wave')
        p = self.run_command([BASH,str(self.repo/'themes/bin/current_theme'),'lotus','lotusWhite3','hex'])
        self.assertEqual(p.stdout, '#f2ecbc\n')
        self.dots('themes','set','rose-pine')
        self.dots('themes','set','rose-pine','invalid',code=1)
        self.assertEqual(self.dots('themes','current').stdout,'rose-pine-main\n')

    def test_pywal_import_snapshot_refresh_and_missing_input(self):
        self.assertEqual(self.dots('themes','list','pywal16').stdout,'current\n')
        self.dots('themes','set','pywal16',code=1)
        self.assertFalse(self.state.exists())
        p = self.wal_export('touch "$HOME/SHOULD_NOT_EXIST"\n')
        self.dots('themes','set','pywal16')
        generation = self.generation()
        self.assertFalse((self.home/'SHOULD_NOT_EXIST').exists())
        self.assertEqual(self.dots('themes','color','pywal16','current','background').stdout,'#102030\n')
        before = self.dots('themes','init').stdout
        p.write_text(p.read_text().replace('#102030','#fafafa'))
        self.assertEqual(self.dots('themes','init').stdout,before)
        self.dots('themes','set','pywal16')
        self.assertNotEqual(self.generation(),generation)
        self.assertNotEqual(self.dots('themes','init').stdout,before)
        p.unlink()
        self.assertEqual(self.dots('themes','current').stdout,'pywal16-current\n')
        self.dots('themes','init')

    def test_pywal_rejects_invalid_exports_without_side_effects(self):
        for suffix in ["background='#ffffff'\n", "color1=$(touch BAD)\n", "cursor='red'\n", '\0trailing', 'x'*65537]:
            self.wal_export(suffix)
            self.dots('themes','set','pywal16',code=1)
            self.assertFalse(self.state.exists())
            self.assertFalse((self.home/'BAD').exists())
        p = self.wal_export()
        p.write_text(p.read_text().replace("cursor='#abcdef'", 'cursor="#abcdef\''))
        self.dots('themes','set','pywal16',code=1)
        self.assertFalse(self.state.exists())
        p = self.wal_export()
        p.write_text(p.read_text().replace("color15='#2f3f4f'\n",''))
        self.dots('themes','set','pywal16',code=1)
        self.assertFalse(self.state.exists())

    def test_hyphenated_completion_and_zsh_roundtrip(self):
        for shell in ('bash','zsh','fish'):
            self.assertIn('rose-pine',self.dots('__complete',shell,'3','--','dots','themes','set','rose-').stdout)
            self.assertIn('dawn',self.dots('__complete',shell,'4','--','dots','themes','set','rose-pine','').stdout)
            self.assertIn('sumiInk3',self.dots('__complete',shell,'5','--','dots','themes','color','kanagawa','wave','sumi').stdout)
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
        names={'tokyonight':'tokyonight.nvim','rose-pine':'rose-pine','kanagawa':'kanagawa.nvim',
               'gruvbox':'gruvbox.nvim','pywal16':'pywal16.nvim'}
        config=os.environ.get('DOTS_THEME_PLUGIN_SOURCES')
        sources=json.loads(Path(config).read_text()) if config else {}
        deps=self.root/'plugins';deps.mkdir()
        for theme,directory in names.items():
            path=Path(sources[theme]['path']) if theme in sources else Path(os.environ['HOME'])/'.local/share/nvim/lazy'/directory
            if not path.is_dir(): self.skipTest('public plugin source unavailable: '+theme)
            shutil.copytree(path,deps/theme,ignore=shutil.ignore_patterns('.git'))
        cat = Path(sources['catppuccin']['path']) if 'catppuccin' in sources else Path(os.environ['HOME'])/'.local/share/nvim/lazy/catppuccin'
        if not (cat/'lua/catppuccin/init.lua').is_file(): self.skipTest('public plugin source unavailable: catppuccin')
        shutil.copytree(cat,deps/'catppuccin',ignore=shutil.ignore_patterns('.git'))
        (self.root/'lua/util').mkdir(parents=True)
        for name in ['dots_theme.lua','dots_theme_adapters.lua']:
            shutil.copy2(REPO/'configs/nvim/lua/util'/name,self.root/'lua/util'/name)
        shutil.copytree(REPO/'configs/nvim/colors',self.root/'colors')
        self.wal_export()
        self.dots('themes','set','tokyonight','night')
        script=self.root/'families.lua'
        script.write_text(r'''local root=vim.env.HOME.."/.."
vim.opt.rtp:prepend(root)
for _,name in ipairs({"tokyonight","rose-pine","kanagawa","gruvbox","pywal16","catppuccin"}) do
  vim.opt.rtp:append(root.."/plugins/"..name)
end
local bridge=require("util.dots_theme")
bridge.startup()
assert(vim.g.colors_name == "tokyonight-night")
assert(not package.loaded.catppuccin, "startup must not load the unselected family")
local choices={
 {"tokyonight","day","light"},{"tokyonight","moon","dark"},{"tokyonight","storm","dark"},
 {"rose-pine","main","dark"},{"rose-pine","dawn","light"},{"rose-pine","moon","dark"},
 {"kanagawa","wave","dark"},{"kanagawa","lotus","light"},{"kanagawa","dragon","dark"},
 {"gruvbox","dark","dark"},{"gruvbox","light","light"},{"pywal16","current","dark"},
 {"catppuccin","mocha","dark"}
}
local function snapshot()
 local state=vim.env.XDG_STATE_HOME.."/dots/themes"
 local g=vim.fn.readfile(state.."/current")[1]
 return vim.json.decode(table.concat(vim.fn.readfile(state.."/generations/"..g.."/palette.json"),"\n"))
end
for _,choice in ipairs(choices) do
 local theme,flavor,mode=unpack(choice)
 vim.fn.system({"bash",vim.env.DOTS.."/bin/dots-themes-set",theme,flavor})
 assert(vim.v.shell_error==0,theme.." set failed")
 vim.api.nvim_exec_autocmds("FocusGained",{})
 assert(vim.o.background==mode,theme.." wrong background")
 local data=snapshot()
 local hl=vim.api.nvim_get_hl(0,{name="Normal",link=false})
 assert(hl.fg==tonumber(data.roles.foreground:sub(2),16),theme.." wrong foreground: "..vim.inspect(hl))
 local gradient=bridge.gradient_colors()
 assert(#gradient>=5)
 if theme~="catppuccin" then assert(gradient[1]==data.roles.info) end
end
-- Same-theme palette edits must change highlights, not reuse the plugin's old cache.
local file=vim.env.DOTS.."/themes/tokyonight/flavors/night.toml"
local lines=vim.fn.readfile(file)
for i,line in ipairs(lines) do if line:match('^fg =') then lines[i]='fg = "#112233"' end end
vim.fn.writefile(lines,file)
vim.fn.system({"bash",vim.env.DOTS.."/bin/dots-themes-set","tokyonight","night"})
assert(vim.v.shell_error==0)
bridge.reload(true)
assert(vim.api.nvim_get_hl(0,{name="Normal",link=false}).fg==0x112233)
-- A missing plugin adapter must preserve the previous display and report only once.
local adapters=require("util.dots_theme_adapters")
local saved=adapters.prepare
adapters.prepare=function(data) if data.theme=="rose-pine" then error("missing plugin fixture") end;return saved(data) end
vim.fn.system({"bash",vim.env.DOTS.."/bin/dots-themes-set","rose-pine","main"})
local warnings=0;vim.notify=function() warnings=warnings+1 end
bridge.reload();bridge.reload()
assert(warnings==1)
assert(vim.api.nvim_get_hl(0,{name="Normal",link=false}).fg==0x112233)
adapters.prepare=saved
bridge.reload(true)
assert(vim.api.nvim_get_hl(0,{name="Normal",link=false}).fg==0xe0def4)
print("ALL_FAMILIES_OK")
''')
        result=self.run_command([NVIM,'--headless','-u','NONE','-i','NONE','-l',str(script)])
        self.assertIn('ALL_FAMILIES_OK',result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
