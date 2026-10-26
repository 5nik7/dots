# Keybinding browser

`dots keys` combines readable binding references for Zsh, Bash, PowerShell,
tmux, Neovim, Yazi, Codex CLI, FZF, Kitty and Television. It uses live evidence where an
adapter can supply it and literal configuration or versioned reference data elsewhere. It never executes a
binding, starts an app to load plugins, or downloads defaults.

```sh
dots keys
dots keys all
dots keys zsh --mode viins
dots keys tmux --query copy
dots keys yazi --print
dots keys codex --print
dots keys codex --mode editor
dots keys apps
dots keys --source live --json
```

## Browsing and notation

Interactive `dots keys` opens a compact FZF category menu with All and the apps
that have available bindings, each with a Nerd Font icon when icons are enabled.
Entries show counts such as `tmux · [47]`; All shows the combined count. The
separator, brackets and count use the same muted color as binding metadata, even
on the selected entry. Zero-count apps are omitted. If every count is zero, the
command prints its normal empty result without opening a menu.

The menu counts the captured snapshot after `--source` and `--no-defaults`
filtering, across all modes and independently of search text or the starting
`--mode`. Selecting an app reuses that snapshot, so counts agree with the available
rows without a second collection. All opens the combined bindings. There is no
redundant Apps entry; the explicit `dots keys apps` route remains an app-only
chooser. `dots keys all` and `dots keys APP` bypass the category menu, and a direct
app route collects only that app.

Menus fit their labels and row count, clamped to the terminal size, and have no
preview. All key pickers use `--info=inline-right` for their match counts.
Binding browsers inside tmux use `--popup center,99%`; outside tmux they
use ordinary FZF. The binding preview occupies 45%, on the right in wide terminals
and below in narrow terminals. `--browse` requests the
picker explicitly, including from a tmux binding. An FZF version without popup
support reports an error in tmux; `--print` remains available. Missing FZF falls
back to a readable list. Redirected output prints by default, and `--json`
produces undecorated version-1 data. These output options are mutually exclusive.

The main menu and combined list use the prompt `󰌆 : `. A specific app uses `󰌆 APP: ` (for example, `󰌆 tmux: `) and omits the repeated app field from its rows. Selecting a mode through `--mode` or Alt-M hides the mode column and changes the prompt to `󰌆 APP·MODE: `, such as `󰌆 zsh·viins: `. Across all apps, a selected mode uses `󰌆 all·MODE: `. Returning to all modes restores the mode column and shorter prompt. Disabled icons omit the prompt glyph.

App, mode and keys columns align to their longest value in the current app/mode view, capped at 12, 18 and 16 terminal cells. Longer values end in `…`. Narrow lists shrink these columns further to reserve description space; typing a search does not change their widths. App/evidence fields and separators use muted colors, modes use the theme's orange role, keys use bold bright magenta, and descriptions retain their foreground. Selected rows keep these colors. Plain output has the same layout without ANSI. Search uses the displayed row text; complete values remain in previews and print/JSON data.

The preview has no heading or leading indentation. Its first fields are Keys, Action and Mode, followed by identifier, evidence, status/scope, exact notation, source location when available and description provenance. Values use the same colors as the list and wrap to the preview pane's width without shortening. Enter prints the selected details and exits; Escape/Ctrl-C in the binding list cancels with status 130. The browser never executes binding actions or alters mappings.

`Ctrl+G` replaces `^G`; `Ctrl+H (Backspace)` and `Backspace (DEL)` remain distinct.
Arrows and modifiers have names. `g → g` is a sequence, while `Ctrl+G` is a chord.
Tmux prefix-table rows include the observed prefix. Unknown sequences retain
readable components and exact notation in details rather than an invented name.
Native maps that represent printable self-insert ranges or undefined keys are
omitted from the shell reference.

**Alt-M** opens a compact FZF mode chooser with the prompt `󰌆 modes:`. It lists `all` first, followed by alphabetically sorted modes, with the current mode initially highlighted. Enter selects a mode; Escape returns unchanged; Ctrl-C cancels browsing. The binding popup closes while the chooser is open and returns with its search preserved. The chooser starts with an empty search each time. Headers show `Alt-M: mode` without a repeated mode label or provider banner.

Available modes come from the selected app's source/default-filtered snapshot; the combined view uses the union of mode names. Search text does not change these choices. Switching modes reuses the snapshot and original preview identities. Reopen the browser to capture changed mappings.

`--query TEXT` initializes FZF search; in print/JSON mode its whitespace-separated
terms are case-insensitive substring filters. In the picker, `--mode MODE`
selects the starting mode and Alt-M can switch to other modes. An unknown starting
mode has no rows; Alt-M can select all or an available mode. Print/JSON and missing-FZF fallback retain
exact mode filtering. `--source live|configured|all` defaults to all. `--no-defaults` removes
identified bundled or installed defaults; live maps whose default/custom origin is unknown
remain visible. `dots keys apps --print` and redirected `dots keys apps` report
provider counts and coverage notes; `--json` retains the versioned data contract.

## Live versus configured evidence

| Provider | Evidence available |
| --- | --- |
| Zsh | Invoking shell's ZLE keymaps, including loaded vi-mode and plugin widgets; the tmux shortcut can request these from its source pane while Zsh is at a prompt. |
| Bash | Invoking shell's Readline maps, keyboard macros and shell-binding identities. Macro/command bodies are omitted. |
| PowerShell | Invoking PSReadLine session's bound handlers and descriptions. Native engine acceptance is separate. |
| tmux | Running server's tables, authored notes and current session prefix settings. No server is started. |
| Neovim | `:DotsKeys` captures current global and buffer mappings; buffer mappings win. Ordinary CLI inspection recognizes conservative literal Lua declarations. |
| Yazi | Complete bundled shipped defaults plus TOML keymaps from the selected config directory. Prepend/replacement/append precedence is compared statically; conditional activation is unverified. |
| Codex CLI | Bundled CLI 0.164.0 default and contextual controls plus user `tui.keymap` overrides. Includes editing, Vim modes, pickers and approvals; no running-session capture. |
| Television | Picker and shell-integration bindings in TOML; supported installed defaults when present. |
| Kitty | Literal `map` declarations and ordinary includes. Dynamic/generated/wildcard includes are omitted with a note. |
| FZF | Exported option bindings or the Dots shared declarations, plus a version-matched installed manual's default-binding table. Per-invocation overrides and `FZF_DEFAULT_OPTS_FILE` contents are not observed. |

Live entries are marked active. Matching configured entries are marked shadowed;
other declarations say activation is unverified. Yazi and Codex include pinned offline references. Other providers include supported installed default data when available. Missing default data and dynamic declarations are reported as coverage gaps, never silently replaced with guessed defaults.
Neovim's unmapped built-in editing commands are not keymap records; plugins that
have not loaded are outside a live snapshot. Multiple modes remain separate.

Shell capture uses a small interactive `dots` function installed by Dots shell
integration. It captures on demand only for the relevant key query; ordinary
routes pass their arguments to the executable unchanged. Reload integration or
start a new shell to install it. An existing user-defined `dots` function is left
alone. `command dots keys` bypasses the shell adapter and therefore cannot inspect
the parent shell's nonexported keymaps. No keymap scans or snapshots occur during
ordinary startup or at each prompt.

### Live Zsh bindings from the tmux shortcut

Prefix → ? passes its originating pane to the browser. Before opening the
counted main menu, the browser requests that pane's loaded Zsh keymaps, including
built-in and plugin bindings. Direct Zsh, All and Apps routes also request them.
Rows and previews identify live versus configured evidence. Coverage notes in print/JSON output explain unavailable live capture; picker headers omit provider banners. Configured evidence is a partial reference: literal declarations do not enumerate Zsh's built-ins or dynamically installed widgets.

The interactive Zsh adapter opens a private Unix socket while its prompt is
active, closes it before running a command, and reopens it at the next prompt.
Requests are handled through ZLE and a bounded background sender. Capture leaves
the current buffer, cursor and editing maps intact. It neither sends keystrokes
to the pane nor interrupts an application. A busy shell, absent integration,
unsupported socket module, unavailable runtime directory or ambiguous responder
falls back to configured rows with a coverage note. Each new browser request
captures fresh mappings; an already-open list remains a snapshot.

Fresh integrated Zsh sessions install the adapter automatically. To enable it in
an existing session without reloading personal bindings, run there:

```zsh
source "$DOTS/lib/dots/shell/keys.bash"
```

The tmux shortcut must also match the configuration below. Explicit caller
snapshots take precedence, and `--source configured` bypasses the request.
Runtime sockets live in an owner-only `dots-k-UID` directory beneath
`XDG_RUNTIME_DIR`, otherwise `TMPDIR` or `/tmp`. Registration performs no keymap
scan; captures use bounded memory and anonymous pipes/sockets, not persistent
keymap dumps. This transport applies to Termux/Linux/WSL Zsh. Native PowerShell
and other providers retain their existing capture paths.

### Other live and configured sources

In Neovim, run `:DotsKeys` in the target buffer. The exporter uses inert temporary
JSON and launches the shared browser in a terminal buffer (FZF owns its popup
when in tmux). Cancel returns to the original window; successful selection leaves
the details in the terminal buffer. It never forces lazy plugins to load.

Active application config directories take precedence over repository fallbacks;
XDG roots and the supported Yazi/Kitty/Neovim directory overrides are respected.
Configured shell inspection includes the applicable profile layers and a readable
Zsh local hook. No private file is sourced. Collection reads bounded regular
files and uses literal/native queries; Lua, shell expressions and returned code
are never evaluated. Exact source locations are shown only when known.

## Yazi defaults

The bundled shipped preset includes all 254 bindings across `mgr`, `tasks`, `spot`, `pick`, `input`, `confirm`, `cmp`, and `help`. Selected user configuration remains visible alongside it, including Dots preview and project shortcuts. Prepend bindings shadow matching base bindings; an explicit `keymap` replaces that context's entire base table, even when empty; matching base bindings shadow append entries. Displaced defaults remain visible as shadowed reference rows. Raw key sequences and authored descriptions are retained. The preset revision is reported in coverage; installed-version compatibility and runtime conditions are unverified.

## Codex CLI defaults and custom keys

`dots keys codex` includes the complete pinned configurable action inventory and contextual controls. Context names match Codex's keymap contexts where possible, including `global`, `chat`, `composer`, `editor`, `vim_normal`, `vim_operator`, `vim_search`, `vim_text_object`, `pager`, `list`, `agents`, and `approval`. Additional contexts identify fixed controls in popups and dialogs. Search descriptions or use `--mode` to narrow the reference. Normal typing, a separate slash-command catalog, and dynamically assigned item-specific accelerators are not listed.

User mappings come only from `$CODEX_HOME/config.toml`, or the native user home's `.codex/config.toml` when `CODEX_HOME` is unset. This location applies to Windows as well; `APPDATA` and XDG directories do not select Codex configuration. Only `tui.keymap` values are inspected for output. Missing or malformed configuration leaves the default reference available with a coverage note.

String values and arrays of alternatives are supported. A space within an alternative denotes a two-stroke chord; `leader` expands to the configured shared prefix for display while the raw spelling remains intact. Composer `submit`, `queue`, and `toggle_shortcuts` use the corresponding global value when no local override exists. Remapping shadows every default alternative for that action. An empty array disables the action and produces an `Unbound` row with status `disabled`; `--no-defaults` retains custom and disabled entries.

Project/profile/command-line layers, runtime conflict validation, feature gates and changes inside a running session are outside this snapshot. Context-specific interception and terminal capabilities affect availability; the reference does not label these rows live or active. Unix suspension is labeled unavailable on native Windows. Source revisions, attribution and maintenance instructions are in the [bundled reference notes](../lib/dots/keys/data/SOURCES.md).

## Tmux compatibility

The [Dots workflow menu](commands.md#dots-workflow-menu) also offers Keybindings. When launched from Prefix m, category/app and binding choosers consume the launcher's exact client context, while preserving the live Zsh pane bridge, Alt-M mode selection and existing preview controls. Prefix s opens the separate session picker. These repository bindings take effect when the configuration is loaded; Prefix ? below retains its original invocation.

`dots menu tmux keys` and `dots-menu-tmux-keys` remain aliases of the tmux provider,
with `--print`, `--json`, `--browse`, `--mode` and `--query` options. The repository
binding now lets FZF own the popup:

```tmux
bind -N "Browse keybinding categories" ? run-shell -b 'DOTS_KEYS_TARGET_PANE=#{pane_id} dots keys --browse; _dots_keys_status=$?; if [ "$_dots_keys_status" -eq 130 ]; then exit 0; fi; exit "$_dots_keys_status"'
```

Keep Dots and FZF on tmux's PATH. Updating the configuration does not reload a
running server. The active `?` binding must match this line: an old `display-popup`
wrapper can nest popups and prevent the picker from opening correctly. Prefix → ?
opens the same category menu as interactive `dots keys`; the compatibility command
continues to open tmux bindings directly.
The shortcut treats Escape/Ctrl-C (status 130) as a normal close, so tmux does not
display a cancellation error. Other failures remain visible with their original
status. Direct `dots keys` invocations still return 130 on cancellation.
The picker reuses the published Dots FZF colors and does not inherit arbitrary
FZF command/preview bindings from the shell. Other tmux popups keep their existing
shared theme styling.

## Termux vi-mode Backspace

The local Termux hook keeps the working `zvm_config()` clipboard/open settings and
semantic highlight colors. Both `^H` and `^?` in `viins` use
`backward-delete-char`. A deduplicated callback reapplies those two bindings after
vi-mode initialization, mode transitions and local-file reloads. Normal and visual
maps are preserved. This removes the insertion-boundary difference between the
two Backspace encodings; device-specific keyboard behavior still needs native use.
