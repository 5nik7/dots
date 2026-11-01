# Tmux sessions, status and keys

The shipped tmux configuration integrates the Dots launcher, session browser and key reference. Loading that configuration is explicit; updating documentation never reloads a server.

## Browse sessions

`dots menu tmux sessions` (Prefix s) opens a themed project/session browser. Projects with open sessions appear first, then inactive projects, then other sessions. It discovers Git checkouts directly under `~/repos` plus Dots; [optional project paths](specification.md#session-browser-projects) add more. Enter switches the current client or creates a session for an inactive project; projects with several sessions open a submenu. **Alt-N** creates, **Alt-R** renames, **Alt-D** confirms deletion, **Alt-T** opens a new Termux tab attached to the selected session (Termux only), and **F1** lists actions. **Alt-H** opens the full shortcut reference; Escape or Alt-H returns to the same search. Escape goes back; Ctrl-C exits. Project rows use ``, with icons matching their names. Non-current project names with sessions use bold theme accent in both the list and preview; non-project session names use bold theme blue. Current names retain magenta emphasis. Empty-project names use `light_foreground`, normal-weight in the list and bold in the preview. The compact preview uses `battery · [1 session]` and `Project: 󰉋 ~/path`. Positive session totals use normal-weight theme orange for both current and non-current projects; zero stays red. The full `·  current` / `· current` marker uses bold theme `bright_green`. Window counts are green, and `N attached` is yellow when positive or muted when zero. Positive menu counts also use orange; `no session` stays muted. Managed workspaces follow their live pane projects and appear under the matching project; mixed workspaces remain separate entries. New sessions use `projectname-ID` (or `termux-ID` outside projects), without a name prompt. The preview keeps each session on one row and clips overflow at the right edge, including long names and paths. New Termux probes `termux-am`, falling back to the Termux-installed `am` when needed. `--print`, `--json` and redirected output remain read-only live-session listings. Use `--client CLIENT` when several clients share the invoking session. Native Windows reports tmux unavailability. See [session controls](commands.md#tmux-session-menu).

## Attention and status

The optional [Codex attention bridge](themes.md#codex-attention-notifications) adds working/waiting glyphs to other Termux tab numbers, red brackets for unread alerts, and a separate `[ N]` badge for alerting tmux sessions displayed by no tab. Open **Prefix s → F1 → Codex alerts** to find them; **Prefix a** acknowledges the current pane. Stock Termux cannot reliably report the selected tab, so the default policy notifies conservatively until an explicit acknowledgement or resolving Codex event. Its toast and vibration are attempted once per event.

On Termux, tmux has two status rows at the top: a bold 12-hour clock, Termux tab numbers and battery above, the current tmux session and its windows below. Termux tab numbers appear immediately after the clock when more than one tab exists, with the viewing tab highlighted. The lower row numbers sessions only when their group has more than one session. Project groups follow the session picker and use canonical project folders; different folders with the same name stay separate. Non-project sessions group by their full case-sensitive logical label, including termux and multi. Attached and detached sessions count, with numbers assigned within each group in creation order. By default only the current session appears: two Dots sessions show `1 dots` and `2 dots`, while a lone Battery session shows `battery`. Two tabs viewing the same tmux session show the same lower number. Window numbers independently appear when that session has multiple windows. Useful names remain when numbers disappear; matching singleton window names and managed default names stay hidden. For example: ` dots `, ` dots │ shell `, or ` 1 dots │ 1 │ 2 shell `. Session labels and all windows without warnings have one space on either side; warning labels have none. A `│` separates sections, and one space joins a number to its icon/name. Numbers may change when tabs or sessions close. COPY/PREFIX/ZOOM remain on the right. Outside Termux only the tmux row appears.

The current session uses bold `bright_cyan` on `selection_background`, without underlining its name, number or remote icon. Current window names use bold `bright_foreground` on `selection_background`, with numbers in bold `bright_green` on the same background. Inactive Codex windows use bold `dark_foreground` numbers and bold, dimmed `foreground` names. Ordinary inactive numbers and names use `dark_foreground`, retaining bold digits and bold, dimmed names. Working windows show ``; explicit Waiting states and input/approval requests show ``. Icons follow the visible number/name with one space: `1 shell `, `1 shell `, or `1 ` when the name is hidden. Both icons use theme `accent` in current and inactive windows; Working is bold, while waiting is normal when inactive and bold when current. With numbers hidden, the label is `shell ` or `shell `; when the singleton window name is hidden too, its icon moves after the session name, as in ` 󰊤 dots  ` or ` 󰊤 dots  `. This session icon uses bold accent on the session background, with its space reserved before shortening the name. A hidden default session label shows only the padded icon. Ordinary idle/Ready states have no marker. Bell/activity/silence alerts override the whole label, including icons, with bold `bright_red` on `darker_background` and brackets, such as `[2]` or `[2 shell]`, without outer spaces. Detection uses foreground processes and the Codex terminal title, refreshing with the status bar. Dividers between sections use `background` on `dark_background`. Current Termux tab numbers use bold `bright_foreground` on `selection_background`; other tabs use bold `dark_foreground` on `dark_background`, without dimming or underlining. The clock, battery, pane border and COPY/PREFIX/ZOOM colors retain their existing semantic roles. Both rows use Dots palette colors, with layout owned by the main configuration and colors supplied by the generated theme. A Nerd Font is needed for the icons. See [tmux theme integration](themes.md#tmux).

The current session can show the active pane repository's remote host icon, matching `dots.yazi`: `󰊤 dots` or `1 󰊤 dots` for GitHub, with GitLab, Bitbucket and generic Git alternatives. Hidden default names retain the icon alone or after the number. This requires optional `git-it` and a Nerd Font; no remote or unavailable metadata means no icon. Icon discovery shares the bounded asynchronous Gitmux job and does not require Gitmux itself to succeed.

The Termux upper row has battery and a daylight-colored clock; Wi-Fi/data and all other device-status indicators are disabled. The clock uses theme yellow during daylight, blue at night and the default foreground when wttr astronomy is unavailable. Background weather refresh uses a configured default or cached city, never Android location acquisition. No weather widget is enabled. See [weather and clock activation](wttr.md#termux-upper-row); the live server is not reloaded automatically.

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
Config details and `dots config explain KEY` show the actual owner and source.

| Component | Controls and supported spans |
| --- | --- |
| Clock (Termux) | `apps.tmux.clock.icon_mode`: `none` (default), `fixed`, `daylight`. Icons: `icons.apps.tmux.clock.{fixed,day,night,unknown}`. `formatting.apps.tmux.clock.format` is a strftime format. Independent `clock.icon`, `clock.text`, `clock.surround`, `clock.spacer` styles. |
| Termux tabs | `tabs.{active,inactive,alert}` base styles and `.number`, `.icon`, `.surround`, `.spacer`; generic span styles provide defaults. Before/after surrounds, alert surrounds, separator and marker spacer live under `formatting.apps.tmux.tabs`. Singleton suppression, alert overflow and current-client identity remain intact. |
| Battery (Termux) | `apps.tmux.battery.critical`/`.low` are nullable percentage thresholds; null inherits the battery tool. When both are set, critical must be lower. `charging_style` is false by default. Icons use `icons.apps.tmux.battery.{critical,low,normal,charging,unknown}`; absent icons inherit the provider. Icon/text colors and attributes are separate, including state overrides. Formatting provides surrounds, spacer and percentage slot width. |
| Sessions | `apps.tmux.session.name_source` is `workspace` (default), `session`, or `repository`. `show_number`, `show_name`, `repository_icon` and `repository_color` control visibility and decoration. `icons.apps.tmux.session.default` overrides the icon, including an empty override. Styles include `session`, `session.repository`, number/icon/name/surround/spacer and active/inactive/alert variants. Host colors may override `hosts.github`, `hosts.gitlab`, `hosts.bitbucket` under `colors.apps.tmux`. |
| Multiple sessions | `apps.tmux.session.multiple` defaults false. When enabled, a display-only list uses cached workspace metadata and one session inventory, retains the current session within the width budget, and indicates overflow. It never switches sessions. Unknown/unmanaged repository metadata falls back to the session label and generic icon. |
| Windows | `windows.{active,inactive,alert}` and number/icon/name/surround/spacer spans; an optional `icons.apps.tmux.window.default`; literal per-span and whole-label surrounds. Existing singleton suppression, native window scrolling and mouse ranges remain. |
| Git | `colors.apps.tmux.git.bg` and `git.surround` styles; before/after text under `formatting.apps.tmux.git`. Gitmux retains ownership of branch and metric content/styles. |
| Indicators | `apps.tmux.indicators.{copy,prefix,zoom,working,waiting,attention}.text` changes displayed text. Working/waiting inherit their existing glyphs when null; attention keeps its existing bracket treatment until text is supplied. Each supports base, surround and spacer styles and literal formatting. Detection, acknowledgement and notifications are unchanged. |

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
