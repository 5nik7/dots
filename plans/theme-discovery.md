# Shared theme discovery

**Status: Implemented; pre-existing verification limitations retained.** Owner-authorized behavior-preserving Bash refactor; general Go migration remains paused.

## Scope

Move selectable-ID enumeration, current-ID resolution and native family/flavor enumeration into a data-only module under `lib/dots/themes`. Commands, switcher, views and completion share it. Preserve existing listing versus completion eligibility: listings validate and deduplicate flat IDs; completion retains literal candidates and duplicates. Preserve duplicate-selection refusal, Pywal without generated input, root overrides, native palette validation, ordering and output formats. Loading the module defines functions only: no scans, cache writes, command dispatch, UI or extension execution.

Correct stale bundled theme counts in user documentation and workflow tests. The formerly masked accent assertion now checks the source palette rather than an outdated blue value; both HEAD and the working tree return the source's mauve accent. No publication, journal, adapter, command grammar, startup or platform support change; no new domain term or ADR is needed.

## Acceptance

- [x] Characterize shared discovery using controlled bundled/user roots, invalid names, duplicate IDs, symlinked/broken palette files, Unicode/space paths, native palettes and Pywal.
- [x] Verify updated data is visible on the next completion request across Bash/Zsh/Fish; current-ID resolution remains shared and scans nothing when loaded.
- [x] Run theme, workflow, picker, dispatcher, shell-init and Zsh/FZF-tab regressions in owned roots; distinguish existing failures and unavailable checks.
- [x] Run Bash syntax/ShellCheck, documentation links and diff checks; measure isolated theme initialization before/after sequentially.
- [x] Synchronize architecture and theme reference ownership, completion reference and user-facing counts.

Follow the [presentation gate](../docs/presentation.md#acceptance-gate). Existing shared renderers and layouts stay unchanged; theme suites cover plain/forced/disabled output, native palette views at 40/80/120 columns, empty/error results and undecorated data. Picker PTYs cover interaction; no new interaction or mutation view is introduced. Record visual-review and native-platform limits separately.

## Evidence

Pre-change focused review: seven tests passed; `Workflow.test_flat_palette_catalog` failed expecting 33 selections but observing 34. The inventory has 33 flat variants plus dynamic Pywal. Pre-change five-sample native Termux benchmark: `/data/data/com.termux/files/usr/tmp/dots-theme-bench-naoeswd7/results.json`; warm medians: unpublished Catppuccin init 90.5 ms, selected init 71.7 ms, Tokyonight init 111.1 ms, selected init 71.6 ms; unchanged prompt 108.5 µs/call. First invocation is not a controlled cold-cache measurement.

### Implementation and final verification

`discovery.bash` defines current-ID resolution and one in-process enumeration helper returning `DT_DISCOVERY_IDS`, reset for every request. Existing listing/switcher callers retain line output. Completion reads the array directly; an initial subprocess-based implementation was rejected after timing showed extra latency. Completion's inherited `DOTS` root is preserved even when the installed executable belongs to a different checkout. Native flavor presentation still validates metadata before enumeration.

Native Termux results, 2026-09-30, all in owned roots:

- Theme suite: 28/29 passed; `test_neovim_all_native_families` exceeded its existing 40-second child deadline. It passed individually earlier, and the same timeout reproduced with HEAD versions of every changed runtime file restored in a separate fixture. The other editor case passed. No timeout or assertion was weakened.
- Workflow 14/14, picker 14/14, dispatcher 23/23, Zsh 17/17 and theme plugins 20/20 passed. Shell-init passed 27 cases with three unavailable optional-interpreter cases skipped (30 total).
- Two new discovery tests cover inert sourcing, native/current-ID parity, result reset, literal completion eligibility, duplicate refusal, next-request freshness and alternate inherited checkout roots. Dispatcher tests exercised real Bash/Zsh/Fish Tab. Native Zsh/FZF-tab PTY acceptance passed with unchanged hooks, FZF, fpath and key bindings (`dots-zsh-zl918a4y`).
- Bash syntax and focused ShellCheck passed, excluding existing SC2015/SC2031 diagnostics and using explicit source search paths. Diff whitespace checks passed. All links in changed documents resolve; the repository-wide gate still fails the pre-existing `docs/testing.md` link to the removed Yazi symlink-plugin README. That unrelated link is not changed.
- Existing renderer tests and picker PTYs cover 40/80/120-column views and output controls. Human layouts are unchanged; no new pixel-level visual review, desktop Linux/WSL/native Windows claim, Go build or live theme activation is included.

Final 20-sample sequential HEAD/working-tree discovery measurement: `/data/data/com.termux/files/usr/tmp/dots-theme-discovery-bench-kb476l68/results.json`. Warm medians in milliseconds: list 81.68/75.90, flat-ID completion 41.79/42.18, family completion 41.73/41.52, core sourcing 30.71/30.57. These advisory samples show no material completion regression; they do not establish a speed improvement.

Post-change five-sample initialization measurement: `/data/data/com.termux/files/usr/tmp/dots-theme-bench-n4i3yqne/results.json`. Warm medians: unpublished Catppuccin 61.1 ms, selected init 46.4 ms, Tokyonight 118.5 ms, selected init 68.1 ms; unchanged prompt 96.8 µs/call. Mobile-device variation and small sample counts prevent attributing these differences to the refactor. No discovery scans or subprocesses were added to prompt refresh.

No repository mutation engine, generation schema, command grammar, domain glossary or decision changed. No commit or push performed.
