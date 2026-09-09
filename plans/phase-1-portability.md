# Phase 1 Termux Portability Experiment

**Status: Authorized Termux experiment and bounded native Linux CI validation completed; broader Phase 1 and Go adoption remain open**

## Scope and Reconciliation

Start from `c1be6eb2417ece2218beb5f724de1b8de27cf403` with a clean working tree. The owner's intervening commits added `logo.txt`, committed the Zsh changes, and repaired the Bash prototype's help/error path. Preserve these files exactly. The experiment is additive under `experiments/go-portability/`; the live `bin/dots` remains the active command.

Implement help (including optional `logo.txt`), version output, and read-only diagnostics in an independent standard-library-only Go module. Build and run natively with the installed Termux Go toolchain. Probe filesystem primitives only in disposable test-owned directories. Confine build caches and artifacts to temporary roots and record repeatable startup measurements.

This limited prerequisite may proceed while Phase 0's manifest, module, and repository-size decisions remain open. It does not complete the end-to-end [Termux MVP](termux-mvp.md).

## Boundaries

The original experiment authorized no package installation, proot, bootstrap, real-home installation, transaction engine, shell changes, directory migration, secret reads, private submodule initialization, commits, or pushes. Subsequent checkpoint and Linux tasks explicitly authorized scoped feature-branch commits/pushes; the Linux task additionally allowed development prerequisites in CI only. The other boundaries remain in force. No production mutation API is introduced. Go adoption, distribution, extension protocol, manifests, and permanent core layout remain deferred.

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

The harness accepts native Termux Android/ARM64 and Linux/AMD64. Linux children omit Termux markers; both retain owned home/config/data/state/cache/temp/repository roots, the optimization guard, and the logo replacement regression. Before invoking Go, it seeds telemetry mode `off` in its owned XDG config directory and checks the reported mode/location. `GOENV`, `GOWORK`, `GOPROXY`, `GOSUMDB`, and `GOVCS` are `off`; `GOTOOLCHAIN=local`. Verification does not fetch modules or toolchains. The branch-push workflow provisions development prerequisites in CI only and checks out without initializing submodules.

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

## Remaining Decisions and Next Milestone

Review these results before adopting Go or promoting the experimental module into the permanent core layout. Native Linux CI execution now passes. The next bounded task should adapt the isolated harness for native Windows/AMD64 and record actual runtime/filesystem behavior without installation; keep release/distribution checks separately pending. Decide the distribution strategy and acceptable performance budgets with the owner, and gather representative desktop-hardware evidence if required. Cold-cache evidence remains separately incomplete. Then scope Phase 2's command registry, extension trust, longest-prefix resolution, shared metadata, and completion design. Manifest format, migrated modules, transaction behavior, bootstrap, real-home installation, and repository-size changes remain deferred.

The implemented command surface is documented in [commands.md](../docs/commands.md), runtime/path limitations in [platforms.md](../docs/platforms.md), and runner guarantees in [testing.md](../docs/testing.md). No documentation for a feature implemented in this experiment is intentionally deferred.
