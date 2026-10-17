# Stash and edit file mappings

The earlier Git XDG overlay rollout below is historical. The [consolidated Git follow-up](git-theme-template.md) supersedes its Androidots mapping and home-overlay layout.

**Status: Implemented and verified, 2026-10-16.**

Owner-approved scope: repository-wide `enabled` state; stash unlinks only matching
links and retains source/catalog metadata; restore re-enables and relinks. Edit
existing or explicitly new source/target mappings, metadata-only by default and
with transactional live reconciliation under `--apply`. Both commands have
interactive review, dry-run, yes, JSON, shared resource presentation and progress.

Use the existing catalog, native adapter, Store and installation receipt. Preserve
first-install baselines when unlinking or relocating receipt-owned targets. Guard
metadata, sources, targets and receipts; refuse conflicts and observed drift;
retain undo and interrupted reverse recovery. Disabled entries remain visible,
do not claim destinations and cannot be reinstalled by setup, link or track update.

Also perform the authorized Git migration after fixture verification: common
`config/git` -> `${CONFIG}/git`, recognized `config` entry point including common
`gitconfig` and optional `~/.config/git-termux/config`; retarget the Android Git resource
to the latter, preserve its settings, remove its obsolete include and the old
matching `~/.gitconfig` link. Journal the migration and preserve nested Git work.

Acceptance: owned fixtures for stash/restore, new/edit, selection/cancellation,
dry-run/JSON, conflicts, inactive platforms, missing/broken links, original backup
retention, repeated operations, rollback/undo/recovery and drift. Exercise
installation/discovery/link integration, native-adapter routing, three-shell
completion and 40/80/120-column presentation. Record native versus skipped tests
and live Git verification without printing configuration values.

Native fixture discovery: a relative `../git-termux/config` include traverses the
directory symlink into the repository and misses the home overlay. The migration
therefore uses `~/.config/git-termux/config` and refuses custom XDG roots. Generic
mapping commands continue supporting custom XDG roots. Shared Git source settings
and Android overrides are compared privately against standard global loading;
failed validation triggers guarded undo.

## Verification and rollout

- Mapping/migration coverage: 26 cases passed across the 25-case suite and focused
  reruns, including cross-platform restore conflicts, historical receipt links,
  source permissions, Git loading and automatic undo on validation failure.
- Shared suites passed: catalog 9, operations 21, installation 16 (plus focused
  receipt reruns), browser 17, confirmations 8, progress 11, resources 11,
  dispatcher 24 and missing-source checks 16. One focused native Zsh completion
  cache test also passed; dispatcher coverage includes native shell completion.
- Adapter suite: 5 passed, 4 skipped for unavailable PowerShell/Windows runtimes.
  Native Windows execution is unverified; no dependency or privilege changes.
- Owned PTYs passed at 40/80/120 columns, including cancellation, delayed progress,
  plain output and dry-run output without animation. JSON stays undecorated.
- Python syntax, wrapper ShellCheck, 84-command metadata validation, relative
  documentation links and parent/Androidots `git diff --check` passed.

The approved live Git migration completed in seven guarded operations with retained
snapshots, transaction `7270ea55c3e248f5bb729e02829a2116`. Both catalog resources
report linked; `~/.config/git` and `~/.config/git-termux/config` resolve to their
intended sources, and `~/.gitconfig` is absent. Standard Git global settings match
the common settings plus unchanged Android override values, compared privately.
Use `dots files undo 7270ea55c3e248f5bb729e02829a2116` for guarded reversal.

No commit or push was performed. Existing parent/nested changes remain preserved;
the scoped Androidots catalog, Git source and README changes remain uncommitted.
