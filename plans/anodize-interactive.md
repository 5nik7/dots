# Anodize user themes and interactive previews

**Status: Implemented; native desktop acceptance pending.** Owner-approved scope,
2026-10-21.

New themes use the platform user configuration root (`~/.config/dots/themes` by
default on POSIX, `%APPDATA%/dots/themes` on Windows). Explicit `--builtin` saves
into the checkout. Journaled promotion moves user themes by default; copying
requires a different ID. Existing themes are not migrated or activated.

Missing-input selection and explicit `--interactive` flows cover authoring,
inspection, import/export, application and promotion. They use FZF, then Gum/plain
fallbacks; selection is separate from approval. Mode selection previews temporary
generated candidates. Zsh FZF-tab shares opt-in previews without engine calls in
ordinary completion or startup. Candidate state is transient.

Anodize and Dots views share exact theme foreground/background and syntax samples,
including FZF panes. Branding, raw interfaces and existing palette/style details
are preserved under the [presentation acceptance gate](../docs/presentation.md#acceptance-gate).

Acceptance: isolated storage/collision/promotion/rollback/undo tests; candidate
equality, cleanup and cancellation; engine-free completion; native Termux FZF and
Zsh preview checks at 40/80/120 columns; matching native PowerShell controller
paths and documented Windows destinations. Native Windows PowerShell 5.1/7,
Linux and WSL terminal acceptance remain pending where unavailable. No live
publication, wallpaper activation, separate plugin edits or commits.

## Verification on native Termux

- The isolated Anodize verifier built a fresh engine and passed Go tests/vet,
  the 18 authoring tests and 11 logo tests. The integration suite passed 5 tests;
  the native Python authoring controller passed 3 fixture tests.
- All 11 interactive tests passed across the complete 10-test run and focused
  reruns after adding existing/imported-palette equivalence coverage. Coverage
  includes both storage roots, copied backgrounds, promotion/copy receipts,
  rollback/recovery/undo, source drift, draft approval, temporary cleanup and
  literal preview tokens. Cached previews match direct generation for all 23
  modes in light/dark image fixtures and direct commands for existing/imported
  palettes. Cached hover does not invoke the engine again.
- Actual FZF and copied-source Zsh FZF-tab tests passed at 40/80/120 columns,
  including cancellation, pane colors, mode candidates, Dots theme previews
  without an engine, and cache cleanup. These PTY checks do not establish font
  appearance or native desktop terminal behavior.
- The broader `tools/zsh_interactive.py --samples 3` run passed completion labels,
  literal insertion, Tab/cd/history pickers and repeated reloads with unchanged
  hooks, FZF options, completion paths and key bindings. Its Anodize label-width
  expectation now derives from current completion metadata. Warm input-ready
  median was 2.18 seconds in the copied public fixture; no before/after startup
  speed claim is made.
- Theme-picker (16), theme-command (12), file-color (11), Bash dispatcher (24)
  and file-picker (19) regressions passed. The file-picker suite required a
  focused rerun after correcting shared error wording. Native-controller checks
  passed 11 tests; the unavailable native PowerShell engine check was skipped.
- The broader Zsh suite passed 28 of 29 tests. Its theme-switch fixture lacks
  `default/file-colors.toml`; the same failure was reproduced with pre-change
  tracked source in the disposable fixture. This unrelated fixture remains
  unchanged.
- The one-pixel image fixture took approximately 1.2–1.6 seconds for 23 modes
  including a second direct-generation comparison pass. This is advisory
  fixture evidence, not a large-image performance claim. Startup and ordinary
  completion retain engine-free paths.
- Generated completion/manual freshness, relative Markdown links, Bash/Zsh syntax
  and diff whitespace checks passed. Focused ShellCheck passed for the new
  wrapper, Anodize bridge and theme command adapter; catalog checking retained
  the existing shared-global `SC2034` exclusion. Full completion-file ShellCheck
  exceeded the bounded CPU limit, including with extended analysis disabled;
  that lint check is incomplete. Resource bounds were used after the Termux crash.

Native Windows PowerShell 5.1/7, Linux and WSL terminal acceptance remain pending.
Application connector destinations are unchanged. No live theme selection,
publication, wallpaper action, repository commit or plugin installation was made.
