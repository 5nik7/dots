# 0010: Bounded Git and managed-file operations

**Status: Accepted and implemented, 2026-09-25; native Termux fixture evidence recorded in the focused plan.**

The owner approved self-contained Git status/publish/sync plus file discovery,
adoption, linking, removal and optional backups. Extend the current Bash/Python
implementation without resuming Go or implementing general module/profile apply.

Git commands port the relevant MIT-licensed git-it engine into dots. They default
to the dots root, use separate owner configuration, preserve child-first publish
and parent-first sync, and require explicit submodule initialization. They expose
compact human views and structured data. They do not form an atomic transaction.

Managed file commands share a Python transaction layer: complete preflight,
verified staging, locks, durable replacement boundaries, reverse rollback and
explicit drift-safe undo/recovery. They consume the existing JSON catalogs and
new per-repository location registries. File-level adoption is the default;
whole-directory linking requires explicit ownership. Remove stops management,
materializes the live config and retains the repository source. Catalog tracking
alone retains its metadata-only contract.

Optional retained snapshots default off and live under XDG state. Temporary
rollback protection is mandatory independently of that preference; completed
transactions without snapshots discard content payloads and retain recovery
metadata. Undo can use verified unchanged repository content when no snapshot was
retained. Different occupied targets require a retained backup before replacement.
Standalone bak and its backup locations remain independent. No automatic pruning,
secret adoption, Git staging, publication or live migration is introduced.

See [files](../files.md), [Git](../git.md), [safety](../safety.md), and the
[implementation plan](../../plans/git-and-file-operations.md).
