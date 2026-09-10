# Phase 2: Permanent Core and Built-in Registry

**Status: First slice implemented and verified natively; broader command center deferred**

## Scope

Implement the [accepted first slice](../docs/decisions/0002-phase-1-go-adoption.md#next-bounded-implementation-task) from merged `origin/main` (`ca99056`) in a separate worktree on `feat/phase-2-core-registry`. Preserve the original checkout and its unrelated logo edit, the independent experiment, `bin/dots`, all live sources, and submodules.

Add a standard-library root Go module, `cmd/dots`, private CLI/platform packages, and a validated in-memory built-in registry. Expose only help, `--version`, and read-only `doctor`/`doctor --json`. Keep exit codes 0/1/2, diagnostic schema 1, optional-logo safety, unprobed capabilities, and explicit Windows path limitations. External execution, completion/discovery commands, manifests, transactions, bootstrap, installation, and releases are excluded.

## Implementation Contract

- `internal/dispatch` owns typed metadata, validation, global spellings distinct from token routes, collision refusal, in-memory route lookup, availability results, and defensive metadata projections. Handler-owned argument parsing preserves existing command acceptance. Synthetic overlapping routes test deeper built-in selection and untouched remaining arguments; no filesystem search or external resolver is added.
- `internal/cli` binds only the approved handlers and renders help from registry metadata. `internal/platform` ports read-only observations and safe opening. No filesystem mutation API is copied from experimental tests.
- `tests/cli_test.go` uses an explicitly supplied prebuilt binary and test-owned environment/roots. Formatting, vet, unit/process checks, source fingerprints, dependency inspection, and relocated rebuilds run through `tools/verify_core.py` with offline/telemetry isolation.
- The core runner copies an explicit allowlist into temporary roots and retains sanitized artifacts outside the checkout. `build`, `check`, and `bench` are implemented runner modes, not CLI routes. Benchmarks use the existing 3-batch/20-warmup/200-sample method and separate registry microbenchmarks; timing thresholds remain advisory under decision 0002.
- CI retains experiment checks, adds sequential native core checks/startup/registry evidence, and covers this feature branch, `main`, and PRs targeting `main`. CI-only prerequisite provisioning does not authorize Termux package changes.

## Acceptance

- [x] Permanent module, approved CLI surface, registry and platform boundary.
- [x] Collision/metadata/projection/availability/argument tests and isolated process checks.
- [x] Native Termux verification and fresh startup/registry measurements.
- [x] Native Linux/Windows CI checks and fresh measurements; final pushed-commit status is retained with the review evidence.
- [x] Documentation, evidence retention, whitespace, and original-checkout preservation checks.

## Remaining Boundaries

Known folders and real restricted Windows ACL policy, broader filesystems, WSL/other architectures, production OS floors, controlled cold-cache/representative desktop results, and release trust implementation remain gated as classified in decision 0002. The next external-command slice requires a separately settled trusted search/metadata protocol.

## Native Termux Results

The first implementation passed `python3 -B tools/verify_core.py check` and then `python3 -B tools/verify_core.py bench` on 2026-09-10, with exact uncommitted source snapshots retained. Both produced the same 4,078,181-byte binary, SHA-256 `b8ea7794395b7fce10403704ecac036fb5b8ecb0cf01c9867cfba8545d4e3c40`. Formatting, vet, Python isolation/optimization regressions, Go unit/process tests, dispatch dependency guard, optional-logo cases, unchanged-root snapshots, dependency inspection and identical relocated rebuild passed. There is no managed mutation or external execution surface.

| Command | Warm samples | Median | p95 | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `--help` | 600 | 7.183 ms | 11.923 ms | 5.654 ms | 34.706 ms |
| `--version` | 600 | 6.796 ms | 9.223 ms | 4.949 ms | 24.253 ms |

Both commands satisfy the accepted Termux advisory targets (12 ms median / 20 ms p95). These are fresh core measurements, not reuse of the spike or a causal speedup claim. Three registry repetitions measured 34.08–35.29 ns/op at 3 entries, 47.57–48.47 ns/op at 1,000 entries, and 50.50–56.01 ns/op at 10,000 entries, all with zero bytes/allocations per lookup. This measures synthetic in-process token lookup, not construction, external dispatch or filesystem discovery.

Evidence is retained privately under `$HOME/dots-review-evidence/phase-2-core-20260910-tzqn4c53/`: `termux-tested-source/`, source fingerprints, check/bench artifacts and sanitized logs, and `termux-environment.json`. An initial earlier check is retained separately; its tooling provenance is not relabeled as the final runner. Raw batches and first-observed Python timings preserve the existing measurement method; no controlled cold-start claim is made. A subsequent CI-collector-only change includes sanitized raw benchmark batches in job logs as well as artifacts; the local Go sources and verifier are unchanged, so the Termux execution and timing evidence retain their original provenance.


## Native Desktop Results and Resolved Finding

[Run 34428376943](https://github.com/5nik7/dots/actions/runs/34428376943) passed both native jobs at `60e591cd2504f1ac8d2dc01114a1eb2b13f03565` on 2026-09-10. Each job retained the independent experiment check/distribution tests and then ran the permanent-core check/bench collector. The root core passed 14 top-level Go tests on Linux and 13 on Windows (Unix FIFO replacement is excluded there), plus six Python regressions per host. Formatting, vet, empty-PATH process contracts, metadata/dispatch tests, snapshots, source identity, dependencies and identical relocated rebuild passed. Windows file/directory symlinks were available in owned fixtures; ACL-denied logos remain explicitly untested.

The first Windows run exposed stale directory modification times in the process test's enumeration-based snapshot. Detailed diagnostics showed unchanged file hashes, sizes, modes and membership. Reading directory metadata from opened handles resolved the failure without dropping modification-time checks. A new fixture regression proves stable snapshots before any CLI invocation and detects same-size content changes and removals. All CLI process roots now include a path component with spaces, Unicode and a leading dash. The updated check also passed natively on Termux with 14 top-level Go tests; its binary matches the Termux startup measurement above, so those measurements retain their original provenance and are not rerun merely for test changes.

| Native environment | Help median / p95 | Version median / p95 | Binary size |
| --- | ---: | ---: | ---: |
| Ubuntu 24.04.5 LTS / AMD64 CI | 1.045 / 1.320 ms | 0.971 / 1.255 ms | 4,026,481 bytes |
| Windows build 26100 / AMD64 CI | 7.283 / 8.059 ms | 7.070 / 7.912 ms | 4,240,384 bytes |

Each command has 600 warm samples using the same method as Termux. Both hosts meet their accepted advisory budgets: Linux 2 ms median / 4 ms p95 and Windows 10 / 15 ms. These are hosted-runner observations; neither controlled cold-cache nor representative physical desktop measurements are claimed. Registry lookup ranges across three repetitions were Linux 22.15–22.71, 17.80–18.32 and 18.24–20.86 ns/op at 3/1,000/10,000 entries respectively; Windows measured 26.53–26.71, 29.83–30.91 and 30.51–31.51 ns/op. All recorded zero bytes and allocations per lookup. Variation between table sizes is not evidence of a causal speedup.

Linux used image `ubuntu24` / `20260907.300.1`, kernel `6.17.0-1022-azure`, four available CPUs (Xeon Platinum 8573C), and the `ext2/ext3` filesystem magic label. Windows used image `win25-vs2026` / `20260824.214.3`, four logical CPUs (EPYC 7763), and NTFS; affinity was not measured. Both used Go 1.27.1 with CGO disabled. Linux SHA-256 is `8553d43c023a1e25b4ff4f977e22407a9c88692e29193180c2916626b6df3d77`; Windows is `bcd487359bdb64eae0125a07e87b14ded8f1f7e053c91de57b045b47af500f4c`. Check and benchmark identities match within each host.

The private evidence directory above contains `ci-60e591c-{linux,windows}.log`, extracted check/bench/runner metadata, raw timing batches, registry repetitions, source snapshots and `*-review.json`. Review verified all 17 source fingerprints against the tested commit and recomputed summaries from the raw 600 samples. CI retains the complete native artifacts for 30 days. Local review used sanitized job-log metadata because artifact-download transport was unavailable; it does not claim locally downloaded ZIP hash verification or desktop binary execution on Termux. `termux-final-check/` and `termux-final-source/` retain the final test revision and byte-identical native rebuild. Subsequent documentation-only CI results are retained separately rather than relabeling these measured commits.

## Next Boundary

This slice leaves the active prototype, historical experiment and all live sources in place. The next implementation task must first settle the trusted external-command search and metadata protocol, including directories, precedence, suffix/interpreter rules and validation, before adding an external resolver. Known folders and restricted Windows permissions stay gated before affected installation behavior; WSL, broader filesystems, other architectures, production OS floors, remaining performance evidence and release trust retain decision 0002's classifications.


## Authorized External-Command Slice

Status: In progress after owner approval of [decision 0003](../docs/decisions/0003-trusted-external-command-protocol.md).

Start from PR #2 merge `1de01687` in the separate `feat/phase-2-external-dispatch` worktree. Preserve both older worktrees and the recovery ref. Transfer only the owner-authorized exact whitespace-cleaned logo into a separate commit; retain its new hash without modifying historical evidence.

Implementation order: pure candidate/metadata contracts; explicit root and targeted lookup; static discovery/help; native process adapters; isolated fixture/process/console tests; verifier/CI and benchmarks; documentation and final native evidence. Keep `internal/dispatch` free of filesystem/process dependencies. Add no real external management commands.

- [x] Verify base/worktrees and commit the exact authorized logo cleanup separately.
- [x] Record accepted protocol, exact limits, reservations and trust boundary before implementation.
- [x] Implement strict metadata, explicit roots, targeted routing and static discovery/help.
- [x] Implement native Unix/Windows execution adapters and required interruption regressions.
- [ ] Pass native Termux/Linux/Windows core verification and retained experiment checks.
- [ ] Measure help/version, external execution and discovery independently; verify cleaned logo.
- [ ] Synchronize documentation, retain sanitized evidence, inspect final-head CI and prepare PR.

No bootstrap, installation, packages, dotfile mutation, transactions, completion, releases or merge belongs in this task. Windows console tests are required; unavailable cases remain explicit blockers for the affected interruption claim.
