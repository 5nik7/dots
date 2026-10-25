# Safety and Recovery Model

**Status: Implemented managed file, theme, Git and checkout workflows**

Safety is a core product feature of `dots`, not a wrapper around destructive file operations. This document is authoritative for planning, mutation, backup, rollback, undo, package, hook, repository, and secret behavior.

## Repository Editing Boundary

Ordinary task-relevant edits to repository source files, including live dotfiles and scripts, are allowed in the existing checkout under [AGENTS.md](../AGENTS.md). Inspect Git status and preserve unrelated, uncommitted, and untracked work. Git history provides recovery for committed repository edits; reverting a commit does not recover uncommitted work or reverse external machine effects.

The transaction guarantees below govern managed installation, target replacement, backup, and undo operations. Permission to edit their source code does not authorize executing those operations against the live machine.

Theme setup and refresh validate required generated output types/readability
before reusing or publishing a generation. Missing outputs are rebuilt into new
state directories; existing payloads are retained. Setup repairs missing managed
publication pointers through its file transaction and preserves the original
installation baseline. Completeness is not content authentication: normal
fingerprints detect source changes, and foreign/unsafe pointers still refuse
automatic replacement. Shell startup only reads publication state and maintains
its existing rebuildable caches; it does not perform this repair.

## Bash Command Framework

The Bash dispatcher reads trusted command directories and optional static metadata.
Help, listing, validation, and completion never run extensions. Direct execution
runs trusted executables with the user's privileges and inherited streams; no
sandbox, mutation classification, transactional guarantee, or automatic elevation
is implied. Symlinked extensions are allowed. The shared presentation library does
not filter/redact extension output. Tests use disposable commands and owned roots.
See [decision 0006](decisions/0006-bash-command-framework.md).

## Existing Shell Startup

Termux's Bash/Zsh startup hook may create a marked default tmux session and attach its client. It retains the outer shell, never deletes detached sessions or adopts an unmarked name collision, and does not install dependencies or reload the server. Repeated initialization does not reattach after deliberate detachment. `DOTS_TERMUX_AUTOSTART=0` disables the hook; failures leave a plain shell. This bounded terminal-session behavior is separate from managed filesystem installation. See [startup guards](shell-init.md#termux-tmux-startup).

The existing Zsh configuration uses user-local completion, Vivid, FSH, and Catppuccin caches outside managed-file transactions. These are rebuildable generated data. FSH's native INI loader builds in a temporary Dots cache directory. The adapter atomically persists validated data as a regular `current_theme.zsh` in the existing `FAST_WORK_DIR`, retaining the last good startup theme on preparation failure. Before replacing a non-Dots selection it creates a unique private backup of the prior script and compiled companion, preserving symlink identity. Stale `.zwc` code is invalidated; directory conflicts are refused and backups are not automatically pruned. These are cache/selection writes outside the managed theme-publication journal. User overlays remain trusted executable shell code. Completion generation validates successful output before atomic publication; failed output is not evaluated. Ordinary startup retains its existing optional plugin bootstrap and private/local sourcing behavior. Tests use copied public dependencies and synthetic private modules under owned roots; they must never run the live startup chain against the developer's home. See the [Zsh guide](../shells/zsh/README.md).

The default [Deja integration](../shells/zsh/README.md#deja-suggestions) is third-party executable shell code, not sandboxed or managed by Dots transactions. On Linux/WSL x86-64 and ARM64, selecting Deja permits Zinit to download a missing executable from upstream GitHub releases into its own plugin directory. This uses Zinit's existing third-party installation lifecycle, outside Dots file journals; the executable run check is not publisher authentication or sandboxing. Existing PATH executables take precedence, cached releases are reused, and updates are explicit. No upstream installer, system package installation or startup-file edits are invoked. Explicit `autosuggestions` or `none` selections skip this bootstrap. When Deja is selected and its binary is available, startup permits its per-user background daemon and plaintext history database under `~/.local/share/deja`; history import is never automatic. Its history exclusions are not general secret redaction. Engine selection is fixed for the shell lifetime to avoid conflicting widget wrappers. Switching back leaves Deja data and its daemon intact; removal and process termination require separate, scoped action.

## Guarantees

Managed file and theme workflows enforce these invariants:

- Read-only commands do not change managed targets or external systems.
- A complete plan exists before apply starts.
- Existing targets are classified before replacement.
- Replaced user data is backed up durably when it is reversible.
- Every mutation has a journaled transaction identity.
- Failure triggers reverse-order rollback of completed reversible operations.
- Undo detects drift before restoring prior state.
- Unsupported or partially reversible work is identified before approval.

No command should imply stronger rollback guarantees than its operations can provide.

## Read-Only Boundary

Read-only status, dry-run previews, discovery, validation and diagnostic operations are read-only unless their help explicitly describes a separate cache-refresh action.

Read-only means no:

- Target creation, replacement, permission change, or timestamp adjustment.
- Package-manager refresh or installation.
- Git fetch, pull, checkout, submodule initialization, stash, or clean.
- Persistent state migration.
- Shell profile edit.
- Registry edit.
- Credential prompt.
- Hook execution with undeclared side effects.

A disposable in-memory representation or rebuildable cache read is acceptable. Cache writes must be designed and described separately so `plan` remains suitable for auditing.

Generated theme-file inspection captures the active generation and observes known application destinations without recovery, publication, application activation or persistent state writes. Verification never launches applications or hooks; terminal text previews may run the optional bounded bat renderer with paging/configuration disabled and the existing captured cache. Supplementary-link discovery reads bounded transaction metadata, never retained backup bodies. Explicit content views use regular-file, symlink, UTF-8, size and possible-credential checks before emitting any bytes; raw output does not bypass these checks. See [theme inspection](themes.md#generated-theme-files).

## Hooks and External Side Effects

Arbitrary hooks weaken dry-run and rollback guarantees.

- Prefer built-in declarative operations.
- Declare hook stage, command, platform, mutation class, inputs, and rollback support.
- Do not execute a mutating hook during planning.
- Mark non-reversible hooks clearly before approval.
- Require explicit opt-in for untrusted or arbitrary repository hooks.
- Capture exit status and bounded, redacted logs.
- Do not claim that transaction rollback reversed a hook without a verified inverse protocol.

The [local theme plugin manager](theme-plugins.md) uses explicit
per-file enablement, post-commit execution, separate Bash children, nonblocking
locks and recursion refusal. No hooks are discovered in downloaded themes.
Custom hooks run with user privileges, are not sandboxed and have no automatic
inverse; their effects are never described as rolled back. Exit status and bounded
diagnostics are reported without persistent hook-output or environment logs.

The bundled GTK 3/Qt6ct adapters use the existing file Store with complete preflight,
retained backups, target guards, ownership receipts, rollback and drift-aware
undo/recovery. Copies stay fixed after disabling. Disable neither deletes output
nor restores old settings. Automatic failures leave the theme published and report
a retry path; malformed/ambiguous plugin configuration prevents execution.

## Secrets

- Checkout setup does not initialize private sources.
- Repository URLs never embed credentials.
- Plans, specs, logs, diagnostics, errors, command history suggestions, and JSON redact secret values.
- A secret reference may expose provider and identifier only when that metadata is not itself sensitive.
- Secret files require restrictive permission planning appropriate to the platform.
- Adoption refuses likely credential material by default.
- Debug bundles use an allowlist rather than attempting to redact arbitrary full environment dumps afterward.

## Repository Operations

- Never force-reset, clean, or discard a dirty repository automatically.
- Pull/update reports dirty state and divergence before changing branches or revisions.
- Record the repository revision used by every apply.
- Do not automatically initialize all submodules.
- Optional source updates are independent from main repository updates.

## Protected Boundaries

The planner needs explicit allowed destination roots. A destination outside those roots is blocked unless a separately designed privileged/system mode authorizes it.

Path validation occurs after variable expansion and normalization. Reject traversal, empty target, filesystem root, unresolved variable, unexpected UNC/device path, and other platform-specific escapes before mutation.

No recursive destructive action may use an unresolved environment variable, broad home directory, repository root, or filesystem root as its target.

## Authorized Development Worktree Cleanup

Local repository maintenance is separate from managed dotfile transactions. The [worktree lifecycle](../agents/guides/worktrees.md) permits automatic cleanup only of explicitly enrolled, merged, unused, clean linked development worktrees during deliberately selected worktree maintenance. Ordinary repository edits do not trigger cleanup. Read-only planning cannot remove worktrees. Original/session/helper roots, live references, local content, branch/recovery refs and review evidence are protected; uncertain checks skip and Git removal never uses force. This does not authorize a general-purpose recursive deletion API or relaxed managed-file safety.

Lifecycle cleanup supplements Git status with metadata-only entry classification and refuses special or uncertain filesystem objects. Its fresh-main fetch uses an empty `--refmap=` and an explicit destination, preventing configured fetch mappings from updating local branch/recovery refs. The trusted-filesystem and concurrent-change limitations in the worktree guide still apply.

## Theme Selection Publication

**Implemented bounded state operation**, separate from the proposed managed-file
installer. `dots theme set` authorizes publication of one shared palette generation;
its expanded connector boundary is defined below and in decision 0008. It validates the theme and
Neovim adapter before state creation, classifies every state ancestor and pointer
without following symlinks, and refuses unexpected objects or dot components.
An exclusive `flock` serializes switches. Existing lock files are not truncated.
Pywal16 imports at most 64 KiB of generated colors.sh as literal color data, never
as executable input. Missing, malformed, duplicate or incomplete colors refuse
publication. The source fingerprint includes the export and rechecks consistency;
wallpaper paths and unrelated export lines never enter the published JSON. Selecting
any family does not execute a palette generator or install its Neovim plugin.

New generations are private transaction directories with the previous token and
all generated artifacts. The helper rechecks the source fingerprint, flushes
files/directories using required `sync -f`, records `prepared`, and atomically
renames the new active token before recording `committed`. Until activation,
readers continue using the previous complete generation. Runtime errors and
INT/TERM restore the previous token (or remove a first selection) and record
`rolled-back`. SIGKILL releases the kernel lock; the next switch recovers prepared
journals before proceeding. A changed token that matches neither the transaction
nor its previous selection blocks recovery rather than overwriting drift.

Completed and incomplete generations are retained. A directory interrupted before
its prepared journal cannot have been activated and is ignored by recovery.
Rollback failure reports the retained journal path; no backup is discarded.
An unknown status or invalid pointer requires inspection. After correcting the
reported filesystem/permission issue, rerun `set` to retry recovery. This is not
a general undo API, app installation engine, pruning facility or arbitrary-hook
mechanism. Coherent published data may be observed before a crashed prepared
transaction is rolled back on the next switch.

State and generated shell initialization are trusted user-owned data, like existing
shell caches. This implementation does not defend against concurrent hostile
replacement of trusted directories/files. Durability depends on the filesystem's
`sync -f` and rename semantics; native Termux fixtures cover process failure, not
physical power loss. Read-only queries/help/completion do not create state; `init`
may populate a separately documented disposable cache. Tests use owned roots only.

## File Catalog and Configuration Migration

File reads expose metadata and observed links, never source contents. Explicit
private-source exclusions apply to discovery and inspection. `files track` writes
only the owning repository catalog with locking, fsync and atomic replacement;
identical records are a no-op and existing IDs need `--update`. It does not install
anything. Catalog updates are source edits recovered through version control.

The scoped config-path migration helper defaults to preview. Apply preflights every
link and confirms old/new paths resolve to the same existing source. An exclusive
staging link and durable per-operation JSON journal record original link text;
rollback runs in reverse and refuses drift. The journal is required and must live
outside repository source. Compatibility aliases remain. This helper does not move
directory trees, replace files or initialize submodules.

## Theme Application and Source Expansion

Decision 0008 expands the earlier theme-state publisher to the stable active link
and fixed application connectors documented in [themes](themes.md). Complete app
outputs and bat caches are generated before pointer publication. Preflight refuses
unexpected state objects and real connector directories. Existing connector files
or links are backed up in the generation journal, flushed and rechecked before
replacement. Failure restores connectors in reverse order and both selection
pointers. Known staged links from prepared transactions are recovered on the next
switch; unknown staging objects and post-write drift refuse destructive recovery.
The Pi connector targets only `themes/dots.json` in an existing agent themes directory;
settings and other themes are untouched. Changed publication renews this link even
when its text is unchanged, using the same backup and restore journal to notify Pi's
directory watcher. Unchanged refresh remains a no-op. No Pi directory is created.
The Codex connector targets only `themes/dots.tmTheme` in an existing Codex
themes directory, using the same backup/restore journal and drift checks.
Publication never creates Codex directories, edits settings/authentication, or
restarts sessions. Unchanged connector links are retained across publications.
Vivid and FSH connectors target only `vivid/themes/dots.yml` and `fsh/dots.ini`
under the configured XDG root when their parents exist. They use the same journal,
backup, conflict refusal and drift checks; publication does not create app directories.
The eza connector targets only `theme.yml` in an existing resolved eza directory, using the same backup, rollback and drift checks. Both publishers validate the absolute destination before connecting; native Windows uses the native link adapter without silent copying. No eza process or directory is created by refresh.
Leaf publishes two links in an existing config root and may journal creation of only its missing `themes` child. Shared-parent creation is recorded once; recovery checks directory identity before removing it. Both connectors retain the usual backup and drift guards. Publication does not replace the Leaf binary or edit its config selector; those require separately authorized changes.
No complete generation or backup is automatically pruned. Reload failures preserve
the published theme and report a retry path; external app state is not rolled back.

FZF environment templates are parsed as restricted literal assignments before
publication. Shell template code is never executed. Invalid statements or color
values refuse the new generation, leaving the active selection intact. Only
validated FZF color tokens enter generated shell initialization; this adds no
hook or general environment-variable injection interface. The Gum shell template
is rendered without execution during publication, refresh or CLI data output.
The owner-authorized interactive Bash/Zsh startup adapters automatically source
the readable published `gum_env.sh`; both shells also reload it on published-generation
changes. Missing files are optional and noninteractive startup does not load it.
Automatic or explicit sourcing executes trusted user-owned shell configuration, including
any personal or bundled overrides; these are not restricted to literal assignments.

The interactive theme switcher does not publish during selection, palette preview,
Back, Cancel or selector failure. It validates the selected ID against its offered
catalog and requires an explicit Apply action before calling the existing theme
publisher, which revalidates the theme and operation set. UI output is treated as
data, never evaluated. Missing tools select a fallback before interaction begins;
UI failure does not retry through another backend. Nonterminal input/output is
refused instead of obtaining confirmation through redirected data streams.

Git theme lifecycle commands use managed-checkout markers, an exclusive user-root
lock, staged clones, validation and atomic journal status updates. Update refuses
dirty or non-fast-forward histories; remove refuses the active theme. Prior trees
remain in `.archives`; interrupted replacements recover from `.transactions` on the
next operation. Imported symlinks and executable theme/config inputs are not used.
These are trusted source directories, not protection against concurrent hostile
replacement. HTTPS/SSH Git can require the user's normal network credentials;
there is no automatic recursive submodule initialization or hook execution.

Wallpaper actions record attempted/successful paths, preserve the successful record
on adapter failure, and use a timeout. An external Android/desktop API may mutate
before failing; there is no promise to recover an unknown prior wallpaper. A palette
switch does not imply wallpaper permission. Only explicit `bg` actions or
`set --background` invoke an adapter. WSL wallpaper is unsupported. Native PowerShell has a separate Windows desktop adapter; see [native PowerShell](powershell.md).

## Managed File Transactions

`files stash`/`files edit` submit complete guarded catalog/link/receipt batches to
the same Store. Stash retains sources and removes only matching links; disabled
resources stop claiming targets and cannot be silently reinstalled. Editing is
metadata-only unless live apply is explicitly requested. Live apply refuses
unrelated links, cross-owner sources, overlaps, unsafe parents, conflicting claims
and receipt drift; occupied regular destinations require backup approval.
Mandatory installation baselines survive `--no-backup`, relocation and temporary
absence. Undo/recovery restore mappings, links and receipts together. Text updates
to existing regular files retain their permission bits.

The shared file engine under decision 0010 implements POSIX add, link and stop-managing remove, plus native-adapter restore, undo, interrupted recovery and bounded checkout installation. Before writes it validates the
complete operation set, source/target overlap, ownership and path boundaries,
then locks the state and affected catalogs. It stages and verifies object copies
before live replacement and records durable per-object phases before renames.
Symlinked parents and special files are refused. Existing unrelated links,
including generated theme connectors, are never overwritten by these operations.

Temporary sibling replacement and reverse rollback preserve the original object.
Recovery compares current objects with recorded before/after identities and
refuses drift. Interrupted rollback is repeatable; unresolved transactions block
new writes. Sources, targets and catalog records participate in the same journal.
Do not claim protection against hostile concurrent filesystem replacement or
applications writing continuously during adoption: close editors/apps before
applying a reviewed batch. Preflight and boundary checks detect observed drift.

The tracked-file browser is a presentation client of the same transaction engine.
Catalog browsing, details, backup toggles and previews do not create state, locks
or journals. Only an explicit Apply choice submits the exact in-memory plan and
guards previously displayed. In addition to operation guards, the browser binds
source composition and non-excluded catalogs (including absent catalogs) to the
preview, so ownership changes require a new review. Source/target guards also
cover no-op plans. It validates selector output against offered choices and never
evaluates labels or paths. An apply failure stops the browser; normal transaction
rollback/recovery remains authoritative. Session backup toggles never write user
preferences or bypass planner refusals. Details display metadata, not contents.

Retained snapshots are opt-in, independent of temporary rollback protection. An
occupied different target requires a verified retained backup before linking.
Backups and journals live in private transaction/state directories outside source
repositories. On success without retained backups, content payloads are discarded;
prior catalog/link metadata and hashes remain. Undo uses verified unchanged
repository content where possible and refuses unavailable original content.
Retained snapshot payloads are not automatically pruned. Backup restore changes
data objects; undo reverses catalog ownership too. No automatic force or pruning
route is implemented. Standalone bak remains outside this managed contract.

`files check` is a bounded, explicit catalog-pruning operation: only absent source
paths qualify, never dangling source symlinks or filesystem errors. Unavailable
repositories are skipped. Target objects and installation receipts are untouched.
Per-entry review and final batch approval precede writes unless `--yes` is given;
dry-run always remains read-only. Composition/catalog digests and source absence
guard the approved batch. The transaction engine distinguishes ENOENT from other
object-inspection errors when checking guards. One transaction journals all changed
catalogs; prior catalog metadata supports undo without retained payload snapshots.

Adoption uses registered roots, excludes known credentials and local/generated
state, and rejects recognizable credential material without printing content.
The shared discovery/adoption exclusions prune known cache/session/dependency
trees, cookies, backup files and generated application previews; see
[system discovery](files.md#user-configuration-discovery). Human grouping and
hidden-status summaries never alter the scan's adoption eligibility or JSON data.
These checks are conservative rather than exhaustive. No command automatically
stages, commits or publishes adopted files. Remove keeps the repository source
and a regular usable config; it is not destructive repository deletion.

## Recursive Git Operations

The [Git family](git.md) is a separate bounded Git workflow, not a managed-file
transaction. Status, info, submodule inspection/completion and previews are local
and read-only. Actual sync/publish use
per-repository common-directory locks, observed-state rechecks, explicit branch
choices and conservative refusal policies. Git hooks/signing and credential
helpers remain active during explicitly requested real operations. Only sync
--init authorizes missing-submodule initialization. Publication validates the
actual push URL and configured owner, uses explicit refspecs, retains staged
pointer intent and blocks dependent parents after child failure. `publish --all`
stages ordinary files from the repository root with literal gitlink exclusions;
tracked files beneath ignored directories remain eligible, without force-adding
ignored new files. A staging failure may leave partial index changes for review.
Completed work
is retained; no multi-repository rollback is promised. Tests never perform these
operations against live repositories or external services.

Scoped `git submodules publish` applies the same Git checks to a selected forest.
It requires PATH or explicit `--all-submodules`, previews once and confirms once.
Excluded parent indexes, HEADs and remotes are never modified by the engine;
changed child pointers are reported for later recording. Registration/selection
checks repeat before a selected repository is published and after fetching.
Missing or unsafe children remain blocked, and safe siblings may continue.
This remains an incremental Git workflow, not a rollback transaction. Inspection
and completion never initialize children, fetch, acquire mutation locks or reveal
URL credentials/query strings/fragments. Hooks remain trusted user code and can
have their own external effects.

## Anodize authoring and apply

Create/import/edit and export-to-file use the existing file transaction Store with retained snapshots. Existing IDs/export destinations, generated-file drift and unsafe theme objects are refused. Complete staging and digest guards protect saves; existing file history, undo and recovery routes apply. Saves do not activate themes. [Anodize](anodize.md) documents confirmation, copied versus referenced wallpaper, and bounded input formats. Apply uses the existing theme publisher after template/target preflight. Explicit wallpaper changes are journaled post-publication adapter actions; a wallpaper failure leaves the app theme published and returns an error. Read-only previews only use disposable temporary rendering directories.

## Generated theme commands

Theme command wrappers and completion registrations are generated only from trusted
Dots templates and validated names. Imported theme code is never executed. Owned
immutable command generations carry checksums; drift blocks replacement and
rollback. Publication records previous/new command pointers in the owning theme
or import journal before switching. Failed parent operations restore both theme
and command state. Command-only refresh has its own durable journal. Incomplete
parent transactions must be recovered before an unrelated command publication.
Unmanaged state paths and symlinked ancestors are refused. Existing PATH commands
keep precedence, and reserved names remain accessible through full-ID routes.

## Dots shell environment

Dots config.env is parsed as literal data, never sourced. Invalid settings preserve previously resolved values. Initialization does not create settings files or publish themes. Portable shell.tsv snapshots are part of the existing theme transaction and are read without evaluation. The legacy repository cleanup was explicitly approved and retained a recovery copy of the removed source files; no home-directory legacy selection files were removed.

## File-style edits and refresh notifications

`theme colors set/reset` uses the existing file Store with retained backups,
complete-file guards and atomic replacement. Dry-run creates no state. Publication
validates all style references before committing generated JSON/Lua/LS_COLORS.
Saved configuration and theme publication are separate transactions: a failed
`--apply` keeps the saved rules and reports that publication needs retrying.
An optional two-second DDS broadcast follows publication; it carries only the
state-root identity, never an executable or a path to load. Notification failure
does not undo a published theme. Plugin snapshot errors retain previous colors.

## Bounded checkout installation

File copies are flushed through writable handles before they close, retaining
source permissions and Windows read-only attributes on the copy without changing
the source. Flush errors remain fatal. Native theme preparation flushes owned
generated files through the platform adapter. Windows directory flushing and
power-loss guarantees remain outside the supported contract. Installation receipt
fingerprints and published text share permission-preserving preparation; actual
post-install permission drift still blocks restoration.

[Setup](installation.md) preflights catalog composition, source contents and target identities before replacement. It retains verified original backups and journals its installation record with the same operation batch. Correct pre-existing links are not claimed. Unrelated links and conflicts block the batch; ordinary occupied objects require the displayed backup/replacement approval. Update reconciliation preserves the first installation baseline.

Uninstall restores only unchanged owned targets; drift remains visible and retained. Empty created-directory cleanup uses separate guarded file transactions. Catalogs, checkouts, generated payloads and recovery records are retained. The shared platform adapter refuses symlinked ancestors, unsupported Windows reparse points and unavailable link capability. Windows flushes payload/journal files, but lacks POSIX directory-fsync/power-loss guarantees; native evidence is required before claiming platform validation.

Theme preparation creates inactive immutable payloads marked `staged`; it publishes nothing. Setup's file transaction owns pointer/connector publication and recovery. These payloads are not mistaken for interrupted normal theme journals. Git updates remain separate non-atomic stages, retain completed updates on later setup failure, and never discard dirty work or recursively initialize private sources. Dry-run performs no writes or network access.

## Starship palette updates

The explicitly enabled Starship theme plugin updates only Dots-selected palettes in the active config and saved Blastoff `dots` theme. It validates TOML, preserves unrelated values/bytes and extra colors, acquires Blastoff operation locks, and records both changed targets in a retained-backup file transaction. Existing configured symlinks are resolved with identity guards and preserved, rather than replaced. Missing files stay absent. Concurrent edits, malformed representations and special files are refused. Plugin failures leave the published theme selected; transaction recovery and drift-aware undo follow the normal file-operation contract. Blastoff provenance is not rewritten to hide external palette edits.

## Git platform companion

The fixed consolidated `dots:git` mapping may select only `config/git/gitplatform`
inside its source directory, pointing at one of four regular sibling platform
files. This does not relax arbitrary source/target overlap or symlink-parent
checks. Known platform-link replacements are previewed, guarded and journaled
with retained installation baselines; unrelated objects and owned-target drift
are refused. Correct pre-existing selectors remain unowned, stash preserves
source content, and uninstall preserves drift. Direct link operations involving
this companion retain receipt recovery data even when optional snapshots are off.

The bounded Termux consolidation migration retires only recognized Androidots
Git catalog/import mappings and verified legacy links, including matching dangling links. It
retains historical receipt baselines, verifies effective configuration without
printing values or executing credential helpers, and undoes failed verification.
It never removes moved platform source files.

## File-picker previews

The [file selectors](files.md#interactive-file-pickers) obtain operands, never
approval. A complete guarded plan and the existing confirmation are still required.
Picker snapshots contain metadata only in private temporary directories and are
removed on normal completion/cancellation. They create no managed state or journals.
Preview helpers receive validated opaque tokens, never shell-interpolated paths.
Content preview is an explicit Alt-C action with bounded reads and escaped control
characters. It refuses excluded/credential-like content, special objects and
unrelated links; a target link may resolve only to its recorded regular source.
These checks are conservative and do not promise exhaustive secret detection.
No editor, arbitrary preview plugin, shell startup or previewed configuration is
executed. Selection does not change backup, rollback or drift protection.

## Native PowerShell publication

Native Windows file operations and theme publication use the shared `Store` guards, preparation, journals, reverse-order rollback, retained backups and drift-aware undo. Publication and recovery use the same theme locks on Windows and POSIX. Native setup renders inactive payloads before its transaction publishes pointers; it never invokes desktop effects or hooks. Unknown reparse points, WSL/device paths, reserved Windows path components and duplicate operation targets are refused. Link privilege failures never enable elevation, Developer Mode or an automatic copy fallback.

Native command generations carry a manifest and are checked before replacement. Unrelated active pointers and modified commands require review. Legacy unfinished Bash theme publication journals are refused on the native path; Windows and WSL installations must remain separate. Explicit wallpaper effects have a recorded attempt and result, but changing an external application's desktop state is not filesystem rollback. See [native PowerShell](powershell.md) for current limits.

Anodize promotion stages a complete destination and removes the source only as a
second operation in the same retained transaction. Copy mode keeps the source and
requires a distinct unused ID. Both roots are collision-checked; source/destination
and authoring-input digests bind review to apply. Receipt drift and unsafe trees
are refused. Interactive selection and mode generation use disposable storage,
never approve an operation, and never publish themes or invoke hooks. Source image
copying preserves the original image.

## wttr cache and completion

Weather refresh writes only a private disposable cache containing the requested location (including coordinates), bounded upstream data and retry/reservation metadata. Background views may spawn a bounded HTTP refresh but use a configured location or read cached geo city/address data only; strict `--cached` never spawns or writes. Foreground automatic refresh may invoke the existing Termux location helper and its reverse-geocoding service. Stock requests use bounded native curl, disable curlrc/globbing, preserve successful response bytes and never populate the weather cache; service pages and moon routes skip location. It does not change permissions, install dependencies or modify Android provider gates. Completion installation is explicit, preflights all targets and uses the shared Store transaction/backup/drift/undo contracts. It never changes shell profiles automatically. See [weather recovery](wttr.md#cache-and-recovery).

The Television connector targets only `themes/dots.toml` in an existing resolved app directory. Its missing `themes` child may be created with a durable journal. Bash records creation intent and directory identity, refuses ambiguous recovery or replacement-directory drift, and removes only an empty owned directory; interruption between creation and recording identity requires manual recovery. Native publication uses Store parent creation and rollback. Existing theme files/links retain the usual backup and drift safeguards. No Television process is started by publication.

## Startup preparation and checkout acquisition

Native startup bundles are rebuildable private caches, not managed app files.
Preparation validates shell syntax and atomically publishes complete generations;
cache metadata contains no caller environment values. Hook diagnostics store only
names, provenance and sensitivity, redacting private values at display time.

An explicitly installed bootstrap snippet may acquire a missing checkout through
a bounded noninteractive clone, sibling staging, process locking, durable status
journaling and atomic no-replace publication. It never updates an existing
checkout or installs packages/application configurations. Failed staging is
retained for inspection. See [bootstrap recovery](profiles.md#missing-checkout-bootstrap).

## Explicit startup diagnostics

`dots debug startup` is read-only unless `--live` or `--isolated` is supplied.
`--live` explicitly authorizes the child shell's normal startup hooks and their
usual side effects; it does not promise rollback or sandboxing. `--isolated` and
curated self-tests use disposable public sources and owned runtime roots. Trace reports contain source/timing/status metadata and sanitized changes. They never contain expanded commands, function bodies or alias expansions. Explicit `--show-values NAME` may include a bounded non-sensitive scalar representation; sensitive names/private-hook values remain redacted. Raw Bash/Zsh state comparisons use an anonymous pipe and bounded memory, never a persisted dump; PowerShell sanitizes changes before writing its event file. Arbitrary child output is discarded. Diagnostics
do not source cached guards, rebuild caches during inspection, or execute routes
to explain resolution. See [debugging](debug.md).

Platform file-ID normalization is an in-memory read step. It must not rewrite receipts or historical journals during inspection or unchanged installation. When an authorized transaction updates a receipt, original backups and drift guards survive the canonical ID change; undo/recovery continue to use the original journal data. See [identity contracts](specification.md#canonical-platform-file-identities).

Opt-in PATH recording installs native hooks only when generated start code is explicitly evaluated or `DOTS_DEBUG_RECORD=path` is supplied before startup. It writes only PATH/location metadata to private bounded temporary storage, preserves conflicting hooks by refusing activation, keeps subshell changes separate, and removes its own recording on normal exit. It does not promise to reconstruct history before activation. A stopped recorder retains evidence until shell exit; abrupt termination can leave disposable temporary files. Ordinary PATH/status inspection does not install hooks or run startup.

## Wiki generation and publication

Wiki inspection/source-only checks never acquire repositories or write exports. Explicit builds preflight all source/target guards, refuse generated-file drift, preserve unknown files and use retained common transactions for replacement, removal, rollback and undo. Initial acquisition uses a staging directory, lock and durable journal, with atomic no-replace publication.

Wiki Git operations preserve ordinary ownership/upstream/refspec/lock checks. The associated wiki follows successful source publication and must match the selected source content; wiki-only publication verifies published source evidence. No automatic generation, staging, commit or push is installed. Completed Git work is retained after partial failure.

## Keybinding inspection

Key browsing never executes binding actions, shell/Lua configuration or returned code. Caller adapters export mapping metadata on demand, omitting shell macro/command bodies and Lua function bodies. Temporary preview/Neovim snapshots are inert data; the picker clears inherited FZF action/preview options and uses numeric selection identities. Application queries never start a tmux server or initialize missing plugins. Configured binding identifiers and source paths remain visible; no environment-value dump is performed.
