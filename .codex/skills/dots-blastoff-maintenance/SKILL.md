---
name: dots-blastoff-maintenance
description: Maintain the bundled Blastoff command family for Starship themes, modules, edits and backups. Use for dots blastoff or shared standalone behavior; use plugin maintenance for Dots installation and legacy migration.
---

# Dots Blastoff Maintenance

Read the plugin's [agent contract](../../../plugins/blastoff/AGENTS.md), [CLI contract](../../../plugins/blastoff/docs/CLI-CONTRACT.md), [recovery guide](../../../plugins/blastoff/docs/RECOVERY.md) and [Dots integration](../../../docs/bundled-applications.md). `plugins/blastoff/lib/cli.py` and `operations.py` own application behavior; `active_config.py`, `editor.py`, `provenance.py` and `backups.py` own distinct safety/state boundaries. Both command forms must retain the same arguments, output and exit status.

Respect nonempty `STARSHIP_CONFIG` even when its target is absent; otherwise use the documented default. `BLASTOFF_HOME` changes storage, not the active config. Validate TOML structurally, retain unrelated fields, and preserve active-file symlink chains with locks and guarded atomic target replacement. Only explicit `--replace-link` replaces a link itself. Storage-root aliases share canonical locking; unsafe children and stale/foreign locks remain protected. Retain failed editor output and distinguish recorded provenance from an exact content match.

Application writes use Blastoff's own backups/locks. [Plugin maintenance](../dots-plugin-maintenance/SKILL.md) owns Dots asset installation and legacy migration; do not claim package-wide Store rollback for application actions. Theme validation never renders a real Starship prompt or runs custom module commands. Dry runs/help/doctor/list/completion must not create state. Explicit backup deletion remains permanent for its selected pairs.

Use [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu review and [dots-config](../dots-config/SKILL.md) for Dots integration, preserving native application setting ownership. Run affected plugin-local tests under its documented contract, `tools/test_bundled_apps.py`, `tools/test_bundled_app_cores.py` and `tools/test_plugin_reports.py` as applicable. Check generated grammar adapters with `python3 -B tools/generate_bundled_apps.py --check`. Fixtures own Starship/Blastoff paths; native PowerShell evidence is separate. Synchronize source docs through [documentation maintenance](../dots-documentation-maintenance/SKILL.md); imported release checksums do not describe the Dots checkout.
