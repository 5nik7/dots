---
name: dots-git-maintenance
description: Maintain the Dots Git command family for status, inspection, recursive publish/sync and wiki Git routing. Use for dots git implementation, not as authorization to commit, push or synchronize repositories.
---

# Dots Git Maintenance

Read [Git operations](../../../docs/git.md), [decision 0010](../../../docs/decisions/0010-git-and-managed-file-operations.md) and [safety](../../../docs/safety.md). POSIX orchestration lives under `lib/dots/git/*.bash`; `lib/dots/git/cli.py`, `inspection.py` and `submodule.py` supply native/shared paths. Dots does not require the standalone git-it command. Maintain equivalent command/data behavior without adding a Bash dependency on Windows.

Preserve explicit repository scope and bounded submodule traversal. Inspection uses local evidence and cached remote state; dry-run never fetches or mutates. Publishing defaults to staged content, preserves hooks/signing and requires validated ownership/upstream/effective push destinations with an explicit branch refspec. `--all` broadens staging only when requested. Do not infer ownership from author identity. Sync preserves dirty/diverged/protected work and recorded child commits; private/missing children are initialized only with explicit authorization.

Recheck mutable inputs and retain compatible per-common-directory locks; never break stale locks automatically. Git operations are incremental, not Store transactions: completed local commits/pushes remain after partial failure. Never add implicit stash/reset/clean/rebase/force-push behavior. Delegate associated wiki evidence and source-before-wiki ordering to [wiki maintenance](../dots-wiki-maintenance/SKILL.md).

Use [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu review and [dots-config](../dots-config/SKILL.md) for integration changes. Profile-owned `git.conf` and Git/file-color roles retain their established readers and owners; preserve raw JSON and semantic human reports.

Run affected `tools/test_git_operations.py`, `tools/test_native_git.py`, `tools/test_git_submodules.py`, `tools/test_git_platform.py` and `tools/test_wiki_git.py` cases sequentially on Termux. Fixtures own working repositories and local bare remotes. Cover literal paths, changed topology, ownership/refspec refusal, missing children, partial failures, cancellation and preview purity. Native Windows evidence remains distinct. Update canonical docs and local wiki via [documentation maintenance](../dots-documentation-maintenance/SKILL.md).
