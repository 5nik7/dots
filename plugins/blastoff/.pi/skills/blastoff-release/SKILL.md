---
name: blastoff-release
description: Check Blastoff release readiness, checksums, version consistency, installation and uninstall recovery. Use before packaging, version bumps, release review or lifecycle changes.
---
# Verify a reviewable release

Read `../../../docs/IMPLEMENTATION-PLAN.md`, `STATUS.md` and
`INSTALLATION.md` from that docs directory. Inspect repository status/remotes.
Keep core version, VERSION, PowerShell manifest, man page and changelog aligned.
Verify source ownership and preserve the actual repository license.

Run isolated core/lifecycle tests and available shell/manual checks.
Run native Termux and native Windows wrapper/filesystem checks independently.
Retain pending gates; never claim fixtures, syntax or cross-builds prove them.
Review performance measurements and host-specific budgets.

Verify `--dry-run`, unowned/modified-file refusal, versioned payload integrity,
interrupted operation recovery and uninstall retention of themes/modules/backups,
active config, shell profiles and unrelated prefix files. Never use a live
installation prefix for tests.

Update help, manual, completions, changelog, contract and evidence for changed
behavior first. Then run `../../../scripts/package.py`, followed by `verify.py`
in the same scripts directory. Verify final archives and outer SHA-256 sums;
rebuild after any later source or documentation edit.

Deliver readiness findings and exact unresolved gates. Do not install into the
user's real prefix, commit/push, move tags or publish unless explicitly requested.


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
