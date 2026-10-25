# Keybinding browser

`dots keys` combines readable binding references for Zsh, Bash, PowerShell,
tmux, Neovim, Yazi, FZF, Kitty and Television. It uses live evidence where an
adapter can supply it and literal configuration elsewhere. It never executes a
binding, starts an app to load plugins, or downloads defaults.

```sh
dots keys
dots keys all
dots keys zsh --mode viins
dots keys tmux --query copy
dots keys yazi --print
dots keys apps
dots keys --source live --json
```

## Browsing and notation

Interactive `dots keys` opens a compact FZF category menu: All, Apps, Bash, FZF,
Kitty, Neovim, PowerShell, Television, tmux, Yazi and Zsh, each with a Nerd Font
icon when icons are enabled. All opens the combined bindings. Apps opens a second
chooser with provider counts and availability; selecting a provider opens its
bindings. `dots keys all` and `dots keys APP` bypass the category menu.

Menus fit their labels and row count, clamped to the terminal size, and have no
preview. Binding browsers inside tmux use `--popup center,99%`; outside tmux they
use ordinary FZF. The binding preview occupies 45%, on the right in wide terminals
and below in narrow terminals. `--browse` requests the
picker explicitly, including from a tmux binding. An FZF version without popup
support reports an error in tmux; `--print` remains available. Missing FZF falls
back to a readable list. Redirected output prints by default, and `--json`
produces undecorated version-1 data. These output options are mutually exclusive.

Rows show app, mode, keys, description and evidence. The preview shows exact
notation, action identifier, source location when available, and whether the
description is authored, dictionary-based, or a humanized identifier. Enter
prints the selected details and exits; Escape/Ctrl-C cancels with status 130.
The browser does not execute action strings, open source files or alter bindings.
App/type, mode, evidence and separators use the theme's muted color; key text is
bold bright magenta and descriptions retain their foreground. Selected rows keep
these field colors. Plain/color-disabled output retains all text without ANSI.

`Ctrl+G` replaces `^G`; `Ctrl+H (Backspace)` and `Backspace (DEL)` remain distinct.
Arrows and modifiers have names. `g → g` is a sequence, while `Ctrl+G` is a chord.
Tmux prefix-table rows include the observed prefix. Unknown sequences retain
readable components and exact notation in details rather than an invented name.
Native maps that represent printable self-insert ranges or undefined keys are
omitted from the shell reference.

`--query TEXT` initializes FZF search; in print/JSON mode its whitespace-separated
terms are case-insensitive substring filters. `--mode MODE` is an exact context
filter. `--source live|configured|all` defaults to all. `--no-defaults` removes
identified installed defaults; live maps whose default/custom origin is unknown
remain visible. `dots keys apps --print` and redirected `dots keys apps` report
provider counts and coverage notes; `--json` retains the versioned data contract.

## Live versus configured evidence

| Provider | Evidence available |
| --- | --- |
| Zsh | Invoking shell's ZLE keymaps, including loaded vi-mode and plugin widgets. |
| Bash | Invoking shell's Readline maps, keyboard macros and shell-binding identities. Macro/command bodies are omitted. |
| PowerShell | Invoking PSReadLine session's bound handlers and descriptions. Native engine acceptance is separate. |
| tmux | Running server's tables, authored notes and current session prefix settings. No server is started. |
| Neovim | `:DotsKeys` captures current global and buffer mappings; buffer mappings win. Ordinary CLI inspection recognizes conservative literal Lua declarations. |
| Yazi | TOML keymaps from the selected config directory and supported installed default files. Full-table replacement and conditional activation are not evaluated. |
| Television | Picker and shell-integration bindings in TOML; supported installed defaults when present. |
| Kitty | Literal `map` declarations and ordinary includes. Dynamic/generated/wildcard includes are omitted with a note. |
| FZF | Exported option bindings or the Dots shared declarations, plus a version-matched installed manual's default-binding table. Per-invocation overrides and `FZF_DEFAULT_OPTS_FILE` contents are not observed. |

Live entries are marked active. Matching configured entries are marked shadowed;
other declarations say activation is unverified. Supported installed default data
is included when available. Missing default data and dynamic declarations are
reported as coverage gaps, never silently replaced with guessed defaults.
Neovim's unmapped built-in editing commands are not keymap records; plugins that
have not loaded are outside a live snapshot. Multiple modes remain separate.

Shell capture uses a small interactive `dots` function installed by Dots shell
integration. It captures on demand only for the relevant key query; ordinary
routes pass their arguments to the executable unchanged. Reload integration or
start a new shell to install it. An existing user-defined `dots` function is left
alone. `command dots keys` bypasses the shell adapter and therefore cannot inspect
the parent shell's nonexported keymaps. No keymap scans or snapshots occur during
ordinary startup or at each prompt.

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

## Tmux compatibility

`dots menu tmux keys` and `dots-menu-tmux-keys` remain aliases of the tmux provider,
with `--print`, `--json`, `--browse`, `--mode` and `--query` options. The repository
binding now lets FZF own the popup:

```tmux
bind -N "Browse keybinding categories" ? run-shell -b 'dots keys --browse; _dots_keys_status=$?; if [ "$_dots_keys_status" -eq 130 ]; then exit 0; fi; exit "$_dots_keys_status"'
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
