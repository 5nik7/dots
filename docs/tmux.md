# Tmux sessions, status and keys

The shipped tmux configuration integrates the Dots launcher, session browser and key reference. Loading that configuration is explicit; updating documentation never reloads a server.

## Browse sessions

`dots menu tmux sessions` (Prefix s) opens a themed project/session browser. Projects with open sessions appear first, then inactive projects, then other sessions. It discovers Git checkouts directly under `~/repos` plus Dots; [optional project paths](specification.md#session-browser-projects) add more. Enter switches the current client or creates a session for an inactive project; projects with several sessions open a submenu. **Alt-N** creates, **Alt-R** renames, **Alt-D** confirms deletion, **Alt-T** opens a new Termux tab attached to the selected session (Termux only), and **F1** lists actions. **Alt-H** opens the full shortcut reference; Escape or Alt-H returns to the same search. Escape goes back; Ctrl-C exits. Project rows use ``, with icons matching their names. Non-current project names with sessions use bold theme accent in both the list and preview; non-project session names use bold theme blue. Current names retain magenta emphasis. Empty-project names use `light_foreground`, normal-weight in the list and bold in the preview. The compact preview uses `battery · [1 session]` and `Project: 󰉋 ~/path`. Positive session totals use normal-weight theme orange for both current and non-current projects; zero stays red. The full `·  current` / `· current` marker uses bold theme `bright_green`. Window counts are green, and `N attached` is yellow when positive or muted when zero. Positive menu counts also use orange; `no session` stays muted. Managed workspaces follow their live pane projects and appear under the matching project; mixed workspaces remain separate entries. New sessions use `projectname-ID` (or `termux-ID` outside projects), without a name prompt. The preview keeps each session on one row and clips overflow at the right edge, including long names and paths. New Termux probes `termux-am`, falling back to the Termux-installed `am` when needed. `--print`, `--json` and redirected output remain read-only live-session listings. Use `--client CLIENT` when several clients share the invoking session. Native Windows reports tmux unavailability. See [session controls](commands.md#tmux-session-menu).

## Attention and status

The optional [Codex attention bridge](themes.md#codex-attention-notifications) adds question/working/waiting glyphs to other Termux tab numbers, red brackets for regular alerts and green brackets for finished alerts, and a separate `[ N]` badge for alerting tmux sessions displayed by no tab. An idle completion alert shows only the bracketed tab number, such as `[1]`; it does not append the Codex icon. The shared Codex icon setting remains available to the quota widget and separate badge. Open **Prefix s → F1 → Codex alerts** to find them; **Prefix a** acknowledges the current pane. Stock Termux cannot reliably report the selected tab, so the default policy notifies conservatively until an explicit acknowledgement or resolving Codex event. Its toast and vibration are attempted once per event. The entire upper alert strip, including the separate badge and overflow, is hidden with zero or one validated Termux app tab. Pending alerts, lower-row window alerts and notification delivery are unaffected.

On Termux, tmux has two status rows at the top: a bold 12-hour clock, Termux tab numbers and battery above, the current tmux session and its windows below. Termux tab numbers appear immediately after the clock when more than one tab exists, with the viewing tab highlighted. The lower row numbers sessions only when their group has more than one session. Project groups follow the session picker and use canonical project folders; different folders with the same name stay separate. Non-project sessions group by their full case-sensitive logical label, including termux and multi. Attached and detached sessions count, with numbers assigned within each group in creation order. By default only the current session appears: two Dots sessions show `1 dots` and `2 dots`, while a lone Battery session shows `battery`. Two tabs viewing the same tmux session show the same lower number. Automatic multi-project workspaces hide the entire session component, including its group number, host icon, padding and divider, while retaining their actual `multi-*` names and picker grouping. Their windows remain visible even when a singleton name matches the workspace label. A single project named `multi` still displays normally. Window numbers independently appear when that session has multiple windows. Useful names remain when numbers disappear; matching singleton window names and managed default names stay hidden. For example: ` dots `, ` dots │ shell `, or ` 1 dots │ 1 │ 2 shell `. Session labels and all windows without warnings have one space on either side; warning labels have none. A `│` separates sections, and one space joins a number to its icon/name. Numbers may change when tabs or sessions close. COPY/PREFIX/ZOOM remain on the right. Outside Termux only the tmux row appears.

The current session uses bold `bright_cyan` on `selection_background`, without underlining its name, number or remote icon. Current window names use bold `bright_foreground` on `selection_background`, with numbers in bold `bright_green` on the same background. Inactive Codex windows use bold `dark_foreground` numbers and bold, dimmed `foreground` names. Ordinary inactive numbers and names use `dark_foreground`, retaining bold digits and bold, dimmed names. Working windows show ``; explicit Waiting states and input/approval requests show ``. Icons follow the visible number/name with one space: `1 shell `, `1 shell `, or `1 ` when the name is hidden. Both icons use theme `accent` in current and inactive windows; Working is bold, while waiting is normal when inactive and bold when current. With numbers hidden, the label is `shell ` or `shell `; when the singleton window name is hidden too, its icon moves after the session name, as in ` 󰊤 dots  ` or ` 󰊤 dots  `. This session icon uses bold accent on the session background, with its space reserved before shortening the name. A hidden default session label shows only the padded icon. A foreground Codex session in an idle/Ready or unknown state shows the open `` marker in normal-weight theme `muted`, with the containing background. There is one marker per window: working takes precedence over waiting across panes, then open; explicit waiting wins over a stale Working title within the same pane. Suspended, background and exited processes do not count as open. Bell/activity/silence alerts override the whole label, including icons, with bold `bright_red` on `darker_background` and brackets, such as `[2]` or `[2 shell]`, without outer spaces. Detection uses foreground processes and the Codex terminal title, refreshing with the status bar. Dividers between sections use `background` on `dark_background`. Current Termux tab numbers use bold `bright_foreground` on `selection_background`; other tabs use bold `dark_foreground` on `dark_background`, without dimming or underlining. PREFIX uses bold `darker_background` text on theme `accent`, including its padding. COPY/ZOOM retain bold `darker_background` on green. The clock, battery and pane border retain their existing semantic roles. Both rows use Dots palette colors, with layout owned by the main configuration and colors supplied by the generated theme. A Nerd Font is needed for the icons. See [tmux theme integration](themes.md#tmux).

A session containing exactly one cached project can show the active pane repository's remote host icon, matching `dots.yazi`: `󰊤 dots` or `1 󰊤 dots` for GitHub, with GitLab, Bitbucket and generic Git alternatives. Hidden default names retain the icon alone or after the number. This requires optional `git-it` and a Nerd Font; zero/multiple projects, no remote or unavailable workspace metadata means no host icon. Icon discovery shares the bounded asynchronous Gitmux job and does not require Gitmux itself to succeed.

The Termux upper row has battery and a daylight-colored clock; Wi-Fi/data and all other device-status indicators are disabled. The clock uses theme yellow during daylight, blue at night and the default foreground when no retained sun schedule is usable. Its optional attached-client worker may refresh location quietly; ordinary background weather requests still use a configured default or cached city. No weather widget is enabled. See [retained widget readings](#retained-widget-readings) and [clock activation](wttr.md#termux-upper-row); the live server is not reloaded automatically.

## Keybinding reference

`dots menu tmux keys` and `dots-menu-tmux-keys` remain compatibility entries for `dots keys tmux`. Prefix → ? invokes `dots keys --browse` through `run-shell -b`, opening the compact category menu before the binding browser. FZF owns each popup. Escape/Ctrl-C closes the shortcut quietly; genuine failures remain visible. Direct CLI cancellation still returns 130. `--print` bypasses the picker. No binding is executed and no tmux server is started or reloaded. Existing shared tmux popup styling remains available to other popups; this picker uses the published FZF theme. See [tmux compatibility](keys.md#tmux-compatibility).

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
see [live Zsh capture](keys.md#live-zsh-bindings-from-the-tmux-shortcut).

## Component preferences

Use Config's `apps.tmux`, `formatting.apps.tmux`, `colors.apps.tmux` and
`icons.apps.tmux` branches. Fields inherit from the selected profile, its parents
and shared defaults. Literal surrounds and text never execute tmux or shell
formats. Null/unset inherits; false attributes and empty icons remain explicit.
Config details and `dots config explain KEY` show the actual owner and source. Human `dots config list icons` includes all four tmux activity keys, including inherited question/working/waiting glyphs and their source; JSON and redirected listings retain declared values.

| Component | Controls and supported spans |
| --- | --- |
| Clock (Termux) | `apps.tmux.clock.icon_mode`: `none` (default), `fixed`, `daylight`. Icons: `icons.apps.tmux.clock.{fixed,day,night,unknown}`. `formatting.apps.tmux.clock.format` is a strftime format. Independent `clock.icon`, `clock.text`, `clock.surround`, `clock.spacer` styles. |
| Termux tabs | `tabs.{active,inactive,alert}` base styles and `.number`, `.icon`, `.surround`, `.spacer`; generic span styles provide defaults. Before/after surrounds, alert surrounds, separator and marker spacer live under `formatting.apps.tmux.tabs`. Zero/one-tab suppression includes all upper-row attention badges and overflow; current-client identity remains intact. |
| Battery (Termux) | `apps.tmux.battery.critical`/`.low` are nullable percentage thresholds; null inherits the battery tool. When both are set, critical must be lower. `charging_style` is false by default. Icons use `icons.apps.tmux.battery.{critical,low,normal,charging,unknown}`; absent icons inherit the provider. Icon/text colors and attributes are separate, including state overrides. Formatting provides surrounds, spacer and percentage slot width. The default `after` surround is empty and percentage `width` is 3; a two-digit percentage has only the reserved stale-marker space after `%`, followed by the existing outside margin. `100%` expands naturally without truncation. |
| Sessions | `apps.tmux.session.name_source` is `workspace` (default), `session`, or `repository`. `show_number`, `show_name`, `repository_icon` and `repository_color` control visibility and decoration. `icons.apps.tmux.session.default` overrides the icon, including an empty override. Styles include `session`, `session.repository`, number/icon/name/surround/spacer and active/inactive/alert variants. Host colors may override `hosts.github`, `hosts.gitlab`, `hosts.bitbucket` under `colors.apps.tmux`. |
| Multiple sessions | `apps.tmux.session.multiple` defaults false. When enabled, a display-only list uses cached workspace metadata and one session inventory, retains the current session within the width budget, and indicates overflow. It never switches sessions. Automatic multi-project sessions are omitted, and the entire list is hidden when the current session is such a workspace. Unknown/unmanaged repository metadata shows the session label without a host icon; an explicit session icon override remains available. |
| Windows | `windows.{active,inactive,alert}` and number/icon/name/surround/spacer spans; an optional `icons.apps.tmux.window.default`; literal per-span and whole-label surrounds. Existing singleton suppression, native window scrolling and mouse ranges remain. |
| Git | `colors.apps.tmux.git.bg` and `git.surround` styles; before/after text under `formatting.apps.tmux.git`. Gitmux retains ownership of branch and metric content/styles. |
| Indicators | `apps.tmux.indicators.{copy,prefix,zoom,open,working,waiting,question,attention}.text` changes displayed text. Open/working/waiting/question inherit `icons.apps.tmux.status.{open,working,waiting,question}` when null; an empty icon/text suppresses the marker and its gap. Open defaults to `` with `colors.apps.tmux.indicators.open.fg=muted`, `bold=false`, `dim=false` and inherited background; attention keeps its existing bracket treatment until text is supplied. Each supports base, surround and spacer styles and literal formatting. Question defaults to bold bright-red ``; priority is question > working > waiting > open. Acknowledgement clears unread brackets while a pending question remains. Finished alert styles use `colors.apps.tmux.{windows,tabs,session,indicators}.finished`; they keep the bracket shape and bold weight, defaulting to bright green. |

Style names in the table are relative to `colors.apps.tmux` unless stated
otherwise. Styles support fg/bg, bold, dim, italic, underline, reverse and
strikethrough only where consumed. Shared `colors.status.working`/`.waiting`
and `colors.icons.status.working`/`.waiting` now reach lower-row activity markers;
the component indicator style overrides them. Termux tab markers inherit their
active/inactive/alert state, with explicit indicator and tab-icon overrides.
Battery state colors are reusable
`colors.battery.{critical,low,normal,charging,unknown}.fg` globals. A continuous battery
background uses all four `colors.apps.tmux.battery.{icon,text,spacer,surround}.bg`
controls; `formatting.apps.tmux.battery.before` and `.after` add the outer padding.
The Termux profile uses `dark_background` for those four spans and a space on
either side, matching the clock background. State-specific icon/text overrides
still take precedence; the fixed percentage slot width remains independent. Clock time
uses `colors.daylight.day.fg` and `.night.fg`. Weather's sunrise/sunset defaults
use the corresponding shared roles unless its native configuration overrides them.

```sh
dots config set colors.apps.tmux.clock.icon.fg colors.daylight.sunrise.fg
dots config set formatting.apps.tmux.clock.format '%H:%M'
dots config set colors.apps.tmux.windows.active.number.bold false
dots config set apps.tmux.indicators.prefix.text P
dots config set formatting.apps.tmux.session.name.before '['
dots config set formatting.apps.tmux.session.name.after ']'
```

Saved visuals publish resolved data and the owned `tmux-controls.conf` fragment;
verified servers receive visual changes without sourcing attention hooks. Normal
configuration loading reapplies that fragment after native status definitions.
Polling reads published preferences only, with no profile scans or extra process
per span. Repository metadata is observed locally during workspace reconciliation,
not on each status render. A repository label falls back to the session name
until that metadata is available. Missing Python retains the original battery
parser and appearance; custom battery controls require the Python renderer.

If an older published snapshot displays literal style text such as `bold] COPY`
while the indicator is inactive, run `dots config refresh`. This regenerates the
supported visual snapshot from current sources, preserves the selected palette,
and refreshes verified running tmux servers without reloading hooks or bindings.

Clock/tabs/battery retain their Termux boundaries. Sessions/windows/Git/indicators
apply on POSIX tmux. Native Windows can inspect/edit these preferences; doing so
does not activate WSL or a tmux server. Native desktop Linux/WSL and Windows
terminal acceptance is separate from the isolated Termux checks.

## Retained widget readings

Clock, battery and Git status read private snapshots immediately and schedule bounded one-shot workers when due. There is no daemon. Refresh failures preserve recent successful data; malformed provider text never reaches tmux. The top row budgets tabs after the clock and battery, including configured padding. Git occupies reserved space after the window list and before mode indicators, with a smaller budget when those indicators are visible.

The Termux clock retains validated sunrise/sunset schedules independently of weather freshness. It prefers today's forecast, then reuses the most recent earlier schedule for up to seven days, recalculating day/night on each render. Missing/expired data uses the neutral foreground. Known location/timezone changes invalidate incompatible schedules. Sunrise and sunset follow the existing local-time assumption; retained earlier dates are approximate.

| Config control | Default and behavior |
| --- | --- |
| `apps.tmux.clock.auto_location` | `false` in shared defaults; `true` in the tracked Termux profile. Attached tmux clients may schedule quiet `termux-geo --json` acquisition. |
| `apps.tmux.clock.location_refresh_seconds` | `21600` (six hours), integer 3600–86400. Successful acquisition resets the interval. |
| `apps.tmux.clock.sun_times_max_stale_seconds` | `604800` (seven days), integer 86400–604800. Reads never renew the successful acquisition timestamp. |

Config uses the existing profile > parent > shared-default precedence and published preference refresh. A configured weather location bypasses automatic device acquisition. Geo failures retry after 5, 15, then 60 minutes; the helper retains responsibility for longer address-service cooldowns. Workers suppress output and keep no raw coordinates or provider diagnostics in widget records. Ordinary weather cache-only commands, previews, help and completion keep their existing acquisition policy.

Battery polls every 30 seconds with a five-second deadline. Failed refreshes retain the reading with `~` for five minutes, then show the unknown battery slot. The marker has reserved space, including at 100%. Missing Python leaves a visible unknown slot without an unbounded provider call. Existing battery thresholds, glyphs, colors and box padding still apply.

Git polls every five seconds with a three-second deadline. Failed Git-status or overall refreshes retain the last result with a leading `~` for 30 seconds, then show ` ?` in a confirmed repository. A confirmed non-repository directory clears it. Snapshots are scoped to directory/worktree identity, HEAD and Gitmux configuration; host icons and Git statistics fail independently. Healthy refresh timing and host-icon-only failures do not mark Git status stale. Gitmux stays on the right before mode indicators, with plain padding and no leading colored divider. Literal branch names remain escaped. No Git network operation is performed.

Snapshots live under `${XDG_CACHE_HOME:-$HOME/.cache}/dots/tmux-widgets` in private directories/files. Atomic replacement, nonblocking per-key locks and expiring worker reservations prevent partial reads and duplicate work across clients. These disposable caches are separate from managed file journals. Removing a cache causes an initial unknown reading followed by recovery on refresh. Source helper updates affect the next invocation; updated row formats and published preferences require the normal explicit Config refresh/tmux reload.

## Codex weekly quota

When optional `aistat` is available on tmux's PATH, a foreground Codex pane in the current window enables a bold Codex icon and remaining weekly percentage. The second Termux row's right group is **quota → Gitmux → mode indicators**; Linux/WSL use their main row. The quota remains visible outside Git repositories. Hidden widgets leave no padding or dividers. Existing foreground-process detection includes idle/working/waiting Codex and excludes stopped/background/exited processes; another window running Codex does not enable this widget. Native Windows has no tmux consumer.

A detached worker invokes `aistat usage codex`, parses the single `active: true` account's `limits.seven_day.remaining_percent`, and rounds down for display. It never substitutes five-hour, code-review or inactive-account limits. This is weekly quota remaining, not an exact token counter. No jq is needed. Missing aistat, a disabled widget, or placement outside the displayed rows prevents quota acquisition; missing/ambiguous data displays muted `?%`. A valid zero is `0%`.

Rendering uses a private local snapshot without waiting for aistat. Refreshes run about every 90 seconds while visible, respect aistat's own usage cache, and have a 15-second deadline. Multiple clients share a refresh reservation. Failed refreshes retain the last value with a trailing `~` for up to 300 seconds from its successful observation, then display `?%`. A normal pending refresh does not add `~`. Executable/authentication-file metadata changes invalidate the snapshot; Dots does not read credentials or retain account identifiers. The provider owns its account/cache writes and may refresh its existing live credential. Dots never runs account-switch commands, installs aistat, or implements a separate authenticated endpoint. See [aistat's usage contract](https://github.com/drogers0/aistat#how-it-works).

| Config family | Controls and defaults |
| --- | --- |
| `apps.tmux.codex_usage` | `enabled=true`, `refresh_seconds=90` (15–3600), `timeout_seconds=15` (1–60), `max_stale_seconds=300` (15–86400, at least the refresh interval). |
| `apps.tmux.codex_usage` thresholds | `green_at=50`, `yellow_at=25`, `orange_at=10`; integer percentages in strictly ascending orange/yellow/green order. Green at ≥50%, yellow at ≥25%, orange at ≥10%, otherwise red. |
| `colors.apps.tmux.codex_usage` | Base attributes, including `bold=true`; state roles `.good`, `.medium`, `.low`, `.critical`, `.unknown` default to green/yellow/orange/red/muted. State foregrounds override the base foreground. |
| `colors.apps.tmux.codex_usage.{icon,text,surround,spacer}` | Independent foreground/background and attributes. Unset values inherit the base/state; each span restores the containing style. |
| `icons.apps.tmux.codex_usage` | Inherits the canonical configured Codex icon; an empty string hides it and its spacer. |
| `formatting.apps.tmux.codex_usage` | `before=" "`, `after=""`, `spacer=" "`, `width=0` (natural percentage width; maximum 20), `alignment="right"` (`left`, `center`, `right`). |
| `formatting.apps.tmux.codex_usage.git_separator` | `" ·"`; Gitmux's normal leading padding completes `72% · branch`. Empty text hides it. It appears only when both widgets are visible and quota immediately precedes Gitmux on the same side of a row. |
| `colors.apps.tmux.codex_usage.git_separator` | Foreground defaults to theme `muted`; background inherits the row, with normal weight. Foreground/background and attributes are independently configurable. |
| `formatting.apps.tmux.main_right` | Shared default `["codex_usage", "git", "indicators"]`; main left defaults to session/windows. Explicit layout overrides are retained; saved copies of the old default layout keep Gitmux right-aligned and omit quota. `codex_usage` is also available in custom component lists. |

Use `dots config browse --query codex_usage` or the normal Config get/set/explain commands. Profile > parent > shared-default precedence, null reset, previews, completion and published preference refresh are shared with other widgets. Changing the refresh interval does not bypass aistat's own cache. Styling and placement use normal Config publication; loading the updated base tmux configuration is explicit. The optional executable is not a bootstrap dependency.
