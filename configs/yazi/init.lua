local mocha = {
  rosewater = "#f5e0dc",
  flamingo = "#f2cdcd",
  pink = "#f5c2e7",
  mauve = "#cba6f7",
  red = "#f38ba8",
  maroon = "#eba0ac",
  peach = "#fab387",
  yellow = "#f9e2af",
  green = "#a6e3a1",
  teal = "#94e2d5",
  sky = "#89dceb",
  sapphire = "#74c7ec",
  blue = "#89b4fa",
  lavender = "#b4befe",
  text = "#cdd6f4",
  subtext1 = "#bac2de",
  subtext0 = "#a6adc8",
  overlay2 = "#9399b2",
  overlay1 = "#7f849c",
  overlay0 = "#6c7086",
  surface2 = "#585b70",
  surface1 = "#45475a",
  surface0 = "#313244",
  base = "#1e1e2e",
  mantle = "#181825",
  crust = "#11111b",
}

require("full-border"):setup({
  -- Available values: ui.Border.PLAIN, ui.Border.ROUNDED
  type = ui.Border.PLAIN,
})

require("git"):setup()
th.git = th.git or {}
th.git.modified = ui.Style():fg("yellow")
th.git.deleted = ui.Style():fg("red"):bold()

require("folder-rules"):setup()

-- require("bookmarks"):setup({
--   last_directory = { enable = false, persist = false, mode = "dir" },
--   persist = "none",
--   desc_format = "full",
--   file_pick_mode = "hover",
--   custom_desc_input = false,
--   show_keys = false,
--   notify = {
--     enable = false,
--     timeout = 1,
--     message = {
--       new = "New bookmark '<key>' -> '<folder>'",
--       delete = "Deleted bookmark in '<key>'",
--       delete_all = "Deleted all bookmarks",
--     },
--   },
-- })
--
-- local catppuccin_theme = require("yatline-catppuccin"):setup("mocha")
--
-- require("yatline"):setup({
--
--   theme = catppuccin_theme,
--
--   section_separator = { open = "", close = "" },
--   part_separator = { open = "", close = "" },
--   inverse_separator = { open = "", close = "" },
--
--   tab_width = 20,
--   tab_use_inverse = false,
--
--   show_background = false,
--
--   display_header_line = true,
--   display_status_line = true,
--
--   header_line = {
--     left = {
--       section_a = {
--         { type = "line", custom = false, name = "tabs", params = { "left" } },
--       },
--       section_b = {},
--       section_c = {},
--     },
--     right = {
--       section_a = {
--         -- { type = "string", custom = false, name = "date", params = { "%I:%M" } },
--       },
--       section_b = {},
--       section_c = {
--         { type = "coloreds", custom = false, name = "githead" },
--       },
--     },
--   },
--
--   status_line = {
--     left = {
--       section_a = {
--         { type = "string", custom = false, name = "tab_mode" },
--       },
--       section_b = {
--         { type = "coloreds", custom = false, name = "tab_path" },
--       },
--       section_c = {
--         {
--           type = "string",
--           custom = false,
--           name = "hovered_name",
--           params = { { trimed = false, show_symlink = false, max_length = 24, trim_length = 10 } },
--         },
--       },
--     },
--     right = {
--       section_a = {
--         -- { type = "string", custom = false, name = "cursor_position" },
--       },
--       section_b = {
--         -- { type = "string", custom = false, name = "hovered_size" },
--         -- { type = "string", custom = false, name = "cursor_percentage" },
--       },
--       section_c = {
--         -- { type = "string",   custom = false, name = "hovered_file_extension", params = { true } },
--         { type = "coloreds", custom = false, name = "permissions" },
--       },
--     },
--   },
-- })
-- require("yatline-symlink"):setup({
--   symlink_color = "cyan",
-- })
--
-- require("yatline-githead"):setup({
--   show_branch = true,
--   branch_prefix = "",
--   prefix_color = "white",
--   branch_color = mocha.overlay0,
--   branch_symbol = "",
--   branch_borders = "",
--
--   commit_color = "bright magenta",
--   commit_symbol = "@",
--
--   show_behind_ahead = true,
--   behind_color = "bright magenta",
--   behind_symbol = "⇣",
--   ahead_color = "bright magenta",
--   ahead_symbol = "⇡",
--
--   show_stashes = true,
--   stashes_color = "bright magenta",
--   stashes_symbol = "$",
--
--   show_state = true,
--   show_state_prefix = true,
--   state_color = "red",
--   state_symbol = "~",
--
--   show_staged = true,
--   staged_color = "bright yellow",
--   staged_symbol = "+",
--
--   show_unstaged = true,
--   unstaged_color = "bright yellow",
--   unstaged_symbol = "!",
--
--   show_untracked = true,
--   untracked_color = "blue",
--   untracked_symbol = "?",
-- })
--
-- require("yatline-tab-path"):setup({
--   path_fg = "bright blue",
--   filter_fg = "brightyellow",
--   search_label = " search",
--   filter_label = " filter",
--   no_filter_label = "",
--   flatten_label = " flatten",
--   separator = "  ",
-- })
--
