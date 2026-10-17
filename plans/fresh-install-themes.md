# Fresh-install theme recovery

**Status: Implemented.** Fix the missing FSH source directory in clean clones,
and prevent setup/refresh from reusing incomplete theme generations.

- [x] Retain `config/fsh` through tracked documentation; leave its generated connector ignored.
- [x] Share completeness checks across setup and the publisher. Prepare and validate new generations before journaled publication; retain old payloads and backup baselines.
- [x] Distinguish FSH artifact, compilation and cache failures without doing publication during shell startup.
- [x] Verify tracked-source-only installation, repeat/restore, missing artifacts/pointers, failed preparation, ownership conflicts and native Zsh consumer behavior in owned roots.
- [x] Follow the [presentation gate](README.md#presentation-gate-for-every-plan), preserving JSON and nonanimated dry runs.

## Verification — 2026-10-17

- Installation: 21 tests passed, including clean public sources with simulated WSL detection, missing-output/pointer repair, failed preparation and rollback after active-pointer replacement.
- File catalog: 9 passed; missing-source check: 16 passed; installation adapters: 5 passed, 4 skipped for unavailable native runtimes/platform capabilities.
- Vivid/FSH: all 14 cases covered successfully through the full run and focused reruns. Fixed stale test dependencies on the removed personal `njen.ini` and the former Vivid template tokens; no retired personal config was restored.
- Theme publisher: 6 focused atomicity, idempotence, recovery, unsafe-state and Zsh-hook cases passed. Shell environment: 8 passed; native hook contracts: 4 focused cases passed. The default-shell test's obsolete personal-loader fixture also failed on baseline HEAD and was corrected to use library loaders.
- Resource presentation: 11 passed; progress: 11 passed. Native Zsh warning checks passed at 40/80/120 columns in automatic and disabled color modes, with one warning, complete wrapped paths and no animation. A FIFO supplied as the theme artifact was rejected without blocking.
- Warm native FSH adapter timing: baseline 17.682 ms/call, updated 17.808 ms/call (median of three sequential 30-call batches in an owned fixture). This measures the affected warm adapter, not full shell startup or WSL performance.
- Edited shell/Python syntax, focused ShellCheck, whitespace and relative Markdown links were checked. Core ShellCheck retains its pre-existing dynamic `dots_options` SC2154 notice; changed publisher/setup/shell files pass the focused check with the repository's dynamic-source exclusions.

Native Termux execution and WSL platform fixtures are separate from native WSL
verification. The exact owner-reported WSL warning has not been supplied; do not
claim the reproduced defects fully explain it. Native Windows theme publication
remains outside this change.
