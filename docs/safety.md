# Safety and Recovery Model

**Status: Implemented bounded workflows below; general installation transactions remain draft**

Safety is a core product feature of `dots`, not a wrapper around destructive file operations. This document is authoritative for planning, mutation, backup, rollback, undo, package, hook, repository, and secret behavior.

## Repository Editing Boundary

Ordinary task-relevant edits to repository source files, including live dotfiles and scripts, are allowed in the existing checkout under [AGENTS.md](../AGENTS.md). They do not require the proposed Go transaction engine. Inspect Git status and preserve unrelated, uncommitted, and untracked work. Git history provides recovery for committed repository edits; reverting a commit does not recover uncommitted work or reverse external machine effects.

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

The existing Zsh configuration uses user-local completion, Vivid, FSH, and Catppuccin caches independently of the proposed managed-file transaction engine. These are rebuildable generated data. FSH's native INI loader builds in a temporary Dots cache directory. The adapter atomically persists validated data as a regular `current_theme.zsh` in the existing `FAST_WORK_DIR`, retaining the last good startup theme on preparation failure. Before replacing a non-Dots selection it creates a unique private backup of the prior script and compiled companion, preserving symlink identity. Stale `.zwc` code is invalidated; directory conflicts are refused and backups are not automatically pruned. These are cache/selection writes outside the managed theme-publication journal. User overlays remain trusted executable shell code. Completion generation validates successful output before atomic publication; failed output is not evaluated. Ordinary startup retains its existing optional plugin bootstrap and private/local sourcing behavior. Tests use copied public dependencies and synthetic private modules under owned roots; they must never run the live startup chain against the developer's home. See the [Zsh guide](../shells/zsh/README.md).

The default [Deja integration](../shells/zsh/README.md#deja-suggestions) is third-party executable shell code, not sandboxed or managed by Dots transactions. On Linux/WSL x86-64 and ARM64, selecting Deja permits Zinit to download a missing executable from upstream GitHub releases into its own plugin directory. This uses Zinit's existing third-party installation lifecycle, outside Dots file journals; the executable run check is not publisher authentication or sandboxing. Existing PATH executables take precedence, cached releases are reused, and updates are explicit. No upstream installer, system package installation or startup-file edits are invoked. Explicit `autosuggestions` or `none` selections skip this bootstrap. When Deja is selected and its binary is available, startup permits its per-user background daemon and plaintext history database under `~/.local/share/deja`; history import is never automatic. Its history exclusions are not general secret redaction. Engine selection is fixed for the shell lifetime to avoid conflicting widget wrappers. Switching back leaves Deja data and its daemon intact; removal and process termination require separate, scoped action.

## Permanent Read-Only Core

The root development executable implements help/version/doctor/commands through a validated built-in registry, plus the bounded external protocol below. It preserves the experiment's bounded optional-logo handle checks, explicit missing-platform-path warnings, unprobed diagnostics and argument redaction. Built-in startup loads no manifests, configuration contents, transaction state or external code. Only explicitly requested external resolution reads sidecars, and only direct external dispatch executes a selected extension. There is no persistent cache or installation surface. Test-only filesystem mutation primitives remain in the independent experiment. The [core verifier](testing.md#permanent-core-verification) owns all build/cache/fixture writes and proves unchanged runtime roots; it never replaces the active `bin/dots` or edits shell configuration.

## Development Extension Trust

The [accepted protocol](decisions/0003-trusted-external-command-protocol.md) permits execution only from explicit trusted `--command-dir` roots, with mandatory bounded static metadata and protected core namespaces. Help/discovery never execute extensions. No real management command ships; fixture execution belongs only to disposable test roots. A `read-only` sidecar is an author assertion, not an enforced sandbox: an invoked extension has the user's environment, working directory and streams and can exercise user privileges. Do not infer safety or publisher authentication from JSON, filename or executable validation.

Root identity and opened-handle metadata checks reject accidental malformed objects. They do not prevent an adversary replacing trusted files or parent directories between checks and execution. No execute-by-handle, ownership/ACL enforcement, credential isolation or process-tree cleanup guarantee is made. Future managed writes still require core transaction APIs; this slice does not implement or exempt them.

## Implemented Experiment Boundary

The [Phase 1 experiment](../plans/phase-1-portability.md) exposes no managed filesystem mutation command. Help may read the optional public logo. It validates the opened handle before reading; Unix opens are nonblocking to avoid waiting for a writer if a regular logo is replaced with a FIFO. This does not impose a general filesystem I/O deadline. Diagnostics reads allowlisted path/environment inputs and limited runtime metadata, without opening dotfile contents or creating capability probes. Version output does not inspect the repository. Unknown arguments are not echoed into diagnostics.

Symlink/copy operations exist only in disposable tests, using directory-rooted filesystem APIs and exclusive creation to exercise refusal on existing targets. Build caches, fixture setup, and retained development artifacts belong to harness-owned temporary roots. Native Windows tests retain required OS environment paths but isolate user/config/temp roots. Copy and traversal cases do not depend on link privileges. Recognized Windows link permission/capability failures are reported as unavailable, never as successful links or silent copy fallback. Tests do not change Developer Mode, registry, elevation, or security policy; Windows ACL-denied-logo cases remain untested. CI may provision development tools before verification; verification-time toolchain/module downloads are disabled, including `GOVCS=*:off`. These tests do not implement backup, apply, rollback, undo, or a journal and provide no exception to the managed-mutation transaction rules below. Read-only CLI process checks compare controlled fixture roots before and after execution; they are not a system-wide syscall audit.

The distribution experiment creates/extracts only fixed-layout bundles under fresh harness-owned roots. It verifies the external SHA-256 manifest and the complete allowed regular-file member set before destination creation, then uses exclusive writes. It rejects existing destinations and unsafe paths/types; no archive-selected links, permissions, or ownership are applied. These bounded fixture writes are not managed installation or a transaction API. Checksums are integrity agreements with the supplied manifest, not publisher authentication. See [testing.md](testing.md#experimental-distribution-check) for exact limits and regression guarantees.

The [accepted packaging and release-trust direction](decisions/0002-phase-1-go-adoption.md#packaging-and-release-trust) separates checksum integrity from publisher authentication and lists gates before public release or remote bootstrap. Its implementation remains pending; acceptance does not authorize installation or weaken the transaction rules below.

## Guarantees

The intended guarantees are:

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

`status`, `spec`, `plan`, discovery, validation, and diagnostic operations are read-only unless their help explicitly describes a separate cache-refresh action.

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

## Target Classification

Before planning a mutation, classify the destination using link-aware filesystem inspection.

| Observed target | Typical plan result |
| --- | --- |
| Missing | Create parent as needed, then install resource |
| Correct managed link | No-op |
| Broken managed link | Repair through a transaction |
| Link to another source | Conflict or backup-and-replace under explicit policy |
| Matching managed copy | No-op |
| Modified managed copy | Drift; require normal replacement/backup policy |
| Unmanaged regular file | Back up, then replace only after approval |
| Unmanaged directory | Conflict unless the resource safely manages compatible children |
| Platform-specific link object | Compare through the platform adapter |
| Inaccessible or ambiguous | Block before mutation |

Classification must not follow a link in a way that causes the engine to back up or delete the link's external target accidentally.

## Plan Contract

A plan contains ordered operations and enough information for review and execution.

Each operation should include:

- Stable operation and resource identifiers.
- Source and canonical destination.
- Observed target classification.
- Requested and effective strategy.
- Action, no-op reason, warning, conflict, or blocked reason.
- Backup action and expected location.
- Required capabilities and privileges.
- Reversibility class.
- Sensitive-field redaction markers.

Apply consumes the plan representation. It must validate that critical observations have not changed between planning and mutation.

Implemented file, Anodize and Git approval prompts may use optional Gum after the
existing preview. The interaction layer neither replans nor applies operations;
only an exact affirmative choice reaches the existing operation path. Default
Cancel, selector failure and interruption grant no approval. Tool failure never
falls through to a second prompt. Existing JSON and explicit approval flags retain
their semantics; see [presentation](presentation.md#optional-gum-interactions).

## Transaction Lifecycle

1. Validate specification and complete plan.
2. Obtain explicit approval or a valid non-interactive approval flag.
3. Acquire an exclusive state lock.
4. Revalidate mutable preconditions.
5. Allocate a transaction ID and backup directory.
6. Write and durably initialize the journal.
7. Apply each operation, recording its start and completion boundary.
8. On failure, stop forward progress and roll back completed reversible operations in reverse order.
9. Record success, successful rollback, partial rollback, or recovery-required state.
10. Release the lock after durable final status.

An interrupted process must be detectable on the next invocation. Recovery must use journal evidence rather than guessing how far apply progressed.

## Journal

The eventual journal schema should record:

- Transaction ID, schema version, timestamps, and status.
- CLI build/version and repository revision.
- Platform, profile, host, and resolved-spec digest.
- Approved plan or a stable reference to it.
- Operation order and per-operation status.
- Previous object metadata, backup path, and integrity digest where applicable.
- Installed object identity or digest for drift checks.
- Errors, rollback attempts, and recovery instructions.
- Explicit force or policy overrides used.

Journal writes must use atomic replacement and appropriate durability for the platform. Secrets are represented by redacted metadata or opaque references.

## Backups

- Transaction backups live in the machine state root, not solely in the repository.
- Preserve the object itself rather than accidentally dereferencing a link.
- Preserve relevant permissions and timestamps when the platform supports them.
- Verify a backup before deleting or replacing the source object it protects.
- Use collision-resistant transaction-owned paths rather than ad hoc `.bak` siblings.
- Retention and pruning must never remove a backup needed by an incomplete or recovery-required transaction.
- Explicit snapshots and automatic transaction backups need distinguishable metadata.

Pruning is a destructive operation with a plan, retention explanation, and narrowly scoped confirmation.

## Atomicity

Use temporary siblings and atomic rename/replace where supported. Filesystem-level atomicity may not span volumes, package managers, repositories, or hooks.

The engine should preflight cross-volume or unsupported replacement behavior and report reduced guarantees. Never describe a multi-system transaction as fully atomic when only its journal is coordinated.

## Rollback

Automatic rollback handles failure during apply.

- Reverse only operations confirmed complete by the journal.
- Execute inverse operations in reverse order.
- Do not continue normal apply after rollback begins.
- Record rollback failures without destroying their backups.
- Finish in a clearly queryable `rolled-back` or `recovery-required` status.
- Provide specific recovery instructions and paths without exposing secret content.

Rollback must itself be resumable or manually recoverable.

## Undo

Undo is a later deliberate reversal of a completed transaction.

- Compare each current target with the object installed by the transaction.
- If the target has changed, report drift and refuse replacement by default.
- Scope any force option to the named transaction/resource.
- Preserve the drifted target before forced restoration when possible.
- Record undo as its own transaction instead of deleting history.
- Do not infer that packages added by the original transaction are safe to remove.

## Link and Copy Policy

- Symbolic link is the repository default.
- Copy is selected explicitly by resource or machine policy.
- A directory link requires declared ownership of the whole destination directory.
- Unavailable link capability blocks the plan unless an explicit fallback is configured.
- Fallback choice appears in the plan and journal.
- Copies record an installed digest so status and undo can detect drift.
- Repository relocation should produce broken-source diagnostics and a repair plan, not automatic unjournaled rewrites.

## Packages

The package adapter records whether each requirement was already satisfied and whether `dots` installed it.

- Package database refresh, install, upgrade, and removal are distinct planned actions.
- Do not upgrade all packages as an implicit prerequisite for applying dotfiles.
- Do not automatically remove packages during ordinary filesystem rollback or undo.
- A future package removal command may propose packages added solely by `dots`, but must query current reverse dependencies and require explicit approval.
- Package-manager output and failure belong in the journal without leaking repository credentials or environment secrets.

## Hooks and External Side Effects

Arbitrary hooks weaken dry-run and rollback guarantees.

- Prefer built-in declarative operations.
- Declare hook stage, command, platform, mutation class, inputs, and rollback support.
- Do not execute a mutating hook during planning.
- Mark non-reversible hooks clearly before approval.
- Require explicit opt-in for untrusted or arbitrary repository hooks.
- Capture exit status and bounded, redacted logs.
- Do not claim that transaction rollback reversed a hook without a verified inverse protocol.

General hooks remain outside the initial Termux MVP. The specifically authorized
[local theme plugin manager](theme-plugins.md) is a bounded exception: explicit
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

- Public bootstrap does not initialize the secrets source.
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
- A moving remote bootstrap channel must allow a pinned alternative.

## Protected Boundaries

The planner needs explicit allowed destination roots. A destination outside those roots is blocked unless a separately designed privileged/system mode authorizes it.

Path validation occurs after variable expansion and normalization. Reject traversal, empty target, filesystem root, unresolved variable, unexpected UNC/device path, and other platform-specific escapes before mutation.

No recursive destructive action may use an unresolved environment variable, broad home directory, repository root, or filesystem root as its target.

## Static Command Catalog

The [versioned catalog](decisions/0004-versioned-command-discovery.md) reads only explicit command roots and metadata, validates the complete discovery result before stdout, and executes no extensions. It includes hidden/unavailable records; hidden is presentation metadata, not a confidentiality boundary. No resolved paths or environment values are added, but author-provided descriptions are reproduced. Availability and read-only declarations do not authenticate, sandbox or protect against concurrent replacement of trusted files.

## Authorized Development Worktree Cleanup

Local repository maintenance is separate from managed dotfile transactions. The [worktree lifecycle](../agents/guides/worktrees.md) permits automatic cleanup only of explicitly enrolled, merged, unused, clean linked development worktrees during deliberately selected worktree maintenance. Ordinary repository edits do not trigger cleanup. Read-only planning cannot remove worktrees. Original/session/helper roots, live references, local content, branch/recovery refs and review evidence are protected; uncertain checks skip and Git removal never uses force. This does not authorize a general-purpose recursive deletion API or relaxed managed-file safety.

Lifecycle cleanup supplements Git status with metadata-only entry classification and refuses special or uncertain filesystem objects. Its fresh-main fetch uses an empty `--refmap=` and an explicit destination, preventing configured fetch mappings from updating local branch/recovery refs. The trusted-filesystem and concurrent-change limitations in the worktree guide still apply.

## Static Completion Boundary

[Zsh generation](decisions/0005-static-zsh-completion.md) validates all metadata before stdout and never executes extensions. Generated scripts omit descriptions, safely quote explicit root strings, and use only embedded route data at completion time. Ordered literal context matching is a conservative presentation filter, not filesystem identity or a trust guarantee. Root paths occur only in explicitly generated script context, not the JSON catalog. No installation, startup edit, persistent cache or implicit discovery is performed.

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
transaction. Status and previews are local and read-only. Actual sync/publish use
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
