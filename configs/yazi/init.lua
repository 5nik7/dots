require("full-border"):setup()

local catppuccin_theme = require("yatline-catppuccin"):setup("mocha")

require("yatline"):setup({

    theme = catppuccin_theme,

    section_separator = { open = "", close = "" },
    part_separator = { open = "", close = "" },
    inverse_separator = { open = "", close = "" },

    tab_width = 20,
    tab_use_inverse = false,

    show_background = false,

    display_header_line = true,
    display_status_line = true,

    header_line = {
        left = {
            section_a = {
                { type = "line", custom = false, name = "tabs", params = { "left" } },
            },
            section_b = {},
            section_c = {
                -- {
                --     type = "string",
                --     custom = false,
                --     name = "hovered_path",
                --     params = { { trimed = false, max_length = 24, trim_length = 10 } },
                -- },
                { type = "coloreds", custom = false, name = "tab_path" },
                { type = "string", custom = false, name = "hovered_name", params = { { trimed = false, show_symlink = true, max_length = 24, trim_length = 10 } },
                },
            },
        },
        right = {
            section_a = {
                { type = "string", custom = false, name = "date", params = { "%I:%M" } },

            },
            section_b = {
                { type = "string", custom = false, name = "date", params = { "%a %b %d" } },
            },
            section_c = {
                { type = "coloreds", custom = false, name = "githead" },
            },
        },
    },

    status_line = {
        left = {
            section_a = {
                { type = "string", custom = false, name = "tab_mode" },
            },
            section_b = {
                { type = "string", custom = false, name = "hovered_size" },
            },
            section_c = {
                -- { type = "string", custom = false, name = "tab_path" },
                { type = "coloreds", custom = false, name = "count" },
            },
        },
        right = {
            section_a = {
                { type = "string", custom = false, name = "cursor_position" },
            },
            section_b = {
                { type = "string", custom = false, name = "cursor_percentage" },
            },
            section_c = {
                { type = "string",   custom = false, name = "hovered_file_extension", params = { true } },
                { type = "coloreds", custom = false, name = "permissions" },
            },
        },
    },
})

require("yatline-githead"):setup()

require("yatline-tab-path"):setup({
    path_fg = "cyan",
    filter_fg = "brightyellow",
    search_label = " search",
    filter_label = " filter",
    no_filter_label = "",
    flatten_label = " flatten",
    separator = "  ",
})
