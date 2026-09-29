# Yazi Config

The active configuration uses the local [dots.yazi plugin](plugins/dots.yazi/README.md), initialized once by `init.lua`. It bundles Dotline (the Yatline-derived header/status renderer), borders, Git indicators and branch details, folder sorting, saved projects, repository naming, responsive symlink paths, hostname/user display, and pane toggles.

Appearance and feature options stay in `init.lua`; `keymap.toml` routes commands through `plugin dots`, and `yazi.toml` routes Git fetching through `dots`. Original merged plugin folders remain inactive for reference. Unrelated package dependencies remain in `package.toml`.

`folder_rules` in `init.lua` accepts an ordered list of rules with `name`, `sort`, `reverse`, and `dir_first` fields. The configured Downloads rule sorts newest first; add more entries to customize other folders. The first matching rule wins, and unmatched folders use alphabetical order with directories first.

The `hover` component combines the current directory, hovered item icon and filename, and symlink target in the header, displaying home paths with `~` before shortening whole leading directories to fit the available window width. For example, a hovered folder appears as `~/dots/config/  yazi`. See the plugin README for setup, commands, storage, and verification instructions.

File panes use the inherited `LS_COLORS` foreground, background, and text attributes. By default, `hover.styles.name.source = "file"` and `hover.styles.link.source = "target"`, so the hovered header icon/name keeps its own symlink color and the target basename uses its actual style, and `hover.styles.link_dir` independently styles the target’s directory portion. Preview rows without a filled background use space padding instead of default-colored `█` caps. Set `ls_colors.enabled = false` to restore Yazi’s native listing styles; an empty or unset `LS_COLORS` also uses native styles. Restart Yazi after changing shell colors. See the plugin README for matching details and limits.

The Git header prepends the remote host icon (for example, `󰊤 dots main !15 ?4`) using optional `git-it`. In `githead`, `show_remote_icon` controls the icon, `repo_color` colors ordinary repositories, and `repo_owned_color` colors repositories matching git-it’s configured owner namespaces. The personal defaults are blue and green. Without usable helper metadata, the label keeps the ordinary color and omits the icon. See the [plugin options](plugins/dots.yazi/README.md) for ownership configuration and fallback behavior.

Customize the header through `hover.styles.path`, `name`, `icon`, `arrow`, `link_dir`, and `link`: choose a file/target/directory/native/custom source, then override `fg`, `bg`, or text attributes independently. The icon inherits the name by default; visibility and icon spacing are configurable too. See [hover styling and layout](plugins/dots.yazi/README.md#hover-styling-and-layout) for examples and legacy color-option precedence.
