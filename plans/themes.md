# Data-driven themes

**Status: Implemented and validated on native Termux**

Approved scope: four Catppuccin TOML palettes; native color names and semantic roles;
shared Bash query/conversion engine; compatible catppuccin/current_theme entry points;
Zsh prompt refresh; Neovim startup/focus refresh; Bash/Zsh/Fish command completion.
Preserve Mocha highlights, adapt other flavors. Use the existing checkout and preserve
uncommitted dispatcher work. Go, other application integrations, commits and publication
remain out of scope.

Implementation sequence: extract palettes and capture compatibility baseline; implement
validated data loading and batched initialization; add journaled generation publication;
connect CLI/completion/Zsh/Neovim; run isolated regression and performance checks;
synchronize reference documentation. Runtime state is never changed by development tests.

## Delivered behavior

The command and data contract is documented in [Shared themes](../docs/themes.md).
Four separate palettes, role metadata, compatibility wrappers, three-shell completion,
journaled snapshot publication, Zsh prompt refresh, and the Neovim adapter are in place.
Published initialization remains readable when source palettes are temporarily invalid.
General Go work, other application adapters, native Windows support, commits and pushes
remain outside this change.

## Verification

- 18 isolated theme tests passed, including the real public Catppuccin Neovim plugin,
  all 1,560 legacy initialization values, publication failures at all 15 durability
  boundaries, SIGKILL recovery, contention, drift refusal, and shell refresh.
- After the final warm-cache optimization, all seven affected compatibility/cache,
  snapshot, selection, CLI, generic palette and Bash sourcing tests passed again.
- 21 Bash framework tests and 17 Zsh tests passed. Real Zsh/FZF-tab acceptance passed;
  reload preserved hooks, FZF state, fpath and keybindings.
- ShellCheck, Bash/Zsh syntax, StyLua, relative documentation links and whitespace
  checks passed. Editor fixtures never ran live LazyVim or installed dependencies.

## Performance evidence

Native Termux; ten warm samples, sequential benchmark runs. Cold figures are single
first invocations, and timings vary with device load.

| Operation | Earlier implementation | Final implementation |
| --- | ---: | ---: |
| Cold legacy-compatible initialization | 16.30 s | 0.64 s |
| Warm legacy-compatible initialization, median | 47.49 ms | 47.70 ms |
| Published initialization command, median | — | 30.07 ms |
| Unchanged Zsh prompt check, average over 10,000 calls | — | 0.087 ms |

The unchanged prompt check launches no subprocesses. Matching content fingerprints
allow already validated initialization to be reused without reparsing the palettes.
Minimal Neovim warm startup measured 67.65 ms without the adapter and 60.71 ms with it;
this noisy result establishes no editor speedup and is not a full LazyVim benchmark.

Retained artifacts:

- Original baseline script/initialization: `/data/data/com.termux/files/usr/tmp/dots-theme-baseline-2qmrtufe/`.
- Baseline comparison: `/data/data/com.termux/files/usr/tmp/dots-theme-bench-kaygxc1i/results.json`.
- Final benchmark: `/data/data/com.termux/files/usr/tmp/dots-theme-bench-q7fxjoe1/results.json`.
- Final PTY acceptance: `/data/data/com.termux/files/usr/tmp/dots-zsh-sxf95kgx/`.

The older comparison artifact labels the kernel Linux; it was collected in Termux.
The final benchmark explicitly labels Termux. Other operating environments and actual
power-loss recovery remain unverified. No live selection or application state was changed.
