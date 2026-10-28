# 0002 — Provenance, staged editing and shared source previews

Status: implemented for the 0.1.7 review build; verification is in STATUS.md.
Supersedes exact-match-only identification and the former styled-picker default.
The Python shared-core decision in 0001 remains unchanged.

Use a small version-1 JSON record associated with the normalized active pathname
under canonical storage. Record last-loaded history separately from the current
local save destination and active/source fingerprints. Do not infer overwrite
authority from matching theme bytes. External edits preserve known history while
changing match status. Old backups without applicable provenance restore unknown
origin; new config backups include an optional snapshot.

Content and provenance cannot be committed in one filesystem replacement. Write a
pending marker around content/state publication; an incomplete marker disables
implicit save authority. Report content/state partial failure explicitly. Readers
never repair state and locks are never automatically broken. This is a bounded
failure-detection mechanism, not a general multi-file transaction journal.

Edit a private sibling working copy, not a live symlink or stored source. Back up
before launching, wait for the editor, reread atomic-save replacements, validate
TOML and compare the original fingerprint before publication. Preserve failed edits
at a reported recovery path. Hold cooperating config/storage locks during editing.

Use the existing numeric-ID preview helper for theme/module/backup fzf sessions.
Basic fzf inherits reviewed appearance/navigation settings; fancy styling is opt-in.
Filter executable, auto-selection, output-remapping and persistent-history settings.
Reserve acceptance/cancellation/multi-select/Ctrl-X keys. Use fzf's responsive
alternative layout instead of launching a resize subprocess. Bat/plain source
rendering is optional and bounded. Arbitrary prompt rendering remains excluded:
custom modules/conditions may execute commands, and timeouts are not isolation.

No new runtime dependencies, shell implementations, install interfaces, storage
migration or branding assets are introduced. Native Windows and human visual
verification remain distinct gates, regardless of shared-core test results.

## 0.1.8 follow-up

Presentation/output and PowerShell lifecycle are superseded for 0.1.8 by
[decision 0003](0003-picker-output-and-powershell-lifecycle.md). The provenance,
editing, backup deletion and recovery safety decisions above remain unchanged.

## 0.1.10 list presentation extension

Human theme listing reuses the tracked origin and bounded single-source inspection.
It distinguishes current loaded bytes from modified history, changed local sources
and unknown state. Save destinations remain independent. It neither scans the
library for inferred origins nor changes provenance or the JSON list schema.
