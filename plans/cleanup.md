# Cleanup command

The [Overkill follow-up](overkill-parity.md) implements home-bounded Linux/WSL cache/log providers and bounded Windows cache/log deletion. Native Windows handle/ACL/accounting fixtures pass; actual Restart Manager integration and live cleanup acceptance remain pending. Windows custom cache roots, build caches and checkpoint providers remain missing implementation. Existing historical Termux evidence below is retained with its original scope. No live cleanup was run for this follow-up.

Status: implemented with platform-specific evidence and pending gates recorded below. The original Termux delivery was locally verified on 2026-11-12; its historical failures and exclusions have not been rewritten as current native results.

## Windows provider follow-up (2026-11-14)

Implementation and tests ran against the uncommitted Windows checkout changes on `main` at base revision `800988ea331c132f29eaf5b645a00b068e38c96a`. The WSL regression run used an owned snapshot of the updated public sources; it did not update the user's WSL checkout. These are source/fixture results, not a live cleanup or a published revision.

- **Implemented:** existing `downloads` and `logs` routes use default npm/pip cache contents and named Neovim logs under home-bounded LocalAppData. The group catalog marks these groups as implemented for scan/run. Windows build/checkpoint groups and custom cache paths remain unsupported.
- **Native deletion gates:** local NTFS; exact current owner; bounded ACL principals; no reparse points, foreign volume, read-only/system/offline objects or pre-existing hardlinks; at most 50,000 group entries. Whole-group exclusive handles and ancestor pins precede exact handle disposition. No permission repair, POSIX deletion, recursive fallback or application termination occurs.
- **Process boundary:** a bounded Restart Manager child query runs only after explicit approval and receipt creation. The first query includes the invoking process; subsequent checks distinguish its own pins. Query failure, timeout, unknown references or reboot requirements retain the group. Actual Restart Manager API integration is still pending; its API and child-result paths were exercised with fixtures.
- **Receipts:** existing schema-1 reports, state root and public history/report contracts remain. Windows adds protected owner/SYSTEM ACLs, an exclusive lock and flushed append-only `RUN_ID.jsonl` snapshots. Legacy `.json` reads remain; duplicate identities refuse. A torn trailing snapshot leaves the last complete snapshot's conservative totals and an incomplete status. A failed append is not retried, unrecorded removals receive no credit, and the 16 MiB bound has no automatic retention policy.
- **Native evidence:** `python -B tools/test_cleanup.py` ran 55 tests: 18 passed and 37 POSIX-only tests skipped. Owned Windows fixtures cover exact file/directory deletion, repeated no-op, active readers, mapped files, a child working directory, denied replacement/writes while pinned, ACL drift, reparse refusal, receipt locks/legacy records/duplicates, interrupted tails, failed receipt writes, partial subtotals, sparse allocation and multi-buffer native directory enumeration. No real cache, registry, service, clipboard or desktop was used as a fixture; Restart Manager and process-provider queries were replaced.
- **WSL evidence:** the same 55-test suite passed in an owned Ubuntu WSL source snapshot: 40 executed and 15 Windows-only tests skipped. This covers retained POSIX engine behavior; it does not establish today's Termux acceptance or unmodified live WSL cache eligibility.
- **Pending acceptance:** real Restart Manager registration/enumeration and failure behavior against reviewed owned fixtures; separately approved native live cache/ACL review and cleanup; Termux regression on the phone for the shared engine/storage dispatch. Host ACLs can legitimately refuse a run even when scanning succeeds. Build/checkpoint/custom-location providers remain separate work.
- **Delivery assessment:** **no configuration integration change needed** because the adapter reuses existing group selection, preferences, confirmation and presentation. **No menu change needed** because existing review/scan/history/report actions already reach the provider and never grant deletion approval. Routes, flags, shell completion grammar and public report schema are unchanged. Native PowerShell 5.1/7 and Bash share the controller; native Win32 filesystem evidence is separate from shell dispatch evidence. Core installation already delivers the new Python adapter; no service or package dependency was added.
- **Rollback:** source edits can be reverted separately from irreversible cleanup. Retain the JSONL-capable receipt reader after any native Windows run until an explicit preservation/migration decision is made. No rollback restores deleted cache/log payloads, and no receipt is automatically replayed. Documentation/wiki integration and publication remain lead-coordinated.

The first bounded Windows stage provided read-only inventory. This follow-up supplies removal and private receipts without treating the earlier scan pass as deletion evidence. Human views retain the shared [presentation acceptance gate](README.md#presentation-gate-for-every-plan); this provider change adds no layout and does not claim new physical-terminal or desktop acceptance.

## Original Termux delivery (2026-11-12)

Approved scope: platform-detected `dots cleanup`, Termux rules matching the
previous manual cleanup, per-group approval, private receipts and cumulative
verified totals. `cleanuo` was treated as a typo. The source-of-truth interface
and exclusions are in [Cleanup](../docs/cleanup.md).

### Delivery decisions

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

### Acceptance

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

### Verification evidence

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

At that original delivery, controller parity and fixtures did not establish cleanup support outside Termux. The explicit provider work and newer evidence above supersede that support limit without changing the dated results. Live-user cleanup and physical terminal review remain separate actions; no actual cache/history deletion was performed for that acceptance.
