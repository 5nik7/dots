# Phase 2: Permanent Core and Built-in Registry

**Status: Authorized first slice in progress; broader command center deferred**

## Scope

Implement the [accepted first slice](../docs/decisions/0002-phase-1-go-adoption.md#next-bounded-implementation-task) from merged `origin/main` (`ca99056`) in a separate worktree on `feat/phase-2-core-registry`. Preserve the original checkout and its unrelated logo edit, the independent experiment, `bin/dots`, all live sources, and submodules.

Add a standard-library root Go module, `cmd/dots`, private CLI/platform packages, and a validated in-memory built-in registry. Expose only help, `--version`, and read-only `doctor`/`doctor --json`. Keep exit codes 0/1/2, diagnostic schema 1, optional-logo safety, unprobed capabilities, and explicit Windows path limitations. External execution, completion/discovery commands, manifests, transactions, bootstrap, installation, and releases are excluded.

## Implementation Contract

- `internal/dispatch` owns typed metadata, validation, global spellings distinct from token routes, collision refusal, in-memory route lookup, availability results, and defensive metadata projections. Handler-owned argument parsing preserves existing command acceptance. Synthetic overlapping routes test deeper built-in selection and untouched remaining arguments; no filesystem search or external resolver is added.
- `internal/cli` binds only the approved handlers and renders help from registry metadata. `internal/platform` ports read-only observations and safe opening. No filesystem mutation API is copied from experimental tests.
- `tests/cli_test.go` uses an explicitly supplied prebuilt binary and test-owned environment/roots. Formatting, vet, unit/process checks, source fingerprints, dependency inspection, and relocated rebuilds run through `tools/verify_core.py` with offline/telemetry isolation.
- The core runner copies an explicit allowlist into temporary roots and retains sanitized artifacts outside the checkout. `build`, `check`, and `bench` are planned runner modes, not new CLI routes. Benchmarks use the existing 3-batch/20-warmup/200-sample method and separate registry microbenchmarks; timing thresholds remain advisory under decision 0002.
- CI retains experiment checks, adds sequential native core checks/startup/registry evidence, and covers this feature branch, `main`, and PRs targeting `main`. CI-only prerequisite provisioning does not authorize Termux package changes.

## Acceptance

- [x] Permanent module, approved CLI surface, registry and platform boundary.
- [x] Collision/metadata/projection/availability/argument tests and isolated process checks.
- [x] Native Termux verification and fresh startup/registry measurements.
- [ ] Native Linux/Windows CI checks and fresh measurements, with final-head inspection.
- [ ] Documentation, evidence retention, whitespace, and original-checkout preservation checks.

## Remaining Boundaries

Known folders and real restricted Windows ACL policy, broader filesystems, WSL/other architectures, production OS floors, controlled cold-cache/representative desktop results, and release trust implementation remain gated as classified in decision 0002. The next external-command slice requires a separately settled trusted search/metadata protocol.

## Native Termux Results

The first implementation passed `python3 -B tools/verify_core.py check` and then `python3 -B tools/verify_core.py bench` on 2026-09-10, with exact uncommitted source snapshots retained. Both produced the same 4,078,181-byte binary, SHA-256 `b8ea7794395b7fce10403704ecac036fb5b8ecb0cf01c9867cfba8545d4e3c40`. Formatting, vet, Python isolation/optimization regressions, Go unit/process tests, dispatch dependency guard, optional-logo cases, unchanged-root snapshots, dependency inspection and identical relocated rebuild passed. There is no managed mutation or external execution surface.

| Command | Warm samples | Median | p95 | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `--help` | 600 | 7.183 ms | 11.923 ms | 5.654 ms | 34.706 ms |
| `--version` | 600 | 6.796 ms | 9.223 ms | 4.949 ms | 24.253 ms |

Both commands satisfy the accepted Termux advisory targets (12 ms median / 20 ms p95). These are fresh core measurements, not reuse of the spike or a causal speedup claim. Three registry repetitions measured 34.08–35.29 ns/op at 3 entries, 47.57–48.47 ns/op at 1,000 entries, and 50.50–56.01 ns/op at 10,000 entries, all with zero bytes/allocations per lookup. This measures synthetic in-process token lookup, not construction, external dispatch or filesystem discovery.

Evidence is retained privately under `$HOME/dots-review-evidence/phase-2-core-20260910-tzqn4c53/`: `termux-tested-source/`, source fingerprints, check/bench artifacts and sanitized logs, and `termux-environment.json`. An initial earlier check is retained separately; its tooling provenance is not relabeled as the final runner. Raw batches and first-observed Python timings preserve the existing measurement method; no controlled cold-start claim is made. Final desktop CI results will be recorded after native execution. A subsequent CI-collector-only change includes sanitized raw benchmark batches in job logs as well as artifacts; the local Go sources and verifier are unchanged, so the Termux execution and timing evidence retain their original provenance.
