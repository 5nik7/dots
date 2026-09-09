# Managed Files Work Guide

Read this guide before changing module manifests, profile resolution, file adoption, links, copies, templates, planning, apply, backups, state journals, history, or undo.

## Boundary

The core transaction engine owns managed filesystem mutations. A platform adapter may perform a primitive selected by the engine, but an extension must not independently replace files in a user's home directory and claim the operation is managed by `dots`.

## Before Editing

1. Read `docs/specification.md`, `docs/safety.md`, and `docs/architecture.md`.
2. Identify the desired-state input, current-state observation, planned operation, journal record, and inverse operation.
3. Identify platform-specific path or link semantics.
4. Add failure and interruption cases to the plan before implementation.
5. Prepare a temporary test root; never test against the real home directory.

## File Ownership

- Source files belong in a declared module.
- A convention such as `modules/<name>/home/` may map files relative to the target home directory.
- Exceptional destinations must be explicit in the module manifest.
- File-level linking is the default because it preserves unrelated files in shared directories.
- A directory link is allowed only when a module explicitly owns the complete destination directory.
- Two selected modules may not claim the same destination unless an explicit, validated replacement relationship exists.

## Planning

Planning is read-only and deterministic for the same specification and observed state.

Every planned operation should expose at least:

- Resource or module identifier.
- Source and destination.
- Observed destination type and ownership.
- Requested strategy, such as link or copy.
- Intended action or no-op reason.
- Backup requirement.
- Reversibility classification.
- Platform-specific caveat or blocked reason.

Do not hide conflicts behind confirmation prompts. A prompt may approve a fully described operation; it does not replace validation.

## Apply and Undo

- Preflight all operations before mutating any target.
- Acquire a state lock for apply and undo.
- Create and durably initialize the transaction journal before the first target change.
- Back up or record the prior object according to `docs/safety.md`.
- Record completion after each operation so interrupted recovery knows the exact boundary.
- On failure, reverse completed reversible operations in reverse order.
- Undo must compare the current target with the applied record before restoring prior data.
- A forced undo must remain explicit, logged, and narrowly scoped.

## Adoption

Adoption brings an existing unmanaged file into the repository. It is not a synonym for force-overwrite.

A safe adoption flow should:

1. Resolve and validate the destination.
2. Refuse secrets or suspicious credential material by default.
3. Copy the existing content into a new module-owned source path.
4. Verify the copy before replacing the original.
5. Plan the replacement as a normal managed link or copy transaction.
6. Leave an auditable record of where the content came from.

Do not automatically commit adopted content.

## Tests

Cover at least:

- Missing target and missing parent.
- Correct existing link.
- Broken link.
- Link to the wrong source.
- Regular file, directory, and platform-specific link object.
- Destination modified after apply.
- Source removed or repository relocated.
- Read-only target or permission failure.
- Interruption after each operation boundary.
- Second unchanged apply producing no operations.
- Paths with spaces, Unicode, and leading dashes.

Any change to classification, force behavior, backup contents, journal fields, or undo semantics requires corresponding updates to `docs/safety.md` and `docs/specification.md`.

