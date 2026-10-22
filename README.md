# dots

`dots` is becoming a fast, safe, modular command center for managing dotfiles, scripts, shells, themes, packages, and environment setup across Termux, Linux, WSL, and native Windows.

## Status

General Go implementation and migration are **paused** as of 2026-09-22. Current work focuses on maintaining the existing dotfiles, scripts, configurations, and documentation directly in the main checkout. Existing Go code, tests, and CI remain in place; the [roadmap](plans/roadmap.md#current-priority) tracks resumption.

The repository contains the existing dotfiles collection, the modular Bash `bin/dots` command framework, and an isolated experimental Go core under `experiments/go-portability/`. The Go command architecture remains partially implemented, with general Go development paused except the owner-authorized Anodize slice. [Go adoption is accepted](docs/decisions/0002-phase-1-go-adoption.md), with Go 1.27.1 as the initial build/test baseline. The first permanent-core slice now adds a development executable and validated read-only built-in registry; a [bounded development external protocol](docs/decisions/0003-trusted-external-command-protocol.md) adds explicit-root discovery and dispatch. The broader command center remains deferred.

There is not yet a supported remote installer or a production-ready `dots apply` workflow. Installation examples will be added only after the planner, transaction engine, backup/rollback behavior, and first Termux profile have been verified.

## Bash Command Framework

The live `dots` command discovers executable `dots-*` commands in `$DOTS/bin` and
`$DOTS/local/bin`. For example, adding `dots-example-list` makes `dots example list`
available immediately. The shared theme commands below ship with the framework.
Bash 4.4+ is required.

```bash
dots                         # Colorful help and available commands
dots commands                # List registered commands
dots commands --check        # Validate metadata and route collisions
dots --raw --dir              # Print the repository path
dots --icons=never help       # Use plain status markers
dots completion bash         # Print an adapter (also zsh or fish)
```

The help logo uses a top-to-bottom blue → cyan gradient when color is enabled.
Nerd Font icons and color are automatic in terminals; `--color=auto|always|never`
and `--icons=auto|always|never` override their environment defaults, `DOTS_COLOR`
and `DOTS_ICONS`. Automatic color respects `NO_COLOR`. Additional trusted roots
can be selected with repeated prefix `--command-dir /absolute/directory` options.
Duplicate command routes fail instead of silently overriding one another.

Slow Git, theme, file and Anodize operations show colorful spinners or phase progress bars after 500 ms in a terminal. Set `DOTS_PROGRESS=never` to disable progress independently of colors. JSON, raw output, dry runs and redirected commands stay free of progress displays; `--yes` retains terminal progress. Prompt-capable external commands use a static phase message. See [operation progress](docs/presentation.md#operation-progress).

Bash, Zsh, and Fish adapters are included in the repository's shell configuration.
They discover new commands and declared arguments on the next Tab, without a
startup scan. Zsh completion menus align command/option names and descriptions in columns,
including in FZF-tab. Open a fresh shell to load the new adapter. Help and completion read
optional static comment headers and never execute extensions. See the
[command authoring and completion contract](docs/commands.md#implemented-bash-command-framework)
for header examples, shared output helpers, and standalone integration.

## Install, update and uninstall

From an existing checkout, run `./install.sh --dry-run`, then `./install.sh` to review and apply the platform's mapped configurations. Windows uses `./install.ps1 -DryRun` and `./install.ps1`. Setup creates missing parents, retains verified backups before replacement, installs the command entry and shell configs, and prepares supported platform theme connectors. Existing correct links remain unchanged.

Fresh POSIX installs include the FSH config directory and its generated theme link.
Setup and `dots theme refresh` rebuild missing required theme outputs even when
the source fingerprint has not changed. To repair an existing checkout after
updating, review `./install.sh --dry-run`, run `./install.sh`, then open a new shell.
FSH failures now identify the affected path and repair step while retaining
last-good colors when available. See [theme recovery](docs/installation.md#declared-ownership).

Older Vivid installations use compatible scalar font styles during theme preparation,
so setup can generate the FSH theme without a font-style parser panic. Dots retains
full core and explicit suffix styles; combined category styles need Vivid 0.10+.
See [Vivid compatibility](docs/file-colors.md#vivid-compatibility) for custom templates.

`dots init --setup` and `dots files install` use the same engine. Ordinary `dots init [shell]` continues to print shell code without installation work. Use `./install.sh --update` for an explicit clean fast-forward update followed by setup, or `--with-source nvim` (repeatable) to initialize a named applicable public source. Missing optional sources are otherwise skipped; secrets are never initialized.

`./uninstall.sh` / `./uninstall.ps1` or `dots files uninstall` restores installer-owned targets to their original state, preserves user drift and retains the checkout and recovery records. Both workflows support preview, unattended approval, JSON and the existing color/progress controls. The native PowerShell frontend now routes file, Git, environment, theme and Anodize commands without Bash, with app-specific Windows destinations and native completion. Windows runtime and desktop acceptance remain pending; see [native PowerShell](docs/powershell.md) for requirements and limits. See [installation and recovery](docs/installation.md) for requirements, options and platform limits.

## Tmux keybinding reference

`dots menu tmux keys` (or `dots-menu-tmux-keys`) shows described live tmux bindings, including defaults and plugins, grouped by key table with colorized keys and a prefix legend. Compact rows keep each key beside its description, including in narrow popups. The optional `less` pager provides `/` search, `n` next match, and `q` to close; bindings are never executed. Use `--print` to bypass paging. Redirected output defaults to plain text; the standard Dots color controls apply.

The repository tmux config uses:

```tmux
bind -N "Show Tmux keybindings" ? display-popup -E -w 85% -h 85% -T "#[fg=yellow,bold]󰌆#[default]" "dots-menu-tmux-keys"
```

Popup borders use the selected Dots theme’s `lighter_background` on `background`. The keybindings popup retains its bold yellow icon title from the terminal palette. All popups use the selected Dots theme’s `background` and `foreground`, with terminal defaults before a theme is published; explicit per-popup styles can override these colors. Keep the repository `bin` directory on tmux's PATH. This requires a running tmux server with `list-keys -F` and `q|a` formats (verified on Termux with tmux 3.7c); unsupported versions report an error. No server is started or reloaded. Without `less`, the command warns and prints instead. See the [command reference](docs/commands.md#tmux-keybinding-reference).

## Tmux status and sessions

On Termux, tmux has two status rows at the top. The upper row starts with a bold 12-hour clock without a leading zero or AM/PM suffix (for example, `6:30`). The right side shows battery. Each attached tmux client highlights its own Termux session. Numbers follow `androidots/bin/termux-sessions` creation order and may change when sessions close; they are informational, not tab-switch buttons. The lower row keeps Termux numbers in order and joins the current number and optional tmux session name into one badge: for example, ` 1:dots  1  2:shell  2 ` when Termux 1 is current. Windows matching the full tmux session name exactly (case-sensitive) show only their number; other windows show `number:name`. Each badge/window owns one leading and one trailing space, including when the project name is hidden. Later numbers follow the windows immediately; COPY/PREFIX/ZOOM indicators remain on the right, using bold `darker_background` text on an `accent` background, with one colored space on each side of every active label. Colored blocks and spacing separate groups, without literal brackets or dividers. Outside Termux, the existing single tmux row is unchanged and has no Termux numbers.

Both rows use the current Dots `background`/`foreground` colors. The clock uses bold daylight-dependent text on `dark_background`. Inactive Termux numbers use bold `hint` on the row background; the joined current number/project badge uses bold `darker_background` on `hint`. Current windows use bold `info` on `selection`, without underlining; other windows use `light_foreground` on `dark_background`. The active pane border uses `selection`. The battery adapter calls `~/repos/battery/battery`, retaining its percentage colors and charging icons; a Nerd Font is needed for the icon. Battery has one space between its icon and percentage, with padding after the percentage to keep its width stable. The main tmux configuration owns the layout; generated themes supply colors. See [tmux theme integration](docs/themes.md#tmux).

The Termux upper row has battery and a daylight-colored clock; Wi-Fi/data and all other device-status indicators are disabled. The clock uses theme yellow during daylight, blue at night and the default foreground when wttr astronomy is unavailable. Background weather refresh uses a configured default or cached city, never Android location acquisition. No weather widget is enabled. See [weather and clock activation](docs/wttr.md#termux-upper-row); the live server is not reloaded automatically.

The standalone [`wttr`](docs/wttr.md) command supports current weather, up to three forecast days, three-hourly rows, JSON/scalar queries and customizable widgets. It uses wttr.in j1 JSON and the city from existing `termux-geo` on Termux. Explicit input wins over configured `default_location`, which wins over auto-location. Stock requests such as `wttr m2T`, `wttr format=3`, `wttr moon` and `wttr :help` pass through native curl with unchanged output. The created [`config/wttr/config.toml`](config/wttr/config.toml) defaults to Fahrenheit, an unset default location and Nerd Font weather icons. It hides the attribution row, defines editable temperature bands and per-condition icon colors that follow the current Dots theme by default, and defaults widgets to ANSI-auto coloring. Colors also accept literal hex or ANSI 256-color indices. Current/midday rows use aligned labels and one space between each icon and condition. Forecast conditions include icons; Zsh/FZF-tab stock completions show descriptions. Run `wttr --help`, `wttr --location London --days 2`, or `wttr --widget`. Native Windows uses `bin/wttr.ps1` with the same shared Python 3.11+ controller. `wttr completion --all --install` explicitly installs Bash/Zsh/Fish/PowerShell completions with a backup transaction; it does not edit profiles.

In Bash and Zsh, plain `t` uses the current Git repository/worktree's directory name—even from a subdirectory—so running it in this repo opens **dots**. Missing automatically named sessions start at the repository root. Outside Git repositories (or without Git), it defaults to **Work** in the current directory. `t project` explicitly opens **project**, creating it in the current directory if needed. Existing sessions are reused; inside tmux, the function switches rather than nesting. Quote names containing spaces. See [shared shell commands](docs/shared-shells.md#commands-and-compatibility).

New Termux tabs using the Dots Bash/Zsh configuration automatically enter their own default tmux session. Both status rows remain visible, but the default session's name badge is hidden; project sessions selected with `t` keep their badges. Exiting the final pane with `exit` or `q` closes the automatically started outer shell without switching to another tmux session. Detaching returns to a plain shell. Run `~/dots/androidots/bin/termux-bar` to reattach that tab's default session. Set `DOTS_TERMUX_AUTOSTART=0` before shell initialization to opt out. Fish, SSH, child shells and noninteractive commands do not autostart tmux. See [startup details](docs/shell-init.md#termux-tmux-startup).

Open a new Termux tab to use automatic startup. In an existing tmux server, **prefix + q** reloads the status configuration; changing source files does not reload that server automatically.

## Shell initialization

Bash and Zsh now share their [interactive functions and aliases](docs/shared-shells.md). Bash uses Readline vi mode, the same Starship configuration, FZF/Gum theme colors and supported native tool integrations. `ff` is the shared FZF picker; Bash's former filename search is `findfiles`. Zsh-only editor plugins remain native.

Bash and Zsh also share the sourceable [`bin/lib/common.sh` helpers](docs/shell-utils.md) for PATH edits, optional file loading, checks, messages, formatting, spinners and explicit color-array construction. The Dots theme adapter owns named color arrays and resets; human output obtains styles lazily from the shared renderer. These helpers use builtins for path and case operations, preserve source failures, and need no optional display tools during startup.

**Implemented.** Load Dots integration in Bash or Zsh with:

```sh
eval "$(dots init)"
```

The repository startup files resolve their actual location through symlinks and load the adjacent native loader, so `dots` need not already be on PATH. Moving the complete checkout and updating its links is sufficient; inherited Dots path variables are replaced with paths from that checkout. Shared setup adds existing `DOTBIN` and `DOTSCRIPTS` directories to PATH. Fish, PowerShell, Nushell and Xonsh have native adapters; linked Nushell configs need no generated hook, and PowerShell initialization needs no Bash. See [shell initialization](docs/shell-init.md) for setup, config.env settings, reload behavior and platform limits. No home-directory links or packages are installed by this command.

PowerShell Core and Desktop share a Starship profile with their own terminal integration, Vi keys and native Tab completion; Alt+F loads fuzzy completion on demand. Blastoff in Core lists repository themes. Other runtime managers and extra modules remain [explicit session opt-ins](docs/shell-init.md#powershell-profile).

Dots-specific settings and runtime variables now belong to `lib/dots/shell/`.
Edit `${XDG_CONFIG_HOME:-$HOME/.config}/dots/config.env`, then reload your shell
or initialize again. `dots init` loads only Dots integration; repository startup
files separately load personal preferences. `dots env` groups the current theme,
settings and paths into a readable terminal view with colored labels and value
sources. `dots env NAME` remains a plain scalar and `dots env --json` returns data.
See [settings and native variable examples](docs/shell-environment.md).
The old env files, repository theme-selection markers and `themes/bin` wrappers
have been removed. Use `dots theme current` instead of `current_theme`; set the
default through `DOTS_THEME_DEFAULT` in config.env.

## Shared Themes

The Omarchy-style theme tree has 33 flat variants under `themes/`, plus the dynamic
`pywal16-current` selection, with shared templates in `default/themed/`. The active generated files live at
`~/.local/state/dots/current/theme/` (XDG_STATE_HOME is respected).

```bash
dots theme list
dots theme show nord
dots theme set catppuccin-mocha --dry-run
dots theme set catppuccin-mocha
dots theme refresh
theme list                         # Equivalent standalone entry point
catppuccin mocha blue hex           # Native palette query
catppuccin mocha set                # Explicit activation
dots theme bg next                 # Explicit wallpaper change
```

The Yazi configuration uses the local [dots.yazi plugin](config/yazi/plugins/dots.yazi/README.md), combining the Dotline header/status renderer, Git indicators, saved projects, folder rules, and pane toggles. File panes use inherited `LS_COLORS` styles, including backgrounds and text attributes; the `hover` header component defaults to the symlink’s own style before the arrow and the target basename’s actual style after it, with a separately styled target directory, with independent style sources, color/attribute overrides, and visibility options for each part. Its repository component shows the Git working tree folder name before branch details and hides outside repositories. Optional `git-it` adds a remote host icon and a configurable color for repositories matching its configured owners; the personal config uses green for owned repositories and blue otherwise.

The personal Yazi configuration uses square section edges and a status-line mode indicator: `N` for normal, `V` for visual selection, and `U` for unsetting selections.

The shared palette supplies Bash, Zsh, Neovim, Termux, Kitty, tmux, btop, bat, Yazi, Codex/Codex-Termux, Pi, FZF, Gum, Vivid and Fast Syntax Highlighting.
Bash/Zsh color arrays such as `${blue[hex]}` and `${hint[esc]}` follow the current Dots theme, including semantic roles and native color names. Global `$rst` and `$RST` reset terminal colors and text attributes. Fixed Catppuccin flavor arrays remain available for compatibility; see the [shell color API](docs/themes.md#shell-and-neovim-behavior).
The [mdcat configuration](config/mdcat/config.toml) uses automatic dark/light detection and ANSI colors, following the terminal palette when the Dots theme is applied there. Code-block highlighting uses mdcat's existing `BAT_THEME` integration.
The FZF template supplies published shell colors; Bash and Zsh pick them up at the next
prompt after `dots theme refresh`, preserving FZF layout and key bindings. Gum
colors render as `gum_env.sh` and load automatically in interactive Bash/Zsh,
without Lua or Hilbish. Both shells refresh them with published theme changes; see the
[loading instructions](docs/themes.md). Fzf-tab file colors now follow the current
`LS_COLORS` at completion time; reload Zsh once to load this fix.
Vivid and Fast Syntax Highlighting use generated **dots** themes, keeping file kinds
and shell syntax on the same palette. Run `dots theme refresh`, then open a new
shell or reload once; later theme changes follow automatically in Bash/Zsh.
FSH path separators inherit the surrounding file or directory color and attributes.
FSH saves the last good Dots theme for startup, so both `fast-theme --show` lines
report `dots`.
See [Vivid and FSH setup](docs/themes.md#vivid-and-fast-syntax-highlighting) for
connectors, optional-tool fallbacks and overrides.
Pi uses `default/themed/pi.json.tpl`: with `~/.pi/agent/themes` present, run
`dots theme refresh`, then `/reload` in Pi and select **dots** in `/settings` → **Theme**.
Subsequent publications hot-reload that theme. See [Pi setup](docs/themes.md#pi)
for custom agent directories and connector backups.
Codex and Codex-Termux use the same generated syntax theme: create
`${CODEX_HOME:-$HOME/.codex}/themes`, run `dots theme refresh`, and select **dots**
in Codex’s `/theme` picker. New sessions use the latest published colors; see
[Codex setup](docs/themes.md#codex-and-codex-termux).
`dots theme switcher` offers fullscreen FZF selection with a live color-palette
preview below the list, styled with the current theme's published FZF colors,
then Back/Apply/Cancel review (using Gum when available).
Without FZF, selection falls back to Gum or a plain menu. Gum is the preferred optional
tool for suitable new interactive workflows; see the [presentation convention](docs/presentation.md#optional-gum-interactions).
File operations and Anodize also offer **Cancel / Apply**, and Git publishing
uses **Cancel / Publish**, with Cancel selected by default. Existing text prompts
remain available without Gum or suitable terminals. `--yes`, `--dry-run` and JSON
keep their existing behavior.
Bat, Yazi and Codex share the syntax rules in `default/themed/bat.tmTheme.tpl`, including
language-specific scopes and palette-based comments, selections, and diff colors.
Selection journals and backs up fixed application theme connectors. Bash and Zsh refresh
at the next prompt; Neovim uses the local Anodize.nvim plugin and refreshes on state changes, focus or `:DotsThemeReload`. Native palette
Family palette APIs such as `catppuccin` remain available; current queries use `theme color` and `theme current`. Dots generates commands for all theme families and standalone themes; a flavor alone previews its native palette. Optional `palette.toml` and usage-only `logo.txt` files are supported. Run `dots theme refresh --commands-only` to rebuild shortcuts without activating a theme. The equivalent `theme` and `dots theme` commands inspect and change the current theme; `dots themes` manages the collection; see the
[plural-command migration table](docs/themes.md#migration-from-plural-commands) for script updates. The local editor plugin defaults to `~/repos/Anodize.nvim` (override with `ANODIZE_NVIM_DIR`); generic imported themes need no downloaded Lua. Git theme installation,
updates, template overrides and wallpaper adapters are described in
[Shared themes](docs/themes.md). Wallpaper changes are always explicit.
`dots theme bg switcher` shows filenames without extensions in fullscreen FZF,
with the prompt and list at the top and a
bottom image preview occupying 70% of the height when optional Chafa is installed.

Theme and file commands now have colored terminal views: palette swatches, active
theme markers, file statuses, and paths that wrap on narrow screens. Group commands
show their available subcommands. Use `dots --color=always theme show nord` to force
color, or `dots --color=never --icons=never files list` for plain styling. Automatic
color respects `NO_COLOR`; JSON, path queries, initialization and completion remain
usable by scripts. Piped lists keep their plain format unless decoration is forced.

The [presentation contract](docs/presentation.md) makes this cohesive style a requirement for new and changed first-party human views, including help, empty results and failures. Future commands must use the same visual language while respecting plain-output preferences and script interfaces; this is a planning requirement, not a claim that every existing tool has been restyled.

## Anodize palette authoring

Anodize help, human results, diagnostics, interactive screens and completion previews use the same responsive logo selection from your bundled braille artwork. Layouts fit the terminal or preview width; short FZF panes keep the supplied artwork and scroll vertically. Plain terminals retain the ASCII fallback. Try `dots anodize --logo=auto --help` for detected graphics or `--logo=chafa` for optional Chafa character art; set `ANODIZE_LOGO` to keep a preference. JSON, raw configuration, exports and completions stay undecorated. See [logo controls and fallbacks](docs/anodize.md#terminal-logo).

New Anodize themes save to `~/.config/dots/themes/ID/` by default, including a copy of source images under `backgrounds/`. Use `--builtin` on create/import to save into repository themes, or `anodize promote ID` to move a user theme there. `anodize --interactive` offers guided FZF selection and editing; theme and mode previews include syntax samples on the candidate background. See [interactive authoring](docs/anodize.md#interactive-authoring-and-previews).

Anodize provides a reusable Go color engine and CLI for creating themes from images, seed colors, existing themes and local imports. Build the private engine explicitly, then preview a new theme:

```sh
python3 -B tools/verify_anodize.py build
bin/anodize create dusk --color '#725ac1' --dry-run
bin/anodize create dusk --color '#725ac1' --yes
bin/anodize preview dusk
bin/anodize apply dusk --dry-run
```

`dots anodize` provides the same routes. Run `anodize --help` for commands and examples, or `anodize create --help` for source and save options. Bash, Zsh and Fish completion is available through `anodize completion SHELL`; read the manual with `man -l man/anodize.1` from the checkout. See [shell setup](docs/anodize.md#shell-completion-and-manual) for loading completions and installing the manual. Saves use recoverable file transactions and do not activate themes. Apply separately with `--yes` after reviewing its preview. See [Anodize](docs/anodize.md) for image extraction, repeatable adjustments, imports/exports, dependencies and limitations. Dots Neovim integration uses the separate local Anodize.nvim checkout. Android APK and TUI remain follow-up work. This is a scoped exception to the general Go pause.

## Files and Configuration Layout

`config/` is canonical in Dots, Androidots and Windots. Temporary `configs -> config`
aliases remain for compatibility. The Neovim submodule now lives at `config/nvim`.

```bash
dots files sources
dots files browse
dots files list --sort app
dots files check --dry-run              # Preview missing-source catalog cleanup
dots files check                        # Review each entry, then confirm removals
dots files stash dots:example --dry-run # Preview disabling and unlinking
dots files edit dots:example            # Review source/target mapping changes
dots files list --repo androidots --platform termux
dots files locate kitty
dots files show dots:kitty
dots files list --all-platforms --json
```

`dots files browse` provides a searchable FZF/Gum/plain-menu view of tracked
configs. Inspect paths and status, toggle retained backups for the session, and
review Link or Stop managing before Apply. The picker starts with metadata;
Alt-C explicitly requests a bounded content preview. See the [browser guide](docs/files.md#interactive-tracked-config-browser).

`dots files check` reviews missing source paths and removes approved catalog
entries only; target files and links remain untouched. Use `--yes` to approve all
eligible entries, `--dry-run` to preview, and list's filters to narrow the check.
Broken source symlinks are retained for repair. Results include a journaled undo
command. See [missing-source checks](docs/files.md#check-missing-sources).

`dots files stash ID` keeps the source and catalog entry, disables installation
and removes its matching link; `--restore` enables and relinks it. `dots files edit`
edits or creates mappings, with `--apply` to reconcile live links. Both support
interactive review, `--yes`, `--dry-run`, JSON and journaled undo. See
[stash and edit](docs/files.md#stash-and-edit-mappings).

The first files slice locates and classifies sources and destinations, and tracks
intent in each repository's `.dots/files.json`. Androidots contributes Termux
resources explicitly; unavailable/private sources are not initialized. `track`
changes catalog metadata only. Bounded file operations use links by default;
add/link/remove, adoption, undo and backups are available below. Source-content editing and general
profile installation remain future work. See the [catalog reference](docs/files.md)
for tracking, filters, JSON and ownership rules. Python 3.9+ is required for this
POSIX implementation; discovery additionally uses Git.

### Interactive file selection

Run `dots files add`, `link`, `stash`, `edit`, `remove` or `show` without operands
in a terminal to select configurations. FZF provides live details, optional content
previews and multi-selection; Gum and numbered menus remain available fallbacks.
Use `dots files link --pick --dry-run` to select and preview, or
`dots files add --pick ~/.config/nvim` to choose files inside a registered location.
See [file pickers](docs/files.md#interactive-file-pickers) for keys and safety details.


## Git and Managed Configurations

`dots git` manages the dots repository and registered nested submodules. Status
uses local tracking information; publication previews staged changes and pushes
children before parents. `publish --all` includes tracked edits/deletions and
non-ignored new files, including edits to files already tracked beneath ignored
directories. Synchronization keeps recorded child commits unless
explicitly asked to advance them. Configure allowed publication owners using the
[Git guide](docs/git.md).

```bash
dots git status
dots git publish --dry-run
dots git sync --dry-run
dots files locations
dots files discover --system
dots files discover --system --verbose
dots files add ~/.config/example --dry-run
dots files add ~/.config/example --backup
```

File adoption copies and verifies configs into their owning repository, then links
individual files at their original locations. Search locations are versioned;
Termux-specific mappings belong to Androidots. `files link ID` installs a known
resource; `files remove ID` (or `rm`) stops managing it while preserving a regular
local config and the repository source. Commands preview before confirmation;
`--yes` is explicit unattended approval. Nothing automatically stages or publishes
imports.

Add `-v`/`--verbose` to file-changing commands and setup (`./install.sh -v` or
`dots files install -v`) for live backup, copy and source -> destination link
rows. Theme application supports it too: `dots theme set nord -v`,
`dots theme refresh -v`, and `dots theme switcher -v`. Details retain progress,
file-type/MIME colors and icons; unchanged/skipped reasons and rollback remain
visible. Defaults stay unchanged, dry runs describe plans, and JSON suppresses
the added trace. See [verbose output](docs/presentation.md#verbose-operations).


System discovery defaults to compact config-directory groups with colored counts
and paths. Use `--verbose` for individual files and source mappings, or `--all` to
include managed/excluded entries. `--json` always retains the full observed list.
Known caches, session data and generated preview trees are excluded from adoption.

Retained backups default off. Use `--backup` or the machine-local preference;
mandatory temporary rollback protection remains active either way. `files backups
list|show|restore`, `files history`, `files undo`, and `files recover` expose
snapshots and transaction recovery. Backups live in dots' XDG state, separately
from the unchanged `bak` utility. Read the [file guide](docs/files.md) for exact
semantics, restrictions, IDs and recovery examples.

## Zsh Configuration

Use `palette` to preview all 256 terminal foreground colors, or `palette_bg` for background colors in the same numbered column layout.

Use `mkcd <directory>` in either configured Bash or Zsh shell to enter an existing directory or create missing parents and enter the new directory. It requires exactly one nonempty path and refuses existing files or broken symlinks. The shared function sources [scripts/mkcd](scripts/mkcd) so the directory change affects your current shell.

The existing [Zsh configuration](shells/zsh/README.md) now uses explicit modules, one completion initialization, immediate tool integrations, and generated-data caches. It preserves the Termux workflow; native WSL/Linux and MSYS2 verification remain pending. See the guide for module registration, reloads, and isolated checks.

Startup automatically repairs completion dumps containing unquoted names such as `_uu-[`, preventing the resulting startup and Tab-completion errors.

[Deja](shells/zsh/README.md#deja-suggestions) is the default suggestion engine. On Linux/WSL x86-64 and ARM64, Zinit automatically installs a missing executable from upstream releases and reuses it in later shells. Open a fresh shell to activate it, or use `DOTS_ZSH_SUGGESTIONS=autosuggestions zsh` for optional `zsh-autosuggestions`. An unavailable or unusable Deja executable falls back to autosuggestions; the two engines never load together through this selector. Tab stays with FZF-tab. History import is manual, and Deja keeps its own plaintext local database and background daemon.

## Optional Neovim Configuration

The public [Neovim configuration repository](https://github.com/5nik7/nvim) is available as a Git submodule at `config/nvim`. From the `dots` repository root, initialize only this source:

```bash
git submodule update --init -- config/nvim
```

`dots` records an exact configuration commit. The submodule's `main` branch is used only when explicitly requesting a remote update. With a clean submodule checkout and any local commits safely preserved, review an update with:

```bash
git submodule update --remote --checkout -- config/nvim
git diff --submodule=log -- config/nvim
```

After review, stage `config/nvim` and commit its new reference in `dots`. Configuration edits belong in the Neovim repository; publish those commits before publishing a `dots` reference to them. Keep submodule operations scoped to this path so other optional and private sources remain opt-in.

Initialization only retrieves source; it does not activate the configuration, install plugins or packages, or change the existing Neovim configuration. Follow the submodule's [installation instructions](https://github.com/5nik7/nvim#install-as-the-default-config) when deliberately activating it, preserving the existing config first. Keep platform-specific plugin, data, and cache directories separate. This source addition does not establish new `dots` platform or installation support.

## Try the Permanent Development Core

With Go 1.27.1 and Python 3 already installed, run from the existing checkout:

```bash
DOTS_DEV_BIN="$(python3 -B tools/verify_core.py build)"
"$DOTS_DEV_BIN" --help
"$DOTS_DEV_BIN" --version
"$DOTS_DEV_BIN" doctor
"$DOTS_DEV_BIN" doctor --json
"$DOTS_DEV_BIN" commands
"$DOTS_DEV_BIN" commands --check
"$DOTS_DEV_BIN" commands --json
```

The verifier creates test-owned build/config/cache/output roots, disables Go downloads and telemetry, and prints only the resulting binary path on stdout. Nothing is installed or added to PATH. The artifact includes `bin/dots`, the optional public logo and sanitized build evidence; it may be removed with temporary storage. A configured `$DOTS` still controls optional-logo lookup. The active `bin/dots` and its directory flags are unchanged.

PowerShell uses `python -B tools/verify_core.py build` to obtain the separate `.exe` path:

```powershell
$dev = python -B tools/verify_core.py build
if ($LASTEXITCODE -ne 0) { throw "Development build failed" }
& $dev --help
& $dev --version
& $dev doctor --json
& $dev commands --json
```

Run `python3 -B tools/verify_core.py check` for isolated validation and `python3 -B tools/verify_core.py bench` for warm startup and registry measurements (`python` on Windows). Checks additionally need installed gofmt/readelf or LLVM, plus Zsh on Termux/Linux; benchmarks need hyperfine. Missing tools are reported without installation. See [testing](docs/testing.md#permanent-core-verification) and [the first-slice results](plans/phase-2-command-center.md). The development extension mechanism is opt-in per invocation: repeat prefix `--command-dir <absolute-trusted-directory>` to select roots. Each executable requires a strict JSON sidecar; use `commands`, `commands --json`, `commands --check`, or `<route> --help` for static inspection without execution. See the [exact protocol and example metadata](docs/commands.md#development-external-protocol). `commands --json` emits the [schema-1 catalog](docs/commands.md#machine-readable-command-catalog), including hidden and unavailable definitions with explicit attributes; no roots yields built-ins only. It cannot be combined with `--check`. No real dotfile extension ships. Unix executes native files; Windows supports `.exe` only in local case-insensitive NTFS roots. Selecting a root trusts its code; this is not a sandbox or publisher authentication. WSL execution, other completion renderers, installation, manifests, transactions, bootstrap and releases remain deferred.

### Disposable Zsh completion demo

The permanent Go development binary supports its own static `completion zsh` generator, separate from the live Bash framework’s on-demand three-shell adapters. The Go generator prints a static script and installs nothing. With an already built development binary in `DOTS_DEV_BIN` (from the build example above), run the following in a separate disposable Zsh process. `mktemp` creates only a new demo directory; retain or remove that exact directory after inspection. The demo uses temporary HOME and ZDOTDIR directories and does not edit live startup files. Zsh still reads its system zshenv, if present.

```bash
demo_root="$(mktemp -d "${TMPDIR:-/tmp}/dots-zsh-demo.XXXXXXXX")"
mkdir "$demo_root/bin"
ln -s "$DOTS_DEV_BIN" "$demo_root/bin/dots"
"$DOTS_DEV_BIN" completion zsh > "$demo_root/completion.zsh"
env -i HOME="$demo_root" ZDOTDIR="$demo_root" XDG_CONFIG_HOME="$demo_root" \
  XDG_DATA_HOME="$demo_root" XDG_STATE_HOME="$demo_root" XDG_CACHE_HOME="$demo_root" \
  TMPDIR="$demo_root" TERM=xterm PATH="$demo_root/bin" \
  "$(command -v zsh)" -f
```

Inside that disposable shell, initialize its completion system without a dump file and source the generated script:

```zsh
autoload -Uz compinit
compinit -i -D
source "$HOME/completion.zsh"
```

Type `dots do` and press Tab to complete `doctor`. The disposable PATH resolves `dots` to the development binary; `dots --version` demonstrates that binding. Exit when finished.

Routes and represented global spellings are completed; command flags and argument values are not inferred. To include external routes, generate with explicit prefix `--command-dir` roots and use that identical ordered root spelling in the completed invocation. The script performs no runtime discovery or extension execution. See the [completion contract](docs/commands.md#static-zsh-completion). Native Windows generation is distinct from Termux/Linux Zsh runtime verification.


## Try the Portability Experiment

**Implemented, experimental:** help, version output, and read-only platform diagnostics, verified natively on Termux Android/ARM64 and on Linux/AMD64 and Windows/AMD64 in GitHub Actions. The live `dots` command and dotfiles are unchanged. Linux and Windows CI results establish execution on the recorded runners; bounded distribution bundles have also been packaged, verified, extracted, and executed natively on all three targets. The minimal bundle direction and publisher-authentication requirement are accepted, but permanent release tooling, the signing mechanism, and production support remain pending.

From the repository root, using the verified Go 1.27.1 toolchain and Python 3 without optimization (`PYTHONOPTIMIZE` unset or `0`; no `-O`/`-OO`). The verifier rejects optimized Python before invoking tools or creating build artifacts:

```bash
DOTS_SPIKE_BIN="$(python3 experiments/go-portability/tools/verify.py build)"
DOTS="$PWD" "$DOTS_SPIKE_BIN" --help
"$DOTS_SPIKE_BIN" --version
"$DOTS_SPIKE_BIN" doctor
"$DOTS_SPIKE_BIN" doctor --json
```

The build command prints the executable path on stdout and progress on stderr. It retains the binary, a public logo copy, and `evidence.json` in a unique directory under the temporary directory. Tool caches and build work are disposable; nothing is installed or added to `PATH`, and no dependencies are downloaded. Temporary artifacts may be removed by the system; rebuild when needed.

The preserved experimental help still says “Go remains provisional”; that historical banner does not reflect the later adoption decision. It is unchanged to preserve the verified executable and evidence.

Help loads the optional `logo.txt` from `$DOTS` or, when unset, beside the executable's parent `bin/` directory. Missing or unusable logos are omitted, and valid file symlinks are supported. Version and diagnostic output contain no logo. Diagnostics reports candidate paths and `not_probed` filesystem capabilities; it does not create files, load configuration contents, or apply changes.

Run focused checks or startup measurements with:

```bash
python3 experiments/go-portability/tools/verify.py check
python3 experiments/go-portability/tools/verify.py bench
```

Checks additionally use installed `gofmt` and `readelf` on Unix or `llvm-readobj` on Windows; measurements use installed `hyperfine`. Missing prerequisites are reported without installation. See the [experiment plan and results](plans/phase-1-portability.md), [testing instructions](docs/testing.md), and [platform evidence](docs/platforms.md). Linux/Windows compilation does not establish that those artifacts run on their target platforms.

The Windows harness accepts native Windows/AMD64. With Go and Python already installed, PowerShell can build and try the separate executable:

```powershell
$spike = python experiments/go-portability/tools/verify.py build
if ($LASTEXITCODE -ne 0) { throw "Experimental build failed" }
& $spike --help
& $spike --version
& $spike doctor --json
python experiments/go-portability/tools/verify.py check
```

Windows diagnostics explicitly leave known-folder resolution unimplemented and filesystem capabilities unprobed. Link tests report actual availability without changing security policy; copy checks run independently.

The experimental distribution check builds, packages, verifies, extracts, and runs the native executable in disposable directories:

```bash
python3 experiments/go-portability/tools/verify.py dist
```

In PowerShell use `python experiments/go-portability/tools/verify.py dist`. This additionally needs installed Git. It uses the **committed** public logo, preserving and excluding any local logo edit. Go source inputs must match the recorded commit. Bundles contain the executable under `bin/`, the logo, and `bundle.json`; an external `SHA256SUMS` covers the `.tar.gz` (Termux/Linux) or `.zip` (Windows). The printed executable path belongs to the retained temporary artifact; bundles, checksums, and CLI logs are under its sibling `distribution/` directory. Nothing is installed. Checksums establish agreement with the supplied manifest, not publisher authentication. See the [distribution guarantees and limitations](docs/testing.md#experimental-distribution-check).

## Intended Experience

The proposed CLI uses discoverable command groups:

```text
dots status
dots spec
dots plan
dots apply
dots files list
dots links check
dots example apply <name>
```

External commands named `dots-*` with matching sidecars can be available through explicitly selected trusted roots. For example, `dots-example-apply` can provide `dots example apply` without adding routing code to the dispatcher.

These examples describe the intended interface and are not yet implemented.

## Design Priorities

1. Protect existing files and preserve a reliable path back.
2. Keep command dispatch, planning, and shell startup fast.
3. Show a complete plan before changing a machine.
4. Use symbolic links by default and copy only when explicitly selected.
5. Compose shared files with platform-, profile-, and host-specific modules.
6. Keep private sources and large optional assets out of the minimum bootstrap path.
7. Keep behavior, tests, help, completions, and documentation synchronized.

## Documentation

- [`AGENTS.md`](AGENTS.md) — authoritative instructions for agents and contributors.
- [`docs/principles.md`](docs/principles.md) — product and engineering priorities.
- [`docs/architecture.md`](docs/architecture.md) — proposed system boundaries and repository structure.
- [`docs/commands.md`](docs/commands.md) — proposed command family and extension model.
- [`docs/specification.md`](docs/specification.md) — draft modules, profiles, hosts, and manifests.
- [`docs/safety.md`](docs/safety.md) — planning, transactions, backups, rollback, and undo.
- [`docs/platforms.md`](docs/platforms.md) — Termux, Linux, WSL, and Windows model.
- [`docs/testing.md`](docs/testing.md) — test isolation, failure cases, and performance measurement.
- [`docs/current-repository.md`](docs/current-repository.md) — baseline inventory and migration constraints.
- [`plans/roadmap.md`](plans/roadmap.md) — phased implementation roadmap.
- [`plans/termux-mvp.md`](plans/termux-mvp.md) — first end-to-end implementation target.

The complete documentation index is in [`docs/README.md`](docs/README.md).

## Contributing With an Agent

Agents must read [`AGENTS.md`](AGENTS.md) before changing the project and then read the task-specific guide under [`agents/guides/`](agents/guides/). A behavior change is incomplete until the corresponding tests, plans, and source-of-truth documentation are updated in the same change.

## Migration Approach

The current dotfiles remain available for ordinary maintenance while migration is paused. When resumed, migration will proceed one module at a time, beginning with a small Termux profile. Existing submodules, platform repositories, large assets, and actively used scripts will not be removed or reorganized without a focused plan and recovery path.

## Development Worktrees

Contributors work directly in the existing checkout on `main` by default. Task-relevant edits are allowed throughout the repository, with unrelated changes preserved. Separate branches and worktrees are optional; ordinary maintenance requires no worktree setup or cleanup. The [worktree guide](agents/guides/worktrees.md) retains procedures for deliberate worktree use and guarded cleanup with `tools/worktree_lifecycle.py`. Git history supports recovery of committed edits; uncommitted work and external machine effects need separate care.

## Local theme plugins

`dots theme plugins` manages explicitly enabled integrations shared by ordinary
Dots themes and Anodize application. GTK 3, Qt6ct and Starship/Blastoff are bundled and disabled by
default; trusted custom Bash hooks can be enabled separately.

```bash
dots theme plugins list
dots theme plugins doctor
dots theme plugins enable gtk
dots theme plugins run gtk
dots theme plugins disable gtk
```

Enable/disable only persist selection. Successful theme publication runs enabled
plugins, and explicit refresh retries them. Disabling keeps existing output.
Bundled app writes use retained backups and the file transaction engine; arbitrary
custom hook effects are not sandboxed or automatically reversible. See the
[plugin guide](docs/theme-plugins.md) for Starship/Blastoff, Qt6ct, authoring, palette variables,
recovery, JSON output, and desktop limitations. Downloaded themes remain data-only.

## File colors and live Yazi themes

`dots theme show catppuccin-mocha` previews all resolved colors and file styles
in a terminal. `theme colors` shows the published colors using the same grouped
tables and swatches; `theme colors --theme catppuccin-mocha` previews saved
configuration. File type, MIME and extension listings use readable style tables,
including a plain layout when color is disabled.

`theme colors git` lists the shared repository (`repo`, magenta; `repo_owned`, yellow), branch and Git status styles used by `dots git status`, `sync` and `publish`. `theme colors set git untracked --fg cyan --apply` customizes a role and refreshes the current selection; filenames retain their type/MIME colors. Yazi follows these roles through live `dots.colors.git.repo` references and shared Git indicator styles. See [Git styles](docs/file-colors.md#git-styles) for defaults and exports.

`theme colors type dir hex` queries a directory color. Use
`theme colors set type dir --fg blue` to save a shared rule and `theme refresh`
to publish it; `--theme ID` stores a theme-specific override and `--apply` publishes
after saving. Full styles, MIME/suffix queries, match explanations, LS_COLORS
inspection, and JSON/Lua exports are described in [file colors](docs/file-colors.md).
Family help uses its own palette with explicit foreground/background. Header
logos retain embedded ANSI colors; logos without colors receive theme coloring.
`tokyonight day --help --color=none` strips all styling and prints plain usage.

The bundled dots.yazi plugin follows published palettes while running, including
file styles and mode colors. The standalone plugin's documented theme callback
accepts `colors.red`, `colors.blue`, `colors.type.dir`, and complete style tables.
Repository-local Codex workflows live in [.codex](.codex/README.md).

Human CLI views share Git-style semantic colors, readable plain output and delayed progress. File/directory fields use published Dots type, extension and MIME styles with optional icons; theme previews and Anodize branding retain their custom appearance. Use the existing `--color=never`, `--icons=never` and `DOTS_PROGRESS=never` controls independently. See [presentation](docs/presentation.md#filesystem-resources).

The [Git configuration](config/git/README.md) follows shared Dots colors in native Git and Delta through a generated theme include. Git's Delta pager/filter also uses the generated Dots syntax cache without replacing the normal bat cache. Managed Git installation/linking selects the ignored platform overlay automatically; the consolidated files live in the parent Dots checkout.

Starship uses `~/.config/starship.toml`, linked to the repository config. Personal
shell startup no longer exports `STARSHIP_CONFIG`; it clears recognized legacy
Dots values while preserving explicit custom overrides. Blastoff 0.1.12 safely
updates the file behind that link. See [the configuration contract](docs/shell-environment.md#starship-configuration).

The saved [Blastoff `dots` theme](config/blastoff/themes/dots.toml) uses shared color names and Git roles while retaining the personal prompt layout. It includes styles for supported inactive Starship modules. With `dots theme plugins enable starship`, publication/refresh updates only `[palettes.dots]` in the active Starship config and saved `dots` theme. Other selected palettes are skipped; module edits and extra palette names remain intact. See [Starship integration](docs/theme-plugins.md#starship-and-blastoff-starship).

## Termux location lookup

Androidots provides `termux-geo` for device coordinates and Nominatim city/state/postal information, with Dots human output, delayed progress, JSON in pipes, scalar getters and cache-only reads. `termux-geo completion --all --install` installs static completions into Androidots-local Bash/Zsh/Fish directories recognized by personal Termux startup. See the [location command reference](androidots/docs/termux-geo.md) for dependencies, service restrictions, flags, and completion activation.
