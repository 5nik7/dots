require("full-border"):setup({
  -- Available values: ui.Border.PLAIN, ui.Border.ROUNDED
  type = ui.Border.PLAIN,
  -- type = ui.Border.DOUBLE,
})

-- th.git = th.git or {}
-- th.git.modified = ui.Style():fg("yellow")
-- th.git.deleted = ui.Style():fg("red"):bold()

require("git"):setup({
  order = 1500,
})

require("folder-rules"):setup()

local palette = {
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

require("yatline"):setup({

  section_separator = { open = "", close = "" },
  part_separator = { open = "", close = "" },
  inverse_separator = { open = "", close = "" },

  padding = { inner = 1, outer = 1 },

  style_a = {
    fg = palette.crust,
    bold = false,
    underline = false,

    bg_mode = {
      normal = palette.blue,
      select = palette.mauve,
      un_set = palette.red,
    },
  },
  style_b = { bg = palette.surface0, fg = palette.text },
  style_c = { bg = palette.base, fg = palette.text },

  permissions_t_fg = palette.lavender,
  permissions_r_fg = palette.yellow,
  permissions_w_fg = palette.red,
  permissions_x_fg = palette.green,
  permissions_s_fg = palette.surface0,

  tab_width = 0,

  selected = { icon = "󰻭", fg = "yellow" },
  copied = { icon = "", fg = "green" },
  cut = { icon = "", fg = "red" },

  files = { icon = "", fg = "blue" },
  filtereds = { icon = "", fg = "magenta" },

  total = { icon = "󰮍", fg = "yellow" },
  success = { icon = "", fg = "green" },
  failed = { icon = "", fg = "red" },

  show_background = true,

  display_header_line = true,
  display_status_line = true,

  component_positions = { "header", "tab", "status" },

  header_line = {
    left = {
      section_a = {
        { type = "line", name = "tabs" },
      },
      section_b = {
        -- { type = "coloreds", custom = false, name = "tab_path" },
        -- { type = "string", custom = false, name = "tab_path" },
      },
      section_c = {},
    },
    right = {
      section_a = {
        -- { type = "string", custom = false, name = "tab_num_files" },
        -- { type = "string", name = "date", params = { "%A, %d %B %Y" } },
      },
      section_b = {
        -- { type = "string", name = "date", params = { "%X" } },
      },
      section_c = {
        { type = "coloreds", custom = false, name = "githead" },
      },
    },
  },

  status_line = {
    left = {
      section_a = {
        { type = "string", name = "tab_mode" },
      },
      section_b = {
        -- { type = "string", name = "hovered_size" },
      },
      section_c = {
        -- { type = "string", name = "hovered_path" },
        { type = "string", custom = false, name = "hovered_name" },
        -- { type = "coloreds", name = "count" },
      },
    },
    right = {
      section_a = {
        -- { type = "string", name = "cursor_position" },
        -- { type = "string", name = "hovered_size" },
      },
      section_b = {
        -- { type = "string", name = "cursor_percentage" },
        { type = "coloreds", name = "permissions" },
        -- { type = "coloreds", custom = false, name = "permissions" },
      },
      section_c = {
        { type = "string", name = "hovered_file_extension", params = { true } },
        -- { type = "coloreds", name = "permissions" },
      },
    },
  },
})

require("yatline-githead"):setup({
  order = {
    "branch",
    "remote",
    "tag",
    "commit",
    "behind_ahead_remote",
    "stashes",
    "state",
    "staged",
    "unstaged",
    "untracked",
  },

  show_numbers = true, -- shows staged, unstaged, untracked, stashes count

  show_branch = true,
  branch_prefix = "",
  branch_color = palette.mauve,
  branch_symbol = "",
  branch_borders = "",

  show_remote_branch = true, -- only shown if different from local branch
  always_show_remote_branch = false, -- always show remote branch even if it the same as local branch
  always_show_remote_repo = false, -- Adds `origin/` if `always_show_remote_branch` is enabled
  remote_branch_prefix = ":",
  remote_branch_color = "bright magenta",

  show_tag = true, -- only shown if branch is not available
  always_show_tag = false,
  tag_color = "magenta",
  tag_symbol = "#",

  show_commit = true, -- only shown if branch AND tag are not available
  always_show_commit = false,
  commit_color = "bright magenta",
  commit_symbol = "@",

  show_behind_ahead_remote = true,
  behind_remote_color = palette.pink,
  behind_remote_symbol = "⇣",
  ahead_remote_color = palette.pink,
  ahead_remote_symbol = "⇡",

  show_stashes = true,
  stashes_color = palette.overlay2,
  stashes_symbol = "$",

  show_state = true,
  show_state_prefix = true,
  state_color = palette.red,
  state_symbol = "~",

  show_staged = true,
  staged_color = palette.teal,
  staged_symbol = "+",

  show_unstaged = true,
  unstaged_color = palette.sapphire,
  unstaged_symbol = "!",

  show_untracked = true,
  untracked_color = palette.teal,
  untracked_symbol = "?",
})
Status:children_add(function(self)
  local arrow = "  "
  local h = self._current.hovered
  if h and h.link_to then
    return ui.Line({
      ui.Span(tostring(arrow)):fg("darkgray"),
      ui.Span(tostring(h.link_to)):fg(palette.sapphire),
    })
  else
    return ""
  end
end, 3300, Status.LEFT)
