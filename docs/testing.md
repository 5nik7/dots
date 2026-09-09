# Testing Strategy

**Status: Proposed; test runner names are not yet implemented**

Testing must prove that `dots` protects user data, resolves specifications deterministically, behaves consistently across adapters, and remains fast on representative machines.

## Isolation Model

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

