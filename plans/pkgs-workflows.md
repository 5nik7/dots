# Package workflows

Status: implemented and verified in isolated Termux fixtures (2026-10-31). Owner: `dots-pkgs-maintenance`. Native acceptance limits are recorded below.

## Agreed outcome

Both `pkgs` and `dots pkgs` share unattended user-wide upgrades, Go tool updates,
literal package policies, full styled subprocess/stdin output, editable JSON
exports and optional package-first checkout setup. Existing install/remove
approval and package-manager protections remain. Package effects have no Dots
filesystem rollback. Verification never changes host packages.

Bare upgrade selects one system database plus global npm, uv tools, pip-owned
non-venv distributions, user RubyGems and Go tools. Explicit managers/names retain
selected-scope behavior. Continue independent failures and return nonzero.
Go uses go-global-update when suitable and available, otherwise go install;
development builds remain untouched. No helper installation is automatic.

Native pkgs JSON owns upgrade manager selection, output mode and manager/package
skip/flag/before/replace/after policies. Dots Config provides guarded edits with
next-invocation activation. Recipes are argv arrays, with whole-argument package
placeholders; scripts are explicit. Direct-target skips require --ignore-skip to
override and do not promise dependency holds. Unknown native config is preserved.

Output keeps full manager messages except the explicitly suppressed APT script
advisory, recognizes events, preserves unknown text and offers raw forwarding. JSON, manifests, completion and ordinary redirected
streams remain undecorated. The stdin formatter cannot recover producer status.

Exports default to explicit roots, label inferred/all evidence, retain observed
versions separately from optional pins and use one versioned JSON file. Restore
installs missing packages, retains unpinned installed versions, enforces pins and
never removes unlisted packages. Non-restorable source entries remain disabled.
File exports and Config writes use Store guards, backups and recovery.

Optional --packages FILE / -Packages FILE setup previews both stages, restores
declared system packages, rediscovers language managers, then revalidates and
applies configuration. Missing prerequisites do not authorize invented installs.
Incomplete package restoration prevents configuration; packages survive later
configuration failure. Ordinary setup remains unchanged.

## Work packages

Selected goal: `3b0fe81b73a641ddbce5f8cd96068860` (`pkgs-update`). Existing output
parent: `b0a96f80edbf40f7b6953e68c033d412`; export parent:
`08a1bdbbf62c4d929a4b9065d73554e8`. Existing titles/aliases/notes are retained.

| Package | UUID | Depends on |
| --- | --- | --- |
| R: rules and Config | fd66b768350144999ab78a5e50318dba | none |
| G: Go integration | cd3f9659935444df82d1a94d6ed2391d | R |
| A: unattended orchestration | 95ae5e784c1a4cf6a13fb0802cec19a2 | R, G |
| O: stream formatting | 4e29d23c30f148daad0f0a72e1b2032a | A |
| E: manifests | 5585bc2094cf425e9088f34df1e9cc18 | R, G, A, O |
| S: setup integration | f4c2343f419743bda02810c5e92712f0 | E |
| V: integration and acceptance | 30c32df65a2742f7add5182070136c35 | all above |

Configuration assessment: **add** native `apps.pkgs` bridge and validated policy
controls; reuse existing semantic styles and formatting preferences. Menu
assessment: **update** package upgrade with review/confirmation, add export,
manifest inspection, restore and configuration; no menu for stdin filtering.

## Acceptance

Use [the presentation gate](../docs/presentation.md) at 40/80/120 columns with
plain/color/icon/NO_COLOR modes and exact data. Test literal/Unicode operands,
no-TTY upgrades, deduplicated scopes, ownership, recipes, Go fallback, streaming
fragments, cancellation, partial failures, manifest round-trips/pins, stale
guards, export rollback and unchanged restore. Test every setup adapter and
source-update forwarding with owned roots and fake managers.

Run plugin and bundled core/report checks, Config/menu checks, file-platform then
installation checks, generator/metadata checks, documentation links and whitespace.
Rebuild/check the available wiki preserving unrelated edits. Record native Termux
evidence separately from pending Linux/WSL and PowerShell 5.1/7 checks. Windows
supports formatting/manifest inspection; package operations still refuse without
launching WSL. Its Config file uses the native platform configuration root.

Save/progress/completion use scoped Todo CLI only, rereading before writes and
completing verified descendants before parents. No commits, pushes or live
package/config activation are included.

## Verification and limits

The implemented contract is documented in [package workflows](../docs/packages.md). All seven work packages and both existing child branches are complete; the selected goal and full saved UUID tree above retain their original relationships.

| Check | Result |
| --- | --- |
| Bundled pkgs core | 110 tests passed, including the new workflow suite |
| Package integration | 9 passed: Config CLI/popup, reviewed upgrade/export/restore, all POSIX/native-controller setup routes, source-update forwarding, repeat restore, package-before-configuration ordering, retained packages on configuration drift and Windows refusal |
| File platform | 5 passed |
| Installation | 27 of 28 passed after correcting missing renderer dependencies in two source-update fixtures; the existing WSL theme repeat-install failure remains |
| Installer adapters | 5 passed; 5 native-runtime checks skipped |
| Bundled application routing | 17 passed; 1 native-runtime check skipped |
| Application reports | 9 passed; 1 native-runtime check skipped; old fixed-ANSI expectations updated to current semantic defaults |
| Config values / profile configuration / Config popup | 12 / 10 / 15 passed |
| Launcher | All 21 cases passed across the broad run and corrected package-action contract rerun |
| Static and documentation checks | 238 command routes validated; generator, Bash syntax, skill validation, relative links, whitespace and rebuilt wiki checks passed |

The package tests include no-TTY approval boundaries, independent failures, Arch database deduplication/full-upgrade exclusions, pip ownership, Go helper/direct fallback and development-build refusal, literal recipes, raw/CRLF/partial output, real child interruption cleanup, 40/80/120-column presentation, pins, disabled source/duplicate entries, export undo/failure recovery and stale guards. All package execution uses fake managers and owned home/config/state/cache roots. No host packages were installed, upgraded or removed.

The broad installation failure is `test_fresh_checkout_wsl_setup_connectors_check_and_restore`: repeat setup republishes `theme:catppuccin-mocha`, `theme:selection` and `theme:active`. It predates this goal and remains outside package scope. Package restoration itself has a passing repeated-setup no-op check; this plan does not claim the full installation suite is green.

An eight-sample interleaved help benchmark during validation measured median 439.2 ms at HEAD and 471.7 ms with the expanded grammar. This noisy Termux sample adds about 33 ms; direct dispatch still introduces no catalog scans, package probes or new caches. Native Linux/WSL real-manager privilege/output acceptance and native Windows PowerShell 5.1/7 format/manifest/Config/setup-refusal acceptance remain pending. Portable fixtures and private terminal tests do not establish those native results.

## Follow-up: export, help and refresh

The user's follow-up explicitly requests refresh without `--yes`, suppression of
APT's unstable-CLI advisory, corrected help/operation formatting and a responsive
export. Completed goals remain complete; follow-up verification is appended to
their existing Todo records without replacing their IDs or acceptance criteria.

Python export previously queried APT ownership for every distribution before
filtering dependencies. On this Termux host export took 55.35 seconds, exhausted
the 45-second Python budget and disabled packages with unknown ownership.
Filter roots first, then query exact metadata paths in batches of up to 128.
Unknown/failed ownership remains disabled. Delayed per-manager progress goes to
terminal stderr, including with stdout redirected; JSON remains clean and query
deadlines remain bounded. The first read-only rerun completed in 18.44 seconds
across six managers without time-budget errors. These are local observations
under variable load, not a performance guarantee.
The final terminal run with stdout redirected completed in 16.16 seconds,
showed the active manager on stderr and produced valid JSON for all six managers
with no notices.

Refresh itself authorizes native supported noninteractive flags, like upgrade.
Install/removal/restore approvals and the Arch refresh refusal remain. The
formatter suppresses only the exact APT script advisory, including split chunks;
other warnings, exit statuses and explicit raw bytes are preserved. Help and
operation previews use shared semantic headings, labels and width-aware command
rows. Help aliases share grammar-derived content without manager probes;
ordinary redirected help retains argparse text.

Configuration assessment: **no configuration integration change needed**; reuse
native output/color and Dots semantic formatting/progress settings. Menu
assessment: **leave unchanged**; the existing refresh action explicitly invokes
metadata refresh, while upgrade/restore retain their separate review actions.
Both entry points share the core. Native Windows shares formatted help and the
stdin formatter; refresh/export retain status 3 and never invoke WSL.

Follow-up acceptance: batched exact ownership and conservative failures, root
filtering before ownership, delayed stderr progress and timeout cleanup,
prompt-free refresh through a fake Termux manager, retained non-boilerplate
warnings/raw bytes, manager-free help aliases and 40/80/120-column layouts.
Core validation: 116 tests passed; the final focused workflow rerun passed all
31 tests. Package integration passed 9 tests, shared reports passed 9 with one
native skip, and bundled entry points passed 17 with one native skip. Metadata
generation, all 238 external command routes, relative links and whitespace pass.
The wiki was rebuilt (transaction `62d2ccbb11b24f5e8adb6d92e91e8c57`) and checked
healthy. No host package transaction was used. Native Linux/WSL refresh and native
PowerShell help/formatter acceptance remain pending.

## Follow-up: profile manifests and publication

Status: implemented and verified in isolated Termux fixtures. Escape from a delegated filename prompt must
return to the same launcher frame/query without a traceback or package action.
All package filename prompts default to `packages.json` beside the active leaf
profile's `profile.json`, independent of cwd. A missing profile is an explicit
error; direct export can still use an explicit output path.

Agreed update policy: preserve pins, enabled flags, reasons, selection evidence,
groups and packages absent from the current inventory. Refresh matching observed
versions and append newly installed packages/groups. `pkgs export --update`
updates the profile manifest by default; `--output FILE` selects another file.
Ordinary bare export remains JSON on stdout. Update dry-run prints the proposed
JSON without writes. Updates use guarded Store writes, backups and existing
replacement approval. Partial inventories cannot replace a manifest.

`dots git publish --update-packages` is opt-in and applies only to the selected
root repository's current profile manifest. Both frontends use the shared Python
publisher for this option. It exports/merges during the read-only publication
preview, then writes and stages that snapshot immediately before the root commit.
The option explicitly includes this one file alongside the normal staged/all
selection; it does not stage unrelated files. Refuse ignored/unmerged/partially
staged manifests, paths outside the selected worktree, scoped-child/wiki-only
usage, and native Windows package inventory. Inventory failure stops before
publication; drift is checked again before writes. Existing ownership, explicit
refspec, hooks, signing, child-first ordering and incremental failure semantics
remain. Dry-run creates no manifest, index changes, locks, commits or network work.

Configuration assessment: **no configuration integration change needed**. The
profile resolver owns the location; refresh before publish is an explicit flag,
not a new implicit hook. Existing colors, layout and progress controls apply.
Menu assessment: **update** package defaults and cancellation; **add** an update
manifest action with preview/Run. Keep the publish automation flag on the CLI;
ordinary Git menu publication retains its existing scope. Owners are
`dots-pkgs-maintenance`, `dots-menu-authoring` and `dots-git-maintenance`.

Acceptance uses owned homes/state/profiles, fake managers and local bare remotes:
Escape and Ctrl-C return cleanly; profile defaults ignore cwd and handle leaf
profiles; merge preserves edits and disabled/missing entries; repeat updates are
no-ops; stale/partial exports refuse safely; publish preview/cancel are pure;
publication includes exactly the manifest plus the authorized selection; native
Windows refuses without WSL. Verify metadata/completion on both frontends,
focused menu/core/Git suites, docs and wiki. No live commit/push or package changes
are authorized by this implementation request.

Verification: 119 package core tests, 10 package integration cases, 21 launcher
cases and five new publication cases pass. The publication cases cover both
Bash and the shared native controller, forced-color JSON, preserved manual
decisions, unrelated unstaged files, no-op updates, ignored/partially staged
manifests, cancellation, drift, inventory failure and Windows refusal. Sixteen
existing Git publication regressions pass (eight per frontend). All 11 wiki
publication cases pass across full/focused runs, including the new manifest,
source and wiki ordering case. The Bash wiki fixture now explicitly supplies its
owned Git configuration instead of reading the live checkout's owner rules.
Both completion frontends, 238 command routes, generator checks, Bash syntax,
relative links and whitespace pass. The wiki was rebuilt in transaction
`5cb1ece550c848039ff9fcb96cc6f9d3` and checks healthy. Real native Windows
PowerShell 5.1/7 and Linux/WSL terminal acceptance remain pending. All Git
commits/pushes used temporary local test repositories; the working checkout and
its remotes were not published, and no host packages were changed.
