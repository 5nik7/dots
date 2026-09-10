# Bounded Development Worktree Lifecycle

Status: Implemented; focused native CI pending delivery (2026-09-10).

Use one `chore/worktree-lifecycle` worktree from fetched `origin/main`; preserve the original checkout's HEAD/logo/index, every branch/recovery ref and retained evidence. This is local development maintenance, not a public dots command or managed-dotfile operation.

Implement a preview-default Python helper, explicit registration tied to Git worktree identity, and apply gated by fresh nonrecursive fetch, merge ancestry, complete local-file inspection, protected original/session/helper paths, known live references and conclusive process inspection. Require the calling agent to review idle sessions and text-based live-configuration references that OS process checks cannot discover; no override may bypass a detected hazard. Unknown eligibility is a skip. Use only non-force `git worktree remove` and retain all branch refs. Do not create backup archives or install automation.

Document one-worktree capacity, exact authorized-maintenance/implementation triggers, read-only planning previews, and loading current policy when the original checkout is older. Test in disposable Git repositories with isolated environment roots. Add a focused development-tooling CI gate; preserve existing native core/experiment gates. No executable product behavior or performance path changes; do not rerun runtime benchmarks for this tooling task.

- [x] Helper and isolated refusal/removal tests.
- [x] Policy/agent guide and reference updates.
- [ ] Focused checks, preservation audit, explicit feature push and CI inspection.
- [ ] PR or prepared comparison fallback; retain current worktree until a later eligible boundary after merge.

## Local Results

`python3 -B tools/test_worktree_lifecycle.py` passed all 14 tests on native Termux with no skips, including real process detection and eligible removal in an owned disposable repository. `python3 -B tools/verify_core.py docs` passed 161 relative links in 29 files; whitespace checks passed. No Go runtime, benchmark, package or installation work was needed. The separate lifecycle CI gate runs these focused tests on Linux/Windows without changing existing CLI gates. Windows removal remains fail-closed because there is no native process inspector; its symlink test may be skipped rather than enabling privileges.

The single task worktree is `$HOME/repos/dots-worktree-lifecycle` on `chore/worktree-lifecycle`, based on merged catalog revision `7d84f3d`. It is explicitly registered in Git-local maintenance metadata. Actual preview reports it protected as the session/helper worktree and reports the original as unmanaged; no real checkout is removed in this implementation task. The original HEAD, logo and exact index bytes are preserved. Evidence and prepared delivery material are retained under `$HOME/dots-review-evidence/worktree-lifecycle-ru4dokwn/`; final commit/CI/PR status belongs in delivery evidence without relabeling earlier checks.

Future sessions starting from the old original HEAD must explicitly load the fetched policy/helper as the guide describes. This task does not install the policy into that checkout, a Codex global instruction file, hooks or scheduled services. After merge, a later authorized session from outside this worktree can review active/live references and clean it; this session cannot remove itself.

## CI Finding and Correction

The first focused Linux run found same-account process-inspection permission restrictions before the test child was visited. The helper correctly refused cleanup, but returned uncertainty before identifying the known active child, so the native detection assertion failed. The inspector now continues after recording permission uncertainty: a definite active reference takes precedence; absent one, any recorded uncertainty still blocks removal. No eligibility rule or assertion was relaxed. Native positive removal is explicitly unavailable on a host with denied inspection. Matrix fail-fast is disabled so Linux findings do not cancel Windows coverage. The original failed log is retained with its commit identity.
