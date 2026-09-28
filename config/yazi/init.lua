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
  pink = "magenta",
  mauve = "magenta",
  red = "red",
  maroon = "red",
  peach = "yellow",
  yellow = "yellow",
  green = "green",
  teal = "cyan",
  sky = "cyan",
  sapphire = "cyan",
  blue = "blue",
  lavender = "#b4befe",
  text = "white",
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

require("projects"):setup({
  event = {
    save = {
      enable = true,
      name = "project-saved",
    },
    load = {
      enable = true,
      name = "project-loaded",
    },
    delete = {
      enable = true,
      name = "project-deleted",
    },
    delete_all = {
      enable = true,
      name = "project-deleted-all",
    },
    merge = {
      enable = true,
      name = "project-merged",
    },
  },
  save = {
    method = "yazi", -- yazi | lua
    yazi_load_event = "@projects-load", -- event name when loading projects in `yazi` method
    lua_save_path = "", -- path of saved file in `lua` method, comment out or assign explicitly
    -- default value:
    -- windows: "%APPDATA%/yazi/state/projects.json"
    -- unix: "~/.local/state/yazi/projects.json"
  },
  last = {
    update_after_save = true,
    update_after_load = true,
    update_before_quit = false,
    load_after_start = false,
  },
  merge = {
    event = "projects-merge",
    quit_after_merge = false,
  },
  notify = {
    enable = true,
    title = "Projects",
    timeout = 3,
    level = "info",
  },
})

require("yatline"):setup({

  section_separator_open = "",
  section_separator_close = "",

  inverse_separator_open = "",
  inverse_separator_close = "",

  part_separator_open = "",
  part_separator_close = "",

  padding = { inner = 1, outer = 1 },

  style_a = {
    fg = "black",
    bold = true,
    underline = false,
    reversed = true,
    bg_mode = {
      normal = "blue",
      select = "pink",
      un_set = "red",
    },
  },
  style_b = { bg = "black", fg = "white" },
  style_c = { bg = "black", fg = "white" },

  permissions_t_fg = "black",
  permissions_r_fg = "yellow",
  permissions_w_fg = "red",
  permissions_x_fg = "green",
  permissions_s_fg = "black",

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
        { type = "coloreds", custom = false, name = "symlink" },
        -- { type = "string", custom = false, name = "tab_path", params = { false, 24, 10 } },
        -- { type = "coloreds", custom = false, name = "tab_path" },
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
      section_c = {},
    },
  },

  status_line = {
    left = {
      section_a = {
        -- { type = "string", name = "tab_mode" },
        { type = "string", name = "date", params = { "%H:%M" } },
      },
      section_b = {
        -- { type = "string", name = "hovered_size" },
      },
      section_c = {
        { type = "coloreds", custom = false, name = "repo_name" },
        { type = "coloreds", custom = false, name = "githead" },
        -- { type = "coloreds", name = "count" },
      },
    },
    right = {
      section_a = {
        -- { type = "string", name = "cursor_position" },
        -- { type = "string", name = "hovered_size" },
      },
      section_b = {
        -- { type = "coloreds", custom = false, name = "hostname_username" },
        -- { type = "string", name = "cursor_percentage" },
        -- { type = "coloreds", custom = false, name = "permissions" },
      },
      section_c = {
        { type = "coloreds", name = "permissions" },
        -- { type = "string", name = "hovered_file_extension", params = { true } },
        -- { type = "coloreds", name = "permissions" },
      },
    },
  },
})

require("dots-repo"):setup({
  repo_color = "blue",
  repo_prefix = "", -- Literal text; include any desired trailing space.
  repo_symbol = "", -- Optional icon; i
})

require("dots-symlink"):setup({
  auto_fit = true,
  path_color = "blue",
  path_max_length = 0,
  path_shorten = true,
  path_rtl = true,
  name_color = "white",
  name_max_length = 0, -- 0 means unlimited.
  name_shorten = true,
  name_rtl = false,
  arrow = "  ",
  arrow_color = "darkgray",
  link_color = "cyan",
  link_max_length = 0,
  link_shorten = true,
  link_rtl = true,
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
  branch_color = "magenta",
  branch_symbol = "",
  branch_borders = "",

  show_remote_branch = true, -- only shown if different from local branch
  always_show_remote_branch = false, -- always show remote branch even if it the same as local branch
  always_show_remote_repo = false, -- Adds `origin/` if `always_show_remote_branch` is enabled
  remote_branch_prefix = ":",
  remote_branch_color = "magenta",

  show_tag = true, -- only shown if branch is not available
  always_show_tag = false,
  tag_color = "magenta",
  tag_symbol = "#",

  show_commit = true, -- only shown if branch AND tag are not available
  always_show_commit = false,
  commit_color = "magenta",
  commit_symbol = "@",

  show_behind_ahead_remote = true,
  behind_remote_color = "magenta",
  behind_remote_symbol = "⇣",
  ahead_remote_color = "magenta",
  ahead_remote_symbol = "⇡",

  show_stashes = true,
  stashes_color = "darkgray",
  stashes_symbol = "$",

  show_state = true,
  show_state_prefix = true,
  state_color = "red",
  state_symbol = "~",

  show_staged = true,
  staged_color = "cyan",
  staged_symbol = "+",

  show_unstaged = true,
  unstaged_color = "cyan",
  unstaged_symbol = "!",

  show_untracked = true,
  untracked_color = "cyan",
  untracked_symbol = "?",
})

require("yatline-hostname-username"):setup({
  color = "red",
  mode = "both", -- "host", "user", "both"
})
