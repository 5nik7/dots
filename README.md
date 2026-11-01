<picture>
  <source media="(prefers-color-scheme: dark)" srcset="media/logo/white/DOTS_white_2048x562.png">
  <source media="(prefers-color-scheme: light)" srcset="media/logo/black/DOTS_black_2048x562.png">
  <img src="media/logo/black/DOTS_black_2048x562.png" alt="dots" width="480">
</picture>

# dots

Manage dotfiles, shells, themes and your development environment through one command family. Dots keeps configuration in the checkout, previews managed changes, and records recovery information.

**[Read the Dots wiki](https://github.com/5nik7/dots/wiki)** · [Installation](docs/installation.md) · [Commands](docs/commands.md) · [Configuration](docs/configuration.md)

## Platforms

Dots has Bash entry points for Termux, Linux and WSL, and a native PowerShell entry point for Windows. Shared Python controllers handle the core workflows. Termux is the primary local development target; application capabilities and native acceptance vary by platform. See [platform support](docs/platforms.md) and [runtime requirements](docs/installation.md).

## Get started

From an existing checkout, preview setup first:

```sh
./install.sh --dry-run
./install.sh
```

On native Windows, use PowerShell:

```powershell
./install.ps1 -DryRun
./install.ps1
```

Interactive setup reviews components and changes before applying them. Core, mapped files, themes and bundled applications are the defaults; packages, fonts and patched Leaf are opt-in. Leaf installer integration has fixture coverage; [real build verification remains separate and pending](plans/installer-update.md#deferred-real-leaf-verification). Existing configuration is classified and protected by the applicable backup/recovery workflow. See [installation](docs/installation.md) for acquiring a checkout, dependencies, optional sources, updates and uninstall.

Open a new shell after setup, then explore:

```sh
dots                          # Discover command families
dots menu                     # Browse common workflows
dots help files               # Read family help
dots config                   # Inspect and edit preferences
dots wiki browse              # Read current guides offline
dots wiki search 'nvim themes' --topics
```

## Find your way around

- [Dots core](docs/core.md): workflows, directory layout and recovery.
- [Managed files](docs/files.md), [Git](docs/git.md) and [profiles](docs/profiles.md).
- [Configuration](docs/configuration.md), [environment](docs/shell-environment.md) and [shell startup](docs/shell-init.md).
- [Themes](docs/themes.md), [Neovim](docs/neovim.md), [tmux](docs/tmux.md) and [keybindings](docs/keys.md).
- [Packages](docs/packages.md), [fonts](docs/fonts.md), [Todo](docs/todo.md) and [weather](docs/wttr.md).

Package installs, removals and upgrades show compact progress and one result per manager.
Successful installs/removals also list the requested package names in a short summary.
Upgrades list packages whose installed versions changed; compact npm output hides
deprecation notices, and skipped counts use the theme's muted foreground.
Use `pkgs install --raw` for full manager output, or `--dry-run` to review commands;
see [package output](docs/packages.md#output).

Fonts menus include Configuration for shared output styles and font-specific list
detail and previews. Use `dots config browse --query apps.fonts` to inspect those
preferences; see [font output controls](docs/fonts.md#output-preferences).

Keys category/mode selectors and Weather menus share [configurable menu colors and icons](docs/configuration.md#keys-and-weather-menu-appearance), including per-entry overrides and readable plain views.

Use `man dots` after managed POSIX core installation for the complete first-party command reference. The [wiki command reference](https://github.com/5nik7/dots/wiki/Command-reference) provides the same coverage on every platform.

Wiki reports and selectors have [output preferences](docs/wiki.md#output-preferences), available through Wiki → Configuration or `dots config browse --query wiki`.

Config lists smart endpoints with category filters and sorting; terminal reports
show an indented configuration tree with compact, styled color records and colored
icon samples with their menu, status, weather or published file/Git color sources.
`dots config list colors icons` selects multiple categories. Existing Config rows
also show template/consumer fallback values and their sources. `dots config set` followed by Tab searches all full keys; `..` then
Tab opens branch choices with an empty search. At a leaf, Tab offers Allowed
values, symbolic colors or cached glyphs. See [configuration and migration](docs/configuration.md#canonical-keys-and-completion)
and [tmux component preferences](docs/tmux.md#component-preferences).

Codex toast colors, background opacity, position and duration use
[`apps.codex.toast`](docs/configuration.md#codex-warning-toast); vibration duration,
force and count use [`apps.codex.vibrate`](docs/configuration.md#codex-vibration).
Run [`dots debug alert`](docs/debug.md#test-codex-alerts) for a labelled device test.

## Contributing

Start with [AGENTS.md](AGENTS.md), the [documentation index](docs/README.md) and [active plans](plans/README.md). Preserve existing configuration and unrelated work; use isolated tests. Canonical docs live here, and the wiki is generated from them. Builds do not publish changes.
