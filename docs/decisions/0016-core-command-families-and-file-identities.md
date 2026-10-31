# 0016: Core command families and recoverable file identities

**Status: Accepted, 2026-10-30.**

The owner requested one theme family and one profile family. This supersedes
only decision 0013's separation of theme collection routes. First-party plural
routes are removed, with their actions under `theme` and `profile`. Bare commands
retain summaries; `profile list` lists definitions and `profile check --all`
validates all definitions. Help, completion and launcher menus use these routes.

Config starts with List/Get/Set. List and Get are read-only; Get/Set choose a
category before rows. Empty terminal get/set calls use that guided flow, while
explicit and data invocations retain their contracts.

File identities may change explicitly through `files edit OWNER:OLD --id NEW`.
One retained transaction updates registry identity, every explicit profile
mapping and replacement reference, current installation receipt identities, and
any requested live edits. Additional mapping fields affect only the selected
profile; live apply requires the active profile. Source ownership never changes.

Schema 3 adds flattened old-to-current identity history to the core registry.
Schema 2 remains readable and upgrades only on an effective rename. Old IDs stay
reserved, commands require the current ID, and receipt readers resolve historical
IDs without rewriting old journals or accessing another platform's state store.
Undo restores the registry, mappings and receipt changes with normal drift
checks and retained installation baselines.

See [file contracts](../files.md#file-id-renames),
[configuration](../profiles.md#configuration-popup) and the
[implementation plan](../../plans/core-updates.md).
