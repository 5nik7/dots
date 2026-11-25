# File catalog

**Status: Inventory, metadata, bounded adoption/link/remove/repair, checkout installation and recovery implemented; general profile installation remains proposed.**

`dots files` reads the active profile, locates its sources, and reports the state of each destination. Files commands require Python 3.9+. Repository discovery also uses Git. Bash and native PowerShell route path adoption and link registration through the shared controller. See [checkout installation](installation.md) for setup, uninstall and recovery.

Slow catalog/system discovery, browser loading, planning and file operations use [terminal progress](presentation.md#operation-progress). Preparation, apply and reverse recovery have separate item counts; final results retain transaction and recovery details. `DOTS_PROGRESS=never` disables the display. JSON, raw source/target queries and dry runs never animate.

## Files rollback and recovery

Managed files operations preflight the complete plan before applying changes. A failed apply rolls completed reversible operations back in reverse order; interrupted transactions retain recovery records. Use `dots files history` to find a transaction, `dots files undo ID` for a completed operation, or `dots files recover` for interrupted work. Undo checks for post-apply drift and refuses destructive restoration. Retained user backups are optional; mandatory rollback protection remains active. See [safety and recovery](safety.md) for boundaries, especially package or other external effects.

## Commands

```bash
dots files sources
dots files browse
dots files ls
dots files list --sort app
dots files list --repo termux --platform termux
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
stderr. Terminal reports abbreviate HOME as `~`. The default and verbose layouts show
resource counts, status and labeled paths. Empty results are explicit. Piped lists
use tab-separated ID, status, source and target unless a human view is explicitly selected.
Piped sources retain ID, availability, repository root and platforms. Success is 0; validation/I/O
errors are 1 and invalid command syntax is 2.

### List views

`dots files ls` and `dots files list` open the same listing. The **short** view is the terminal default. At 50 columns and up, a linked file that fits shows its repository source and installed destination on one line. A stashed entry shows its qualified ID.

```text
 󰈔 ~/dots/shells/zsh/zshrc -> 󰌷 ~/.zshrc
  dots:waybar
```

Below 50 columns, each linked file has its own source line. Its destination starts on the next line with two spaces and `󱞩`, or `->` when icons are off. A linked directory that fits stays on one line, with a single directory icon on the source side when icons are enabled. Longer paths retain their basenames as intermediate directories are shortened. The short view uses the theme’s `dark_foreground` color for link arrows at every width.

The narrow layout uses headings such as `[missing]` for exceptional statuses. With status grouping enabled, stashed entries form a compact list of qualified IDs at the end. An explicit `--sort` keeps the selected order. Setting `apps.files.group_by_status` to `false` also preserves the catalog order. If two shortened path pairs look alike, the listing gives them more room and shows their qualified IDs when needed.

| View | Option | Contents |
| --- | --- | --- |
| Short | `-s`, `--short` | Compact path pairs and status rows |
| Default | `--default` | Resource ID, status, source and target |
| Verbose | `-v`, `--verbose` | Default fields plus application, category, ownership, strategy and mapping details |

`--view short|default|verbose` selects the same layouts. A view flag also works in a pipe. Use `--json` for the complete catalog with its original paths. To change future terminal and Files menu listings, use the Config browser or set a preference directly.

```sh
dots config browse --query apps.files
dots config set apps.files.list_view verbose
dots config set apps.files.group_by_status false
```

Setting `apps.files.list_view` to `short` restores the shipped view. `apps.files.group_by_status` defaults to `true`. The stashed glyph uses `icons.status.stashed`. With icons disabled, its row carries a text label.

Tracking writes the core registry and selected profile metadata in one guarded, retained transaction. The result includes an undo ID. Legacy schema-1 catalogs retain their compatible single-file writer. Quote destination tokens to leave them literal:

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

`dots files stash` disables tracked resources in the active profile while keeping their
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
dots files edit termux:os-release --category config --dry-run
dots files edit --new --repo dots --id example --source config/example \
  --target '${CONFIG}/example' --app example --category config \
  --strategy directory-link
```

Stashed entries have `enabled: false` in their profile mapping and remain visible
with status `stashed`. Omitted `enabled` means true; other types are invalid.
Disabled entries do not claim destinations, replace active resources or participate
in install/setup/direct linking. Track updates preserve disabled state. Discovery
still recognizes their repository sources as tracked, but their destinations are
not active claims. `files check` still checks actual source absence independently
of displayed status. Stashing on one machine does not unlink another machine;
repeat stash there to unlink a matching link, even if metadata is already disabled.
All machines must use a CLI version that understands `enabled`.

`edit` changes mappings, not source contents. It preserves unspecified fields,
IDs unless `--id` is supplied, and repository ownership. `--source` accepts a rooted token, an absolute path or an owner-relative path;
existing sources must be regular files or directories within that owner. Whole
directories require `directory-link`. `--target` accepts existing destination
templates or home/XDG paths normalized to portable templates. Other absolute
destinations remain unsupported. `--strategy` accepts link/directory-link/copy,
but live copy installation remains unsupported.

With `--new`, specify an available `--repo`, unique `--id`, `--source`, `--target`,
`--app` and `--category`; interactive mode collects missing values. New mappings
inherit the source's platforms unless `--platforms` is given. `--platforms` also
updates an existing resource's core registry eligibility. `--platform` selects that
platform's base profile; without it the active leaf profile is edited. Each profile
has one target per mapping. Eligibility changes validate other profiles, while
implementation edits affect only the selected profile. Live apply requires the
active profile. Legacy schema-1 catalogs retain their target-override semantics.

`--category NAME` updates the selected profile's category. It can be combined with `--id` to rename and reclassify a mapping in one transaction.

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

## Relink and prune the active profile

| Command | What it does |
| --- | --- |
| `dots files relink` | Creates missing links, repairs verified broken links, and converts byte-identical regular files to links after backing up the files. |
| `dots files prune` | Removes profile mappings whose repository sources have been deleted. Each destination stays in place, including a dangling link. |
| `dots files sync` | Prunes selected stale mappings and relinks eligible files using the resulting profile. A combined apply has one transaction ID for undo. |

All three commands preview by default. Add `--yes` to apply eligible changes, or `-i` / `--interactive` to choose items and confirm the batch. Use `--repo`, `--app`, or `--category` to narrow the active profile. Add `--verbose` to see healthy and skipped entries as well. Use `--json` for a structured preview or `--yes --json` for the applied result.

```sh
dots files relink --app tmux
dots files prune -i
dots files sync --dry-run --json
dots files sync --yes
```

Correct links keep their identity. An edited file, a working link to a different source, or an occupied directory stays available for review with `dots files repair`. Copy mappings keep their strategy. Pruning preserves the registry and original uninstall receipts. It skips unavailable repositories, dangling source symlinks, and generated theme artifacts that have yet to be published.

When a destination needs manual review, the command exits with status 1. Other eligible changes can still be applied. The JSON status is `partial` if a transaction completed with unresolved items, or `unresolved` if no changes could be applied. Use `dots files undo TRANSACTION` to reverse an applied batch.

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

## Repair managed destinations

`dots files repair` scans catalog mappings on the current platform and reviews destination repairs. It automatically queues missing file/directory links when the catalogued source exists and broken links with verified Dots ownership. In a terminal, it also helps resolve unverified broken links and occupied destinations through explicit choices. Unlike `files check`, it retains entries whose sources are missing. It does not recover source contents, check configuration syntax, discover nested broken files, relocate a checkout, install the launcher, acquire repositories or regenerate themes.

```bash
dots files repair                         # Resolve issues, review the queue, then Cancel/Apply
dots files repair --dry-run               # Inspect without writes or prompts
dots files repair --yes                   # Apply automatic repairs only; preserve unresolved issues
dots files repair --dry-run --json        # Machine-readable inspection
dots files repair dots:kitty --yes        # Limit to named resources
dots files repair --repo dots --app kitty # Filter the scan
```

Optional qualified resource IDs and `--repo`, `--app`, `--category` filters intersect. Unknown IDs/repositories fail; results are sorted by ID. Disabled, inactive, replaced and unmapped resources are skipped. Inactive resources appear only when named explicitly. Unavailable/excluded repositories remain visible without acquisition. Live repair is restricted to the detected platform, using its existing app destination adapters; there is no platform override.

Correct working links are unchanged and never adopted into installation ownership. A `replaces` declaration naming an absent or inactive mapping does not by itself block repair or turn a healthy link into a conflict; actual competing catalog claims do. Regular files, directories, working links pointing elsewhere and unverified broken links require an explicit helper choice. Sources must be regular files or owned directories matching the link strategy; copy mappings are reported unsupported. Special objects, ownership conflicts, unsafe parents and overlapping source/repository/state destinations remain blocked. No source or catalog edits occur.

For automatic relinking, a broken link needs either a same-resource installation receipt whose `after` digest still matches the link, or matching evidence from the latest completed transaction touching its destination. Only catalog file actions (`add`, `link`, `install`, `edit`, `restore`, `repair`) establish transaction evidence, and a receiptless historical link must remain within its owning source repository. A later undo/theme/other action supersedes older evidence; receipt-owned drift cannot fall back to history. The helper can explicitly authorize an ordinary unverified link, including a retired Androidots path, or same-resource drift. Generated-state links and destinations owned by another resource, including a theme receipt for a missing target, remain protected. Use `dots theme files check` to inspect theme connections.

Bare terminal invocation opens the issue helper when findings are unresolved. It prefers terminal FZF with metadata previews, then Gum, then a numbered fallback, including native Windows without Bash. Details show the catalog source, destination, current object/link, reason and backup policy. Choose **Relink to catalog source** or **Back up and replace with catalog link** where available; **Back** and **Skip for this run** preserve the object. Decisions only change the queue. Automatic repairs start queued and can also be skipped. Blocked issues show a next-step command. No file contents are previewed.

Choose **Review queued repairs** to see the complete batch, then confirm once with Cancel selected by default. With no unresolved findings, the command goes directly to its ordinary batch confirmation. **Cancel repairs** and final Cancel exit 0 and discard every queued decision; selector Escape/Ctrl-C/EOF interrupts with 130. Failed selectors never approve a repair. Optional Gum confirmation has a plain yes/no fallback.

`--yes` applies automatic repairs only: it does not answer ownership or replacement questions. Run the bare command to resolve those issues. JSON, dry-run and redirected execution never open the helper or infer choices. Nonterminal mutation requires `--yes`. `--dry-run` overrides `--yes`, never prompts, and writes no state, locks, catalogs or journals. Cancellation and an unchanged run likewise create no managed state. `--verbose`/`-v` shows unchanged/skipped reasons and transaction events. JSON and dry runs never animate; human views reuse shared resource styling and wrap full paths.

Queued repairs can be applied while other entries remain unresolved. Invalid shared metadata, an unfinished transaction, or source/target/catalog/receipt/evidence drift blocks apply and requires a new review; approval never triggers a fresh plan. Occupied directories and source trees are hashed for drift protection when preparing a choice. The complete batch is preflighted and applied through one retained transaction. Links and installation receipt updates roll back together, and existing first-install backup references survive repair, including explicitly approved same-resource drift. Newly managed repaired destinations retain their pre-repair baseline. Results provide the transaction ID and `dots files undo ID`; undo restores the immediate pre-repair object, while uninstall retains its original-backup semantics. History/recover handle interrupted work.

`--json` requires `--yes` or `--dry-run`. Its undecorated schema-1 result contains `action: "repair"`, `platform`, `dry_run`, `status`, `items`, `sources`, and `counts` (`checked`, `eligible`, `repaired`, `unchanged`, `skipped`, `unresolved`). Items retain catalog fields and add `repair_action` (`link`, `relink`, `unchanged`, `skipped`, `unresolved`), `reason`, and `outcome`. Preview candidates use `would-link`/`would-relink`; applied candidates use `repaired`. Interactive replacement adds the human action `replace-with-backup`; helper decisions are not accepted through JSON. An applied result includes the Store `transaction` object. Status is `preview`, `unchanged`, `complete`, `partial`, `unresolved` or `cancelled`. Skipped helper issues remain counted as unresolved. Diagnostics go to stderr.

Exit 0 means no unresolved findings, a repairable preview, completed repairs or explicit cancellation. Exit 1 means unresolved findings or an inspection/apply failure, including when some safe repairs succeeded; inspect the JSON counts/status. Usage errors return 2 and interruption returns 130. Read-only preview may therefore return 1 while still producing a useful report.

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
shell configuration. Native Windows uses the shared controller and native interactions; bounded setup/recovery uses the separate native adapter.

## Ownership and formats

[.dots/sources.json](../.dots/sources.json) declares composition with schema 2 and
`sources` containing `id`, repository-relative `path`, allowed `roots`, `platforms`
and optional `excluded`. Dots owns shared sources; `termux`, `windows` and `nvim`
own their declared roots. Missing source directories are unavailable. Secrets and
third-party PowerShell/Rainmeter ownership remain excluded; inspection never
initializes private or optional sources.

Each profile has one `files` array. You can write a row directly in `profile.json` and inspect it immediately with `dots files list`. Use a local ID, a portable source, one target, an application, a category and a strategy.

```json
{"schema": 1, "id": "linux", "files": [{
  "id": "example", "source": "${PROFILE}/config/example", "target": "${CONFIG}/example",
  "app": "example", "category": "config", "strategy": "directory-link"
}]}
```

`${DOTS}` names the checkout, `${PROFILE}` names the directory containing the declaration, and `${THEME}` names the stable published theme. The most specific source owner supplies the qualified ID. For example, `${DOTS}/config/nvim` belongs to `nvim`. Child profiles inherit mappings by qualified ID. A child row can override one mapping or disable it with `enabled: false`.

[.dots/files.json](../.dots/files.json) retains explicit platform eligibility, reserved IDs and rename history. An effective profile mapping supplies the installation definition. A new hand-written ID inherits its owner's eligibility until explicit limits are recorded. Grouped profiles retain their earlier whole-owner inheritance and owner-relative sources. Older receipts and catalogs remain readable.

### File ID renames

`dots files edit OWNER:OLD --id NEW` changes a local resource ID within its owner.
Use `--dry-run --json` to inspect the complete change; normal interactive edits
review before approval, and explicit noninteractive edits use `--yes`. The mapping
editor offers ID editing; Config → Set → Files also offers Rename ID.

A rename updates the core registry, all explicit profile mappings and all
`replaces` references, preserving inherited definitions and disabled resources.
Registry-only entries and missing sources can be renamed without installation.
Combine `--id` with mapping fields if needed: source/target/strategy affect only
the active leaf or the base selected by `--platform`, while the ID changes across
the checkout. `--platforms` retains its global eligibility meaning. Optional
`--apply` reconciles only the active profile's supported live links.

The first effective rename upgrades the registry to schema 3:

```json
{"schema": 3, "resources": [{"id": "dots:renamed", "platforms": ["linux", "wsl"]}], "renames": {"dots:example": "dots:renamed"}}
```

History maps qualified old IDs directly to current IDs within the same owner.
Successive renames flatten the map. Current and historical IDs cannot collide;
old IDs remain reserved for recovery. Commands given an old ID explain its current
replacement. An unchanged current ID is a no-op. Schema 2 remains readable and
ordinary edits do not upgrade it; legacy catalogs require a core registry before
using the new rename operation. Other installations sharing a schema-3 registry
need the updated CLI. Bulk config edits cannot reuse historical IDs.

One guarded, retained transaction owns the registry, affected profile files,
current receipt identities and optional live operations. Receipts keep original
backup pointers. Other installations recognize historical IDs on read, without
cross-platform state access. Historical journals are immutable. Use the returned
`dots files undo ID` for drift-aware reversal; interrupted operations use normal
`dots files recover ID`.

IDs, applications and categories use lowercase letters, digits, `_` and `-`,
starting with a letter. Portable source suffixes must stay within their owner. Targets
start with `${HOME}`, `${CONFIG}`, `${BIN}`, `${TERMUX}` or `${PREFIX}` on POSIX and contain no traversal.
CONFIG uses XDG_CONFIG_HOME or HOME/.config; BIN is HOME/.local/bin; TERMUX is
HOME/.termux and resolves only on Termux. A null target records an unmapped source.
PREFIX resolves the explicit Termux `PREFIX` environment value and is unmapped on other platforms or when unset. It must be an absolute non-root directory without traversal or control characters. Absolute paths beneath it can be converted back to `${PREFIX}` by mapping/registration commands. Existing Windows application destination tokens remain supported.
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

WSL inherits the Linux file mappings. Its base profile overrides two resources, `dots:file-config-eza-themes-catppuccin-mocha-mauve-yml` and `dots:vivid`, to disable them. An edit to an inherited mapping can be scoped to the WSL profile.

In the effective flat array, a child override keeps the parent mapping's position. New qualified IDs follow inherited mappings in the child's declaration order.

On Termux, Config groups `termux:config-json` under `pkgs`, `termux:config` under `codex-termux`, `termux:config-toml` under `mise`, and `termux:method` under `zsh-system-clipboard`. For example, `dots config get 'apps.mise.files["termux:config-toml"]'` reads the mise mapping. The former `apps.config.files` view and its qualified lookups still reach these resources.

An explicit theme connection may live below a managed application directory. Operations verify the parent link against its active directory mapping and guard the physical destination. A theme link follows the stable active pointer across publications. A link pinned to a specific generation requires review.

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
`config/`; Termux configs map into `profiles/termux/config/termux`; home dotfiles have explicit
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

The explicit gitmux home-file mapping imports `~/.gitmux.conf` into `config/gitmux/gitmux.conf` on Termux, Linux and WSL. The catalog resource is `dots:gitmux`, application `gitmux`, with the ordinary file-link strategy. It has no native Windows destination. Use `dots files show dots:gitmux` to inspect it, or `dots files link dots:gitmux --backup` to link a checkout's source with the normal conflict/backup policy. Gitmux reads this file through the tmux integration's explicit `-cfg` argument; see [status configuration](themes.md#gitmux).

## Add, link and find

```sh
dots files add ~/.config/example/settings.toml --dry-run
dots files add ~/.config/example/settings.toml --global
dots files add ~/.example --source config/example/dotfile
dots files ln '${PROFILE}/config/example/settings.toml' '${CONFIG}/example/settings.toml'
dots files link -s '${THEME}/yazi' -t '${CONFIG}/yazi/flavors/dots.yazi'
dots files fd --dry-run --json
dots files find ~/Documents
dots files fd --path "${PREFIX}/etc" --dry-run
```

`add PATH` imports an ordinary file under the active profile. `-g` or `--global` places imported content under the checkout. Both save the mapping only in the current profile. A known destination rule supplies the relative source layout. For a previously unmapped home file, enter the desired source during review or pass `--source`. An existing repository source or link can be registered in place. If it already belongs to a profile, the theme, or a nested repository, omit `--global` to retain that ownership.

`link` and `ln` accept source first and target second. Supply either operand using its flag or use two positionals. The source and destination parent must exist. A missing final target is created with its profile mapping. A correct pre-existing link keeps its ownership. If the Yazi flavor still has the old two-link layout, use the [installer migration](installation.md#declared-ownership) so its backups remain usable on uninstall. Existing resource-ID and picker forms remain available.

`find` and `fd` review existing links to Dots, profile and generated theme sources. With no search roots they search managed locations. Give an existing directory positionally or with `--path DIR` to search recursively from it. On Termux, `dots files fd "${PREFIX}/etc"` and `dots files fd --path "${PREFIX}/etc"` search the same tree. You can repeat `--path`, combine it with positional roots, or pass an individual link positionally.

Review proposed pairs individually, preview with `--dry-run` or `--json`, or select eligible entries with `--yes`. Registration records the selected pairs together and preserves their link text and uninstall ownership. Two links to the same source can have separate mappings. A repeated scan skips pairs already represented in the effective profile. A generated directory mapping covers its contents, including the previous individually linked Yazi flavor files. The broader `add --scan` also finds ordinary files eligible for adoption.

## Register files already in the repository

`files add` accepts an existing link into an eligible source repository or the repository source itself. It infers the owning repository and saves the resource identity in the core registry and its mapping in the active leaf profile. Repository directories use one `directory-link`; files use `link`. Registration does not copy or relocate source content. Nested links remain entries in the directory and their referents are never imported. Ordinary unmanaged-directory adoption keeps its file-by-file default and `--directory-link` option.

```sh
dots files add ~/.termux --dry-run
dots files add ~/.termux                         # Register the existing directory link
dots files add "$PROFILE/config/termux" --dry-run
dots files add config/example --target '${CONFIG}/example' --dry-run
dots files add --scan --dry-run                  # Ready sources and eligible imports
```

An existing link supplies its destination directly. For source operands, a unique existing mapping or observed link in registered user locations takes precedence over a reverse mapping from the location registry. Missing or ambiguous destinations require interactive input or `--target DESTINATION`. That option accepts one explicit repository source, without `--scan` or `--pick`. Dry-run never prompts and reports `needs-target`; noninteractive apply requires a resolved destination. Explicit `--repo` must match the inferred owner.

Repository discovery groups known app directories, proposes destinations and strategies, and retains individual sources when no directory boundary is known. The Add picker combines repository sources, eligible imports and existing links. Explicit repository-directory picker operands select that directory as a whole. Scans include ready sources, report unresolved/excluded candidates as skipped, and preflight all selected conflicts before changing anything. Repository enumeration uses Git exclusions; user-location imports still work in fixtures/checkouts without Git enumeration. Neither discovery nor ordinary startup searches the whole home directory. Known private/generated exclusions and nested repository boundaries remain enforced.

New IDs start with the normalized source filename. For example, `${PROFILE}/system/etc/os-release` registers as `termux:os-release` when that ID is free. Files recognizes `system/etc` sources and `${PREFIX}/etc` destinations as configuration. When a filename is taken within its owner, Files adds parent directory names until it finds an available ID. It can also use the destination to distinguish multiple links to one source. Retired names remain reserved. An existing source–target mapping keeps its ID and platform eligibility. Only the active profile receives the new mapping.

A correct pre-existing link keeps its original link text and object identity and is not claimed by installation. Registration undo restores metadata; uninstall leaves that link alone. Newly created links receive installation receipts and retained recovery baselines. Occupied ordinary targets require `--backup`; unrelated links, broken or chained source links, unsafe ancestors, unsupported objects and conflicting claims are refused. The complete metadata/link/receipt batch uses guarded transactions, rollback and normal drift-aware undo. Catalog, source, destination or location changes after preview require a fresh review.

JSON keeps its existing envelopes. Registration candidates add `kind`, `candidate`, `target_spec`, `strategy` and `profile`; repository discovery retains `status: discovered` and adds `registration_status`. Readiness/action values include `register-existing-link`, `register-and-link`, `needs-target`, `excluded`, `skipped` and `unchanged`. Existing redirected catalog columns remain intact. Human views show the intended strategy, target, profile and unresolved reason using shared presentation controls.

Bash and native PowerShell use the same controller and metadata. Native Windows uses its application destination tokens and native filesystem adapter; unsupported reparse points and missing symbolic-link capability fail explicitly. Native PowerShell 5.1/7 filesystem and terminal acceptance remains separate from portable controller tests.

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
`dots:example` require that resource to exist in the catalog. Add previews
the available ID for each new mapping. Use
`files list` to obtain qualified IDs for subsequent commands.

Add copies and verifies imported configurations under the selected source root,
records catalog entries and links the original locations to the sources. It uses
individual files by default, preserving unrelated files and directory structure.
`--directory-link` requires explicit paths and owns the whole directory. Identical
existing sources may be reused; different occupied sources are refused. For home files outside registered locations, supply the intended source path. Symlinked parent paths,
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

If you deleted the repository source, `dots files rm OWNER:ID` removes its profile mapping and leaves the destination as you found it, including a dangling link. You can also remove a mapping marked `replaced`. For example, when `dots:tmux` owns the live link, `dots files rm termux:tmux --dry-run` previews just the old Termux mapping. The winner keeps its link and installation history. Removing an inherited mapping disables it in the active profile.

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

Bare `dots files add` shows one searchable scan list grouped by action. Each row shows a short action label and one path. Use the details preview for the full source and target. You can mark candidates across groups and review them together.

Explicit operands without `--pick` retain their behavior. Only add accepts
operands together with `--pick`; supplied paths narrow its eligible discovery
inventory. `add --scan` without `--pick` still selects all eligible discoveries.
Directory-link adoption of unmanaged directories requires explicit paths without a picker; repository directory registration is available in the picker. Link lists
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

## Platform source names

Use `termux:NAME` and `windows:NAME` for platform resources and `--repo termux` or `--repo windows` for filters. `androidots` and `windots` are rejected as CLI source names with a replacement hint. Legacy catalog/receipt IDs are recognized internally without rewriting history or changing backup ownership. See [identity compatibility](specification.md#canonical-platform-file-identities).
