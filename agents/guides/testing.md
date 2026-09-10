# Testing Work Guide

Read this guide before adding tests, changing test runners, touching mutation code, or claiming platform support or a performance improvement.

## Isolation Is Mandatory

Tests must receive explicit test-owned roots for home, repository, config, data, state, cache, and executable installation. A test must fail closed if any resolved mutation target escapes those roots.

Never let a test:

- Write to the developer's real home or platform config directory.
- Change the active shell, environment, registry, Developer Mode, or package database.
- Initialize private submodules or prompt for credentials.
- Depend on the current repository being clean.
- Delete a broad directory through an empty or unresolved variable.

## Test Layers

- Unit tests: route resolution, manifest parsing, precedence, path normalization, classification, and inverse-operation construction.
- Golden tests: human plans, JSON plans, help, command discovery, and generated documentation.
- Filesystem integration tests: apply, interruption, rollback, undo, drift, and repository relocation in a temporary sandbox.
- Adapter contract tests: every platform adapter produces equivalent normalized behavior from fixtures.
- Bootstrap tests: disposable platform environments and failure injection.
- Performance tests: dispatcher startup, command discovery, spec resolution, and large-plan generation.
- Manual platform checks: gaps that hosted CI cannot reproduce faithfully, recorded with environment and result.

## Required Safety Cases

- No-op idempotent apply.
- Existing regular file and directory.
- Correct, incorrect, and broken links.
- Permission failure before and during apply.
- Process interruption after each journal boundary.
- Rollback failure with actionable recovery instructions.
- Undo after the managed target has drifted.
- Link unavailable with copy fallback disabled.
- Path traversal and destination escape attempts.
- Secret redaction in human and structured output.

## Performance Method

- Establish a baseline on at least Termux and one conventional desktop platform before setting hard budgets.
- Measure cold and warm runs separately where the distinction matters.
- Benchmark with representative small and large command/module sets.
- Record environment, build mode, sample count, and statistical summary.
- Do not call a change faster based on one interactive run.
- Follow the accepted warm targets and regression-review policy in [decision 0002](../../docs/decisions/0002-phase-1-go-adoption.md#performance-budgets-and-regression-policy). Numeric timing checks remain advisory; confirmed comparable regressions require a fix or owner-approved exception. Numeric gates remain advisory; the permanent core now has the isolated runner below.

## Permanent Core

For root `cmd/dots`, `internal`, and `tests`, use `python3 -B tools/verify_core.py check`, `bench`, `build`, or `docs` (`python` on Windows). Run check before bench and keep other builds/tests out of timing intervals. The runner enforces installed Go 1.27.1, owns configuration/cache/telemetry and runtime roots, and supplies the prebuilt binary required by process tests. Do not use inherited raw Go build/test settings. Use `python3 -B tools/test_verify_core.py` for the seven core Python regressions without Go. See [testing.md](../../docs/testing.md#permanent-core-verification) for guarantees, CI, measurement method, and durable retention.

Preserve the independent experiment and its verifier. Core verification may execute only disposable extension fixtures under decision 0003; it does not authorize an installed executable, real management commands, completions or managed mutation. Keep the dispatch dependency guard, metadata projection tests, argument/error contracts, optional-logo replacement regression and empty-PATH process snapshots.

## Documentation

For changes to `experiments/go-portability/`, use `python3 experiments/go-portability/tools/verify.py check` from the repository root on native Termux Android/ARM64, Linux/AMD64, or Windows/AMD64 (`python` in PowerShell). Use an unoptimized interpreter: the verifier rejects `-O`/`-OO` and positive `PYTHONOPTIMIZE` before tools or work/artifact creation. The `check` mode includes the optimization regression; run it separately without Go using `python3 -B experiments/go-portability/tools/test_verify.py`. This runner provides the required temporary Go configuration, caches, and fixture roots, seeds telemetry off before invoking Go, and verifies its owned telemetry location; avoid running Go build/test commands directly with inherited machine settings. Run `dist` for packaging, checksum refusal, validated extraction, and isolated native execution; this mode needs installed Git and packages only the committed logo. Preserve checksum-before-extraction checks, fixed member/type/size/mode validation, and the fresh owned destination. Run `python3 -B experiments/go-portability/tools/test_distribution.py` for failure regressions without Go. Run `bench` when startup behavior changes, `cross` when checking compilation boundaries, and `docs` for relative Markdown links. These are modes of the same script, not new dots commands. See `docs/testing.md` for prerequisites, evidence retention, and the distinction between native execution and cross-compilation.

Linux and Windows CI use the branch-push workflow and `tools/ci_verify.py` collector described in `docs/testing.md`. Record actual runs and retained artifacts before promoting platform claims; keep CI prerequisite provisioning separate from offline verification. Current jobs run `check` and `dist`, reusing earlier startup evidence only when executable identity and behavior match.

Keep `GOVCS=*:off` alongside the other offline settings. On Windows preserve required OS paths while redirecting user/config/temp roots, inspect PE imports with `llvm-readobj`, and keep copy/traversal checks independent of symlink availability. Report observed link refusals as unavailable, unexpected failures as failed, and Windows ACL-denied-logo behavior as untested; do not change registry or security policy. Archive reviewed evidence privately outside temporary storage and the checkout.

The Unix Go suite includes an isolated child-process regression for logo replacement with a FIFO; preserve its deadline and test-owned roots when changing logo opening. See `docs/testing.md` for the exact boundary it tests.

The test commands in `docs/testing.md` must exist before they are presented as runnable. Until runners are implemented, label proposed names clearly. Update the relevant task guide when a new mandatory suite or verification step is introduced.

For external changes, retain strict sidecar/root tests, targeted operation counts, empty-PATH forwarding and static-help snapshots. Native Windows Ctrl+C and Ctrl+Break acceptance must use a real disposable console; an injected cancellation or skipped case is not a substitute. Never weaken acceptance to make CI green.

Console-test failure cleanup must own the entire disposable process tree, not just the dispatcher PID. Keep the startup-gated Windows Job Object, job deadlines/WaitDelay, independent fixture lifetime and negative process-handle assertions. Do not change the product interruption contract to simplify tests. Benchmark result labeling must refuse count mismatches before applying labels.
