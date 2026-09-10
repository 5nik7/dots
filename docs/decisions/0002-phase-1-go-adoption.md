# 0002: Adopt Go for the Core with Bounded Initial Coverage

Status: Accepted
Date: 2026-09-10
Review checkpoint: `dcfea900875656750c6c4b763c1f9119e4339b6a` on `feat/phase-1-portability`

## Owner Approval Record

On 2026-09-10, the owner explicitly approved all four decisions in this record as proposed at `c7d86a989e6397a3ecd74407e63097994f183694`. This accepts the language/toolchain and development targets, performance policy, packaging/release-trust direction, gap classifications, and next implementation boundary without changing their substance. Acceptance is a design decision, not an implementation or production-support claim. The approval-recording task permits documentation, scoped commits/pushes, and a pull request into `main`; Phase 2 implementation and merging are excluded from that task.

## Context

[0001](0001-go-portability-experiment.md) accepted an isolated experiment, not a production language. Native execution, filesystem fixtures, startup measurements, and bounded distribution checks are now available. This record accepts the adoption, support, performance, and release direction needed to close that decision. Recording acceptance does not begin Phase 2 or authorize installation. The live `bin/dots`, dotfiles, shell configuration, repository layout, and owner's unrelated `logo.txt` edit remain unchanged.

The historical experiment and [Phase 1 results](../../plans/phase-1-portability.md) remain the evidence source. This record owns the accepted choices and gap classification; the [platform support matrix](../platforms.md#support-matrix) continues to describe actual verified capabilities.

## Decision

### Language

Adopt Go for the permanent core. Keep platform operations behind adapters and begin with the standard library, `CGO_ENABLED=0`, and no runtime helper dependencies. Shell and PowerShell remain bootstrap/extension boundaries; they do not implement competing transaction engines.

The experiment demonstrates native Android/ARM64, Linux/AMD64, and Windows/AMD64 execution; read-only help/version/diagnostics; isolated filesystem primitives; same-toolchain identical relocated builds; and verified bundle extraction and execution independent of the source checkout and PATH. Termux warm startup is comfortably within the accepted targets below. Review findings in Python optimization handling, Unix logo replacement, offline Go configuration, and Windows existing-directory refusal were resolved and verified.

No demonstrated technical blocker requires rejecting Go or another portability experiment before the first read-only command-registration slice. The remaining Windows and filesystem gaps constrain affected functionality, not Go's suitability for a core that does not yet install or mutate managed files. Owner acceptance has satisfied the adoption gate; implementation remains a separate task. This is not approval of production platform support, manifests, transactions, or the full command protocol.

### Initial Targets and Toolchain

| Platform | Initial build/development target | Native evidence | Production support and OS floor |
| --- | --- | --- | --- |
| Termux | Primary target, Go `android/arm64`; identify bundles as `termux-arm64` | Termux 0.119.0-beta.3, Android API 35, app-private f2fs fixtures, Go 1.27.1 | First intended installation target. No production installation support yet. API 35 is tested, not a promised minimum Android API; older API/app versions and shared storage are unverified. |
| Linux | Continuous native development checks, Go `linux/amd64` | Ubuntu 24.04 CI, including 24.04.5 at the checkpoint; kernel 6.17.0-1022-azure, ext-family filesystem label | Development coverage for the experimental surface only. Ubuntu 24.04 and the observed kernel are test baselines, not minimum distribution/kernel promises. |
| Native Windows | Continuous native development checks, Go `windows/amd64` | `windows-2025`, build 26100, NTFS, native process execution | Development coverage only. Neither the runner label nor PE OS headers establish a Windows client/server minimum. Known folders and restricted policy remain open. |
| WSL | Deferred native coverage; future Linux artifact may be reusable only after validation | Detector fixtures only; no WSL execution | Separate platform, paths, capabilities, and state store. No support or cross-boundary path/link promise follows from Linux or Windows CI. |

Do not add other architectures to the initial acceptance matrix on cross-compilation alone. Keep the runtime/loader distinction explicit: Termux requires Android's `/system/bin/linker64` despite no ELF `DT_NEEDED` entries; the tested Linux binary has neither an ELF interpreter nor `DT_NEEDED` entries; Windows has a static `kernel32.dll` import, which is not a complete dynamic/transitive dependency inventory. None requires an installed Go runtime or Python to execute.

Use **Go 1.27.1 as both the initial supported development/test baseline and pinned build toolchain**. The experiment's `go 1.27.0` directive is a historical module minimum, not evidence that 1.27.0 was tested. Set the future root module directive to `go 1.27.1`; preserve the experimental module. Do not promise other toolchains until tested. This is an evidence-based starting pin, not a claim about the latest upstream version or security status. Reassess upstream support/security before public release and when updating the pin.

Retain `-trimpath -buildvcs=false -mod=readonly`, Android's default PIE, and no stripping changes for the first slice. Go configuration, telemetry, caches, and fixtures must retain the current harness isolation and offline settings. Python, Git, Go, readelf/LLVM, and hyperfine are development tools only. Preserve the recorded Python/tool versions in evidence rather than promising an untested Python minimum. A toolchain update requires all three native checks, dependency inspection, relocated rebuild comparison, relevant distribution checks, and fresh startup evidence before rebasing the build/performance baseline. Same-toolchain repeatability does not promise identical bytes across toolchains or compression implementations.

### Performance Budgets and Regression Policy

Adopt these initial **warm complete-process targets**, separately for each of `--help` and `--version`:

| Environment | Retained help median / p95 | Retained version median / p95 | Accepted median / p95 budget |
| --- | ---: | ---: | ---: |
| Recorded Termux device | 8.314 / 10.188 ms | 8.261 / 10.127 ms | 12 / 20 ms |
| Linux CI | 1.044 / 1.247 ms | 0.998 / 1.202 ms | 2 / 4 ms |
| Windows CI | 6.958 / 7.534 ms | 6.714 / 7.170 ms | 10 / 15 ms |

These allow headroom above observed process startup without accepting unbounded growth. They are engineering targets, not user latency guarantees or measurements of future dispatch/discovery/planning commands. Termux values retain the 2026-09-09 logo-fix provenance. Desktop values are from the later [run 34422396422](https://github.com/5nik7/dots/actions/runs/34422396422) at `0f538ff40deaf4f51b42b4439b6ae0c2f68899f4`, not the earlier implementation-run table in the plan. The distribution review confirmed identical executable hashes before reusing those measurements.

Use the [existing method](../testing.md#implemented-portability-runner): build once, prebuilt binary, empty PATH, optional public logo for help, stdout discarded, hyperfine `--shell=none`, three alternating-order batches, 20 warmups and 200 measured executions per command per batch. Pool 600 samples per command; report median and nearest-rank p95, min/max, raw batches, toolchain, source/binary hashes, logo hash, runner/device, filesystem, and timing configuration. Retain first-observed Python timings separately; they include parent spawn/wait overhead and uncontrolled cache state. There are **no controlled cold-start results**.

Accepted policy:

1. Enforce correctness, empty-PATH operation, read-only snapshots, test isolation, and source/artifact identity. Require new benchmark evidence for meaningful startup/dispatch changes; documentation-only changes may reuse evidence when executable identity and behavior match. Current CI runs `check` and `dist`, not timing thresholds.
2. Treat absolute timing budgets and hosted-CI timing comparisons as advisory initially. The existing testing guide requires representative desktop evidence before hard budgets; hosted CI is not that evidence. Do not fail CI on one noisy timing result or compare unrelated runner images as a causal regression.
3. Trigger investigation when either median or p95 exceeds its absolute budget, or increases over a comparable baseline by both more than 20% and more than 0.5 ms. Rerun baseline and candidate serially on the same host/toolchain/configuration using the full method; perform a second paired measurement only if the first confirms the concern. Do not run builds/tests concurrently with timings.
4. A regression confirmed in both paired measurements requires an explanation and owner-approved exception or a fix before acceptance. Preserve old and new evidence; never silently reset a baseline. This is a review gate, not an implemented numeric CI gate. An unavailable comparable host leaves an explicit unresolved performance review item, not a fabricated pass.
5. Before promoting numeric limits to hard enforcement, collect representative physical desktop warm baselines and repeatability evidence, then approve a dedicated-runner policy. Cold-cache work is separately deferred until a cold-start claim or requirement needs it. Measure extracted-path/fallback-logo startup before an installed-startup claim. Establish external dispatch and registry-size baselines when those paths exist; these help/version targets do not stand in for them.

### Packaging and Release Trust

Use versioned `dots-<version>-<platform>-<architecture>.tar.gz` for Termux/Linux and `.zip` for native Windows, using the tested minimal relative layout with the permanent executable name:

```text
bin/dots             # bin/dots.exe on native Windows
logo.txt             # committed public optional logo
bundle.json          # versioned schema, target, release version, source commit,
                     # toolchain/build identity, payload sizes and hashes
```

Archive contents have no wrapper directory; extract into a separately chosen fresh staging directory. Keep binaries and their parent logo together. Do not bundle dotfiles, private/optional submodules, caches, or toolchains. Any mandatory license/notice payload must be audited before publication and added explicitly to a versioned member allowlist. The permanent names/layout are accepted direction awaiting implementation; the exact release schema and any legal payload still need the release-design work below. They are not compatibility claims for experimental schema 1.

Retain an external SHA-256 manifest covering each archive. Verify bounded downloaded bytes against it **before parsing or extraction**, then validate the complete member set, target/schema/version identity, paths, duplicates, regular-file types, modes, expansion bounds, and payload hashes before any destination write. Use exclusive writes into a fresh owned destination; refuse existing destinations. Preserve Unix binary `0755` and data `0644`; validate Windows execution and access with native rules, not POSIX mode assumptions. Freeze explicit limits in the release verifier; the experiment's limits are a starting point documented in [testing.md](../testing.md#experimental-distribution-check).

A checksum proves agreement with a supplied digest. An attacker who replaces both the archive and manifest can satisfy it. Source fingerprints, CI artifact hashes, HTTPS transport, and successful extraction alone do not authenticate the publisher.

Require a **publisher-signed release manifest** binding version, target, archive name/size/hash, source revision, and build toolchain, verified against an explicitly trusted publisher identity before extraction or execution. Select the concrete signing mechanism, trust-root distribution, key custody/rotation/revocation, and verifier dependency strategy in a separate release-design task. No specific signing tool is adopted here. Authentication must fail closed for a wrong identity, invalid/missing signature, or mismatched target/version. Immutable version selection should be the default; a moving channel needs an explicit rollback/downgrade policy.

Before any public release: approve the exact supported OS floors and acceptance matrix; check toolchain support/security and licensing; implement and test the signed-manifest trust path and immutable artifact naming; retain source/build provenance and native verification results for the released bytes. Before remote bootstrap: establish the verifier's own trust entrypoint (an unverified downloaded verifier cannot establish trust), authenticated retrieval and redirect/failure policy, bounded staging safe against parent replacement, interrupted-download cleanup, and recoverable installation/update behavior under [safety.md](../safety.md). Test tampering with both archive and manifest, wrong publisher/target/version, unsafe members, interrupted extraction/installation, existing targets, and rollback in owned roots. No pipe-to-shell instructions, publication, signing setup, installer, or release automation is implemented by this decision.

### Remaining Gaps and Gates

The classification below is authoritative for this decision. A deferred platform must pass the relevant functionality gates before its status expands.

| Gap | Classification | Reason and required boundary |
| --- | --- | --- |
| Language, initial targets/toolchain, performance policy, and permanent-core scope approval | Required before Go adoption or Phase 2 | Satisfied by the owner approval recorded above. Native evidence reveals no unresolved technical adoption blocker. The permanent core is still unimplemented. |
| First registry contract and isolated root-core runner | Required before Go adoption or Phase 2 | The bounded built-in contract is approved; its safe runner is an acceptance requirement implemented alongside the first slice, not a prerequisite to choosing Go. Full external metadata/search policy is not needed for built-in-only work but must be decided before external execution. |
| Native Windows known-folder resolution | Required before affected installation/release functionality | Needed before choosing real Windows config/state/install destinations or claiming resolved paths. Keep diagnostics explicit about missing paths until implemented; read-only registration can proceed. |
| Restricted/unelevated Windows link policy, ACL-denied logo and destination access | Required before affected installation/release functionality | Successful links in CI and mocked errors 5/50/1314 do not verify real refusal behavior. Require native restricted-account cases before Windows release support; safe refusal and explicit fallback precede Windows managed-file work. Do not change host policy to force a pass. |
| Broader filesystem semantics: UNC/network paths, junctions/reparse points, long-path policy, reserved/device names, cross-volume operations, case collisions, inaccessible paths | Required before affected installation/release functionality | Fixture primitives do not establish general canonicalization, replacement, durability, or undo. Supported cases need native tests; unsupported cases need explicit preflight refusal. Cross-volume rollback and drift/interruption tests precede managed mutations. |
| Hostile concurrent extraction-parent changes and partial-install recovery | Required before affected installation/release functionality | Test-owned extraction assumes exclusive parent ownership and may leave partial files for harness cleanup. A real installer must close that race or enforce an equivalent safe boundary and journal recovery. |
| Publisher authentication, trust-root delivery, support floors, release provenance/licensing, authenticated download and bootstrap | Required before affected installation/release functionality | Integrity evidence cannot authorize public release or remote execution. Complete the release gates above in later scoped tasks. |
| Representative desktop warm measurements and numeric gate calibration | Deferred platform coverage | CI gives useful development observations but cannot justify physical-desktop performance guarantees. Required before hard timing gates or broader performance claims, not before read-only core development. |
| Controlled cold-cache measurements | Deferred platform coverage | No cold-start guarantee is proposed. Gather controlled evidence before making one; first-observed timings cannot substitute. |
| Extracted-path/fallback-logo startup timings | Required before affected installation/release functionality | Existing timings use a different logo/path setup. Measure the actual packaged startup configuration before claiming installed performance. |
| WSL native execution, mounted-filesystem boundaries, and separate state | Deferred platform coverage | Linux compilation and detector fixtures do not establish WSL behavior. Validate WSL separately before enabling its support; never translate native Windows paths silently. |
| Other CPU architectures, older OS versions, Android shared storage and other filesystem environments | Deferred platform coverage | Keep them outside the initial matrix. Native runtime/filesystem/dependency evidence is required before extending claims; explicit capability refusal remains necessary. |
| External dispatch/discovery scale, specification/planning performance | Required before affected installation/release functionality | Establish benchmarks when those features are implemented, before shipping their performance claims. No meaningful measurements can be inherited from an unimplemented path. |

The open Phase 0 manifest, module-selection, and repository-size choices remain tracked in the [roadmap](../../plans/roadmap.md). They do not block the approved built-in-only slice, which loads no manifests and moves no live sources. They remain gates for their dependent planning/migration work.

## Next Bounded Implementation Task

Create the permanent Go entry point and register **only the existing experimental read-only built-ins** through a small validated registry. This is the first Phase 2 slice, not the whole command center. The following file scope is approved for a later task; none is created by this documentation task:

| Planned files | Responsibility |
| --- | --- |
| Root `go.mod` (`module github.com/5nik7/dots`, `go 1.27.1`) | Permanent private-core module; no third-party requirements, no workspace file, no dependency download |
| `cmd/dots/main.go` | Wire streams, exit status, logo provider, and platform report into the CLI |
| `internal/cli/cli.go`, `cli_test.go`, `logo_unix_test.go` | Preserve bounded optional-logo handling and stream/error behavior; adapt branding to the new development binary |
| `internal/dispatch/registry.go`, `registry_test.go` | Typed built-in metadata and validated lookup, separating aliases/global help/version spellings from canonical route tokens; route-to-handler binding |
| `internal/platform/platform.go`, `platform_test.go`, `open_unix.go`, `open_other.go` | Port the verified read-only adapter and tests with existing limitations intact |
| `tests/cli_test.go` | Isolated process contracts and unchanged-root snapshots for the new development binary |
| `tools/verify_core.py` and `.github/workflows/phase-1-linux.yml` | Explicit root-core allowlisted copying/build/check/bench support with equivalent offline and telemetry isolation; add native core checks without repointing or deleting the experiment checks |
| `plans/phase-2-command-center.md` and affected reference docs | Focused acceptance plan, built-in metadata contract, new development runner instructions, performance evidence, and accurate status |

Seed help (`help`, `-h`, `--help`, and no arguments), `--version`, `doctor`, `doctor --json`, and contextual doctor help only. Preserve current experimental argument acceptance and exit codes 0/1/2 for the new read-only surface, with explicit `dots` development branding/version changes; preserve the experimental executable unchanged. Keep diagnostic JSON schema 1 and `not_probed` capabilities, including Windows missing-path warnings. Do not add `version`, `commands`, completion, or mutation routes in this first slice.

Define typed metadata for route, summary, synopsis, examples, aliases, hidden status, platform/capability requirements, output/schema support, mutation class, and handler identity according to [commands.md](../commands.md#metadata). Generate built-in help and testable metadata projections from that one table. A projection consumed by future completion/JSON/Markdown renderers must have consistency tests; no public completion/discovery command or external metadata carrier is selected yet. Update `docs/commands.md` with the concrete built-in representation in the implementation change.

Use exact validated built-in route resolution and handler-owned argument parsing. Reject duplicate canonical routes and alias collisions before dispatch. Test overlapping synthetic built-in route tokens and argument preservation without exposing fixture commands. Reserve the longest-prefix external resolver for the next distinct slice, after explicit trusted search directories, precedence, executable suffix/interpreter rules, and metadata validation are approved. No PATH scan, extension subprocess, plugin handshake, or new trust input belongs in the first slice.

Compatibility constraints: keep `bin/dots` active and its `-d`/`--dir`, `-r`/`--raw` behavior unchanged. Build the new binary only into harness-owned output roots; do not add it to PATH or replace the live command. Preserve `experiments/go-portability/` as an independent historical module and retain all evidence. Do not copy the test-only filesystem primitives into a production mutation API. Do not create the proposed empty resolver/state/apply directories, move dotfiles, edit shell initialization, initialize submodules, or embed the logo. Preserve DOTS-first and executable-relative optional-logo lookup.

Acceptance tests: native isolated Go formatting/vet/unit and process checks on the three initial development targets; metadata completeness, canonical/alias collisions, unknown/extra arguments, contextual help avoiding diagnostics, stdout/stderr/exit contracts, JSON schema and redaction, no helper dependency with empty PATH, optional-logo failures and Unix FIFO regression, path strings with spaces/Unicode/leading dashes, and unchanged runtime roots. Use injected/synthetic unavailable-platform cases to distinguish unavailability from unknown routes without announcing a new stable exit-code scheme. Assert known dispatch does not enumerate a registry directory or inspect the repository. Retain relocated rebuild/dependency checks and new help/version/registry lookup measurements; do not reuse spike binary timing identities after a code/layout change. Synchronize README's development instructions, architecture, commands, testing and its guide, platforms/safety if behavior changes, and the roadmap. Keep future runner commands labeled proposed until implemented and verified.

## Alternatives Considered

- **Keep Go provisional:** appropriate if native execution or packaging had failed without a bounded remedy. The retained evidence resolves those uncertainties for the intended next slice. Continuing provisional status until every future installer/platform feature exists would conflate language selection with production support.
- **Reject Go or repeat the core in another language:** no observed startup, runtime dependency, build, or primitive-filesystem failure justifies that cost. Go remains replaceable at adapter boundaries, and higher-level safety design is not language-specific.
- **Claim all four platforms supported or select broad minimum OS versions now:** the evidence does not support it. Adopt a small development matrix and gate production support by subsystem.
- **Publish checksum-only bundles immediately:** checksums do not establish publisher identity, and extraction fixtures do not implement safe installation. Retain the tested packaging direction but require the release trust work first.

## Validation and Evidence Reuse

Review started on the exact requested checkpoint with only `logo.txt` modified. The retained [checkpoint CI run 34424607080](https://github.com/5nik7/dots/actions/runs/34424607080) reports successful native Linux and Windows `check`/`dist` jobs. The private archive is `$HOME/dots-review-evidence/phase-1-distribution-20260910-trlmvjbr/`: `final-ci-results.json`, `final-checkpoint.json`, `linux-dcfea90.review.json`, `windows-dcfea90.review.json`, the corresponding ZIPs, and `termux-final-dist/artifact/evidence.json` retain exact provenance. Desktop reviews record 36 contained file hashes and 17 source fingerprints verified per artifact. This review rechecked both outer ZIP digests and current Go input fingerprints, and reused those successful detailed reviews instead of executing artifacts again.

Termux's final distribution and preceding native check retain their distinct source/tooling provenance in that archive. Native binaries match the prior startup evidence: Termux `af73814fe6777aa2436ab5dc4c6dce18a2a9d53a9f8fa693f9f1686aa2c8d693`, Linux `979a4f412d24d815ea484a5e8c291f70a2bc1da7cfeafaeebc30b25d37a603e5`, Windows `8850624e20a07a8f983b851fd0427f41a0d0e896b1c07b857ff3993afd5a909a`. The desktop timing reviews are in `$HOME/dots-review-evidence/phase-1-windows-20260910-1dse8mjt/{linux,windows}-0f538ff.review.json`; original Termux raw evidence remains in the durable archive identified by the plan's [reviewable checkpoint](../../plans/phase-1-portability.md#reviewable-checkpoint).

The original proposal review made no executable behavior changes requiring a new test or benchmark run. The existing `python3 experiments/go-portability/tools/verify.py docs` check passed (101 relative links in 24 files), as did `git diff --check`, staged whitespace checks, and fragment-target validation for the changed documentation. The owner logo hash and unchanged historical decision/executable sources were also checked. Evidence remains outside Git. Any automatic branch-push CI run is additional documentation-commit verification, not new language, production-support, or performance evidence.

## Approved Decisions

1. Adopt Go and the initial Go 1.27.1 build/test baseline, while retaining the three-target development matrix and no untested production OS-floor claims.
2. Approve the warm targets and advisory timing/mandatory regression-review policy.
3. Approve the minimal bundle direction and publisher-authenticated release requirement, with implementation and trust mechanism selection deferred behind the stated gates.
4. Approve the gap classifications and the built-in-only permanent-core task above as the next implementation boundary.

All four decisions above were approved at the revision identified in the owner approval record. No further technical adoption blocker was found within this bounded evidence review. Phase 2 remains unimplemented.

## Supersedes or Superseded By

This record settles the language question left open by [0001](0001-go-portability-experiment.md). That accepted experiment authorization and its evidence remain historical and unchanged; this decision does not invalidate them.

## Implementation Follow-up

The first permanent read-only core/registry slice is implemented and tracked in [the Phase 2 plan](../../plans/phase-2-command-center.md). Statements above about implementation status describe the decision at acceptance; its scope, remaining gates, and historical evidence are preserved.
