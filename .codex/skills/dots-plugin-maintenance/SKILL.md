---
name: dots-plugin-maintenance
description: Maintain first-party Dots application plugins, portable runtime paths, installation assets and legacy migration. Use for Anodize, Blastoff, pkgs or another application absorbed into Dots; not theme hooks or editor plugins.
---

# Dots Plugin Maintenance

Read [application plugin ownership](../../../docs/plugins.md), the selected plugin's local instructions, and the task's focused plan. Keep application-specific code/assets in its plugin and shared Dots services in the core. Preserve standalone and Dots-prefixed command/data contracts. Resolve code from the checkout, not the caller's current directory or an old installed copy.

The plugin manifest owns relative runtime/manual/completion paths and provenance. Application grammars own command metadata. Update their generators and native adapters together; no plugin scans or application execution during ordinary dispatch, help or shell startup. Preserve stable build/test entry points and keep ignored build output out of Git.

For installation changes, use the existing installer receipt and Store. Audit old command resolution, known installer layouts, receipts, completion loaders and startup references. A receipt supplies candidates, not unrestricted mutation authority: constrain paths, verify expected content and guard preview inputs. Never run an old uninstaller to remove overlapping ownership. Preserve unknown/edited files, existing backups, configuration, themes and caches. Source maintenance alone does not authorize live migration; honor the user's existing authorization without requesting it again.

Use [command maintenance](../dots-command-maintenance/SKILL.md), including a recorded add/update/no-menu assessment. Reuse [menu authoring](../dots-menu-authoring/SKILL.md) when a workflow benefits from a picker; do not generate menus automatically from every subcommand.

Verify relocation, both command forms, all three installed asset sets, no-op repeat setup, baseline restoration, drift, rollback and inert metadata using isolated roots. Migration tests use synthetic legacy receipts and never target host packages. Run relevant plugin core suites and shared tests; report actual native evidence separately. Follow [documentation maintenance](../dots-documentation-maintenance/SKILL.md) for canonical sources and wiki synchronization.
