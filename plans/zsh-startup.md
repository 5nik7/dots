# Zsh Startup Optimization

**Status: Implemented; native Termux and isolated fixture verification complete, with platform limits below**

Optimize the existing Zsh configuration in the main checkout while preserving immediate integration readiness, prompt details, aliases, completion, theme switching, and reloads. Go development remains paused.

- [x] Capture isolated baseline with public plugins and synthetic private/platform modules.
- [x] Replace recursive environment discovery with an explicit compatibility list.
- [x] Modularize startup, platform detection, and integrations; initialize completion and FZF once.
- [x] Reduce PATH/color/theme computation and cache generated completion data.
- [x] Test behavior, reloads, missing tools, cache failure, and platform fixtures.
- [x] Compare startup and prompt measurements and record verification limits.

Use temporary HOME/config/state/cache/history/repository roots. Preserve the eight currently discovered environment-module paths and their order; never print private configuration values. No submodule changes, commits, pushes, or new worktrees are part of this task.

## Implementation and Compatibility

Startup now has explicit environment, cache, completion, integration, and platform stages. Completion initializes once with ownership checks enabled. FZF loads once; the effective FZF Ctrl-R and FZF-tab Tab bindings are preserved. PATH insertion and color array construction avoid the old subprocess pipelines. Stable command completions and Vivid data are cached with input metadata; session activations remain immediate and Catppuccin retains its existing cache.

The compatibility list preserves the eight discovered environment-module paths and their order. Private/local hooks remain active; tests substitute synthetic files. Stateful tool/plugin initialization is guarded against repeated wrapping, while ordinary environment files and theme settings reapply on reload. Correctness repairs include the NVM default, `ll`, stable PATH deduplication, repeated theme options, and the selected-theme file fallback.

A before/after public-interface comparison found no removed public aliases, functions, or completion mappings. The only added public alias is the repaired `ll`. The single completion pass explicitly retains legacy registrations that narrower provider headers would otherwise lose. Internal plugin wrapper functions differ with the corrected initialization order.

## Native Termux Evidence

Baseline source: `2e40509` (copied before edits). Measurements use public configuration copies, installed public plugin copies, synthetic private/platform modules, isolated user roots, and a controlling PTY. Runs are sequential. Values below are medians of five samples except the single empty-application-cache observations. They are not controlled OS cold-cache measurements or timing claims for the real private configuration.

| Measurement | Baseline | Refactored |
| --- | ---: | ---: |
| Warm startup to input-ready prompt | 5.320 s | 1.426 s |
| Repeated prompt, fixture home | 338 ms | 243 ms |
| First input-ready prompt, empty application caches | 27.14 s | 21.18 s |

Refactored prompt medians were 243 ms in home, 232 ms in small repo, 243 ms in public config repo.

Raw warm input-ready samples (seconds):

- Baseline: 5.448, 4.928, 5.320, 5.346, 4.844.
- Refactored: 1.308, 1.426, 1.325, 2.091, 1.455.

Validation:

- 16 isolated regression tests passed, including syntax, platform fixtures, literal PATH order, exact color/terminfo values, generator failures and replacement, cache storage failure, theme switching, missing optional tools, relocated roots with spaces/Unicode, and plugin path precedence.
- Native PTY checks passed for Tab/FZF completion, Ctrl-R history, preview toggling, vi-mode cursor changes, and immediately rendered prompts in ordinary and Git fixture directories.
- Repeated `rl` preserves hooks, keymaps, FZF options, and fpath exactly. `rlcs` rebuilds completion and leaves FZF-tab operational. A separate final refresh acceptance run passed after those runner checks were added.
- Starship TOML parsed successfully. Relative Markdown links and whitespace checks passed. Go tests and runtime code are outside this change.

Temporary raw evidence (subject to normal temporary-directory cleanup):

- Baseline PTY: `$TMPDIR/dots-zsh-wcg6jick/` (`interactive.json`, `pty.log`).
- Refactored PTY: `$TMPDIR/dots-zsh-aacerz_y/` (`interactive.json`, `pty.log`).
- Final reload/refresh acceptance: `$TMPDIR/dots-zsh-bp808ei6/` (`interactive.json`, `pty.log`).
- Public interface comparison: `$TMPDIR/dots-zsh-93rxdwv2/comparison.json`.

Original optimization runtime source aggregate SHA-256, before the completion-dump repair below: `8cfa212fbc21cc775d943cce425ab38d64d02b302da7cb84a27f9a51578c76cd`. The digest covers sorted relative paths and bytes, NUL-delimited, for Zsh source/completions (excluding its README), shared util/colors, theme application, and the selected Starship theme.

## Follow-up: Literal Completion Names

A fresh session exposed an unquoted `_uu-[` autoload name in the installed Zsh completion dump. Loading that declaration raised `bad pattern` and left `_setup` and `_complete` unavailable during Tab completion. The loader now normalizes dump autoload declarations with `noglob` before loading and after generation, atomically repairs existing dumps, invalidates their compiled copies, and falls back to uncached initialization if repair is unavailable. Normal wildcard expansion and compinit ownership checks are retained.

The new regression failed before the fix and passes afterward. It exercises initial generation, a legacy unquoted dump in a second process, and a subsequent cached process, checking both completion helpers and shell options. All 17 isolated tests pass. Native PTY acceptance now opens a second shell before interaction and includes `cd <Tab>`; reload, refresh, history, preview, and vi-mode checks passed with no completion/startup diagnostics in either startup log. Evidence: `$TMPDIR/dots-zsh-dcng_1eh/`. Three sequential warm input-ready samples were 1.085, 1.084, and 1.109 seconds (follow-up sanity measurement, not a new controlled before/after comparison).

## Remaining Limits

- Empty-cache startup still spends substantial time in the existing Catppuccin palette generator. Its output/cache contract was retained; this is the largest remaining first-run optimization candidate.
- Linux/WSL and MSYS2 have detection/path fixtures and adapter boundaries, not native interactive acceptance. No new platform or installer support is claimed.
- Private/platform module contents and external local startup customizations were intentionally excluded from tests. Their real-world cost and side effects remain outside these measurements.
- Generated-data invalidation uses file metadata, not content hashing on every shell launch. Metadata-preserving edits can require `rlcs`; stateful activation-code changes require a new shell.
- Existing first-run plugin downloads remain possible during ordinary user startup. Test fixtures refuse Git remote operations and install nothing.

## Presentation Acceptance for Follow-up Work

Future dots-owned human shell diagnostics must meet the [presentation contract](../docs/presentation.md) and its acceptance gate. Keep ordinary startup quiet, preserve generated initialization/completion and palette data, and do not load extra presentation dependencies or scan commands during startup. Third-party shell interfaces retain their own output contracts.
