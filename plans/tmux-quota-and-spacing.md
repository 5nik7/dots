# Tmux quota and status spacing

**Status: Implemented, locally verified and live-activated after owner approval.** Approved scope: one fewer internal battery padding cell; bold darker-background prefix text on accent; no leading Gitmux divider; Git stale markers only after failures; optional weekly Codex quota before right-aligned Gitmux.

## Accepted behavior

- Quota uses `aistat usage codex`, the single active account and `seven_day.remaining_percent`. Current-window foreground Codex detection gates display and acquisition. Missing aistat or disabled settings hide it.
- Refresh every 90 seconds in a bounded 15-second detached worker, sharing the existing widget cache across clients. Retain failures with a trailing `~` for 300 seconds, then muted `?%`. No jq, daemon, direct credential parsing, account switching or automatic dependency installation.
- Configured Codex icon and whole remaining percentage are bold. Theme green applies at 50%, yellow at 25%, orange at 10%, and red below 10%. Timing, thresholds, icon, span styles, padding, width/alignment and component placement use existing Config ownership and publication.
- Main right order is quota, Gitmux, indicators. Preserve explicit layout overrides, native window scrolling/ranges and plain spacing without orphan dividers. Termux uses its second row; Linux/WSL use the main row. Native Windows has no tmux consumer; Config stays shared with PowerShell.
- Reuse [presentation acceptance](../docs/presentation.md#acceptance-gate), existing Config menus and directory-managed tmux installation. Configuration assessment: add consumed quota controls. Menu assessment: existing Config browser suffices. No public command route or installer dependency change. Theme/configuration maintenance own this feature; existing Codex detection remains observational.

## Acceptance and delivery

- [x] Isolated provider/cache cases: active-account selection, weekly selection, zero, thresholds, malformed data, timeout, identity drift, concurrency, retention and recovery.
- [x] Private tmux rendering at 40/80/120 columns: visibility, right alignment, colors/attributes, padding, mode indicators, overflow, custom placement and repeated reloads.
- [x] Config inheritance, validation, discovery/completion, style publication and refresh checks; measured warm rendering. The unrelated discovery round-trip baseline failure is recorded below.
- [x] Canonical docs and README updated; available Wiki rebuilt/checked; links and diff checked.
- Native Linux/WSL visuals and PowerShell 5.1/7 remain pending unless separately exercised. No live aistat acquisition, theme publication, tmux reload, commit or push is part of this implementation.

## Verification evidence

Termux evidence, 2026-11-17, uses owned homes/config/cache/state, synthetic aistat accounts and private tmux sockets. Logs are retained locally at `/data/data/com.termux/files/usr/tmp/dots-quota-checks-djprlb0w`.

| Checks | Result |
| --- | --- |
| `tools/test_tmux_quota.py` | 10 pass; cached in-process render maximum 1.51 ms over ten samples; eight simultaneous callers invoke the fake provider once. |
| `tools/test_tmux_widgets.py` | 20 pass, including failure-only Git markers and independent host metadata. |
| `tools/test_style_config.py`, `tools/test_config_values.py` | 9 and 18 pass. |
| `tools/test_config_layout.py` | Initial six checks pass; all three final `Layout` cases pass, including saved legacy defaults and hidden custom components without orphan dividers. |
| `tools/test_tmux_status.py` | 18 pass across the full run and corrected prefix-color rerun; one optional upstream battery-source check skipped. |
| `tools/test_gitmux.py` | All 12 cases pass across the full run and focused reruns, including all palettes/Bash and Python renderers. Updated old divider/prefix expectations; the timeout fixture now stalls the actual provider and restores one-second polling after reload. |
| `tools/test_config_completion.py` | Five pass, including native Bash/Zsh/Fish insertion and FZF-tab. |
| `tools/test_config_live.py` | 13 pass, including quota save/reset, preference publication and unchanged palette bytes. |
| `tools/test_config_discovery.py` | Ten pass. `test_canonical_control_and_style_roundtrip` raises `KeyError: formatting`; the identical failure reproduces from a temporary archive of committed baseline `5d5fca2eeb3ce4fb1d1aa7126e697491fe9c0dcc`. Its old popup-storage assertion is outside this change. |
| Documentation | Local Wiki rebuilt and healthy; relative Markdown links and source/Wiki whitespace checks pass. |

The new helper uses existing directory-managed tmux installation, configuration menus, snapshot publication and foreground Codex detection. There is no public command/completion route to add, no new Windows app destination and no optional package installation. Native PowerShell still shares the configuration implementation; its runtime acceptance remains pending. During implementation verification, the installed live aistat provider was not invoked, and live credentials and cache were not used as test fixtures.

## Authorized live activation

On 2026-11-17 the owner requested theme and tmux refresh. `dots theme refresh -v` regenerated the selected Catppuccin Mocha theme as `g.wH7LIBKX`, published it through the theme journal and reloaded Termux settings. The current server then explicitly sourced the linked base tmux configuration and refreshed its attached 66-column client; theme-only notification does not define newly added base options.

Live checks confirm two rows, quota/Gitmux/indicator order, no leading Gitmux divider, empty battery `after` padding, the retained `PRFX` label and prefix foreground `#101019` on accent `#cba6f7`. The quota worker acquired a valid 78% weekly remaining reading with no failure flag. This is live Termux activation evidence, separate from the isolated test results above. Kitty reload and Yazi notification were unavailable; no unrelated application was launched. No commit or push was performed.

## Quota-to-Gitmux separator follow-up

Implemented: a configurable `·` between visible, adjacent quota and Gitmux components, using theme `lighter_background`. `formatting.apps.tmux.codex_usage.git_separator` defaults to `" ·"` (Gitmux supplies the following padding); `colors.apps.tmux.codex_usage.git_separator` owns foreground/background/attributes. Empty text hides it. Row background, right alignment, hidden-widget behavior and custom placement are preserved; Git's budget includes the separator width. Existing Config menus, completion and shared precedence own these controls; no new command, installer dependency or Windows tmux destination is needed. Native Linux/WSL and PowerShell runtime acceptance remain separate.

All 14 focused checks pass: ten quota cases including 40/80/120-column separator color/spacing and hidden-Git behavior, three layout cases including empty/reordered separators, and quota Config publication with text/color overrides. Evidence: `/data/data/com.termux/files/usr/tmp/dots-quota-separator-lmckd4eh`. Live Config refresh transaction `24e86f0b47e34d8a92ac71a6ba4ef536` published `g.7196e25155e341ffaa95c1118b6cfdf4`, preserving Catppuccin Mocha. The current tmux server reloaded its base configuration; the separator resolves to `#313244`, the theme's `lighter_background`, with row background and normal weight. Shared refresh is pending only for the unrelated Yazi notification. Canonical docs and the local Wiki were updated; no commit or push was made.

## Remaining battery padding

The owner requested removing one further space after the battery percentage. The existing `formatting.apps.tmux.battery.width` preference is now 3 instead of 4, retaining the stale-marker cell and outside margin. The existing default-padding check covers one/two/three-digit and unknown values with equal fresh/stale widths; generic visual fixtures retain their explicit four-cell baseline. Both affected padding/style checks pass, including private rendering at 40/48/80/120 columns. No new controls, menu, command, installer or platform behavior are needed. No README change needed: this appearance preference belongs in the tmux topic guide.

Config transaction `34282618a9b344e48c182bc5e5d5ee25` saved the preference; publication `efea1a497c20478682a3662be319babc` produced `g.1e88f70c981c4ea9a30e5d1dae011aa1`. Tmux was notified and its attached client refreshed. Live read-only rendering of the cached 79% reading confirms one trailing widget space. The unrelated Yazi notification remains unavailable. Canonical tmux docs and the local Wiki were updated; links and whitespace checks pass.
