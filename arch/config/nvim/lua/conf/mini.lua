local M = {}

local starter = require 'mini.starter'

local keymap = vim.api.nvim_set_keymap

local lazy_stats = require("lazy").stats()
local vim_version = table.concat({ vim.version().major, vim.version().minor, vim.version().patch }, ".")

local logo = {
    val = {
        " NEOVIM v" .. vim_version .. " ",
    },
}

local footer = {
    val = {
        " " .. lazy_stats.count .. " plugins (" .. lazy_stats.loaded .. " loaded) ",
    },
}

local menu = {
    [[ menu ]],
}

starter.setup {
    header = logo.val[1],
    footer = footer.val[1],
    items = {
        {
            { action = 'Telescope projects',     name = 'project',  section = menu[1] },
            { action = 'Telescope oldfiles',     name = 'recent',   section = menu[1] },
            { action = 'Telescope find_files',   name = 'find',     section = menu[1] },
            { action = 'Telescope live_grep',    name = 'word',     section = menu[1] },
            { action = 'NvimTreeFindFileToggle', name = 'explore',  section = menu[1] },
            { action = 'Lazy sync',              name = 'lazy',     section = menu[1] },
            { action = 'qall!',                  name = 'quit',     section = menu[1] },
        },
    },
    content_hooks = {
        starter.gen_hook.adding_bullet("󰤂 "),
        starter.gen_hook.aligning('center', 'center'),
    },
    starter.gen_hook.padding(5, 2),
    query_updaters = [[abcdefhijklmnopqrsuvwxyz]],
}

require('mini.indentscope').setup {
    mappings = {
        object_scope = '',
        object_scope_with_border = '',
    },
    symbol = '│',
}

local my_augroup = require('conf.builtin_extend').my_augroup
local autocmd = vim.api.nvim_create_autocmd
local set_hl = vim.api.nvim_set_hl
local highlight_link = function(opts)
    set_hl(0, opts.linked, { link = opts.linking })
end

-- The colorscheme is loaded at conf.colorscheme
-- autocmd defined in the next will not execute at that time
-- now need to manually reset the HL at the first time.
highlight_link { linked = 'MiniCursorword', linking = 'CursorLine' }
highlight_link { linked = 'MiniCursorwordCurrent', linking = 'CursorLine' }

autocmd('ColorScheme', {
    group = my_augroup,
    desc = [[Link MiniCursorword's highlight to CursorLine]],
    callback = function()
        highlight_link { linked = 'MiniCursorword', linking = 'CursorLine' }
        highlight_link { linked = 'MiniCursorwordCurrent', linking = 'CursorLine' }
    end,
})

require('mini.cursorword').setup {}

require('conf.colorscheme').default_colorsheme()

return M
