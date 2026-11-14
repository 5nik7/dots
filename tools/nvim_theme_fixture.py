"""Copy only public theme runtime files into a test-owned Neovim configuration."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

from test_themes import REPO, NVIM


def install(test):
    plugin = Path(os.environ.get('ANODIZE_NVIM_DIR') or Path.home() / 'repos/Anodize.nvim')
    if not (plugin / 'lua/anodize/init.lua').is_file():
        test.skipTest('Anodize.nvim source unavailable; set ANODIZE_NVIM_DIR')
    target = test.root / 'Anodize plugin ü'
    target.mkdir()
    for name in ('lua', 'colors', 'plugin'):
        shutil.copytree(plugin / name, target / name)
    config = test.root / 'editor config ü'
    for name in ('util', 'config/highlights', 'plugins'):
        (config / 'lua' / name).mkdir(parents=True, exist_ok=True)
    for name in ('util/dots_theme.lua', 'util/dots_config.lua', 'util/dots_theme_legacy.lua', 'util/dashboard_gradient.lua',
                 'config/highlights/anodize.lua', 'plugins/anodize.lua', 'plugins/lualine.lua', 'plugins/colorscheme.lua'):
        shutil.copy2(REPO / 'config/nvim/lua' / name, config / 'lua' / name)
    runtime = test.root / 'runtime'
    runtime.mkdir(exist_ok=True)
    test.env.update(ANODIZE_NVIM_DIR=str(target), NVIM_TEST_CONFIG=str(config),
                    XDG_RUNTIME_DIR=str(runtime), USERPROFILE=str(test.home),
                    NVIM_LOG_FILE=str(test.root / 'nvim.log'))
    return config


PRELUDE = r'''
vim.opt.rtp = { vim.env.NVIM_TEST_CONFIG, vim.env.ANODIZE_NVIM_DIR, vim.env.VIMRUNTIME }
vim.opt.packpath = {}
vim.o.modeline = false
vim.o.shadafile = "NONE"
local spec = require("plugins.anodize")[1]
assert(spec.dir == vim.env.ANODIZE_NVIM_DIR and spec.lazy == false and spec.priority == 1000)
local loads = 0
package.loaded.lazy = { load = function(opts)
  assert(opts.plugins[1] == "anodize")
  if loads == 0 then spec.config(spec, spec.opts) end
  loads = loads + 1
end }
local bridge = require("util.dots_theme")
local function hl(name) return vim.api.nvim_get_hl(0, {name=name, link=false}) end
local function snapshot()
 return vim.json.decode(table.concat(vim.fn.readfile(vim.env.XDG_STATE_HOME.."/dots/current/theme/palette.json"),"\n"))
end
local function publish(theme, flavor)
 local id = flavor and (theme.."-"..flavor) or theme
 local command = {"bash", vim.env.DOTS.."/bin/dots-theme-set", id}
 vim.fn.system(command)
 assert(vim.v.shell_error == 0, "fixture publication failed")
end
local function current(id)
 return vim.wait(3000, function()
   local p = require("anodize").get_palette()
   return p and p.metadata.id == id
 end, 20)
end
'''


def _run_posix(argv, *, env, cwd, output_root, timeout=40):
    """Bound an editor and its publication children to one owned process group."""
    # Files avoid communicate() waiting forever on pipes inherited by children.
    # The files and all commands belong to this fixture, never a live editor.
    with tempfile.TemporaryFile(dir=output_root) as stdout, tempfile.TemporaryFile(dir=output_root) as stderr:
        process = subprocess.Popen(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   start_new_session=True)
        expired = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
        finally:
            # Also remove background children left after an otherwise successful
            # editor exit. No process outside this freshly created group is sent
            # a signal. Reap the direct child; orphan reaping belongs to the OS.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
        stdout.seek(0); stderr.seek(0)
        output = stdout.read()
        errors = stderr.read()
        if expired:
            raise subprocess.TimeoutExpired(argv, timeout, output=output, stderr=errors)
        return subprocess.CompletedProcess(argv, process.returncode,
                                           output.decode('utf-8'), errors.decode('utf-8'))


def run(test, body, marker='ANODIZE_NVIM_OK'):
    script = test.root / 'check_editor.lua'
    script.write_text(PRELUDE + '\n' + body + '\nprint(' + repr(marker) + ')\n')
    command = [NVIM, '--headless', '-u', 'NONE', '-i', 'NONE', '-n', '--noplugin', '-l', str(script)]
    if os.name == 'posix':
        result = _run_posix(command, env=test.env, cwd=test.home, output_root=test.root)
        test.assertEqual(result.returncode, 0, (command, result.stdout, result.stderr))
    else:
        result = test.run_command(command)
    test.assertIn(marker, result.stdout + result.stderr)
