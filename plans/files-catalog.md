# Files catalog

**Status: Implemented; isolated verification recorded in docs/testing.md**

- [x] Bash routes with a standard-library Python backend.
- [x] Per-repository versioned catalogs; explicit Androidots Termux composition.
- [x] Discover, track metadata, classify, locate, list and inspect without installing files.
- [x] Test isolation, collisions, optional sources, atomic updates and structured output.

Go implementation remains paused. No commits, pushes, package installation or live theme/wallpaper activation are included. Existing user changes and independent submodule histories are preserved.

The contract is in [docs/files.md](../docs/files.md). Sorting and categories are
metadata/views; no source files are moved. The approved [Git and file operations plan](git-and-file-operations.md) now adds bounded add/link/remove, adoption, undo and recovery. Editing and general profile installation remain deferred.

## Terminal presentation follow-up (2026-09-24)

Implemented colored human output using the dispatcher's color/icon policy, static
subcommand menus and terminal-aware layouts. Plain pipelines, JSON, scalar/path
queries, initialization and completion retain their data contracts. Validation is
recorded in [testing](../docs/testing.md#terminal-presentation).

## Presentation Acceptance for Follow-up Work

Future inventory and installation slices must meet the [presentation contract](../docs/presentation.md) and its acceptance gate. Preserve the current JSON, TSV and raw-path interfaces; keep Python presentation policy aligned with Bash. Use consistent Source, Target, Repository and Status fields across Dots and submodule resources. Bounded add/link/remove and undo/recovery flows are implemented under the [Git and file operations plan](git-and-file-operations.md). Further set/edit and general profile installation remain deferred; their future plans must cover preview, conflict, partial failure and recovery views.
