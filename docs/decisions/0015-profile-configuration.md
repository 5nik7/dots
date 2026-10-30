# 0015: Checkout-local profile configuration

**Status: Accepted.**

## Context

Environment declarations already belong to platform profiles, while Dots settings, file mapping edits and format-specific preferences used separate user-directory files. That split made it difficult to keep a platform's desired configuration together or edit it consistently through the CLI.

## Decision

Extend the existing `profile.json` with validated `settings` and repository-scoped `files` resource lists. Preserve the existing profile inheritance order, literal environment templates, file resource identities and source ownership. Each base profile contains its applicable shared inventory in `files.dots`. Independent and older checkouts may still use legacy catalogs. A profile list replaces the corresponding repository list as a unit; ordinary file editors save resolved lists into the active profile.

Keep format-specific files beside the profile manifest and resolve the most specific existing input. User-authored themes and runtime state remain in their existing platform directories. Add `dots config` for inspection, literal edits and explicit migration through the existing transaction Store. Preserve legacy reads to support a deliberate migration and independent older checkouts. Saving configuration does not activate shells, install mappings or publish themes.

## Consequences

Each platform can evolve configuration without modifying another platform's overrides. Full-list file overrides deliberately stop inheriting later changes to that repository's default list; remove a child override to resume parent inheritance. The permanent schema-2 root registry retains qualified IDs and platforms. Profiles retain implementation mappings without platforms or target maps; a registry identity alone never installs. Writable tests must own their checkout as well as user/state roots. Profile configuration can contain machine-specific data and must be reviewed before publication. Migration retains recovery data and protects the user's theme directory. Native Windows/WSL state and destination semantics remain separate.

The implemented contract and examples live in [profiles](../profiles.md#profile-configuration); verification and remaining native acceptance are recorded in [the focused plan](../../plans/profile-configs.md).

The approved refinement generates profile paths and native maps centrally, with canonical prefixes and optional non-inherited aliases. Application `environment` declarations remain separate. See [the implementation plan](../../plans/profile-backend.md).
