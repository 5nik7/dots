# Safety and Recovery Model

**Status: Proposed invariant set; transaction details remain draft**

Safety is a core product feature of `dots`, not a wrapper around destructive file operations. This document is authoritative for planning, mutation, backup, rollback, undo, package, hook, repository, and secret behavior.

## Implemented Experiment Boundary

The [Phase 1 experiment](../plans/phase-1-portability.md) exposes no managed filesystem mutation command. Help may read the optional public logo. It validates the opened handle before reading; Unix opens are nonblocking to avoid waiting for a writer if a regular logo is replaced with a FIFO. This does not impose a general filesystem I/O deadline. Diagnostics reads allowlisted path/environment inputs and limited runtime metadata, without opening dotfile contents or creating capability probes. Version output does not inspect the repository. Unknown arguments are not echoed into diagnostics.

Symlink/copy operations exist only in disposable tests, using directory-rooted filesystem APIs and exclusive creation to exercise refusal on existing targets. Build caches, fixture setup, and retained development artifacts belong to harness-owned temporary roots. These tests do not implement backup, apply, rollback, undo, or a journal and provide no exception to the managed-mutation transaction rules below. Read-only CLI process checks compare controlled fixture roots before and after execution; they are not a system-wide syscall audit.

## Guarantees

The intended guarantees are:

- Read-only commands do not change managed targets or external systems.
- A complete plan exists before apply starts.
- Existing targets are classified before replacement.
- Replaced user data is backed up durably when it is reversible.
- Every mutation has a journaled transaction identity.
- Failure triggers reverse-order rollback of completed reversible operations.
- Undo detects drift before restoring prior state.
- Unsupported or partially reversible work is identified before approval.

No command should imply stronger rollback guarantees than its operations can provide.

## Read-Only Boundary

`status`, `spec`, `plan`, discovery, validation, and diagnostic operations are read-only unless their help explicitly describes a separate cache-refresh action.

Read-only means no:

- Target creation, replacement, permission change, or timestamp adjustment.
- Package-manager refresh or installation.
- Git fetch, pull, checkout, submodule initialization, stash, or clean.
- Persistent state migration.
- Shell profile edit.
- Registry edit.
- Credential prompt.
- Hook execution with undeclared side effects.

A disposable in-memory representation or rebuildable cache read is acceptable. Cache writes must be designed and described separately so `plan` remains suitable for auditing.

## Target Classification

Before planning a mutation, classify the destination using link-aware filesystem inspection.

| Observed target | Typical plan result |
| --- | --- |
| Missing | Create parent as needed, then install resource |
| Correct managed link | No-op |
| Broken managed link | Repair through a transaction |
| Link to another source | Conflict or backup-and-replace under explicit policy |
| Matching managed copy | No-op |
| Modified managed copy | Drift; require normal replacement/backup policy |
| Unmanaged regular file | Back up, then replace only after approval |
| Unmanaged directory | Conflict unless the resource safely manages compatible children |
| Platform-specific link object | Compare through the platform adapter |
| Inaccessible or ambiguous | Block before mutation |

Classification must not follow a link in a way that causes the engine to back up or delete the link's external target accidentally.

## Plan Contract

A plan contains ordered operations and enough information for review and execution.

Each operation should include:

- Stable operation and resource identifiers.
- Source and canonical destination.
- Observed target classification.
- Requested and effective strategy.
- Action, no-op reason, warning, conflict, or blocked reason.
- Backup action and expected location.
- Required capabilities and privileges.
- Reversibility class.
- Sensitive-field redaction markers.

Apply consumes the plan representation. It must validate that critical observations have not changed between planning and mutation.

## Transaction Lifecycle

1. Validate specification and complete plan.
2. Obtain explicit approval or a valid non-interactive approval flag.
3. Acquire an exclusive state lock.
4. Revalidate mutable preconditions.
5. Allocate a transaction ID and backup directory.
6. Write and durably initialize the journal.
7. Apply each operation, recording its start and completion boundary.
8. On failure, stop forward progress and roll back completed reversible operations in reverse order.
9. Record success, successful rollback, partial rollback, or recovery-required state.
10. Release the lock after durable final status.

An interrupted process must be detectable on the next invocation. Recovery must use journal evidence rather than guessing how far apply progressed.

## Journal

The eventual journal schema should record:

- Transaction ID, schema version, timestamps, and status.
- CLI build/version and repository revision.
- Platform, profile, host, and resolved-spec digest.
- Approved plan or a stable reference to it.
- Operation order and per-operation status.
- Previous object metadata, backup path, and integrity digest where applicable.
- Installed object identity or digest for drift checks.
- Errors, rollback attempts, and recovery instructions.
- Explicit force or policy overrides used.

Journal writes must use atomic replacement and appropriate durability for the platform. Secrets are represented by redacted metadata or opaque references.

## Backups

- Transaction backups live in the machine state root, not solely in the repository.
- Preserve the object itself rather than accidentally dereferencing a link.
- Preserve relevant permissions and timestamps when the platform supports them.
- Verify a backup before deleting or replacing the source object it protects.
- Use collision-resistant transaction-owned paths rather than ad hoc `.bak` siblings.
- Retention and pruning must never remove a backup needed by an incomplete or recovery-required transaction.
- Explicit snapshots and automatic transaction backups need distinguishable metadata.

Pruning is a destructive operation with a plan, retention explanation, and narrowly scoped confirmation.

## Atomicity

Use temporary siblings and atomic rename/replace where supported. Filesystem-level atomicity may not span volumes, package managers, repositories, or hooks.

The engine should preflight cross-volume or unsupported replacement behavior and report reduced guarantees. Never describe a multi-system transaction as fully atomic when only its journal is coordinated.

## Rollback

Automatic rollback handles failure during apply.

- Reverse only operations confirmed complete by the journal.
- Execute inverse operations in reverse order.
- Do not continue normal apply after rollback begins.
- Record rollback failures without destroying their backups.
- Finish in a clearly queryable `rolled-back` or `recovery-required` status.
- Provide specific recovery instructions and paths without exposing secret content.

Rollback must itself be resumable or manually recoverable.

## Undo

Undo is a later deliberate reversal of a completed transaction.

- Compare each current target with the object installed by the transaction.
- If the target has changed, report drift and refuse replacement by default.
- Scope any force option to the named transaction/resource.
- Preserve the drifted target before forced restoration when possible.
- Record undo as its own transaction instead of deleting history.
- Do not infer that packages added by the original transaction are safe to remove.

## Link and Copy Policy

- Symbolic link is the repository default.
- Copy is selected explicitly by resource or machine policy.
- A directory link requires declared ownership of the whole destination directory.
- Unavailable link capability blocks the plan unless an explicit fallback is configured.
- Fallback choice appears in the plan and journal.
- Copies record an installed digest so status and undo can detect drift.
- Repository relocation should produce broken-source diagnostics and a repair plan, not automatic unjournaled rewrites.

## Packages

The package adapter records whether each requirement was already satisfied and whether `dots` installed it.

- Package database refresh, install, upgrade, and removal are distinct planned actions.
- Do not upgrade all packages as an implicit prerequisite for applying dotfiles.
- Do not automatically remove packages during ordinary filesystem rollback or undo.
- A future package removal command may propose packages added solely by `dots`, but must query current reverse dependencies and require explicit approval.
- Package-manager output and failure belong in the journal without leaking repository credentials or environment secrets.

## Hooks and External Side Effects

Arbitrary hooks weaken dry-run and rollback guarantees.

- Prefer built-in declarative operations.
- Declare hook stage, command, platform, mutation class, inputs, and rollback support.
- Do not execute a mutating hook during planning.
- Mark non-reversible hooks clearly before approval.
- Require explicit opt-in for untrusted or arbitrary repository hooks.
- Capture exit status and bounded, redacted logs.
- Do not claim that transaction rollback reversed a hook without a verified inverse protocol.

General hooks are outside the initial Termux MVP.

## Secrets

- Public bootstrap does not initialize the secrets source.
- Repository URLs never embed credentials.
- Plans, specs, logs, diagnostics, errors, command history suggestions, and JSON redact secret values.
- A secret reference may expose provider and identifier only when that metadata is not itself sensitive.
- Secret files require restrictive permission planning appropriate to the platform.
- Adoption refuses likely credential material by default.
- Debug bundles use an allowlist rather than attempting to redact arbitrary full environment dumps afterward.

## Repository Operations

- Never force-reset, clean, or discard a dirty repository automatically.
- Pull/update reports dirty state and divergence before changing branches or revisions.
- Record the repository revision used by every apply.
- Do not automatically initialize all submodules.
- Optional source updates are independent from main repository updates.
- A moving remote bootstrap channel must allow a pinned alternative.

## Protected Boundaries

The planner needs explicit allowed destination roots. A destination outside those roots is blocked unless a separately designed privileged/system mode authorizes it.

Path validation occurs after variable expansion and normalization. Reject traversal, empty target, filesystem root, unresolved variable, unexpected UNC/device path, and other platform-specific escapes before mutation.

No recursive destructive action may use an unresolved environment variable, broad home directory, repository root, or filesystem root as its target.
