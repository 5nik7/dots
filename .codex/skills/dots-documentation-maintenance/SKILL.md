---
name: dots-documentation-maintenance
description: Maintain canonical Dots documentation when commands, configuration, platform support or workflows change. Verify implementation claims and refresh the generated wiki when available.
---

# Dots Documentation Maintenance

Read [the documentation guide](../../../agents/guides/documentation.md) and the affected source-of-truth references. Check the actual implementation, static command metadata and relevant tests before changing claims or examples. Preserve implemented/proposed distinctions and native-platform evidence limits.

Update authoritative prose in the same change as behavior; do not create a competing exhaustive reference. Add or adjust wiki page mappings for new top-level documents. Use [wiki maintenance](../dots-wiki-maintenance/SKILL.md) to regenerate and check the local export when present. If unavailable, run source-only checks and report synchronization pending. Structural checks do not prove prose accuracy; review the affected examples and statements.

For accompanying command changes, verify the recorded [configuration review](../../../agents/guides/commands.md#configuration-integration-review), menu assessment and [family owner](../../README.md#command-family-owners). Configuration integrations use [dots-config](../dots-config/SKILL.md); update existing catalogs and references instead of inventing a documentation-only registry. Skill changes must keep the index, discovery links and affected cross-links current. Pure documentation upkeep does not require new settings or reviews of unchanged commands.

Run relative-link and affected command checks. Keep unrelated changes intact and report any deferred documentation. Ordinary documentation work does not authorize commits, pushes, automatic cloning or live configuration changes.
