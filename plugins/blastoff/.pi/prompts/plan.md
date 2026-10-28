---
description: Plan a bounded Blastoff implementation slice
argument-hint: "[task]"
---
Load the blastoff-plan skill and repository AGENTS.md. Plan ${@:-the next incomplete slice in docs/IMPLEMENTATION-PLAN.md}. Inspect the actual repo and prior status first. Record the behavior, affected paths, acceptance cases, safety/recovery and native-platform gates. Do useful read-only work now. Ask only for decisions that block safe progress. Do not modify live config, install, edit profiles or publish during this planning request.


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
