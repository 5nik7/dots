# Unified keybinding browser

Status: implemented locally; native Windows and personal terminal acceptance pending.

Implement the approved `dots keys [APP]` browser for Zsh, Bash, PowerShell,
tmux, Neovim, Yazi, FZF, Kitty and Television. Capture caller-owned live state
on demand; otherwise parse literal configuration and installed default data.
Never execute configurations or binding actions to discover keys. Preserve
explicit coverage and source distinctions, exact JSON and existing user edits.
Use content-sized category/app menus, then FZF popup center,99% in tmux and ordinary FZF elsewhere. Retain the old tmux
route. Add the Termux vi-mode insert Backspace callback fix.

Acceptance includes native caller capture, configured parsing, malformed inputs,
control/sequence notation, live precedence, optional dependencies, popup argv,
40/80/120-column presentation, JSON, completion and isolated Neovim/tmux/ZLE
checks. Follow the [presentation gate](README.md#presentation-gate-for-every-plan).
Update docs and the local wiki. Native Windows runtime acceptance is separate.

## Local verification

### Middle-dot prompts and narrower keys (2026-10-26)

Implemented locally: separate selected app/mode prompts with an unspaced
middle dot (`󰌆 zsh·viins:` / `󰌆 all·viins:`), retaining the trailing colon and
input space. Reduce only the keys column cap from 24 to 16 terminal cells;
app/mode/key caps are now 12/18/16, including ellipsis. Keep narrow-screen sizing,
full preview values, mode navigation and data output. No route or schema changes.

Acceptance: update existing prompt/cap assertions, run owned FZF checks at
40/80/120 columns, live Zsh/tmux and exact-client launcher checks, and shared
controller print/JSON checks. Both frontends share the renderer; native Windows
terminal evidence remains pending. Update canonical docs and local wiki.
Changes take effect on the next picker opening; no reload, commit or push.

Verification: ten runnable browser checks, 20 core key checks, eight tmux checks,
the two-client launcher key/mode check and two native-controller fixtures passed
(41 passed; one native PowerShell preview check skipped). Real FZF checks cover
40/80/120 columns, retained searches, complete previews and selected-mode prompts.
The tmux test clients now explicitly enable UTF-8 with `-u`; their locale-free
fixture previously substituted terminal characters for the middle dot.
Python parsing, whitespace and 841 Markdown links passed. The local wiki was
rebuilt and checked healthy, retaining transaction
`ddefc47690294b21841c28f18eb318e8`.

### Aligned columns, compact mode chooser and preview (2026-10-26)

Implemented locally: align visible app/mode/key columns to their longest
values with 12/18/24-cell caps and ellipsis, shrinking for the list pane while
reserving description space. Use orange modes and matching preview value colors.
The preview starts at the left edge with Keys, Action, Mode and no title, wrapping
to the actual preview width. Remove provider/mode banners from picker headers.

Alt-M opens a compact FZF chooser containing all and sorted available modes.
Preserve the binding query, snapshot, numeric identities and exact tmux client.
Escape returns unchanged; Ctrl-C cancels browsing. A selected mode moves into
the prompt (`󰌆 zsh:viins:` or `󰌆 all:viins:`); all-mode prompts stay compact.
Shared selector event maps and detail indentation are opt-in. Print/JSON,
other selector defaults, shell startup and Windows app destinations are unchanged.

Acceptance: 40/80/120-cell light/dark/plain/icon layouts, Unicode ellipsis,
preview ordering/colors/wrapping, selection/cancellation and retained searches,
unknown/empty modes, one capture, stable identities, temporary cleanup and
exact-client handoff. Run isolated key/IPC/tmux, shared-menu/launcher, resource
and affected file/theme picker checks sequentially. Both dispatchers share the
implementation; native Windows PowerShell 5.1/7 and Linux/WSL terminal evidence
remain separate from Termux fixtures. Synchronize canonical docs and local wiki.
No live reload, commit or push is included.

Verification: 20 core key checks, ten runnable browser checks, 15 resource
presentation checks, eight private-server tmux checks, 11 live Zsh transport
checks, 23 shared-menu checks, 15 launcher checks, 19 file-picker checks, three targeted theme-picker
checks, ten runnable defaults/override checks, 24 Bash dispatcher checks and two
native-controller fixtures passed. Two native PowerShell checks were skipped
because no engine is installed. Real FZF tests at 40/80/120 columns cover mode
selection, current-mode focus, Escape back, preserved binding searches and exact
preview identity. Current-mode positioning runs on FZF's load event: the native
Enter-without-search check caught the earlier start event firing too soon.

Owned two-client tmux acceptance confirms that binding and mode popups stay on
the invoking client and return to the launcher with its query intact. Live Zsh
mode selection still captures once and preserves a partly typed shell command.
Plain rendered samples and palette fixtures cover alignment, ellipsis, orange
modes and unindented wrapped previews; personal font/color review and native
Windows/Linux/WSL terminal acceptance remain separate.

The broad launcher run completed after releasing one fixture-owned tmux client
that stalled in its old teardown wait; the focused two-client key/mode navigation
case passed separately without intervention. Concurrent launcher prompt work was
preserved and the final launcher checks used its updated prompt expectations.
Both command validators accepted 139 extensions. Python parsing, Bash syntax,
ShellCheck, whitespace and 841 relative Markdown links passed. The local wiki
was already current at the final build (`unchanged`) and checked healthy. No live
shell/tmux reload, commit or push was performed.

### Counted categories and conditional mode labels (2026-10-26)

Implemented locally: main/All prompts use `󰌆 :`, specific apps use
`󰌆 APP:`, respecting disabled icons. Binding rows show mode only when the mode
filter is all; the active mode remains in the header and preview. Keep original
record identities and query text while swapping between both row presentations.

Remove Apps from the main menu and show All plus nonempty app entries with
`app · [47]` counts. Use the existing muted metadata color for the complete count
suffix, preserving it on selection and excluding ANSI from geometry. Count the
source/default-filtered snapshot across all modes before opening the menu and
reuse it after selection. Direct app routes remain targeted. Explicit `apps`
routes and print/JSON reports remain compatible; an empty menu prints the normal
empty result. Preserve the shared tmux client context and live Zsh capture.

Acceptance: exact prompts, conditional labels on initial mode and cycling,
counts/totals, zero hiding, empty datasets, one collection/capture, direct-route
scope, 40/80/120-column light/dark/plain/icon views, stable previews and query
retention, native tmux cancellation and unchanged machine output. Measure
controller-to-menu latency in owned fixtures. Both dispatchers share the change;
native Windows/PowerShell acceptance remains pending when unavailable, with no
Windows destination changes. Update canonical docs and regenerate/check the wiki.
No cache, startup scan, live reload, commit or push is part of this change.

Verification: the 20 core key-browser, 12 runnable mode-browser, eight tmux,
13 launcher, 11 live Zsh transport, 22 shared-menu, ten runnable default/override
and two targeted native-controller checks passed in owned fixtures. Two native
PowerShell checks were skipped because no engine is installed. Real FZF checks
covered counted-menu selection and conditional mode fields at 40/80/120 columns;
fixtures covered plain/icon views, light/dark metadata colors, stable record
selection, preserved queries and one live capture/collection. Native Windows,
native Linux/WSL and personal terminal/font acceptance remain separate.

The warm controller-to-menu fixture median increased from 0.42 ms to 238.54 ms
for 792 bindings because collection now happens before the menu opens. Five
post-warmup samples were 198.58, 198.14, 238.54, 399.74 and 248.86 ms. The same
owned fixture stubs the picker/native tool discovery; this measures controller
preparation, not FZF launch or a real source-pane IPC round trip. Selecting an
app reuses the collection, and direct app routes keep their existing scope.

Both command validators accepted 139 extensions. Python parsing, whitespace
and all 841 relative Markdown links passed. Canonical docs and the local wiki
are synchronized and healthy; the build retained transaction
`f3869c5426844b7abaa1d417f89c501b`. The presentation changes take effect on the
next picker opening. No shell/tmux reload, commit or push was performed.

### Compact prompts and mode cycling (2026-10-26)

Implemented locally: apply inline-right FZF information to key menus;
use `󰌆 keys:` / `󰌆 APP keys:` binding prompts, respecting disabled icons.
Specific app lists omit only the repeated app field. Alt-M cycles all and the
alphabetically ordered modes from the captured, source/default-filtered dataset,
preserving the search in the same popup. The active mode stays in the header.
Interactive `--mode` selects the initial mode; print/JSON retain exact filtering.
Unknown initial modes show an empty view from which Alt-M returns to all.

Reuse the shared selector through opt-in info/binding/initial-index controls.
Private temporary rendering data supports in-place reloads with stable record
identities; mode changes do not recapture providers or execute binding text.
Use native PowerShell binary output for reload records on Windows, not Bash or
WSL. Other selectors, JSON v1 and application destinations remain unchanged.

Acceptance: 40/80/120-column plain/colored layouts, icon settings, all/specific-app
prompts, mode wraparound, retained queries, empty/single/unknown modes, preview
identity, cleanup, one live capture per opening and quiet tmux cancellation.
Run isolated key/IPC/tmux/shared-menu regressions and native-controller fixtures;
native Windows PowerShell 5.1/7 and Linux/WSL acceptance remain separate. Update
help, metadata, canonical docs and the local wiki. No live reload, commit or push.

Verification: eight new browser checks passed, including real FZF mode cycling,
unknown initial modes, retained queries and correct original-record selection at
40/80/120 columns; native PowerShell byte-stream execution was skipped because no
engine is installed. The eight tmux tests passed, including mode cycling to viins
from a live Zsh popup with exactly one capture and a preserved partial command.
The 11 IPC, 20 existing key-browser, 22 shared-menu, ten defaults/override, 24 Bash
dispatcher and two targeted native-controller checks passed. The defaults suite
also skipped its native PowerShell smoke check. Both command validators accepted
138 extensions; shell syntax, ShellCheck, whitespace and documentation links passed.

The file-picker regression initially passed 18 cases and timed out in the content
preview-toggle case at three widths. That case subsequently passed at all three
widths without a code change; a 40-column owned baseline with the new selector
options removed also passed. Record this initial timing failure rather than
claiming an uninterrupted broad-suite pass. Native Windows terminal acceptance
and actual human font/color review remain pending.

Canonical documentation and the local wiki are synchronized and checked healthy;
the final build retained transaction `13a10eaeac0e42888b95363df36c353e`. Changes
take effect on the next picker opening. No shell/tmux reload, commit or push was
performed for this presentation change.

### Live Zsh capture from tmux (2026-10-26)

Implemented locally: the approved change requests loaded Zsh maps from
the originating pane through a private ZLE socket, using an anonymous pipe and
a bounded background sender. The listener exists only at a prompt, is closed
before commands run, and is deduplicated across reloads. Snapshot reads remain
on demand; no keymap scans or persistent snapshots are added to startup/prompts.
One-second client and two-second worker deadlines, owner-only runtime endpoints,
exact server/pane matching and ambiguous-response refusal protect editing.
The picker labels live versus configuration-only coverage. Explicit caller
snapshots retain priority and configured-only requests bypass capture.

Acceptance: owned ZLE/tmux/FZF sessions, dynamic mappings, modes, reloads, nesting,
pane routing, cancellation, buffer/cursor/status preservation, missing/busy/stale
responders, malformed/oversized responses, concurrency/deadlines, 40/80/120-column
coverage, JSON and startup measurements. Follow the existing presentation gate.
Native Windows keeps its existing caller capture; the new Unix socket adapter is
Zsh-only on Termux/Linux/WSL, with native Linux/WSL acceptance pending.
Update source docs and regenerate/check the local wiki. Activation may replace
only the tmux shortcut after retaining its old value; existing Zsh sessions need
a targeted capture-adapter reload. Backspace mappings remain unchanged so the
reported failure can be inspected. No commits or pushes are authorized.

Verification: all 11 private ZLE/transport tests, 20 key-browser tests, eight
private-server tmux tests and nine shell-environment tests passed. The actual
tmux/FZF popup displayed a live-only widget and preserved a partial command on
cancellation. An additional owned Deja + vi-mode NEX fixture captured 565 loaded
bindings, including history search and FZF, before and after repeated reload;
capture preserved editing and the tested Backspace action. No live personal
shell was injected with test input.
The five personal-key configuration tests, three native ZLE editing/history
tests and ten defaults/override tests passed; one native PowerShell defaults
check was skipped. Command validation, shell syntax, ShellCheck, whitespace and
relative Markdown links passed.

Three alternating warm startup samples measured medians of 1.689 seconds without
the adapter and 1.581 seconds with it; this is no observed regression in a noisy
local fixture, not a speedup claim. One hundred listener close/open cycles averaged
3.1 ms. The integration-only Zsh environment and portable-link checks passed;
native PowerShell was unavailable. The broader personal startup/reload test failed
its existing color-variable assertion (exit 7, theme initialization diagnostic).
An owned baseline with the new adapter disabled failed identically. Native
Linux/WSL, Windows and the user's existing terminal remain separate acceptance.

Activation: replaced and verified only the running tmux server's Prefix → ?
binding, adding the source-pane context while preserving quiet cancellation.
Its old command and note are retained in
`/data/data/com.termux/files/usr/tmp/dots-keys-tmux-1jajp7qh/previous-binding.conf`.
Existing Zsh sessions still need the documented targeted adapter reload.
Source documentation and the generated local wiki passed synchronization checks;
wiki transaction `ff4ed69c6e5a4589bebf46e30e99dcfc` retains recovery. Nothing was
committed or pushed.

### Yazi defaults and Codex CLI extension (2026-10-25)

Implemented: bundle the complete pinned 254-binding Yazi shipped preset and the Codex CLI 0.164.0 action inventory plus contextual controls. Preserve configured sources, raw notation and the version-1 JSON interface. Evaluate Yazi prepend/replacement/append precedence; read user Codex `tui.keymap`, global fallbacks, alternatives, leader/two-stroke chords and explicit unbinding. Keep these references offline and activation unverified. Register Codex in both controller surfaces, metadata/completion, category/app menus, and targeted shell adapters.

Windows destinations: Yazi retains `%APPDATA%/yazi/config` and its supported overrides; Codex uses `CODEX_HOME` or the native user home's `.codex` directory. No application installation or binding mutation is part of this extension. Follow the existing [presentation gate](README.md#presentation-gate-for-every-plan), including plain/JSON output and 40/80/120-column checks.

Local verification: 10 defaults/override tests passed, with one native PowerShell smoke check skipped; 20 existing browser tests, seven private-server tmux tests, 24 Bash dispatcher tests and the ZLE Backspace acceptance test passed. The native-controller suite passed 13 tests with one missing-engine skip after clearing the inherited `YAZI_CONFIG_HOME` from the runner environment; its original failure was an existing fixture-environment leak, not a path implementation change. Both command validators accepted 137 extensions; Python/shell syntax, ShellCheck, whitespace and Markdown-link checks passed. The generated action catalog reproduces from the pinned source input. The nine shell-environment tests passed. Documentation links and the generated local wiki are synchronized; wiki build transaction `c019b7057d614f7988f66cc76d63b705` retains recovery. Direct read-only invocation reports 254 Yazi defaults plus 10 existing custom bindings, and 519 Codex reference rows plus one existing custom mapping. Native Windows PowerShell 5.1/7 and actual terminal key delivery remain separate acceptance checks. Project/profile/command-line Codex layers and full runtime conflict validation are explicitly outside the static reader.

### Earlier browser verification

Category refinement: implemented and verified locally. Interactive `dots keys` and
Prefix → ? open the icon category menu; Apps offers provider counts and availability.
Direct `dots keys all|APP` bypasses categories. Binding previews occupy 45%, with
muted metadata and bold bright-magenta keys. Noninteractive reports and caller
snapshots are preserved. The private-server test exercised category → Apps → tmux,
category → All, and cancellation back to the original pane. After it passed,
only the running server's stale `?` binding was replaced; its previous value was
retained in a private temporary recovery file. Other bindings were not reloaded.

Cancellation refinement implemented: only status 130 is normalized in the tmux
shortcut launcher. All seven tmux tests pass, including Escape/Ctrl-C at the
category, app and binding stages, direct CLI cancellation, and preserved genuine
failure statuses/diagnostics. The live binding was updated after these checks,
with its previous value retained in a private temporary recovery file.

- Key browser: 20 isolated tests passed, including invoking Bash/Zsh maps,
  configuration parsing, live precedence, notation, JSON, native Neovim mapping
  snapshots, category navigation, caller snapshot retention, menu sizing,
  45% previews, field colors and popup color policy.
- Tmux: five tests passed, including private-server notes/prefixes, missing
  dependencies, 40/80/120-column output and a real FZF popup launched by the
  repository binding.
- ZLE: both Ctrl-H and DEL passed after normal-to-insert transitions through
  `i` and `a`, including repeated local reloads and callback deduplication.
- Shared regressions: resource presentation (15), file pickers (19), Bash
  dispatcher (24), shell environment (9), and native controller (13 passed,
  one native PowerShell skip).
- The broader Zsh suite passed 26 of 29 tests. Three existing failures concern
  MSYS platform expectations, missing optional-tool fixture preparation, and
  historical FZF/theme fixture paths. All three reproduce with the original
  integration file in owned fixtures; they are outside this change.
- Both command validators accepted 137 extensions. ShellCheck, shell syntax,
  Neovim StyLua, whitespace and documentation-link checks passed.

Seven alternating warm startup samples in owned public fixtures measured Bash
medians of 318.5 ms before / 318.0 ms after and Zsh 217.3 ms / 218.3 ms. These are
local noisy measurements, not cross-platform performance guarantees. Startup
installs the adapter function without querying maps or launching providers.

Native PowerShell 5.1/7 PSReadLine capture, native Windows preview execution,
GitHub wiki rendering and the user's actual keyboard remain named acceptance
checks. Existing running shells and complete tmux configuration were not reloaded. No commits
or publication are part of this change.
