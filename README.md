<picture>
  <source media="(prefers-color-scheme: dark)" srcset="media/logo/white/DOTS_white_2048x562.png">
  <source media="(prefers-color-scheme: light)" srcset="media/logo/black/DOTS_black_2048x562.png">
  <img src="media/logo/black/DOTS_black_2048x562.png" alt="dots" width="480">
</picture>

# dots

Manage dotfiles, shells, themes and your development environment through one command family. Dots keeps configuration in the checkout, previews managed changes, and records recovery information.

`dots menu projects` opens a native shell in a selected configured project;
`--print` and `--json` only inspect. Windows uses PowerShell without a WSL bridge.
Theme publication can add [Dots schemes for Windows Terminal and WezTerm](docs/themes.md#native-terminal-schemes)
without replacing the selected scheme or application configuration. Native
activation and remaining parity gates are tracked in the
[Windows/WSL implementation record](plans/overkill-parity.md).

**[Read the Dots wiki](https://github.com/5nik7/dots/wiki)** · [Installation](docs/installation.md) · [Commands](docs/commands.md) · [Configuration](docs/configuration.md)

Tmux clock, battery and Git widgets retain recent valid readings through temporary refresh failures. The Termux clock supports quiet six-hour location updates and seven-day sun-time retention; battery/Git show `~` while using an older reading. See [widget settings and activation](docs/tmux.md#retained-widget-readings).

Git reports group default and verbose file lists under counted headings such as ` unstaged modified (42)`, with two spaces per level beneath each repository. Publish counts selected paths, sync groups actual changed paths, and info/submodule trees show compact state summaries. Headings use configurable status icons: `dots config browse --query icons.git.status`. Use `dots git status --short` for a state-count summary and XY rows, and `--verbose` for XY headings, metadata and phases. File rows use the configured directory color for prefixes such as `bin/`, with file colors on basenames. Save your preferred view with `dots config set apps.git.view short`. Shared progress fills the available terminal width, with only a bar and overall percentage on the first row, and a spinner, bare step count, activity and measured bar on the second. Bar glyphs and colors are configurable; `dots config set apps.cli.progress bar` selects bars alone. Available modes are `none`, `spinner`, `bar` and `both`. See [Git views](docs/git.md#output-views) and [progress settings](docs/configuration.md#progress-appearance).

Preview your current appearance with `dots debug demo progress`, `dots debug demo spinner --loop`, or `dots debug demo all --static`. The [mock gallery](docs/debug.md#mock-output-gallery) includes package, Git, file, message and help views without running operations. Package-manager labels have a separate `colors.apps.pkgs.manager` color, defaulting to the theme's magenta/pink.

Zsh completion menus distinguish commands, options, values and Git references,
with separate descriptions and existing file colors. Use
`dots config browse --query apps.completion` to customize them; see
[completion appearance](docs/shell-environment.md#completion-appearance).
Known Dots route words also use Fast Syntax Highlighting's subcommand theme
style on the command line, including after Tab insertion.
The same preferences cover Dots subcommands and standalone plugin completions,
including when FZF-tab group headings are hidden. Development checks enumerate
the command catalog and audit completion ownership in associated projects;
see [completion verification](docs/testing.md#shell-completion-colors).

## Platforms

Dots has Bash entry points for Termux, Linux and WSL, and a native PowerShell entry point for Windows. Shared Python controllers handle the core workflows. Termux is the primary local development target; application capabilities and native acceptance vary by platform. See [platform support](docs/platforms.md) and [runtime requirements](docs/installation.md).

## Get started

For a fresh machine, obtain the repository's `bootstrap.sh` or `bootstrap.ps1`,
then preview checkout acquisition and required runtimes:

```sh
sh bootstrap.sh --dry-run
sh bootstrap.sh
```

On native Windows, use `./bootstrap.ps1 --dry-run`, then `./bootstrap.ps1`.
Bootstrap requests approval before preparing prerequisites or managed changes;
see [fresh-machine bootstrap](docs/installation.md#fresh-machine-bootstrap).

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
dots config                   # Browse and edit shared preferences
dots wiki browse              # Read current guides offline
dots wiki search 'nvim themes' --topics
```

## Find your way around

Help distinguishes executables, commands, subcommands, options and arguments with configurable theme colors. Open `dots config browse --query colors.apps.cli.help` to edit them, or set `apps.cli.tagline` to change the root phrase (`Manage your dotfiles and more...` by default; empty hides it). Help-only changes apply on the next invocation. See [help preferences](docs/configuration.md#help-and-usage-preferences).

Human text preserves valid Unicode and renders malformed bytes and terminal
controls as inert escapes across byte-oriented and Unicode-aware Bash locales.

Bash startup evaluates each successful tool activation once per shell, including
mise; reload retries failed or newly available tools. See [shared shell behavior](docs/shared-shells.md#interactive-startup).

Use `dots cleanup` to review supported disposable caches and diagnostic logs
in groups, then see the size and number of files removed. `dots cleanup scan`
previews candidates; `dots cleanup history` shows runs and the combined verified
size. Old Pi/Ayu checkpoints require explicit selection and approval. See
[cleanup groups, safeguards and reports](docs/cleanup.md).

Native Windows also has [standalone utility adapters](docs/shell-utils.md#native-windows-standalone-adapters)
for link/path inspection, FZF workflows and HTTP/cheat-sheet/browser commands,
with inert contextual completion. Explicit theme background changes support a
Windows lock-screen adapter; desktop activation and visible acceptance remain
separate from source verification. See the [Overkill acceptance record](plans/overkill-parity.md).

- [Dots core](docs/core.md): workflows, directory layout and recovery.
- [Managed files](docs/files.md), [Git](docs/git.md) and [profiles](docs/profiles.md).
- [Configuration](docs/configuration.md), [environment](docs/shell-environment.md) and [shell startup](docs/shell-init.md).
- [Themes](docs/themes.md), [Neovim](docs/neovim.md), [tmux](docs/tmux.md) and [keybindings](docs/keys.md).
- [Packages](docs/packages.md), [fonts](docs/fonts.md), [Todo](docs/todo.md) and [weather](docs/wttr.md).

`bak PATH` moves files to `~/.bakstore` by default (`--copy` retains originals). `dots link SOURCE TARGET` safely replaces destinations with recoverable links. Blastoff uses the same backup store; deleting backups also removes their empty owned containers. See [backups and safe links](docs/backups.md).

Package installs, removals and upgrades show compact progress and one result per manager.
`pkgs up` / `dots pkgs up` give managers equal shares of overall progress, with
current steps and native transfer percentages shown separately. Font batches
and downloads also use the shared progress preference.
Successful installs/removals also list the requested package names in a short summary.
Upgrades list packages whose installed versions changed; compact npm output hides
deprecation and the routine force/allow-scripts notices. Package names use the theme
accent, skipped counts use the muted foreground, and inactivity shows a timer.
Pip upgrades continue after individual failures, prioritize failed-package errors
and summarize dependency conflicts once.
Global npm installs/upgrades offer a separate prompt to run blocked install scripts,
remembering verified runs for unchanged installations. Automatic Termux pip upgrades
use compatible wheels, and gem upgrades include RubyGems self-update. Package colors
are configurable under `colors.apps.pkgs`.
Use `pkgs install --raw` for full manager output, or `--dry-run` to review commands;
see [package output](docs/packages.md#output).

Fonts menus include Configuration for shared output styles and font-specific list
detail and previews. Use `dots config browse --query apps.fonts` to inspect those
preferences; see [font output controls](docs/fonts.md#output-preferences).

The Termux profile includes [Dots FIGlet lettering](docs/fonts.md#figlet-lettering): `figlet -C utf8 -f dots 'Dots'` uses logo capitals, while `-f dots-mixed` preserves upper/lowercase. Both include degree signs and additional symbols.

Keys category/mode selectors and Weather menus share [configurable menu colors and icons](docs/configuration.md#keys-and-weather-menu-appearance), including per-entry overrides and readable plain views.

Use `man dots` after managed POSIX core installation for the complete first-party command reference. The [wiki command reference](https://github.com/5nik7/dots/wiki/Command-reference) provides the same coverage on every platform.

Wiki reports and selectors have [output preferences](docs/wiki.md#output-preferences), available through Wiki → Configuration or `dots config browse --query wiki`.

Preferences are separated from profile file/environment mappings: behavior and
formatting use `default/config.json`, with colors/icons in adjacent TOML files.
`dots config set KEY VALUE` saves shared defaults; `--profile NAME` saves an override.
Use `dots config import termux --profile windows --dry-run` to review a portable
appearance merge. Native application settings keep their native files. See
[configuration storage and import](docs/configuration.md#preference-files-and-appearance-import).
Bak completion is included for all six initialized shells; see [backups](docs/backups.md#completion).

Config menu previews use `~/…` for home paths, including path-valued settings; editors retain the full values.
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

Use `cpy "some text"` or `command | cpy` to copy text, and `pst` to print the system clipboard. The shortcuts select Android, Linux desktop, or Windows/WSL providers; see [clipboard commands](docs/shell-utils.md#system-clipboard-commands) for dependencies and PowerShell usage.

Use `dots clipboard` for searchable local history, pinning, copy/print, and input-buffer selection. `dots clipboard capture` saves the current clipboard explicitly; automatic copy recording and the external watcher stay off until enabled. The [clipboard guide](docs/clipboard.md) covers commands, popup keys, Ctrl-X/Ctrl-V widgets and Config controls.

## Contributing

Start with [AGENTS.md](AGENTS.md), the [documentation index](docs/README.md) and [active plans](plans/README.md). Preserve existing configuration and unrelated work; use isolated tests. Canonical docs live here, and the wiki is generated from them. Builds do not publish changes.
