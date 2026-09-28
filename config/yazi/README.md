# Yazi Config

The active configuration uses the local [dots.yazi plugin](plugins/dots.yazi/README.md), initialized once by `init.lua`. It bundles Dotline (the Yatline-derived header/status renderer), borders, Git indicators and branch details, folder sorting, saved projects, repository naming, responsive symlink paths, hostname/user display, and pane toggles.

Appearance and feature options stay in `init.lua`; `keymap.toml` routes commands through `plugin dots`, and `yazi.toml` routes Git fetching through `dots`. Original merged plugin folders remain inactive for reference. Unrelated package dependencies remain in `package.toml`.

The symlink component combines the current directory, hovered filename, and symlink target in the header, shortening whole leading directories to fit the available window width. See the plugin README for setup, commands, storage, and verification instructions.
