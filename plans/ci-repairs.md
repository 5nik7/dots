# GitHub workflow repairs

**Status: Implemented locally; native GitHub acceptance pending.**

Repair checkout installation, worktree lifecycle and native command failures reported for `4b9d36c`. Retain the Linux/Windows installation and worktree jobs and optional-submodule checkout policy.

## Changes

- Pin parent-document links to the recorded public Androidots revision so docs
  checks work without initialized submodules.
- Untrack and ignore the machine-local Bat theme connector while retaining the
  owner's local link.
- Flush copied file payloads through writable handles before closing them,
  preserving read-only metadata without changing the source. Native inactive
  theme preparation uses the same platform flushing boundary.
- Share text preparation between installation receipt prediction and publication,
  including preserved target modes, UTF-8 and LF. Retain permission-sensitive
  drift refusal and original backups.
- Establish the stale Git tracking ref explicitly in disposable worktree tests.
  Permit only named PowerShell runtime caches in read-only command fixtures.

## Verification and acceptance

Run native file-durability, installation, adapter, worktree, native CLI/Anodize/Git
and transaction regressions sequentially in owned roots. Test read-only copies,
flush failure before replacement, undo and drift, plus theme reconciliation and
uninstall under POSIX umasks `022` and `077`. Run `python3 -B tools/verify_docs.py` and its regression suite against parent-only fixtures and check whitespace.

Both Bash and native PowerShell use the repaired shared transaction code. Windows
app destinations and public command/data interfaces are unchanged. The existing
[presentation gate](README.md#presentation-gate-for-every-plan) applies; no new
human view or visual styling is introduced. Existing adapter tests retain plain,
colored and JSON checks.

Native Ubuntu, Windows PowerShell 5.1 and PowerShell 7 workflow acceptance requires
the repaired revision to be published and all jobs to finish successfully. Local
Termux checks do not establish Windows or WSL runtime support. No live setup,
theme activation, submodule initialization, commit or push belongs to this repair.

## Evidence

Local Termux verification on 2026-10-24:

- File durability: 5 passed. Installation: 24 passed, including both umasks and
  the parent-only fresh-checkout fixture.
- Installation adapters: 9 run, 4 capability skips, no failures. Native CLI:
  14 run, 1 PowerShell availability skip, no failures. Native Anodize: 3 passed
  using the existing prebuilt engine.
- File operations: 21 passed. Native Git controller: 24 passed. Catalog: 9 passed.
  File mappings: 28 passed.
- Documentation checks passed against disposable parent-only trees with Unix symlinks and simulated Windows link-text files. The standalone checker retains regression coverage for both layouts.
- The stale-ref worktree regression passed. The suite's active-process case
  reported `process inspection uncertainty` on this Termux host. Running the
  unmodified test and helper exported from `4b9d36c` reproduced the same failure.
  That initial run had 16 passes, 1 host failure and 1 native-removal capability skip. A later complete rerun passed all 17 available cases with 1 capability skip; the active-process case passed without further code changes. The helper's conservative refusal behavior was not weakened.
- Theme workflows: 27 run, 1 optional skip, no failures. PowerShell startup:
  all 21 cases skipped because no engine is installed locally; this is not native
  runtime evidence. Native Windows/PowerShell workflow results remain pending
  publication; no live setup or publication ran.
- Python syntax, tracked-link portability and staged/unstaged whitespace checks
  passed. The ignored Bat connector still resolves locally; only its tracked
  removal is staged. No commits or pushes were made.

Final local regression pass on 2026-10-24:

- Standalone documentation checker: 4 regression tests passed and 666 relative links in 106 files passed in the working checkout and both parent-only layouts (native symlinks and Windows-style link text).
- Anodize build-environment isolation: 2 tests passed. A fresh offline engine build, Go package tests and vet passed, followed by 18 CLI, 11 interactive (1 optional skip) and 15 logo tests.
- Bash dispatcher: 24 passed. Native CLI: 14 run with 1 PowerShell availability skip. Installation adapters: 9 run with 4 capability skips. Worktree lifecycle: 18 run with 1 native-removal capability skip, no failures.
- Changed Python syntax, workflow YAML, workflow-local entry points and relative Markdown anchors passed review. Native Windows and hosted GitHub acceptance still require publication.
