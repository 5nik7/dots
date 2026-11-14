# Cleanup

`dots cleanup` finds known disposable files, reviews them in groups and reports confirmed removals. It detects the execution platform. Termux retains its existing rules. Linux and WSL support bounded user cache/log rules through the same guarded POSIX engine. Windows implements a bounded native adapter for default npm/pip caches and named Neovim logs. Its handle, ACL, removal and accounting paths have owned native fixture evidence; actual Restart Manager integration and live acceptance remain pending. See the dated [verification evidence](../plans/cleanup.md#windows-provider-follow-up-2026-11-14).

Linux/WSL candidates include npm `_cacache`, pip, Go module/build caches, uv,
Cargo registry and named Neovim logs under an owned home. System package caches,
CPAN and checkpoint rules are not imported from Termux. Location overrides must
remain within recognized layouts, outside projects and protected application
data. Missing helpers, active references or incomplete process inspection retain
the target. WSL process visibility can make deletion unavailable even when a
scan succeeds.

Windows uses `%LOCALAPPDATA%/npm-cache/_cacache`, `%LOCALAPPDATA%/pip/Cache` and the named Neovim diagnostic files under `%LOCALAPPDATA%/nvim-data`; LocalAppData must remain beneath the native home. Custom npm/pip cache locations, Windows build caches and checkpoints remain unsupported. The JSON group catalog exposes additive `scan_supported` and `run_supported` flags; `supported` means the provider implements deletion for that group, not that the current machine satisfies every safety gate. Age or size does not establish disposable ownership. Native cache definitions follow [npm](https://docs.npmjs.com/cli/cache/) and [pip](https://pip.pypa.io/en/stable/topics/caching/) ownership boundaries.

```sh
dots cleanup                         # Scan, then Delete / Skip / Stop per group
dots cleanup scan --verbose          # Read-only review including target paths
dots cleanup run --group downloads   # Review just downloaded package caches
dots cleanup run --yes               # Explicit unattended ordinary cleanup
dots cleanup history                # Last 20 runs and combined verified size
dots cleanup report                 # Latest run; accepts a full run ID
```

Bare invocation scans without deleting when redirected or used with `--json`.
Interactive approval defaults to Skip; `yes`/`y` deletes, `no`/`n` skips, and
Stop ends the run. Optional Gum provides the same three choices. Selecting a
menu item does not approve deletion. Cleanup is permanent: there is no retained
payload copy or undo. Regenerating caches may require downloads or rebuilds.

## Groups and scope

| Group | Default | Termux targets and effect |
| --- | --- | --- |
| `downloads` | Yes | Contents of `~/.npm/_cacache` and `$XDG_CACHE_HOME/pip`; direct `.deb` files in the Termux app's `cache/apt/archives`. APT `lock` and `partial` remain. |
| `builds` | Yes | Go module/build caches, Cargo registry and uv cache. Go and uv use their native cleanup tools; a missing or failed helper never falls back to recursive deletion. |
| `logs` | Yes | `~/.cpan/build` contents and Neovim diagnostic files `log`, `mason.log`, `lsp.log`, `conform.log`, `nvim.log`, `luasnip.log`, `noice.log` under `$XDG_STATE_HOME/nvim`. Diagnostic history is lost. |
| `project-checkpoints` | No | Old Pi/Ayu checkpoint session directories classified from manifest metadata and Git tree filenames. Saved project versions and rollback points are lost. |
| `sensitive-checkpoints` | No | Old checkpoints containing authentication/configuration/history indicators, or whose manifest identifies the Pi agent directory. |
| `unclassified-checkpoints` | No | Old checkpoint stores whose original scope cannot be established; potentially valuable or sensitive data. |

Checkpoint stores are restricted to
`~/.pi/agent/ayu/checkpoints/sessions/*` containing a `.git` directory.
Their newest filesystem mtime must be at least 30 days old by default. Git
classification is bounded; missing tools, invalid manifests, excessive history
or incomplete inspection classify the store as unclassified. Classification
reads manifest metadata and Git filenames. It does not open authentication
payload files or chat transcripts, and does not report extra manifest fields.

```sh
dots cleanup groups
dots cleanup scan --include-checkpoints
dots cleanup run --group project-checkpoints --older-than 60
dots cleanup run --include-checkpoints --exclude sensitive-checkpoints
```

Each checkpoint group always needs its own interactive approval. `--yes` with
any checkpoint group fails before deletion. `--older-than DAYS` is valid only
when checkpoint groups are selected (0–36500). Repeat `--group` to select groups;
repeat `--exclude` to remove groups from the selection. `--include-checkpoints`
adds all three checkpoint groups. `--dry-run` uses the same read-only scan.

Only known locations are scanned recursively, including hidden entries. Dots
does not classify arbitrary home files by extension or size. Installed tools,
projects, Android shared storage, current credentials, shell/Codex histories,
Neovim undo/swap/sessions and chat logs are outside these rules.

## Paths and safeguards

The Termux prefix must identify `com.termux/files/usr`. All deletion targets
must remain within that app's boundary with the current owner and filesystem.
Linked roots/ancestors, mounted descendants, special files and overlapping
targets are refused. Nested symlinks are removed as links, never traversed.
An approved group is rechecked before its first deletion; each target is checked
again for changes and active process references. An uninspectable process blocks
the group. Running tools, working directories and the receipt store are protected.
Direct deletion removes only inventoried entries through directory descriptors;
newly arrived files are retained. External writers can still cause a partial run.

### Native Windows safeguards

Windows deletion requires a local NTFS volume, current-user ownership, and ACLs beneath the home that grant write access only to the current user, SYSTEM or local Administrators. It refuses reparse points at every level, foreign volumes/owners, unsupported ACL entries, read-only/system/offline objects and multiply-linked files. Existing ACLs are inspected, never repaired automatically. A group is limited to 50,000 inventoried entries; larger groups remain untouched.

After approval and the first durable receipt, Restart Manager checks the reviewed files, including references from the cleanup process itself. Dots then pins every approved entry with exclusive native handles and pins its ancestors against writes or replacement. It checks process references again while the pins remain held. A busy file or working directory, changed inventory, incomplete process query, timeout or required reboot retains the group. Restart Manager runs in a bounded child process and never stops or restarts an application or service. Scans, help, group catalogs and history never create Restart Manager sessions.

Removal uses ordinary `FileDispositionInfo` on the exact pinned handle, followed by close and an absence check. It does not use POSIX delete semantics, clear read-only attributes, change permissions or fall back to recursive deletion. Native mapped-file refusal remains active even if a process observer incorrectly reports idle. Only confirmed removals enter the totals; newly arrived or uncertain entries remain uncredited. Cache roots are retained. Native handle metadata supplies allocation figures, including sparse/compressed allocation rather than logical length.

XDG cache/state paths default to `~/.cache` and `~/.local/state`. Go defaults to
`~/go/pkg/mod` and `$XDG_CACHE_HOME/go-build`, Cargo to `~/.cargo/registry`, and uv
to `$XDG_CACHE_HOME/uv`. `GOMODCACHE`, `GOCACHE`, `CARGO_HOME` and `UV_CACHE_DIR`
overrides must pass the same boundary, protected-data and recognized-layout
checks. Arbitrary target paths and executable rule plugins are not accepted.

## Output, history and preferences

Reports show allocated bytes removed, regular files, folders and links, elapsed
time, free space and the combined verified size across recorded runs. Filesystem
free-space change is a separate observation: other processes and open files can
make it differ from removed allocation. JSON also includes logical bytes.
Sparse files use allocated storage. POSIX hardlinks are counted conservatively, with allocation credited only when every name for the inode is removed within the verified target; cross-target hardlinks can undercount reclaimed allocation. Windows refuses files already known to have multiple links and does not credit a racing surviving alias as reclaimed allocation.

Private, metadata-only schema-1 receipts live under the platform Dots state root
in `cleanup/` (`$XDG_STATE_HOME/dots/cleanup` on Termux). They record identifiers,
paths, outcomes and counts, not file contents. A lock permits one mutating run.
Read-only routes and a wholly skipped run create no receipt store. Cumulative
totals are derived from retained receipts; old manual cleanup is not imported.
`history --limit 0` returns all receipts. Deleting receipts removes their
contribution to the combined total.

Windows creates the receipt directory, lock and new journal files with a protected ACL granting access only to the current user and SYSTEM. Existing receipts with broader ACLs, links or multiple hardlinks are refused; Dots does not change their permissions. Ancestors stay pinned and the lock is exclusive during a run. History can report a busy receipt while a writer holds it.

New Windows runs append complete schema-1 report snapshots to `RUN_ID.jsonl` in the same `cleanup/` directory. Every successful append is flushed before the next deletion boundary; no payload data is stored. The journal is limited to 16 MiB, with no automatic rotation, pruning or replay. An append/flush failure stops further appends for that run. The reader uses the last complete snapshot; an incomplete final line marks that record incomplete while retaining its prior confirmed totals. A removal followed by interruption before its accounting append is excluded from retained totals. Older `RUN_ID.json` receipts remain readable; duplicate identities across the two representations are refused. Keep this reader when rolling source back after a Windows run, or explicitly preserve/export those records before a separately reviewed migration. Reverting source cannot restore deleted data.

Interrupts preserve confirmed subtotals. An interrupted/failed native helper's
unverified removals are excluded. An abruptly terminated run appears incomplete;
there is no automatic replay or continuation. Inspect `report RUN_ID`, then scan
again. Exit statuses are 0 success, 1 partial/failure, 2 invalid arguments,
3 unsupported platform and 130 stopped/interrupted.

Human views reuse Dots semantic colors, resource styles, icons, spacing and
alignment. `--color auto|always|never`, `--icons auto|always|never`, `--quiet`,
`--verbose` and `--progress auto|never` control output. `NO_COLOR` and redirected
output retain the shared presentation rules. JSON and completion output contain
no decoration, prompts or progress. Explicit noninteractive deletion requires
`dots cleanup run --yes`; checkpoint groups remain interactive.

Set `apps.cleanup.checkpoint_min_age_days` through Config to change the next
invocation's default age. It follows shared defaults, inherited profile and
selected profile precedence; the command flag overrides the resolved value.
`dots config browse --query apps.cleanup` and Cleanup → Configuration expose
this control. `icons.menu.cleanup` controls the family icon; existing CLI
formatting and semantic color controls apply without a separate style store.

The Cleanup submenu offers ordinary review, scan, groups, checkpoint review,
history, report and configuration. Completion is available through Dots shell
initialization in Bash, Zsh, Fish, PowerShell, Nushell and Xonsh. Cleanup ships
with the existing core checkout and adds no installer component or service.

## Extending rules

Trusted providers live in `lib/dots/cleanup/`. Use the repository's
[cleanup maintenance skill](../.codex/skills/dots-cleanup-maintenance/SKILL.md)
when adding a file class or platform. Establish ownership, regeneration cost,
sensitivity and a narrowly bounded path before adding a candidate. New native
platform adapters require their own isolated tests and native acceptance;
controller/help parity does not establish deletion support.
