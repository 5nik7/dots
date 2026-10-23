# Tmux battery status and named sessions

**Status: Implemented; focused verification passes, with unrelated baseline failures recorded below.** Scoped maintenance; no general CLI migration or battery-repository changes.

## Contract

- On Termux, use two top rows: the bold `%-I:%M` clock on the upper left, with connected Wi-Fi or eligible mobile data then battery on the upper right; creation-ordered Termux numbers below, with the current number expanded by its optional tmux badge and windows before later numbers, with the exact blue COPY/PREFIX/ZOOM indicators on the right. Outside Termux show only the tmux row. No hostname; retain the five-second refresh.
- A Bash adapter calls `~/repos/battery/battery` once, preserving configured thresholds and charging icons. Translate only its red/yellow/green ANSI output to tmux styles. The fixed-width bar mode uses one space after the icon and pads after percentages and shows an unknown placeholder on failure; standalone legacy mode clears missing or invalid output without diagnostics. No cache, service, package installation or live-server reload.
- The main tmux config owns `status-left` and `status-right` after the theme include. Generated themes supply the badge’s `@dots-session-style` instead of replacing layouts, with blue/black fallback in the main config. The template also publishes `@dots-termux-*` colors: `background`/`foreground` for both row bases, `dark_background` for window labels, `lighter_background`/`hint` for inactive entries, and `hint`/`darker_background` for the current entry. Use `info` without underlining for the current tmux window and `selection` for the active pane border. Do not edit existing generated artifacts.
- Shared Bash/Zsh `t [session-name]` infers the Git worktree root's basename when called without arguments, even from nested directories. New inferred sessions start at the root; explicit names bypass detection and use the caller's directory. Missing Git/non-repository directories fall back to Work. Normalize dots/colons/control characters only in inferred names to hyphens. Same resulting names reuse one session; explicit names disambiguate. Attach/create outside tmux; switch/create inside, without nesting or renaming. Exact targeting, quoted arguments, explicit invalid-name refusal, error propagation and legacy-alias reload safety are required.
- Preserve all unrelated working-tree changes and the existing config-directory link.

## Acceptance

- [x] Battery adapter and main/theme configuration agree on layout ownership.
- [x] Bash/Zsh named-session and reload tests pass.
- [x] Isolated battery fixtures cover color, icon, thresholds, failure clearing and single invocation.
- [x] Disposable native tmux verifies config loading, legacy-theme override, asynchronous output and named-session behavior.
- [x] Applicable shell/theme suites, syntax checks and documentation links are checked; unrelated baseline failures are distinguished.
- [x] README, shared shell, architecture and testing documentation reflect implemented behavior.

Apply the [presentation acceptance gate](../docs/presentation.md#acceptance-gate). The adapter is a tmux-format data interface, intentionally colored even under `NO_COLOR`, not human CLI output; no banners, ANSI leaks or unsafe format text. Percentage text preserves meaning without color; Nerd Font glyph appearance needs manual review. Native tests use Termux-owned disposable homes and sockets, never the live tmux server. No desktop or native Windows verification is claimed.

## Termux system row follow-up

Implemented on 2026-10-14. A bounded Python adapter invokes `termux-sessions --json` once per job and matches the viewing client's TTY; it preserves creation order without depending on server ancestry or altering the script's CLI. Missing/invalid data and one-second timeouts clear session labels. Numbers may change as sessions close, and no click-to-switch behavior is added. The main config saves tmux's standard window row after resetting defaults, so repeated reloads and theme-only refreshes preserve row ownership and mouse ranges. Native clipping keeps the current Termux entry visible on narrow terminals.

Verification on Termux with tmux 3.8: the status suite passes eight tests with one optional battery-source skip, including actual cell/attribute capture through disposable outer tmux terminals, two clients, 40/80/120 columns, overflow, malformed-data and missing-Python clearing, non-Termux fallback and color refresh. Theme workflow passes 26 tests with one optional Pi skip. The theme suite passes 28 tests; its Neovim all-families case hits the previously reproduced 40-second timeout and a fixture cleanup race. The remaining owned fixture was removed after verifying no fixture processes remained. 171 local documentation targets resolve; the previously recorded Yazi link in `docs/testing.md` remains broken. `git diff --check` passes. Existing unrelated source/submodule changes remain intact. No live activation or human font/color review is performed. Run `dots theme refresh`, then tmux **prefix + q**, to activate.

## Clock and theme styling follow-up (historical single-row layout)

Implemented on 2026-10-14: the clock is first on the left in bold 12-hour format without a leading zero or AM/PM suffix; the session badge follows it. Theme-only refreshes update the badge style without replacing either layout. Current-window text uses `info`, and the active-pane border uses `selection`.

Verification on Termux with tmux 3.8: status suite passed five tests with one optional battery-source skip, including native rendering, legacy overrides and theme reloads. Platform `strftime` checks cover midnight, morning, noon and evening. Theme workflow passed 21 tests with one optional Pi skip; the theme suite passed 28 tests with one Neovim all-families timeout, reproduced using the original HEAD tmux template in a disposable fixture. The baseline timeout also triggered a fixture cleanup race; the remaining owned directory was removed after verifying no fixture processes remained. All 111 existing local targets in the affected documentation resolve except the previously recorded Yazi link in `docs/testing.md`; whitespace checks pass. Live reload and human visual review remain manual. Run `dots theme refresh`, then tmux **prefix + q**, to activate the template and layout changes.

## Repository-aware default follow-up

Requested after initial implementation: plain `t` in this checkout must select `dots`, while explicit arguments still win. Detection is one on-demand Git query, not a startup scan or cache; linked worktrees retain their own names. Shared mock regressions and native Git/tmux fixtures cover these cases. Follow-up verification passes: 19 shared-shell tests, three native tmux tests (Bash and Zsh), and 30 shell-init tests with three existing skips. Bash/Zsh syntax, Bash ShellCheck and `git diff --check` pass. The initial verification record below remains historical.

## Verification record

Native verification ran on Termux. Live reload and visual font review remain manual.

- All 17 shared-shell tests pass, including Bash/Zsh argument, exact-target, failure, race and legacy-alias cases.
- All six status tests pass, including the optional copied upstream battery script with owned PREFIX/API mocks and native tmux rendering.
- Both native session tests pass (6.380 seconds), each exercising Bash and Zsh clients, exact-prefix collisions, attach/create/switch/reuse and working directories.
- Broader suites pass: common helpers (29), shell init (30, three skips), Bash dispatcher (24), Zsh (22), themes (29), theme workflow (22, one skip). Native Bash and Zsh PTY runners pass. Full logs are retained in `/data/data/com.termux/files/usr/tmp/dots-tmux-checks-r71nlkhc`.
- An isolated definition/alias-load microbenchmark used a t-only reconstructed pre-change baseline and seven alternating warm batches of 50 loads per shell, with optional tools disabled. Median milliseconds per load pair: Bash 2.455 before / 2.432 after; Zsh 2.932 / 2.708. These advisory figures show no observed regression, not a speedup claim, full-startup measurement or Android API timing.
- Bash/Zsh syntax, explicit Bash ShellCheck and `git diff --check` pass.
- The global Markdown checker stops on the pre-existing `docs/testing.md` link to `config/yazi/plugins/dots-symlink.yazi/README.md` (also present in HEAD). The other 132 local targets in affected docs resolve.
- The existing tmux-key suite passes 18/19 checks. Its popup test expects blue/cyan, whereas the pre-existing user binding uses brightblack/yellow; neither the binding nor that unrelated test is changed here.
- The first optional upstream battery test inherited the real Termux `PREFIX`, bypassing its PATH mock and timing out during a read-only battery API request. Its owned remaining processes were terminated. The corrected fixture now owns `PREFIX/bin` and kills its complete adapter subprocess group on timeout; all six rerun checks pass.

## Automatic Termux default sessions

Implemented on 2026-10-14, following the approved plan. New Dots Bash/Zsh Termux tabs enter independent default tmux sessions. The default badge is hidden while both rows and windows remain; project sessions keep their badges. Detaching returns to the outer shell without looping. `androidots/bin/termux-bar` provides manual reattachment and guarded `--auto` startup, with `DOTS_TERMUX_AUTOSTART=0` opt-out. Identity uses the Termux root PID and start ticks, never its displayed session number. Existing default sessions are retained without cleanup; unmarked name collisions are refused.

The shared hook remains outside Fish, SSH, child-shell and noninteractive startup. The launcher uses the existing server and does not reload it. Plain help and concise stderr diagnostics satisfy the presentation fallback; tmux owns the themed UI. Apply the existing [presentation gate](../docs/presentation.md#acceptance-gate), with disposable homes/procfs and private tmux sockets for verification. Update shell-init, architecture, platform, command and test references and both READMEs with implemented behavior. Verification results follow below.


### Automatic startup verification

- The six Androidots launcher tests pass. Five native autostart cases pass (four together plus the added cold-server case): Bash/Zsh attachment, separate tabs, same-client project switching, detach/reload/manual reattach, final-session exit, guarded startup/failure fallback, and creating the first private server. App process identity is simulated; real Android new-tab startup remains manual.
- Status tests pass nine cases with one optional battery-source skip, including hidden badges at 40/80/120 columns and config/theme reloads. Existing named-session tests pass all three cases, shared-shell tests pass all 19, and theme workflow passes 27 cases with one optional Pi skip. Native testing exposed quiet missing-target lookups and option-target parsing; the launcher now checks existence explicitly and uses exact session targets with a trailing colon for options. The status fixture also waits for both clients to attach before refreshing them.
- The broader shell-init run executes 30 tests with three skips and 19 Xonsh subcase errors. The installed Xonsh executable points to absent `python3.13`; launching it without any Dots initialization reproduces the error. Bash/Zsh cases pass. This task does not repair that unrelated interpreter installation.
- Seven alternating warm samples in disposable minimal-tool Bash/Zsh initialization fixtures measured median startup milliseconds before/after this hook: Bash 80.284/90.757; Zsh 97.740/103.184. The hook adds a source/guard check to interactive initialization. Separately, seven fresh default-session attachments per shell on a private existing server with simulated procfs/discovery took median 310.278 ms (Bash) and 282.011 ms (Zsh), including fixture polling. These advisory measurements include scheduling/process overhead; they are not real Android app startup or full live-plugin timing. Existing tmux panes skip the Python launcher.
- Bash/Zsh syntax, hook ShellCheck, Python syntax, and parent/child `git diff --check` pass. Plain help was reviewed. 241 local Markdown targets in affected docs resolve; the global checker still stops at the pre-existing missing Yazi README target in `docs/testing.md`.
- No live tmux server was reloaded, no packages or shell links were installed, and no commits were created. Open a new Termux tab to use the hook; reload an existing tmux server with prefix + q to activate badge hiding.


## Android indicator cluster

Implemented on 2026-10-14, following the approved plan. Added a separate bounded Python adapter for Wi-Fi, cellular, notification and location JSON reads, in that order before the upper-row battery. Preserve the session adapter, lower row, clock and battery semantics. Ordinary reads retain Androidots' caching/permission gates; no recurring `--refresh`, cache-only polling, duplicate cache or daemon. Use supplied icons, preserve unknown/stale markers, and append positive notification counts capped at `99+`. Missing or invalid modules clear only their segment.

Change the upper-row background to `dark_background` and inactive-session colors to `background`/`hint`; retain current-session `hint`/`darker_background`. Validate 40/80/120-column rendering, reloads, theme updates, quoting, safe output, failures and bounded reads with private tmux servers, copied scripts/libraries and mocked providers. Apply the existing presentation gate. Update both repositories' documentation and report focused plus relevant regression results separately from device/font checks. No live provider initialization, permissions, package installation, server reload, commits or pushes.


### Android cluster verification

- Parent checks pass: Android adapter 6/6; tmux status 8 passed plus one optional battery-source skip; named sessions 3/3; automatic startup 5/5; themes 29/29; theme workflow 26 passed plus one optional Pi skip. The added cell-color assertions also pass in the rendered status case. The historical Neovim timeout did not recur in this theme run.
- Androidots regressions pass: status 25/25, session discovery/completions 28/28, launcher 6/6. Integration uses copied libraries and scripts with a fixture-only override of the entire provider-command boundary, including the absolute location command. No live Android providers or permissions are exercised.
- Attached private tmux clients verify all four indicators before the battery at 40/80/120 columns, including `99+~`, current session 31 in an overflowing list, valid unknown states, missing/invalid helpers, missing Python, repeated config reloads, theme refresh, hidden default badges, normal project badges, and unchanged non-Termux layout. Captured cells prove the Android cluster uses the upper-row foreground/background and the green battery retains that background.
- Nine alternating warm samples in disposable fixtures measured median 186.283 ms for the existing session adapter and 424.541 ms for the added Android cluster using the real copied scripts with warm caches. No provider calls occurred during warm samples. These are advisory process/scheduling timings, not live Android API or font evidence; tmux jobs remain asynchronous and helper reads have concurrent one-second deadlines.
- Python syntax, parent/child whitespace checks, and new-file whitespace checks pass. 180 relative documentation links resolve. The global docs checker still fails on the pre-existing missing `config/yazi/plugins/dots-symlink.yazi/README.md` target; no unrelated documentation repair is included.
- Existing source/submodule work is preserved. An unrelated Blastoff provenance-file change appeared during verification and was left alone. No live server reload, provider initialization, package/permission changes, commits or pushes were performed.

Changed for this integration: `config/tmux/android-status.py`, `config/tmux/tmux.conf`, `default/themed/tmux.conf.tpl`; `tools/test_android_status.py`, `tools/test_tmux_status.py`, `tools/test_theme_workflow.py`; parent README, testing guide, architecture/platform/testing/theme references and this plan; Androidots README and `docs/termux-status.md`. Session discovery, launcher, battery adapter and Androidots provider/cache implementations are unchanged by this integration.

Activation: run `dots theme refresh`, then tmux prefix + q. Run `"$HOME/dots/androidots/bin/termux-cell-status" --refresh --both` and `"$HOME/dots/androidots/bin/termux-notification-status" --refresh --both` interactively to initialize the gated providers; grant access if requested and repeat until successful. Use the server's HOME/XDG cache location. Provider failures require another successful explicit refresh. Location may legitimately remain unknown; actual Nerd Font appearance and Android permission interactions remain manual checks.


## Fixed slots, sound and exit follow-up

Implementation: move sessions before the clock; use `background` above and `dark_background` below, with inactive session `dark_background`/`hint`. Order the fixed-width right slots as notification count, media volume, location, Wi-Fi, fixed cellular glyph and battery. Reserve three notification digits and one marker per Android slot; use one separator cell and pad battery percentages. Signal levels 0–1/2/3–4 map to theme red/yellow/green; unavailable/stale samples remain muted. Preserve selected-session visibility, lower-row indicators, theme/layout ownership and non-Termux behavior.

Add `termux-volume-status` with the existing CLI/cache/provider framework. Read all streams using argument-free `termux-volume`; select music by default or `--stream`. Cache for five seconds, never set audio state, and suspend failures under the existing recovery contract. Completion and metadata reads remain API-free.

For automatic Bash/Zsh attachment, distinguish tmux completion stdout from pane rendering. Only successful exact `[exited]` yields internal status 20; the startup hook consumes it to exit the outer shell. Termux `detach-on-destroy on` prevents unrelated session switching. Deliberate detach, manual attachment and server failures retain the shell. Preserve unrelated sessions and normal pane/window lifetime.

Validation uses owned homes, fake providers and private tmux sockets only. No live activation, Android permission changes, package installation, commits or pushes. Final verification results are recorded below.

Changed in this follow-up: parent `config/tmux/tmux.conf`, `config/tmux/android-status.py`, `config/tmux/battery-status.sh`, `default/themed/tmux.conf.tpl`, `shells/shared/termux-tmux.sh`; `tools/test_tmux_status.py`, `tools/test_android_status.py`, `tools/test_termux_autostart.py`, `tools/test_theme_workflow.py`; README, testing guide, architecture/command/platform/shell-init/testing/theme references and this plan. Androidots changes: `bin/termux-volume-status`, `bin/termux-bar`, shared status provider/cache/display/CLI/completion modules, status/launcher tests, README and status documentation. Existing unrelated dirty and untracked work is preserved.

Activation: `dots theme refresh`, then **Ctrl-Space q** (or **Ctrl-b q**); alternatively `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"`. Open a new Termux tab to use the updated automatic-attachment exit behavior. Cellular/notification initialization commands remain those above. Volume polling starts automatically; use `"$HOME/dots/androidots/bin/termux-volume-status" --refresh --both` to inspect or recover it interactively. Actual Android new-tab closing and Nerd Font appearance remain owner-run checks.

### Fixed-slot and exit verification

- Pre-change baselines: autostart 5/5, Android adapter 6/6, Androidots status 25/25.
- Updated focused checks: tmux status 8 passed and one optional skip; the optional battery-source test was then run separately with copied source and mocked APIs and passed. Android adapter 6/6, named sessions 3/3, autostart 7/7; Androidots status 27/27, launcher 7/7 and session discovery 28/28. Shared-shell regressions pass 19/19 and Zsh passes 22/22. Theme workflow passes 26 tests with one optional Pi skip.
- Attached native clients verify 40/80/120 columns, sessions preceding the clock, both row backgrounds, theme signal colors, selected-session clipping, fixed icon positions across `99+~`, missing data and 1/80/100% battery levels, battery failure placeholders, repeated reloads and non-Termux fallback. Resize assertions wait for the actual new frame rather than stale terminal cells.
- Bash/Zsh PTYs verify pane-only exits, final-pane `exit`/`q`, project-session exits, another tab/session surviving, detach returning to the shell, and unexpected server loss retaining the shell. The launcher only recognizes an exact successful completion response.
- Bash/Zsh syntax, ShellCheck and both repositories' diff whitespace checks pass. Changed-document link checking resolves 224 relative targets outside fenced examples; the existing Yazi plugin README link in `docs/testing.md` remains broken. Full shell-init testing still fails on Xonsh's existing launcher pointing at missing `python3.13` (19 errors/subtest errors, three skips); no Xonsh sources were changed.
- The full theme run passes 28/29, with the historically intermittent 40-second Neovim all-families timeout. The failing case passes in isolation with the pre-change tmux template (38.389 seconds overall) and the updated template (38.867 seconds). No Neovim changes were made for this task; retain the full-run timeout in the evidence rather than claiming a clean initial run.
- Nine alternating warm-cache samples of the same adapter with four versus five modules measure medians of 480.16 ms and 513.35 ms respectively (about 33 ms for the additional volume read). All reads used copied real scripts and fake providers; warm samples made zero provider calls. These asynchronous job timings do not measure live Android API latency or physical font rendering.
- After the lower-row style fix, the final connector test passes again, evaluating the published status style in both Termux and non-Termux contexts and checking all new semantic color options.


## Conditional network display follow-up

Historical integration (unknown-network behavior superseded by the network uncertainty repair below): poll only Wi-Fi and cellular, then keep the independent battery segment. Connected Wi-Fi wins. Cellular appears only with explicitly disconnected Wi-Fi, enabled data and `data_state == "connected"`; unknown/missing Wi-Fi hides both. Valid stale cached observations remain eligible with a muted `~`, including stale Wi-Fi evidence used to select cellular. Expired/unavailable data does not qualify. Notification, volume and location remain available as standalone commands.

Keep Wi-Fi/data in equal-width slots, omit the slot and separator when neither qualifies, and retain dynamic Wi-Fi/fixed cellular glyphs and signal colors. Battery uses exactly one icon-to-percentage space and pads after the percentage, including the unknown placeholder. Preserve all row layout, session, clock, mode, exit and non-Termux behavior. No template or generated-theme changes are needed.

Changed for this follow-up: `config/tmux/android-status.py`, `config/tmux/battery-status.sh`, `tools/test_android_status.py`, `tools/test_tmux_status.py`; parent README, architecture/platform/testing/theme references, testing guide and this plan; Androidots README and status integration documentation. Provider/cache implementations are unchanged. Tests use owned fixtures and private sockets; no live providers, permissions, server reload, packages, commits or pushes. Verification results follow below.

Existing directory-linked installations pick up adapter changes on the next status refresh (normally five seconds). An optional config reload is tmux **prefix + q**, or `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"`. Cellular initialization remains `"$HOME/dots/androidots/bin/termux-cell-status" --refresh --both`, run interactively with the server's HOME/XDG cache location; repeat after a provider failure. No notification or volume initialization is required for this bar.

### Conditional display verification

- Android adapter: 7/7 pass, including the strict connectivity matrix, stale selection, disabled-helper nonexecution, bounded failures and copied real cache/provider integration.
- Tmux status: 8 passed with the optional battery-source case skipped; that source-only, mocked-API case also passes when run explicitly. Attached private clients verify Wi-Fi/data/no-network transitions at 40/80/120 columns, stable network/battery positions, one-space battery gaps at 1/80/100% and unknown, repeated reloads, theme changes and non-Termux behavior.
- Androidots regressions: status 27/27, sessions 28/28 and launcher 7/7 pass. The targeted theme connector/publication test passes; no template or theme engine changes were made in this follow-up. Earlier broader-suite limitations remain recorded above.
- Python/Bash syntax, battery ShellCheck and both repositories' diff whitespace checks pass. All 180 other relative Markdown targets in affected documents resolve; the pre-existing missing Yazi plugin README link in `docs/testing.md` remains.
- No live tmux reload, live Android provider queries, permission changes, installation, commits or pushes were performed. Physical Nerd Font rendering remains a device check.


## Lower-row Termux numbers

Implemented: move Termux numbers before the optional session badge and windows on row two; leave the clock alone at upper left. Termux-only colors: row two `background`, inactive numbers `lighter_background`/`hint`, windows `dark_background` with existing foregrounds. Retain current-number and session-badge colors and default-session badge hiding. Bound numbers to one quarter of client width capped at 20 columns, keeping nearby entries and overflow arrows; bound the badge to one quarter capped at 30. The session adapter clips complete numeric labels without window-list directives so native tmux window scrolling and mouse ranges remain independent. Preserve non-Termux appearance, network/battery behavior and existing uncommitted work. Validate attached private clients at 40/80/120 columns, theme publication/reloads, long names, overflow, colors, mouse ranges, mode indicators and failure clearing. No live activation or provider/permission changes.

### Lower-row verification

- All 10 tmux status tests pass, including the optional copied battery source with mocked APIs. Attached clients at 40/80/120 columns verify the new order, two independent selections, number and window overflow at the same time, long project badge clipping, default badge hiding, current/inactive colors, native mouse selection, COPY/PREFIX/ZOOM placement, reloads, theme updates, missing-helper clearing and the non-Termux branch.
- Android adapter 7/7 and Androidots session discovery 28/28 pass. Theme workflow passes 26 tests with one optional Pi skip. No Android providers were queried.
- Numeric width comparisons use tmux arithmetic operators; fixture clicks are separated to avoid double-click gestures, and fixture pane IDs remain stable across base-index settings. These checks caught and resolved layout/test issues before completion.
- Activation is `dots theme refresh`, then **Ctrl-Space q** or **Ctrl-b q**. Alternatively reload with `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"` after refreshing the theme. No live reload, package or permission changes, commits or pushes were performed.

Python syntax and both repositories' whitespace checks pass. Changed-document checking resolves 183 relative targets; the pre-existing missing `config/yazi/plugins/dots-symlink.yazi/README.md` target remains. Changed sources are the canonical tmux config, session adapter and theme template; status and theme-workflow tests; parent README, testing guide, architecture/platform/shell-init/testing/theme references and this plan; Androidots README and status integration documentation.

The broader theme suite passes 28/29 tests and again reaches the previously recorded 40-second `test_neovim_all_native_families` timeout (`nvim --headless`, `check_editor.lua`). This run has one timeout error and no additional assertion failures; no Neovim code was changed. The isolated status and full theme-workflow results above pass. Actual device font appearance and live activation remain owner-run checks.


## Current Termux group and unavailable cellular indicator

Implemented: expand only the current Termux number with its optional tmux badge and native window list, followed immediately by later Termux numbers. Keep numeric order, existing colors and clipping budgets, no literal brackets or divider. Split one cached asynchronous discovery job into before/after segments; preserve native window ranges/scrolling and lower-right mode indicators. Unmatched clients keep numbers before the tmux content; failures clear both sides.

Historical behavior (superseded by the network uncertainty repair below): when Wi-Fi is explicitly disconnected, confirmed active data retains its signal indicator, confirmed disabled/nonconnected data stays hidden, and missing/incomplete/expired cellular readings show a muted fixed data icon with `?`. Unknown Wi-Fi still hides both. Preserve stale markers for eligible readings and provider polling gates. The current device cache was inspected read-only during planning: Wi-Fi disconnected, both cellular providers suspended after timeouts, with no currently valid cellular sample. No live API refresh or permission changes are part of implementation. Test grouping, two clients, narrow widths, mouse targets, unknown-data transitions and one discovery query per job using private fixtures.

### Grouping and unknown-cellular verification

- All 12 tmux status tests pass, including optional upstream battery source with mocked APIs. Native 40/80/120-column clients verify current-number grouping, later numbers directly after windows, two independent clients, hidden default badges, narrow overflow, mouse targets, mode indicators, colors, theme/config reloads and failure clearing. A dedicated attached-client case confirms both segments share exactly one discovery query and captures `1 fixture 0:window 2` with the intended spacing and suffix styling.
- Android adapter tests pass 8/8, covering known active/inactive, partial/missing/invalid/timed-out cellular helpers, stale/expired cache transitions and suspended-provider nonexecution. The rendered unavailable-data indicator uses the theme's muted color. Androidots regressions pass status 27/27 and session discovery 28/28; the targeted theme connector test passes. No theme template or provider/cache implementation changed in this follow-up; earlier broader-suite limitations remain documented above.
- Changed sources: the canonical tmux config, Termux session adapter and Android indicator adapter; focused status/Android tests; parent README, testing guide, architecture/platform/testing/theme references and this plan; Androidots README and status integration documentation. Existing unrelated work is preserved.
- Reload with **Ctrl-Space q** or **Ctrl-b q**, or `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"`. No theme refresh is required for this follow-up. To restore live cellular readings after the observed suspended providers, run `"$HOME/dots/androidots/bin/termux-cell-status" --refresh --both` interactively and retry after granting any requested permission. The muted `?` fallback does not require initialization. No live reload, Android API refresh, permission changes, installation, commits or pushes were performed.

Python syntax and both repositories' whitespace checks pass. All 180 other relative Markdown targets in changed documents resolve; the existing missing Yazi plugin README link in `docs/testing.md` remains.

## Network uncertainty repair

Implemented: replaced disappearing unknown Wi-Fi and the cellular-specific unavailable marker with a neutral muted `?` in the existing two-character network slot. Only fresh disconnected Wi-Fi plus fresh confirmed inactive telephony data hides the segment. Retained positive Wi-Fi/data observations remain eligible with `~`; stale negative or indeterminate evidence shows `?~`. Registered-cell signal alone never establishes active mobile data. Preserve signal colors, battery, clock, lower-row styling, normal JSON reads and all Androidots cache/permission gates.

Acceptance follows the [presentation contract](../docs/presentation.md#acceptance-gate): isolated helper/provider failures, stale/expired/partial snapshots, explicit successful recovery, disabled-helper nonexecution, bounded reads and private attached-client captures at 40/80/120 columns with repeated reloads. Recheck shared files before narrow edits to preserve concurrent styling work. No live API refresh, permissions, installation, live-server reload, commits or pushes. Baseline: Android adapter 8/8; Androidots status 27/27; tmux status 12 tests, one optional battery-source skip.


### Network repair verification

- Parent Android adapter: 11/11 tests passed, covering missing/failed/malformed/timed-out helpers, unknown Wi-Fi with each cellular activity state, signal colors, neutral/stale markers, independent device freshness, response limits, stderr suppression and helper descendant cleanup. Copied real Androidots code with mocked provider commands verifies failure suspension, expiry and explicit successful Wi-Fi/cellular recovery.
- Native tmux status: 13 tests completed successfully, with one optional upstream battery-source check skipped. Attached clients on private sockets rendered the actual upper row at 40/80/120 columns, verifying fixed slot/battery positions, colors, hidden/unknown/stale/recovered states and two reloads at every width. The first run exposed an attachment race in the new test, fixed by waiting for the client; an existing fixture cleanup race also occurred once and did not recur on the successful full rerun. The inactive leftover fixture was removed.
- Androidots regressions: status 29/29, sessions 28/28 and launcher 7/7 passed. Provider/cache production code is unchanged; tests confirm registered-cell signal does not establish data activity or telephony-device freshness.
- Theme workflow: 27 tests completed successfully, one optional Pi native-loader check skipped. Broader themes: 28/29 tests passed; the previously recorded `test_neovim_all_native_families` again timed out at 40 seconds and additionally reported a temporary-directory cleanup race. The inactive leftover fixture was removed. No theme/Neovim implementation changed.
- Changed Python sources compile and both repositories pass `git diff --check`. All 181 valid relative Markdown targets in changed documents resolve; the existing missing Yazi plugin README target in `docs/testing.md` still blocks the full documentation checker. Starship formatting inside code fences is excluded from Markdown-link checks.
- Read-only cache inspection after implementation found Wi-Fi and both cellular providers suspended with no current network values. Applying only the selector to those snapshots produced the neutral `?`; no API requests or cache mutations were made by this inspection. Live Android recovery and device font appearance remain owner-run checks.

Existing directory-linked installations use the repaired adapter on the next status refresh, normally five seconds. No theme refresh is required. Optional owner-run reload: `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"`, or **prefix + q**. Recover suspended providers interactively with the server's HOME/XDG cache environment:

```sh
"$HOME/dots/androidots/bin/termux-wifi-status" --refresh --both
"$HOME/dots/androidots/bin/termux-cell-status" --refresh --both
```

These explicit recovery commands may encounter Android permission prompts and are never placed in recurring jobs. This work did not reload the live server, change permissions, install packages, commit or push. The three pre-existing untracked Fish completions and all unrelated styling files were preserved.

## Compact joined badges and teal/blue styling

Implemented (supersedes the earlier lower-row styling): join the current Termux number and optional project name as ` 1:dots `; default sessions keep ` 1 `. In Termux only, windows whose full name exactly matches the full tmux session name show only their number; other windows show ` number:name `. Each segment owns one leading/trailing space, with no extra separators. Current badges use `hint`/bold `darker_background`; inactive numbers use row `background`/bold `hint`; selected windows use `selection`/bold `info`; inactive windows use `dark_background`/`light_foreground`. The clock uses `dark_background`/bold `info`, preserving 12-hour formatting without a leading zero or icon.

Keep names in tmux's formatting layer, preserve one discovery job, per-client highlighting, independent clipping and native window mouse ranges. Add an internal three-field numeric split while retaining the older helper interface for configurations not yet reloaded. Canonical config owns label/layout logic; the theme supplies semantic colors and references the configured label format. Preserve concurrent network repair work. Validate the presentation gate with attached private clients at 40/80/120 columns, default/project/name transitions, exact padding, special names, theme/config reloads and non-Termux behavior. No live activation or Android API calls.


### Compact badge verification

- Baseline before styling: tmux status 13 tests completed successfully, one optional upstream battery-source skip. After styling: 15 tests completed successfully, one optional skip. Private attached clients at 40/80/120 columns verify exact padding, current number/project joining, matching/differing/case-sensitive window labels, default-name hiding, literal Unicode and format punctuation, per-client selection, independent overflow, mouse targets, modes, one shared discovery query, repeated reloads, and theme-only color refresh. Follow-up native checks also pass for unchanged non-Termux matching-name labels and omission of a colon when no project text fits.
- Androidots session discovery 28/28 and status 29/29 pass. The existing network repair production code and its tests were not edited by this styling work. Theme workflow: 27 tests completed successfully, with one optional Pi native-loader skip. Broad themes: 28/29 passed; the previously recorded 40-second `test_neovim_all_native_families` timeout remains, with no additional failures. Parent Android adapter: 11/11 pass on the final run after the broad suites finished. Earlier concurrent runs exposed the existing real-cache test's timing sensitivity (fresh samples became stale or unavailable under load); the network adapter and its tests were left unchanged.
- Python syntax and whitespace checks pass. All 180 valid relative targets in changed parent documents resolve; the previously recorded missing Yazi plugin README in `docs/testing.md` still fails the full documentation checker.
- Activation remains owner-run: `dots theme refresh`, then `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"` (or **Ctrl-Space q** / **Ctrl-b q**). No live tmux reload, Android API refresh, permission change, package installation, commit or push was performed.

## Accent indicators follow-up (2026-10-22)

COPY, PREFIX and ZOOM use bold theme `accent` text on the inherited row background. The theme template publishes `@dots-indicator-fg`; the main config owns the conditions, spacing and trailing style reset, with blue as its unpublished fallback. Theme-only reloads update the color without replacing layouts. Follow the shared presentation gate: verify all three indicators through native cell/attribute capture, theme reloads and the Termux/non-Termux layout gate in isolated servers. Native Linux/WSL acceptance remains pending; native Windows PowerShell has no tmux equivalent or affected app destination. Live activation uses normal journaled theme refresh followed by only the updated status-right setting and popup binding.

Verified on Termux/tmux 3.8: the status suite ran 16 tests successfully with one optional upstream battery-source skip. Native captures prove accent foreground, inherited background and bold attributes for COPY/PREFIX/ZOOM; reload and platform-gate cases pass. The isolated dark/light publication case also checks the published indicator accent. All 818 documentation links and `git diff --check` pass. Live refresh retained Catppuccin Mocha, and the selectively applied status-right setting resolves to `#[fg=#cba6f7,bold]` with the existing conditions and trailing reset.

## Accent indicator background revision (2026-10-22)

The approved revision changes COPY/PREFIX/ZOOM to bold `darker_background` text on `accent`. The template publishes `@dots-indicator-fg` and `@dots-indicator-bg`; unpublished fallback is black on blue. Existing conditions, spacing and the trailing reset remain, and popup styling is preserved. Acceptance covers native foreground/background/bold attributes and restoration of row styling after the indicators, dark/light publication and both layout modes. Activate through the existing theme publisher and selectively reload status-right. Native Linux/WSL acceptance remains pending; native Windows PowerShell has no tmux equivalent.

Verified on Termux/tmux 3.8: 15 status tests passed with one optional battery-source skip, including all three indicators and restoration of background and non-bold text after the trailing reset. The dark/light connector publication case, all 818 documentation links and whitespace checks pass. Live journaled refresh and selective status-right reload completed; the effective indicator style is `fg=#101019,bg=#cba6f7,bold`, and the popup border is unchanged.

Indicator padding follow-up: each active condition now emits ` COPY `, ` PREFIX ` or ` ZOOM `, with both spaces inside the accent-colored span. Inactive indicators emit no padding. This is a status-right-only change; activate it selectively without theme publication.

Padding verification passed: the focused native two-client status test checks each padded label and the leading space's colors, alongside bold text and the trailing style reset. All 818 documentation links and whitespace checks pass. The running server's status-right setting was selectively reloaded and verified; no theme refresh was performed.

## Current-window and mode colors (2026-10-23)

The shared template now uses `lighter_background` for the current window on every tmux platform, retaining bold `info` and no underline. COPY and ZOOM use bold `darker_background` on `green`; PREFIX has independent `@dots-prefix-fg`/`@dots-prefix-bg` colors, bold `accent` on `dark_background`. Each conditional label retains one space on each side and its own style/reset. Fallbacks are bright-black for the current window, black on green for modes and blue on black for PREFIX. Layout stays in the main config. Native Linux/WSL rendering acceptance remains pending; native Windows PowerShell has no tmux equivalent or affected destination. Verify native individual/combined indicators, narrow layouts and theme reloads, dark/light publication and both platform layout paths, then activate through journaled theme refresh plus selective status-right reload.

Verified on Termux/tmux 3.8: 15 status tests pass with one optional battery-source skip, including individual and simultaneous COPY/PREFIX/ZOOM colors, bold text, padding, style resets and 40/80/120-column layouts. The initial run exposed one stale window-color assertion (updated) and a clock-color check that passed on rerun without clock changes. Dark/light publication and both platform format paths pass; all 834 documentation links and whitespace checks pass. Live refresh retains Catppuccin Mocha: current-window background `#313244`, COPY/ZOOM `#101019` on `#a6e3a1`, PREFIX `#cba6f7` on `#161622`, all intended bold styles verified. Publication recovery remains in the generation journal.
