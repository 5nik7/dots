# Shared Bash/Zsh configuration

Status: Implemented, 2026-09-30.

Owner-approved scope: use Zsh's effective command behavior in both shells, share user-facing functions and aliases, retain Bash-only helpers (`ff` becomes `findfiles`), and give Bash practical parity through native installed tools and Readline vi mode. No new editing plugins or dependency installation. Keep portable public settings shared, private/platform hooks native, and script utilities separate from interactive configuration. Native completion/widget/bootstrap internals retain their shell adapters. Existing Git/worktree helper semantics are not redesigned.

- [x] Consolidate commands, compatibility loaders and portable environment settings.
- [x] Add Bash prompt, theme refresh, completion, history and optional native integrations.
- [x] Verify isolated public interfaces, reloads, missing/failing tools, path handling and native PTY interaction.
- [x] Measure startup sequentially and synchronize references and evidence.

Follow the [presentation contract](../docs/presentation.md), preserving machine output and plain fallbacks. Tests own all runtime roots and use synthetic private modules; no live shell, theme, package manager, remote Git mutation, commit or push is part of this change.

Baseline: native Termux public fixtures, five warm non-PTY startup samples, median Zsh with installed public plugins 1.839 s; minimal-tool Bash 63.784 ms. Public source and interface snapshots are retained in `$TMPDIR/dots-zsh-f4_y4lc3`. Compare equivalent fixtures; report added integrations separately from minimal startup overhead.

## Verification

Native Termux results: shared-shell contracts passed 12/12, Zsh 17/17, shell initialization 27 passed with 3 PowerShell skips, shared utilities 29/29 and Bash dispatcher 23/23. The existing Zsh listing-alias failures are resolved by the agreed eza/plain fallback. Added fixtures cover Bash native completion retry/refresh, NVM/rbenv/Cargo activation, private-module exclusion, decoding, portable platform detection, path-safe navigation, FZF cancellation, Yazi cleanup, prompt composition/status and builtin-only unchanged-theme checks. A synthetic Zsh module verifies the retained module-to-app-setting precedence. Syntax, focused ShellCheck and whitespace checks passed.

Native PTY checks passed in both shells. Bash verified prior-command status, Ctrl-R FZF selection/cancellation, vi cursor transitions, actual Tab completion, and identical hooks/key bindings/FZF options across repeated reloads (`$TMPDIR/dots-zsh-igb_q59z`). Zsh retained completion/history/preview/cursor behavior and reload equality (`$TMPDIR/dots-zsh-vpia72bt`). PTY timing output overlapped other tests and is not performance evidence. The public Zsh comparison retained all command names and completion mappings; changed alias definitions reflect safe quoting, the repaired `.sb`, and `eff` becoming a cancellation-aware function. Plugin-generated wrapper identities differ between processes.

Theme verification passed 26/27 with the previously reproduced Neovim all-family 40-second timeout. Theme workflow passed 12/14 with the existing 33-versus-34 catalog assertions. The repository Markdown gate retains the existing retired Yazi plugin link in docs/testing.md; a focused audit of 210 relative paths found no additional broken targets. These unrelated failures were not weakened or repaired in this migration.

## Startup measurements

Five sequential, alternating warm samples per version compared the retained public baseline with the changed source. Interactive process startup was measured without a PTY, with isolated roots and no concurrent tests. Medians in milliseconds:

| Mode | Before | After |
| --- | ---: | ---: |
| Bash, minimal tools | 77.079 | 128.375 |
| Bash, native installed tool integrations | 299.205 | 2367.646 |
| Zsh, public installed plugins | 2223.904 | 2666.078 |

The larger Bash cost accompanies newly enabled native completion, prompt and tool integrations; the old configuration activated only a small subset. Zsh variance prompted a separate six-pair, alternating Zsh-only comparison of the same fixtures: 2168.425 ms before and 2245.705 ms after (about 3.6%). The first run's larger difference did not reproduce. Results are advisory mobile measurements, not a speed improvement or desktop performance claim. The reproducible runner is `tools/bench_shared_shells.py`; raw first-run results remain under `$TMPDIR/dots-zsh-np4znh2d/shared-shell-timing.json`.

Native Linux, WSL, MSYS and Windows interaction remains unverified. No dependencies were installed, live shell or theme activated, private modules inspected, or commits/pushes performed. Open a fresh shell for the completed integration stack; ordinary later reloads remain idempotent.

Function-style follow-up: all 67 shared definitions use `name() { ... }`. The loader temporarily disables alias expansion and restores its original setting, preserving existing aliases. Bash/Zsh regression cases cover enabled and disabled alias expansion plus repeated loads; both full startup/reload checks also passed.
