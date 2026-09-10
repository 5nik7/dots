# Phase 2: Permanent Core and Command Dispatch

**Status: Built-in and bounded external slices implemented and verified natively; broader command center deferred**

## First Slice Scope (Completed)

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

Known folders and real restricted Windows ACL policy, broader filesystems, WSL/other architectures, production OS floors, controlled cold-cache/representative desktop results, and release trust implementation remain gated as classified in decision 0002. That protocol is now accepted in decision 0003; its implementation and new evidence are tracked below.

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

## Boundary After the First Slice

This slice leaves the active prototype, historical experiment and all live sources in place. The first slice required a separate trusted search/metadata decision before adding an external resolver. Decision 0003 now settles that boundary; see the authorized slice below. Known folders and restricted Windows permissions stay gated before affected installation behavior; WSL, broader filesystems, other architectures, production OS floors, remaining performance evidence and release trust retain decision 0002's classifications.


## Authorized External-Command Slice

Status: Implemented after owner approval of [decision 0003](../docs/decisions/0003-trusted-external-command-protocol.md).

Start from PR #2 merge `1de01687` in the separate `feat/phase-2-external-dispatch` worktree. Preserve both older worktrees and the recovery ref. Transfer only the owner-authorized exact whitespace-cleaned logo into a separate commit; retain its new hash without modifying historical evidence.

Implementation order: pure candidate/metadata contracts; explicit root and targeted lookup; static discovery/help; native process adapters; isolated fixture/process/console tests; verifier/CI and benchmarks; documentation and final native evidence. Keep `internal/dispatch` free of filesystem/process dependencies. Add no real external management commands.

- [x] Verify base/worktrees and commit the exact authorized logo cleanup separately.
- [x] Record accepted protocol, exact limits, reservations and trust boundary before implementation.
- [x] Implement strict metadata, explicit roots, targeted routing and static discovery/help.
- [x] Implement native Unix/Windows execution adapters and required interruption regressions.
- [x] Pass native Termux/Linux/Windows core verification and retained experiment checks.
- [x] Measure help/version, external execution and discovery independently; verify cleaned logo.
- [x] Synchronize documentation and retain sanitized evidence. Final-head CI/PR outcome is retained with the delivery evidence; PR creation may require the owner because the integration returned HTTP 403.

No bootstrap, installation, packages, dotfile mutation, transactions, completion, releases or merge belongs in this task. Windows console tests are required; unavailable cases remain explicit blockers for the affected interruption claim.

## External Slice Results

The source at `25ca5f7725dfbde2b100c50129398904d620e94d` passed native Termux verification and [Linux/Windows run 34436215758](https://github.com/5nik7/dots/actions/runs/34436215758). Each host recorded 28 top-level Go test outcomes, plus six Python regressions. No Go cases were skipped on these hosts. Windows passed real console Ctrl+C and Ctrl+Break broadcast/wait tests, ASCII case lookup, root alias identity, symlink refusal, fixed-drive NTFS root validation, quoting/empty-argument/metacharacter forwarding, and propagation of native status `0xC000013A`. Unix passed same-PID replacement, SIGINT/SIGTERM, execute-bit and FIFO refusal checks. The original follow-up added a timeout that killed only the Windows wrapper. PR #3 review found that a fixture child could survive and retain inherited pipes; that timeout did not establish child cleanup. The corrective test-infrastructure work is tracked below and does not change the CLI binary. Final-head CI must recheck that test and is retained separately without relabeling these measurements.

Strict sidecar parsing initially rejected valid metadata due to an incorrect required-field count; it now checks the exact eleven required keys and positive/negative fixtures. Review also replaced Unicode filename lowercasing with ASCII-only folding on Windows, preventing a non-ASCII name from becoming a valid route during discovery. Deterministic tests verify direct lookup never enumerates directories and keeps the same targeted work with 1,000 unrelated entries. Both initial and final source/log evidence are retained.

The separate logo commit `47e3129` contains the owner's exact original edited bytes: SHA-256 `400a1229f5ef3bd7d60d529ef498d25d2ac77f8cbc8da129abd90953c0b654d9`. Native core checks verify those bytes appear in help with the normal separating newline. Historical logos, experiment/adoption records, and evidence retain their original hashes.

| Native environment | Help median / p95 | Version median / p95 | External no-op median / p95 | Discovery (10) median / p95 |
| --- | ---: | ---: | ---: | ---: |
| Termux Android/ARM64 | 8.810 / 16.308 ms | 8.143 / 10.146 ms | 16.233 / 22.200 ms | 10.002 / 19.738 ms |
| Ubuntu 24.04.4 / AMD64 CI | 0.935 / 1.046 ms | 0.898 / 1.004 ms | 1.846 / 1.987 ms | 1.492 / 1.617 ms |
| Windows build 26100 / AMD64 CI | 6.092 / 6.937 ms | 5.976 / 6.784 ms | 13.176 / 17.244 ms | 8.458 / 10.183 ms |

Each cell uses 600 warm complete-process samples: three alternating batches, twenty warmups and two hundred samples per command per batch, no shell, empty PATH, discarded stdout. External execution uses a native no-op fixture; discovery uses one root with ten definitions. These establish separate baselines, not external-command latency budgets. All help/version absolute targets remain satisfied. Registry lookup at 3/1,000/10,000 entries recorded zero allocations; ranges were Termux 26.02–31.28 / 37.13–46.41 / 42.11–48.56 ns/op, Linux 19.77–20.20 / 20.88–20.92 / 21.67–22.09, and Windows 19.23–20.36 / 21.04–21.11 / 21.84–22.37. This is synthetic in-process lookup, not discovery.

The initial Termux help increase over the retained first-core measurement triggered decision 0002's investigation rule. A serial paired run reused the verified first-core and candidate binaries with the same cleaned logo, host, environment and full 600-sample method. Baseline/candidate help median was 8.487/8.480 ms and p95 12.055/13.057 ms; version median 8.310/8.617 and p95 16.045/15.716 ms. Neither increase exceeded both 20% and 0.5 ms; the paired run did not confirm the concern, so the policy did not call for a second pair or exception. Original and paired samples remain separate. No controlled cold-cache, installed-startup or representative physical desktop claim is made.

Evidence is under `$HOME/dots-review-evidence/phase-2-external-giv_olc9/`: exact tested sources, native artifacts and source/binary/logo hashes, raw check/bench logs, paired measurement script/samples, and CI metadata/review summaries. All 37 CI input hashes were checked against `25ca5f7`; pooled summaries were recomputed from raw samples. Linux/Windows check and bench binaries matched within each host. Local desktop review uses sanitized CI job logs, not downloaded ZIP verification or execution on Termux. Linux image was `ubuntu24/20260831.293.1`, four EPYC 9V74 CPUs, kernel `6.17.0-1022-azure`, filesystem label `ext2/ext3`; Windows was `win25-vs2026/20260824.214.3`, four logical CPUs and NTFS. Both native jobs retained the independent experiment check/distribution steps.

Remaining limitations are explicit: WSL execution, other architectures, broader/network/cross-volume filesystems, Windows case-sensitive directory use, known folders and actual restricted ACL policy, physical desktop/controlled cold-cache performance, installation and release trust. Code validation does not authenticate publishers, enforce read-only behavior, prevent concurrent trusted-file replacement or clean up arbitrary descendants. No actual management extension, completion, public discovery JSON, manifest, transaction, package change, bootstrap, installation or release was added. The next slice needs separate scope; this branch must not be merged by the agent.

## PR #3 Review Corrections

Implementation: replace the inadequate wrapper-only timeout with test-owned Windows job containment established before helper launch proceeds, bounded fixture lifetimes, supervisor job deadlines, bounded output-copy waits and process reaping. Add native stalled-readiness and stalled-interruption regressions that fail within six seconds and verify the fixture process handle is signaled after cleanup; preserve successful native Ctrl+C/Ctrl+Break acceptance and the product contract. Verify the fixture watchdog independently on all native test hosts.

Remove the new `zip(strict=True)` Python-version dependency using explicit result-count validation before ordinary pairing; test missing and extra results as well as the exact case. Historical measurements retain their original source/fixture identities. Fresh verification evidence belongs under `$HOME/dots-review-evidence/pr3-cleanup-1e51tbd7/`; CI will remeasure using the changed disposable fixture, without changing the production executable or resetting historical baselines.

The first Windows review run rejected `SetReadDeadline` on the runner pipe handles before fixture startup. The revised supervisor cancels the entire test job at its deadline and retains `WaitDelay` for inherited output-copy pipes. Acceptance remains unchanged: native success cases plus deadline failures at both stalled phases and a signaled fixture process handle after cleanup.

The revised isolated Termux check passed 29 top-level Go test outcomes with no skips and seven Python regressions. The core binary SHA-256 remains `af5ffcb6f786a84d1b60ce4c87dd01484a60eecf32f18bc31a4d455b9177d6ff`, identical to the retained pre-review core. Native Windows success/negative acceptance and final push/PR workflow results must be inspected and retained separately before delivery.

## Authorized Command Catalog Slice

Status: Implemented and verified natively under [decision 0004](../docs/decisions/0004-versioned-command-discovery.md).

Start from PR #3 merge `4286c6f` in a separate `feat/phase-2-command-catalog` worktree. Preserve older worktrees/indexes, original logo edit, recovery ref, live prototype and historical evidence. Implement CLI-owned schema-1 catalog types over shared projections and ordinary discovery, with explicit mode selection, typed availability reasons, deterministic ordering, complete validation before output and no execution. Update metadata, user/reference/agent documentation and the native CI branch trigger. No execution/routing adapter changes, completion, configuration, installation or mutations.

- [x] Implement catalog projection, mode and schema/status/nonexecution acceptance.
- [x] Run isolated native Termux check and separate JSON-discovery warm measurements.
- [x] Inspect implementation Linux/Windows CI including retained experiment and console-cleanup regressions; retain final-head revalidation separately at delivery.
- [x] Synchronize documentation, retain sanitized evidence and verify unrelated-work preservation.

### Catalog Termux Results

The isolated `python3 -B tools/verify_core.py check` passed 35 top-level Go tests (including catalog schema/process/error/limit cases), with no skips, and seven Python regressions. Formatting, vet, dependency guard/inspection, unchanged-root checks, logo bytes and identical relocated rebuild passed. The JSON slice leaves native execution and pure routing sources unchanged. Documentation links and `git diff --check` passed separately after documentation synchronization.

Fresh `bench` evidence uses the approved 600 warm samples per series. Termux median / p95: help 8.024 / 11.048 ms; version 8.160 / 11.747 ms; external dispatch 17.445 / 45.208 ms; text discovery (10) 12.307 / 48.068 ms; JSON discovery (10) 17.587 / 62.817 ms. Help/version meet their 12 / 20 ms advisory targets. The discovery/external batches show substantial timing variability; these are observed baselines, not controlled causal comparisons or new latency budgets. No controlled cold-start result is claimed. Registry lookups remain zero-allocation.

Evidence: `$HOME/dots-review-evidence/phase-2-catalog-3aq372sx/`, including separate native check/bench artifacts, logs and exact source snapshots. Check/bench binary SHA-256 is `3bb2ea7fa8c87b897997fffc845d8a77da7f089589194271e9fc04860df43ebb`; raw sample counts and summaries were recomputed. Source fingerprints identify this local implementation before commit; final-commit desktop results must be inspected separately. Historical evidence and original logo/index identities are preserved.

### Catalog Native Desktop Results

[Run 34441014484](https://github.com/5nik7/dots/actions/runs/34441014484) passed both native jobs at `24102a4cbbb243d5166a4506bce237a7e75e5b88`. Linux passed 35 top-level Go tests and Windows 36, with no skipped cases; each passed seven Python regressions. Windows passed real Ctrl+C/Ctrl+Break acceptance and both stalled-readiness/stalled-interruption cleanup cases. Independent experiment check/distribution and core formatting/vet/dependency/source/relocation checks passed on both hosts.

| Native CI host | Help median / p95 | Version median / p95 | External median / p95 | Text discovery (10) median / p95 | JSON discovery (10) median / p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ubuntu 24.04.5 / AMD64 | 1.149 / 1.313 ms | 1.123 / 1.286 ms | 2.314 / 2.488 ms | 1.907 / 2.114 ms | 2.014 / 2.253 ms |
| Windows build 26100 / AMD64 | 7.700 / 8.697 ms | 7.393 / 8.444 ms | 16.699 / 19.092 ms | 10.312 / 12.187 ms | 10.319 / 12.039 ms |

All series contain 600 warm samples and help/version meet accepted absolute targets. Hosted results are advisory; Windows used an AMD runner/image different from the retained PR #3 Intel run, so cross-run discovery differences are not a controlled regression comparison. Registry lookup remained zero-allocation. JSON has a separate new baseline; no controlled cold-cache or physical-desktop claim is made.

Reviewed evidence in the catalog directory includes sanitized native job logs, extracted check/bench metadata, runner details and review summaries. All 40 input hashes were verified against the tested commit; check/bench binary identities match within each host; all timing summaries were recomputed from raw samples. Desktop review uses CI logs, not locally downloaded archive verification or desktop execution on Termux. Final documentation-only commit CI is retained separately at delivery rather than relabeling these measurements.

PR creation returned HTTP 403 from the GitHub integration and local `gh` authentication was invalid. The authorized fallback is the [comparison](https://github.com/5nik7/dots/compare/main...feat/phase-2-command-catalog); a prepared PR description is retained beside the evidence. No merge is authorized. Existing worktrees' HEAD/status/logo/index identities and remote main/recovery refs were rechecked unchanged. Remaining limitations include WSL execution, other architectures, restricted Windows ACLs/known folders, broader filesystems, production OS floors, release trust and representative performance evidence; completions/configuration/installation/mutations remain outside this slice.

## Authorized Zsh Completion Slice

Status: In progress under owner approval of [decision 0005](../docs/decisions/0005-static-zsh-completion.md).

Start from verified main `2ae087926305e6dee742b61ffb488f774a833c74` in the explicitly enrolled `feat/phase-2-zsh-completion` worktree after eligible lifecycle cleanup. Preserve the original checkout, all branch/recovery refs, live configuration and historical evidence.

- [x] Shared in-memory catalog and stdout-only Zsh generator, registry/help and error contracts.
- [x] Literal ordered root context, bounded static candidates, safe quoting and argument boundaries.
- [ ] Real isolated Termux/Linux Zsh acceptance; native Windows generation/CLI checks without Zsh claims.
- [ ] Existing native core/experiment gates, startup measurements, disposable demonstration and retained evidence.
- [ ] Documentation, final-commit CI review, explicit branch push and PR or comparison fallback.

No installation, live shell startup edits, Bash/Fish/PowerShell renderers, argument-schema expansion, package installation on Termux or merge. Retain this worktree while the implementation session uses it.

### Zsh Termux Results

The isolated core check passed 40 top-level Go tests with no skips and seven Python regressions on Termux Android/ARM64 using zsh 5.9.2 (aarch64-unknown-linux-android). Candidate tests execute the generated function in real Zsh with an empty PATH, and the native pseudo-terminal test initializes compinit without a dump file and exercises normal completion registration with the real compadd builtin. Shared schema/projection, full discovery-failure/availability, native external interruption, unchanged-root, dependency and identical relocated-build checks passed.

| Warm series | Median / p95 (ms) |
| --- | --- |
| --help | 8.590 / 10.284 |
| --version | 8.336 / 10.000 |
| external-dispatch | 16.200 / 19.214 |
| discovery-10 | 10.696 / 13.133 |
| discovery-json-10 | 10.823 / 12.348 |

Each series retains 600 samples under the existing three-batch method. Help/version meet the accepted Termux advisory budgets. These are fresh observations, not controlled causal speedups or cold-cache results. Check/bench binaries match at SHA-256 `3ff0f733c2e0d0fb89e094004e141d8d27217395aaa1cc7e00a9a7df000bb333`. Generation and interactive latency have no new numeric budget; runtime nonexecution and embedded-only candidate evaluation are structural guarantees.

Evidence is retained under `$HOME/dots-review-evidence/phase-2-zsh-iwmrh6tl/`: exact tested inputs, native check/bench artifacts, sanitized logs and a disposable demonstration using the retained development binary. No live PATH/startup or prototype file changed. Desktop and final-commit CI results are recorded separately after inspection.
