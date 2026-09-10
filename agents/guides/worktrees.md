# Development Worktree Lifecycle

This guide governs local development tooling, separate from the public `dots` CLI. Read it before creating, registering or cleaning development worktrees. The owner authorized automatic eligible cleanup during maintenance and implementation workflows; a fresh approval question is not required for each eligible managed worktree. Explicit task constraints still take precedence.

## Capacity and Triggers

Keep at most one active development worktree alongside the original checkout. Run `git worktree list --porcelain` and inspect every existing worktree before creating another. Reuse the existing worktree only when its branch and outstanding work match the authorized task. If it is active, dirty, unmerged, unmanaged or uncertain, report the blocker and do not create a second worktree. Registration enforces this capacity; Git itself is not intercepted.

At the start of authorized implementation or maintenance, and after verifying a merge, inspect managed cleanup candidates. Remove eligible candidates automatically after the checks below. A worktree containing the current session or executing helper is protected even after merge: defer its cleanup to the next eligible task boundary, from outside it. Do not register an old unmanaged worktree merely to make a cleanup preview green; registration is a deliberate workflow enrollment, not a name-pattern inference.

During explicitly read-only planning, inspect and report candidates only. Do not fetch, register, export tools to disk or apply cleanup in that task. A cached `origin/main` preview is not a fresh merge verification. No hook, timer, background service or scheduled job performs cleanup; “automatic” means the agent invokes the helper at these authorized task boundaries without repeatedly asking the owner.

## Load Current Instructions When the Original Checkout Is Older

The original checkout may intentionally remain at an older HEAD to preserve live files and its index. Committing or merging this guide elsewhere does **not** update that checkout's `AGENTS.md`, nor does Codex automatically load instructions from remote refs. Do not reset it or overwrite its guide to activate this policy.

For future sessions, include this startup instruction in the task (or read it explicitly before acting):

> Worktree lifecycle applies. From the original checkout, inspect Git/worktree status and preserve its HEAD, index and unrelated edits. For an authorized implementation/maintenance task, fetch origin without submodule recursion, then read AGENTS.md and agents/guides/worktrees.md from the fetched origin/main. Read-only planning uses cached refs and reports candidates without cleanup. Load the new worktree's AGENTS.md and relevant guides before editing.

For authorized implementation/maintenance after this change merges:

```bash
cd "$HOME/repos/dots"
git -c submodule.recurse=false fetch --no-recurse-submodules --no-prune --no-tags --no-auto-maintenance origin refs/heads/main:refs/remotes/origin/main
policy_revision="$(git rev-parse origin/main)"
git show "$policy_revision:AGENTS.md"
git show "$policy_revision:agents/guides/worktrees.md"
```

Until merge, the owner may explicitly direct a session to read the pushed `origin/chore/worktree-lifecycle` revision instead. Do not claim that unmerged policy is already in `origin/main`.

If the older original checkout lacks the helper, export only the reviewed helper at the selected revision into a new test/tool-owned temporary directory. This is one small script, not a worktree backup. Do this only in an authorized non-read-only task:

```bash
lifecycle_tools="$(mktemp -d "${TMPDIR:-/tmp}/dots-worktree-tool.XXXXXXXX")"
git show "$policy_revision:tools/worktree_lifecycle.py" > "$lifecycle_tools/worktree_lifecycle.py" &&
python3 -B "$lifecycle_tools/worktree_lifecycle.py" --repo "$HOME/repos/dots"
```

Use this exported script from outside the cleanup candidate. It must be the reviewed tracked helper, not an unreviewed copy from a dirty candidate. No executable is installed and PATH is unchanged. A currently available reviewed helper may also be used directly; its containing worktree will be protected.

## Explicit Enrollment and Preview

Before creating a worktree, resolve capacity as above. Create a branch from verified fetched `origin/main`, under an immediate sibling directory of the original checkout, then register that exact path:

```bash
# Example only: choose the authorized task's branch and unused sibling path.
git worktree add -b chore/example "$HOME/repos/dots-example" origin/main
python3 -B "$lifecycle_tools/worktree_lifecycle.py" \
  --repo "$HOME/repos/dots" --register "$HOME/repos/dots-example"
```

Registration is explicit authorization for this workflow's future eligibility checks, not immediate deletion. It records path, Git administrative directory and a random identity token in `.git/dots-managed-worktrees.json`, paired with `dots-managed-token` in the linked worktree's Git administrative directory. Recreating a directory or Git registration does not inherit enrollment. Names alone authorize nothing. Registration writes Git-local maintenance metadata only, never source files or the original index. The registry is bounded to 64 records and 64 KiB; stale/malformed identities need manual review, never automatic adoption or force removal.

Preview is the default and makes no filesystem/ref changes or network requests:

```bash
python3 -B "$lifecycle_tools/worktree_lifecycle.py" \
  --repo "$HOME/repos/dots" --session-worktree "$HOME/repos/dots"
```

It reports `candidate` only against cached merge information and current observable checks. It reports original/unmanaged/protected/uncertain worktrees as `skipped`. No candidate is guaranteed removable until apply rechecks it. Exit 0 means a report was produced, not that every candidate was removed; inspect each status. Global repository/registry failures return 1 and argument errors return 2. A `removal_failed` record requires inspection even when the reporting invocation exits 0.

## Apply and Active-Use Review

Before apply, the agent must verify there is no other active or idle agent/editor/session assigned to the candidate and no known live configuration referring to it. Inspect known session state, task history and declared live paths. OS process checks cannot discover an idle remote UI session or every `source /path/file` string. If that review is uncertain, report and retain the worktree. Do not assert review just to obtain removal.

After that review, invoke apply with the **actual session worktree**, even if the command has changed cwd to the original checkout:

```bash
python3 -B "$lifecycle_tools/worktree_lifecycle.py" \
  --repo "$HOME/repos/dots" \
  --session-worktree "$HOME/repos/dots" \
  --usage-reviewed --apply
```

`--usage-reviewed` records the calling agent's completed session/configuration review for that invocation. It is not an owner-approval prompt and bypasses no eligibility check. Supply repeatable `--protect /absolute/live/path` for additional known references; helpers resolve these paths before checking. Never pass the original as the session worktree merely to evade protection of the session's real worktree.

Apply requires correct repository registration and canonical immediate-sibling placement, matching enrollment token, fresh successful fetch of remote main, and HEAD ancestry in that newly fetched `origin/main`. Fetch uses an explicit remote-main refspec, disables submodule recursion, pruning, tag fetching and automatic maintenance; it never writes a local branch. No network success means no removal. Eligibility and active-use checks repeat after fetch and changing HEAD is refused.

Git status includes staged/modified, all untracked and ignored content. Any such content is retained, even if it looks disposable. Index flags, populated submodules, untracked empty directories, inaccessible paths, locked/prunable registrations and ambiguous identities also block cleanup. The helper never reads ignored content or initializes submodules. It uses only `git worktree remove` without force; a failed or interrupted attempt reports `removal_failed` and requires inspection, with no automatic retry or bypass. No reset, clean, branch deletion, GC trick or backup archive is used. All branch/recovery refs and `dots-review-evidence` remain outside the removal scope.

The original checkout, cwd, explicit session worktree, executing helper location, allowlisted live environment paths, PATH entries, conventional home/config paths, `$HOME/dots-review-evidence`, original-checkout symlink targets and extra protected paths are checked. On Termux/Linux, the helper checks this account's `/proc` cwd, executable, descriptors, mapped paths and path arguments. It emits fixed reasons, never argv/environment contents. It skips when live-process inspection is unavailable or denied. A definite active reference takes diagnostic precedence over earlier permission uncertainty, but either blocks removal. Hosted Linux runners can deny inspection of some same-account processes; native eligible-removal coverage is then explicitly unavailable, while refusal and injected-idle tests still run. Native Windows removal is therefore deferred; preview/registration and platform-independent refusal logic are testable there, but no mocked idle result establishes native removal support.

These checks assume trusted local Git metadata and no concurrent worktree/user-file changes. A Git-local exclusive lock prevents simultaneous helper mutations; a stale lock requires review and is never automatically cleared. There is no hostile-filesystem race guarantee, cross-user process audit or proof against arbitrary undeclared configuration references. Uncertainty is a reason to retain, not to weaken the checks. After successful removal the registry entry is removed; if bookkeeping fails, report and inspect the stale entry rather than retry deletion.

## Verification and Delivery

Run `python3 -B tools/test_worktree_lifecycle.py` (`python` on Windows), `python3 -B tools/verify_core.py docs`, and `git diff --check`. Tests own temporary home/config/state/cache/repository roots and local bare remotes, with no network or package installation. Positive portable removal tests inject a known idle snapshot; native process tests separately prove detection of an active child and eligible removal when process inspection is available. Windows symlink privilege is not changed. Existing native core/experiment CI gates remain intact; this tooling-only slice requires no Go build or startup benchmark rerun locally.

Report managed/removed/skipped paths and reasons, source revision, verification, and how the next session loads current policy. Do not remove the current session's worktree at delivery. After verified merge, clean it at the next authorized boundary from another helper/session location.
