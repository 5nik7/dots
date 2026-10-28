---
name: blastoff-safe-config
description: Implement and verify safe Blastoff theme, module, backup, restore and migration changes. Use whenever a change writes, replaces, deletes or merges TOML files or alters path/lock behavior.
---
# Preserve user configuration

Read `../../../AGENTS.md` and `../../../docs/CLI-CONTRACT.md`.
Resolve storage and active-config paths separately. Honor nonempty overrides
when destinations are absent. Use the shared Python core for all mutations.

Resolve the configured storage root to its existing directory-link target before
building child paths; do not resolve storage children or the active-config leaf.
Validate names and regular files, including remaining symlink/reparse parents and
FIFOs. Root aliases share the canonical operation lock; linked children remain
unsafe write destinations.
Parse TOML; do not use regex-only edits or execute theme commands for validation.
For a module, preserve unrelated values and text; replace the selected table
and descendants only. Refuse unsupported layouts before changing user files.

Stage replacement beside its destination. Back up old bytes first. Retain link
metadata on explicit active-symlink conversion and leave the target untouched.
Refuse collisions and stale locks by default. Compare pre-write fingerprints.
Never silently migrate directories, prune backups or recursively delete prefixes.

Test in temporary roots: valid apply, invalid TOML, collision, permissions,
interruption, backup/restore, changed destination, symlink/FIFO, nested and custom
module tables, multiline strings, unrelated values and unsupported layouts.
Use fault injection to demonstrate original-file survival after a failed commit.
Distinguish per-file atomicity from multi-file crash recovery and malicious races.

Report exact checks, data/recovery guarantees and unsupported layouts. Keep live
user files unchanged unless the user explicitly requests that operation.


For 0.1.8, follow the current CLI contract and RECOVERY.md: dry-run writes nothing,
failed editor work is retained, provenance is independent of matches, and pending
tracking cannot authorize implicit saves. Include backup deletion/module viewing,
Ctrl-X/basic/fancy picker and four-shell completion in relevant reviews. Reconcile
all maintained help/manual/docs/plans and record actual gates before final package
and checksum regeneration. Preserve historical evidence and native Windows deferral.

Human output is the default; JSON must be explicit and diagnostics use stderr.
Use fancy Unicode by default and --fzf for compatible user styling; preserve bat
configuration/cache discovery. Root PowerShell lifecycle shares the ownership
engine; import/static completion starts no tools. Read docs/POWERSHELL.md from
the repository root. Keep step-5 manual acceptance and all native gates truthful.
