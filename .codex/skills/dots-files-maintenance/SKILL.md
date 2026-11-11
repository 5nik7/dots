---
name: dots-files-maintenance
description: Maintain Dots core file registry, source ownership, profile mappings and journaled file workflows. Use for catalog schemas, mapping editors, installation, repair or migration.
---

# Dots File Maintenance

`bak` and `link` also belong here. Read [backups](../../../docs/backups.md).
`files/backup_catalog.py` composes payload/catalog/consumer operations into Store;
do not add a second writer. Move is the default; restore retains the saved version
and protects occupied destinations. Receipt `backup_id` references protect first
uninstall baselines. Keep legacy journals readable. Generate backup metadata with
`tools/generate_backup_commands.py`; verify native bridges and all six `.ln`
adapters with backup, link and bootstrap integration tests in owned roots.

Read [managed-file guidance](../../../agents/guides/managed-files.md),
[file contracts](../../../docs/files.md), [safety](../../../docs/safety.md) and the
root agent contract. Inspect Git state, source boundaries and the active profile.
Capture effective inventories before migrations, including Windows destinations.

Keep the core `.dots/files.json` registry and `.dots/sources.json` source list.
The registry owns qualified IDs and platform eligibility. Profile
`files.REPOSITORY` arrays own implementation fields: local ID, source, target,
app, category, strategy and optional enabled/replaces. Profile rows never carry
platform lists or target maps. A registered resource without a profile mapping
must not install. Preserve qualified IDs and recovery compatibility.
Explicit ID edits use the registry rename history and one transaction across all
profile references and current receipts; mapping fields remain selected-profile
edits. Never reuse retired IDs or rewrite historical journals. Test renames with
`tools/test_file_renames.py` alongside the backend and lifecycle suites.

Use `Catalog` to join these inputs. Obtain preview guards with `input_paths()`
and serialize edits with `updates()`. Registry/profile changes belong to one
Store transaction, including tracking. Never hand-write one half of a CLI edit.
Default edits target the active leaf; explicit `--platform` mapping edits target
that platform's base profile. Live apply requires the active profile. Keep source
ownership separate from the profile storing the mapping.

Preserve full preflight, retained recovery, reverse rollback, receipt baselines,
drift-aware undo, explicit copy and occupied-target policies. Read-only commands
must not create state or initialize optional/private repositories. Do not use
real home/config/state paths in tests or run a live install for verification.

Run `tools/test_profile_backend.py` plus affected catalog, mapping, transaction,
installation, repair and adapter suites. Cover registry-only IDs, combined write
failure/undo, idempotence, inheritance, replacements and platform destinations.
Use [profile maintenance](../dots-profile-maintenance/SKILL.md) for manifests and
[command maintenance](../dots-command-maintenance/SKILL.md) for routes/presentation.
Record configuration and menu assessments for command changes. Use [dots-config](../dots-config/SKILL.md) for applicable integrations while retaining managed mapping and receipt ownership here. Preserve machine output, update canonical docs and rebuild/check the wiki. Native Windows evidence remains separate from fixtures.

Checkout setup uses the shared component/wizard/preparation modules under `lib/dots/files`. Follow [bootstrap](../../../agents/guides/bootstrap.md) for two-stage approval, opt-in preference saving, native parity and selective font/Leaf baselines. Only exact effective catalog directory mappings may translate child writes; keep link/catalog guards and preserve legacy backup references. Package/build effects remain outside filesystem rollback.

Bak deletion/pruning removes only a UUID payload container proven created by its original transaction and containing no unrelated members. Keep whole-container guards, rollback and missing-payload catalog cleanup; never infer ownership from a directory name or remove adjacent/import parents. Blastoff new snapshots also use this backend; legacy app pairs remain a compatibility reader.

Bak completion is owned by `bak_commands.py`/`bak_completion.py` with shared six-shell adapters. Keep standalone and nested routes synchronized; catalog ID completion must not read payloads or mutate state. Run `tools/test_backup_completion.py` and `tools/test_backup_shell_completion.py` for provider and installed-shell evidence. Follow the shared command/script delivery gate for future backup/link routes.
