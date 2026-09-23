# Files catalog

**Status: Implemented; isolated verification recorded in docs/testing.md**

- [x] Bash routes with a standard-library Python backend.
- [x] Per-repository versioned catalogs; explicit Androidots Termux composition.
- [x] Discover, track metadata, classify, locate, list and inspect without installing files.
- [x] Test isolation, collisions, optional sources, atomic updates and structured output.

Go implementation remains paused. No commits, pushes, package installation or live theme/wallpaper activation are included. Existing user changes and independent submodule histories are preserved.

The contract is in [docs/files.md](../docs/files.md). Sorting and categories are
metadata/views; no source files are moved. Future `add`, `remove`, `set` (links by
default), `edit`, adoption and undo require a separate installation plan.
