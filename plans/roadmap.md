# Dots Roadmap

**Status: Active incremental implementation; later phases proposed**

This roadmap sequences the future `dots` CLI around its riskiest foundations: Termux portability, deterministic specification resolution, and recoverable filesystem mutation.

## Completion Legend

- `[ ]` Not started.
- `[~]` In progress or partially complete.
- `[x]` Complete and reflected in durable documentation.
- `[!]` Blocked; explain the blocker beneath the item.

## Phase 0: Documentation and Inventory

Goal: establish sources of truth before implementation changes the live repository.

- [x] Add root `AGENTS.md` with project-wide rules and documentation contract.
- [x] Add task-specific agent guides.
- [x] Add working principles, architecture, command, specification, safety, platform, and testing docs.
- [x] Record a baseline inventory of the current public repository.
- [x] Define the first Termux MVP plan.
- [~] Review working decisions with the project owner. The isolated Go experiment is approved; other foundational choices remain open.
- [~] Create decision records for accepted foundational choices. [0001](../docs/decisions/0001-go-portability-experiment.md) authorizes evaluation only.
- [ ] Classify current files by module, destination, platform, ownership, size, generated status, and sensitivity.
- [ ] Identify current commands/configurations that require compatibility during migration.

Exit criteria:

- The core language experiment, manifest format decision, first migrated modules, and repository-size strategy have an agreed direction.
- No proposed command is presented as implemented.

## Phase 1: Portability and Core Skeleton

Goal: prove the executable model before building stateful behavior.

The owner authorized the limited [Termux portability experiment](phase-1-portability.md) before the unrelated Phase 0 manifest, module-selection, and repository-size decisions. This does not waive those decisions for subsequent phases or settle the permanent core language/layout.

- [x] Create a minimal core project without altering current dotfile installation.
- [x] Implement version and basic help fast paths.
- [~] Implement normalized platform diagnostic interfaces. Termux and Linux CI identity/candidates work; native Windows paths and live capability probing remain deferred.
- [x] Build and run a candidate Go core on the current Termux architecture.
- [~] Build and run candidate Linux and Windows artifacts. Both AMD64 targets cross-compile; Linux executable/tests now also run natively in CI. Windows execution is pending.
- [~] Measure cold and warm startup baselines. The experiment records Termux and Linux CI first-observed/warm runs; controlled cold-cache and representative desktop-hardware baselines remain pending.
- [x] Validate Termux filesystem and link primitives in a disposable target.
- [ ] Record the implementation-language decision.
- [x] Establish initial unit test and formatting commands.
- [x] Add bounded native Linux CI validation and retained evidence. Native checks, startup samples, and uploaded artifact hashes/source were reviewed; see the [focused results](phase-1-portability.md#native-linux-validation).

Exit criteria:

- The selected core builds reproducibly for the intended first platforms.
- Termux startup and filesystem capability results are recorded.
- The project can reject the Go direction without discarding higher-level design work.

## Phase 2: Command Center

Goal: establish the stable discovery and extension foundation.

- [ ] Implement built-in route registration.
- [ ] Implement longest-prefix direct external command resolution.
- [ ] Define trusted extension directories and precedence.
- [ ] Finalize command metadata representation.
- [ ] Implement contextual help and group discovery.
- [ ] Implement command metadata validation and collision detection.
- [ ] Implement machine-readable command discovery.
- [ ] Generate Bash, Zsh, Fish, and PowerShell completion data as supported.
- [ ] Add dispatch, collision, unavailable-platform, and structured-output tests.
- [ ] Record the command protocol decision.

Exit criteria:

- Adding a valid `dots-*` extension makes it discoverable without editing the central dispatcher.
- A normal direct route avoids full registry scanning.
- Help, discovery, completion, and generated reference agree.

## Phase 3: Specification and Read-Only Planning

Goal: resolve a desired state and compare it with an isolated machine without mutation.

- [ ] Finalize TOML or select another manifest format.
- [ ] Add schema-version handling.
- [ ] Implement repository and machine configuration loading.
- [ ] Implement platform, profile, host, module, and dependency resolution.
- [ ] Implement destination variables and allowed-root validation.
- [ ] Implement resource collision and explicit replacement rules.
- [ ] Implement current filesystem observation.
- [ ] Implement human and structured resolved-spec output.
- [ ] Implement human and structured operation plans.
- [ ] Add deterministic, path-safety, and golden-output tests.
- [ ] Record manifest and resolution decisions.

Exit criteria:

- The same inputs resolve to the same specification and plan.
- Planning against a temporary home causes no persistent changes.
- Every selected resource can explain its provenance.

## Phase 4: Transactions, Backups, and Undo

Goal: safely manage files in disposable environments before touching a real home.

- [ ] Finalize transaction and journal schemas.
- [ ] Implement exclusive state locking.
- [ ] Implement backup creation and verification.
- [ ] Implement link and copy operations.
- [ ] Implement durable operation boundaries.
- [ ] Implement automatic reverse-order rollback.
- [ ] Implement interrupted-transaction detection and recovery guidance.
- [ ] Implement history inspection.
- [ ] Implement drift-aware undo as a new transaction.
- [ ] Test interruption and failure at every operation boundary.
- [ ] Test idempotent reapply and repository relocation.
- [ ] Record transaction, force, retention, and compatibility decisions.

Exit criteria:

- Failure injection cannot silently lose the preexisting test target.
- An unchanged second apply is a no-op.
- Drifted targets are not overwritten by ordinary undo.

## Phase 5: Termux MVP

Goal: manage a small, valuable set of real Termux dotfiles using the new engine.

Detailed scope and acceptance criteria live in [`termux-mvp.md`](termux-mvp.md).

- [ ] Select initial modules from the inventory.
- [ ] Write manifests without moving unrelated existing files.
- [ ] Generate and review a plan against the current Termux setup.
- [ ] Apply first in a disposable Termux-like test root.
- [ ] Back up current real targets through the transaction engine.
- [ ] Apply the approved real Termux transaction.
- [ ] Verify shell behavior, links, status, idempotence, and undo.
- [ ] Keep a compatibility path for actively used legacy commands.
- [ ] Update README with the first truthful usable workflow.

Exit criteria:

- The selected Termux modules can be planned, applied, checked, and undone safely.
- The old installation remains recoverable.
- User-facing documentation matches the verified commands exactly.

## Phase 6: Bootstrap and Packages

Goal: reproduce the Termux MVP from a fresh installation.

- [ ] Create the minimal POSIX bootstrap script.
- [ ] Publish versioned artifacts and checksums.
- [ ] Clone the public repository without recursive submodules.
- [ ] Add `pkg`/Termux-APT package adapter fixtures and integration tests.
- [ ] Consider Termux-pacman only after detecting its actual environment safely.
- [ ] Add explicit profile selection and unattended approved apply.
- [ ] Add resumable failure behavior.
- [ ] Test no-install, existing-install, network-failure, and dirty-repository cases.
- [ ] Publish a pipe-to-shell example only after hosted content and verification are ready.

Exit criteria:

- A disposable fresh Termux environment reaches the same desired state without private credentials.
- Re-running bootstrap is safe and explains any divergence.

## Phase 7: Linux and WSL

Goal: reuse the same core, modules, and transaction semantics across additional Unix-like platforms.

- [ ] Add verified Linux platform and package adapters incrementally.
- [ ] Add WSL detection and boundary tests.
- [ ] Create shared and platform-specific modules without destination ambiguity.
- [ ] Add bootstrap coverage.
- [ ] Add hosted or recorded platform evidence.
- [ ] Update the support matrix only for verified subsystems.

## Phase 8: Native Windows

Goal: support native Windows without depending on Git Bash or WSL.

- [ ] Create PowerShell bootstrap.
- [ ] Implement Windows known-folder and canonical-path adapter.
- [ ] Capability-test symbolic links, junctions, and hardlinks.
- [ ] Implement explicit copy/junction policy without silent fallback.
- [ ] Migrate a small PowerShell profile/module set.
- [ ] Add Windows transaction and undo integration tests.
- [ ] Add package adapter only after file management is stable.

## Phase 9: Optional Sources and Advanced Modules

Goal: expand capability without burdening the core bootstrap.

- [ ] Design profile-aware optional source synchronization.
- [ ] Handle private sources without logging credentials.
- [ ] Move or fetch large fonts, wallpapers, demos, and third-party payloads lazily.
- [ ] Add themes, generated environment files, templates, and shell reload adapters.
- [ ] Design a constrained hook protocol if declarative operations are insufficient.
- [ ] Add source/manifest locks for reproducibility if needed.
- [ ] Add self-update and release-channel policy.

## Deferred Decisions

- Whether to keep the main repository at `~/dots` by default long term.
- Whether large assets move to one optional repository, multiple sources, releases, or another distribution mechanism.
- Whether personal platform submodules are absorbed into modules or remain optional sources.
- How generated command docs and schema docs are checked into the repository.
- Which package managers beyond the first verified set are supported.
- Whether a higher-level `dots sync` workflow should compose repository, source, package, and apply stages.

Resolve deferred decisions only when the next phase requires them.
