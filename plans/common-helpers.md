# Shared common helper consolidation

**Status: Completed, 2026-09-29.** `bin/lib/common.sh` is the single Bash/Zsh helper entry point. `bin/util` is removed without a forwarding file. `bin/colors.env` is also removed without a forwarding file; startup no longer creates named palette/terminal globals.

## Implementation

Common contains the optimized utility helpers, explicit color-array builders, logging, formatting and spinner interfaces. Loading is quiet and starts no subprocesses, builds no arrays, initializes no styling and changes no traps. Human output lazily uses the shared renderer with plain fallbacks. Array builders retain all 256 exact values, are independent of named color globals, and can be repeated without leaking counters.

Bash/Zsh startup, compatibility profiles, the exported Bash UTIL path and fixture manifests use common. Bash no longer overrides the shared builtin case-conversion functions with awk implementations. Test and benchmark entry points are `tools/test_common.py` and `tools/bench_common.py`; current usage, architecture, testing guidance and README references are synchronized. Older utility and shell-init evidence is explicitly historical.

The initial spinner implementation left an extra wrapper between an asynchronous caller and the worker. Brace-bodied workers now handle signals at the owned PID; command evaluation stays in a child shell. Signal cleanup reaps owned children, preserves caller traps and returns 130/143. Zsh uses local trap scope; Bash restores saved INT/TERM handlers. The legacy command string remains trusted shell code; detached descendants remain the command's responsibility. See the [helper contract](../docs/shell-utils.md).

A tracked/untracked source and symlink audit covered the parent checkout and initialized submodules, including private references without printing contents. There are no active references to the retired helper or runner paths; remaining mentions identify removal, historical evidence or accepted benchmark snapshots. Unrelated work and submodule state were preserved. No commit, push, installation or live shell activation was performed.

## Initial consolidation verification — native Termux ARM64 (historical)

- Common: 25 tests pass in disposable Bash/Zsh roots, including exact arrays, loading behavior, optional tools, source failures, raw paths, message policy, command status, foreground INT/TERM, background TERM, process reaping and caller traps.
- Shell initialization: 26 pass, with three PowerShell skips (29 discovered). Reload checks cover Bash's authoritative case helpers and both shells' initialized arrays.
- Bash dispatcher: all 23 tests pass. Zsh: 15 of 17 pass; both existing alias-expectation failures reproduce with saved pre-migration helpers and startup sources in owned fixtures.
- Isolated native Zsh PTY acceptance passes reload equality for hooks, key bindings, fpath and FZF settings, real completion rows, Tab/cd/history pickers and cursor transitions. Evidence: `/data/data/com.termux/files/usr/tmp/dots-zsh-8wzt5y24/interactive.json` and `pty.log`.
- Bash/Zsh syntax and ShellCheck for common pass. The full documentation checker still reports the pre-existing retired Yazi symlink-plugin README link in `docs/testing.md`; the same link is present in the saved pre-migration document. New helper links resolve. Whitespace checks pass.

The [presentation acceptance gate](../docs/presentation.md#acceptance-gate) covers automatic/forced/disabled colors and icons, NO_COLOR, dumb terminals, narrow/wide PTYs, plain fallback, terminal-control escaping, raw values and disabled/redirected animation. No selector, transaction, preview or conflict view is introduced. Native desktop, Windows and font appearance remain unverified; PTY results establish terminal behavior and captured text.

## Initial consolidation performance and retained evidence (historical)

The pre-migration snapshot is `/data/data/com.termux/files/usr/tmp/dots-common-review-kubrt5r7/before`; baseline alias-test output is retained alongside it. The implementation-start snapshot is `/data/data/com.termux/files/usr/tmp/dots-common-review-hsmi_38p`.

Sequential warm helper benchmarks use five measured batches of 100 iterations after one warmup, including shell process startup. The comparison uses the saved optimized utility source against consolidated common. Source loading grows from 130.73 to 170.91 ms per Bash batch and from 67.87 to 134.46 ms per Zsh batch: approximately 0.40 and 0.67 ms extra per source operation for the additional function definitions. There is no new subprocess, cache or eager initialization. All operation samples, source snapshots and hashes are retained in `/data/data/com.termux/files/usr/tmp/dots-common-bench-jqbg75m3/results.json`. These advisory microbenchmarks are not per-command latency guarantees or evidence for another platform.

The final full-startup comparison used the same disposable public Zsh fixture, one warmup and seven alternating sequential samples per version, without concurrent verification. Median `zsh -dic` startup was 2300.24 ms before and 2206.11 ms after. All runs exited successfully with identical existing non-PTY diagnostics. This shows no observed startup regression in this run, not a speed guarantee; terminal acceptance is separate. Samples, source hashes and diagnostics are retained in `/data/data/com.termux/files/usr/tmp/dots-zsh-yx87hqc5/common-startup-comparison.json`. Representative common-helper output was reviewed as captured PTY text at 40/120 columns in Bash and Zsh; raw captures are retained in `/data/data/com.termux/files/usr/tmp/dots-common-review-hsmi_38p/presentation.json`. Evidence paths are temporary local artifacts outside Git.

## Named-color removal — completed, 2026-09-29

Removed the color environment file, startup sourcing, exported COLORS assignment and fixture dependencies. Explicit array construction now follows common loading, independently of any optional environment module. Existing caller-owned variables remain untouched. Both dirout entry points request blue/reset values lazily from the shared renderer, with terminal/color policy and plain standalone fallback; paths and argument semantics are preserved. The script resolves its own symlink chain rather than trusting inherited DOTS. Current README, architecture, commands, helper, startup and testing documentation is synchronized. Earlier results above describe the initial consolidation before this removal.

Verification on native Termux ARM64:

- All 29 common-helper tests pass, including exact arrays, absent/conflicting legacy globals, tool-free compatibility profiles, both dirout interfaces, redirected/native PTY policy at 40/120 columns, symlinked invocation, unrelated inherited DOTS and missing-renderer fallback.
- Shell initialization: 26 pass and three PowerShell skips (29 discovered). Fresh Bash/Zsh startup creates no legacy globals; reload preserves caller values and all arrays.
- All 23 dispatcher tests pass. Zsh: 15 of 17 pass. Both alias-expectation failures reproduce against the immediately preceding removal snapshot; they remain unrelated.
- Native Zsh PTY acceptance passes reload equality, completion, Tab/cd/history pickers and cursor checks. Evidence: `/data/data/com.termux/files/usr/tmp/dots-zsh-0nawn1h5/interactive.json` and `pty.log`.
- Bash/Zsh syntax, ShellCheck for common and standalone dirout, and whitespace checks pass. The 135 checked relative links have only the existing retired Yazi README failure, also present in the saved pre-removal documentation. No active references to the deleted file or its exported path remain in maintained sources or initialized submodules; independent COLORS arrays in other scripts remain unchanged.

The final startup comparison used one warmup and seven alternating sequential samples per version, with no concurrent verification. Minimal-tool interactive Bash initialization measured 293.13 ms before and 43.88 ms after; the full public `zsh -dic` fixture measured 1545.25 ms before and 1546.97 ms after. All runs succeeded; this shows the removed Bash terminal queries and no meaningful observed Zsh regression in these fixtures. These are advisory non-PTY measurements, not live-home or desktop-platform guarantees. Native Windows/desktop and font appearance remain unverified.

The pre-removal sources, source hashes, full samples/diagnostics, baseline alias results and reviewed plain/colored dirout PTY captures are retained under `/data/data/com.termux/files/usr/tmp/dots-colors-removal-g492gjh9` (`before/`, `startup-comparison.json`, `baseline-alias-tests.txt`, `presentation.json`). These temporary artifacts are outside Git. No live reload, external configuration change, commit or push was performed.
