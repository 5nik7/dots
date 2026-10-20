# Git commands

**Status: Implemented in the live Bash command family; native Windows is unsupported.**

`dots git` shows static help for `status`, `publish`, and `sync`. These commands
start at the dots repository regardless of cwd. `-C DIR` / `--directory DIR`
selects the repository containing another directory, without climbing to its
outermost parent. Only registered submodules are traversed, independently of the
file catalog and its platform/private exclusions. Missing repositories are never
initialized by inspection or publication.

[Terminal progress](presentation.md#operation-progress) covers recursive inspection and local operation phases, with repository counts when known. Fetch, initialization, commit and push use static phase messages so credentials, hooks and signing retain terminal access. `DOTS_PROGRESS=never` disables both displays; JSON and dry runs bypass them. Completion counts do not imply that every repository was successfully published.

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
handled separately so deliberately staged pointers are preserved. Tracked files
remain eligible even beneath ignored directories; ignored new files stay excluded.
Staging failures can leave some changes staged; inspect `git status` before retrying. Review the
preview, then confirm once; unattended callers require `--yes`. A default UTC
message is generated if `-m` / `--message` is omitted. Children publish before
parents; failed children block dependent parents, while safe siblings continue.

Human terminal approval uses Gum's **Cancel / Publish** menu when available,
with Cancel selected by default. Otherwise the existing text prompt applies.
JSON keeps its stderr text prompt; `--yes` and `--dry-run` bypass Gum. Selector
failure does not retry or publish, and Ctrl-C exits 130. Existing previews,
fingerprint checks and incremental publication are unchanged. See the
[interaction contract](presentation.md#optional-gum-interactions).

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

## Theme colors

Dots Git status, sync and publish use the shared [Git style roles](file-colors.md#git-styles). Repository names use `repo_owned` when the selected fetch remote matches a configured owner, otherwise `repo`; branches use `branch`, or `detached` for detached HEAD descriptions. Tracking counts use `ahead` and `behind`. Repository status uses its corresponding role. Successful operation events use `clean`, failed/blocked events use `blocked`, and missing/modified events use their named roles. Neutral information, planned operations and final summaries retain shared diagnostic colors.

File status labels use conflict, untracked, deleted, renamed, copied, added, modified or staged colors, in that priority order when multiple states apply. A staged-only modification uses `staged`; a staged plus worktree modification uses `modified`. Full status wording is retained. Filenames and icons keep their independent type/MIME styles, including old paths in rename rows. The `ignored` style is available for consumers; status does not start listing ignored files.

Styles come from the current published theme. Run `dots theme colors git` to inspect them, and use `dots theme colors set git ROLE --fg COLOR --apply` to save and refresh a customization. Older, missing or malformed publications have bounded terminal-color fallbacks. Color/icon settings and destination-stream TTY detection still apply; JSON and Git operation semantics are unchanged. Shell prompts, native Git configuration and editor Git displays are not changed by these roles.

Ownership highlighting uses the branch remote (falling back to `origin`) and exact host/namespace matching from `dots/git.conf`, including `hostAlias`. It reads only local Git metadata and caches the result per repository per command. Missing or malformed presentation configuration falls back to `repo` for status/sync; publish retains its strict configuration and destination checks. Push URLs do not determine this display color. JSON and plain output remain unchanged.

## Native PowerShell

`dots.ps1 git status|sync|publish` invokes `lib/dots/git/cli.py` directly with native Git. It preserves cached status, dry-run, ownership checks, recursive child-before-parent publication, explicit remote/ref arguments and refusal to discard local state. `tools/test_native_git.py` runs the portable safety cases against that controller. Bash PTY cases are excluded from that runner and remain separate; native Windows Ctrl-C/Ctrl-Break, lock cleanup and visual equivalence still require acceptance. See [native PowerShell](powershell.md).
