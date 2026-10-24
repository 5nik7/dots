# File catalog

**Status: Inventory, metadata, bounded adoption/link/remove, checkout installation and recovery implemented; general profile installation remains proposed.**

`dots files` starts the managed-files workflow by locating sources, recording their
intent, classifying targets, and listing them. It requires Python 3.9+; discovery additionally requires Git. Native Windows supports the bounded install/uninstall, inspection and recovery routes described in [checkout installation](installation.md); adoption and the browser remain POSIX-only. Neither ordinary dispatch nor basic
help requires Python or Git.

Slow catalog/system discovery, browser loading, planning and file operations use [terminal progress](presentation.md#operation-progress). Preparation, apply and reverse recovery have separate item counts; final results retain transaction and recovery details. `DOTS_PROGRESS=never` disables the display. JSON, raw source/target queries and dry runs never animate.

## Commands

```bash
dots files sources
dots files browse
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
`--strategy directory-link`; `copy` records an explicit copy strategy for managed installation.
`--update` is required to change an existing ID. Repeating the identical record is
a no-op. `--replaces REPOSITORY:ID` is repeatable. Tracking does not install, move,
link, copy, stage in Git, or read the contents of the source. The separate managed
operations below implement add, link, remove/rm, undo and recovery. Source-content editing remains separate from mapping edits.

## Stash and edit mappings

`dots files stash` disables tracked resources repository-wide while keeping their
source files and catalog entries. It unlinks only a matching current symlink,
including a matching dangling link. Unrelated destination objects are preserved;
receipt-owned drift or a link still claimed by another enabled resource blocks
the batch. `--restore` enables and relinks the selected resources after validation.
Stash also retires unchanged receipt-owned historical links left by metadata-only
edits, with each removal shown in the preview; it never scans for arbitrary links.

```bash
dots files stash                         # Select resources, then review the batch
dots files stash dots:example --dry-run
dots files stash dots:example --yes
dots files stash dots:example --restore
dots files edit                         # Select an entry or choose New mapping
dots files edit dots:example --target '${CONFIG}/example-new' --apply
dots files edit --new --repo dots --id example --source config/example \
  --target '${CONFIG}/example' --app example --category config \
  --strategy directory-link
```

Stashed entries have `enabled: false` in their owning catalog and remain visible
with status `stashed`. Omitted `enabled` means true; other types are invalid.
Disabled entries do not claim destinations, replace active resources or participate
in install/setup/direct linking. Track updates preserve disabled state. Discovery
still recognizes their repository sources as tracked, but their destinations are
not active claims. `files check` still checks actual source absence independently
of displayed status. Stashing on one machine does not unlink another machine;
repeat stash there to unlink a matching link, even if metadata is already disabled.
All machines must use a CLI version that understands `enabled`.

`edit` changes mappings, not source contents. It preserves unspecified fields,
stable IDs and repository ownership. `--source` is relative to the owning repo;
existing sources must be regular files or directories within that owner. Whole
directories require `directory-link`. `--target` accepts existing destination
templates or home/XDG paths normalized to portable templates. Other absolute
destinations remain unsupported. `--strategy` accepts link/directory-link/copy,
but live copy installation remains unsupported.

With `--new`, specify an available `--repo`, unique `--id`, `--source`, `--target`,
`--app` and `--category`; interactive mode collects missing values. New mappings
inherit the repository's platforms unless `--platforms` is given. `--platform`
updates only that target override; without it `--target` updates the common target.
Unspecified overrides remain unchanged. Shared-field edits validate ownership
conflicts across all applicable platforms. Live apply is for the current platform.

By default edit only saves catalog metadata. It explicitly reports that existing
links remain; use `--apply` during the edit to migrate the current old/new mapping.
Live edits also reconcile unchanged historical targets recorded in the installation
receipt, but never scan for arbitrary old links. Unrelated links, unsafe parents,
source/target overlap and observed drift block application. Editing a stashed
entry keeps it disabled; restore it before requesting live apply.

Both commands default to interactive selection/review and final Cancel/Apply
confirmation. Gum is optional, with text fallbacks including a native numbered
selector when Bash is unavailable or on native Windows. Native mapping prompts
never launch a WSL Bash bridge. `--yes` bypasses prompts and requires explicit
IDs/fields. `--dry-run` takes precedence and writes no catalogs/state/locks; it
does not prompt. `--json` requires `--yes` or `--dry-run` and emits an undecorated
schema-1 object containing `action`, `status`, `dry_run`, `items` and, after apply,
`transaction`. Items carry qualified IDs, source/target paths, action status/reason
and old mapping paths for edits. Diagnostics go to stderr. Global presentation
flags precede the route; human paths use shared type colors/icons and wrap fully.
Delayed progress never runs in dry-run, JSON or redirected output.

Occupied regular destinations require `--backup` (or the existing backup preference)
for live replacement. `--no-backup` refuses them; it does not remove mandatory
installation/recovery baselines. Live changes retain verified snapshots. Catalog,
link and receipt edits share one transaction, preserving original installation
backup references when an owned target becomes intentionally absent. Undo restores
all three; ordinary uninstall can still restore a pre-install object at a suspended
destination. Results show transaction and undo commands. Metadata-only edits use
the same journal without creating an installation receipt.

Success/no-op/cancel return 0, validation or operation errors 1, syntax/nonterminal
usage errors 2, and interruption/EOF 130. These routes also use the native
PowerShell adapter; link capability failures are explicit, never silent copies.

## Check missing sources

`dots files check` reviews the same tracked catalog as `list` and removes approved
entries whose source paths are absent. It changes **catalog metadata only**:
source objects, target files/directories/links and installation receipts remain
untouched. It differs from `files remove`, which preserves usable local copies.

```bash
dots files check                         # Review entries, then confirm the batch
dots files check --repo dots --dry-run   # Read-only preview, no prompts
dots files check --yes                   # Remove every eligible entry in scope
dots files check --dry-run --json        # Machine-readable preview
```

Default scope, filtering and sorting match `list`: `--repo`, `--app`, `--category`,
`--status`, `--platform`, `--all-platforms`, and `--sort` have the same meanings.
`--status` filters the observed catalog status, while eligibility checks source
absence independently, including entries whose displayed status is a conflict.
Unknown repository IDs fail. Unavailable/excluded repositories are reported and
skipped without initialization. Missing sources in inactive platforms require
`--all-platforms` or the appropriate explicit platform selection.

Each candidate shows its ID, source, target and catalog-only action. Optional Gum
offers Skip/Remove entry, with Skip selected; otherwise a plain yes/no prompt
defaults to skip. The selected batch then requires Cancel/Apply confirmation.
Cancelling the final review changes nothing. EOF or Ctrl-C interrupts with 130;
UI errors never approve or fall through to another backend.

`--yes` selects all eligible entries without prompts. `--dry-run` takes precedence
and never writes catalogs, state, locks or journals. Nonterminal mutation requires
`--yes`; `--json` requires `--yes` or `--dry-run`. Empty/all-skipped results create
no transaction. Existing dangling source symlinks are reported for repair and
retained. Permission errors, symlinked ancestors and other uncertain observations
fail closed instead of being classified as missing.

Apply guards the reviewed composition, catalogs and absent paths; reappearing
sources or metadata drift require a new review. One journaled transaction covers
all selected catalogs. Results provide the transaction ID and `dots files undo ID`;
existing history/recover commands handle interruption. Undo uses prior catalog
metadata retained in the journal, without an optional retained-backup flag. Other
records, unknown metadata and replacement declarations retain their values/order.

Human output uses shared resource colors/icons, complete wrapped paths, semantic
statuses, counts and delayed progress. JSON and dry runs never animate. Redirected
output is plain unless human decoration is explicitly forced. JSON is always
undecorated: schema 1 contains `action`, `platform`, `dry_run`, `status`, `items`,
`sources`, and `counts` (`checked`, `eligible`, `selected`, `removed`, `skipped`).
Items retain catalog fields and add `source_state`, `eligible`, `reason`, and
`outcome`; dry-run candidates use `would-remove`. Applied results also include
the Store's `transaction` object. Preview `selected`/`removed` counts remain zero.
Errors go to stderr. Success, no changes and explicit cancellation return 0;
inspection/apply errors return 1 and invalid usage returns 2.

The same controller is available through the native PowerShell adapter; optional
Gum remains capability-checked and the text fallback does not require Bash.

## Interactive tracked-config browser

`dots files browse` searches tracked configs applicable to the detected platform,
one resource at a time. Optional `--repo`, `--app`, `--category` and `--status`
filters use the existing catalog fields. Search includes qualified ID, app, status
and source/target paths. Details show the full paths, strategy, platform and
ownership metadata. The picker starts with metadata; Alt-C explicitly requests a bounded content preview. Unavailable/excluded sources
are reported without initialization. Empty filtered results exit successfully.

The browser prefers FZF with live previews, falls back to Gum, then uses a numbered menu; `TERM=dumb`
uses the plain menu. It requires terminal input, output and diagnostics. Help/completion never
launch a UI, and existing list/show JSON and path interfaces are unchanged.
For scripts use the existing list/show and link/remove commands. The browser has
no `--json`, `--yes`, discovery, platform override, editor or batch mode.

After selection choose **Back to list**, **Link**, **Stop managing**,
**Retained backups: on/off**, or **Exit**. Back to list is the default. Stop managing
uses the existing removal semantics: preserve the repository source, materialize
matching managed links, retain regular configs and leave absent targets absent.
Conflicts, protected links, missing sources and other blocked plans display the
planner's reason without offering Apply.

Link or Stop managing presents the actual managed-operation plan and backup mode,
then **Back**, **Apply** and **Exit**, with Back as the default. Only Apply executes
the approved operations and guards. Source, target or catalog drift refuses the
operation instead of silently recomputing the preview. Changing backups requires
returning to details and obtaining a new preview; it changes this session only,
starting from the existing backup preference. Existing-target replacement still
requires a retained backup, and unrelated/generated links remain protected.

After success, transaction/backup IDs are shown where present. Choose Return to
list or Exit; the catalog is refreshed before returning. Failures stop browsing
and preserve the transaction engine's rollback/recovery behavior. Browsing,
details, backup toggles, preview, Back and Exit create no state directories, locks
or journals. Operation planning may hash contents for drift protection but does
not display them unless content preview is explicitly selected.

Explicit Exit returns 0; Ctrl-C and plain-menu Escape/EOF return 130. Gum retains
the [documented Escape/error ambiguity](presentation.md#optional-gum-interactions).
Other tool/validation/operation errors return 1; invalid CLI syntax returns 2.
The chosen backend is fixed for the session, with no fallback after a UI failure.
Inherited Gum colors and Dots presentation controls are respected without sourcing
shell configuration. The browser and its adoption/stop-managing actions remain unsupported on native Windows; bounded setup/recovery uses the separate native adapter.

## Ownership and formats

[.dots/sources.json](../.dots/sources.json) declares composition with schema 1 and
`sources` containing `id`, repository-relative `path`, allowed `roots`, `platforms`
and optional `excluded`. Dots owns common configurations; Androidots contributes
Termux-specific sources. Windots supplies the native VS Code settings target; its other resources remain unmapped. Neovim owns its catalog at `config/nvim/.dots/files.json`.
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

The JSON catalog defines resource ownership and target mappings in [data contracts](specification.md). Managed file operations consume that ownership and follow the transaction rules in [safety](safety.md).

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

Interactive human confirmations prefer Gum's **Cancel / Apply** menu, with Cancel
selected by default. Missing tools, dumb terminals or redirected output retain
the text prompt. JSON retains its stderr text prompt when stdin is a terminal;
`--yes` and `--dry-run` bypass Gum. Explicit Cancel makes no changes; selector
failure stops without another prompt, and Ctrl-C exits 130. This applies to the
existing shared approval point, including recovery and backup restoration. See
the [interaction contract](presentation.md#optional-gum-interactions).

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

### Verbose action details

Use `-v`/`--verbose` with `install`, `uninstall`, `add`, `link`, `remove`/`rm`, `undo`, `recover`, `backups restore`, `stash`, `edit`, or `check` to see actions and unchanged/skipped reasons. For example:

```bash
dots files add ~/.config/example --backup --verbose
dots files install -v
dots files undo TRANSACTION_ID --dry-run -v
```

Existing previews and summaries remain. Additional stderr rows show verified recovery copies, completed links/copies/metadata updates, retained backup locations and IDs, cleanup, and rollback. File links read `repository source -> installed target`. Colors and icons follow file-type/MIME rules; progress resumes between rows. `edit` without `--apply` and `check` still change only catalog metadata as documented, even with verbose enabled. `--json` suppresses the additional trace; dry runs label intentions rather than reporting completed writes. See the [verbose presentation contract](presentation.md#verbose-operations). The existing `discover --system --verbose` option continues to expand discovery listings.

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
operation is implemented. Journals are outside Git and never contain configuration contents
except catalog and installation metadata. The shared filesystem adapter also supports bounded native Windows installation/recovery; adoption and stop-managing remain POSIX-only. See [safety](safety.md#managed-file-transactions).

## Checkout installation and restoration

`dots files install` links all applicable mapped resources and retains verified backups before replacing regular objects. `dots files uninstall` restores installation-owned targets, preserves drift and does not remove source catalog entries. Both share the transaction Store and expose existing history/undo/recovery. This differs from `files remove`, which materializes configs and removes catalog entries. See [installation](installation.md) for all options, source updating and platform boundaries.

Catalog resources may provide an optional `targets` object mapping platform names to target strings or null, overriding `target` only on that platform. Native mappings add `${APPDATA}`, `${LOCALAPPDATA}`, `${NVIM_CONFIG}` and `${POWERSHELL_PROFILE}`. NVIM_CONFIG honors XDG_CONFIG_HOME, otherwise LOCALAPPDATA; the PowerShell adapter passes the current host's profile path. A missing native profile path remains unmapped instead of guessing. Inventory uses the same resolution as installation.

### Consolidated Git platform selector

The fixed `dots:git` directory mapping also plans its ignored `gitplatform`
selector when its entry point includes that filename. Install, link, mapping
apply and stash restoration select the native `termux`, `linux`, `wsl` or
`windows` regular overlay. Previews expose this companion separately. This
bounded source-directory operation adds no general nested-target permission or
catalog schema. Stash keeps repository sources and the selector. Correct
pre-existing links are not claimed; changed companions use installation receipts
and retained baselines for undo/uninstall. Direct Git linking therefore retains
its installation baseline even with optional snapshots disabled.

See the [Git config guide](../config/git/README.md) for the guarded migration from
the retired Androidots Git catalog/import mappings and obsolete home overlay.

## Interactive file pickers

`add`, `link`, `stash` (including `--restore`), `edit`, `remove`/`rm` and `show`
open a picker when operands are omitted in a terminal. `browse` uses the same
rich resource selector. FZF is preferred, then Gum, then a numbered menu;
`TERM=dumb` uses the plain menu. Optional tools are never installed automatically.

```sh
dots files add                         # Choose eligible registered configurations
dots files add --pick ~/.config/nvim  # Choose a subset under an explicit path
dots files add --scan --pick          # Choose a subset of registered discoveries
dots files link --pick --dry-run      # Select, then preview without applying
dots files stash                     # Multi-select enabled resources
dots files stash --restore           # Multi-select disabled resources
dots files edit                      # Choose a mapping or New mapping
dots files show                      # Select one resource to inspect
dots files remove                    # Select resources to stop managing
```

Explicit operands without `--pick` retain their behavior. Only add accepts
operands together with `--pick`; supplied paths narrow its eligible discovery
inventory. `add --scan` without `--pick` still selects all eligible discoveries.
Directory-link adoption requires explicit paths without a picker. Link lists
active-platform enabled mappings, stash lists enabled mappings, restore lists
disabled mappings, and remove lists active-platform mappings. Conflicts remain
visible and the planner decides whether the complete selection can proceed.
Existing command filters constrain selection; empty inventories exit without changes.

Batch selectors support Tab/Shift-Tab to mark and move, Ctrl-A to select matching
rows, and Ctrl-D to clear selection. Enter accepts marked rows, or the highlighted
row when nothing is marked. Edit, show and browse select one resource. Enter
advances to the existing detail/plan flow; it never grants approval to mutate.
Alt-P hides/shows the preview, Alt-C cycles details/source/target content, and
Alt-J/K scroll it. FZF/plain-menu Esc and Ctrl-C cancel with status 130. Gum retains
its [Escape/error ambiguity](presentation.md#optional-gum-interactions).
Other selector failures stop without retrying another backend. Fallbacks offer equivalent selection and
subsequent detail/plan review without a live content pane.

Previews show full paths, owner, status, strategy and intended semantics. Content
is read only after Alt-C, capped at 64 KiB/200 lines; directories show up to 200
immediate entries. Excluded paths, detected credentials, binary/special files and
unsafe links have no content preview. Control characters are escaped. Detection
is conservative, not a guarantee that an arbitrary config contains no secrets.
Source and target content are inspected independently. Preview metadata is
informational; the guarded operation plan and existing backup approval follow.

`--pick --dry-run` explicitly permits selection followed by a read-only plan.
Plain `--dry-run` never prompts. `edit --pick --dry-run` requires explicit edit
fields; source/target text entry remains available during ordinary interactive
editing, with searchable repository/strategy choices. `--pick --new` is invalid:
use `edit --new` for direct mapping creation. `--pick` rejects `--yes`, `--json`
and nonterminal streams. Help/completion and explicit data/path interfaces never
open a selector. Recovery commands continue to require explicit IDs.

## Native Windows commands

The PowerShell dispatcher reaches the shared catalog, adoption, mapping, linking, browser, installation and recovery controllers. File pickers use native FZF PowerShell previews, with Gum/numbered fallbacks; selection still requires a later reviewed operation. The catalog resolves app destinations individually rather than assuming `~/.config` for Windows apps. See [native PowerShell](powershell.md) for destinations, link capability rules, supported engines and pending native acceptance. Both shell frontends must remain synchronized in future file changes.
