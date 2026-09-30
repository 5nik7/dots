# Testing Work Guide

Read this guide before adding tests, changing test runners, touching mutation code, or claiming platform support or a performance improvement.

The [Go development pause](../../plans/roadmap.md#current-priority) retains existing tests and CI. Run checks appropriate to the changed files from the existing checkout with test-owned roots. For documentation-only policy changes, run `python3 -B tools/verify_core.py docs` and `git diff --check`; Go builds, benchmarks, and helper regression suites are unnecessary unless their implementation changes.

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

## Yazi Configuration

For the local symlink header component, use the isolated Lua checks described in [the testing reference](../../docs/testing.md#yazi-symlink-component). Keep simulated text widths and Windows paths distinct from native Yazi rendering evidence.

## Permanent Core

For root `cmd/dots`, `internal`, and `tests`, use `python3 -B tools/verify_core.py check`, `bench`, `build`, or `docs` (`python` on Windows). Run check before bench and keep other builds/tests out of timing intervals. The runner enforces installed Go 1.27.1, owns configuration/cache/telemetry and runtime roots, and supplies the prebuilt binary required by process tests. Do not use inherited raw Go build/test settings. Use `python3 -B tools/test_verify_core.py` for the seven core Python regressions without Go. See [testing.md](../../docs/testing.md#permanent-core-verification) for guarantees, CI, measurement method, and durable retention.

Preserve the independent experiment and its verifier. Core verification may execute only disposable extension fixtures under decision 0003; it does not authorize an installed executable, real management commands, live completion installation or managed mutation. Keep the dispatch dependency guard, metadata projection tests, argument/error contracts, optional-logo replacement regression and empty-PATH process snapshots.

## Documentation

For changes to `experiments/go-portability/`, use `python3 experiments/go-portability/tools/verify.py check` from the repository root on native Termux Android/ARM64, Linux/AMD64, or Windows/AMD64 (`python` in PowerShell). Use an unoptimized interpreter: the verifier rejects `-O`/`-OO` and positive `PYTHONOPTIMIZE` before tools or work/artifact creation. The `check` mode includes the optimization regression; run it separately without Go using `python3 -B experiments/go-portability/tools/test_verify.py`. This runner provides the required temporary Go configuration, caches, and fixture roots, seeds telemetry off before invoking Go, and verifies its owned telemetry location; avoid running Go build/test commands directly with inherited machine settings. Run `dist` for packaging, checksum refusal, validated extraction, and isolated native execution; this mode needs installed Git and packages only the committed logo. Preserve checksum-before-extraction checks, fixed member/type/size/mode validation, and the fresh owned destination. Run `python3 -B experiments/go-portability/tools/test_distribution.py` for failure regressions without Go. Run `bench` when startup behavior changes, `cross` when checking compilation boundaries, and `docs` for relative Markdown links. These are modes of the same script, not new dots commands. See `docs/testing.md` for prerequisites, evidence retention, and the distinction between native execution and cross-compilation.

Linux and Windows CI use the branch-push workflow and `tools/ci_verify.py` collector described in `docs/testing.md`. Record actual runs and retained artifacts before promoting platform claims; keep CI prerequisite provisioning separate from offline verification. Current jobs run `check` and `dist`, reusing earlier startup evidence only when executable identity and behavior match.

Keep `GOVCS=*:off` alongside the other offline settings. On Windows preserve required OS paths while redirecting user/config/temp roots, inspect PE imports with `llvm-readobj`, and keep copy/traversal checks independent of symlink availability. Report observed link refusals as unavailable, unexpected failures as failed, and Windows ACL-denied-logo behavior as untested; do not change registry or security policy. Archive reviewed evidence privately outside temporary storage and the checkout.

The Unix Go suite includes an isolated child-process regression for logo replacement with a FIFO; preserve its deadline and test-owned roots when changing logo opening. See `docs/testing.md` for the exact boundary it tests.

The test commands in `docs/testing.md` must exist before they are presented as runnable. Until runners are implemented, label proposed names clearly. Update the relevant task guide when a new mandatory suite or verification step is introduced.

For external changes, retain strict sidecar/root tests, targeted operation counts, empty-PATH forwarding and static-help snapshots. Native Windows Ctrl+C and Ctrl+Break acceptance must use a real disposable console; an injected cancellation or skipped case is not a substitute. Never weaken acceptance to make CI green.

Console-test failure cleanup must own the entire disposable process tree, not just the dispatcher PID. Keep the startup-gated Windows Job Object, job deadlines/WaitDelay, independent fixture lifetime and negative process-handle assertions. Do not change the product interruption contract to simplify tests. Benchmark result labeling must refuse count mismatches before applying labels.

Catalog acceptance adds exact schema/projection/ordering tests and isolated native JSON process tests for hidden/unavailable records, failure streams, discovery limits, nonexecution and unchanged roots. Retain separate `discovery-json-10` warm measurements with strict sample/result counts; do not substitute JSON timings for the historical text-discovery baseline.

## Bash Command Framework

Use the [Bash test entry points](../../docs/testing.md#bash-command-framework) for
`bin/dots`, `lib/dots`, and its three shell adapters. Test all installed Bash/Zsh/Fish
interpreters with owned homes and fixture commands, including real Tab input and
changes visible without reloading. Never execute existing `dots-*` extensions as
test fixtures. Keep sequential benchmark intervals free of other tests. Preserve
the existing Zsh cache/reload regression coverage and FZF-tab acceptance.

For new or changed human views, apply the [presentation acceptance gate](../../docs/presentation.md#acceptance-gate) using the existing command suites and test-owned roots. Cover the applicable output modes and states, review representative terminal layouts, and report gaps. Cross-renderer policy checks and forced-decoration data checks are required when shared presentation behavior changes; current evidence does not establish every command or native platform.

## Existing Yazi Configuration

For `config/yazi/plugins/dots.yazi` changes, run its Lua dispatcher, Git-head metadata, hover and LS_COLORS fixtures, GNU ls oracle comparisons, and isolated native PTY runner as documented in [Testing Strategy](../../docs/testing.md#yazi-plugin-bundle). The native runner needs Python, Git, git-it, and Yazi on a Unix PTY and owns all home/config/state/cache/runtime and DDS storage. Never test project saves, deletions, or merge events against the live configuration. Keep fixture results, native platform evidence, and visual review limits distinct.

## Existing Zsh Configuration

For Zsh startup changes, run `python3 -B tools/test_zsh.py` plus the isolated startup and PTY runners described in [the Zsh guide](../../shells/zsh/README.md). Capture the baseline before editing and keep timing runs sequential. Never profile the live startup chain against the real home; private/platform modules use synthetic substitutes. Treat native Termux results and other-platform fixtures separately.

## Development Worktree Helper

Use `python3 -B tools/test_worktree_lifecycle.py` for the separate local lifecycle helper; see [the workflow guide](worktrees.md). Tests use disposable repositories, local bare remotes and owned environment roots. Preserve refusal cases and distinguish injected idle snapshots from native process detection. Do not run the helper against live fixtures to test deletion. The focused workflow adds this gate without replacing existing native core/experiment gates.

Lifecycle review regressions verify preview/apply retain native FIFO and filesystem socket fixtures where supported, and that a fresh remote-main fetch ignores an additional configured recovery-branch mapping while preserving every local branch. Device/unknown modes and metadata denial use injected `lstat` results; they do not establish native device-node coverage. Native Windows FIFO/socket fixtures are unavailable and skipped. Positive portable removal still injects an idle process snapshot; native process coverage remains separate.

For completion changes, follow [decision 0005](../../docs/decisions/0005-static-zsh-completion.md). Require installed Zsh for Termux/Linux core check, isolated real candidate and ZLE tests, literal ordered root matching, safe quoting and unchanged roots. Windows CLI generation coverage must never be labeled native Zsh coverage. CI may provision Zsh; the runner never installs it.

For shared palette, state publication, Zsh refresh, or Neovim theme adapter changes,
run `python3 -B tools/test_themes.py`; use `python3 -B tools/bench_themes.py` for performance.
The theme suite also covers the unified full-ID CLI, removed plural routes, native palette filtering/querying, and contextual color completion. Preserve these migration checks alongside publication/recovery tests.
The editor tests copy public plugin sources and never start live LazyVim or download
plugins. Missing sources report skipped tests; the optional source-map input for all
families is documented in [Shared Themes](../../docs/testing.md#shared-themes).

For the optional Gum adapter or theme switcher, run
`python3 -B tools/test_theme_picker.py` plus the shared theme/workflow and Bash
suites. This runner owns its PTYs, tool fixtures, homes and publication roots;
installed Gum enables native selection/cancellation checks at 40/80/120 columns.
Keep native tool evidence distinct from deterministic fixture backend tests.

For the tracked-config browser and Python/Bash interaction bridge, run
`python3 -B tools/test_files_browser.py`, the file catalog/operation suites, the
Bash dispatcher suite and the existing theme picker tests. Keep preview and
cancellation free of state writes; exercise metadata/source/target drift between
review and Apply. Native Gum/FZF PTY checks must use disposable catalogs and homes.

For inventory/catalog or config-link migration changes, run
`python3 -B tools/test_files.py`. For flat theme templates, connectors, imports and
wallpaper adapters, also run `python3 -B tools/test_theme_workflow.py`. These suites
own their home/config/state/source roots; local Git fixtures and fake external
adapters require no network or live app changes. Use `python3 -B tools/bench_files.py`
for inventory scaling, sequentially with other benchmarks.

## Git and managed file operations

Use `python3 -B tools/test_git_operations.py` and `python3 -B tools/test_file_operations.py` for the bounded operation engines. Fixtures own configuration/state/Git roots; publication uses local bare remotes through a test-only transport. Include abrupt interruption, snapshot drift, partial failure and optional backup cases. Run existing file and Bash suites for shared contracts and completion; never test sync, publish, import or restore against live repositories or configs.

## Anodize

Use `python3 -B tools/verify_anodize.py check` for the isolated core/CLI suite and `bench` for engine measurements. `build` writes only the ignored private executable. Keep all integration roots disposable and retain Termux LD_PRELOAD compatibility in spawned environments. Run existing theme/file/dispatcher suites for shared changes. Do not run the real Neovim startup or apply a live theme as a test.

For the Dots Neovim bridge, run `python3 -B tools/test_anodize_nvim.py` plus the existing theme suites. Set `ANODIZE_NVIM_DIR` to a completed local plugin checkout when needed. The shared helper copies public runtime files; do not replace it with a normal editor startup. Preserve dashboard timing and test manual colorscheme inactivity explicitly.

For Anodize completions or manual changes, run `python3 -B tools/test_anodize_integration.py` (Bash, Zsh, Fish and mandoc required), generated-artifact freshness, and the shared Bash/Zsh/FZF-tab checks when their integration changes. Completion must work without the private Go engine.


For shared operation confirmations, run `python3 -B tools/test_confirmations.py`
and the existing file/Git, browser, theme-picker and Bash suites. Anodize cases
must run through `python3 -B tools/verify_anodize.py check`. Preserve each command's
JSON/plain fallback and approval semantics; test selector failure without retry
and drift while the prompt is open. Native Gum checks require disposable PTYs and
local-only publication fixtures; see [testing](../../docs/testing.md#optional-operation-confirmations).

For shared progress or its integrations, run `python3 -B tools/test_progress.py` and the affected command suites. Follow the [progress testing contract](../../docs/testing.md#operation-progress), including data-mode suppression, native PTY cleanup, prompt-capable children and transaction rollback. Keep benchmark measurements sequential.

## Shell initialization

For `dots init` or native startup-loader changes, run `python3 -B tools/test_shell_init.py` on Unix and `python3 -B tools/test_powershell_init.py` for portable native PowerShell acceptance, the Bash dispatcher and Zsh suites, affected theme tests, and native syntax checks. Use the isolated PTY and timing fixtures for interactive/startup changes. Use `tools/public_fixture.py` when copying these public trees so absolute symlinks cannot write through to the live checkout. Preserve synthetic private modules and distinguish unavailable PowerShell/Windows evidence from verified native Termux shells. See [initialization testing](../../docs/testing.md#shell-initialization).

For local theme plugins, run `python3 -B tools/test_theme_plugins.py` plus the existing theme/workflow, file-operation, Bash-framework and Anodize suites described in [testing](../../docs/testing.md#theme-plugins). Preserve test-owned roots, stub desktop apps, non-execution in read-only paths, and explicit desktop/native-Windows limitations.

For `bin/lib/common.sh`, run `python3 -B tools/test_common.py`, Bash/Zsh syntax checks and `shellcheck -x bin/lib/common.sh`, then the shell-init, dispatcher and Zsh regressions. Use the isolated PTY runner for reload changes. Preserve a pre-change utility snapshot and run `tools/bench_common.py` sequentially for hot-path changes; see [utility verification](../../docs/testing.md#shared-shell-utilities). Keep package checks stubbed and all directory creation inside fixtures.

For shared Bash/Zsh interactive configuration, run `python3 -B tools/test_shared_shells.py`, the shell-init/shared-utility/dispatcher/Zsh suites, affected theme suites, and both native PTY runners (`tools/bash_interactive.py` and `tools/zsh_interactive.py`). Use their owned public fixtures and synthetic private modules. Capture source/interface baselines before edits and measure comparable startup modes sequentially; report optional-tool and native-platform gaps. See [shared shells](../../docs/shared-shells.md) and the [focused plan](../../plans/shared-shells.md).
