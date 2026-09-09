# Phase 1 Termux Portability Experiment

**Status: Completed for the authorized Termux experiment; broader Phase 1 and Go adoption remain open**

## Scope and Reconciliation

Start from `c1be6eb2417ece2218beb5f724de1b8de27cf403` with a clean working tree. The owner's intervening commits added `logo.txt`, committed the Zsh changes, and repaired the Bash prototype's help/error path. Preserve these files exactly. The experiment is additive under `experiments/go-portability/`; the live `bin/dots` remains the active command.

Implement help (including optional `logo.txt`), version output, and read-only diagnostics in an independent standard-library-only Go module. Build and run natively with the installed Termux Go toolchain. Probe filesystem primitives only in disposable test-owned directories. Confine build caches and artifacts to temporary roots and record repeatable startup measurements.

This limited prerequisite may proceed while Phase 0's manifest, module, and repository-size decisions remain open. It does not complete the end-to-end [Termux MVP](termux-mvp.md).

## Boundaries

No package installation, proot, bootstrap, real-home installation, transaction engine, shell changes, directory migration, secret reads, private submodule initialization, commits, or pushes. No production mutation API is introduced. Go adoption, distribution, extension protocol, manifests, and permanent core layout remain deferred.

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

## Remaining Decisions and Next Milestone

Review these results before adopting Go or promoting the experimental module into the permanent core layout. Complete native Linux/Windows execution and desktop startup evidence, decide the release/distribution strategy, and establish acceptable performance budgets with the owner. Cold-cache evidence remains separately incomplete. Then scope Phase 2's command registry, extension trust, longest-prefix resolution, shared metadata, and completion design. Manifest format, migrated modules, transaction behavior, bootstrap, real-home installation, and repository-size changes remain deferred.

The implemented command surface is documented in [commands.md](../docs/commands.md), runtime/path limitations in [platforms.md](../docs/platforms.md), and runner guarantees in [testing.md](../docs/testing.md). No documentation for a feature implemented in this experiment is intentionally deferred.
