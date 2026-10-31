---
name: dots-files-maintenance
description: Maintain Dots core file registry, source ownership, profile mappings and journaled file workflows. Use for catalog schemas, mapping editors, installation, repair or migration.
---

# Dots File Maintenance

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
