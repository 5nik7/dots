require("full-border"):setup {
  -- Available values: ui.Border.PLAIN, ui.Border.ROUNDED
  type = ui.Border.PLAIN,
}

require("git"):setup()
require("folder-rules"):setup()

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
      section_b = {
        -- { type = "coloreds", custom = false, name = "tab_path" },
        -- {
        --   type = "string",
        --   custom = false,
        --   name = "hovered_path",
        --   params = { { trimed = false, max_length = 24, trim_length = 10 } },
        -- },
      },
      section_c = {
        -- {
        --   type = "string",
        --   custom = false,
        --   name = "hovered_name",
        --   params = { { trimed = false, show_symlink = false, max_length = 24, trim_length = 10 } },
        -- },
        -- {
        --   type = "string",
        --   custom = false,
        --   name = "hovered_name",
        --   params = { { trimed = false, show_symlink = false, max_length = 24, trim_length = 10 } },
        -- },
        -- { type = "coloreds", custom = false, name = "symlink" },
      },
    },
    right = {
      section_a = {
        -- { type = "line", custom = false, name = "tabs", params = { "right" } },
        -- { type = "string", custom = false, name = "date", params = { "%I:%M" } },
      },
      section_b = {
        -- { type = "string", custom = false, name = "date", params = { "%a %b %d" } },
      },
      section_c = {
        -- { type = "coloreds", custom = false, name = "githead" },
      },
    },
  },

  status_line = {
    left = {
      section_a = {
        { type = "string", custom = false, name = "tab_mode" },
      },
      section_b = {
        { type = "coloreds", custom = false, name = "tab_path" },
        {
          type = "string",
          custom = false,
          name = "hovered_name",
          params = { { trimed = false, show_symlink = false, max_length = 24, trim_length = 10 } },
        },
      },
      section_c = {
        { type = "coloreds", custom = false, name = "githead" },
        -- { type = "coloreds", custom = false, name = "githead" },
        -- { type = "string", custom = false, name = "tab_path" },
        -- { type = "coloreds", custom = false, name = "count" },

      },
    },
    right = {
      section_a = {
        { type = "string", custom = false, name = "date", params = { "%I:%M %p" } },
        -- { type = "string", custom = false, name = "cursor_position" },
      },
      section_b = {
        { type = "string", custom = false, name = "hovered_size" },
        -- { type = "string", custom = false, name = "cursor_percentage" },
      },
      section_c = {
        -- { type = "coloreds", custom = false, name = "githead" },

        -- { type = "string",   custom = false, name = "hovered_file_extension", params = { true } },
        { type = "coloreds", custom = false, name = "permissions" },
      },
    },
  },
})
require("yatline-symlink"):setup({
  symlink_color = "cyan",
})

require("yatline-githead"):setup({
  show_branch = true,
  branch_prefix = "",
  prefix_color = "white",
  branch_color = "bright black",
  branch_symbol = "",
  branch_borders = "",

  commit_color = "bright magenta",
  commit_symbol = "@",

  show_behind_ahead = true,
  behind_color = "bright magenta",
  behind_symbol = "⇣",
  ahead_color = "bright magenta",
  ahead_symbol = "⇡",

  show_stashes = true,
  stashes_color = "bright magenta",
  stashes_symbol = "$",

  show_state = true,
  show_state_prefix = true,
  state_color = "red",
  state_symbol = "~",

  show_staged = true,
  staged_color = "bright yellow",
  staged_symbol = "+",

  show_unstaged = true,
  unstaged_color = "bright yellow",
  unstaged_symbol = "!",

  show_untracked = true,
  untracked_color = "blue",
  untracked_symbol = "?",
})

require("yatline-tab-path"):setup({
  path_fg = "bright blue",
  filter_fg = "brightyellow",
  search_label = " search",
  filter_label = " filter",
  no_filter_label = "",
  flatten_label = " flatten",
  separator = "  ",
})

th.git = th.git or {}
th.git.modified = ui.Style():fg("yellow")
th.git.deleted = ui.Style():fg("red"):bold()
