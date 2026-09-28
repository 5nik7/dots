# dots.yazi

One local Yazi plugin for the Dots file-manager configuration. It bundles the active UI, Git, project, sorting, and pane features into this directory. **Dotline** is the bundled renderer derived from Yatline; it draws the header and status line.

The original plugin directories are retained for reference, but the active configuration only loads `dots`. This plugin uses its own bundled sources and does not load those originals.

## Installation and setup

Place this entire directory at `plugins/dots.yazi` inside your Yazi configuration directory. Keep the Lua modules and license files together. This is a repository-local plugin; there is no published `ya pkg add` command for it.

The sources declare Yazi 26.8.15 or newer. Native verification uses **Yazi 26.9.1 on Termux**. Git features require the `git` executable. Icons and separators use the same Nerd Font glyphs as the existing configuration.

Call setup once from `init.lua`:

```lua
require("dots"):setup({
  full_border = { type = ui.Border.PLAIN },
  git = { order = 1500 },
  folder_rules = {},
  projects = {
    save = { method = "yazi", yazi_load_event = "@projects-load" },
  },
  dotline = {
    header_line = {
      left = {
        section_a = { { type = "line", name = "tabs" } },
        section_b = { { type = "coloreds", name = "symlink" } },
        section_c = {},
      },
      right = { section_a = {}, section_b = {}, section_c = {} },
    },
    status_line = {
      left = {
        section_a = { { type = "string", name = "date", params = { "%H:%M" } } },
        section_b = {},
        section_c = {
          { type = "coloreds", name = "githead" },
        },
      },
      right = {
        section_a = {}, section_b = {},
        section_c = { { type = "coloreds", name = "permissions" } },
      },
    },
  },
  symlink = { auto_fit = true, path_color = "blue", link_color = "cyan" },
  githead = { repo_color = "blue", repo_prefix = "", repo_symbol = "", branch_color = "magenta", branch_symbol = "" },
  hostname_username = { color = "red", mode = "both" },
})
```

The complete personal configuration, including colors, separators, Git indicators, and project events, lives in [init.lua](../../init.lua). Its appearance settings are passed into the plugin, not hardcoded as personal defaults. An omitted section uses that component's defaults. All bundled features initialize; `false` is not a component-disable switch.

## Components and configuration

| Setup section | Bundled module | Behavior and options |
| --- | --- | --- |
| `full_border` | [full-border.lua](full-border.lua) | Wraps the file panes in borders; `type` selects the border style. |
| `git` | [git.lua](git.lua) | Adds per-file Git indicators; `order` controls their placement. Fetcher rules below are also required. Theme overrides remain in `th.git`. |
| `folder_rules` | [folder-rules.lua](folder-rules.lua) | Sorts a directory named `Downloads` by descending modification time; other directories use alphabetical order with directories first. No options. |
| `projects` | [projects.lua](projects.lua) | Saves, restores, deletes, and merges tab collections; sections are `event`, `save`, `last`, `merge`, and `notify`. |
| `dotline` | [dotline.lua](dotline.lua) | Header/status renderer; preserves Yatline's section, component, separator, padding, style, permission, and layout options. |
| `symlink` | [symlink.lua](symlink.lua) | Registers `symlink`, combining the current path, hovered name, and link target; fits whole leading directories to available width. |
| `githead` | [githead.lua](githead.lua) | Registers `githead`, one colored component containing repository name and Git details separated by a space; repository options are `repo_color`, `repo_prefix`, and `repo_symbol`. Retains branch, remote, tag, commit, ahead/behind, stash, state, staged, unstaged, and untracked options. |
| `hostname_username` | [hostname-username.lua](hostname-username.lua) | Registers `hostname_username`; `mode` accepts `host`, `user`, or `both`, and `color` sets its foreground. Shown only when added to a Dotline section; returns no text on non-Unix platforms. |

[toggle-pane.lua](toggle-pane.lua) is command-driven and needs no setup section. It restores the previous pane ratios when toggled again.

For `symlink`, `path_*`, `name_*`, and `link_*` options accept `color`, `max_length`, `shorten`, and `rtl` suffixes. A length of `0` means unlimited. `auto_fit` defaults to true; `arrow` and `arrow_color` style the connector. Color overrides can also be supplied in its `theme` table. Control characters are sanitized for single-line display.

### Dotline extensions

Bundled components register against `Dotline.string`, `Dotline.line`, and `Dotline.coloreds`, replacing the old `Yatline` global. Existing component names such as `tabs`, `permissions`, `repo_name`, `symlink`, and `githead` remain unchanged. Add custom getters after setup, for example:

```lua
function Dotline.string.get:greeting()
  return "hello"
end
```

Reference that getter with `{ type = "string", name = "greeting" }` in a section. External Yatline extensions must be adapted to `Dotline`; there is no `Yatline` compatibility alias. Do not initialize the old renderer or extensions alongside `dots`.

## Commands and keymaps

The first argument after `--` selects the feature; remaining arguments are forwarded to it. For example:

```toml
[[mgr.prepend_keymap]]
on = ["P", "s"]
run = "plugin dots -- projects save"
desc = "Save current project"

[[mgr.prepend_keymap]]
on = ["<C-x>"]
run = "plugin dots -- toggle-pane min-preview"
desc = "Show or hide the preview pane"
```

The current [keymap](../../keymap.toml) uses these routes:

| Keys | Command |
| --- | --- |
| `Ctrl-x` | `plugin dots -- toggle-pane min-preview` |
| `X` | `plugin dots -- toggle-pane max-preview` |
| `P s` | `plugin dots -- projects save` |
| `P l` | `plugin dots -- projects load` |
| `P P` | `plugin dots -- projects load_last` |
| `P d` | `plugin dots -- projects delete` |
| `P D` | `plugin dots -- projects delete_all` |
| `P m` | `plugin dots -- projects merge current` |
| `P M` | `plugin dots -- projects merge all` |

Load or delete by saved key or name by appending it, e.g. `plugin dots -- projects load 'My project'`. Save/load/delete retain the existing interactive selection and cancellation behavior. `delete_all` immediately clears the saved project list, as in the original plugin. Unknown feature routes produce a warning. The `githead` route refreshes both repository naming and Git status internally.

### Git fetchers

Use these rules in `yazi.toml` for both files and directories:

```toml
[[plugin.prepend_fetchers]]
id = "git"
url = "*"
run = "dots"
group = "git"

[[plugin.prepend_fetchers]]
id = "git"
url = "*/"
run = "dots"
group = "git"
```

Repository-name options live in the `githead` setup section; there is no separate `repo` section or module. Use only `{ type = "coloreds", name = "githead" }` in the section: it renders `dots main !169 ?24` as one group, with no Dotline part separator between the repository and branch. The `repo_name` getter remains available for repository-only displays; adding it alongside `githead` would repeat the name. Both share one refresh generation, and results from an older request or directory are discarded.

The dispatcher forwards fetch jobs to the bundled Git module. These rules keep the configuration's existing matching, IDs, and grouping. A single combined repository/Git-head refresh responds to directory, tab, rename, bulk, move, trash, and delete events.

## Project storage and runtime

`projects.save.method = "yazi"` retains Yazi DDS persistence through `@projects-load`. Existing project data and event names are unchanged; this consolidation requires no data migration. Save/load/delete/delete-all/merge notifications still use the `project-saved`, `project-loaded`, `project-deleted`, `project-deleted-all`, and `project-merged` events. Cross-instance merge uses `projects-merge`.

For JSON file storage, set `save.method = "lua"` and a writable `save.lua_save_path`. If that path is omitted from the `save` table, the existing fallback is `%APPDATA%/yazi/state/projects.json` on Windows or `~/.local/state/yazi/projects.json` on Unix. The plugin does not create missing parent directories. The current personal config has an empty path because it uses DDS; replace that value when switching to file storage.

`main.lua` performs setup and dispatch. Each relative module has separate Yazi-managed state (for example, `dots.projects` and `dots.git`). Dotline initializes before its additional getters. Project prompts and Git commands run asynchronously; their state updates and pane ratio changes cross into the UI context using `ya.sync`.

The merged upstream packages have been removed from [package.toml](../../package.toml). Unrelated installed plugins remain separate. Updates to these bundled sources are maintained in Dots rather than through the original package entries.

## Verification

From this directory:

```sh
lua test.lua
lua test-symlink.lua
python3 -B test-native.py
```

The Lua fixtures check setup order, dispatcher arguments, fetch forwarding, pane restoration, combined Git refresh/stale-result rejection, and responsive symlink formatting. The Unix PTY test uses the surrounding repository's config and a temporary home/config/state/cache/runtime, isolated Git repository, and DDS socket directory. Only `dots.yazi` and a test probe are installed there. It checks real loader state, Git fetching and callbacks, project save/load/deletion and merge event dispatch, folder rules, pane shortcuts, and 40/80/160-column redraws. It requires Python, Git, and Yazi and does not install dependencies.

Native results currently cover Termux with Yazi 26.9.1. Lua Windows-path fixtures are not native Windows verification. The PTY checks establish successful rendering without errors, not pixel-perfect visual equivalence.

## Attribution

Dotline is derived from [Yatline](https://github.com/5nik7/yatline.yazi). Other bundled sources come from [yazi-rs/plugins](https://github.com/yazi-rs/plugins) (full-border, git, toggle-pane), [MasouShizuka/projects.yazi](https://github.com/MasouShizuka/projects.yazi), [imsi32/yatline-githead.yazi](https://github.com/imsi32/yatline-githead.yazi), and [jaja360/yatline-hostname-username.yazi](https://github.com/jaja360/yatline-hostname-username.yazi). Folder rules, repository naming, and responsive symlink integration come from the existing Dots configuration.

Original notices are retained in [licenses/](licenses/), including the Projects JSON helper's inline notice. Dots changes use the repository's [MIT license](LICENSE).
