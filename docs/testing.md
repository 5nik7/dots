# Testing Strategy

**Status: Focused runner verified on native Termux and Linux/Windows CI; broader strategy proposed**

Testing must prove that `dots` protects user data, resolves specifications deterministically, behaves consistently across adapters, and remains fast on representative machines.

## Permanent Core Verification

The independent root-core runner exists alongside the preserved experiment:

```bash
python3 -B tools/verify_core.py build
python3 -B tools/verify_core.py check
python3 -B tools/verify_core.py bench
python3 -B tools/verify_core.py docs
python3 -B tools/test_verify_core.py
```

Use `python` in PowerShell. Supported native verification hosts are Termux Android/ARM64, Linux/AMD64, and Windows/AMD64, with the installed Go 1.27.1 policy pin enforced. Other architectures are refused. Python must be unoptimized: six Python regressions include ten early optimization-refusal cases covering all four modes and help with `-O` or positive `PYTHONOPTIMIZE`. Missing prerequisites never trigger installation. Build uses only Go/Python; check adds gofmt and readelf/LLVM, bench adds hyperfine. No core distribution/cross/installer mode is introduced.

The runner copies only root `go.mod` and `.go` sources under `cmd`, `internal`, and `tests` into a fresh owned source tree with spaces in its path. It fingerprints those inputs, the public logo, its three Python tools, and the workflow. It rejects symlinked inputs and changes during execution. Source, runtime, home/config/data/state/cache/temp, Go caches/configuration, and telemetry are isolated with the same offline policy as the experiment below (`GOENV=off`, `GOWORK=off`, `GOTOOLCHAIN=local`, `GOPROXY=off`, `GOSUMDB=off`, `GOVCS=*:off`, `CGO_ENABLED=0`). Telemetry is seeded off in the owned config before invoking Go and its location is checked. No real shell config, user Go config, credentials, or package database is used. Windows retains only required system paths and redirects user folders.

`check` runs the Python regressions, formatting, vet, uncached Go JSON tests, process/optional-logo checks, dependency inspection, a byte-identical relocated rebuild, and documentation links. `tests/cli_test.go` requires an absolute runner-supplied `DOTS_CORE_TEST_BIN`; missing input fails closed instead of building against inherited settings. Its process cases use explicit owned roots containing spaces, Unicode and a leading dash, empty PATH, poison configuration/extension fixtures, sensitive sentinels, deadline-bounded execution, and unchanged-root snapshots. These snapshots cover type/mode/size/modification time and regular-file hashes, not access times or a system-wide syscall trace. Directory metadata comes from opened handles rather than cached enumeration records; a fixture regression checks stable observations and detection of content changes/removal.

Registry tests cover canonical/alias/global collisions, required metadata, overlapping synthetic routes, unchanged remaining arguments, global-only version, injected unavailability, and defensive projections. CLI tests compare help/examples to the same metadata. A dependency guard requires `internal/dispatch` to have no `os`, `io/fs`, `path/filepath`, `os/exec`, or `net` dependency, keeping direct lookup independent of runtime discovery. The ported Unix logo replacement test retains its isolated child and 10-second deadline. Windows ACL-denied logos remain untested; native known-folder resolution is unimplemented and capabilities stay `not_probed`. No filesystem mutation engine was ported from the experiment.

`bench` builds once and measures complete `--help`/`--version` processes using the existing three alternating batches, 20 warmups and 200 samples per command per batch, empty PATH, no shell, public logo and discarded stdout. It retains all 600 samples per command and median/nearest-rank p95/min/max, plus separate first-observed Python timings. It then runs `BenchmarkRegistryLookup` at 3, 1,000 and 10,000 synthetic entries, `-benchmem -benchtime=200ms -count=3`; raw ns/op, allocation and iteration results measure in-process lookup only. Registry construction is outside that timed loop; it remains included in complete-process startup. Benchmarks and builds/checks run sequentially. Budgets and review thresholds in decision 0002 remain advisory numeric checks, with no cold-cache or physical-desktop claim.

Every mode except docs retains `bin/dots` (or `.exe`), the logo and sanitized `evidence.json` under a unique `dots-core-artifact-*` temporary directory; caches and fixture roots are removed. Preserve reviewed evidence privately under `$HOME/dots-review-evidence` before temporary retention expires. The source hashes identify uncommitted local runs; CI also compares every input to its commit and retains exact public source snapshots. Reuse historical experiment evidence only for unchanged experimental inputs; the new core has its own fresh binary identity and measurements.

`tools/ci_core.py` runs core check then bench and verifies source/native binary identity across both. The existing workflow now covers `main`, both Phase 1/Phase 2 feature branches, and PRs targeting `main`; PR checkout and evidence identify GitHub's tested merge commit. The existing experiment collector still runs check/dist and uploads its independent artifact before core checks. Native Linux/Windows jobs provision development hyperfine/readelf/LLVM only in CI, then run offline verification. Core artifacts are `phase-2-core-<linux|windows>-<commit>-<attempt>`, retained for 30 days, with allowlisted source, logs, binary, raw timings and hashes. Final native outcomes and limitations are recorded in the [focused plan](../plans/phase-2-command-center.md).

## Implemented Portability Runner

From the repository root on native Termux Android/ARM64, Linux/AMD64, or Windows/AMD64 (use `python` in PowerShell when that is the installed Python command):

```bash
python3 experiments/go-portability/tools/verify.py build
python3 experiments/go-portability/tools/verify.py check
python3 experiments/go-portability/tools/verify.py bench
python3 experiments/go-portability/tools/verify.py cross
python3 experiments/go-portability/tools/verify.py dist
python3 experiments/go-portability/tools/verify.py docs
git diff --check
```

`build` is verified with installed Go 1.27.1 and Python 3. The accepted build/test baseline is Go 1.27.1; the preserved experiment still declares its historical `go 1.27.0` module minimum and does not enforce the project policy pin. `check` additionally needs `gofmt` and either `readelf` on Unix or LLVM `llvm-readobj` on Windows; `bench` needs `hyperfine`. `cross` uses only the same Go/Python tools. `dist` additionally needs installed Git to read the committed logo and identify committed Go build inputs; archive/compression/checksum handling uses the Python standard library. Missing tools are named explicitly and never installed. The harness accepts native Android/ARM64, Linux/AMD64, and Windows/AMD64 Go hosts; other native hosts remain deferred. Human and JSON diagnostic expectations follow the selected native host; Linux and Windows child environments omit Termux markers. Windows diagnostics require runtime identity, the executable path, unprobed capabilities, and an explicit warning that known-folder/path resolution is unimplemented. `docs` is a read-only relative Markdown link check and does not require Go.

Use Python without optimization. Every verifier mode, including its own `--help`, rejects an optimized interpreter (`python3 -O`, `python3 -OO`, or a positive `PYTHONOPTIMIZE`) with exit status 1 and an explicit error on stderr, before argument parsing, tool lookup/invocation, or temporary work/artifact creation. Rerun without optimization flags and with `PYTHONOPTIMIZE` unset or `0`. This guard keeps the existing assertion-based CLI behavior, read-only fixture, and identical rebuild checks active.

The focused Python regression can also run without Go or a build:

```bash
python3 -B experiments/go-portability/tools/test_verify.py
```

Two optimization tests launch the verifier with `-O` and, separately, `PYTHONOPTIMIZE=1` across all six modes and `--help` (14 cases). Children use an empty `PATH`, test-owned home/config/data/state/cache/temp/repository roots, and disabled bytecode writes. Each case requires exit status 1, empty stdout, the exact optimization error, and an unchanged snapshot of the initially empty fixture directories. The suite uses `unittest` assertion methods, which remain active under optimized Python. Four additional tests cover supported/unsupported host identities, isolation from inherited Go/configuration settings, executable suffixes and Windows path redaction, and recognized Windows symlink refusals, for six Python tests total. Mocked refusal codes test classification; only native fixture attempts establish actual capabilities.

Each non-documentation invocation owns a fresh temporary work directory, copies only the experiment's Go sources and the public logo, and supplies isolated home/config/data/state/cache/temp/bin/repository roots. Go configuration is ignored with `GOENV=off` and `GOWORK=off`; automatic toolchain/module downloads are disabled with `GOTOOLCHAIN=local`, `GOPROXY=off`, `GOSUMDB=off`, and `GOVCS=*:off`. Go caches, GOPATH, and compiler scratch files are redirected into the owned root. Before any Go invocation, the harness creates a telemetry `mode` file containing `off` under its own `XDG_CONFIG_HOME/go/telemetry` on Unix or `APPDATA\go\telemetry` on Windows; it checks `go env GOTELEMETRY GOTELEMETRYDIR` to verify mode and location. This disables counter collection/uploads without touching host Go settings. Windows children retain only required `SystemRoot`/`WINDIR` system paths; `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, and the combined `HOMEDRIVE`/`HOMEPATH` point into owned roots. UTF-8 subprocess decoding and `.exe` names are explicit. Tool invocations use argument arrays, with no shell. `GOTELEMETRY` is a read-only Go environment value, so setting an environment variable alone is not used as an off switch. See the [Go telemetry configuration reference](https://go.dev/doc/telemetry#configuration). Tests do not source shell configuration or call package managers. No `go install`, `go env -w`, dependency fetch, or submodule operation is used.

At completion the harness retains only artifacts in a new temporary `dots-spike-artifact-*` directory: `bin/`, the public `logo.txt` copy, and `evidence.json`. It prints the native executable path on stdout and progress/evidence location on stderr. Evidence also records Python/dependency-inspector versions, structured Go test and CLI case outcomes, native execution versus compilation, offline Go settings, and SHA-256 fingerprints of Go/Python sources, the workflow when present, and the public logo. Inputs are fingerprinted again before retention to refuse source changes during a run; retained metadata replaces checkout/work paths with placeholders. Build work, caches, and fixtures are automatically cleaned through their owning temporary-directory context. The module's `.gitignore` also excludes accidental local binaries/test executables and Python bytecode. The harness does not create bytecode. Do not add retained temporary evidence or binaries to Git; record reviewed summaries in the focused plan.

`check` first runs the six verifier regressions and seven distribution regression tests in its isolated environment, before invoking Go. It then runs `gofmt -l`, `go vet ./...`, and uncached `go test -count=1 -json ./...` in the copied module. Tests cover argument/stream contracts, help/version fast paths, metadata collisions, JSON schema, platform detection/false positives, path defaults, and warning behavior. Go filesystem tests use `testing.T.TempDir` and `os.Root` to test file/directory links, explicit exclusive copies, spaces, Unicode, leading dashes, existing objects, broken links, missing parents, and traversal/symlink escape refusal. Escape sentinels are also test-owned. Copy, missing-copy-parent, and direct traversal tests run independently of symlink availability. Only Windows errors 5 (access denied), 50 (not supported), and 1314 (privilege not held) mark link cases unavailable; unexpected errors fail. Go JSON pass/skip/fail events are retained as passed/unavailable/failed, with refusal reasons in logs. Broken-link fixtures necessarily require link creation. These primitives are not production apply or rollback operations.

Existing-target tests require `ErrExist`, or specifically `EISDIR` for an existing directory on Windows, followed by object-identity/content/link-target preservation checks. An arbitrary failure does not satisfy overwrite refusal.

`TestLogoReplacement` runs a Unix-only child of the Go test executable in fresh test-owned home/config/data/state/cache/temp/repository/bin roots with an empty `PATH`. Its injected opener replaces a regular file or a symlink target with a FIFO after the preliminary pathname check. A writer-present FIFO also tests rejection before a read could block, and a valid regular-file symlink checks compatibility. The parent enforces a 10-second child deadline and cleans up its own roots even when a faulty implementation hangs. This is deterministic boundary replacement, not a probabilistic stress test, race-detector run, or general I/O timeout guarantee.

The harness executes the prebuilt CLI with an empty `PATH` and controlled environment, tests optional logo failures (including a FIFO), checks dynamic logo reload and executable-symlink fallback, and compares fixture snapshots before and after read-only requests. Snapshots cover contents, object types, sizes, and modification times, not access times or system-wide syscall tracing. It also compares a rebuild from a relocated source path byte-for-byte and records ELF interpreter/library metadata or PE/COFF AMD64 headers and static DLL imports. PE inspection does not enumerate dynamic or transitive DLL loading. Windows runs missing/empty/directory/oversized logos, dynamic reload, direct fallback, and link-dependent cases when available. Windows ACL-denied logo behavior is explicitly untested; Unix FIFO cases are unavailable on Windows. No registry, Developer Mode, elevation, or security-policy changes are made to force success.

`bench` builds once, then runs the compiled executable directly with the public logo and an empty `PATH`. It records a Python-timed first observed invocation for each command, followed by three hyperfine batches per command, 20 warmups and 200 measured executions per batch, with alternating command order, no shell, and stdout discarded. The 600 samples per command yield pooled median, nearest-rank p95, minimum, and maximum. Raw batches and build/environment metadata are retained in `evidence.json`. Windows additionally executes from a path containing spaces. Hyperfine `--shell=none` parses command expressions with `shell_words` on both platforms, so the harness uses `shlex.join` for those expressions and Python argument arrays for outer process invocation. First-observed timings include the Python parent's spawn/wait overhead and have uncontrolled filesystem cache state. Warm hyperfine timings measure complete process execution. Neither establishes true cold-cache startup or a shell-startup budget; no cache flush, reboot, or power/thermal control is performed.

`cross` builds Linux/AMD64 and Windows/AMD64 executables and compiles each test package with `go test -c`; it does not run foreign artifacts. Fixture success on Termux is not native Windows/WSL evidence. No race-detector, transaction, or bootstrap suite is claimed. Native Linux and Windows evidence belongs to separately executed CI jobs below; cross-compilation remains compilation evidence only. Results and limitations are recorded in the [focused plan](../plans/phase-1-portability.md).

## Experimental Distribution Check

`python3 experiments/go-portability/tools/verify.py dist` builds natively with the same isolated, offline toolchain settings and runs seven focused distribution regressions plus the six verifier regressions. Git reads `HEAD:logo.txt` as bytes, so an unrelated working-tree logo edit is excluded from the bundle. All copied Go inputs must match the recorded commit; an uncommitted Go change is refused rather than attributed to that commit. Tooling may be uncommitted during local verification, and its exact hashes are retained separately in `evidence.json`/the evidence collector.

The temporary artifact contains `distribution/dots-spike-<platform>-<architecture>.tar.gz` for Termux/Linux or `.zip` for Windows, and `distribution/SHA256SUMS`. The fixed archive layout contains exactly these regular files:

```text
bin/dots-spike       # bin/dots-spike.exe on Windows
logo.txt            # committed public logo
bundle.json         # experimental schema 1: platform/OS/architecture/commit,
                    # committed Go source hashes and executable/logo sizes,
                    # hashes and archive modes
```

The external manifest is one ASCII SHA-256 line naming the archive. The verifier hashes and parses the same bounded in-memory archive bytes. A checksum mismatch is rejected before archive parsing, extraction-root creation, or execution. A matching checksum proves agreement with the supplied manifest; it does not authenticate a publisher. Signing, authenticated retrieval, release channels, and permanent release packaging remain outside this experiment.

Before creating the destination, the extractor validates the complete fixed member set, rejects duplicates and all other paths (including traversal, absolute/drive paths, backslashes, alternate streams and reserved-name aliases), requires plain regular files with expected modes, and checks metadata and payload hashes against the known build. It rejects links, devices/FIFOs, directories, sparse/PAX tar members, and unsupported ZIP encodings. Bounds are 16 MiB for the archive, 10 MiB for expanded tar data, 8 MiB for the executable, and 64 KiB each for the logo and metadata. It writes only validated payload bytes with exclusive file creation; it never calls `extractall` or reuses an existing destination.

Extraction runs only under a fresh test-owned parent, into a directory containing spaces and Unicode. On Unix, the binary must have mode `0755` and logo/metadata `0644`; Windows records POSIX execute bits as not applicable and proves actual process execution. The test removes its original binary directory and copied Go source repository before extracting/running the bundle. New isolated home/config/data/state/cache/temp/repository roots, an empty PATH, DOTS unset, and a working directory outside the checkout force executable-relative logo discovery. Extracted binary bytes must match the verified build. Help must show the bundled logo; version and JSON diagnostics must remain clean. Runtime snapshots, including the extracted bundle, must remain unchanged after all three requests.

This is an internal fixed-layout test-owned extractor, not an installer or general archive tool. No filesystem race protection against another actor changing the owned extraction parent, hostile network-filesystem behavior, generalized archive compatibility, durable installation rollback, or system-wide syscall audit is claimed. Failure may leave partial files in the disposable destination until its owning temporary context cleans them up; no live state is affected.

Run failure regressions without Go or a build:

```bash
python3 -B experiments/go-portability/tools/test_distribution.py
```

The seven tests exercise both formats: successful round trips, checksum-before-parser rejection, malformed manifests, unsafe/duplicate names, nonregular members, bad permissions, missing files, wrong payload/metadata identity, archive/payload/expansion bounds, malformed archives, and existing-destination preservation. Native `dist` additionally flips a byte in a real executable archive and requires checksum refusal before extraction/execution. No foreign executable is run by these format regressions. Native Termux/Linux/Windows outcomes are recorded in the [focused plan](../plans/phase-1-portability.md#bounded-distribution-experiment).

The experiment CI collector runs `check` and `dist`; previous spike startup evidence is reused only after comparing binary identity and unchanged behavior. The manual `bench` mode remains available if a later executable change requires new measurements. Reuse preserves the original benchmark configuration and limitations; it does not time archive extraction or establish startup performance for the extracted Unicode path and fallback-logo configuration.

## Native Linux and Windows CI

The [Phase 1 workflow](../.github/workflows/phase-1-linux.yml) runs on pushes to `feat/phase-1-portability`, `feat/phase-2-core-registry`, and `main`, and on PRs targeting `main`, using `ubuntu-24.04`/AMD64 and `windows-2025`/AMD64 jobs, pinned action revisions, Go 1.27.1, and disabled setup-go caching. Linux CI provisions `binutils` and `hyperfine`; Windows CI provisions hyperfine 1.20.0 and requires the runner’s LLVM `llvm-readobj`; Termux never installs them through this runner. Checkout uses `submodules: false` and does not retain credentials. Windows checkout sets both `core.autocrlf=false` and `core.eol=lf` to preserve committed bytes under this repository's `text=auto` attributes. The collector compares every captured input byte-for-byte with `git show <commit>:<path>` before verification; a clean Git status alone does not establish identical line endings. Verification subprocesses receive allowlisted environment values without GitHub tokens, then the harness creates its own Go and CLI environments. Toolchain/module downloads remain disabled throughout verification.

`python3 -B experiments/go-portability/tools/ci_verify.py` is the CI-only collector. It now runs `check` then `dist` sequentially and verifies commit identity, clean public inputs, matching source hashes, and identical native binaries across both runs. Its artifact directory is `$RUNNER_TEMP/dots-linux-evidence` or `$RUNNER_TEMP/dots-windows-evidence`, outside the checkout. It records runner image/kernel/CPU/filesystem details and actual Go, Python, Git, and readelf/LLVM versions; no full environment dump is collected.

An always-run upload step retains `phase-1-<linux|windows>-<commit>-<attempt>` for 30 days: sanitized check/distribution logs, `tested-source.json` and public source snapshots, native binaries and `evidence.json`, experimental bundles and external manifests, hashes, and result summaries. Historical spike benchmark artifacts retain their original raw timings; the experiment collector does not rerun benchmarks. The independent permanent-core collector runs fresh benchmarks as described above. Logs from failed verifier processes are included when available; provisioning/collector failures remain visible in the workflow job log. Downloaded artifact executables may need their execute bit restored because GitHub artifact storage does not preserve file permissions. These are experimental review artifacts, not published or authenticated release packages.

Startup results are **Linux CI measurements** or **Windows CI measurements**, labeled separately, using the existing warm/first-observed method. Virtualized runner CPU allocation, co-tenancy, frequency, and cache state are not controlled; this does not establish controlled cold-cache or representative desktop-hardware performance. Infrastructure availability alone is not a passing run: actual run links and outcomes belong in the [Phase 1 results](../plans/phase-1-portability.md). The first [native Linux run](https://github.com/5nik7/dots/actions/runs/34416309614) passed check, bench, source/binary identity checks, and evidence upload on 2026-09-09. Its [artifact](https://github.com/5nik7/dots/actions/runs/34416309614/artifacts/10129219910) was downloaded and its source/file hashes and timing summaries verified against the committed inputs and raw samples. The [native Windows and Linux follow-up run](https://github.com/5nik7/dots/actions/runs/34421915915) passed both jobs at `fe0e5d722a322bca9d97c48aaa1dac688752e17a` on 2026-09-10. Windows ran 14 top-level Go tests and Linux ran 15, plus six Python tests on each host. All Go cases passed; Windows file/directory links were available with no observed permission refusal. Windows ACL-denied logos remain untested and Unix FIFO replacement is unavailable there. Bounded distribution validation passed on Termux and in both jobs of [run 34423939448](https://github.com/5nik7/dots/actions/runs/34423939448) at `613e64c7de8fd16a858554fd26f3a451f316e764`; release publication, authentication/signing, and download transport remain untested. Download and preserve reviewed ZIPs in a private durable directory outside temporary storage and the checkout; verify archive digests, source fingerprints against the tested commit, contained file hashes, and timing summaries against raw samples.

## Broader Proposed Isolation Model

Every test that can mutate state receives explicit test-owned roots:

```text
TEST_ROOT/
├── home/
├── repo/
├── config/
├── data/
├── state/
├── cache/
├── tmp/
└── bin/
```

The harness should make mutations outside these roots fail closed. Tests do not inherit the developer's actual `HOME`, XDG roots, Windows known folders, package-manager executables, or repository selection unless a read-only test requires a deliberately captured fixture.

## Test Layers

### Unit

- Longest-prefix route resolution.
- Built-in and extension precedence.
- Metadata parsing and validation.
- Platform detection from fixtures.
- Path expansion, normalization, and allowed-root validation.
- Profile dependency resolution and cycle detection.
- Resource collision and replacement rules.
- Current-target classification.
- Plan ordering and inverse operation construction.
- State and output schema round trips.

### Golden Output

- Human help and command discovery.
- Structured command records.
- Human and JSON specification output.
- Human and JSON plans.
- Conflict, unavailable-platform, and recovery diagnostics.
- Generated completion and Markdown reference output.

Golden updates require review of semantic changes; they are not refreshed automatically merely to make a test pass.

### Filesystem Integration

- Apply into an empty target.
- Existing file/directory backup and replacement.
- Correct, wrong, and broken link behavior.
- Copy drift detection.
- Idempotent second apply.
- Interruption at each journal boundary.
- Reverse-order rollback.
- Recovery from incomplete rollback.
- Undo with and without post-apply drift.
- Repository relocation and removed source.
- Permission errors and cross-volume limitations.

### Adapter Contract

Every platform adapter runs a shared normalized behavior suite with platform-specific fixtures. Capability absence is a valid explicit result; silently changing strategy is not.

### Bootstrap

Use disposable environments to cover first install, identical reinstall, managed upgrade, unrelated existing executable, clean and dirty repository, network failure, checksum mismatch, unavailable private source, and paths with spaces.

### Security and Path Safety

- `..` traversal after variable expansion.
- Empty or unresolved destination.
- Filesystem root and broad home-directory targets.
- Symlink traversal out of an allowed root.
- Leading-dash paths.
- Unicode and normalization-sensitive names.
- Windows UNC, device, and reserved-name cases.
- Secret redaction in success and failure output.

## Package Testing

Do not invoke a real package manager in ordinary automated tests. Place fixture executables in the test `bin/` and verify normalized arguments, stdin behavior, output capture, preexisting-package classification, and failure journaling.

Real package-manager integration belongs in disposable images or machines with explicit scope.

## Performance

The [accepted Phase 1 adoption decision](decisions/0002-phase-1-go-adoption.md#performance-budgets-and-regression-policy) sets concrete warm targets and a regression-review policy using the existing method. Numeric checks remain advisory pending representative desktop evidence and a separately approved enforcement policy; the core runner records measurements without enforcing numeric thresholds.

Establish baselines before hard budgets.

Measure at least:

- `dots --version` and `dots --help` cold and warm startup.
- Direct built-in dispatch.
- Direct external command dispatch.
- Full command discovery with small and large registries.
- Specification resolution with representative dependency graphs.
- Plan generation for tens, hundreds, and thousands of files.
- Status with correct links versus copies requiring hashes.
- Generated shell initialization cost.

Record platform, architecture, build mode, repository size, operation count, sample count, and statistical summary. Retain results in a machine-readable benchmark artifact once CI exists.

## Proposed Runner Shape

No runner below exists yet. Candidate future entry points are:

```text
test/unit
test/integration
test/cli
test/bootstrap
test/all
```

The final names should match the implementation language's standard tooling and avoid wrappers that add no value. Update this document before presenting any runner as usable.

## Documentation Verification

Documentation changes currently require:

- `git diff --check`.
- Relative Markdown link validation.
- Search for stale proposed/implemented status labels.
- Search for renamed commands and paths.
- Confirmation that README examples only show implemented safe behavior.

Once command metadata generation exists, CI should regenerate output and fail on a dirty diff.

## Platform Evidence

For manual checks that CI cannot reproduce, record:

- Date.
- Platform and version.
- Architecture.
- Filesystem location/type.
- CLI revision and build mode.
- Command or test case.
- Result and observed limitation.

Do not upgrade a support-matrix status based on an undocumented one-off success.
