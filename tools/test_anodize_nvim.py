#!/usr/bin/env python3
"""Dots integration tests; use only copied public plugin/config and fixture state."""
import os
from pathlib import Path
import sys
import shutil
import unittest

import test_themes
from nvim_theme_fixture import install, run


@unittest.skipUnless(test_themes.NVIM, 'Neovim unavailable')
class AnodizeNvim(unittest.TestCase):
    run_command = test_themes.Themes.run_command
    dots = test_themes.Themes.dots

    def setUp(self):
        test_themes.Themes.setUp(self)
        self.config = install(self)

    def test_startup_fallback_and_missing_plugin(self):
        run(self, r'''
assert(not package.loaded.anodize)
assert(#bridge.gradient_colors() > 0)
assert(not package.loaded.anodize, "gradient must not load a theme plugin")
vim.g.terminal_color_0="#123456"
require("plugins.colorscheme")[1].opts.colorscheme()
assert(vim.g.colors_name=="anodize")
assert(require("anodize").get_palette().metadata.fallback)
assert(hl("Normal").bg==nil and hl("NormalFloat").bg~=nil)
assert(vim.g.terminal_color_0=="#123456")
bridge.install();bridge.install()
local events=vim.api.nvim_get_autocmds({group="dots_theme"})
assert(#events==1 and events[1].event=="ColorScheme")
vim.cmd.colorscheme("habamax")
local old=vim.g.colors_name
vim.cmd.DotsThemeReload();vim.api.nvim_exec_autocmds("VimResume",{});vim.wait(150)
assert(vim.g.colors_name==old)
for _, name in ipairs({"DiagnosticInfo","DiagnosticHint","DiagnosticWarn","DiagnosticError","SnacksDashboardHeader"}) do
 vim.api.nvim_set_hl(0,name,{})
end
vim.api.nvim_set_hl(0,"Normal",{fg="#123456"})
assert(vim.deep_equal(bridge.gradient_colors(),{"#123456"}))
-- Simulate an unavailable optional local checkout without downloading anything.
package.loaded.lazy={load=function() error("missing local plugin") end}
local original=require
_G.require=function(name) if name=="anodize" then error("unavailable") end; return original(name) end
bridge.startup()
assert(vim.g.colors_name=="habamax")
_G.require=original
''')

    def test_lualine_and_highlight_preferences(self):
        self.dots('themes','set','catppuccin')
        run(self, r'''
bridge.startup()
local p=require("anodize").get_palette()
assert(hl("SnacksPickerMatch").bold and hl("SnacksPickerMatch").underline)
assert(hl("DiagnosticVirtualTextError").bg==nil)
assert(hl("LspReferenceRead").bg==0x242438)
assert(hl("SnacksDashboardIcon").fg==tonumber(p.roles.accent:sub(2),16))
local theme=require("lualine.themes.anodize")
local initial=theme.normal.a.bg
package.loaded.lualine_require={}
_G.LazyVim={config={icons={diagnostics={Error="E",Warn="W",Info="I",Hint="H"},git={added="+",modified="~",removed="-"}}},
 lualine={root_dir=function() return "ROOT" end,pretty_path=function() return "PATH" end}}
_G.Snacks={profiler={status=function() return "PROFILER" end}}
vim.g.lualine_laststatus=3
local opts=require("plugins.lualine")[1].opts()
assert(opts.options.theme=="anodize" and opts.options.globalstatus)
assert(opts.sections.lualine_a[1].fmt("NORMAL")=="N")
assert(opts.options.component_separators.left=="" and opts.options.section_separators.right=="")
assert(opts.sections.lualine_c[1]=="ROOT" and opts.sections.lualine_y[2][1]=="location")
publish("rose-pine","dawn");assert(bridge.reload())
assert(theme==require("lualine.themes.anodize") and theme.normal.a.bg~=initial)
assert(hl("NormalFloat").bg==tonumber(snapshot().roles.background:sub(2),16))
''')

    def test_dashboard_repaint_preserves_phase_and_cleanup(self):
        self.dots('themes','set','catppuccin')
        run(self, r'''
bridge.startup()
local uv=vim.uv or vim.loop
local real_timer,real_clock=uv.new_timer,uv.hrtime
local ticks=0
local timer={}
function timer:start(_,interval,callback) self.interval=interval;self.callback=callback;self.running=true end
function timer:stop() self.running=false end
function timer:close() self.closed=true end
uv.new_timer=function() return timer end
uv.hrtime=function() return ticks end
local gradient=require("util.dashboard_gradient")
local buf=vim.api.nvim_create_buf(false,true)
vim.api.nvim_win_set_buf(0,buf)
local dashboard={buf=buf,opts={preset={header="A"}}}
local item=gradient.section(dashboard)
uv.new_timer=real_timer
assert(item.padding==1 and timer.interval==66 and timer.running)
local group=item.text[1].hl
local function expected()
 local colors=bridge.gradient_colors()
 local a,b=colors[1],colors[2]
 local parts={}
 for i=2,6,2 do
  local x,y=tonumber(a:sub(i,i+1),16),tonumber(b:sub(i,i+1),16)
  parts[#parts+1]=math.floor(x+(y-x)*0.8+0.5)
 end
 return parts[1]*65536+parts[2]*256+parts[3]
end
ticks=800000000;timer.callback();vim.wait(20)
assert(hl(group).fg==expected())
publish("rose-pine","main");assert(bridge.reload())
assert(hl(group).fg==expected(), "repaint reset animation elapsed time")
assert(not timer.closed)
-- Hide then restore the dashboard: phase pauses while hidden.
local other=vim.api.nvim_create_buf(false,true)
vim.api.nvim_win_set_buf(0,other);vim.api.nvim_exec_autocmds("TabEnter",{});vim.wait(20)
assert(not timer.running)
ticks=1800000000
vim.api.nvim_win_set_buf(0,buf);vim.api.nvim_exec_autocmds("TabEnter",{});vim.wait(20)
assert(timer.running)
timer.callback();vim.wait(20)
assert(hl(group).fg==expected(), "hidden time advanced animation")
vim.g.snacks_animate=false
assert(gradient.section(dashboard).header=="A")
vim.api.nvim_buf_delete(buf,{force=true});vim.wait(20)
assert(timer.closed)
uv.hrtime=real_clock
''')

    def test_real_lazy_load_order(self):
        source = Path(os.environ['HOME']) / '.local/share/nvim/lazy/lazy.nvim/lua'
        if not (source / 'lazy/init.lua').is_file():
            self.skipTest('installed public lazy.nvim source unavailable')
        target = self.root / 'lazy fixture'
        shutil.copytree(source, target / 'lua')
        self.env['NVIM_TEST_LAZY'] = str(target)
        self.dots('themes','set','catppuccin')
        run(self, r'''
package.loaded.lazy=nil
vim.go.loadplugins=true -- Runtime/package paths already contain only fixture sources.
vim.opt.rtp:prepend(vim.env.NVIM_TEST_LAZY)
vim.fn.system=function() error("unexpected subprocess") end
vim.fn.jobstart=function() error("unexpected job") end
vim.system=function() error("unexpected subprocess") end
require("lazy").setup({
 spec,
 {dir=vim.env.NVIM_TEST_CONFIG,name="startup-fixture",lazy=false,priority=2000,
  config=function() require("plugins.colorscheme")[1].opts.colorscheme() end},
}, {
 root=vim.env.XDG_DATA_HOME.."/lazy",lockfile=vim.env.HOME.."/lazy-lock.json",
 install={missing=false},checker={enabled=false},change_detection={enabled=false},
 rocks={enabled=false},pkg={enabled=false},readme={enabled=false},
 performance={cache={enabled=false},rtp={reset=false}},
})
assert(vim.g.colors_name=="anodize")
assert(require("anodize").status().source=="dots")
assert(hl("Normal").bg==nil and hl("Comment").fg==0x5b6078)
assert(require("lazy.core.config").plugins.anodize._.loaded)
''')

    def test_authored_theme_publication_to_editor(self):
        engine = Path(os.environ.get('ANODIZE_ENGINE') or test_themes.REPO/'anodize/.build/anodize-engine')
        if not engine.is_file():
            self.skipTest('Build the Anodize engine before authoring integration tests')
        env = dict(self.env, ANODIZE_ENGINE=str(engine))
        cli = [sys.executable,'-B',str(self.repo/'lib/dots/anodize/cli.py')]
        self.run_command(cli+['create','fixture_theme','--color','#725ac1','--yes','--json'],env=env)
        self.run_command(cli+['apply','fixture_theme','--yes','--json'],env=env)
        run(self, r'''
bridge.startup()
local p=require("anodize").get_palette()
local data=snapshot()
assert(not p.metadata.fallback and p.metadata.id=="fixture_theme")
assert(p.colors.color4==data.colors.color4)
assert(p.roles.accent==data.colors.accent)
assert(hl("Normal").fg==tonumber(data.colors.foreground:sub(2),16))
assert(hl("Normal").bg==nil and hl("NormalFloat").bg==tonumber(data.colors.background:sub(2),16))
''')


if __name__=='__main__':
    unittest.main()
