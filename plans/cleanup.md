# Cleanup command

Status: implemented and locally verified on Termux (2026-11-12); native
Windows/Linux/WSL acceptance and pre-existing regression failures are recorded
below.

Approved scope: platform-detected `dots cleanup`, Termux rules matching the
previous manual cleanup, per-group approval, private receipts and cumulative
verified totals. `cleanuo` was treated as a typo. The source-of-truth interface
and exclusions are in [Cleanup](../docs/cleanup.md).

## Delivery decisions

- Commands: shared Python controller, generated Bash metadata/wrappers and
  native controller routing. Read-only noninteractive default; explicit
  `run --yes` limited to ordinary groups. No standalone alias.
- Platforms: Termux provider; Linux/WSL/Windows scan/run explicitly unsupported.
  Help, group catalog, history, reports and six-shell completion retain parity.
  Native Windows PowerShell 5.1/7 and native Linux/WSL acceptance remain pending.
- Configuration: **add** `apps.cleanup.checkpoint_min_age_days` (0–36500,
  default 30, next invocation) and family icon. Reuse shared semantic
  foreground/background, nullable icon styles, CLI labels/values, indentation,
  spacing and alignment. No second style store or persistent auto-approval.
- Menu: **add** Cleanup family with ordinary review/scan, catalog, opt-in
  checkpoints, history/report and Config. Selection never approves deletion.
- Installer: **no integration change needed**; core dispatch already delivers
  checkout commands and shared controllers. No service/runtime install.
- Maintenance owner: **add** `dots-cleanup-maintenance`, family index and
  repository skill discovery link for future narrowly scoped rules/platforms.
- Docs: user guide, README, command/schema/safety/platform/configuration/testing
  references, Wiki mapping and generated command reference/manual assessment.

## Acceptance

Use only owned fixture homes/cache/state/PTYs. Cover recursive hidden files,
approved target boundaries, links, ownership/mount refusal, stale review,
process references, unavailable tools, exact counts, hardlinks/sparse files,
partial/interrupted runs, receipt failure/locking and repeat-run totals.
Keep help, completion, JSON, dry runs and history inert. Verify shared/native
metadata and contextual completion for Bash/Zsh/Fish/PowerShell/Nushell/Xonsh.
Check 40/80/120-column human views, plain/light/dark modes, forced decoration
against exact data, config inheritance/reset and family menu actions.

No live cleanup, installation, activation, commit or publication is part of
implementation acceptance. Previously deleted bytes are not seeded into the new
receipt history.

## Verification evidence

- Cleanup: 35 tests, 34 passed and one native hardlink test skipped because this
  Android filesystem forbids hardlink creation. Synthetic hardlink accounting
  and actual sparse-file deletion passed. Real Go/uv binaries were exercised
  only against fixture caches. Directory-swap, process references, stale review,
  lock contention, partial/interrupted deletion and durable totals passed.
- Presentation: owned PTYs at 40/80/120 columns, plain and forced color/icon
  output with light/dark terminal background settings; wrapping, full run IDs,
  literal path controls and exact undecorated JSON passed. Shared progress:
  13 tests passed. This is terminal/fixture evidence, not a native Windows review.
- Config: 15 tests passed, including the new setting's validation, profile
  override, reset to shared default and actual age consumer/flag precedence.
- Commands: Bash 28 tests passed; shared native controller 23 tests with two
  native-runtime skips. Both metadata checks validated 290 commands. Six-shell
  contextual completion, inert help and explicit unsupported-platform routes
  passed. Native PowerShell 5.1/7 execution remains pending.
- Menus: 24 of 27 launcher tests initially passed. Three expected-menu assertions
  needed the new Cleanup family; all three passed on focused rerun. Cleanup's
  action/approval and missing/failed-selector checks passed separately.
- Docs: Wiki 18 tests and Wiki Git 11 tests passed; local build/check is healthy
  (build `ae2fcf3138ec44078cb9e2e2d7b437dc`, final guide refresh
  `ab55475556024e0ea63d8a511ee0b10f`). Generated manual/command
  freshness, skill validation, relative links and `git diff --check` passed.
  Nothing was published or installed.
- Existing failures: alignment suite has two failures and one error from its
  old rounded-border/four-space assumptions; committed defaults use sharp/two.
  Manual suite has one existing foreign-link blocking assertion failure
  (`ManagedManual.test_unowned_correct_link_foreign_link_and_owned_drift`).
  All four reproduced in a temporary archive of unchanged `HEAD`. Manual
  generation/coverage/lint and the other eight manual tests passed. These
  unrelated behaviors were not changed by cleanup implementation.

Controller parity and fixture checks do not imply cleanup support outside
Termux. Adding another platform remains explicit provider work under the
maintenance skill. Live-user cleanup and physical terminal review remain user
actions; no actual cache/history deletion was performed for acceptance.
