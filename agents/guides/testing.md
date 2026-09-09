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

## Documentation

For changes to `experiments/go-portability/`, use `python3 experiments/go-portability/tools/verify.py check` from the repository root on native Termux Android/ARM64. Use an unoptimized interpreter: the verifier rejects `-O`/`-OO` and positive `PYTHONOPTIMIZE` before tools or work/artifact creation. The `check` mode includes the optimization regression; run it separately without Go using `python3 -B experiments/go-portability/tools/test_verify.py`. This runner provides the required temporary Go configuration, caches, and fixture roots; avoid running Go build/test commands directly with inherited machine settings. Run `bench` when startup behavior changes, `cross` when checking compilation boundaries, and `docs` for relative Markdown links. These are modes of the same script, not new dots commands. See `docs/testing.md` for prerequisites, evidence retention, and the distinction between native execution and cross-compilation.

The native Go suite includes an isolated child-process regression for logo replacement with a FIFO; preserve its deadline and test-owned roots when changing logo opening. See `docs/testing.md` for the exact boundary it tests.

The test commands in `docs/testing.md` must exist before they are presented as runnable. Until runners are implemented, label proposed names clearly. Update the relevant task guide when a new mandatory suite or verification step is introduced.
