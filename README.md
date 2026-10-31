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

Interactive setup reviews components and changes before applying them. Core, mapped files, themes and bundled applications are the defaults; packages, fonts and patched Leaf are opt-in. Existing configuration is classified and protected by the applicable backup/recovery workflow. See [installation](docs/installation.md) for acquiring a checkout, dependencies, optional sources, updates and uninstall.

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

Fonts menus include Configuration for shared output styles and font-specific list
detail and previews. Use `dots config browse --query apps.fonts` to inspect those
preferences; see [font output controls](docs/fonts.md#output-preferences).

Use `man dots` after managed POSIX core installation for the complete first-party command reference. The [wiki command reference](https://github.com/5nik7/dots/wiki/Command-reference) provides the same coverage on every platform.

Wiki reports and selectors have [output preferences](docs/wiki.md#output-preferences), available through Wiki → Configuration or `dots config browse --query wiki`.

## Contributing

Start with [AGENTS.md](AGENTS.md), the [documentation index](docs/README.md) and [active plans](plans/README.md). Preserve existing configuration and unrelated work; use isolated tests. Canonical docs live here, and the wiki is generated from them. Builds do not publish changes.
