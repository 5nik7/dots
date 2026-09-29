# Shared shell utility review

**Status: Completed historical work, before helper consolidation.** Optimized the existing sourceable `bin/util` for Bash and Zsh while preserving the owner's existing removals and unrelated working-tree changes.

The paths and measurements below describe the pre-migration implementation. Current helpers and verification runners are documented in the [common-helper plan](common-helpers.md) and [shell utilities](../docs/shell-utils.md).

## Changes

- Replace PATH membership pipelines, directory-name subprocesses, and case-conversion processes with shell builtins. Preserve literal paths and existing PATH ordering.
- Consolidate source/existence checks, preserve separate arguments, accept `--verbose` alongside the existing `--verboss`, and propagate sourcing failures. Keep `--first` and the `zieces` alias.
- Execute `chcmd` once with normal streams/status, report real directory-creation failures, and query actual installed package status through an optional platform tool.
- Replace the missing box dependency with lazy shared presentation and a standalone plain fallback. Keep optional eza formatting confined to explicitly requested file-name/icon helpers; quiet checks and directory creation perform no display work.

## Verification

Use disposable Bash/Zsh roots for literal paths, broken links, missing tools, repeated PATH additions, source side effects and failures, multiple arguments, command invocation counts, and mkdir refusal. Test shared color/icon policy, stderr diagnostics, raw path formats and no execution during helper loading. Compare saved pre-change code with the new code through sequential owned-root benchmarks. Run the existing shell-init, dispatcher and Zsh suites; report existing failures separately.

Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate). There is no new selector or managed-install flow. No live configuration sourcing, package query, directory creation or theme publication is used as a test.

## Results — 2026-09-29, native Termux ARM64

The implemented interface is documented in [shell utilities](../docs/shell-utils.md). Loading remains subprocess-free. PATH edits, directory formatting and case conversion use builtins. Source/check helpers share argument handling and report source failures; `chcmd` executes once; directory creation reports failure; package queries check the installed state, including held packages. Human messages reuse the shared renderer lazily and standalone copies use plain markers.

`tools/test_util.py` passes 17 tests across Bash and Zsh, including native PTY message checks at 40 and 120 columns. Bash/Zsh syntax checks and `shellcheck -x bin/util` pass. The dispatcher suite passes 23 tests. The latest shell-initialization suite passes 26 tests with three PowerShell skips (29 discovered). The Zsh suite passes 15 of 17: both alias-expectation failures reproduce when the saved pre-change utility is substituted into disposable fixtures. They are not utility regressions.

The isolated Zsh PTY acceptance passes reload, bindings/hooks, Tab completion and history checks. Removing the box dependency resolves the previously observed reload diagnostic. Presentation checks cover automatic/forced/disabled colors and icons, NO_COLOR, dumb terminals, stream selection, plain fallback, Unicode and escaped terminal controls. Raw paths remain undecorated. These are simple message lines; selectors, previews, conflicts and recovery layouts do not apply. Terminal output was inspected as captured PTY text; font appearance and native desktop/Windows shells remain unverified.

The full documentation checker still fails at the existing `docs/testing.md` link to the retired Yazi symlink-plugin README. A focused check of 175 relative links in affected documents found only that same link, also present in the saved pre-change documentation. New utility links resolve. `git diff --check` passes.

### Sequential warm measurements

Each cell is the median milliseconds for a batch of 100 iterations, five measured samples after one warmup. PATH and case batches each call two helpers per iteration. Shell process startup is included; these advisory microbenchmarks are not per-command latency guarantees.

| Operation | Bash before → after (ms) | Zsh before → after (ms) |
| --- | --- | --- |
| Source utility definitions | 94.46 → 79.64 | 78.12 → 72.24 |
| Existing PATH membership | 1807.32 → 17.88 | 22.61 → 20.11 |
| Directory formatting | 828.60 → 22.27 | 851.06 → 16.40 |
| Upper/lower conversion | 1817.78 → 16.16 | 1843.73 → 11.23 |
| Source one small file | 20.43 → 26.05 | 17.47 → 25.22 |

Single-file sourcing adds about 0.056 ms per Bash call and 0.077 ms per Zsh call for regular/readable-file validation, literal source paths and failure handling. The complete public Zsh startup fixture, with one warmup and seven sequential samples for each source version, measured 1235.39 ms before and 1186.06 ms after. This is `zsh -dic` without a PTY; both versions emitted identical existing ps/ZLE diagnostics. It establishes no observed startup regression in that mode. Native PTY acceptance is separate functional evidence, and timing variation is not a hard budget or desktop-platform claim.

Retained local evidence (temporary, outside Git):

- Original utility and documentation snapshots: `/data/data/com.termux/files/usr/tmp/dots-util-review-2i88d_b7`.
- Final microbenchmark sources, hashes and all samples: `/data/data/com.termux/files/usr/tmp/dots-util-bench-26xuq23y/results.json`.
- Complete startup samples and matching diagnostics: `/data/data/com.termux/files/usr/tmp/dots-zsh-5d5t6qml/util-startup-comparison.json`.
- Initial successful PTY acceptance: `/data/data/com.termux/files/usr/tmp/dots-zsh-1gppjazf/interactive.json` and `pty.log`.
- Final-source PTY acceptance: `/data/data/com.termux/files/usr/tmp/dots-zsh-jhri2g2_/interactive.json` and `pty.log`; all reload equality checks pass. PTY runs are functional evidence only; timing comparisons above ran separately.
