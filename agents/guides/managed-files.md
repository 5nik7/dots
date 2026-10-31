# Managed Files Work Guide

Read this guide before changing catalogs, mapping resolution, file adoption, links, copies, templates, planning, apply, backups, state journals, history, or undo.

## Boundary

The shared `lib/dots/files/transactions.py` engine owns managed filesystem mutations under decision 0010, with explicit POSIX and Windows adapters. A platform adapter may perform a primitive selected by the engine, but an extension must not independently replace files in a user's home directory and claim the operation is managed by `dots`.

## Before Editing

1. Read `docs/specification.md`, `docs/safety.md`, and `docs/architecture.md`.
2. Identify the desired-state input, current-state observation, planned operation, journal record, and inverse operation.
3. Identify platform-specific path or link semantics.
4. Add failure and interruption cases to the plan before implementation.
5. Prepare a temporary test root; never test against the real home directory.

## File Ownership

- Source files belong to their catalog repository; resources declare explicit source and destination mappings.
- Preserve unrelated files and nested repository ownership.
- Directory mappings must declare ownership of the complete destination.
- Reject conflicting active claims unless the catalog supplies a valid explicit replacement.
- Link by default; copying is an explicit strategy, never a silent fallback.

## Planning

Planning is read-only and deterministic for the same specification and observed state.

Every planned operation should expose at least:

- Resource identifier.
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
3. Copy the existing content into a new repository-owned source path.
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

## Implemented Catalog and Config Migration

Read [files](../../docs/files.md) before changing `lib/dots/files`, `.dots` catalogs
or `bin/dots-files-*`. Catalog tracking edits source metadata only; do not add
installation behavior under an inventory route. Keep owning-repository boundaries,
private exclusions, explicit replacements and directory collision classification.
`config/` is canonical in Dots/Androidots/Windots; retain compatibility aliases.
The separate `tools/migrate_config_paths.py` defaults to preview and requires an
absolute recovery journal for apply/rollback. Never use real-home migration as a test.
Run `python3 -B tools/test_files.py`; scale checks use `tools/bench_files.py`.

## Bounded managed operations

Read [files](../../docs/files.md) and [decision 0010](../../docs/decisions/0010-git-and-managed-file-operations.md) before changing adoption, linking, removal or backups. All routes use the shared Python engine and existing per-repository ownership. Keep optional retained snapshots separate from mandatory temporary rollback data. Remove preserves both a usable config and the repository source. Never use bak as an unverified replacement primitive. Run `python3 -B tools/test_file_operations.py` alongside catalog regressions; use only disposable homes and repositories.

## Bounded checkout lifecycle

`dots files repair` owns current-platform destination repair. Reuse its receipt/latest-transaction evidence checks and retained installation baselines; do not broaden automatic eligibility or infer ownership from a catalog path alone. Ordinary occupied destinations and unverified links require an explicit helper choice plus final batch approval. Keep theme/other-owner/catalog-conflict/unsafe-path blocks, bind review to captured guards and never rebuild after approval. Run `tools/test_files_repair.py` with file-platform, picker, installation and mapping regressions. Source restoration, recursive repair and theme publication remain separate workflows.

Stash/edit mappings use the same installation receipt and Store. `enabled: false`
must remain visible but excluded from active claims/install/link; never reset it
in a track update. Retain original backup pointers for deliberately absent owned
targets, validate candidate catalogs without writing them, and include receipt
changes in undo/recovery. Run `tools/test_file_mappings.py` alongside catalog,
file-operation and installation suites. Source content editing is separate from
the public mapping editor.

`dots files install/uninstall` and root setup scripts share the Store and native adapter. Preserve transactional installation receipts, first-install backups across updates, pre-existing-link nonownership and drift-preserving restoration. Keep `files remove` semantics separate. Native Windows support is bounded to mapped resources and recovery; see [installation](../../docs/installation.md). Theme setup prepares inactive generations and publishes through the Store without app side effects.

Profile `files` arrays are effective catalog inputs. Use `Catalog.input_paths()` for preview guards and `Catalog.updates()` for metadata writes; do not hardcode `.dots/files.json` as the mutation destination. Preserve profile settings/environment fields and independent repository ownership. Run `tools/test_profile_config.py` alongside affected file lifecycle suites. See [profile configuration](../../docs/profiles.md#profile-configuration).

The core schema-2/3 registry is permanent: IDs/platforms stay in `.dots/files.json`, sources in `.dots/sources.json`, and implementations in profile arrays without platforms/target maps. Always journal the full `Catalog.updates()` result, including tracking. Explicit mapping `--platform` selects a base profile; live apply requires the active leaf. See [file maintenance](../../.codex/skills/dots-files-maintenance/SKILL.md) and run `tools/test_profile_backend.py`.

File ID edits use `files edit OWNER:OLD --id NEW`. Schema 3 retains reserved
historical IDs for receipt recovery; schema 2 remains readable until an effective
rename. Journal all profile/replacement references and receipt identities with
optional selected-profile/live edits. Never infer a rename from arbitrary bulk
array replacement. Run the focused file-rename suite and preserve old journals.
