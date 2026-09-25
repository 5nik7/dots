# Git and managed file operations

**Status: Implemented; native Termux fixture validation complete, 2026-09-25.**

Implement the approved recursive Git status/publish/sync commands independently of
the file adoption workflow. Port the bounded Git engine with attribution; keep
git-it and bak unchanged. Go remains paused.

File work adds versioned search locations, individual-file adoption by default,
explicit directory links, link and remove/rm, history, undo/recovery, and optional
retained backups. Remove materializes the current config and preserves repository
sources. All filesystem operations share a durable Python transaction engine with
preflight, locks, verified recovery payloads and drift checks. Never test on live
home paths. Backups default off with a machine-local override; rollback protection
is mandatory regardless of that preference.

Git defaults to the dots root, includes registered submodules, and uses independent
owner configuration. Publish is staged-only by default, child-first, confirmed and
non-atomic. Sync is parent-first and pinned by default; initialization requires
explicit --init. Human output uses compact names and relative files; absolute paths
require --full-paths. Preserve data modes and the presentation acceptance gate.

Verification uses disposable repositories/homes and local remotes. Cover failure
and interruption boundaries, drift, ownership, recursive ordering, filenames,
plain/colored/JSON output and static metadata/completion. Update durable command,
safety, architecture, platform and user references with actual results.

## Delivered and verified

### Discovery readability follow-up

Default system discovery now groups candidates by their immediate config directory,
summarizes managed/excluded entries, and retains unavailable entries visibly.
`--verbose` expands files and source mappings; `--all` includes other statuses.
JSON retains the complete schema-1 records independently of human display flags.
Use the shared renderer with terminal-palette path/count accents and semantic
status colors under the [presentation gate](../docs/presentation.md#acceptance-gate).
Prune known cache/session/dependency trees from discovery and adoption; retain
ordinary settings and intentional config assets. Verify fixtures, read-only
behavior, static metadata/completion, 40/80/120 columns, color/icon controls,
control characters, empty results and unchanged JSON. Native desktop validation
remains outside this Termux follow-up.

- [x] Compact/expanded/all views, shared status colors and additional palette accents.
- [x] Cache/session/dependency/preview exclusions with settings and custom assets retained.
- [x] Isolated file-operation (21), inventory (9), and Bash framework (23) tests passed;
  representative 40/80/120-column layouts reviewed. Help/completion, docs links,
  ShellCheck and whitespace checks passed. No live configs were adopted or changed.

### Initial implementation

- [x] Static Git routes, separate ownership config, compact status, recursive
  publish/sync and explicit initialization, with git-it license attribution.
- [x] Versioned discovery registries, including Androidots Termux mappings.
- [x] File-level adoption, explicit directory links, link/remove/rm and snapshots.
- [x] Shared transaction engine, history, drift-safe undo and interrupted recovery.
- [x] Optional retained backups with machine preference and command-line overrides;
  standalone bak and live preferences remain unchanged.
- [x] Presentation/data contracts, static help/completion and synchronized docs.

[Verification](../docs/testing.md#git-and-managed-file-operations) records 75 tests,
lint/docs checks and a repeatable status timing fixture. Nested symlinks/Git
metadata require manual whole-directory materialization; source collisions,
protected theme connectors and drift are refused. No automatic pruning, live
imports, Git commits/pushes or native Windows mutation support was added.
