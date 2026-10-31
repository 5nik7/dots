#!/usr/bin/env python3
"""Published editor preference consumption in copied public Neovim runtimes."""
import json
import unittest
import test_anodize_nvim as fixtures
from nvim_theme_fixture import install,run
from test_themes import NVIM

@unittest.skipUnless(NVIM,'Neovim unavailable')
class Config(unittest.TestCase):
    setUp=fixtures.AnodizeNvim.setUp
    run_command=fixtures.AnodizeNvim.run_command
    dots=fixtures.AnodizeNvim.dots
    # Run only the focused integration below; existing bridge tests are separate.
    test_startup_fallback_and_missing_plugin=None
    test_lualine_and_highlight_preferences=None
    test_dashboard_repaint_preserves_phase_and_cleanup=None
    test_real_lazy_load_order=None
    test_transparency_setting_and_inactive_theme=None

    def test_published_options_highlights_icons_and_placement(self):
        path=self.repo/'default/config.json';doc=json.loads(path.read_text())
        doc['apps']['nvim']['options'].update(wrap=False,number=True)
        doc['apps']['nvim']['theme']['transparent']=False
        doc['apps']['nvim']['highlights']={'@variable.member':{'fg':'#123456','bold':True}}
        doc['apps']['nvim']['icons']={'diagnostics':{'Error':'TEST'}}
        doc['apps']['nvim']['icon_styles']={'diagnostics.Error':{'fg':'#654321'}}
        layout=doc['formatting']['apps']['nvim']['lualine']
        layout['sections'].update(a=[],c=['mode','path'],x=['diagnostics'])
        layout.update(padding_left=0,padding_right=2,component_separator_left='L',
                      component_separator_right='R',section_separator_left='S',section_separator_right='T')
        path.write_text(json.dumps(doc))
        self.dots('theme','set','catppuccin-mocha')
        run(self,r'''
vim.o.number=false
_G.LazyVim={config={icons={diagnostics={Error="E",Warn="W",Info="I",Hint="H"},git={added="+",modified="~",removed="-"}}},
 lualine={root_dir=function() return "ROOT" end,pretty_path=function() return "PATH" end}}
_G.Snacks={profiler={status=function() return "PROFILER" end}}
package.loaded.lualine_require={}
bridge.startup();vim.wait(40)
local config=require("util.dots_config")
assert(not vim.o.wrap and vim.o.number)
assert(hl("Normal").bg~=nil)
assert(hl("@variable.member").fg==0x123456 and hl("@variable.member").bold)
assert(hl("DiagnosticSignError").fg==0x654321)
assert(LazyVim.config.icons.diagnostics.Error=="TEST")
vim.g.lualine_laststatus=3
local layout=require("plugins.lualine")[1].opts()
assert(#layout.sections.lualine_a==0)
assert(layout.sections.lualine_c[1][1]=="mode" and layout.sections.lualine_c[2][1]=="PATH")
assert(layout.sections.lualine_x[1].symbols.error=="TEST")
assert(layout.sections.lualine_c[1].padding.left==0 and layout.sections.lualine_c[1].padding.right==2)
assert(layout.options.component_separators.left=="L" and layout.options.component_separators.right=="R")
assert(layout.options.section_separators.left=="S" and layout.options.section_separators.right=="T")
local file=vim.env.XDG_STATE_HOME.."/dots/current/theme/preferences.json"
local doc=vim.json.decode(table.concat(vim.fn.readfile(file),"\n"))
doc.apps.nvim.options.options.number=vim.NIL
doc.apps.nvim.options.options.wrap=true
doc.apps.nvim.options.icons={}
doc.apps.nvim.options.highlights={}
doc.apps.nvim.options.icon_styles={}
vim.fn.writefile({vim.json.encode(doc)},file)
config.refresh();vim.wait(40)
assert(not vim.o.number and vim.o.wrap)
assert(LazyVim.config.icons.diagnostics.Error=="E")
assert(hl("@variable.member").fg~=0x123456)
vim.fn.writefile({"{broken"},file);config.refresh()
assert(vim.o.wrap)
''')

if __name__=='__main__':unittest.main()
