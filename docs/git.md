# Git commands

**Status: Implemented in the live Bash command family; native Windows is unsupported.**

`dots git` shows static help for `status`, `publish`, and `sync`. These commands
start at the dots repository regardless of cwd. `-C DIR` / `--directory DIR`
selects the repository containing another directory, without climbing to its
outermost parent. Only registered submodules are traversed, independently of the
file catalog and its platform/private exclusions. Missing repositories are never
initialized by inspection or publication.

```bash
dots git status
dots git status --full-paths
dots git status --json
dots git publish --dry-run
dots git publish -m 'Update configuration'
dots git publish --all --yes -m 'Update repository tree'
dots git sync --dry-run
dots git sync
dots git sync --init          # Explicit permission to initialize missing children
dots git sync --remote        # Explicit configured branch advancement
```

Status reports every repository with branch, local changes, and cached ahead/behind
counts when available. Files use repository-relative paths and index/worktree
status. Detached branches, conflicts, missing repositories and unknown tracking
state stay distinguishable. Repository labels use basenames with disambiguation;
`--full-paths` expands human repository/file paths. Shared dots color/icon controls
and plain fallbacks apply; no fetch occurs during status.

Publish is staged-only by default, also publishing existing ahead commits. `--all`
stages ordinary tracked and untracked files, respecting ignore rules; gitlinks are
handled separately so deliberately staged pointers are preserved. Review the
preview, then confirm once; unattended callers require `--yes`. A default UTC
message is generated if `-m` / `--message` is omitted. Children publish before
parents; failed children block dependent parents, while safe siblings continue.
Changed detached/foreign dependencies are blocked; unchanged ones need not be
owned. Hooks and signing remain enabled. Only the configured upstream branch is
pushed using an explicit refspec, without tags or force.

Owner configuration is `${XDG_CONFIG_HOME:-$HOME/.config}/dots/git.conf`:

```ini
[dots-git]
    owner = github.com/your-account
    hostAlias = github-work=github.com
```

`--config FILE` overrides this for publish; `--no-config` disables it. No owners
are inferred or imported from git-it. Exact host/namespace matching checks the
effective push URL, not author identity or authentication. Multiple push URLs,
custom push refspecs, mirrors and push-remote overrides are refused. Configuration
is Git-config data with includes and unknown keys refused. See the commented
[example](../default/git.conf).

Sync fast-forwards the root and then visits children at recorded commits. Dirty
state, divergence, unsafe topology changes and unprotected local commits block the
affected subtree. `--remote` requires a configured submodule branch or attached
upstream; it never guesses a default branch. Missing children report incomplete
traversal unless `--init` explicitly permits downloading them, including private
repositories. Changed parent pointers remain unstaged.

`--dry-run` is local: no network, locks, or repository writes. Actual operations
recheck mutable inputs and use the compatible `git-it.lock` in each common Git
directory. Ordinary Git does not honor this lock. Stale locks require manual
review. Operations are incremental, not atomic transactions: completed work and
local commits remain after failure. Nothing automatically stashes, resets, cleans,
rebases, or force-pushes. Standalone git-it remains unchanged and is not required.

`--json` emits one undecorated schema-1 object. Status contains `remote_state:
"cached"`, `complete` and `repositories` with path, branch, status, nullable
ahead/behind counts, and files (`path`, `xy`, `old_path`). Operations contain
`command`, `complete`, `dry_run`, and ordered events (`path`, `status`, `detail`,
`file`, `xy`). File paths in records are relative; repository paths are absolute.
Diagnostics and interactive confirmation go to stderr. Cancellation is an explicit
event. Exit codes: 0 complete/cancelled, 1 failed/incomplete, 2 syntax/configuration,
3 dependency/context. Dirty status alone is not an error.

Git commands require Bash 5, Git and ordinary POSIX utilities; publication also
requires `sha256sum`. Basic dots help retains its existing lighter requirements.
Tests and platform limits are in [testing](testing.md#git-and-managed-file-operations).
