# Shared Git theme colors

Status: completed, 2026-10-16.

## Accepted scope

Add the sibling `git` style group through existing defaults, overrides, queries, edits, exports and publication. Apply it to Dots Git status/sync/publish metadata, preserving independent type/MIME filenames, plain wording and JSON contracts. The owner authorized refreshing the current selection after isolated verification. Prompts, native Git configuration and editor integrations are out of scope.

## Implementation and acceptance

- [x] Add palette-relative defaults and additive schema-1 exports; preserve file matching and LS_COLORS.
- [x] Publish a separate bounded data projection with lazy Bash consumption and older-generation fallbacks.
- [x] Apply roles through shared presentation helpers and Git renderers; preserve existing dirty work.
- [x] Synchronize [style defaults and interfaces](../docs/file-colors.md#git-styles), [Git behavior](../docs/git.md#theme-colors) and [projection ownership](../docs/themes.md#cli-git-style-projection).
- [x] Pass isolated rule/publication, resources, Git operation and completion checks.
- [x] Review 40/80/120-column native PTYs, dark/light colors, long Unicode identities, plain output and JSON bytes under the [presentation acceptance gate](../docs/presentation.md#acceptance-gate).
- [x] Refresh the existing live selection and verify read-only Git output.

## Verification record

Verified on native Termux:

- File-color suite: 9 cases passed, followed by the additional dark/light publication and native-render case (10 cases total). Shared/per-theme edits, old snapshots, scalar formats, JSON/Lua, unchanged LS_COLORS and all three completion providers passed.
- Resource suite: 11 cases passed. Git style coverage: all 6 cases passed, including actual added/deleted/renamed files, conflict/blocked handling, malformed projections, cached reads, independent status/path colors, tracking and sync/publish output.
- Existing Git operations: all 27 cases passed; the two status/presentation cases also passed with explicitly isolated XDG state/data/cache roots.
- Theme publication: atomicity/idempotence, failed-publication rollback and published-snapshot independence passed (3 cases). Theme command suite (12) and Bash dispatcher suite (24) passed.
- Native 40/80/120-column PTYs covered long Unicode identity/resource rows and destination-stream color policy. Actual published Catppuccin Mocha and Latte colors were consumed by the Git renderer at all three widths. Generic pre-existing summary lines were not redesigned.
- Scoped ShellCheck passed with the repository's SC1091/SC1003 exclusions. Shell syntax, whitespace and relative Markdown links passed.
- Authorized live refresh retained `catppuccin-mocha`, publishing generation `g.XRSiWAOn` with all 17 Git roles. Live status across seven repositories completed successfully, used the published identity/branch styles, and retained undecorated schema-1 JSON.

Existing discovery reports unmerged indexes as blocked before enumerating file statuses; this behavior remains unchanged. Native blocked output and the explicit conflict renderer boundary were both checked. Native Windows Git support remains outside this Bash-only slice. No commit, push, theme-selection change or unrelated cleanup was performed.
