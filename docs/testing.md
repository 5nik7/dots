# Testing Strategy

**Status: Focused Termux experiment runner implemented; broader strategy proposed**

Testing must prove that `dots` protects user data, resolves specifications deterministically, behaves consistently across adapters, and remains fast on representative machines.

## Implemented Portability Runner

From the repository root on native Termux Android/ARM64:

```bash
python3 experiments/go-portability/tools/verify.py build
python3 experiments/go-portability/tools/verify.py check
python3 experiments/go-portability/tools/verify.py bench
python3 experiments/go-portability/tools/verify.py cross
python3 experiments/go-portability/tools/verify.py docs
git diff --check
```

`build` uses installed Go 1.27.x and Python 3. `check` additionally needs `gofmt` and `readelf`; `bench` needs `hyperfine`. `cross` uses only the same Go/Python tools. Missing tools are named explicitly and never installed. The harness currently refuses non-Android/ARM64 Go hosts; native runners for other platforms remain deferred. `docs` is a read-only relative Markdown link check and does not require Go.

Each non-documentation invocation owns a fresh temporary work directory, copies only the experiment's Go sources and the public logo, and supplies isolated home/config/data/state/cache/temp/bin/repository roots. Go configuration is ignored with `GOENV=off` and `GOWORK=off`; automatic toolchain/module downloads are disabled with `GOTOOLCHAIN=local`, `GOPROXY=off`, and `GOSUMDB=off`. Go caches, GOPATH, and compiler scratch files are redirected into the owned root. Go disables telemetry on the Android host. Tests do not source shell configuration or call package managers. No `go install`, `go env -w`, dependency fetch, or submodule operation is used.

At completion the harness retains only artifacts in a new temporary `dots-spike-artifact-*` directory: `bin/`, the public `logo.txt` copy, and `evidence.json`. It prints the native executable path on stdout and progress/evidence location on stderr. Build work, caches, and fixtures are automatically cleaned through their owning temporary-directory context. The module's `.gitignore` also excludes accidental local binaries/test executables and Python bytecode. The harness does not create bytecode. Do not add retained temporary evidence or binaries to Git; record reviewed summaries in the focused plan.

`check` runs `gofmt -l`, `go vet ./...`, and uncached `go test -count=1 -v ./...` in the copied module. Tests cover argument/stream contracts, help/version fast paths, metadata collisions, JSON schema, platform detection/false positives, path defaults, and warning behavior. Go filesystem tests use `testing.T.TempDir` and `os.Root` to test file/directory links, explicit exclusive copies, spaces, Unicode, leading dashes, existing objects, broken links, missing parents, and traversal/symlink escape refusal. Escape sentinels are also test-owned. These primitives are not production apply or rollback operations.

The harness executes the prebuilt CLI with an empty `PATH` and controlled environment, tests optional logo failures (including a FIFO), checks dynamic logo reload and executable-symlink fallback, and compares fixture snapshots before and after read-only requests. Snapshots cover contents, object types, sizes, and modification times, not access times or system-wide syscall tracing. It also compares a rebuild from a relocated source path byte-for-byte and records ELF interpreter/library metadata.

`bench` builds once, then runs the compiled executable directly with the public logo and an empty `PATH`. It records a Python-timed first observed invocation for each command, followed by three hyperfine batches per command, 20 warmups and 200 measured executions per batch, with alternating command order, no shell, and stdout discarded. The 600 samples per command yield pooled median, nearest-rank p95, minimum, and maximum. Raw batches and build/environment metadata are retained in `evidence.json`. First-observed timings include the Python parent's spawn/wait overhead and have uncontrolled filesystem cache state. Warm hyperfine timings measure complete process execution. Neither establishes true cold-cache startup or a shell-startup budget; no cache flush, reboot, or power/thermal control is performed.

`cross` builds Linux/AMD64 and Windows/AMD64 executables and compiles each test package with `go test -c`; it does not run foreign artifacts. Fixture success on Termux is not native Windows/WSL evidence. No race-detector, desktop runtime, transaction, or bootstrap suite is claimed. Results and limitations are recorded in the [focused plan](../plans/phase-1-portability.md).

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
