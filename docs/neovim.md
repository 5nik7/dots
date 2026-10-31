# Neovim (nvim) with Dots

The optional `config/nvim` submodule contains a personal LazyVim configuration. Dots records an exact configuration commit; the editor repository owns its plugins, language tooling and keymaps. This guide explains the Dots integration. The [Neovim repository](https://github.com/5nik7/nvim) owns the full editor handbook and platform requirements.

## Inspect and set up safely

```sh
git submodule status -- config/nvim
dots files list --repo nvim
./install.sh --with-source nvim --dry-run
```

The setup preview reports the optional source and applicable mappings. Explicitly applying setup with `--with-source nvim` can acquire that public source; ordinary documentation lookup never initializes it. To retrieve only the source, use `git submodule update --init -- config/nvim` after reviewing the checkout. Retrieval alone does not install plugins or activate the configuration.

Before activation, inspect `:echo stdpath('config')` and `:echo stdpath('data')` in your existing editor and preserve its configuration. Conventional destinations are `~/.config/nvim` on Termux/Linux/WSL and `%LOCALAPPDATA%\nvim` on native Windows, subject to XDG settings and `NVIM_APPNAME`. Keep Windows and WSL installations separate. Follow [installation and recovery](installation.md) and the editor's [installation instructions](https://github.com/5nik7/nvim#install-as-the-default-config).

First startup can download lazy.nvim and plugins. The current editor configuration requires Neovim 0.11.2+ with LuaJIT and Git 2.19+. Termux uses native PATH executables and disables Mason downloads; desktop platforms use supported Mason integrations. Missing language tools are skipped. Installing prerequisites or running the real editor is an explicit action, not a documentation test.

## Find the configuration owner

| Location inside `config/nvim` | Purpose |
| --- | --- |
| `init.lua`, `lua/config/lazy.lua` | Startup and LazyVim imports |
| `lua/config/` | Options, keymaps and autocommands |
| `lua/plugins/` | Plugin specifications and overrides |
| `lua/util/` | Shared helpers and UI assets |
| `lazyvim.json` | Enabled extras and installation metadata |
| `config/highlights/anodize.lua` | Personal Anodize highlight overrides |

Changes to these files belong to the Neovim repository. Dots profile preferences and generated JSON belong to Dots; the separate local Anodize.nvim plugin owns palette reading and reload APIs.

## Nvim themes and Dots configuration

Dots publishes palette data through the stable `dots/current/theme` state link. The local Anodize.nvim plugin, normally at `~/repos/Anodize.nvim` or `ANODIZE_NVIM_DIR`, reads the validated data. It refreshes on state changes, focus or `:DotsThemeReload`; generic imported palettes do not execute downloaded Lua.

```sh
dots theme current
dots theme files
dots config explain apps.nvim
dots config get 'apps.nvim.highlights["@variable.member"].fg'
```

Supported `apps.nvim` controls include editor options, diagnostics, autoformat, animation, Anodize transparency/terminal colors, literal highlights and LazyVim icons. `formatting.apps.nvim.lualine.sections` places existing status components. The bridge preserves its last good JSON snapshot and uses public Anodize APIs. See [configuration](configuration.md), [native controls](profiles.md#other-application-controls), and [theme integration](themes.md#shell-and-neovim-behavior) for precedence and activation.

## Keybindings and troubleshooting

Run `:DotsKeys` inside Neovim to inspect effective global and buffer-local mappings. `dots keys` provides the wider application reference; configured and live observations are labeled separately. Language or buffer mappings may only exist after their plugin loads.

Use `:checkhealth`, `:Lazy` and `:messages` to diagnose the editor. Restart after installing missing external tools so availability checks run again. If a Dots preference seems absent, inspect `dots config explain KEY`, the published theme and the local Anodize.nvim path before changing editor files. Preserve explicit custom highlight and theme choices.

## Update the optional source

Review and preserve local Neovim changes before updating. `git submodule update --init -- config/nvim` checks out Dots' recorded revision; an explicit `git submodule update --remote --checkout -- config/nvim` instead follows its configured branch. Review that change with `git diff --submodule=log -- config/nvim`. Source commits belong to the Neovim repository and must be published before a dependent Dots reference is published. None of these actions is automatic.
