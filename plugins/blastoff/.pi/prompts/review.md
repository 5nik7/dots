---
description: Review Blastoff changes against the command and safety contracts
argument-hint: "[focus]"
---
Read AGENTS.md and the CLI contract. Review current changes for ${@:-data safety, Bash/PowerShell parity, dependency footprint, performance and documentation consistency}. Inspect actual diffs and run relevant isolated checks. Identify concrete triggers and consequences with file references. Distinguish bugs from unsupported behavior documented in the contract. Preserve unrelated changes. Make routine reversible fixes supported by the current task, then recheck. Report unchecked native-platform/interactive gates; do not claim an unrun check passed.


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
