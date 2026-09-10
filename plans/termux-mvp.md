# Termux MVP Plan

**Status: Proposed**

The Termux MVP is the first end-to-end proof that `dots` can inspect, plan, apply, track, and undo real dotfile changes safely. It deliberately manages a small subset of the current repository.

## Goal

On the current Termux installation, use the new core to manage selected shared and Termux-specific files with symbolic links by default, while preserving existing files in a recoverable transaction and producing no changes on a second identical apply.

## Dependencies

- Core language and Termux artifact validated by the [Phase 1 experiment](phase-1-portability.md). Native experimental evidence exists and [Go adoption is accepted](../docs/decisions/0002-phase-1-go-adoption.md). Permanent release/installation implementation and its trust/verification gates remain pending.
- Command center sufficient for implemented lifecycle routes.
- Manifest/profile resolver.
- Filesystem observer and planner.
- Transaction journal, backup, rollback, history, and undo.
- Temporary-root integration harness with failure injection.

The real-home trial does not begin until these foundations pass isolated tests.

## Proposed Initial Modules

Final selection follows the repository inventory. Prefer a small set with high value and understandable destinations:

- Git configuration that contains no secrets.
- Zsh entry point and a limited shared Zsh configuration subset.
- A small set of actively used portable scripts.
- Termux configuration such as properties or colors only after reload behavior is represented safely.
- Generated shell environment integration, if it can replace the current Zsh-specific `dot.env` behavior without slowing startup.

Do not migrate all `configs/`, fonts, wallpapers, PowerShell content, secrets, or the complete Android submodule in the MVP.

## Profile Selection

Use the clean internal model:

```text
platform = termux
profile  = personal
host     = explicitly selected optional device name
```

A bootstrap convenience flag may select Termux, but the persisted desired-state model must not treat platform and profile as interchangeable.

## Work Stages

### 1. Inventory the Candidate Files

- Record source path, current destination, current object type, sensitivity, current consumers, and required reload behavior.
- Identify whether any candidate currently comes from `androidots` or `secrets`.
- Exclude private or ambiguous material from the first slice.
- Decide file-level versus complete-directory ownership explicitly.

### 2. Create Modules Beside the Existing Layout

- Add module manifests and profile composition without deleting legacy sources.
- Reuse existing source files initially when doing so has unambiguous ownership.
- Avoid duplicating content that could drift between legacy and new paths.
- Add compatibility notes for existing shell loaders.

### 3. Resolve and Plan in an Isolated Root

- Use fixtures representing the current target classifications.
- Review human and structured specification output.
- Review every planned source, destination, backup, and link strategy.
- Verify paths containing Termux prefixes are adapter-derived rather than hard-coded.

### 4. Exercise Transactions

- Apply into an empty fixture home.
- Apply over existing files and directories.
- Inject failure after every journal boundary.
- Verify automatic rollback and recovery-required behavior.
- Verify second apply is a no-op.
- Verify undo restores the fixture's previous content.

### 5. Dry Run the Real Environment

- Run diagnostics and record platform/capability evidence.
- Produce a real plan without cache, Git, package, submodule, or target mutations.
- Manually review conflicts and exclusions.
- Export or persist the approved plan for comparison during apply.

### 6. Apply the Real Transaction

- Confirm the repository revision and clean/known working state.
- Create the journal and verified backups before replacement.
- Apply only the approved module set.
- Stop and roll back on any unplanned state change.
- Preserve logs with secret redaction.

### 7. Verify and Undo Drill

- Confirm every managed link points to the expected repository source.
- Start a fresh Zsh session and verify startup behavior and timing.
- Verify affected Termux configuration and reload behavior.
- Confirm status reports no drift.
- Confirm a second plan contains no mutations.
- Perform an undo drill in the isolated fixture again and document the real recovery command/path without necessarily undoing the successful real installation.

## Acceptance Criteria

- Planning the real environment makes no persistent changes.
- Every selected file has documented ownership and provenance.
- Existing replaced targets have verified transaction backups.
- Apply either succeeds completely or reaches a clear rolled-back/recovery-required state.
- Correct links are reported as no-ops.
- A second unchanged apply produces zero mutations.
- Drifted targets are detected.
- Undo refuses to overwrite post-apply drift by default.
- Shell startup remains within an agreed measured regression bound.
- No private submodule is initialized during the public/core workflow.
- No secrets appear in human output, JSON, or journal diagnostics.
- README documents only the exact verified workflow.

## Risks

### Termux Binary Compatibility

The proposed Go core must first prove a reliable build artifact for the current Android architecture and Termux runtime. Failure returns the project to the implementation-language decision without changing the specification or safety goals.

### Existing Shell Coupling

The current environment uses Zsh-specific variables, `PATH`, and `fpath` integration. Replacing this too broadly could break shell startup. Migrate a small generated integration file and retain a clear compatibility path.

### Repository and Submodule Paths

Some current Termux content may live in a submodule unavailable during anonymous bootstrap. The MVP should use public, directly available sources or explicitly separate the authenticated stage.

### Termux Reload Side Effects

Reloading application settings can affect active sessions. Treat reload as an explicit post-apply adapter action with documented scope and test it independently from file replacement.

## Non-Goals

- Fresh-device remote bootstrap; that follows the successful local MVP.
- Full package reproduction.
- Secret synchronization.
- All shell families.
- All current configurations and scripts.
- Wallpapers, fonts, and theme asset migration.
- Native Windows or WSL support claims.
- Arbitrary hooks.

## Documentation Updates During the MVP

- Accepted manifest decisions go to `../docs/specification.md` and decision records.
- Verified Termux paths and limitations go to `../docs/platforms.md`.
- Transaction behavior goes to `../docs/safety.md`.
- Actual commands and examples go to `../docs/commands.md`.
- Test runners and evidence go to `../docs/testing.md`.
- Implemented user workflow goes to `../README.md`.
- Completed roadmap items are checked in `roadmap.md` in the same change.
