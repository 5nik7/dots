# dots

`dots` manages dotfiles, scripts, shells, themes and checkout setup across Termux, Linux, WSL and native Windows.

The live CLI uses Bash and native PowerShell adapters with shared Python controllers for managed files, Git operations and themes. Anodize is an independent Go palette-authoring engine. See [installation](docs/installation.md) for existing-checkout setup, runtime requirements and platform limits.

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

Personal Bash, Zsh and Fish startup discovers [user-local completions](docs/shell-init.md#user-local-completion-directories) with priority over repository providers. This includes Zsh's `${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions`, Bash's user completion bases and Fish's native user directories. Start a new shell after configuration changes; Zsh's `rlcs` also refreshes local completion discovery.

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

Setup preserves existing text-file permissions and records those same permissions
for restoration, including after theme changes and reconciliation. Generated
machine-local theme links are excluded from the portable checkout.

`./uninstall.sh` / `./uninstall.ps1` or `dots files uninstall` restores installer-owned targets to their original state, preserves user drift and retains the checkout and recovery records. Both workflows support preview, unattended approval, JSON and the existing color/progress controls. The native PowerShell frontend now routes file, Git, environment, theme and Anodize commands without Bash, with app-specific Windows destinations and native completion. Windows runtime and desktop acceptance remain pending; see [native PowerShell](docs/powershell.md) for requirements and limits. See [installation and recovery](docs/installation.md) for requirements, options and platform limits.

## Keybinding browser

`dots keys` opens a compact FZF category menu with Nerd Font icons and muted counts such as `tmux · [47]`. All opens the combined reference; each nonempty app opens its bindings directly. Zero-count apps are hidden, and the selected list reuses the counted snapshot. Use `dots keys all` or `dots keys zsh --mode viins` to browse directly, `dots keys yazi --print` for the full shipped Yazi reference, `dots keys codex --print` for Codex CLI defaults and custom keys, or `dots keys apps --print` for coverage. Binding browsers show readable keys such as `Ctrl+G` in bold bright magenta, orange modes and muted metadata, descriptions and live/configured evidence. Inside tmux the browser uses `fzf --popup center,99%` with a 45% preview; outside tmux it uses ordinary FZF. Missing FZF prints a readable list. `--json` stays undecorated. Neovim's `:DotsKeys` captures effective global and buffer mappings. See [keybinding browsing](docs/keys.md).

## Dots workflow menu

`dots menu` opens a compact FZF menu with icons: `keys`, `tmux`, `files`, `git`, `theme`, `themes`, `anodize`, `debug`, `profile`, `profiles`, `wiki`, `env`. Select a family for its common workflows. Prompts show `dots:`, `dots·files:` and nested breadcrumbs such as `dots·themes·plugins:`. Escape goes back, Ctrl-C closes the menu, and F1 opens help. Workflows return to their menu with its search preserved; successful tmux session selection closes the launcher. The Git menu includes status, info, submodules, wiki, publish and sync. Both Git and Git → Wiki publish choices pass `--all` and retain the existing review and confirmation; sync previews changes and asks for confirmation. Help and reports open in a scrollable reader: arrows/Page Up/Down or mouse to scroll, `/` to search, `q` to return. Reader popups fit short reports and grow to a 90% height cap for long output. The reader displays Nerd Font symbols directly; a read-only FZF viewer is the fallback when less is unavailable. `wiki browse` also pages the selected document. Use `--query TEXT` to search or `--print`/`--json` to inspect root choices without running them. Existing file/theme/Anodize confirmations still apply. See [launcher commands](docs/commands.md#dots-workflow-menu).

Less prompts and standout highlights use theme foreground on lighter_background globally in Dots-initialized shells and popup readers. See [less colors and overrides](docs/shell-environment.md#global-less-colors) for reload behavior and platform support.

The repository tmux configuration binds Prefix m to the launcher and Prefix s to the session picker, replacing the stock mark-pane and session-tree shortcuts. These take effect when that configuration is loaded; implementation does not reload a running server. Both shortcuts target the invoking client and close quietly on Escape/Ctrl-C. Prefix ? keeps its existing keybinding browser.

## Tmux keybinding reference

`dots menu tmux keys` and `dots-menu-tmux-keys` remain compatibility entries for `dots keys tmux`. Prefix → ? invokes `dots keys --browse` through `run-shell -b`, opening the compact category menu before the binding browser. FZF owns each popup. Escape/Ctrl-C closes the shortcut quietly; genuine failures remain visible. Direct CLI cancellation still returns 130. `--print` bypasses the picker. No binding is executed and no tmux server is started or reloaded. Existing shared tmux popup styling remains available to other popups; this picker uses the published FZF theme. See [tmux compatibility](docs/keys.md#tmux-compatibility).

Key pickers show match counts inline on the right. The main/All prompt is
`󰌆 :`; a specific app uses `󰌆 APP:` and omits the repeated app name from rows.
**Alt-M** opens a compact mode chooser and preserves the binding search. A selected
mode hides its row field and appears in the prompt, such as `󰌆 zsh·viins:`.
Returning to all restores the mode column. App/mode/key columns align within
12/18/16-cell caps and shorten with `…`. Previews start at the left edge with
Keys, Action and Mode, using matching colors and no heading. `--mode` selects the initial
picker mode and remains an exact filter for print/JSON output.

The keys popup captures live Zsh bindings from its originating pane when Zsh is
at a prompt. Rows and previews show live/configured evidence; print/JSON coverage
notes explain when only the partial configuration reference is available.
Existing sessions can load the capture adapter without resetting their bindings;
see [live Zsh capture](docs/keys.md#live-zsh-bindings-from-the-tmux-shortcut).

## Tmux status and sessions

`dots menu tmux sessions` (Prefix s) opens a themed project/session browser. Projects with open sessions appear first, then inactive projects, then other sessions. It discovers Git checkouts directly under `~/repos` plus Dots; [optional project paths](docs/specification.md#session-browser-projects) add more. Enter switches the current client or creates a session for an inactive project; projects with several sessions open a submenu. **Alt-N** creates, **Alt-R** renames, **Alt-D** confirms deletion, **Alt-T** opens a new Termux tab attached to the selected session (Termux only), and **F1** lists actions. **Alt-H** opens the full shortcut reference; Escape or Alt-H returns to the same search. Escape goes back; Ctrl-C exits. Project rows use ``, with icons matching their names. Non-current project names with sessions use bold theme accent in both the list and preview; non-project session names use bold theme blue. Current names retain magenta emphasis. Empty-project names use `light_foreground`, normal-weight in the list and bold in the preview. The compact preview uses `battery · [1 session]` and `Project: 󰉋 ~/path`. Positive session totals use normal-weight theme orange for both current and non-current projects; zero stays red. The full `·  current` / `· current` marker uses bold theme `bright_green`. Window counts are green, and `N attached` is yellow when positive or muted when zero. Positive menu counts also use orange; `no session` stays muted. Managed workspaces follow their live pane projects and appear under the matching project; mixed workspaces remain separate entries. New sessions use `projectname-ID` (or `termux-ID` outside projects), without a name prompt. The preview keeps each session on one row and clips overflow at the right edge, including long names and paths. New Termux probes `termux-am`, falling back to the Termux-installed `am` when needed. `--print`, `--json` and redirected output remain read-only live-session listings. Use `--client CLIENT` when several clients share the invoking session. Native Windows reports tmux unavailability. See [session controls](docs/commands.md#tmux-session-menu).

On Termux, tmux has two status rows at the top: a bold 12-hour clock, Termux tab numbers and battery above, the current tmux session and its windows below. Termux tab numbers appear immediately after the clock when more than one tab exists, with the viewing tab highlighted. The lower row has separate server-wide tmux session numbers in creation order: only the current session is shown, and its number disappears when there is only one tmux session. Two tabs viewing the same tmux session show the same lower number. Window numbers independently appear when that session has multiple windows. Useful names remain when numbers disappear; matching singleton window names and managed default names stay hidden. For example: ` dots `, ` dots │ shell `, or ` 1 dots │ 1 │ 2 shell `. Session labels and all windows without warnings have one space on either side; warning labels have none. A `│` separates sections, and one space joins a number to its icon/name. Numbers may change when tabs or sessions close. COPY/PREFIX/ZOOM remain on the right. Outside Termux only the tmux row appears.

The current session uses bold `bright_cyan` on `selection_background`; only the project/session name is underlined, leaving its number, remote icon and spaces plain. Current window names use normal-weight `foreground` on `selection_background`, with numbers and markers in bold `bright_green` on `selection_background`. Inactive window numbers use bold theme `accent` when running Codex and bold `dark_foreground` otherwise; inactive names use `dark_foreground`, bold while Working and normal otherwise. Working windows show `•` and explicit input/approval waits show `·`: `1• shell` or `1· shell`. Inactive markers use theme `accent`, bold while Working; current markers stay bold green. With numbers hidden, the label is `• shell` or `· shell`; with names hidden too, only the marker remains. Ordinary idle/Ready states have no marker. Bell/activity/silence alerts override the whole label with bold `bright_red` on `darker_background` and brackets, such as `[2]` or `[2 shell]`, without outer spaces. Detection uses foreground processes and the Codex terminal title, refreshing with the status bar. Dividers between sections use `background` on `dark_background`. Current Termux tab numbers use bold bright cyan on `selection_background`; other tabs use bold dim cyan on `lighter_background`, without underlining. The clock, battery, pane border and COPY/PREFIX/ZOOM colors retain their existing semantic roles. Both rows use Dots palette colors, with layout owned by the main configuration and colors supplied by the generated theme. A Nerd Font is needed for the battery icon. See [tmux theme integration](docs/themes.md#tmux).

The current session can show the active pane repository's remote host icon, matching `dots.yazi`: `󰊤 dots` or `1 󰊤 dots` for GitHub, with GitLab, Bitbucket and generic Git alternatives. Hidden default names retain the icon alone or after the number. This requires optional `git-it` and a Nerd Font; no remote or unavailable metadata means no icon. Icon discovery shares the bounded asynchronous Gitmux job and does not require Gitmux itself to succeed.

The Termux upper row has battery and a daylight-colored clock; Wi-Fi/data and all other device-status indicators are disabled. The clock uses theme yellow during daylight, blue at night and the default foreground when wttr astronomy is unavailable. Background weather refresh uses a configured default or cached city, never Android location acquisition. No weather widget is enabled. See [weather and clock activation](docs/wttr.md#termux-upper-row); the live server is not reloaded automatically.

The standalone [`wttr`](docs/wttr.md) command supports current weather, up to three forecast days, three-hourly rows, JSON/scalar queries and customizable widgets. It uses wttr.in j1 JSON and the city from existing `termux-geo` on Termux. Explicit input wins over configured `default_location`, which wins over auto-location. Stock requests such as `wttr m2T`, `wttr format=3`, `wttr moon` and `wttr :help` pass through native curl with unchanged output. The created [`config/wttr/config.toml`](config/wttr/config.toml) defaults to Fahrenheit, an unset default location and Nerd Font weather icons. It hides the attribution row, defines editable temperature bands and per-condition icon colors that follow the current Dots theme by default, and defaults widgets to ANSI-auto coloring. Colors also accept literal hex or ANSI 256-color indices and text styles such as `bold bright blue`. Any number of temperature cutoffs is supported with one more style than cutoffs. Widgets accept explicit style directives such as `{icon_color}`, `{temp_color}`, `{feel_color}`, `{bold white}`, and `{reset}`. The aligned `Now` row shows icon and temperature, followed by a separate `Condition` row. Wind arrows point downwind; location, wind, sunrise, sunset, humidity and precipitation icons have configurable theme-based styles and widget/scalar fields. The location icon appears beside the city heading; humidity, wind, precipitation, sunrise and sunset icons follow their row values. Sunrise/sunset omit leading hour zeros in human output, widgets and scalar queries. `label_gap` controls the aligned row gap (three spaces by default); named `[icons]` and `[icon_colors]` entries customize detail glyphs/styles, with matching widget directives such as `{humidity_color}`. Forecast conditions include icons; Zsh/FZF-tab stock completions show descriptions. Run `wttr -h` for the theme-gradient usage banner and short/long option list, `wttr -l London -d2`, or `wttr -w`. Short aliases also include `-V` version, `-v` verbose, `-f` format, `-j` JSON, `-F` fields and `-g` get; see the weather guide for the full set. Native Windows uses `bin/wttr.ps1` with the same shared Python 3.11+ controller. `wttr completion --all --install` explicitly installs Bash/Zsh/Fish/PowerShell completions with a backup transaction; it does not edit profiles.

In Bash and Zsh, plain `t` uses the current Git repository/worktree's directory name—even from a subdirectory—so running it in this repo opens **dots**. Missing automatically named sessions start at the repository root. Outside Git repositories (or without Git), it defaults to **Work** in the current directory. `t project` explicitly opens **project**, creating it in the current directory if needed. Existing sessions are reused; inside tmux, the function switches rather than nesting. Quote names containing spaces. See [shared shell commands](docs/shared-shells.md#commands-and-compatibility).

New Termux tabs using the Dots Bash/Zsh configuration enter their own workspace, initially identified as `termux-<root-pid>-<start-ticks>`. Its ID stays fixed while its prefix follows all live pane directories: one project gives `projectname-ID`, several distinct projects give `multi-ID`, and no projects restores `termux-ID`. Git repositories/worktrees anywhere and explicitly configured project directories count; panes outside projects do not add a project. The bar shows only `projectname` or `multi`, hiding the ID and the default `termux` name. Prefix **C** creates a fresh workspace in the current pane directory and switches only that client. Manual renaming opts out of automatic naming. Closing a project’s last pane/window updates the name. The existing `t` helper keeps its explicit named-session behavior.

Exiting the final pane with `exit` or `q` closes the automatically started outer shell; detaching returns to a plain shell. Run `~/dots/profiles/termux/bin/termux-bar` to reattach the tab’s original workspace, even after it has been renamed. `DOTS_TERMUX_AUTOSTART=0` disables automatic startup; Fish, SSH, child shells and noninteractive commands do not autostart tmux. See [startup details](docs/shell-init.md#termux-tmux-startup).

New Bash/Zsh panes load the directory hook automatically. In a shell that was already running before this update, load it once with `source "$DOTS/shells/shared/tmux-workspaces.sh"`. Open a new Termux tab to use automatic startup. In an existing tmux server, **prefix + q** reloads the status configuration; changing source files does not reload that server automatically.

Optional gitmux adds Starship-style Git status such as `main !68 ?45 +1849-340` immediately after the last session/window label, with shared Dots Git colors, compact counts and line-change totals that follow theme refreshes. Its editable config is cataloged and linked at `~/.gitmux.conf`; Git status hides outside repositories or when gitmux is unavailable. Mode indicators remain on the right. See [gitmux configuration](docs/themes.md#gitmux).

## Shell initialization

Bash and Zsh now share their [interactive functions and aliases](docs/shared-shells.md). Bash uses Readline vi mode, the same Starship configuration, FZF/Gum theme colors and supported native tool integrations. `ff` is the shared FZF picker; Bash's former filename search is `findfiles`. Zsh-only editor plugins remain native. Personal Zsh bindings live in [`shells/zsh/keys.zsh`](shells/zsh/README.md#personal-keybindings-and-history-search), including vi-mode history search with Up/Down and normal-mode `k`/`j`, unique substring matches, and current Dots theme colors.

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
sources. Human path fields show `~` for the home directory. `dots env NAME`,
`dots env --json` and ordinary redirected listings retain full paths.
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
dots theme files
dots theme files info bat.tmTheme
dots theme files check
theme list                         # Equivalent standalone entry point
catppuccin mocha blue hex           # Native palette query
catppuccin mocha set                # Explicit activation
dots theme bg next                 # Explicit wallpaper change
```

The Yazi configuration uses the local [dots.yazi plugin](config/yazi/plugins/dots.yazi/README.md), combining the Dotline header/status renderer, Git indicators, saved projects, folder rules, and pane toggles. File panes use inherited `LS_COLORS` styles, including backgrounds and text attributes; the `hover` header component defaults to the symlink’s own style before the arrow and the target basename’s actual style after it, with a separately styled target directory, with independent style sources, color/attribute overrides, and visibility options for each part. Its repository component shows the Git working tree folder name before branch details and hides outside repositories. Optional `git-it` adds a remote host icon and a configurable color for repositories matching its configured owners; the personal config uses green for owned repositories and blue otherwise.

The personal Yazi configuration enables `githead.hide_in_tmux`: inside tmux, the entire top-right repository/Git group is hidden and its background queries stop, while file-list Git badges remain enabled. Outside tmux the header appears normally. Set the option to `false` in `init.lua` and restart Yazi to show the group inside tmux as well.

The personal Yazi configuration uses square section edges and a status-line mode indicator: `N` for normal, `V` for visual selection, and `U` for unsetting selections. The bundled [dots.preview component](config/yazi/README.md) uses Chafa's `vhalf` image rendering on Termux and mdcat for Markdown, with Alt+m toggling Bat source view per tab. Image/Markdown renderers, extra arguments and platform overrides live in `init.lua`.

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

eza also follows the selected palette through a generated `theme.yml` in an existing eza config directory. The default template adapts the supplied Catppuccin Mocha Mauve theme and shared Git roles. `EZA_CONFIG_DIR` and Windows APPDATA destinations are supported; existing LS_COLORS/EZA_COLORS overrides remain effective. See [eza setup](docs/themes.md#eza).

Leaf can use Dots colors for both its interface and code highlighting with the [local Leaf build and setup](docs/themes.md#leaf). Select `theme = "themes/dots.toml"`; publication maintains the UI theme and its shared syntax file together.

Television follows the selected palette through its generated `themes/dots.toml`. Select `[ui] theme = "dots"` in Television’s config; Dots refreshes the theme using a journaled connector. See [Television setup](docs/themes.md#television).
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
the expanded Catppuccin-derived language scopes, dynamic Dots palette colors, and
configured Git diff colors. Leaf and bat-backed previews use the same syntax theme.
The generated Bat cache includes custom `.sublime-syntax` files from your Bat
configuration's `syntaxes/` directory. Run `dots theme refresh` after changing
them; see [custom Bat syntaxes](docs/themes.md#custom-bat-syntaxes).
Selection journals and backs up fixed application theme connectors. Bash and Zsh refresh
at the next prompt; Neovim uses the local Anodize.nvim plugin and refreshes on state changes, focus or `:DotsThemeReload`.

Browse generated artifacts and their application destinations with `dots theme files`. Use `info FILE` to trace sources and links, `show FILE` for highlighted terminal text or directory contents, `path FILE` for an exact path, or `browse` for an optional read-only picker. `check --consumers` adds read-only checks of supported environment/configuration evidence. Sources describe the next refresh; inspection never publishes changes. See [generated theme files](docs/themes.md#generated-theme-files).

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

Anodize defaults use only the supplied six-row braille LOGO1 and LOGO2: wide help uses LOGO2, narrow help and ordinary results/previews use LOGO1. Piped output, disabled icons and short panes preserve the artwork; short panes scroll. Colored logos blend from bottom-left theme hint through info to top-right accent, restarting for the symbol and wordmark; previews use their candidate palette. Palette views, including Show, color the entire panel from the logo through the header and result details. The Anodize menu includes Extract, with image/lightness/mode selection and a scrollable result. Preview also retains its result until dismissed. Explicit graphics and larger braille layouts remain available. JSON, raw configuration, exports and completion data stay undecorated. See the authoritative [logo contract](docs/anodize.md#terminal-logo).

New Anodize themes save to `~/.config/dots/themes/ID/` by default, including a copy of source images under `backgrounds/`. Use `--builtin` on create/import to save into repository themes, or `anodize promote ID` to move a user theme there. `anodize --interactive` offers guided FZF selection and editing; theme and mode previews include syntax samples on the candidate background. See [interactive authoring](docs/anodize.md#interactive-authoring-and-previews).

Anodize provides a reusable Go color engine and CLI for creating themes from images, seed colors, existing themes and local imports. Build the private engine explicitly, then preview a new theme:

```sh
python3 -B tools/verify_anodize.py build
bin/anodize create dusk --color '#725ac1' --dry-run
bin/anodize create dusk --color '#725ac1' --yes
bin/anodize preview dusk
bin/anodize apply dusk --dry-run
```

`dots anodize` provides the same routes. Run `anodize --help` for commands and examples, or `anodize create --help` for source and save options. Bash, Zsh and Fish completion is available through `anodize completion SHELL`; read the manual with `man -l man/anodize.1` from the checkout. See [shell setup](docs/anodize.md#shell-completion-and-manual) for loading completions and installing the manual. Saves use recoverable file transactions and do not activate themes. Apply separately with `--yes` after reviewing its preview. See [Anodize](docs/anodize.md) for image extraction, repeatable adjustments, imports/exports, dependencies and limitations. Dots Neovim integration uses the separate local Anodize.nvim checkout. Android APK and TUI remain follow-up work.

## Files and Configuration Layout

`config/` is canonical in Dots and its bundled Termux/Windows profiles. Temporary `configs -> config`
aliases remain for compatibility. The Neovim submodule now lives at `config/nvim`.

Dots no longer exports `DOTRUBY` or `RUBYCOMP`. Reload Dots initialization or open a new shell to clear inherited values and obsolete checkout `ruby/completion` PATH entries. Ruby configuration under `config/ruby` remains available. File resources use `termux:*` and `windows:*`; old CLI names return a replacement hint. See [profile migration](docs/profiles.md#androidots-and-windots-migration).

```bash
dots files sources
dots files list --repo termux          # windows selects the Windows source
dots files browse
dots files list --sort app
dots files check --dry-run              # Preview missing-source catalog cleanup
dots files check                        # Review each entry, then confirm removals
dots files repair --dry-run             # Preview safe destination repairs
dots files repair                       # Resolve link issues, then review and confirm repairs
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

`dots files repair` restores missing catalog destinations and verified broken links. Its interactive helper lets you resolve old links and ordinary destination conflicts by queuing a relink or backed-up replacement, then approving the batch once. Generated-theme connections and conflicting ownership stay protected. Use `--dry-run` to inspect, or `--yes` to apply automatic repairs only; unresolved issues need the bare command. Resource IDs and repository/app/category filters narrow the scan. Results include unresolved findings and a journaled undo command. See [managed file repair](docs/files.md#repair-managed-destinations).

`dots files stash ID` keeps the source and catalog entry, disables installation
and removes its matching link; `--restore` enables and relinks it. `dots files edit`
edits or creates mappings, with `--apply` to reconcile live links. Both support
interactive review, `--yes`, `--dry-run`, JSON and journaled undo. See
[stash and edit](docs/files.md#stash-and-edit-mappings).

The first files slice locates and classifies sources and destinations, and tracks
intent in each source's `.dots/files.json`. The bundled Termux profile contributes
resources explicitly; unavailable/private sources are not initialized. `track`
changes catalog metadata only. Bounded file operations use links by default;
add/link/remove, adoption, undo and backups are available below. Profile installation uses explicit catalog mappings; directories are not merged automatically. See the [catalog reference](docs/files.md)
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

Inspect the Dots repository with `dots git info`, browse registered descendants
with `dots git submodules --details`, or show their full info blocks with
`dots git submodules info --depth 2`. Use `dots git submodule nvim` for one
repository, `dots git submodule nvim status --dirty` for its subtree, or
`dots git submodule 5ui7e info` for the optional Rainmeter source. Named navigation uses
direct-child path basenames; the Rainmeter source is registered at `profiles/windows/rainmeter/5ui7e`.
Preview publication with `dots git submodule nvim publish --dry-run` or the exact
path form `dots git submodules publish config/nvim --dry-run`. Both exclude the
outer repository. Use plural `publish --all-submodules` to select every direct
child subtree. Human identities use host icons and `main`, following your icon
and color settings; Git info `Path` fields use normal folder styling. Human
submodule trees keep vertical guides connected through spacing and details.
JSON and scalar output keep their original values.

```bash
dots git info
dots git submodules
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
Termux-specific mappings belong to `profiles/termux`. `files link ID` installs a known
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

## Design Priorities

1. Protect existing files and preserve a reliable path back.
2. Keep command dispatch, planning, and shell startup fast.
3. Show a complete plan before changing a machine.
4. Use symbolic links by default and copy only when explicitly selected.
5. Keep repository ownership and platform-specific destinations explicit.
6. Keep private sources and large optional assets out of the minimum bootstrap path.
7. Keep behavior, tests, help, completions, and documentation synchronized.

## Documentation

- [`AGENTS.md`](AGENTS.md) — authoritative instructions for agents and contributors.
- [`docs/principles.md`](docs/principles.md) — product and engineering priorities.
- [`docs/architecture.md`](docs/architecture.md) — implemented component boundaries and repository ownership.
- [`docs/commands.md`](docs/commands.md) — implemented command families and extension model.
- [`docs/specification.md`](docs/specification.md) — theme, catalog, shell and installation data contracts.
- [`docs/safety.md`](docs/safety.md) — planning, transactions, backups, rollback, and undo.
- [`docs/platforms.md`](docs/platforms.md) — Termux, Linux, WSL, and Windows model.
- [`docs/testing.md`](docs/testing.md) — test isolation, failure cases, and performance measurement.

The complete documentation index is in [`docs/README.md`](docs/README.md).

## Contributing With an Agent

Agents must read [`AGENTS.md`](AGENTS.md) before changing the project and then read the task-specific guide under [`agents/guides/`](agents/guides/). A behavior change is incomplete until the corresponding tests, plans, and source-of-truth documentation are updated in the same change.

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

The bundled Starship prompt shows its Git branch, commit, status, metrics and operation state only outside tmux. A nonempty `TMUX` hides the entire Git group; outside tmux it retains the configured Git styles and palette.

The saved [Blastoff `dots` theme](config/blastoff/themes/dots.toml) uses shared color names and Git roles while retaining the personal prompt layout. It includes styles for supported inactive Starship modules. With `dots theme plugins enable starship`, publication/refresh updates only `[palettes.dots]` in the active Starship config and saved `dots` theme. Other selected palettes are skipped; module edits and extra palette names remain intact. See [Starship integration](docs/theme-plugins.md#starship-and-blastoff-starship).

## Termux location lookup

Androidots provides `termux-geo` for device coordinates and Nominatim city/state/postal information, with Dots human output, delayed progress, JSON in pipes, scalar getters and cache-only reads. `termux-geo completion --all --install` installs static completions into Androidots-local Bash/Zsh/Fish directories recognized by personal Termux startup. See the [location command reference](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-geo.md) for dependencies, service restrictions, flags, and completion activation.

## Platform profiles and environment

Use `dots profile` for the detected platform and active layers, `dots profiles`
for available definitions, and `dots env` for managed settings, app environment,
PATH contributions and hook provenance. Platform resources live under `profiles`;
root config, scripts and shell trees stay universal. Bash/Zsh prepare native
startup bundles. `dots init --bootstrap bash|zsh|powershell` prints a standalone
missing-checkout bootstrap snippet. See [profiles and startup](docs/profiles.md)
for installation boundaries, compatibility paths and native acceptance limits.

Profile inspection now includes `dots profile layers`, `paths`, `env`, `files`,
`commands`, and `check`; `dots profiles check` validates every definition.
`dots debug` provides health/PATH/command/cache inspection, explicit startup
traces and isolated self-tests. Start with `dots debug startup --shell zsh`,
then add `--isolated` or explicitly `--live`. Reports use nested trees; `--detail changes` adds per-boundary state differences, and `--detail deep --changes path,aliases,options` adds native observations. Opt-in `dots debug record start --shell zsh` emits code to evaluate in the current shell; `dots debug path --history` then explains recorded PATH edits. See [debugging](docs/debug.md)
and [profile inspection](docs/profiles.md#profile-inspection-subcommands).

## Wiki

`dots wiki` provides grouped terminal navigation for the [project wiki](https://github.com/5nik7/dots/wiki). Use `list`, `show PAGE`, `search QUERY`, `browse`, `open PAGE`, or `edit PAGE` to read and maintain documentation. Canonical pages live in this repository; `dots wiki build --dry-run` previews the generated export and sidebar, and `dots wiki check` verifies freshness. The default checkout is `~/repos/dots.wiki`, overridden by `DOTS_WIKI_DIR`.

Normal Git operations include the associated wiki; use `--no-wiki` to exclude it or `dots git wiki status|sync|publish` for wiki-only work. Builds never stage or publish changes. See [wiki maintenance](docs/wiki.md).
