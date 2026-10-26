# Git commands

**Status: Implemented in Bash and the native Python/PowerShell controller; native Windows runtime and visual acceptance remain pending.**

`dots git` shows static help for `info`, `submodule`, `submodules`, `status`, `publish`, and `sync`. These commands
start at the dots repository regardless of cwd. `-C DIR` / `--directory DIR`
selects the repository containing another directory, without climbing to its
outermost parent. Registered submodules are traversed independently of the file catalog and its
platform/private exclusions. A declared wiki is included as a separate associated
repository; `--no-wiki` excludes it from top-level info/status/sync/publish. Missing repositories are never
initialized by inspection or publication.

`dots menu` includes a Git family with report and submodule/wiki inspection choices, plus publish and sync. The Git and Git → Wiki publish choices pass `--all` to their respective commands and retain the existing terminal review and confirmation. Direct CLI publication remains staged-only by default. Menu sync first shows the local `--dry-run` report; a successful, normally dismissed preview opens a Cancel/Sync confirmation with Cancel selected. Only explicit Sync runs the existing command. Menu sync adds no flags or repository scope and does not change direct CLI sync behavior. See the [launcher mapping](commands.md#dots-workflow-menu).

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

Direct CLI publish is staged-only by default, also publishing existing ahead commits. `--all`
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

## Repository info and submodules

```bash
dots git info
dots git submodules
dots git submodules --details --depth 2
dots git submodules status
dots git submodules status config/nvim --dirty
dots git submodules publish config/nvim --dry-run
dots git submodules publish config/nvim --yes -m 'Update editor'
dots git submodules publish --all-submodules --all --dry-run
```

`info` shows repository identity/path, selected fetch remote and URL, owner
namespace, configured ownership match, branch/HEAD/upstream, local-change counts,
cached tracking counts and submodule availability counts. It does not list file
contents or include the full tree. `Owner` is the account/namespace in the remote
URL; `Owned` is an exact match against the configured owner rules, independent of
color settings. Missing or malformed ownership configuration is identified.
Credentials, query strings and URL fragments are removed from human and JSON
output. Remote selection uses the attached branch's remote, falling back to
`origin`; local-only upstream `.` also falls back to `origin`.

`submodules` shows registered descendants in a tree: paths relative to the selected
repository, branches, working-tree states, and HEAD differences from parent index
pointers. `--details` adds remote/owner and full recorded/current commit IDs.
`--depth N` limits discovery to N submodule levels (`1` means immediate children).
Counts cover that traversal; the output explicitly identifies the depth limit.
The limit deliberately avoids inspecting deeper registrations, so it does not
claim that a displayed boundary node has no children.

`submodules info [--depth N]` shows the same info fields for every discovered
descendant, excluding the outer root. Each block adds its named selector and
counts of discovered descendants from the same traversal. Depth-limited counts
are explicitly scoped; missing children have an unavailable block and their
undiscovered descendants remain unknown. Ambiguous selectors are identified.

### Named submodule navigation

```sh
dots git submodule nvim                        # defaults to info
dots git submodule nvim status --dirty
dots git submodule nvim publish --dry-run
dots git submodule 5ui7e info
dots git submodule 5ui7e submodules info --depth 1
dots git submodules publish profiles/windows/rainmeter/5ui7e --dry-run
```

NAME is a direct child's path basename: `nvim` selects `config/nvim`, and
`5ui7e` selects the registered `profiles/windows/rainmeter/5ui7e` child. For nested
submodules, `parent:child` traverses explicit registration edges.
Registration subsection names and remote repository names are not aliases.
There is no recursive search for a matching basename. Duplicate sibling names
are refused with exact-path alternatives; use `git info -C DIR` for their info
or `git submodules status|publish PATH` for an exact registered path. Literal
colons cannot be addressed by the short-name grammar. Use `--` before a
leading-dash name, with options before the separator.

`-C` selects the initial base even when placed after an action. Repeated singular
navigation and colon chains are equivalent. `info` inspects the selected repo;
`status` includes it and its descendants; `publish` resolves it to a registered
path and uses guarded, child-first scoped publication. The excluded parent's
index, commit and remote remain untouched. It may have a pending pointer update.
Named `publish --all` includes unstaged files; it rejects `--all-submodules`.
`NAME submodules` browses only descendants, and its `info`, `status [PATH]` and
`publish PATH|--all-submodules` actions use the selected repo as their base.
Missing nodes can be inspected but cannot be traversed or published.

Contextual help reads static action headers without querying Git or executing
extensions. Completion discovers only registered names/paths when requested,
honors `-C`, and offers leaf-specific options in Bash, Zsh, Fish and PowerShell.
Named JSON delegates to the existing action schema, with exact paths rather than
display selectors in operation records. No executable is generated per name.

### Path-based submodule actions

`submodules status [PATH]` shows detailed Git status for descendants, or the named
submodule and its descendants. `--dirty` retains staged, unstaged, untracked,
conflicted and changed-pointer entries, plus missing/blocked entries. Clean
repositories that are only ahead/behind or have unknown tracking are omitted.
Discovery errors remain visible even when no ordinary status rows match.

All these routes accept `-C DIR` / `--directory DIR`, `--json` and `--full-paths`.
The base defaults to the Dots checkout, not cwd. PATH names a registered submodule
relative to that base, including nested paths such as `middle/leaf`; it is not an
arbitrary directory, basename alias or path outside the base. Use forward slashes
on both platforms. Use `--` before a leading-dash PATH (put options before `--`).
Completion suggests registered paths relative to the selected base, lazily and
without executing extensions. No inspection initializes missing children or
fetches remote information. Unavailable descendants remain unknown.

Scoped publication requires PATH or `--all-submodules`, exclusively. The latter
selects every direct child's subtree, excluding the outer repository. Existing
publish options retain their meaning: `--all` selects ordinary unstaged/untracked
files; it does **not** select all submodules. One combined preview and approval
covers the forest. Children publish first; dependent parents are blocked after
failure and safe siblings can continue. Selected roots have no mutable parent
outside their selection: excluded ancestors are never staged, committed or pushed.
A successful child publish can therefore leave an excluded parent's gitlink
outdated; a `pending` event identifies this follow-up. Record that pointer later
through an explicitly selected parent publication. Existing staged pointer intent
inside selected subtrees is preserved. Selection registrations are rechecked
before publication and after fetch, alongside the usual snapshot checks.

Info/tree/status JSON emits one schema-1 object containing `command`, `base`,
`selection` (selected path or null), `remote_state: "cached"`, `complete`,
`depth_limit`, `depth_limited`, `submodules` availability counts, `errors`, and
`repositories`. Info has one root record; tree/status contain descendant records.
Records contain absolute `path`/`parent`, base-relative `relative_path`, `depth`,
`availability`, `reason`, `recorded_commit`, `head`, `pointer_changed`, `branch`,
`detached`, `status`, nullable `upstream`/`ahead`/`behind`, existing `files` records,
and nullable `remote` metadata (`name`, sanitized `url`, `host`, `owner`, nullable
`owned`, and `ownership`: configured/unconfigured/unavailable). Missing information
is null rather than an invented value. A deliberately limited traversal can be
complete within its depth; unavailable requested traversal sets `complete: false`.
Empty collections and dirty state alone succeed.

Collection info uses schema 1 with `command: "submodules info"` and the same
discovery envelope. Each repository adds `selector` (null when ambiguous or not
representable), `submodules` descendant availability counts and `depth_limited`.
Counts describe discovered nodes only. Named info/status/publication retain the
underlying action's JSON schema and values.

Scoped publication retains the operation event schema with `command: "submodules
publish"` and adds absolute `base` and a `selection` array of selected roots. The
existing status/publish/sync JSON contracts are unchanged. Existing exit codes
apply. New views and Bash submodule selection require Python 3.9+ in addition to
Git; named contextual help also requires Python but never queries Git.
Basic group help remains dependency-light.

Human tree connectors are muted and remain connected through header rows,
separators, nested entries, wrapped names/status, reasons and `--details` fields.
Intermediate siblings use `├──`, final siblings use `└──`, and `│` continues only
while that branch remains open. Icon-disabled human views use ASCII equivalents.
Empty trees have no dangling guides; summary rows sit outside the tree. Ordinary
redirected text retains its established layout.

Repository/branch/status fields use published Git roles and identity icons.
Git info `Path` fields use the shared folder icon and directory color, including
collection and named info. `--full-paths` changes the displayed path, not its
styling. Narrow views wrap complete values; icons and colors remain independent.
Shared progress is disabled for redirected/JSON/dry-run output.

## Theme colors

Dots Git status, sync and publish use the shared [Git style roles](file-colors.md#git-styles). Repository names use `repo_owned` when the selected fetch remote matches a configured owner, otherwise `repo`; branches use `branch`, or `detached` for detached HEAD descriptions. Tracking counts use `ahead` and `behind`. Repository status uses its corresponding role. Successful operation events use `clean`, failed/blocked events use `blocked`, and missing/modified events use their named roles. Neutral information, planned operations and final summaries retain shared diagnostic colors.

File status labels use conflict, untracked, deleted, renamed, copied, added, modified or staged colors, in that priority order when multiple states apply. A staged-only modification uses `staged`; a staged plus worktree modification uses `modified`. Full status wording is retained. Filenames and icons keep their independent type/MIME styles, including old paths in rename rows. The `ignored` style is available for consumers; status does not start listing ignored files.

Styles come from the current published theme. Run `dots theme colors git` to inspect them, and use `dots theme colors set git ROLE --fg COLOR --apply` to save and refresh a customization. Older, missing or malformed publications have bounded terminal-color fallbacks. Color/icon settings and destination-stream TTY detection still apply; JSON and Git operation semantics are unchanged. Shell prompts, native Git configuration and editor Git displays are not changed by these roles.

Ownership highlighting uses the branch remote (falling back to `origin`) and exact host/namespace matching from `dots/git.conf`, including `hostAlias`. It reads only local Git metadata and caches the result per repository per command. Missing or malformed presentation configuration falls back to `repo` for status/sync; publish retains its strict configuration and destination checks. Push URLs do not determine this display color. JSON and plain output remain unchanged.

## Native PowerShell

`dots.ps1 git status|sync|publish` and `git submodules publish` invoke `lib/dots/git/cli.py` directly with native Git. It preserves cached status, dry-run, ownership checks, recursive child-before-parent publication, explicit remote/ref arguments and refusal to discard local state. `tools/test_native_git.py` runs the portable safety cases against that controller. Bash PTY cases are excluded from that runner and remain separate; native Windows Ctrl-C/Ctrl-Break, lock cleanup and visual equivalence still require acceptance. See [native PowerShell](powershell.md).

The new info/tree/submodule-status routes share `inspection.py` between Bash and
PowerShell. Scoped publication reuses each established engine. Windows app
destinations are unchanged; see the [focused plan](../plans/git-submodules.md)
for verification and remaining native acceptance.

## Associated wiki repository

`dots git wiki` defaults to wiki info; `info`, `status`, `sync` and `publish` select only the associated checkout. Ordinary top-level Git operations include it when declared, with `--no-wiki` as an exclusion. It has no parent gitlink: its branch/upstream and index remain independent. Missing checkouts are visibly skipped; `dots wiki init` is the explicit acquisition route. Submodule-only routes retain their existing scopes.

Source/submodule synchronization precedes wiki synchronization; source publication precedes dependent wiki publication. A source failure blocks that dependent operation. Publication checks the selected index (or explicit `--all` working-tree content) against generated documentation for the selected/published source tree, and never builds or stages pages automatically. Wiki-only publication requires published source inputs. See [wiki commands](wiki.md) for generation, provenance, recovery and maintenance.
