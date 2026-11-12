# Cleanup

`dots cleanup` finds known disposable files, reviews them in groups and reports
confirmed removals. It detects the execution platform. Cleanup rules currently
support Termux; other platforms provide help, groups and receipt inspection, but
scan/run return an explicit unsupported result (exit 3).

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
Sparse files use allocated blocks; hardlinks are counted conservatively, with
allocation credited only when every name for the inode is removed within the
verified target. Cross-target hardlinks can undercount reclaimed allocation.

Private, metadata-only schema-1 receipts live under the platform Dots state root
in `cleanup/` (`$XDG_STATE_HOME/dots/cleanup` on Termux). They record identifiers,
paths, outcomes and counts, not file contents. A lock permits one mutating run.
Read-only routes and a wholly skipped run create no receipt store. Cumulative
totals are derived from retained receipts; old manual cleanup is not imported.
`history --limit 0` returns all receipts. Deleting receipts removes their
contribution to the combined total.

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
