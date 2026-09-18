# Phase 1 Termux Portability Experiment

**Status: Bounded portability/distribution experiments completed and Go adoption accepted; remaining platform/release gates deferred; first Phase 2 slice tracked separately**

The owner approved all four decisions in [0002](../docs/decisions/0002-phase-1-go-adoption.md) as proposed at `c7d86a989e6397a3ecd74407e63097994f183694` on 2026-09-10. The results below retain their original chronology, including then-provisional language status; current policy is the accepted decision. Acceptance does not complete untested capabilities.

## Scope and Reconciliation

Start from `c1be6eb2417ece2218beb5f724de1b8de27cf403` with a clean working tree. The owner's intervening commits added `logo.txt`, committed the Zsh changes, and repaired the Bash prototype's help/error path. Preserve these files exactly. The experiment is additive under `experiments/go-portability/`; the live `bin/dots` remains the active command.

Implement help (including optional `logo.txt`), version output, and read-only diagnostics in an independent standard-library-only Go module. Build and run natively with the installed Termux Go toolchain. Probe filesystem primitives only in disposable test-owned directories. Confine build caches and artifacts to temporary roots and record repeatable startup measurements.

This limited prerequisite may proceed while Phase 0's manifest, module, and repository-size decisions remain open. It does not complete the end-to-end [Termux MVP](termux-mvp.md).

## Boundaries

The original experiment authorized no package installation, proot, bootstrap, real-home installation, transaction engine, shell changes, directory migration, secret reads, private submodule initialization, commits, or pushes. Subsequent checkpoint, Linux, and Windows tasks explicitly authorized scoped feature-branch commits/pushes; the desktop validation tasks additionally allowed development prerequisites in CI only. The other boundaries remain in force. No production mutation API is introduced. Go adoption, distribution, extension protocol, manifests, and permanent core layout remain deferred.

## Work and Acceptance

- [x] Add the experimental executable and dynamic optional logo help.
- [x] Add read-only platform/path diagnostics with explicit unprobed capabilities.
- [x] Add isolated CLI, platform, metadata, and filesystem tests.
- [x] Build and execute Android/ARM64 natively; inspect runtime dependencies.
- [x] Measure first-observed and warm startup separately, without claiming controlled cold-cache results.
- [x] Check compilation for other targets if the installed toolchain permits it; never report this as native execution.
- [x] Synchronize README, commands, architecture, platform, safety, testing, inventory, and roadmap documentation.
- [x] Run final focused verification and documentation checks; confirm protected files remain unchanged.

## Verification Design

The Python standard-library harness copies only experimental Go sources and the public logo into its own temporary repository. It provides test-owned home/config/data/state/cache/temp/bin roots, disables Go toolchain and dependency downloads, and keeps Go configuration/cache writes inside the sandbox. Filesystem tests use `testing.T.TempDir` and directory-rooted operations, covering spaces, Unicode, leading dashes, existing files/directories, broken links, missing parents, and escape attempts. CLI process checks are implemented in the harness rather than a separate Go integration-test file; this keeps environment setup and executable invocation together.

The compiled CLI must start with an empty executable search path. Help must work without a logo; version and JSON diagnostics must not read or display it. Diagnostics must not probe capabilities by creating files. A filesystem snapshot of controlled target roots before and after CLI execution must remain unchanged.

Measure the prebuilt executable directly with explicit warmup and sample counts, recording build mode, tool versions, device/runtime, filesystem, artifact identity, and raw timing samples. Fresh-process timings do not establish cold filesystem cache behavior. No hard budget is selected before desktop evidence exists.

## Results

### Environment and Build

Recorded on 2026-09-09; warm measurement metadata timestamp `2026-09-09T20:46:15Z`.

| Item | Observation |
| --- | --- |
| Source baseline | `c1be6eb2417ece2218beb5f724de1b8de27cf403` plus this uncommitted experimental change |
| Host | Termux 0.119.0-beta.3, Android API 35, `aarch64` |
| Kernel | `5.4.274-qgki-30957850-abG996USQSJHZB1` |
| Test filesystem | f2fs under the app-private Termux temporary directory; not shared Android storage |
| Toolchain | Go 1.27.1, native host/target `android/arm64`; Python 3.14.6; hyperfine 1.20.0 |
| Build | Standard library only; `CGO_ENABLED=0`; default Android PIE; `-trimpath -buildvcs=false -mod=readonly`; no stripping flags |
| Artifact size | 4,069,044 bytes |
| Artifact SHA-256 | `0875df8adc034e068fcf65c4234712e029814d41529f6d282587ba4ba7ce6da5` |
| Runtime dependencies | Android `/system/bin/linker64`; no ELF `DT_NEEDED` shared-library entries; starts with empty `PATH` |
| Repeatability | A second build from a relocated source path produced identical bytes with the same toolchain |

### Native Verification

`python3 experiments/go-portability/tools/verify.py check` runs formatting, vet, uncached Go tests, CLI process checks, relocated rebuild comparison, ELF inspection, and relative Markdown links. The Go suite has 12 top-level tests, with additional table-driven cases for command errors, platform false positives, and filesystem paths/objects. All passed natively on Termux, including the final harness checks for platform identity and broken logo symlinks. Relative Markdown links and `git diff --check` passed; protected command, logo, shell, configuration, and submodule files have no diff against the starting commit. No unrelated repository-wide suite for the future core exists.

Process checks cover no-argument/help spellings, contextual help, version, human/JSON diagnostics, unknown commands, logo absence/empty/directory/unreadable/oversize/broken-link/FIFO cases, dynamic reload, and executable-symlink fallback. Controlled target snapshots remain unchanged across read-only commands. A separate read-only invocation with this session's actual Termux environment reported `termux`, `android/arm64`, expected XDG candidates, no warnings, and all filesystem capabilities `not_probed`; no configuration contents were read.

### Startup Results

`python3 experiments/go-portability/tools/verify.py bench` measures the already built executable directly with `hyperfine --shell=none`, three batches, 20 warmups per command per batch, 200 measured executions per command per batch, and alternating command order. Help reads a copy of the current public `logo.txt`; executable `PATH` is empty and stdout is discarded. Raw timings and environment/build metadata remain in the harness's temporary `evidence.json`; these reviewed summaries are retained in Git.

| Command | Warm samples | Median | p95 | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| `--help` | 600 | 7.804 ms | 12.807 ms | 5.049 ms | 42.498 ms |
| `--version` | 600 | 8.020 ms | 15.643 ms | 5.855 ms | 42.336 ms |

Python-timed first-observed invocations were 8.574 ms for help and 6.468 ms for version. These include parent spawn/wait overhead and uncontrolled cache state; they are not cold-start measurements and are not directly interchangeable with hyperfine samples. Hyperfine reported statistical outliers in multiple batches. Phone background activity, power state, and thermals were not controlled. No benchmark ran concurrently with this task's cross-compilation or test suites. These observations establish a device baseline, not a speedup claim, comparison between commands, or hard performance budget. Desktop and controlled cold-cache evidence remain pending.

### Cross-Compilation Only

`python3 experiments/go-portability/tools/verify.py cross` successfully built Linux/AMD64 and Windows/AMD64 executables and compiled all three test packages for each target with `go test -c`. None of those foreign artifacts was executed. WSL/Windows detection fixtures were executed on Termux and do not verify native runtime, paths, permissions, or filesystem behavior. No proot, emulator, package change, or additional toolchain was used.

### Python Verifier Review Follow-up

The completed review of `8980621c49c507fbd7aec0bc0cfe32ab052ea467` confirmed that Python optimization removes the harness assertions for CLI behavior, read-only snapshots, and identical rebuilds. This focused follow-up starts from that commit on `feat/phase-1-portability` with a clean working tree. Go remains provisional; the Go sources, executable behavior, live command, logo, and dotfiles are outside this fix.

The verifier now explicitly rejects an optimized interpreter before argument parsing, tool lookup/invocation, or temporary work/artifact creation. The regression launches both `-O` and `PYTHONOPTIMIZE=1` across all five modes and verifier help, requiring the optimization-specific stderr error, exit status 1, empty stdout, and unchanged test-owned fixture roots. `check` includes this regression before Go invocation. The standalone entry point is `python3 -B experiments/go-portability/tools/test_verify.py`.

Validated on 2026-09-09 with Python 3.14.6 (optimization level 0) and Go 1.27.1, natively on Termux 0.119.0-beta.3, Android/ARM64. The normal check started at `2026-09-09T22:19:07Z`; its build metadata timestamp is `2026-09-09T22:19:21Z`. The kernel, build flags, 4,069,044-byte executable, and SHA-256 match the original results above.

| Command or check | Actual outcome |
| --- | --- |
| `python3 -B experiments/go-portability/tools/test_verify.py` against the original verifier | Failed as expected: both tests, all 12 cases; optimization was not rejected for the required reason |
| Same regression after the fix | Passed: 2 tests, 12 cases; each optimized child returned 1 with the exact error, empty stdout, and unchanged fixture roots |
| `python3 experiments/go-portability/tools/verify.py check` | Passed: Python regression, formatting, vet, all 12 top-level Go tests, 10 CLI requests, 7 optional-logo cases, fallback/reload, read-only snapshots, identical relocated rebuild, ELF inspection, and 68 relative Markdown links in 23 files |
| `python3 experiments/go-portability/tools/verify.py docs` and `git diff --check` | Passed after the results update |
| Diff against `8980621` for Go sources, live command, logo, shells, configurations, and submodule declarations | Empty |

Sanitized verification evidence is retained outside the checkout at `/data/data/com.termux/files/usr/tmp/dots-verifier-fix-ffw8cxdu/`: before/after regression logs, the complete native-check log, build metadata, and validation results. `tested-source.json` records the base commit, branch, dirty working-tree status, and SHA-256 for every public input captured in `tested-source/`, including the modified verifier and new untracked regression test. All captured inputs were unchanged during the regression and native check. Only this plan's results were amended afterward; `final-source.json` and the final tracked diff record that documentation update and identify the complete uncommitted change. Final documentation/whitespace checks are recorded separately. The native binaries, logo, and original harness metadata are retained at `/data/data/com.termux/files/usr/tmp/dots-spike-artifact-763yvxl1/`. Temporary evidence may be removed by the system.

The Python verification review finding is resolved. The original startup measurements, timestamp, source baseline, and cross-compilation results above remain historical evidence; neither benchmarks nor cross-compilation were rerun for this Python-only fix. Native desktop execution remained untested and Go remained provisional at the end of this Python-only follow-up. The separate logo Stat/Open race was deferred at that point; its subsequent fix is recorded below.

### Logo Replacement Review Follow-up

**Completed for the Termux experiment; native desktop validation remains open.** Continued from the Python verifier fix above with its uncommitted changes intact. Go remains provisional and the live command/dotfile setup is unchanged. The loader retains its early optional-file check, opens read-only through the platform adapter, and classifies the actual handle before reading. Unix builds use `O_NONBLOCK` to avoid waiting for a FIFO writer. Valid logo symlinks, formatting, the 64 KiB bound, and logo-free version/diagnostic output are preserved. Other platforms retain native read-only open semantics and gain the handle check; this does not establish native desktop support or a universal filesystem timeout.

The new Unix `TestLogoReplacement` has four deterministic child cases: replacing a regular logo with a FIFO, replacing its symlink target with a FIFO, a FIFO with a writer, and an unchanged regular-file symlink. The parent runs the child with an empty `PATH`, test-owned roots, and a 10-second deadline. The passing child completed in approximately 0.01 seconds on this device; that duration is a test observation, not a startup benchmark.

| Verification | Actual outcome on 2026-09-09 |
| --- | --- |
| `python3 experiments/go-portability/tools/verify.py check` | Passed: Python optimization regression, formatting, vet, all 13 top-level Go tests, CLI/optional-logo checks, read-only snapshots, identical relocated rebuild, ELF inspection, and 68 Markdown links in 23 files |
| Focused regression against disposable copies with each fix component removed | Both failed as expected at the 10-second child deadline: blocking open failed on `fifo`; missing handle validation failed on `fifo-with-writer`. Only copied source was changed. The recorded command was `go test -count=1 -timeout=30s -run=^TestLogoReplacement$ -v ./internal/cli`, using the harness's isolated Go environment. |
| `python3 experiments/go-portability/tools/verify.py cross` | Built Linux/AMD64 and Windows/AMD64 executables and compiled all three test packages for each. No foreign artifact was executed. The Unix replacement test is included in the Linux test binary, not the Windows build. |
| `python3 experiments/go-portability/tools/verify.py bench` | Passed; both commands have 600 successful measured executions and retained raw samples |
| Final `python3 experiments/go-portability/tools/verify.py docs` and `git diff --check` | Passed; live command, logo, shells, configurations, and submodule declarations remain unchanged |

The environment remains Termux 0.119.0-beta.3 on Android/ARM64, Python 3.14.6, Go 1.27.1, and hyperfine 1.20.0, with the same kernel and app-private temporary filesystem as the original run. Native check metadata is timestamped `2026-09-09T22:34:23Z`; benchmark metadata is timestamped `2026-09-09T22:36:03Z`. Build flags and runtime dependencies are unchanged: Android PIE, `CGO_ENABLED=0`, `-trimpath -buildvcs=false -mod=readonly`, `/system/bin/linker64`, and no ELF `DT_NEEDED` entries. The new executable is 4,070,316 bytes with SHA-256 `af73814fe6777aa2436ab5dc4c6dce18a2a9d53a9f8fa693f9f1686aa2c8d693`; native artifacts from check, cross, and bench are identical.

The updated measurements use the original method: prebuilt executable, public logo, empty `PATH`, `hyperfine --shell=none`, three alternating-order batches with 20 warmups and 200 samples per command per batch, and stdout discarded. Tests and cross-compilation completed before timing began.

| Command | Warm samples | Median | p95 | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| `--help` | 600 | 8.314 ms | 10.188 ms | 7.193 ms | 19.767 ms |
| `--version` | 600 | 8.261 ms | 10.127 ms | 7.251 ms | 15.380 ms |

First-observed Python timings were 8.097 ms for help and 7.240 ms for version; neither is a controlled cold-cache measurement. Relative to the historical run above, observed medians are 0.510 ms higher for help and 0.241 ms higher for version, while p95 values are lower. Help now performs an additional handle metadata check, but these separate runs do not isolate that cost: background activity, power state, and thermals were uncontrolled, and hyperfine reported outliers. No speedup, causal regression estimate, or hard performance budget is claimed. The historical measurements and their provenance above are retained unchanged.

Sanitized logs, raw benchmark evidence, expected-failure mutation logs, and exact tested source are retained outside the checkout at `/data/data/com.termux/files/usr/tmp/dots-logo-fix-mhhzhd3q/`. `starting-source.json` identifies the preceding Python fix; `tested-source.json`, `tested-source/`, and `tested-tracked.patch` identify commit `8980621c49c507fbd7aec0bc0cfe32ab052ea467` plus all uncommitted Python/logo changes and public documentation. All captured inputs were unchanged during verification. Only this plan's results were amended afterward, as recorded in `final-source.json` and the final source snapshot/diff. `run_verification.py` records the one-off orchestration and isolated mutation method; it is retained evidence, not a new repository runner. Artifacts are at `/data/data/com.termux/files/usr/tmp/dots-spike-artifact-aebcll2s/` (native check), `dots-spike-artifact-ea1az1mq/` (cross-compilation), and `dots-spike-artifact-atmy2suv/` (benchmark) under the same temporary directory. Temporary evidence may be removed by the system.

Both Phase 1 review findings are now resolved for the verified Termux experiment. Native Linux/Windows execution, desktop startup, controlled cold-cache measurements, and release/distribution checks remain open. No package changes, bootstrap, real-home installation, transaction engine, or Phase 2 work was introduced.

### Reviewable Checkpoint

On 2026-09-09 the complete logo-fix evidence directory and its three referenced artifact directories were copied into the private, durable archive `/data/data/com.termux/files/home/dots-review-evidence-20260909-8b5f6e31/`, outside both the checkout and temporary storage. All 117 copied files were verified by SHA-256; the original evidence remains intact. Archive directories are owner-only (`0700`), with owner-only files (`0600`, or `0700` for executables). `preservation.json` maps original locations to archived content, while `logo-fix/` preserves the recorded manifests and logs verbatim. Native-check, cross-compilation, and benchmark binaries are retained under `artifacts/`.

The implementation, verifier, and tests exactly match `tested-source.json`. The plan differs because it records the completed results and this preservation checkpoint. A newer owner edit to `logo.txt` is unrelated to these fixes and is excluded from the checkpoint; the logo retained in the commit matches the tested input. Existing native verification, cross-compilation, mutation checks, and startup measurements therefore apply to the checkpoint without a behavioral rerun. Documentation links and staged whitespace are checked again for this added record. No evidence snapshots, logs, or binaries are added to Git.

### Native Linux Validation

**Passed on native Linux/AMD64 in GitHub Actions; Go remains provisional.** This bounded task started from `b043a321ffe367504b4a1fdc4bdf03bda543fc32` on `feat/phase-1-portability`. Commit `6a18cc50b007fb1e0fedcedb6e4a214c0174d235` added Linux expectations, environment regressions, the CI collector/workflow, and corresponding documentation. Go implementation and Go tests were unchanged; the owner's unrelated `logo.txt` edit remained unstaged and was not sent to CI. Documentation recording these results was added after the measured commit.

The harness accepts native Termux Android/ARM64 and Linux/AMD64. Linux children omit Termux markers; both retain owned home/config/data/state/cache/temp/repository roots, the optimization guard, and the logo replacement regression. Before invoking Go, it seeds telemetry mode `off` in its owned XDG config directory and checks the reported mode/location. In this historical Linux run, `GOENV`, `GOWORK`, `GOPROXY`, `GOSUMDB`, and `GOVCS` were `off`; `GOTOOLCHAIN=local`. The later Windows follow-up corrects the malformed `GOVCS` value to `*:off`; the other controls already disabled toolchain/module downloads in this recorded run. Verification does not fetch modules or toolchains. The branch-push workflow provisions development prerequisites in CI only and checks out without initializing submodules.

[Run 34416309614, attempt 1](https://github.com/5nik7/dots/actions/runs/34416309614) completed successfully on 2026-09-09. The actual entry point was `python3 -B experiments/go-portability/tools/ci_verify.py`, which ran `python3 -B experiments/go-portability/tools/verify.py check` followed by `python3 -B experiments/go-portability/tools/verify.py bench`, sequentially. This built and executed native Linux artifacts; it was not cross-compilation or emulation.

| Environment/build item | Recorded value |
| --- | --- |
| Runner | GitHub-hosted `ubuntu-24.04`, image `ubuntu24` / `20260907.300.1`; Ubuntu 24.04.5 LTS |
| Runtime | Linux `x86_64`, kernel `6.17.0-1022-azure` |
| CPU | Intel Xeon 6973P-C; 4 logical CPUs reported and available through affinity |
| Test filesystem | `stat -f -c %T` reported `ext2/ext3` for the temporary evidence filesystem; this ext-family magic label does not distinguish the precise mounted ext variant |
| Tools | Go 1.27.1 (`linux/amd64`), Python 3.12.3, hyperfine 1.18.0, GNU readelf/binutils 2.42; Git 2.55.0 in the job log |
| Check/benchmark metadata time | `2026-09-09T23:18:48.503430Z` / `2026-09-09T23:18:59.233111Z` |
| Build | Standard library only; `CGO_ENABLED=0`; `-trimpath -buildvcs=false -mod=readonly`; no stripping flags |
| Native binary | 3,991,208 bytes; SHA-256 `979a4f412d24d815ea484a5e8c291f70a2bc1da7cfeafaeebc30b25d37a603e5` |
| Dependencies/repeatability | No ELF interpreter or `DT_NEEDED` entries; identical relocated rebuild and identical check/bench binaries |

| Acceptance/check | Actual result |
| --- | --- |
| Host-aware harness and isolated Go configuration | Passed on native Linux; telemetry reports `off` under `<work>/config/go/telemetry`; supported-host and inherited-configuration regressions passed |
| Python regressions | Passed: 4 tests, including all 12 optimized-interpreter rejection cases, before Go invocation |
| Formatting and vet | Passed: `gofmt -l cmd internal tests` produced no paths; `go vet ./...` exited 0 |
| Native Go tests | Passed: `go test -count=1 -v ./...`, 13 top-level tests; all four isolated `TestLogoReplacement` child cases passed |
| Disposable filesystem tests | Passed: file/directory symlinks, exclusive copies, spaces, Unicode, leading dashes, existing files/directories/broken links, missing parents, and escape refusal |
| Empty-PATH CLI and snapshots | Passed: 10 command requests, Linux human/JSON identity, 7 optional-logo cases, fallback/reload, secret sentinels excluded, target snapshots unchanged |
| Rebuild and runtime inspection | Passed: byte-identical rebuild from a relocated module; `readelf -l -d` reports no interpreter or shared-library requirements |
| Startup method | Passed: original no-shell method, 3 alternating batches, 20 warmups and 200 measured executions per command per batch, public committed logo, empty PATH, stdout discarded |
| Documentation and source preservation | Passed: 71 relative links in 23 documents at the measured commit; `git diff --check`; clean committed verification inputs before/after both runs |
| Evidence retention and review | Passed: artifact upload completed; downloaded ZIP digest, 31 contained file hashes, 15 source fingerprints against the committed files, and raw timing summaries independently checked |

**Linux CI startup measurements:**

| Command | Warm samples | Median | p95 | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| `--help` | 600 | 0.977 ms | 1.244 ms | 0.781 ms | 1.391 ms |
| `--version` | 600 | 0.963 ms | 1.215 ms | 0.762 ms | 1.332 ms |

Python-timed first-observed invocations were 1.312 ms for help and 1.150 ms for version. They include spawn/wait overhead and uncontrolled cache state. The virtualized runner's frequency, co-tenancy, power, thermal state, and caches were not controlled. These are Linux CI observations, not controlled cold-start performance, a physical desktop baseline, a cross-host speedup, or an approved performance budget. Historical Termux measurements above retain their original provenance.

The [CI artifact](https://github.com/5nik7/dots/actions/runs/34416309614/artifacts/10129219910), named `phase-1-linux-6a18cc50b007fb1e0fedcedb6e4a214c0174d235-1`, contains sanitized check/bench logs, `tested-source.json` and the public input snapshots, runner metadata, native binaries, both `evidence.json` files, raw timing batches, file hashes, and result summaries. ZIP SHA-256 is `1e8b86dfc150c4b8c97646125c3d52902a17f7f785caefb1b0123d160d89b958`; size is 7,185,047 bytes. GitHub reports expiry `2026-10-09T23:19:01Z` (30-day retention). These review artifacts are not a release package; archive permissions and authenticated artifact retrieval do not establish release distribution. A downloaded review copy is retained at `/data/data/com.termux/files/usr/tmp/dots-linux-phase1-1lxhd2gs/phase-1-linux-6a18cc5.zip`, subject to temporary-file cleanup. No artifact, snapshot, or binary is committed.

Termux compatibility was rechecked with `python3 experiments/go-portability/tools/verify.py check` before the Linux commit: four Python tests, all 13 Go tests, CLI/snapshot checks, identical rebuild, and Android dependency inspection passed. Metadata time is `2026-09-09T23:11:08.814556Z`, Go 1.27.1, Python 3.14.6. The 4,070,316-byte binary remains `af73814fe6777aa2436ab5dc4c6dce18a2a9d53a9f8fa693f9f1686aa2c8d693`. Local evidence at `/data/data/com.termux/files/usr/tmp/dots-spike-artifact-u95xd0tq/evidence.json` fingerprints the uncommitted harness/workflow and the owner's local logo; that logo differs from the clean committed CI input. The CLI tests use an owned fixture logo. No Termux benchmark or cross-compilation was rerun because executable behavior was unchanged, and nothing was installed in Termux.

Windows execution, Windows filesystem policy, release packaging/checksums/permissions, clean destination retrieval/execution, WSL execution, other Linux distributions/architectures, and controlled cold-cache performance remain untested. The CI log reports Node runtime deprecation warnings for two pinned actions; checkout and artifact upload nevertheless completed successfully. No remote bootstrap, live installation, transaction engine, or Phase 2 work was performed.

### Bounded Native Windows Follow-up

**Passed on native Windows/AMD64 and Linux/AMD64 CI, with a native Termux recheck; Go remains provisional.** This authorized task started from Linux checkpoint `a337794311ed71038c42f199b0701cd900483946` on `feat/phase-1-portability`, preserving the owner's unrelated `logo.txt` edit. The resumed shell and isolated create/read/delete/cleanup check passed on 2026-09-10. The implementation stays within the authorized validation scope.

Current verification uses `GOVCS=*:off`, with its test and documentation corrected. The previous `off` value lacked the required pattern separator; historical records retain the actual inputs used then. The shared harness now handles Windows/AMD64 executable names, native paths/quoting, OS environment requirements, isolated Go settings/telemetry, UTF-8 logs, and PE dependency inspection. The optimization guard and Unix logo replacement regression are preserved. Copy/traversal tests run independently of symlink privilege requirements, and unavailable/untested cases are explicit without changing security policy.

The existing Linux job is preserved alongside native Windows CI execution and the established startup method. Source identity, dependencies, outcomes, timings, and runner limitations are retained. Both jobs passed on the implementation commit below, and Termux was rechecked. Downloaded evidence is preserved privately under `$HOME/dots-review-evidence`, outside the checkout and temporary storage. The documentation checkpoint triggers a further run whose final-commit results are reviewed and retained separately. Windows known-folder resolution, live capability probes, distribution, bootstrap, installation, transactions, and Phase 2 remain outside this task.

The first Windows attempt, [run 34421433827](https://github.com/5nik7/dots/actions/runs/34421433827) at `3717ab3416dc5c6d815f1972d4b489e086060232`, passed Python regressions and native build but failed formatting before vet/Go tests/CLI execution. All 15 captured inputs differed from committed bytes only by CRLF conversion. `core.autocrlf=false` alone did not override native line endings under the existing `text=auto` attributes. The workflow now also sets `core.eol=lf`, and the collector compares captured bytes directly with committed blobs before invoking verification. The failed Windows ZIP and successful Linux ZIP from this run are preserved in the private durable evidence archive. No Windows startup result is claimed for the failed attempt.

The second Windows attempt, [run 34421664838](https://github.com/5nik7/dots/actions/runs/34421664838) at `d83edccc22b8e3188d2726190ca9ef9bf6b86b94`, passed committed-byte checks, formatting, vet, Python regressions, CLI unit tests, copies, file/directory symlinks, and escape cases. The existing-directory copy/link cases failed their error expectation: native Windows returned `EISDIR` instead of `ErrExist`. The test now accepts only that additional Windows directory-specific refusal and still verifies object identity and content/link preservation. Later executable CLI checks and startup measurements were not reached in that failed attempt; Linux passed again.

#### Successful Native Execution and Shared Rechecks

[Run 34421915915, attempt 1](https://github.com/5nik7/dots/actions/runs/34421915915) passed both jobs on 2026-09-10 at implementation commit `fe0e5d722a322bca9d97c48aaa1dac688752e17a`. These were native builds and executions on separate hosted Windows/AMD64 and Linux/AMD64 machines, not cross-compilation, WSL, or emulation. The Windows job ran `python -B experiments/go-portability/tools/ci_verify.py`; Linux used `python3 -B experiments/go-portability/tools/ci_verify.py`. Each collector invoked the corresponding interpreter with `-B experiments/go-portability/tools/verify.py check`, then `bench`. Exact interpreter paths/argv and tool commands are retained in result metadata and logs.

| Check | Windows/AMD64 | Linux/AMD64 |
| --- | --- | --- |
| Committed source bytes, isolated config/caches/roots, offline settings | Passed; `GOVCS=*:off`, telemetry `off` under owned `APPDATA` | Passed; same controls, owned XDG telemetry path |
| Python regressions | Passed: 6 tests, including 12 optimization rejection cases | Passed: same 6 tests |
| Formatting and vet | Passed: `gofmt -l cmd internal tests`; `go vet ./...` | Passed: same commands |
| Native Go tests | Passed: `go test -count=1 -json ./...`; 14 top-level tests, 56 pass events including subtests, no skips/failures | Passed: 15 top-level tests, 57 pass events, no skips/failures |
| Copy and link fixtures | Passed: independent copies, file/directory symlinks, spaces/Unicode/leading dashes, broken links, existing objects, missing parents, slash/backslash traversal and symlink escape refusal | Passed: equivalent native Unix cases |
| Actual link permission/capability | Both file/directory links available; no permission refusal observed | Both link types available |
| Empty-PATH CLI and snapshots | Passed: 10 requests, native identity and explicit unimplemented-path warning, stream/secret checks, snapshots unchanged | Passed: 10 requests, Linux identity and snapshots unchanged |
| Optional logos | Passed: missing, empty, directory, oversized, broken link, direct/symlink executable fallback, dynamic reload | Passed: same, plus unreadable/FIFO fixtures |
| Unix logo replacement regression | Unavailable: excluded by Unix build constraint | Passed: all four isolated child cases |
| Windows ACL-denied logo | Untested; no ACL/security-policy change | Not applicable |
| Rebuild/dependencies | Passed: relocated identical rebuild; AMD64 PE/COFF; static `kernel32.dll` import | Passed: relocated identical rebuild; no ELF interpreter or `DT_NEEDED` entries |
| Startup and retention | Passed: established first-observed/warm method, all raw samples, identical check/bench binaries, evidence upload | Passed: same method and retention |
| Documentation/source preservation | Passed: relative links, whitespace, clean inputs before/after, captured bytes match commit | Passed: same checks |

The six Python tests include mocked Windows refusal classification for errors 5, 50, and 1314; those are not observations of a restricted Windows machine. An unexpected error fails the suite. Copies remain independently runnable when symlink cases are unavailable. Windows known-folder resolution, live `doctor` capability probes, ACL-denied logos, UNC/network/junction/long-path/cross-volume behavior, and ordinary unelevated desktop policy variations remain unimplemented or untested as described in [platforms.md](../docs/platforms.md). Static PE imports do not enumerate dynamic/transitive Windows DLL loading.

| Environment/build item | Windows CI | Linux CI |
| --- | --- | --- |
| Runner | `windows-2025`; image `win25-vs2026` / `20260907.229.1`; Windows build 26100 | `ubuntu-24.04`; Ubuntu 24.04.5 LTS; image `20260907.300.1`; kernel `6.17.0-1022-azure` |
| CPU | `Intel64 Family 6 Model 207 Stepping 2, GenuineIntel`; 4 logical CPUs; affinity not measured | Intel Xeon Platinum 8573C; 4 logical CPUs and 4 available through affinity |
| Evidence/test volume | NTFS via volume API, without retaining serial number | `ext2/ext3` from `stat -f` (ext-family magic label) |
| Tools | Go 1.27.1; Python 3.12.10; hyperfine 1.20.0; LLVM 20.1.8; Git 2.55.0.windows.5 in job log | Go 1.27.1; Python 3.12.3; hyperfine 1.18.0; binutils/readelf 2.42; Git 2.55.0 in job log |
| Build | Standard library only; `CGO_ENABLED=0`; `-trimpath -buildvcs=false -mod=readonly`; no stripping | Same flags and dependency policy |
| Binary | 4,207,104 bytes; `8850624e20a07a8f983b851fd0427f41a0d0e896b1c07b857ff3993afd5a909a` | 3,991,208 bytes; unchanged `979a4f412d24d815ea484a5e8c291f70a2bc1da7cfeafaeebc30b25d37a603e5` |
| Check/bench metadata time (UTC) | `00:36:27.321306` / `00:36:45.693830`, 2026-09-10 | `00:35:51.406872` / `00:36:03.748424`, 2026-09-10 |

**Windows CI and Linux CI startup measurements, kept separate:**

| Host | Command | Samples | Median | p95 | Minimum | Maximum | Python first observed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Windows CI | `--help` | 600 | 6.645 ms | 7.314 ms | 6.288 ms | 9.843 ms | 23.798 ms |
| Windows CI | `--version` | 600 | 6.345 ms | 6.916 ms | 6.033 ms | 7.443 ms | 6.854 ms |
| Linux CI | `--help` | 600 | 1.002 ms | 1.251 ms | 0.809 ms | 1.431 ms | 1.317 ms |
| Linux CI | `--version` | 600 | 0.963 ms | 1.199 ms | 0.758 ms | 1.366 ms | 1.008 ms |

Each command has three alternating hyperfine batches with 20 warmups and 200 measured executions per batch, `--shell=none`, empty PATH, stdout discarded, and the committed public logo. Windows also runs from a path containing spaces; `shlex.join` follows hyperfine's `shell_words` command-expression parsing, while Python invokes tools through argument arrays. The first-observed Windows help call was 23.798 ms; it includes Python spawn/wait overhead and is not a controlled cold-cache result. Hosted CPU allocation, co-tenancy, filesystem caches, frequency, thermal/power state, and Windows process/security-scanner overhead are uncontrolled. These numbers are platform-specific CI observations, not a comparative speedup, representative desktop-hardware baseline, or approved startup budget. Historical Termux/Linux measurements above are preserved with their original source and environment.

The native Termux recheck ran `python3 experiments/go-portability/tools/verify.py check` successfully on 2026-09-10, metadata time `00:34:42.922462Z`, after the Windows directory-refusal adjustment. All six Python tests, 15 top-level Go tests, empty-PATH CLI/snapshots, Unix logo replacement, relocated rebuild, dependency inspection, and documentation links passed. Go 1.27.1 / Python 3.14.6 produced the unchanged 4,070,316-byte Android/ARM64 binary `af73814fe6777aa2436ab5dc4c6dce18a2a9d53a9f8fa693f9f1686aa2c8d693`, with `/system/bin/linker64` and no `DT_NEEDED` entries. No benchmark or cross-compilation was rerun in Termux because executable behavior did not change; no packages were installed.

Termux `tested-source.json` identifies `d83edccc22b8e3188d2726190ca9ef9bf6b86b94` plus the then-uncommitted Windows directory-refusal test and owner logo. All 14 non-logo input hashes match `fe0e5d722a322bca9d97c48aaa1dac688752e17a` exactly. The unrelated local logo is `400a1229f5ef3bd7d60d529ef498d25d2ac77f8cbc8da129abd90953c0b654d9`; committed CI uses `c9b9059f2c336cb53838aa3287ec7135caa21183a4aa158fe94923bb0af62948`. CLI checks use owned fixture logos. Documentation added after measurement does not alter the tested implementation/harness inputs.

Durable sanitized evidence is archived privately at `/data/data/com.termux/files/home/dots-review-evidence/phase-1-windows-20260910-1dse8mjt/`, outside temporary storage and the checkout. `termux-recheck/` retains exact sources, identity, logs, binaries, `evidence.json`, and a committed-input comparison; `termux-check/` preserves the earlier successful recheck. `historical-linux/` preserves both previously downloaded Linux checkpoint ZIPs and their provenance without moving or overwriting the originals. Downloaded Windows/Linux ZIPs from all attempts remain separate, with GitHub metadata and independent review reports alongside them. Directories are `0700`, files `0600`; archived executables require an explicit execute-bit restoration to run on Unix. Nothing from this archive is in Git.

| Successful run artifact | ZIP bytes | ZIP SHA-256 |
| --- | ---: | --- |
| [Windows, artifact 10131239084](https://github.com/5nik7/dots/actions/runs/34421915915/artifacts/10131239084), `windows-fe0e5d7.zip` | 7,495,491 | `ff4e685dfdd0d2d648d07be87ada8e2d7e39739cb359758ceda78443fd225ddb` |
| [Linux, artifact 10131218148](https://github.com/5nik7/dots/actions/runs/34421915915/artifacts/10131218148), `linux-fe0e5d7.zip` | 7,190,466 | `577dbc2acd65e549cc4d4c56213759142bb362b22c06d6375e64deccb28c5cb0` |

Both ZIP digests matched GitHub's recorded digests. Independently checked 32 contained file hashes and all 15 source fingerprints per archive against the committed files; recomputed each 600-sample timing summary from raw batches; confirmed native check/bench binary hashes match. CI artifacts have 30-day retention; durable private copies preserve the evidence beyond that service retention. Action runtime deprecation warnings did not prevent execution or upload. No infrastructure blocker remains for this bounded validation. Distribution, controlled cold-cache performance, representative desktop policy/hardware, and final Go adoption remain open. The evidence supports keeping Go as the provisional candidate and proceeding to a bounded distribution experiment; it does not establish full Windows support or a production safety engine.

### Bounded Distribution Experiment

**Completed on native Termux, Linux, and Windows; Go and permanent release strategy remain provisional.** Started from `0f538ff40deaf4f51b42b4439b6ae0c2f68899f4` on `feat/phase-1-portability`. Preserve the unrelated owner logo edit; package only the public logo read from the recorded commit. No core behavior, live command, dotfiles, shell configuration, submodules, or permanent repository layout changes are required.

Added a `dist` mode to the shared verifier with Python-standard-library `.tar.gz` bundles for Termux/Linux and `.zip` for Windows. The fixed layout is `bin/dots-spike[.exe]`, `logo.txt`, and `bundle.json`; an external `SHA256SUMS` covers the archive. Record native target, source commit, committed build-input hashes, and payload hashes/modes. Reject corrupt checksums before parsing/extraction, validate the complete fixed member set, types, sizes, paths, modes, and payload identity before creating the fresh destination, and refuse existing destinations. This is a bounded test-owned extractor, not a general installer or arbitrary archive utility; checksums do not authenticate a publisher.

Exercise both formats in focused negative regressions. Run the host's bundle natively after deleting copied build inputs, under a path containing spaces and Unicode, with an empty PATH, DOTS unset, isolated roots, and a working directory outside the checkout. Require the bundled logo in help, clean version/JSON output, identical executable bytes, applicable Unix permissions, and unchanged runtime snapshots. Preserve optimized-Python rejection for the new mode.

Run native `check` and `dist` locally in Termux and in both existing CI jobs. Reuse prior startup measurements only where binary identity and behavior match; retain historical timing provenance. Keep bundles, checksums, sanitized logs, exact tested sources, and results in a new private durable directory under `$HOME/dots-review-evidence`, outside temporary storage and the checkout. Inspect both CI jobs for the final pushed commit. Publisher authentication/signing, download transport, releases/tags, installation, remote bootstrap, cross-platform policy expansion, and Phase 2 remain outside this task.

Initial native Termux `check` and `dist` passed on 2026-09-10 with Go 1.27.1, Python 3.14.6, and Git 2.55.0. Six verifier tests (14 optimization rejection cases), seven distribution regressions, and all 15 top-level Go tests passed. The extracted executable retained SHA-256 `af73814fe6777aa2436ab5dc4c6dce18a2a9d53a9f8fa693f9f1686aa2c8d693`, so prior Termux startup evidence remains applicable. The bundle contained the committed 248-byte logo (`c9b9059f2c336cb53838aa3287ec7135caa21183a4aa158fe94923bb0af62948`), not the local edit. Private evidence is under `/data/data/com.termux/files/home/dots-review-evidence/phase-1-distribution-20260910-trlmvjbr/termux/`; source snapshots identify the then-uncommitted tooling. Desktop results and the subsequent committed-source Termux run are recorded below.

#### Distribution Results

[Run 34423939448, attempt 1](https://github.com/5nik7/dots/actions/runs/34423939448) passed both native desktop jobs at implementation commit `613e64c7de8fd16a858554fd26f3a451f316e764` on 2026-09-10. Linux ran `python3 -B experiments/go-portability/tools/ci_verify.py`; Windows ran `python -B experiments/go-portability/tools/ci_verify.py`. Each collector ran `verify.py check` followed by `verify.py dist` with that interpreter. Termux ran `python3 experiments/go-portability/tools/verify.py check` before commit and `python3 experiments/go-portability/tools/verify.py dist` both before and after commit. These were native builds and executions, not cross-compilation or emulation. The final documentation checkpoint triggers both CI jobs again; its evidence is retained separately rather than relabeling the implementation-run results below.

| Acceptance/check | Actual result |
| --- | --- |
| Minimal native bundle and source identity | Passed on all three targets: fixed executable/logo/metadata layout, recorded commit and Go-input/payload hashes; committed logo only |
| External archive checksum | Passed: supplied manifest verified before parsing/extraction; deliberately flipped archive byte rejected before extraction or execution |
| Complete member/path/type/mode validation | Passed: seven focused regressions exercise both formats, including unsafe/duplicate names, nonregular entries, missing members, identity mismatch, limits, malformed input, and existing destination refusal |
| Fresh extraction and executable identity | Passed: spaces/Unicode destination, binary matches verified build; Termux/Linux `0755` binary and `0644` logo/metadata; POSIX execute bits not applicable to Windows |
| Runtime independence | Passed: original copied binary/source directories deleted before extraction/execution; empty PATH, DOTS unset, new owned roots, working directory outside checkout |
| Bundled help/version/JSON and read-only behavior | Passed: all three extracted requests on each native host; bundled logo discovered from executable location; isolated runtime snapshots unchanged |
| Existing focused suite | Passed: 6 verifier tests including 14 optimization rejection cases, plus 7 distribution tests; 15 top-level Go tests on Termux/Linux and 14 on Windows; formatting/vet/CLI/fixtures/rebuild/dependency inspection retained |
| Native link/Unix replacement coverage | Existing check passed; Windows file/directory links available with no observed permission refusal; Unix FIFO replacement unavailable on Windows and ACL-denied-logo behavior still untested |
| Evidence and documentation | Passed: private durable retention, independent outer/nested archive/source/payload review, relative links, and whitespace checks |
| Startup | Reused prior native evidence after confirming unchanged Go sources and all three executable hashes; no new benchmark or controlled cold-cache claim |
| Failed cases | No unresolved verification failures; negative-input tests passed by refusing their inputs. An initial duplicate-name fixture had the wrong mode, was corrected, and its focused regressions passed before commit |

| Native host | Environment and tools | Distribution metadata time (UTC, 2026-09-10) |
| --- | --- | --- |
| Termux Android/ARM64 | Existing app-private f2fs fixture context; Go 1.27.1, Python 3.14.6, Git 2.55.0; kernel `5.4.274-qgki-30957850-abG996USQSJHZB1` | `01:04:39.239676` |
| Linux/AMD64 CI | Ubuntu 24.04.4, image `20260831.293.1`, kernel `6.17.0-1022-azure`, AMD EPYC 9V74, 4 CPUs/affinity, ext-family `ext2/ext3` magic label; Go 1.27.1, Python 3.12.3, Git 2.55.0, binutils 2.42 | `01:04:54.254205` |
| Windows/AMD64 CI | `windows-2025`, image `win25-vs2026` / `20260907.229.1`, Windows build 26100, AMD64 Family 25 Model 1 Stepping 1, 4 CPUs, NTFS; Go 1.27.1, Python 3.12.10, Git 2.55.0.windows.5, LLVM 20.1.8 | `01:05:24.442332` |

The runtime/build flags and dependencies are unchanged. Native executable SHA-256 values remain Termux `af73814fe6777aa2436ab5dc4c6dce18a2a9d53a9f8fa693f9f1686aa2c8d693`, Linux `979a4f412d24d815ea484a5e8c291f70a2bc1da7cfeafaeebc30b25d37a603e5`, and Windows `8850624e20a07a8f983b851fd0427f41a0d0e896b1c07b857ff3993afd5a909a`. The prior Windows/Linux startup artifacts are from [run 34422396422](https://github.com/5nik7/dots/actions/runs/34422396422), source `0f538ff40deaf4f51b42b4439b6ae0c2f68899f4`; prior Termux timings keep their original provenance above. Archive digests change when `bundle.json` records another source commit even when executable bytes are identical. No archive reproducibility across compression libraries/tool versions is claimed. Startup reuse preserves the original benchmark configuration; archive extraction and startup from the extracted Unicode path with fallback-logo discovery were not timed separately.

| Bundle at `613e64c7de8fd16a858554fd26f3a451f316e764` | Bytes | Archive SHA-256 |
| --- | ---: | --- |
| `dots-spike-termux-arm64.tar.gz` | 2,177,774 | `ff4250fc9003b499ec5b99a197dda9b098525f2e1fefea8518ea562150447bd0` |
| `dots-spike-linux-amd64.tar.gz` | 2,355,462 | `c25a51b723d0527c1e5fc69a1115496862ab19a64be113f30817529e2238f440` |
| `dots-spike-windows-amd64.zip` | 2,457,862 | `000785202c8f0076cc118599b3a7f8b3ad96f6c10e3ad74371ab794e7dfc0802` |

Every bundle contains the committed 248-byte logo with SHA-256 `c9b9059f2c336cb53838aa3287ec7135caa21183a4aa158fe94923bb0af62948`. The owner's preserved local edit remains `400a1229f5ef3bd7d60d529ef498d25d2ac77f8cbc8da129abd90953c0b654d9`, excluded from commits and bundles. The committed Termux distribution snapshot differs from committed CI inputs only by that unrelated working-tree logo; all tooling and Go input hashes match the implementation commit. Its initial pre-commit `check` covers the same check behavior; a subsequent distribution-only change sanitized parsed Windows JSON before log encoding, and the committed `dist` run verified that path locally and in both CI hosts.

Durable private evidence is `/data/data/com.termux/files/home/dots-review-evidence/phase-1-distribution-20260910-trlmvjbr/`. `termux/` retains initial check/dist evidence and exact uncommitted source snapshots; `termux-committed-dist/` retains committed-tooling distribution evidence. `linux-613e64c.zip` and `windows-613e64c.zip` preserve the CI artifacts, with GitHub metadata and independent review reports alongside them. The CI artifacts are [Linux 10131937463](https://github.com/5nik7/dots/actions/runs/34423939448/artifacts/10131937463) and [Windows 10131950525](https://github.com/5nik7/dots/actions/runs/34423939448/artifacts/10131950525). Their outer ZIP digests are `f4494368a6abd28c0918ba56372495588f1a9cd51d94ed60b39e9e890f00f108` and `c3385490b3af7ec05f92043d00a06b5c98e77c9e75124e3bd59ef7d84d0eef9e` respectively. Both matched GitHub; 36 contained file hashes and 17 source fingerprints per artifact were checked, along with nested bundle manifests/layout/payloads, committed logo bytes, sanitized runtime logs, and previous executable identities. Archive directories are `0700`, files `0600`; nested tar metadata retains the tested executable mode. Earlier evidence is preserved in its existing durable archive.

These results prove this bounded build/package/verify/extract/execute path. They do not authenticate a publisher, exercise a remote download/installer, settle permanent release formats or support baselines, or implement installation rollback. Windows ACL/policy variations, known-folder resolution, UNC/junction/long-path/cross-volume cases, WSL/other architectures, hostile concurrent extraction-parent changes, representative desktop hardware, and controlled cold-cache performance remain outside the tested scope. No release/tag, live command/dotfile change, Termux package install, submodule initialization, bootstrap, or Phase 2 work occurred.

## Remaining Decisions and Next Milestone

The owner accepted [0002: Go adoption](../docs/decisions/0002-phase-1-go-adoption.md) on 2026-09-10, approving all four decisions at proposal commit `c7d86a989e6397a3ecd74407e63097994f183694`. The language, initial development targets/toolchain, advisory warm budgets and regression-review policy, bundle/release-trust direction, gap classifications, and first permanent-core task are accepted. Their implementation and production-support gates remain pending. Experimental checksums alone do not authenticate a publisher.

The accepted built-in-only permanent-core slice is now tracked in [the Phase 2 plan](phase-2-command-center.md). The historical approval-recording task did not implement it. The historical experiment decision, executable, tests, and retained evidence are unchanged.

The retained final-checkpoint [CI run 34424607080](https://github.com/5nik7/dots/actions/runs/34424607080) passed native Linux/Windows checks and distribution verification at `dcfea900875656750c6c4b763c1f9119e4339b6a`. Final Termux distribution evidence and desktop reviews are retained separately in the existing private distribution archive; decision 0002 records their provenance and reuses verified results without relabeling earlier measurements.

Restricted/unelevated Windows policy and ACL behavior, known-folder resolution, UNC/junction/long-path/cross-volume cases, WSL/other architectures, and controlled cold-cache or representative desktop-hardware performance remain separate gaps. Scope any required follow-up explicitly. No Phase 2, bootstrap, real-home installation, transaction, manifest, migration, or repository-size work begins automatically from this evidence.

The implemented command surface is documented in [commands.md](../docs/commands.md), runtime/path limitations in [platforms.md](../docs/platforms.md), and runner guarantees in [testing.md](../docs/testing.md). No documentation for a feature implemented in this experiment is intentionally deferred.
