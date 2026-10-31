---
name: dots-profile-maintenance
description: Maintain Dots profile manifests, generated path variables, aliases, configuration and native shell maps. Use for profile ownership or environment changes; not for ordinary theme publication.
---

# Dots Profile Maintenance

Read the root agent contract, [profiles](../../../docs/profiles.md),
[environment contract](../../../docs/shell-environment.md) and
[profile backend plan](../../../plans/profile-backend.md). Inspect Git state and
the selected profile before editing. Preserve unrelated changes and submodules.

`profiles.py` resolves definitions and inheritance; `profile_environment.py`
generates paths for every declared profile. `profile_config.py` resolves saved
configuration. Keep these responsibilities shared by all native adapters.
`environment` contains application defaults, never generated Dots path names.
An alias adds a namespace; it neither replaces the canonical namespace nor
inherits into child profiles. Validate all namespaces before emitting assignments.

Keep active `PROFILE*`, canonical `DOTS<PROFILE>*`, aliases and native maps in
sync. Standard paths exist as values even without directories. Only visible
immediate directories add keys. Preserve config/configs aliases, root shared
variables, legacy bridges and PowerShell's built-in `$PROFILE`. Avoid filesystem
creation and inactive profile PATH additions. Do not restore profile `.env` files.

Use [dots-config](../dots-config/SKILL.md) for configuration integration, guarded CLI/popup writes, visual precedence and consumer refresh. Keep colors/icons beside profiles, shared visual defaults under `default`, and user themes/runtime state separate. Record configuration and menu assessments for command changes through [command maintenance](../dots-command-maintenance/SKILL.md).
For file registry changes use [file maintenance](../dots-files-maintenance/SKILL.md).

Test alias conflicts/removal, directory changes, inheritance, literal templates,
reload and checkout switching. Cache inputs include inactive manifests and shallow
directory inventories; warm startup must not launch Python or scan directories.
Run `tools/test_profile_backend.py`, profile/config/menu and affected shell suites
in owned roots, sequentially on Termux. Measure cold/warm startup after changes.
Follow [shell integration](../dots-shell-integration/SKILL.md) and report unavailable
native engines separately. Update canonical docs and regenerate/check the wiki.

Configuration coverage includes foreground/background, nullable icon styles, labels/values, indentation/tab stops, spacing, alignment and native placement where useful. Follow [dots-config](../dots-config/SKILL.md) for typed controls and consumer verification; use [dots-config-audit](../dots-config-audit/SKILL.md) for requested broad discovery. Preserve native ownership and data output, and record a reason for controls deliberately left unchanged.
