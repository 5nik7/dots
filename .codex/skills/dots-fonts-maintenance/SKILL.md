---
name: dots-fonts-maintenance
description: Maintain dots fonts catalogs, retained versions, installed inventory, application targets and pickers. Use for font-management implementation; ordinary theme publication and system-wide font administration are separate workflows.
---

# Dots Fonts Maintenance

Read [fonts](../../../docs/fonts.md), [font transaction safety](../../../docs/safety.md#personal-font-transactions) and the [font plan](../../../plans/fonts.md). `lib/dots/fonts/commands.py` owns the grammar; model/providers and directories own identities/storage, inventory owns installed discovery, operations/actions own changes, and config/destinations own native targets. Keep downloaded, retained, installed and selected identities distinct.

Directory install/update is storage-only. Explicit Set/use targets activate from the personal library, retain exact payloads in the active profile and save `fonts.json` preferences in the same guarded transaction. Termux retains the chosen TTF; desktop targets retain the selected variant's styles. An unchanged legacy target may still require retention/preference backfill without rewriting active bytes. Restore uses exact saved versions/hashes, not implicit upgrades.

Copy preserves originals; Migrate requires proven user ownership and keeps registration/lookup paths usable. System/package/uncertain fonts are copy-only. Stage and validate downloads before review/apply; reject unsafe archives, links, collisions and drift. Keep partial-family accumulation, pins, prior selections and recovery history. Native Windows uses its user-font/HKCU adapter; never translate WSL paths or adopt missing app configs automatically. No inventory/provider scans during help, completion or startup.

Follow [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu assessments, [dots-config](../dots-config/SKILL.md) for configuration exposure and [menu authoring](../dots-menu-authoring/SKILL.md) for picker changes. Fonts' native settings and retained preferences keep their existing owners.

Select `tools/test_fonts.py`, `tools/test_font_directories.py`, `tools/test_font_workflows.py` and `tools/test_fonts_browser.py` by changed boundary; use `python3 -B tools/generate_fonts_commands.py --check` for metadata. Tests own payloads, roots, network substitutes and native registration substitutes. Verify preservation, partial retention, stale inputs, failed downloads, rollback/undo, idempotence and unavailable consumers. Real device/Windows activation is separate evidence. Finish through [documentation maintenance](../dots-documentation-maintenance/SKILL.md).

Display work also uses `tools/test_fonts_presentation.py`. Fonts reports bind shared
CLI rendering in `fonts/presentation.py`; selectors bind shared menu spans. Keep
`apps.fonts` controls, nullable `colors.fonts.*` roles, Config discovery/activation
and menu links synchronized. Render preview metadata at the actual pane width.
Use render-local preference snapshots for large catalogs; preserve plain captured
human layout via `DOTS_MENU_CAPTURE` and exact redirected/JSON/path/glyph output.
