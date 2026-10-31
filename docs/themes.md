# Shared themes

**Status: Implemented flat themes, application templates, Git theme sources, explicit wallpapers and opt-in local theme plugins.**

`theme` and `dots theme` inspect and change the current theme and manage the
collection through one engine. Only the singular first-party family remains.
See [decision 0016](decisions/0016-core-command-families-and-file-identities.md).

Theme preparation, rendering, bat caches, publication, quiet reloads and installed-source validation use [terminal progress](presentation.md#operation-progress). Batch updates show processed checkout counts. Downloads, tmux reloads and wallpaper adapters use static phase messages to keep child output readable. `DOTS_PROGRESS=never` disables these displays. Raw queries, shell initialization and dry runs stay undecorated.

## Tmux

The linked tmux configuration has two top rows on Termux (detected from `TERMUX_VERSION`): the clock followed by Termux tab numbers on the upper left, battery on the upper right, and the current tmux session followed by its windows below. Outside Termux only the tmux row appears. The main configuration owns layout and conditional formatting after the generated include; `default/themed/tmux.conf.tpl` supplies semantic colors. Theme refreshes preserve the layout.

Termux tab numbers appear above only when more than one tab exists. The lower row numbers sessions only when their group has more than one session. Project groups follow the session picker and use canonical project folders; different folders with the same name stay separate. Non-project sessions group by their full case-sensitive logical label, including termux and multi. Attached and detached sessions count, with numbers assigned within each group in creation order. Only the current session appears: two Dots sessions show `1 dots` and `2 dots`, while a lone Battery session shows `battery`. Two tabs viewing the same tmux session have the same lower number. Window indexes independently depend on that session’s window count. Useful names remain when numbers disappear; matching singleton window names disappear. Full labels are compared case-sensitively before clipping. Managed labels hide immutable ID suffixes; project/multi names remain and the default termux label stays hidden. Manual names remain literal. Legacy `@dots-termux-default=1` sessions retain name hiding until adopted. Session labels and all windows without alerts have one outer space per side. Bracketed alerts have none; adjacent sections use one `│` without orphan dividers.

| Element | Background | Foreground |
| --- | --- | --- |
| Popup content | `background` | `foreground` |
| Popup border | `background` | `lighter_background` |
| COPY/ZOOM indicators (one space on each side) | `green` | Bold `darker_background` |
| PREFIX indicator (one space on each side) | `dark_background` | Bold `accent` |
| Upper row | `background` | `foreground` |
| Clock | `dark_background` | Bold `yellow` by day, `blue` at night, `foreground` when unknown |
| Current Termux tab number | `selection_background` | Bold `orange`, no underline |
| Other Termux tab numbers | `dark_background` | Bold `dark_foreground`, no dimming or underline |
| Lower tmux row on Termux | `background` | `foreground` |
| Inactive Codex window numbers | Existing inactive background | Bold `magenta` |
| Ordinary inactive window numbers | Existing inactive background | Bold `dark_foreground` |
| Inactive Working marker | Existing inactive background | Bold `accent`, `` |
| Inactive waiting marker | Existing inactive background | Normal `accent`, `` |
| Current window numbers on all tmux platforms | `selection_background` | Bold `bright_green`, no underline |
| Current Working/waiting markers | `selection_background` | Bold `accent`, `` / `` |
| Session Working/waiting marker when windows are hidden | Session background | Bold `accent`, `` / `` |
| Current window name | `selection_background` | Bold `bright_foreground` |
| Inactive Codex window name | Existing inactive background | Bold, dimmed `foreground` |
| Ordinary inactive window name | Existing inactive background | Bold, dimmed `dark_foreground` |
| Current session, including its number when shown | `selection_background` | Bold `bright_cyan`, no underline |
| Window with a bell, activity or silence alert, including its name | `darker_background` | Bold `bright_red`, no underline or reverse video |
| Divider between sections `│` | `dark_background` | Normal `background` |
| Number/name space | Containing section’s background | Plain spacer |

Generated number/name separators are single spaces. Session sections and both current and inactive windows retain one outer padding space on both sides; alerted windows omit it. Adjacent windows render as `│ 1  │ 2  │`, or `│ 1 editor  │ 2 shell  │` with names. Selecting a window preserves its padding. The session number, remote icon and name use the session style without underlining. Current window names switch to bold `bright_foreground` on `selection_background`; inactive names use bold, dimmed `foreground` for Codex and `dark_foreground` otherwise. Dimming ends with the name span. After each name, number/marker styling is restored for padding and closing warning brackets. Literal punctuation and whitespace inside names stay unchanged. Section-boundary `│` bars use `background` on `dark_background` without bold, underline, dim or reverse attributes.

Alerts surround the complete window label with square brackets: `[2]`, `[2 shell]`, or `[shell]` when its number is hidden. These brackets have no outer padding: ` dots │[2]`. Alert styling takes precedence over current-window and Codex styling. Codex attention also keeps internal spaces bold and bright red; native tmux alerts retain their existing separator styling. An alerted duplicate singleton shows its bracketed name, or its bracketed state marker if Working/waiting. Without an alert, a hidden singleton places its state marker after the session name instead of opening a separate window section. Tmux acknowledges its native bell/activity/silence alerts independently; the optional [Codex attention bridge](#codex-attention-notifications) acknowledges when the originating pane is viewed. Outside Termux the named session uses the same cyan style and windows use the same conditional numbering and separate number/name styles. The active pane border uses `selection`. Missing published colors use terminal-color fallbacks until a theme is applied.

Inactive Codex window numbers use bold theme `magenta`, with bold, dimmed `foreground` names. Ordinary inactive numbers and names use `dark_foreground`, with bold digits and bold, dimmed names. Working uses ``; explicit Waiting and input/approval requests use ``. Place the marker after the visible number/name, separated by one space: `1 `, `1 shell `, `1 ` or `1 shell `. A marker alone gets no extra leading separator; normal outer padding still applies. Both markers use `accent`, including in the current window. Working markers are bold; waiting markers are normal when inactive and bold when current. Without a number, show `shell ` or `shell `; when the singleton name is hidden too, append the marker to the session label instead, with one separating space and the usual outer padding: ` 󰊤 dots  ` or ` 󰊤 dots  `. Session markers use bold accent on the session background and restore the session style afterward. If the session label is also empty, show a padded marker-only session section. A visible window keeps its own marker, without duplication in the session. Idle, Ready and unknown states have no marker. Current names use bold `bright_foreground` on `selection_background`; current numbers retain bold `bright_green` on that background. Alerts retain bold bright red on `darker_background` across the complete label, including names and markers, such as `[1 shell ]` or `[]`. All panes count, including unselected panes; the window priority is Working, then explicit waiting, then idle.

The Python 3 `codex-status.py` helper shares one asynchronous inventory job across window labels in each client status context. It checks local same-user procfs process metadata for a foreground process named `codex` on the pane’s terminal, including launches through shell/Node wrappers. Suspended, background, exited and retained dead panes do not count. A title field exactly matching `Working`, with optional trailing dots or an ellipsis, marks work. An exact `Waiting` field (also with trailing dots or an ellipsis), `[ ! ] Action Required` or `[ . ] Action Required` marks an explicit wait and overrides a lingering Working field within the same pane. Ready, absent or unrecognized titles remain idle, with no marker. Codex must include `activity` and `run-state` in its configured [terminal title](https://learn.chatgpt.com/docs/config-file/config-reference) to expose these signals. This is a local title heuristic, not a Codex API or session-log integration.

The job uses the existing five-second status interval and a one-second inventory/process deadline. Missing tmux/Python/procfs, denied access, invalid data or a deadline failure clears Codex markers and coloring to ordinary inactive styling. It reads no process arguments, credentials or conversation history, sends no network requests and persists no state. With the attention bridge installed it also reads a bounded, expiring worker snapshot; only still-detected Codex windows can acquire attention tokens. Termux/Linux/WSL procfs is supported; other systems fall back to ordinary colors and native Windows has no tmux consumer.

### Codex attention notifications

The optional bridge adds attention for Codex choice questions (including asynchronous questions), permission approvals requiring a person, and successful completed turns. It replaces outer label spaces with brackets and uses bold theme `bright_red` on `darker_background` across the whole label: ` 2 ` becomes `[2]`, and ` 2 editor  ` becomes `[2 editor ]`. An alert in any pane overrides another pane's working color. Existing state glyphs and window scrolling remain; hidden singleton windows become visible while alerted.

On terminals with reliable focus reporting, viewing the originating pane acknowledges the event; focused events are suppressed at receipt and reconciliation. Control clients do not count. Stock Termux does not implement terminal focus reporting, so its default `termux.focus_policy = "conservative"` treats focus as unknown: alerts may occur in the visible tab, and a default tmux `focused` flag never suppresses or clears them. **Prefix a** acknowledges only the invoking Codex pane; the session picker also offers explicit acknowledgement. Answers/resumed work, new turns, interruption and session closure retire applicable pending attention. Merely opening the picker or switching Android tabs does not acknowledge anything. Switching away after acknowledgement never repeats the event. Fresh idle sessions and unknown titles never imply completion. Set `focus_policy = "terminal"` only for a terminal integration whose focus reporting has been verified.

On Termux, each eligible event attempts `termux-vibrate -d 300 -f` and `termux-toast -b <dark_background hex> -c <warning hex> -g middle -- <message>`. The default `toast_short = false` omits `-s` for the longer toast duration. The toast contains a compact Termux/tmux location when available, an event prefix and the actual question, approval description or final-response excerpt, normalized to 240 Unicode characters with an ellipsis. Missing text uses the event prefix alone. Colors are read from the current published palette at delivery time, with missing/invalid-role fallbacks `#000000` and `#ffff00`. Both requests start independently, each with a five-second deadline; a failure does not remove the tmux alert or trigger repeated attempts. Android may limit toast appearance or length.

[Preferences](../config/tmux/codex-alerts.toml) are repository source. The [hook template](../config/tmux/codex-hooks.json) and Python bridge are also repository-owned. The bridge uses the documented [completion notify callback](https://learn.chatgpt.com/docs/config-file/config-advanced#notifications) and [observational hooks](https://learn.chatgpt.com/docs/hooks), not conversation-log scraping. Setup makes `thread-id` the final Codex terminal-title field so events can be matched to panes even when Codex uses a shared background server. Codex can shorten that field to the first 29 UUID characters plus `...`; the bridge resolves this exact form only when it uniquely matches a full ID already received through a hook or completion callback. Acknowledged identities also count when rejecting collisions. Missing, malformed or ambiguous identities never acquire attention. Hooks never approve, deny or rewrite a request.

Setup requires Python 3.11+ and the optional `tomlkit` dependency listed in `tools/requirements-codex-notifications.txt`; normal operation uses only Python's standard library, tmux and local procfs. From the Dots checkout, preview and then apply:

```sh
python3 -B tools/configure_codex_notifications.py
python3 -B tools/configure_codex_notifications.py --apply
```

The helper updates only owned Codex settings, merges its hook handlers, retains an existing notify command as a bounded downstream callback, and records a retained Dots transaction. It leaves unrelated TOML/comments and hooks intact and refuses linked personal config files or changed ownership/notify settings. `--dry-run` overrides `--apply`. To preview recovery, use `python3 -B tools/configure_codex_notifications.py --undo TRANSACTION`; add `--apply` to perform drift-checked undo. Personal config is not copied into Git.

Load the updated tmux configuration through the existing reload binding. Codex must load the updated settings and its new hook definitions must be reviewed in `/hooks`; reconnect or restart a client as needed without interrupting other active sessions or restarting a shared server automatically. Hook trust is not bypassed by setup. The bridge remains inactive before explicit setup. Real Codex hook delivery, background-server reload behavior, Android appearance and device vibration require an owner acceptance check after trust; private tmux and mocked Android tests do not establish those results.

One worker per socket polls every five seconds, with cross-worker event deduplication and focus acknowledgement hooks. Rendering only reads its snapshot, which expires after 15 seconds and is tied to the socket's inode. Messages are removed from the private queue when delivered/dismissed; unmatched candidates expire after ten minutes, and acknowledged IDs are retained up to seven days within a 4096-event cap. Delivery is at-most-once attempt: a worker crash after claiming an event can skip that toast, rather than replay it. See the [maintenance guide](../agents/guides/codex-notifications.md), [storage contract](specification.md#codex-attention-state) and [safety boundary](safety.md#codex-attention-bridge).

The Termux tab adapter requires Python 3 and `profiles/termux/bin/termux-sessions` in the same checkout. Keep the directory link for `config/tmux`: the adapter resolves it without scanning PATH. One JSON query per job matches `client_tty` and emits `--tabs`, a bounded numeric strip immediately after the clock. An unalerted singleton produces nothing; outstanding attention in an undisplayed tmux session still produces its separate badge. It keeps nearby entries and the current tab visible, with overflow arrows when needed, reserving 18 columns for the clock/battery and capping the strip at 30 columns. Unmatched clients show an unselected strip; failed queries clear the strip. Tab discovery never controls lower-row visibility or numbering.

With the attention bridge running, other tabs include aggregate working (``) or waiting (``) activity from all foreground Codex panes in their attached tmux sessions, even if title thread IDs are unavailable. Attention requires a matched thread ID and wraps the full tab label in bold bright-red brackets, for example `[2 ]`; idle completion attention uses ``. Working takes precedence over waiting for the glyph; attention always overrides the label style. A separate `[ N]` counts distinct alerting tmux sessions displayed by no live Termux tab, including other registered sockets. The current tab and separate badge take space before neighbouring tabs; overflow hiding attention uses the alert color. Tab identity follows current attached client TTYs plus live PID/start-time validation, never the server ancestry or original workspace tab. **Prefix s → F1 → Codex alerts** lists affected sessions/windows/panes across registered servers, with same-server navigation, explicit acknowledgement and the existing New Termux tab action for another server.

The `--tabs` path explicitly clears dimming; older rendering modes retain their attribute contracts. The older `--compact-badge`, unsplit, `--split-current` and `--split-badge` outputs retain their contracts. The shipped lower row instead uses session-local group numbering maintained on creation, closure, project transitions and manual renames. Its current-session label uses at most one quarter of client width, capped at 30 columns; names shorten first to leave room for the number, remote icon and any session Codex marker. The icon is omitted only if the fixed prefix cannot fit. Hidden names leave no dangling separator. Native window scrolling and mouse ranges remain intact. Visibility checks use plain fields instead of recursively expanding complete styled sections. Workspace renaming is event-driven and does not run during status rendering; see [workspace metadata](specification.md#session-browser-projects).

The current session's optional remote icon follows the active pane directory. Like `dots.yazi`, it uses `git-it info --json`, including that tool's configured host aliases and branch-remote/origin selection. GitHub uses `󰊤`, GitLab ``, Bitbucket ``, and other remotes ``; a repository without a remote has no icon. The label reads `󰊤 dots` or `1 󰊤 dots`; a hidden default name retains `󰊤` or `1 󰊤`. The icon inherits current-session colors and boldness without underlining, and uses display cells in the badge budget. Missing or invalid metadata clears it without hiding the session name or Gitmux status. A Nerd Font is required for the glyphs.

The upper row no longer invokes Wi-Fi or cellular status helpers; notification, volume and location status modules also remain disabled. The independent `android-status.py` adapter and Androidots permission/cache contracts remain available to other consumers. Battery retains its existing thresholds, icon/percentage spacing and colors.

`config/tmux/weather-status.py` reads the shared wttr daylight interface with a one-second/16-byte bound and suppressed stderr. It accepts only day/night/unknown tokens. The clock uses theme yellow between today's sunrise and sunset, blue at night, and foreground for missing, failed, stale or invalid astronomy. Geometry and background are unchanged. The recurring job can schedule a bounded weather refresh using cached coordinates or configured fallback; it cannot acquire Android location. No weather widget is enabled. See [weather configuration, timezone limits and owner-run activation](wttr.md#termux-upper-row).

### Gitmux

When [gitmux](https://github.com/arl/gitmux) is installed on the tmux server's PATH and its managed `~/.gitmux.conf` is present, Git status follows the last session/window label. Its Starship-style appearance is `main !68 ?45 +1849-340`, using the shared Dots Git colors. It appears on Termux's lower row and the single tmux row on Linux/WSL. COPY/PREFIX/ZOOM stay on the right. A non-repository directory, unavailable executable/configuration or failed/timed-out query hides the entire Git segment, including its divider and padding. The upper row is unchanged.

The editable [gitmux configuration](../config/gitmux/gitmux.conf) shows branch/divergence/flags/statistics. Symbols touch their counts, with one space between populated groups; positive and negative line totals touch each other. The clean checkmark and remote branch names are hidden, and zero line totals are omitted. Gitmux owns counts, status order, special-state labels and detached/unborn representations; this matches Starship's appearance for supported fields rather than adding its separate deleted/renamed file counters. Gitmux's line statistics describe the unstaged diff. Branch names remain limited to 24 characters, and Git text is clipped to half the client's width, capped at 48 cells including an ellipsis, with one space on each side. Native window scrolling/mouse ranges and the five-second status interval are retained.

| Field | Appearance | Dots foreground | Weight |
| --- | --- | --- | --- |
| Branch | `main` | `git_branch` | Normal |
| Modified files | `!68` | `git_modified` | Bold |
| Untracked files | `?45` | `git_untracked` | Bold |
| Staged files | `+3` | `git_staged` | Normal |
| Conflicts | `=2` | `git_conflict` | Normal |
| Stashes | `*1` | `muted` | Normal |
| Added/deleted lines | `+1849-340` | `git_added` / `git_deleted` | Normal |
| Ahead / behind | `⇡2` / `⇣1` | `git_ahead` / `git_behind` | Normal |
| Diverged | `⇡2⇣1` | `git_conflict` | Normal |
| Special state | `[merge]`, `[rebase]`, etc. | `git_conflict` | Bold |

The existing generated tmux include supplies semantic options, with terminal-color fallbacks in the main config. YAML styles reference these options directly, including resolved [Git foreground overrides](file-colors.md#git-styles). Palette refreshes do not rewrite gitmux layout. Font attributes are fixed by the editable YAML rather than inherited from Git role attributes. `reset` foregrounds become tmux `default`, and resets prevent style leakage. No separate theme connector or generated gitmux file is needed.

The small `config/tmux/gitmux-status.py` adapter invokes gitmux for the safely quoted active pane directory with `-cfg "$HOME/.gitmux.conf" -timeout 1s`, enforcing a one-second deadline and 16 KiB output limit. It joins only adjacent Dots-styled positive/negative metric totals and recolors an adjacent Dots-styled ahead/behind pair as diverged. It rejects controls and escapes hashes in ordinary text while preserving configured styles, since tmux otherwise expands format-like Git branch names. Its opt-in `--snapshot DIRECTORY` mode also runs optional `git-it info --json` in that directory, concurrently under the same one-second deadline with a separate 64 KiB limit. Only a validated remote-present host icon is retained; URLs and other metadata are discarded. The internal result is `icon|gitmux-output`, split only at the first delimiter so Git names may contain pipes. Both consumers reuse one tmux job; each provider can succeed independently, and directory changes cannot retain the preceding directory’s icon. The existing one-directory interface still returns only Gitmux output. No cache, network request or tracker is added. Python 3 is required, like the other Dots status adapters. Native Windows has no tmux consumer or gitmux destination in Dots.

## Local theme plugins

`dots theme plugins list|enable|disable|run|doctor` adds explicitly enabled GTK 3,
Qt6ct and trusted local hooks. The shared post-commit publisher covers theme set,
refresh and Anodize apply; unchanged refresh retries integrations. Enable/disable
only persist selection. Bundled app writes use journaled copies; arbitrary local
hook effects are outside publication rollback. See [plugin authoring and safety](theme-plugins.md).
Downloaded themes remain data-only and never provide executable hooks.

## Unified commands and family shortcuts

`theme` forwards to `dots theme`, including help, exit statuses and existing full-ID
routes. Generated family and standalone commands use that same Dots handler:

```sh
theme list
catppuccin                         # Usage, logo and flavors
catppuccin mocha                   # Native palette preview
catppuccin mocha blue hex          # Native scalar query
catppuccin mocha set               # Journaled activation
rose-pine dawn set --dry-run
nord show
dots theme catppuccin mocha set    # Equivalent family route
```

No flavor-specific executables are generated. Family/flavor membership comes from
`theme.toml`; names are not split heuristically. A declared `default_flavor` wins;
a sole flavor is the default, while multiple flavors without a default require
an explicit choice. A bare family or standalone command shows usage. Explicit
`set` is required to activate. Native queries use `palette.toml`; ordinary
`dots theme color` and application templates use resolved colors.

Set/refresh and successful theme install/update/remove reconcile thin executable
wrappers under `${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes/commands`.
`dots theme refresh --commands-only` rebuilds wrappers without selecting a theme.
Shells append the stable `commands/current/bin` path. If an existing executable owns a theme's command name, Dots generates `name-theme` instead: an installed Ristretto image viewer leaves `ristretto` intact and the theme shortcut becomes `ristretto-theme`. If that alternative is also occupied, including by another theme's canonical command name, Dots skips the shortcut and reports the explicit `theme NAME` route. There are no numbered alternatives. Reserved Dots/action names remain excluded; full-ID routes remain available.

Allocation checks the publisher's PATH without executing discovered programs; native Windows checks case-insensitive names, PATHEXT extensions and `.ps1`. Verified current wrappers do not count as conflicts. Parent-shell aliases and functions are outside this check. Each generation recomputes names, including when theme colors are unchanged: after an external conflict is removed, the next refresh restores the bare name. Successful suffix selection is quiet by default and appears in verbose output. Skipped notices clear the progress display before printing.

Completion reads generated executable-to-theme mappings rather than guessing from suffixes. Startup reads published names instead of discovering palettes. Bash/Zsh refresh registrations at the next prompt; Fish and PowerShell reload them when their command fingerprint changes. Obsolete Dots registrations are removed where supported, preserving other providers. Mixed Fish registrations and retired PowerShell registrations remain inert instead of erasing another provider. Open a new shell after updating the completion adapter source; subsequent command refreshes use the loaded adapter. See the [generated command data contract](specification.md#implemented-theme-palette-and-command-metadata).

Optional regular `logo.txt` files appear only above human help/usage. Flavor help
prefers the variant's file, then its family file. Catppuccin's artwork lives at
`themes/catppuccin/logo.txt`. Artwork with embedded ANSI foreground/background colors keeps its own SGR
colors and formatting; only logos without embedded colors use the addressed
palette. Plain output strips styling. Other terminal control sequences are not accepted as
artwork. Scalar queries, previews, initialization and completion never include logos.

`palette.toml` alone is enough for discovery, previews and native queries. Its
supported syntax is flat named `#RRGGBB` assignments with quoted strings and
comments; duplicate keys, unsupported TOML and invalid colors fail validation.
For activation, recognized semantic names and `[roles]` mappings in metadata
must resolve background and foreground; existing Dots defaults fill other roles.
If `colors.toml` exists it remains authoritative for application colors. Both
bundled and installed palettes use these rules. Pywal retains its explicit export
reader. Legacy family flavor links remain readable as a fallback when a variant
has no native palette file.

Zsh and Bash source the Dots shell adapter directly and load the published theme.
`set_theme`, `change_theme` and `has_theme` remain compatibility helpers.
`theme` is an executable command; use `theme init --shell zsh` for generated shell
code. The old `themes/bin` wrappers have been removed; generated family commands
use the published command directory. Catppuccin-specific startup snippets are no longer sourced.

## Flat themes and templates

Selectable variants live at `themes/ID/`, normally with `colors.toml`, `theme.toml`,
optional native `palette.toml`, and `backgrounds/`. There are 33 flat variants plus
the dynamic `pywal16-current` selection (34 bundled selections in total).
The flat variants include the previous palette variants and Omarchy imports, merging six overlaps.
Overlapping semantic colors use Omarchy's appearance. Its Rosé Pine import is Dawn;
Main and Moon remain separate. Import provenance and license text are retained beside
the themes and under `default/themed`. Background assets are bundled (54.6 MB across 92 files).

`colors.toml` is the shared application palette: quoted `#RRGGBB` assignments plus
optional `mode = "light"` or `"dark"`. Foreground/background are required; ANSI and
semantic roles are resolved from supplied keys with deterministic fallbacks. No
TOML is executed. Desktop-only Omarchy gradient decorations are inert. The native
`palette.toml` retains upstream names for the legacy color-query API. Compatibility
family `flavors/*.toml` files link to these native palettes. Edit `colors.toml` to
change shared application appearance, then publish again with `set` or `refresh`.

Templates under `default/themed/*.tpl` render into a fresh generation. Literal
`{{ color }}`, `{{ color_strip }}` (hex without #) and `{{ color_rgb }}` (comma-separated
RGB) are supported; unresolved variables refuse publication. Personal templates in
`themed/` inside the resolved profile override bundled templates by filename.
A trusted bundled theme's explicit application file takes precedence over both.
Downloaded themes contribute colors and backgrounds only. Templates never evaluate
shell substitutions, Lua or hooks. Outputs include Kitty, Termux, tmux, btop, bat,
Yazi, Codex, Pi, Vivid, FSH, eza, Leaf and Television data; Zsh/Fish and Neovim data come from the palette generator.

The [mdcat configuration](../config/mdcat/config.toml) uses `base = "auto"` for dark/light detection and ANSI color names for its overrides. Its colors follow the terminal palette, so the terminal must have the Dots theme applied; mdcat does not read the published Dots palette directly. Existing heading markers, alert labels and text styles are preserved. Code-block highlighting continues to use mdcat's `BAT_THEME` integration. Explicit `--theme` or `MDCAT_THEME` selections override the base, with config style overrides still applied on top.

`fzf.sh.tpl` supplies FZF colors to published Bash/Zsh and Fish initialization.
Bash and Zsh refresh them at the next prompt; Fish users can explicitly load
`dots theme init` output for their shell. Running FZF processes retain their
existing environment. Personal templates override the defaults, and a bundled
`fzf.sh` application file takes precedence over both. Refresh tracks these edits.
Zsh completion and fzf-tab file colors resolve `LS_COLORS` at each completion, rather
than retaining startup colors. After updating the shell adapter or completion
configuration itself, open a fresh shell or reload your shell configuration once.

The FZF template accepts one `export _FZF_COLORS_="..."` assignment (including
backslash-newline continuations), blank lines, comments, and the optional exact
`export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"` line. Colors
must be `#RRGGBB`, `-1`, or ANSI indices 0–255, optionally combined with style
attributes such as `regular`, `bold`, `strip`, `italic` and `underline`. Selectors
use literal lowercase names, hyphens and plus signs. Other statements or malformed
values refuse publication. Dots parses this file as data; it never sources it.

Shell initialization preserves the original FZF options and replaces its generated
color option on repeat loads. Dots' Bash/Zsh adapters also preserve configured bindings
and preview settings. Published template colors and the Dots shell adapter replace the Catppuccin
startup snippets; mdcat follows its terminal-palette configuration. Older generations and session-only
`set_theme ID` retain the existing FZF behavior. FZF needs no app connector. Bash/Zsh use their native prompt hooks; Fish remains explicit.

`gum_env.sh.tpl` renders to `gum_env.sh` under the active theme path. It exports
all 116 Gum color variables directly in Bash or Zsh, without Lua or Hilbish.
Interactive Bash/Zsh startup automatically sources the readable published file
at `${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh`.
Missing files are optional; loading needs no Gum executable or theme regeneration.
Both shells reload it through their published-theme refresh hooks and configuration reloads. Publication itself never
executes the artifact. Personal `gum_env.sh.tpl` templates and bundled
`gum_env.sh` overrides follow the same rendering precedence as other app files.
To publish and explicitly load the current colors:

```bash
dots theme refresh
source "${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh"
```

The explicit source command also updates an already-running Bash session immediately.
Bash and Zsh pick up published generation changes at their next prompt. Session-only
`set_theme ID` calls do not load a different Gum artifact. Noninteractive startup,
CLI data paths and generated `dots theme init` output do not source this file.
Already-running Gum processes retain their environment. The generic Gum Style
exports include `FOREGROUND`, `BACKGROUND`, `BORDER_FOREGROUND` and
`BORDER_BACKGROUND`; automatic and explicit sourcing set these alongside `GUM_*` variables.
Sourcing runs trusted user-owned shell configuration, including any overrides.
The shell template replaces `gum_env.lua.tpl`; existing personal Lua templates
or bundled Lua overrides are not converted. Move custom color assignments to
`gum_env.sh.tpl` or `gum_env.sh` using `export NAME='#RRGGBB'` syntax.
This consumer targets Bash/Zsh; Fish and PowerShell need their own export syntax.

The bundled `bat.tmTheme.tpl` adapts 186 Catppuccin reference rules and adds seven
generic diagnostic/diff fallbacks, covering language-specific, Markdown and diff
scopes. It preserves reference ordering, explicit style resets and font styles,
while colors follow the selected Dots palette.
Comments and punctuation use `muted`, selection and line highlights use opaque
`selection`, and diff headers use `blue`. Inserted/deleted/changed diff text follows
resolved Git colors, including overrides; `reset` uses the theme foreground.
Mauve maps to `accent`, pink to `magenta`, peach to `orange`, green to `bright_green`,
maroon/flamingo to `bright_red`, rosewater to `bright_foreground`, sky to `bright_cyan`,
sapphire/blue to `blue`, and lavender to `bright_blue`; remaining hues use their named
Dots counterparts. Subtext uses `light_foreground`. Some reference shades therefore
share a Dots color. Font attributes depend on consumer support; a stored declaration
does not establish that every application renders it. Bat disables italic output by
default; `bat --italic-text=always` enables it when supported by the terminal.
Its rendered `bat.tmTheme`
is also copied to `yazi/tmtheme.xml` in the same generation; `yazi.toml` becomes
`yazi/flavor.toml`. The Yazi `flavors/dots.yazi` connector points to that generated
`yazi` directory, so both applications share the syntax theme. Edit the template
and run `dots theme refresh` to publish changes; generated files are replaced on
publication. Personal templates and bundled application overrides retain the
precedence described above.

### Custom Bat syntaxes

When Bat is installed, theme publication and setup build a private cache containing
the generated Dots theme, Bat's built-in languages and your custom
`.sublime-syntax` files. Dots asks Bat for its `--config-dir` before staging the
build, so `BAT_CONFIG_DIR` takes precedence and Bat's native platform default is
used otherwise. `BAT_CONFIG_PATH` selects the configuration file independently;
it does not select the syntax directory.

Put custom definitions beneath that directory's `syntaxes/` and run
`dots theme refresh` after adding, editing or removing them. Nested directories
and linked configuration/syntax directories or files are supported. Dots stores
ordinary file snapshots under the new generation's `bat-source/syntaxes/` and
compiles them into its `bat-cache/`. Existing generations keep their snapshots;
the normal Bat configuration and cache remain intact. Bat and the Git Delta
integration use this generated cache through the existing shell exports and
pager configuration. Other apps sharing the tmTheme do not automatically gain
Bat's custom language definitions.

Explicit publication/setup detects syntax content changes even when file size
and modification time stay the same, as well as additions, removals, source-path
changes and Bat compiler changes. Startup and prompt refresh do not scan syntaxes
or invoke Bat. An unchanged explicit refresh reuses the complete generation.
Broken links, directory cycles, unreadable or invalid syntax definitions, failed
compilation and input changes during preparation prevent activation and retain
the previous generation. Reads are limited to 2 MiB per syntax, 64 MiB total,
16,384 directory entries and 64 directory levels; `.git` contents are excluded.

```bash
dots theme list
dots theme show nord
dots theme color accent --theme catppuccin-mocha
dots theme dir nord
dots theme set nord --dry-run
dots theme set nord
dots theme current
dots theme refresh
dots theme switcher                 # Gum, FZF or a plain terminal menu
```

`set ID` publishes colors only. `--background` additionally requests an explicit
wallpaper action after successful publication; wallpaper failure leaves colors
selected. `--dry-run` prints the selection, publication path and planned connectors
without creating state. `refresh` rebuilds changed inputs and retries available app
reloads even when generation inputs are unchanged. `init [--shell bash|zsh|fish]`
prints sourceable initialization. Theme IDs complete from local data on Tab.

## Interactive theme switcher

`dots theme switcher` requires terminal input and output. It prefers fullscreen
FZF with the prompt/list at the top and a visible live palette preview below,
occupying 70% of the height. Hovering shows the theme's semantic colors and hex
values via `theme show`, with a syntax sample and exact theme foreground/background when terminal color policy allows them. FZF preview rows fill the pane width and unused height; terminal-global colors are unchanged.
Browsing never applies a theme. Without FZF it uses `gum filter`, or a numbered
menu when neither tool is available or `TERM=dumb`; these fallbacks show the palette
after selection. Backends are chosen once per invocation; selector failures never
launch another backend. FZF ignores inherited
`FZF_DEFAULT_OPTS` and `FZF_DEFAULT_OPTS_FILE` so user bindings cannot bypass the
single-selection interface or Dots presentation controls. It reads the published
`$XDG_STATE_HOME/dots/current/theme/fzf.sh` (default
`~/.local/state/dots/current/theme/fzf.sh`) through the shared literal color parser,
not by sourcing shell code, and supplies its colors explicitly to FZF. Unpublished
theme edits and stale shell color variables do not affect the picker. Missing
published colors leave FZF defaults; malformed color data refuses selection.
`NO_COLOR` and Dots color controls still apply, including explicit `always` precedence.

After selection, Dots shows the palette and offers **Back**, **Apply** and **Cancel**,
using Gum when available (even after FZF browsing), otherwise a numbered menu.
Back is the default. Only Apply invokes the existing `set ID` publisher and app
reloads; no wallpaper change is requested. Back returns to the catalog, and Cancel
exits successfully without changing state. Selector output must match an offered
ID, and preview failure prevents publication. The plain menu accepts a numbered
choice, Enter for the indicated default, and Escape or Ctrl-D to abort.

Explicit Cancel exits 0; plain-menu Escape/EOF and Ctrl-C exit 130. Gum 2.0 returns
1 for Escape as well as runtime errors (Escape leaves filter input first, then
another Escape quits); Dots preserves this ambiguity. Other selector failures,
invalid selections, empty catalogs and noninteractive calls exit 1. In scripts use
`dots theme list` and `dots theme set ID` instead. Gum widgets honor inherited Gum
colors and Dots color/icon controls; the switcher does not source `gum_env.sh`.

## Presentation

`dots theme` and `dots theme bg` show colored help with subcommand descriptions,
derived from the same static metadata as completion. In terminals, `list` marks the
current theme and shows a count, `show` displays true-color swatches beside hex
values, `set --dry-run` formats the planned paths, and background listings show
readable names/paths. Successful wallpaper actions report the chosen image.
Theme operations use the existing success/error styles.

Automatic color honors NO_COLOR, TERM and the output stream. Override it with
`dots --color=always theme show nord` or disable decoration with
`dots --color=never --icons=never theme list`. Forced color/icons select the human
view even when redirected. Unforced piped listings retain their plain formats.
`current`, `dir`, `color`, `bg current` and `init` retain their machine-consumable
values under every presentation setting; explicit ANSI color formats remain
intentional ANSI output. Native palette queries use the same output policy.

## Application connections

The stable path is `${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme`, a symlink
to a complete generation. Kitty includes `~/.local/state/dots/current/theme/kitty.conf`
and a local `dots-theme.conf` connector for nondefault XDG state roots. Tmux uses its
local connector. Btop selects `dots.theme`; Yazi selects the `dots` flavor. Bat reads
the generated `Dots` theme and per-generation cache through shell initialization.
Existing app settings and Neovim transparency remain in their source configurations.

On selection, fixed connector links are created only for configured applications:
Kitty/tmux `dots-theme.conf`, btop `themes/dots.theme`, Yazi `flavors/dots.yazi`, and
Termux `~/.termux/colors.properties`, Pi's `themes/dots.json`, and Codex's
`themes/dots.tmTheme`, Vivid `themes/dots.yml`, FSH `dots.ini`, eza `theme.yml`, Television `themes/dots.toml`, and Leaf `themes/dots.toml` plus `themes/dots.tmTheme` (see below). Existing regular files or symlinks are saved in
the generation's connector journal before replacement; real directories are refused.
Parent application directories must exist. If an application directory itself is
linked into a repository, the connector lives in that source directory. It is
machine state, not a configuration to commit. No generic files installer is involved.

Termux settings reload when available; an existing tmux server reloads the generated
colors; Kitty remote control is used only when KITTY_LISTEN_ON is supplied. Reload
failures report that colors were published and can be retried with `refresh`. Apps
without a running reload adapter pick up the files through their normal startup.
No terminal/editor process is restarted and no plugin or package is installed.

### eza

`default/themed/eza.yml.tpl` generates `eza.yml`, adapting the categories and bold permission attributes from `config/eza/themes/catppuccin-mocha-mauve.yml` to the selected semantic palette. SELinux colors use `security_context.selinux`. Git states use resolved shared Git roles, including user `file-colors.toml` overrides; `git_<role>_eza` tokens translate `reset` to eza's `default` foreground. Both branch categories use the branch role, and type changes use the modified role. The supplied reference remains available as a separate theme.

Publication connects an existing eza directory's `theme.yml` to the active generation's `eza.yml`. Directory resolution is `DOTS_APP_EZA_CONFIG`, then `EZA_CONFIG_DIR`, then `${XDG_CONFIG_HOME:-$HOME/.config}/eza` on Termux/Linux/WSL or `%APPDATA%/eza` on native Windows. The fallback when APPDATA is absent is `~/AppData/Roaming/eza`. Paths must be absolute without control characters or `.`/`..` components; no tilde expansion is performed. `DOTS_APP_EZA_CONFIG` changes Dots' destination only: set eza's `EZA_CONFIG_DIR` to the same location when using that override.

Existing files and symlinks are backed up through the publisher journal; real directories at `theme.yml` are refused. Normal publication creates no eza directory, requires no eza executable, and does not restart a process. Subsequent eza commands read the theme. The generated repository connector is ignored by Git. A trusted bundled `eza.yml` override takes precedence over personal `themed/eza.yml.tpl` inside the resolved profile and the default template, matching other app artifacts; native Dots configuration uses its platform config root.

Dots leaves LS_COLORS, EZA_COLORS and aliases unchanged. As described in the [upstream theme guide](https://github.com/eza-community/eza-themes#readme), these environment colors override theme file colors, with EZA_COLORS taking precedence over LS_COLORS. Native Termux eza acceptance and pending Windows checks are recorded in [testing](testing.md#eza-theme).

### Vivid and Fast Syntax Highlighting

`default/themed/vivid.yml.tpl` and `default/themed/fsh.ini.tpl` generate `vivid.yml`
and `fsh.ini` in each published generation. Both follow the shared palette and the
normal template/override precedence. With the existing config directories present,
publication connects `${XDG_CONFIG_HOME:-$HOME/.config}/vivid/themes/dots.yml` and
`${XDG_CONFIG_HOME:-$HOME/.config}/fsh/dots.ini` through the same backup journal.
These machine-local links are ignored when config directories link into this repository.

Checkout setup installs the FSH directory and connector even on a fresh clone;
the tracked `config/fsh/README.md` preserves its source directory. Theme refresh
keeps the existing-directory opt-in rule for standalone app connectors. Both
setup and refresh verify required generated outputs before reusing a matching
input fingerprint, and validate new outputs before publication. Missing or
nonregular artifacts trigger a new generation without editing the old payload.

Directories use blue, executables and shell commands green, links/options/escapes
cyan, ordinary files and paths foreground, comments and unimportant files muted,
source files and archives yellow, configuration files and numeric syntax orange,
and media and shell keywords magenta. Broken links and syntax errors use `error`.
FSH path separators inherit the surrounding path style, including blue and bold for directories; the default template leaves `pathseparator` empty. FSH strings use `bright_green`, matching the shared bat syntax template. Special
permissions and devices have separate styles using the same palette. Vivid's
filetype database supplies extension and filename coverage; a custom database
continues to control classification.

After `dots theme refresh`, open a new shell or reload the shell configuration once
to load the updated adapters. All shell adapters read the published `ls_colors`
artifact; Bash/Zsh update it at the next prompt after publication. Completion and
fzf-tab consume that value. Vivid generation happens during publication, so shell
startup does not run Vivid for new generations. `vivid generate dots` remains
available through the connector. Without Vivid, publication supplies basic file
types and explicit suffixes. A present but failing Vivid aborts publication and
retains the previous generation. Older generations and session-only selections
retain their compatibility fallback. FSH is a Zsh-only integration.

Generated font styles support older Vivid parsers through scalar compatibility
mode; Vivid 0.10+ retains combined category attributes. Setup/publication emits
one compatibility notice on stderr, while exact core and explicit suffix styles
remain intact in the final LS_COLORS. Custom templates retain precedence and are
not rewritten. See [Vivid compatibility](file-colors.md#vivid-compatibility) for
the selection order, diagnostics and recovery commands.

FSH's native INI loader builds validated theme data in the Dots Zsh cache. The
adapter saves a regular copy to `$FAST_WORK_DIR/current_theme.zsh`, so FSH loads
Dots directly at the next startup, before the Dots hook. Both lines from
`fast-theme --show` report `dots`. After plugin initialization and on published
theme changes, the adapter checks for updated colors and saves them atomically;
identical copies are left untouched. The configured `FAST_WORK_DIR` is retained.

FSH failures identify unavailable generated data, loader/cache compilation or
startup-cache persistence, and show the relevant path and repair action. The
same failure is reported once per generation in a shell; success resets that
suppression. A missing artifact retains last-good saved colors when available.
Explicit session-only palettes retain their fallback without a setup warning.
No theme generation or installation runs during startup or prompt refresh.

Before replacing a non-Dots startup selection, the adapter preserves its script
and compiled companion (including symlink identity) in a private
`$FAST_WORK_DIR/.dots-theme-backup.XXXXXXXX` directory. It invalidates stale
`current_theme.zsh.zwc` code so an older compiled selection cannot override the
new source. Directory conflicts and preparation failures refuse replacement.
Backups are retained; restoring one requires disabling automatic Dots FSH loading
first, otherwise a later successful theme load will save Dots again.

Explicit FSH overlays remain in the work directory and are reapplied. Secondary
theme styles are included in the saved script; the default empty `secondary`
keeps nested command substitutions and `eval` expressions on the same palette.
Malformed input keeps the previous theme and reports an error. Missing current
artifacts and session-only palette selections retain the last successfully saved
Dots colors without overwriting the startup file. The saved script works even if
the separate Dots build cache has been removed. Neither integration installs
dependencies.

### Codex and Codex-Termux

Codex uses the shared `default/themed/bat.tmTheme.tpl`, including its normal
personal-template and bundled-theme override precedence. No separate syntax
palette or duplicate template is maintained. When
`${CODEX_HOME:-$HOME/.codex}/themes` exists, publication links `dots.tmTheme` there
to the stable active `bat.tmTheme`, also used by bat and Yazi. `CODEX_HOME` must be
an absolute path without control characters or `.`/`..` components; a literal
`~/` is not expanded. Supply the same home to Dots and Codex.

For first-time setup:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/themes"
dots theme refresh
```

Select **dots** in Codex's `/theme` picker, or set `theme = "dots"` under `[tui]`
in that Codex home's `config.toml`. The publisher never edits this setting or
creates Codex directories. It backs up existing connector files/links, refuses
real directories, and retains the connector on unchanged refresh. Future theme
publications change the shared artifact; open a new Codex session to load it.
Automatic reload inside running Codex sessions is not guaranteed.
Custom-theme discovery and selection were verified with Codex 0.162.1 in an
isolated native Termux session; visual contrast across all palettes remains a
manual check.

Codex-Termux and Neovim's Codex launcher inherit the same Codex configuration;
there is no wrapper-specific theme setting or launcher override. The existing
Neovim OSC foreground/background adapter remains responsible for terminal color
queries. Custom `.tmTheme` files control code-block and diff syntax highlighting,
not every TUI widget or desktop-app appearance. See the
[official Codex theme documentation](https://learn.chatgpt.com/docs/cli-customization).

### Pi

`default/themed/pi.json.tpl` renders a custom Pi theme named `dots` to `pi.json`
in each generation. It maps UI, Markdown, syntax and export colors to the shared
palette, including light/dark appearance. Panels use `lighter_background` rather
than fixed Mocha tints. Personal `pi.json.tpl` templates and bundled `pi.json`
overrides follow normal precedence and invalidate the publication fingerprint.

When `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/themes` exists, publication links
`dots.json` there to the active generation's `pi.json`. The agent directory must
be absolute, without `.`/`..` components; `~` and `~/` are expanded. It is not an
XDG config path. No Pi executable is required, and no settings file is rewritten.
For first-time setup with the default directory:

```bash
mkdir -p ~/.pi/agent/themes
dots theme refresh
```

In Pi, run `/reload` and select **dots** under `/settings` → **Theme**. Alternatively,
set `"theme": "dots"` in Pi's settings. With a custom agent directory, create its
`themes` subdirectory and supply the same `PI_CODING_AGENT_DIR` to both applications.
Missing themes directories are skipped, not created by the publisher.

Pi watches its own themes directory, not Dots' active-state pointer. On changed
publication, Dots atomically renews the Pi connector through the existing backup
journal, notifying Pi to hot-reload the selected `dots` theme. Unchanged refresh
preserves the connector and generation. Other selected Pi themes are unaffected.
The installed Pi 0.99.1 loader/watcher was verified in an isolated Termux fixture;
older versions may require `/reload`. No live Pi process is restarted.

## User themes and wallpapers

```bash
dots theme install https://example.org/owner/theme.git --name my-theme
dots theme update my-theme
dots theme update --all
dots theme remove my-theme
dots theme bg list
dots theme bg next
dots theme bg set /absolute/image.png
dots theme bg set /absolute/image.png --lock-screen
dots theme bg current
```

Git themes live in `${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes/ID`. Installation
accepts HTTPS/SSH Git sources, validates color data in a staged clone, and never
selects automatically. Updates require a managed, clean checkout and fast-forward
history. Removal refuses the current theme. Updates/removals retain prior sources
under `.archives`; `.transactions` records interrupted publication for recovery on
the next lifecycle action. Git hooks and global/system Git configuration are disabled
for these operations. Downloaded scripts/configuration are never sourced. Manual
bundled/user ID collisions refuse selection. Recovery is bounded to theme sources;
there is no generic Git repository manager.

Background discovery includes the selected theme's `backgrounds/` and personal
`~/.config/dots/backgrounds/ID` (with XDG_CONFIG_HOME respected). `next` cycles images;
`select` reapplies the remembered image or the first; `switcher` uses optional fzf.
The background picker uses fullscreen FZF with the prompt and list at the top,
overriding inherited height, layout, margin and padding settings.
It displays and searches only basenames without their final
extension, retaining full paths internally (including for duplicate labels).
Optional Chafa renders the hovered image as terminal symbols in a bottom
preview occupying 70% of the height, scaled to the largest fit while preserving
aspect ratio (no stretching or cropping), and explicitly shown by default even when
inherited FZF options hide previews. Without Chafa, selection works without a
preview. Hovering does not apply the wallpaper; accepting a selection does.
Cancellation or an invalid selection makes no wallpaper/state changes. Raw
`bg list` and `bg current` output retains full paths.
PNG, JPEG, WebP and BMP are supported. Android uses `termux-wallpaper` (Termux:API),
Wayland uses `swww img`, and X11 uses `feh`; adapters are capability-checked and have
a 15-second timeout. `--lock-screen` is Android-only and does not replace the stored
home-wallpaper selection. WSL and video wallpapers are unsupported. Native PowerShell provides a Windows desktop wallpaper adapter; see [native PowerShell](powershell.md).
A failed adapter preserves the previous successful record, but an external API may
have changed the device before failing; prior wallpapers are not backed up. Actions
are explicit and journaled, never automatic consequences of ordinary palette set.

## Native palette compatibility


| Family | Flavors (default first) |
| --- | --- |
| `catppuccin` | `mocha`, `macchiato`, `frappe`, `latte` |
| `tokyonight` | `night`, `storm`, `moon`, `day` |
| `rose-pine` | `main`, `moon`, `dawn` |
| `kanagawa` | `wave`, `dragon`, `lotus` |
| `gruvbox` | `dark`, `light` |
| `pywal16` | `current` (imported generated colors) |

Fixed palettes retain upstream color names. Each fixed family has `SOURCE.md`
and upstream license text beside its metadata. Pywal16 has no fixed palette: see
[its import contract](#pywal16-import).

## Shared discovery

`lib/dots/themes/discovery.bash` is the data-only reader shared by listing, the switcher, current-ID queries, native palette views and completion. Loading it performs no scans or command dispatch; discovery happens only when requested. Flat listing validates and deduplicates IDs, while completion retains its existing literal filename hints, including duplicates and invalid names. These hints do not authorize selection: the loader still rejects invalid IDs and duplicate bundled/user themes. Native flavor views retain metadata validation. No discovery cache or shell-startup scan is added.

## Native palette queries

`dots theme list --families` lists native family names. `dots theme list --flavors FAMILY` lists that family's flavor names; these two filters are mutually exclusive. Plain redirected output is one identifier per line. Human views use the shared theme presentation. Pywal16 flavor discovery does not require generated input. Unknown families fail with a diagnostic.

`dots theme show ID --native` previews upstream palette names and values. `dots theme color COLOR [FORMAT] [--theme ID] --native` queries that map exclusively. Without `--native`, color queries prefer application semantic colors, falling back to native names. This distinction matters when the same name has different upstream and application values. Generic themes use their existing engine palette representation. Formats and scalar bytes remain unchanged, including explicitly requested ANSI formats.

## Migration from plural commands

`dots theme` owns collection management: `list`, `switcher`, `install`,
`update`, `remove`, and `plugins`. The old `dots themes` routes are removed;
replace that command prefix with `dots theme`. Bare `dots theme` retains its
current-theme summary; `dots theme --help` shows the unified command family.

Use `theme` for a current-theme summary, `theme current` for the plain full ID,
and `theme color`, `show`, `set`, `refresh`, or `bg` for current-theme operations.
`theme show` defaults to the selected theme; an explicit ID previews another.
Its human view shows all resolved named and terminal colors, file types, MIME
rules and configured extension rules using the shared `theme colors` tables.
The source is labeled because `show` reads configured sources while `colors`
defaults to the published snapshot. Native previews retain their native-only
scope. See [human color views](file-colors.md#human-color-views) for details and
redirected-output compatibility.
`theme list` and `dots theme list` list the same selectable IDs; `--families`
and `--flavors FAMILY` provide the corresponding filters. Full IDs remain the
selection interface. Family commands retain native flavor queries and explicit
`set`. Internal callers use `dots-theme-current`; the old `current_theme`
wrapper has been removed.

Exit statuses remain 0 for success, 1 for data/publication errors, and 2 for invalid arguments. Diagnostics use stderr. Initialization defaults to Zsh and remains sourceable with `--shell bash|zsh|fish`.

Each legacy family has `themes/IDENTIFIER/theme.toml` and `flavors/FLAVOR.toml` links. Flat variants own the native data in `palette.toml`.
The root can be selected with `DOTHEMES`, then `THEMES`; otherwise it is relative
to the installed engine. Family identifiers allow internal hyphens (`rose-pine`);
flavor identifiers use `[a-z][a-z0-9_]*`. Native color keys use
`[a-zA-Z_][a-zA-Z0-9_]*`, including Kanagawa's `sumiInk3` and Rosé Pine's `_nc`.
Persisted `theme-flavor` identifiers split at the final hyphen.

A flavor contains only ordered color assignments:

```toml
rosewater = "#f5e0dc"
blue = "#89b4fa"
base = "#1e1e2e"
```

The example is abbreviated; Catppuccin requires its existing 26 named colors.
Its flavors are Mocha, Macchiato, Frappé (`frappe`), and Latte.

Metadata separates names and integrations from color values:

```toml
name = "Catppuccin"
default_flavor = "mocha"
[roles]
background = "base"
foreground = "text"
muted = "overlay0"
accent = "mauve"
selection = "surface1"
error = "red"
warning = "yellow"
info = "blue"
hint = "teal"
[integrations]
nvim = "catppuccin"
vivid = "catppuccin"
```

All nine roles are required and must reference colors in the selected flavor.
Optional `[roles.FLAVOR]` tables override individual mappings, useful when a light
variant has different native names. Querying, previewing and initialization discover
theme files without hardcoded family lists. Native families use their matching Neovim adapter. Other flat variants use the
built-in generic highlight adapter without executing downloaded code. Adding another app integration is an
explicit adapter change; metadata cannot run commands. `vivid` records the integration
identity for compatibility. Published generations use the shared Vivid Dots template
for every palette. Old generations and session-only Catppuccin selections retain
their named Vivid theme and inherited-entry fallback. New generations follow the
[file-color publication contract](file-colors.md).

The supported TOML subset includes bare keys, double-quoted strings without
escapes, single-quoted literal strings, blank lines, full-line/trailing comments,
and the `roles`, `roles.FLAVOR` and `integrations` tables in metadata. CRLF is accepted. Colors
must be six hex digits prefixed with `#`. Duplicate keys/tables, unknown metadata
keys, missing roles, control characters, arrays, numbers, multiline strings,
escapes and other unsupported TOML constructs fail with file/line diagnostics
where applicable. Palette input is never sourced or evaluated.

## Pywal16 import

Generate a palette using your existing pywal16/wal installation, then publish it:

```bash
dots theme set pywal16-current
# After generating another wallpaper palette, run the same command again.
```

`themes/pywal16/theme.toml` declares `source = "pywal16"`; the comment-only
`flavors/current.toml` is a discovery marker. Input is `DOTS_PYWAL_FILE` when set,
otherwise `$PYWAL_CACHE_DIR/colors.sh`, otherwise
`${XDG_CACHE_HOME:-$HOME/.cache}/wal/colors.sh`. The reader accepts literal,
single- or double-quoted `#RRGGBB` assignments for `background`, `foreground`,
`cursor` and `color0` through `color15`. All 19 are required and unique. It rejects
NUL, exports over 64 KiB, malformed recognized assignments, and missing colors;
other export lines are ignored. It never sources shell/Vimscript, executes `wal`,
changes wallpapers, or watches the cache.

Missing/invalid input refuses publication before state creation. Source changes
during generation refuse the switch. Published snapshots keep working after the
cache changes or disappears. `show`/`color` query the current export, while `init`
loads the published selection. Bash/Zsh/Fish can list and complete the `current`
flavor without an export; color completion requires valid input.

## Selection and generated data

Read-only selection and startup use the published generation, otherwise
`DOTS_THEME_DEFAULT` from [Dots settings](shell-environment.md). Legacy `.default`
and `.theme` files are not read or imported. `DOTS_THEME_SELECTION` remains an
explicit session-only override used by `set_theme ID`.
`change_theme ID` persists through `dots theme set`, then updates the calling Zsh.

State lives in `${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes`. Its legacy `current`
token is maintained for compatibility; readers prefer the stable sibling
`dots/current/theme` link. Publication journals restore both pointers on failure. Each `generations/g.*` directory contains its
selection, fingerprint, `palette.json` (schema 1), `init.zsh` (also Bash compatible), `init.fish`,
previous-generation token, and journal status. Readers load one complete generation.
The JSON carries theme, flavor, ID, adapter, mode, native palette values and resolved hex `roles`; it contains no executable
Lua or machine paths. Neovim uses its JSON decoder, not a second TOML parser.

Generations are immutable snapshots. After editing palette files, run `set` again
to publish the changes, including when keeping the same theme/flavor. The fingerprint
covers native flavor files, selected semantic palette and app data, personal/default
templates, metadata and Bash generator modules, plus the input export for pywal16.
Background images do not invalidate palette generations. Unchanged selection
and fingerprint, with all connectors correct, cause no changes to the generation or active pointer. `current` and initialization read the published snapshot even if palette source
files are temporarily invalid. Explicit palette queries read the source files. Previous
complete generations are retained; no automatic pruning or general undo command
is provided. To return to a previous flavor, use `set` with that flavor.

Legacy initialization caches live under `${XDG_CACHE_HOME:-$HOME/.cache}/dots/themes`.
These are disposable generated data, keyed by content and shell. Publication uses
a temporary file and rename. Bash arithmetic handles integer conversions; AWK
batches fractional conversions for each palette while preserving legacy rounding.
Basic help and hex/RGB queries do not require AWK. Initialization needs AWK and
`sha256sum`; switching additionally requires `flock`, `sync -f`, and standard
file utilities. Dependencies are required only on the paths using them.

## Shell and Neovim behavior

Generated family commands retain the positional/flag query interface, formats,
raw/array output and completion generators for Bash, Zsh and Fish. Current-theme
queries use `theme color`; the bare command previews the selected palette. `--all` queries every flavor;
`init` emits the selected palette's initialization. Catppuccin's fixed
flavor-prefixed arrays remain available. Generic initialization exposes
`dots_palette` and `dots_roles` associative arrays in Bash/Zsh; Fish receives
`dots_color_NAME` and `dots_role_NAME` variables plus `THEME` and `FLAVOR`.
Bash/Zsh initialization also exposes a global associative array for every current-theme color: `${blue[hex]}`, `${hint[esc]}`, `${background[rgb]}`, and so on. It combines native palette names with the resolved Dots template colors and roles; resolved values win on overlap. This includes terminal aliases (`color0` through `color15`) and native extras such as `rosewater` or `blue1`, but excludes `mode`. Thus `${cyan[hex]}` can differ from `${dots_palette[cyan]}`: the former follows the template palette, while the latter retains the native palette API.

Each color array contains `name`, `hex`, `rgb`, `r`, `g`, `b`, `luminance`, `brightness`, `cmyk`, `ansi-8bit`, `ansi-8bit-value`, `ansi-8bit-escapecode`, `ansi-24bit`, `ansi-24bit-escapecode`, and `esc`. Escape fields contain actual terminal foreground sequences. Global Bash/Zsh scalars `$esc` and `$ESC` each contain the single escape character, equivalent to `$'\033'`; `$rst` and `$RST` both contain the SGR reset sequence `ESC[0m`, restoring terminal colors and text attributes. For example: `printf '%sHello%s\n' "${blue[esc]}" "$rst"`, or `printf '%s[31mHello%s\n' "$esc" "$rst"`. Initialization can be sourced repeatedly when these scalars are already readonly with the correct values. The values are calculated during initialization generation and cached, not recalculated on each prompt. Bash requires `${blue[hex]}`; Zsh also accepts `$blue[hex]`.

Switching removes obsolete unprefixed arrays owned by Dots. The first reload from the older Catppuccin initializer uses its palette-name list to remove stale colors. Catppuccin initialization still supplies fixed-flavor arrays such as `${mocha_blue[hex]}` and `${latte_blue[hex]}` with their original values; switching away does not remove them. Fish retains its scalar initialization interface.

Direct array names must start with a lowercase ASCII letter (optionally preceded by one underscore) and contain only ASCII letters, digits, or underscores. Shell special parameters, Dots control names, adapter locals, `esc`, `rst`, and the `_dots_`, `dots_`, `catppuccin_`, `mocha_`, `macchiato_`, `frappe_`, and `latte_` prefixes are reserved. A conflicting color name fails Bash/Zsh initialization and publication before replacing the active generation; rename that palette key. Existing shared color names intentionally occupy global shell variables.

The library-owned shell adapters load published initialization at startup. Native
Fish, Nushell, Xonsh and PowerShell also consume the published `shell.tsv` data;
see [the shell environment contract](shell-environment.md). Bash and Zsh retain
their sourceable initialization. Their prompt hooks check the
published generation with builtins on the unchanged path and reload only when it
changes. Bash compares the active link with the loaded generation directory;
resolving a changed link may invoke readlink once. The hooks preserve the previous
command's status, existing hooks and FZF options; Zsh also retains autosuggestion
styling. Existing Catppuccin shell sources remain in use. Fish receives explicit
initialization output and does not install an automatic theme hook.

The local Anodize.nvim plugin renders shared native and generic palettes in
`config/nvim`. Its source defaults to `~/repos/Anodize.nvim`, overridden by
`ANODIZE_NVIM_DIR`. It reads validated JSON without CLI calls, watches stable state
parents and handles focus/resume. `:DotsThemeReload` delegates to its active-only
reload; after manually choosing another colorscheme, use `:colorscheme anodize`
to return. No old native-adapter focus loader runs alongside it.

Dots owns transparent main windows, opaque floats, terminal-color opt-out,
15% inactive foreground dimming, Mocha exceptions and other personal highlights.
Lualine uses the Anodize palette without layout changes. Dashboard role updates
preserve animation phase and lifecycle. Missing/invalid shared state uses the
plugin fallback initially and retains last-good colors on reload. An unavailable
local plugin reports its path and falls back to bundled habamax. Optional native
plugins remain available for manual selection; they are not Anodize dependencies.
See [Neovim integration](anodize.md#neovim-integration) and the nested configuration
README. No downloaded theme code is executed and no plugin is installed by the
reader or CLI.

Shared sourceable theme helpers live in `lib/dots/themes/shell.bash`; shell
configuration normally loads them through `dots init`.

## Anodize authoring and consumer colors

[Anodize](anodize.md) creates editable themes using the existing flat theme layout and publisher. Saving and applying are separate operations. Published schema-1 `palette.json` includes an additive `colors` object containing normalized named hex colors and ANSI aliases; existing `palette`, `roles`, and `adapter` fields remain available. The publisher fingerprint includes engine source changes, so a subsequent explicit apply creates an updated generation when necessary. No automatic live theme switch is performed by this source update.

## Theme-owned usage colors and file styles

Family help and native palette previews use the addressed theme's explicit
foreground/background. Bare family help follows the active flavor when it belongs
to that family, otherwise the family's default. This changes presentation only;
existing palette-query and activation defaults remain unchanged. Explicit flavors
always choose their own palette. Themed help lines reset styling, wrap on narrow
terminals, and use readable text contrast while preserving actual swatch colors.
`logo.txt` artwork retains its authored SGR colors when it contains ANSI
foreground/background colors; otherwise it receives the theme color. Bold and
reset codes alone do not count as embedded colors. Width checks ignore SGR codes,
and authored multiline styling is isolated with a reset before and after the logo.
Other terminal controls are sanitized; disabled color strips all styling.

`--color=none` aliases `never`; family commands accept the equals form anywhere.
`--color NAME` / `-c NAME` still query palette colors. Raw values, JSON, Lua,
completion and init output never acquire decoration. Plain help remains usable
if the palette is unavailable. See [file colors](file-colors.md) for the new
`theme colors` commands, customization layers, full styles and portable exports.

## Explicit checkout setup

[Checkout installation](installation.md) reuses immutable theme and generated-command preparation, then publishes state pointers and fixed connectors through the shared file Store. Prepared generations carry `staged` status; normal theme recovery leaves them to the owning file journal. The current theme/default is preserved. Fixed app connector definitions are shared through `lib/dots/themes/connectors.tsv`; btop's generated connector is now ignored. Setup creates declared missing parents and suppresses application reloads, wallpaper actions and plugin hooks. Normal theme commands keep their existing publication behavior.

### CLI file-style projection

Theme publication now also writes internal `file-styles.tsv` beside `colors.json`,
`colors.lua` and `ls_colors`. The header is `dots-file-styles<TAB>1`. Subsequent
rows have four tab-separated fields: group, literal key, numeric SGR sequence and
case mode (`-`, `exact`, `fold`). Groups are `type`, `extension`, `mime`, `suffix`
and `default_mime`, in matching-priority order. Suffix case collisions are resolved
by the existing file-style matching policy before publication. The projection is
data, never executable shell source; it does not change export JSON/Lua schemas.
Ordinary CLI views only read published artifacts. A normal refresh supplies the
new projection; older publications remain usable through the documented fallback.

### CLI Git-style projection

Theme publication also writes `git-styles.tsv` atomically with the same generation. Its header is `dots-git-styles<TAB>1`; subsequent rows contain a lowercase role key and numeric SGR sequence separated by one tab. This output name is reserved against custom templates. Git styles use the existing fingerprinted rule inputs. `file-styles.tsv` and LS_COLORS remain independent.

The shared Bash presentation layer lazily reads this bounded regular data file once per colored Git command. It rejects symlinked payloads, oversized data, malformed rows and duplicate keys, and never sources the contents or invokes Python/theme resolution to render a row. Missing roles use terminal defaults. The [Git styles reference](file-colors.md#git-styles) owns the role list and public export interface.

The Dots Yazi plugin exposes live Lua references such as `dots.colors.background`, `dots.colors.git.repo`, `dots.colors.type.dir`, and `dots.colors.mime["image/*"]`. These resolve from the existing `colors.json` publication at setup and refresh; no second Lua template is needed. The existing `colors.lua` export remains available to other Lua consumers. `dots.colors()` and `dots:colors()` still return the loaded palette. Header defaults and per-file Git indicators use shared Git roles; explicit configuration and `th.git` overrides retain precedence. Update remote-installed plugin runtime through `ya pkg`, so its revision and hash remain package-manager owned.

The default `blastoff.toml.tpl` publishes a Starship-compatible Dots palette. `{{ git_colors_starship }}` is a data-only expansion of resolved Git foreground shortcuts into flat `git_*` entries; palette names otherwise match the semantic theme names. The optional [Starship plugin](theme-plugins.md#starship-and-blastoff-starship) merges the palette into existing configuration after publication, including explicit unchanged-theme refreshes. It never replaces module configuration with the template.

### Git and Delta default template

`default/themed/gitconfig.tpl` publishes a theme-only Git include, connected as
`${CONFIG}/git/dots-theme.gitconfig` when the Git config directory exists. The
common Git config includes it after fallback colors; the platform overlay remains
last. Personal settings are not regenerated. See the [Git config guide](../config/git/README.md).

Literal `{{ git_<role> }}` tokens resolve configured Git foregrounds. Their
`_delta` variants translate `reset` to Delta's `normal`. For semantic colors and
Git foregrounds, `<name>_blend_10` and `<name>_blend_25` blend that percentage into
`background`, rounding each RGB channel with integer half-up rounding. A reset
foreground blends as background. These template-only expansions do not change
exported palette namespaces and do not execute expressions. Normal attributes
remain explicit in the template. Unknown tokens still fail preparation.

Prepared generations expose the existing bat cache at `delta-cache/bat`; Git's
Delta commands set a process-local XDG cache root and request Dots syntax. Missing
cache uses the normal Delta invocation. The standard bat cache is never replaced.
Use the [template skill](../.codex/skills/dots-theme-template/SKILL.md) when adding
other default consumers.

## Verbose application output

`dots theme set ID -v`, `dots theme refresh --verbose`, `dots theme refresh --commands-only -v`, and `dots theme switcher -v` add action details on stderr. Standalone `theme` forwarding and family/flavor `set` helpers preserve the flag. The switcher passes it into Apply; selection previews and cancellation remain read-only.

Verbose output shows preparation/render/cache phases, source -> destination links, connector recovery copies retained in generation journals, publication, reload/plugin outcomes and concise unchanged/skipped reasons. Already-current generations are explained without claiming new backups or links. Rollback is reported separately from completed writes. Default output, selector styling, approvals and mutation behavior remain unchanged. Resource colors/icons and progress use the [shared contract](presentation.md#verbose-operations). `set --dry-run -v` describes planned connections without writes; this does not add dry-run support to refresh or switcher. Theme collection downloads/removal, background selection and data-query routes do not gain verbosity.

## Native PowerShell publication

The native frontend provides literal palette queries, theme/family commands, generated `.ps1` commands, native initialization, selection/refresh, source operations and background selection. It shares file-color rendering, semantic presentation, progress, FZF snapshot previews and the guarded file transaction engine. Setup renders without desktop effects; explicit publication may run enabled native hooks and supported app notifications. Windows wallpaper uses its desktop API; Android lock-screen, GTK/Qt and tmux actions retain explicit platform limits. User `.ps1` hooks are native Windows-only; downloaded themes remain inert. See [native PowerShell](powershell.md) for implementation status, state paths and native acceptance requirements.

Anodize-created user themes share the normal user theme root and discovery rules.
Explicit built-in saves and promotion are described in [Anodize](anodize.md#interactive-authoring-and-previews).
Duplicate bundled/user IDs remain errors; promotion moves by default and copies
require a different ID. Saving or promoting does not activate a theme.


### Television

`default/themed/television.toml.tpl` generates `television.toml` with all 19 color fields from the [upstream Catppuccin reference](https://github.com/alexpasmantier/television/blob/main/themes/catppuccin.toml). It uses the selected Dots semantic palette: normal background/foreground, muted borders, accent input/count/matches, blue/yellow/bright-blue results, the shared selection pair, orange preview title, and magenta/green/blue mode badges with background-colored text. `orange` falls back to `yellow` where the palette omits it. Layout, keybindings, channels and preview commands remain editable Television configuration.

Select the generated theme in Television's config:

```toml
[ui]
theme = "dots"
```

Publication links `themes/dots.toml` to the stable active generation's `television.toml`. Both publishers resolve `DOTS_APP_TELEVISION_CONFIG`, then `TELEVISION_CONFIG`, then an absolute `XDG_CONFIG_HOME/television`, then `~/.config/television` on Termux/Linux/WSL or `%LOCALAPPDATA%/television/config` on native Windows (fallback `~/AppData/Local/television/config`). This Windows default follows [Television 0.15.9's implementation](https://github.com/alexpasmantier/television/blob/0.15.9/television/config/mod.rs), rather than the older APPDATA comment in its example config. Explicit destinations must be absolute with no control characters or dot components; tilde expansion is not performed. Dots' override affects only its connector: set Television's `TELEVISION_CONFIG` to the same directory when using it.

The app config directory must already exist. Publication may create its missing `themes` child through the journal, backs up existing `dots.toml` files or links, and refuses real-directory targets and unsafe parents. Rollback removes transaction-created parents only when safe and empty, preserving new user content. The Bash journal records directory identity; interruption before identity is recorded requires manual inspection instead of guessing ownership. The native publisher uses the shared Store's parent journal. No Television executable is required for publication, and no running Television process is restarted. New launches read the generated theme; `[ui.theme_overrides]` retains Television's normal precedence.

Profile-local `themed/television.toml.tpl` templates override the default; trusted bundled `television.toml` files override both. These inputs participate in generation fingerprints. Use `dots theme set ID --dry-run` to preview and `dots theme refresh` to publish the current selection. Native consumer evidence and outstanding platform checks are recorded in [testing](testing.md#television-theme).


## Leaf

`default/themed/leaf.toml.tpl` adapts every UI and Markdown color field from `config/leaf/themes/catppuccin-mocha.toml` to the selected Dots semantic palette. It uses `ocean` as the dark base and `arctic` as the light base; `leaf_base` and `leaf_badge_foreground` are literal renderer tokens shared by Bash and Python. Surfaces use background variants, ordinary text uses foreground variants, highlights use selection/accent, and dark/light status badges retain contrasting foregrounds. Layout, editor and watch settings stay in Leaf's editable config. The reference theme is preserved.

The generated `leaf.toml` selects `syntax = "dots.tmTheme"`. Publication links both `leaf/themes/dots.toml` to the active `leaf.toml` and `leaf/themes/dots.tmTheme` to the existing active `bat.tmTheme`, sharing syntax scopes with bat, Yazi and Codex. Stock Leaf 1.28.2 only supports bundled syntax names and silently falls back for a file path. Use the [custom Leaf build](leaf-build.md) before selecting this template for matching code colors.

Select the generated theme in Leaf's `config.toml`:

```toml
theme = "themes/dots.toml"
```

Both publishers resolve `DOTS_APP_LEAF_CONFIG`, then `${XDG_CONFIG_HOME:-$HOME/.config}/leaf` on Termux/Linux/WSL or `%APPDATA%/leaf` on Windows. Missing APPDATA leaves the Windows destination unmapped, matching Leaf. Explicit paths must be absolute with no control characters or dot components; no tilde expansion is performed. The Dots override changes the publication destination only; arrange for Leaf to read that location separately. The catalog uses `${APP_CONFIG:leaf}` on Windows.

Refresh requires an existing Leaf config root. It may create only its missing `themes` child, recording directory identity and both links in the publisher journal. Existing files and broken links are backed up; directory conflicts and post-write drift refuse replacement or recovery. Both artifacts participate in setup/uninstall and normal publication. No Leaf executable is needed for generation and no running Leaf session is restarted. Open Leaf again to read a refreshed theme; selected external syntax loads once per process.

Profile-local `themed/leaf.toml.tpl` templates override the default; trusted bundled `leaf.toml` overrides both. These files and shared syntax inputs participate in fingerprints. Preview with `dots theme set ID --dry-run`, then publish with `dots theme refresh`. See [verification and platform limits](testing.md#leaf-theme).

## Generated theme files

`dots theme files` inspects the active published generation without generating a theme, refreshing, recovering, editing or reloading anything. It defaults to `list`; standalone `theme files` and native PowerShell expose the same interface.

```bash
dots theme files
dots theme files list --app yazi
dots theme files info bat.tmTheme
dots theme files show yazi/tmtheme.xml
dots theme files show bat-cache
dots theme files show bat.tmTheme --source
dots theme files path bat.tmTheme
dots theme files path bat.tmTheme --resolved
dots theme files check --json
dots theme files check --consumers
dots theme files browse
```

| Action | Arguments and behavior |
| --- | --- |
| `list` | `[--app APP] [--json]`: artifacts, consumers and connection status. The bare group accepts the same filters. |
| `info` | `FILE [--json]`: source resolution, stable and generation paths, consumers, configured destinations, their actual locations through linked directories, and link values. |
| `show` | `FILE [--source] [--raw]`: highlighted terminal text, directory entries, or the current template/override. Regular-file `--raw` and redirected output preserve accepted UTF-8 bytes. |
| `path` | `[FILE] [--source\|--resolved]`: one absolute path; defaults to the stable active directory. `--resolved` returns the captured generation location. `--source` requires a file and cannot combine with `--resolved`. |
| `check` | `[--app APP] [--consumers] [--json]`: inspect artifacts and connections; opt into confirmed consumer failures with `--consumers`. Exit 1 when applicable checks fail; no repair is performed. |
| `browse` | `[--app APP]`: optional shared Gum/FZF/numbered selector with details, highlighted generated/source text or directory entries, Back and Exit. Unavailable source actions are omitted. Requires terminal input/output; re-observes the active generation after interactions. |

`FILE` is a listed generation-relative identifier, including `yazi/flavor.toml` and `yazi/tmtheme.xml`. Completion supplies file and app names without rendering or executing extensions. Application outputs, custom template outputs, shared palette/shell data and derived files are listed. Cache directories are aggregate entries; publication bookkeeping, generated command wrappers, journals and backups are excluded. Missing outputs expected by the current templates or fixed connector definitions remain visible for diagnosis.

Sources are labeled **Source for next refresh**, not historical provenance: retained generations have no source manifest. Current resolution follows trusted bundled overrides, personal templates and default templates. Derived files identify their parent artifact. Generated shared data and caches have no single editable template. Missing source files do not prevent inspecting the published artifact. Direct changes to generated files are replaced on publication; this interface never opens an editor or refreshes automatically.

Fixed connector inspection uses the publisher's platform paths and directory eligibility. `linked` means the destination follows the stable active path; relative links are resolved from their actual parent. `pinned` means a link resolves to the captured generation directly and will not follow future switches. Other statuses are `missing`, `broken`, `points-elsewhere`, `regular-file`, `unavailable` and `not-configured`. Missing optional app directories and unsupported native-platform connectors are informational. Eligible unhealthy connections, missing/unreadable generated artifacts, an app filter matching no artifacts and incomplete inspection make `check` fail. Checks do not compare arbitrary regular-file contents or prove that a running application loaded its theme.

Supplementary connections are discovered only at destinations recorded by completed managed file transactions, when their existing links still refer to a listed active artifact. This finds links such as a separately repaired bat theme without scanning the home directory. Finalized journals do not retain the intended link value, so a removed or redirected supplementary link cannot be reconstructed from those records. Fixed connectors remain independently diagnosable. Discovery is bounded to 512 transaction entries and 4096 operations per record; oversized, unreadable or malformed metadata reports incomplete inspection. No retained file contents are read.

Listings separate artifacts with blank lines, combine each application's connection and evidence, and show destinations underneath. Configuration and inherited-environment evidence appears beside consumer names; detailed reasons and checked paths live in `info`. Unsupported checks retain their integration kind in the listing and an unknown reason in `info`. Runtime scope is explained once rather than repeated on every row. App filters select matching artifacts; details retain other consumers of shared artifacts. An absent generation gives an empty listing, a failed check, and unavailable file-specific queries. Invalid active pointers are reported without following foreign paths. Each request captures one generation; browser actions capture again after user interaction.

Text previews accept only safe regular UTF-8 files up to 64 KiB, refuse binary/possible credential content and special files, and never evaluate generated shell code. Source directory links may resolve to managed sources; source leaf symlinks are refused. JSON and paths are always undecorated; redirected listings are plain even when decoration is forced. JSON schema and exit behavior are defined in [data contracts](specification.md#generated-theme-file-inspection). Native acceptance limits are in [PowerShell](powershell.md).

### Directory and highlighted previews

`show bat-cache`, `show bat-source` and `show delta-cache` list up to 200 immediate children, sorted within the bounded observation, with types and literal link targets. Child links are never followed and binary cache contents are not opened. Empty and truncated results are explicit. When a directory has no editable source, `show DIRECTORY --source` explicitly falls back to the generated directory listing. `--raw` remains a regular-file interface and rejects directories. Redirected directory views are plain, control-escaped listings.

Terminal text previews use optional `bat` (or `batcat`) when Dots color policy enables color and the captured generation has a usable Dots syntax cache. Language detection uses the filename without a final `.tpl`; shared tmTheme/XML files explicitly select XML. The renderer receives sanitized text through stdin, has user configuration and paging disabled, uses the existing captured cache, and is bounded to five seconds of execution and 1 MiB of output. It never builds caches. Missing tools/cache, unsupported syntax, errors or timeouts fall back to plain text. Browser text previews share this behavior. Disabled color stays plain; regular-file `--raw` and redirected output bypass highlighting and remain byte-exact.

### Consumer evidence

Verification reads known, bounded configuration files and values inherited by the inspector; it does not execute applications or hooks. Config reads are limited to 256 KiB, cached only for the current request, and checked for observed changes during reading. It reports selected keys and concise reasons, never unrelated environment or configuration contents.

| Consumer | Evidence inspected |
| --- | --- |
| bat | Inherited `BAT_THEME` and `BAT_CACHE_PATH`, resolving the cache to the captured generation. |
| FZF | Supported literal generated colors and effective literal color options in `FZF_DEFAULT_OPTS`; an options-file override remains unknown. |
| LS_COLORS | Inherited `LS_COLORS` against the generated value. |
| Gum | Supported published literal color assignments against exported values. |
| Kitty / tmux | Supported direct literal includes; dynamic or indirect includes remain unknown. |
| btop / Yazi / Television / Leaf | Explicit theme selections in known config locations; Yazi mode-dependent differences remain unknown, and inherited `LEAF_THEME` takes precedence. Leaf syntax references are checked separately. |
| GTK / Qt6ct | Installed content, registration and any available ownership receipt against the current generated file. |
| Starship / Blastoff | The selected active Starship Dots palette, including a linked configuration, compared with published colors while allowing user palette extensions. |

Results distinguish `matches` (shown as environment/installed-content matches), `configured`, `different`, `stale`, `not-configured` and `unknown`. Only a recorded publication ancestor establishes an older generation and a stale result; a different arbitrary location is simply different. Plugin automatic-update selection is separate from installed content: disabled automation can leave matching files in use. Unexported shell values and unsupported consumers, including Neovim/general Lua runtime loading, remain unknown. No result proves that a running application has loaded the theme or that command-line overrides are absent.

Ordinary `check` still checks generated artifacts and connections. `check --consumers` additionally fails on confirmed `different` or `stale` evidence for the selected app/artifacts; unknown, unavailable and disabled-plugin automation remain informational. `list` and `info` show evidence without requiring the flag. No persistent receipts or activation acknowledgements are created by inspection.

The published `foreground` and `lighter_background` colors also supply [global less standout styling](shell-environment.md#global-less-colors). Shell refresh and Dots readers consume them without requiring a less connector or changing pager selection.

Visual preferences from the selected profile are inputs to both publishers. The generated `preferences.json`, Gitmux configuration and app-specific template tokens share the same resolver; profile files participate in publication fingerprints. Shared UI/status colors and file/Git icons use [the profile binding table](profiles.md#icons-and-semantic-colors). Palette swatches and file/Git rule colors remain exact. Editing preferences only changes sources; application fragments change on explicit publication or refresh.
