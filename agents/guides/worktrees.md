# Development Worktree Lifecycle

Work directly in the existing checkout on `main` by default. Read its `AGENTS.md` and task guides, inspect Git status, and preserve unrelated work. Ordinary maintenance requires no new branch or worktree, enrollment, remote-policy fetch, or cleanup. Earlier requirements to preserve the original checkout unchanged applied to historical implementation tasks.

This guide governs optional local development tooling, separate from the public `dots` CLI. Use the procedures below only when a task calls for a separate worktree or deliberate worktree maintenance. Creating a worktree is optional; the existing helper and its removal safeguards remain available.

## Capacity and Triggers

When deliberately using linked worktrees, keep at most one active development worktree alongside the original checkout. Run `git worktree list --porcelain` and inspect every existing worktree before creating another. Reuse the existing worktree only when its branch and outstanding work match the authorized task. If it is active, dirty, unmerged, unmanaged or uncertain, do not create a second worktree. This does not block task-relevant edits in the main checkout. Registration enforces this capacity; Git itself is not intercepted.

During deliberately selected worktree maintenance, inspect managed cleanup candidates and remove eligible ones after the checks below; no repeated owner approval is required for already authorized eligible cleanup. Ordinary implementation, maintenance, or a merge alone does not trigger cleanup. A worktree containing the current session or executing helper is protected even after merge: defer its cleanup to a later worktree-maintenance task from outside it. Do not register an old unmanaged worktree merely to make a cleanup preview green; registration is deliberate enrollment, not a name-pattern inference.

During explicitly read-only worktree planning, inspect and report candidates only. Do not fetch, register, export tools to disk or apply cleanup. A cached `origin/main` preview is not a fresh merge verification. No hook, timer, background service or scheduled job performs cleanup.

## Select Instructions and Tools

Use the instructions in the current checkout for ordinary edits. Loading policy from remote refs is not a startup requirement. If a deliberate worktree task needs a newer reviewed policy or helper from another revision, read that exact revision and preserve unrelated local content; do not reset the checkout to activate it.

Before creating a linked worktree from remote main, fetch without submodule recursion or unrelated ref changes:

```bash
git -c submodule.recurse=false fetch --no-recurse-submodules --no-prune --no-tags --no-auto-maintenance --refmap= origin refs/heads/main:refs/remotes/origin/main
```

Use a reviewed tracked helper from outside any cleanup candidate. For the helper in the original checkout, set the path used by the examples below:

```bash
lifecycle_tools="$HOME/repos/dots/tools"
```

If the required reviewed helper exists only in another revision, export that script into a test/tool-owned temporary directory during the authorized worktree task. Do not use an unreviewed dirty copy. The helper's containing worktree is protected from removal. No executable is installed and PATH is unchanged.

## Explicit Enrollment and Preview

When a task calls for a separate worktree, resolve capacity as above. Create a branch from verified fetched `origin/main`, under an immediate sibling directory of the original checkout, then register that exact path:

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

Apply requires correct repository registration and canonical immediate-sibling placement, matching enrollment token, fresh successful fetch of remote main, and HEAD ancestry in that newly fetched `origin/main`. Fetch uses `--refmap=` and an explicit remote-main refspec so configured fetch mappings cannot update unrelated local or recovery refs. It disables submodule recursion, pruning, tag fetching and automatic maintenance; it never writes a local branch. No network success means no removal. Eligibility and active-use checks repeat after fetch and changing HEAD is refused.

Git status includes staged/modified, all untracked and ignored content. Any such content is retained, even if it looks disposable. A metadata-only walk also rejects FIFOs, sockets, device nodes, unknown entry types and metadata inspection failures without opening special objects or following symlinks. Git status alone can omit untracked special objects. Index flags, populated submodules, untracked empty directories, inaccessible paths, locked/prunable registrations and ambiguous identities also block cleanup. The helper never reads ignored content or initializes submodules. It uses only `git worktree remove` without force; a failed or interrupted attempt reports `removal_failed` and requires inspection, with no automatic retry or bypass. No reset, clean, branch deletion, GC trick or backup archive is used. All branch/recovery refs and `dots-review-evidence` remain outside the removal scope.

The original checkout, cwd, explicit session worktree, executing helper location, allowlisted live environment paths, PATH entries, conventional home/config paths, `$HOME/dots-review-evidence`, original-checkout symlink targets and extra protected paths are checked. On Termux/Linux, the helper checks this account's `/proc` cwd, executable, descriptors, mapped paths and path arguments. It emits fixed reasons, never argv/environment contents. It skips when live-process inspection is unavailable or denied. A definite active reference takes diagnostic precedence over earlier permission uncertainty, but either blocks removal. Hosted Linux runners can deny inspection of some same-account processes; native eligible-removal coverage is then explicitly unavailable, while refusal and injected-idle tests still run. Native Windows removal is therefore deferred; preview/registration and platform-independent refusal logic are testable there, but no mocked idle result establishes native removal support.

These checks assume trusted local Git metadata and no concurrent worktree/user-file changes. A Git-local exclusive lock prevents simultaneous helper mutations; a stale lock requires review and is never automatically cleared. There is no hostile-filesystem race guarantee, cross-user process audit or proof against arbitrary undeclared configuration references. Uncertainty is a reason to retain, not to weaken the checks. After successful removal the registry entry is removed; if bookkeeping fails, report and inspect the stale entry rather than retry deletion.

## Verification and Delivery

For helper changes, run `python3 -B tools/test_worktree_lifecycle.py` (`python` on Windows), `python3 -B tools/verify_core.py docs`, and `git diff --check`. Tests own temporary home/config/state/cache/repository roots and local bare remotes, with no network or package installation. Positive portable removal tests inject a known idle snapshot; native process tests separately prove detection of an active child and eligible removal when process inspection is available. Windows symlink privilege is not changed. Existing native core/experiment CI gates remain intact; helper-only changes require no Go build or startup benchmark rerun locally. For documentation-only changes, run the documentation and whitespace checks without rerunning the helper suite.

For worktree maintenance, report managed/removed/skipped paths and reasons, source revision, and verification. Do not remove the current session's worktree at delivery. After verified merge, it may be cleaned during a later deliberately selected worktree-maintenance task from another helper/session location.
