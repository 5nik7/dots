# File catalog

**Status: Inventory, metadata, bounded adoption/link/remove and recovery implemented; general profile installation remains proposed.**

`dots files` starts the managed-files workflow by locating sources, recording their
intent, classifying targets, and listing them. It requires Python 3.9+ on a POSIX
host; discovery additionally requires Git. Neither ordinary dispatch nor basic
help requires Python or Git. Go development remains paused.

## Commands

```bash
dots files sources
dots files list --sort app
dots files list --repo androidots --platform termux
dots files list --all-platforms --json
dots files discover
dots files locate kitty
dots files show dots:kitty
dots files source dots:kitty
dots files target dots:kitty
```

`list` shows tracked records; `discover` shows untracked candidates in declared
roots, respecting Git exclusions and directory ownership. `locate QUERY` searches
both by case-insensitive ID, application, source and target substrings. `show`,
`source` and `target` require a qualified `repository:resource` ID. `sources` reports
available, unavailable and explicitly excluded repositories without initializing
submodules. Read-only commands do not create caches, lock files or state.

List/discover/locate accept `--repo`, `--app`, `--category`, `--status`, `--platform`,
`--all-platforms`, `--sort id|app|repository|source|status`, and `--json`. The default
platform is detected; other platforms can be inspected explicitly. `--json` emits
one schema-1 object with `platform`, `resources` and `sources`; diagnostics go to
stderr. Terminal views use colored status markers, counts and labeled source/target paths,
abbreviating HOME as `~` and wrapping long paths for narrow screens. Details show
application, category, platform, strategy and ownership information. Empty results
are explicit. Piped lists retain tab-separated ID, status, source and target; piped
sources retain ID, availability, repository root and platforms. Success is 0; validation/I/O
errors are 1 and invalid command syntax is 2.

Tracking writes only repository metadata, with an exclusive lock, flushed temporary
file and atomic replacement. Quote destination tokens to leave them literal:

```bash
dots files track config/example/settings --repo dots --id example-settings \
  --app example --category config --target '${CONFIG}/example/settings' \
  --platforms termux linux wsl --strategy link
```

The source must exist in its owning repository. Whole directories require
`--strategy directory-link`; `copy` records a future explicit copy preference.
`--update` is required to change an existing ID. Repeating the identical record is
a no-op. `--replaces REPOSITORY:ID` is repeatable. Tracking does not install, move,
link, copy, stage in Git, or read the contents of the source. The separate managed
operations below implement add, link, remove/rm, undo and recovery. Editing and
general module/profile installation remain future work.

## Ownership and formats

[.dots/sources.json](../.dots/sources.json) declares composition with schema 1 and
`sources` containing `id`, repository-relative `path`, allowed `roots`, `platforms`
and optional `excluded`. Dots owns common configurations; Androidots contributes
Termux-specific sources. Windots is inventoried for Windows but has no native
Windows target adapter. Neovim owns its catalog at `config/nvim/.dots/files.json`.
Missing optional catalogs are reported unavailable. Secrets are explicitly excluded;
no private submodule is initialized and no source-file contents are printed. Third-party
PowerShell and Rainmeter submodules are explicitly excluded from resource ownership.

Every participating repository owns `.dots/files.json`:

```json
{
  "schema": 1,
  "repository": "dots",
  "resources": [{
    "id": "example",
    "source": "config/example",
    "app": "example",
    "category": "config",
    "platforms": ["termux", "linux", "wsl"],
    "target": "${CONFIG}/example",
    "strategy": "directory-link"
  }]
}
```

IDs, applications and categories use lowercase letters, digits, `_` and `-`,
starting with a letter. Sources stay repository-relative without `..`. Targets
start with `${HOME}`, `${CONFIG}`, `${BIN}` or `${TERMUX}` and contain no traversal.
CONFIG uses XDG_CONFIG_HOME or HOME/.config; BIN is HOME/.local/bin; TERMUX is
HOME/.termux and resolves only on Termux. A null target records an unmapped source.
Catalog and lock symlinks are refused. Source symlinks remain observable data.

Resources are never silently overridden by repository order. Exact target claims
conflict unless one explicitly replaces every other claimant. A directory resource
owns its descendants: a second nested target conflicts, even when the directory is
already linked. These remain inventory observations; managed operation planning applies additional checks. Correct links,
broken links, other links, existing files/directories, absent sources, inactive
platforms, unmapped targets, unsupported destinations and conflicts are distinct
statuses. `replaced_by`, `conflicts` and `replacement_unavailable` explain composition.
There is no content hashing or claim that an existing copy matches its source.

The JSON catalog is a small implemented inventory model, separate from the proposed
module/profile manifests in [specification.md](specification.md). Bounded file operations consume explicit ownership and the transaction rules in
[safety.md](safety.md); they do not implement the proposed module/profile resolver.

Theme publication may deliberately connect Termux colors to generated state instead
of the catalogued baseline source. Inventory reports that link as `linked-elsewhere`;
it does not infer adoption or overwrite it. Managed operations refuse to replace these unrelated generated links.

## Presentation

Color/icons follow the dispatcher's `auto|always|never` policy, including NO_COLOR.
The following force or disable decoration; global options go before `files`:

```bash
dots --color=always files list --sort app
dots --color=never --icons=never files show dots:kitty
```

Forced color/icons select the human layout even when redirected. `--json` and
`source`/`target` always retain their machine output. Completion uses plain rows
independently of these settings. Tracking reports metadata saved without claiming
files were installed. Human file views escape control characters in filenames.

## User configuration discovery

`dots files locations` lists versioned `.dots/file-locations.json` registries from
available, applicable, non-excluded repositories. `dots files discover --system`
inspects their target paths; existing `discover` retains repository-only behavior.
System discovery is metadata-only. Its default human view groups candidate and
existing-source entries by the immediate directory under each registered root,
with counts and repository names. Unavailable entries remain visible; managed and
excluded entries appear only in totals. `--verbose` expands individual paths and
source mappings; `--all` includes managed/excluded entries and combines with
`--verbose`. These two flags require `--system`. A managed label means the catalog
claims the path, not that its link has been verified; use `files list` for link status.
`--repo ID` filters owners. `--json` returns the complete `schema: 1` and `items`
records regardless of human display flags, including hidden statuses. It never
initializes optional/private repositories.

```bash
dots files discover --system                  # Compact directory groups
dots files discover --system --verbose        # Candidate files and sources
dots files discover --system --all --verbose  # All observed entries in detail
```

Paths use the terminal theme's magenta, counts cyan, and repository names blue;
statuses retain semantic colors (informational candidates, green catalog claims,
muted exclusions and red unavailable entries). Plain output keeps the same layout
and status text. Paths wrap without truncation on narrow terminals.

Each registry has `schema: 1`, `repository`, and `locations`. A location has `id`,
`kind` (`root` or `file`), `target` using existing destination tokens, repository-
relative `source`, `platforms`, and optional relative glob `exclusions`. More
specific locations win; equal-specificity owner ambiguity requires `--repo`.
Edit and version these files to update coverage. Common XDG configs map into Dots
`config/`; Termux configs map into Androidots `termux/`; home dotfiles have explicit
mappings. The existing catalog's ownership claims always block duplicate adoption.

No directory symlinks are followed. Known credential locations, caches, databases,
logs, backups, generated dots state and special files are excluded. Import adds a
bounded streaming check for recognizable credentials without displaying content;
it is not an exhaustive secret detector. Review imports before committing them.
Built-in exclusions also prune Code/Electron cache and session-storage trees,
`node_modules`, cookies, backup suffixes, and XfceThemeManager's generated preview
directories. Ordinary settings, keybindings, snippets and custom theme assets
remain eligible. Excluded directories produce one metadata record without walking
their contents; totals count observed entries, not every descendant of a pruned
directory. The same exclusions protect `add --scan` and explicit adoption.

## Import, link and stop managing

```bash
dots files add ~/.config/example --dry-run
dots files add ~/.config/example
dots files add --scan --dry-run
dots files add --scan --backup
dots files add ~/.config/example --directory-link
dots files link dots:example --backup
dots files remove dots:example
dots files rm dots:example           # Alias for remove
```

All mutations preview before confirmation; `--yes` enables unattended execution,
`--dry-run` writes nothing, and `--json` keeps stdout structured. Examples using
`dots:example` require that resource to exist in the catalog. Add generates stable
IDs from repository-relative paths, displays them, and refuses collisions. Use
`files list` to obtain qualified IDs for subsequent commands.

Add copies and verifies configurations into their mapped owning repository,
records catalog entries and links the original locations to the sources. It uses
individual files by default, preserving unrelated files and directory structure.
`--directory-link` requires explicit paths and owns the whole directory. Identical
existing sources may be reused; different occupied sources are refused. Paths
outside registered locations need a registry update first. Symlinked parent paths,
unrelated links, overlapping batches, secret-like files and protected generated
theme targets require manual review. A blocked input refuses the complete batch.

Link installs catalogued `link` or `directory-link` sources. Correct links are
no-ops; different existing objects require an enabled verified backup. It never
silently converts a `copy` preference or replaces an unrelated link.

Remove replaces a matching managed link with a verified regular copy, removes its
catalog record, and preserves the repository source. An already regular config is
left untouched; an absent target is not recreated. Whole-directory materialization
refuses nested links or Git metadata that would change meaning outside the source
repository; these require manual review. Removal does not delete the
repository source, so repository discovery can find it again as an untracked
resource. Nothing stages or commits Git changes.

## Backups, history and recovery

Retained backups default off. `--backup` enables them per operation; `--no-backup`
overrides the machine-local `${XDG_CONFIG_HOME:-$HOME/.config}/dots/files.json`
preference (`{"schema":1,"backup":true}`). The [default example](../default/files.json)
is opt-out. Preferences are never created automatically.

Snapshots live under `${XDG_STATE_HOME:-$HOME/.local/state}/dots/backups`, with
verified payloads in the corresponding private transaction directory. They remain
independent of bak, bak.ps1, `.bak.*` and `~/.bakstore`; no pruning is implemented.

```bash
dots files history
dots files backups list
dots files backups show BACKUP_ID
dots files backups restore BACKUP_ID --dry-run
dots files undo TRANSACTION_ID --dry-run
dots files recover TRANSACTION_ID --dry-run
```

History, backup listing and details accept `--json`. Undo reverses a completed
transaction only when affected objects match recorded post-operation state.
Recover rolls back an interrupted transaction; pending recovery blocks new writes.
Restore replaces backed-up data objects, not catalog metadata (use undo for that).
A changed occupied restore target requires a new explicit backup. All three
mutating routes use the same preview/confirmation and backup options.

Temporary verified recovery copies are required even with retained backups off.
After success, unneeded content payloads are removed; journals retain identity,
hashes, link text and previous catalog metadata. Undo without a retained snapshot
can use unchanged repository content and refuses when original data is unavailable.
Content copied for a retained snapshot remains until a future explicit retention
operation is implemented. Journals are outside Git and never contain file contents
except catalog metadata. Filesystem operations are bounded POSIX operations; native
Windows remains unsupported. See [safety](safety.md#managed-file-transactions).
