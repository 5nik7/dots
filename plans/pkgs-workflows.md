# Package workflows

## Native Go updates and package progress (2026-10-31)

The user now requests native `go install PACKAGE@latest` as the default,
superseding the earlier helper/force preference. Compare installed build versions
with native latest-module queries and install only newer eligible tools. Share
query/version comparison with `upls`; deduplicate module lookups, preserve major
paths, and never downgrade newer/prerelease builds. Queries remain bounded and
outside the working project with toolchain downloads disabled. A failed query
must fail preparation rather than become an empty success or guessed update.

Keep source/replaced/renamed/ambiguous exclusions, skip overrides and literal build
flags. Explicit replacement recipes keep their own semantics and bypass the
default version gate. Show each native install's binary name before it produces
output, retain that target through download/build chatter and show elapsed silence
after 15 seconds. Preserve raw/dry-run commands and actual failure/cancel status.
Do not start or stop live upgrades or mutate the installed npm dependency tree.

Owner: `dots-pkgs-maintenance` with shared presentation. Configuration: **no
configuration integration change needed**; existing policies already support
explicit helper/custom replacements and native flags. Menu: **no menu change
needed**; existing upgrade/list actions use the shared core. Both shell surfaces
share this behavior; Windows/WinGet and native Linux/WSL/PowerShell acceptance
remain separate. Verify current/newer/older/prerelease versions, shared modules,
query failures, policies, helper non-use, per-package progress, raw/JSON and
40/80/120-column output in owned fixtures. Refresh canonical docs/wiki and append
verification to the completed Todo goal without reopening it.

Implemented and verified: all 167 package-core cases pass, including the new
Go version/policy cases, no-TTY native-install fixture with a sentinel helper,
dry-run purity and per-tool progress through quiet builds. Private terminal
checks cover Go/npm at 40/80/120 columns, plain/color, failures, interruption and
terminal restoration. Package metadata, shell syntax, relative documentation
links and whitespace checks pass. The aggregate command check currently rejects
option metadata in `bin/dots-files-install`, part of concurrent installer work
outside this follow-up. No host Go tools were installed or upgraded;
native Go build/toolchain acceptance remains separate from the owned fixtures.

Warning investigation: the two named deprecated modules are installed under
`live-server`. Maintainer notices describe retirement, not an upgrade failure or
a specific vulnerability finding. The corresponding native npm log also reports
blocked install scripts for five packages; those approvals were left untouched.

## Visible npm activity (2026-10-31)

The user left the apparent npm hang running. Read-only inspection found the
native npm process consuming CPU, completing registry downloads and entering
postinstall scripts. Preserve that running transaction. Its loaded controller
cannot acquire new presentation behavior mid-run.

For subsequent compact upgrades, request npm's native info-level events through
the child environment, retaining explicit environment/CLI logging overrides and
exact recipe arguments. Show safe package identities from metadata/cache/tarball
events and lifecycle script stages, with a quiet-time counter after 15 seconds
without output. Describe completed fetches as fetched, not invented transfer
percentages; progress labels omit URLs, credentials, query strings and script commands.
Keep raw/ordinary redirected environments unchanged, custom non-npm commands
untouched, and prompts, diagnostics, cancellation and native status intact.

Owner: `dots-pkgs-maintenance` and shared CLI presentation. Configuration: **no
configuration integration change needed**; existing output modes and native
logging flags/environment suffice. Menu: **no menu change needed**; existing
upgrade actions use this shared runner. Verify fake-stream and owned native npm
fixtures, overrides, silence, failures and narrow terminals; update canonical
docs/wiki and append a note without reopening the completed Todo tree. Native
Windows/WinGet and concurrent installer work are outside this follow-up.

Implemented and verified: the original global npm batch and the subsequent exact
Codex replacement both logged exit 0, and the existing run advanced to Go without
intervention. Native npm warned about blocked lifecycle scripts; no script
approvals were changed. Thirteen compact-output cases (including npm activity in
real 40/80/120-column PTYs), the native npm loopback/prefix fixture and all 39
workflow cases passed. The native fixture confirms info fetch events and explicit
CLI silence precedence. Metadata, documentation links and whitespace checks pass.
Docs and the local wiki were refreshed; native Linux/WSL/PowerShell acceptance
remains separate. No live package transaction was started or stopped by the agent.

## npm platform failure and visible pip activity (2026-10-31)

The recorded npm failure occurs in the ordinary global update batch before the
Codex recipe: npm checks an unrelated, intentionally installed Linux ARM64 alias
against Android. Use targeted native global installs for selected npm upgrades,
preserving skip lists and the exact Codex replacement. Keep project npm update
semantics. Verify against real npm in an owned prefix with a loopback registry
and an unrelated unsupported-platform fixture, without global force overrides.

Compact pip progress must show its current package, actual native download bytes,
metadata/build/install stages and elapsed silence. Request raw pip progress and
unbuffered Python output only for native pip commands in compact upgrades; preserve
explicit progress overrides, full raw/redirected streams and native exit status.
Recognize partial build-stage lines without treating ordinary fragments as prompts.
Do not call a slow task hung, invent percentages or terminate ongoing builds.

Owner: `dots-pkgs-maintenance` with shared CLI presentation. Configuration: **no
configuration integration change needed**; existing output mode, native pip options
and recipes remain authoritative. Menu: **no menu change needed**; existing upgrade
actions use the shared controller. Concurrent native Windows/WinGet changes are
outside this follow-up; actual Linux/WSL/PowerShell acceptance is separate from
Termux and owned fixtures.
Verify native npm isolation, Codex recipe argv, pip stage/byte/silence rendering,
prompt/cancel/status and raw-mode preservation at 40/80/120 columns, then update
canonical docs/wiki and append verification without reopening completed goals.

Implemented and verified: 161 package-core cases passed, including the real npm
loopback/prefix regression and exact Codex argv. All 11 compact-output cases also
passed after bounding malformed progress counters. Nine shared presentation cases
passed, including private popup checks at 40/80/120 columns; the unavailable
native PowerShell case skipped. No host packages were installed or upgraded.

The broader package-integration run passed seven cases and failed four outside
these npm/progress paths: two installer previews no longer expose the expected
top-level `packages` field, the missing-prerequisite setup case returned no JSON,
and the Windows boundary case still expects the refusal removed by concurrent
WinGet work. Preserve that ongoing installer/Windows work; its reconciliation and
native acceptance are not claimed complete by this follow-up. The user's original
pip job had ended before inspection, so its actual delay remains undiagnosed.

## Go helper force default (2026-10-31)

Requested follow-up: generated Go upgrade commands use `go-global-update -f`
before the selected binary names. This asks the helper to reinstall selected
tools even when their versions are current. Existing identity/source checks,
skip policies and explicit replacements still apply; direct `go install`
fallback and custom build flags retain their own behavior. Dry-run prints the
planned command without invoking the helper.

Owner: `dots-pkgs-maintenance`. Configuration: **no configuration integration
change needed**; this is the requested helper default and explicit replacement
recipes already permit customization. Menu: **no menu change needed**; existing
upgrade actions share this adapter. Both POSIX entry points use the shared core;
native Windows keeps its package-operation refusal. Verify exact helper argv,
no-TTY execution, dry-run purity and direct fallback with owned fake tools;
refresh the documentation/wiki and append a Todo note without reopening goals.

Verification: all 39 workflow cases pass, including a fake-helper CLI run without
a controlling terminal and a dry-run that does not invoke the helper. Existing
missing-helper fallback and custom build-flag checks pass. Metadata generation,
relative documentation links and whitespace checks pass. No host Go tools were
updated; native platform acceptance remains as documented above.

## Follow-up implementation (2026-10-31)

Authorized continuation: aliases `in`, `un`, `up`, `xup`, `upls`; equivalent
read-only `upgrade ls` / `upgrade --list`; reviewed manifest cleanup; personalized
Codex npm recipe; concise APT mirror diagnostics. Preserve the completed Todo
tree and append verification notes without reopening its records.

Implementation order and acceptance:

1. Normalize aliases in the shared grammar, retaining literal operands after
   `--`. List updates with native read-only queries for every supported manager,
   using the same scopes and exclusions as bulk upgrade. System indexes remain
   cached; language queries may contact configured registries. Show one manager
   summary and package/version rows, bounded failures and exact schema-1 JSON.
   Never execute recipes or upgrades while listing; a failed query is not an
   empty successful result. Refresh indexes separately with `pkgs refresh`.
2. `cleanup [FILE]` defaults to the active profile manifest. Only disabled pip
   entries with the exact source/editable reason qualify for review. Reinspect
   provenance, metadata paths and system ownership; uncertain/system-owned,
   absent, other-platform and other-scope records are excluded. Preview first,
   select with the existing FZF picker, show native uninstall argv, require a
   separate default-no terminal confirmation. Recheck manifest/config/profile
   guards and selected provenance before removal. `--dry-run`/`--json` only
   inspect; `--yes` cannot bypass this review. Keep manifest records and original
   source trees. Report actual removal failures and verify absence afterwards.
3. Through guarded Dots Config, preserve existing npm policy and configure
   `@openai/codex` install/upgrade replacement with the user's exact global
   two-package command. Skip the companion alias in ordinary npm updates.
   Do not execute the recipe against host packages during development.
4. Retain partial output until a complete line or recognizable prompt, so mirror
   fragments cannot join result rows. For APT unexpected-size/mirror-sync errors,
   preserve failure status and report a short retry-after-sync hint; never bypass
   integrity checks, change repositories or silently retry transactions.

Configuration assessment: **update** existing native npm policy using its guarded
Config bridge; no new controls needed for aliases/list/cleanup. Reuse shared
presentation settings and next-invocation activation. Menu assessment: **add**
upgradable-package report and cleanup terminal action; aliases reuse canonical
actions. Family owner remains `dots-pkgs-maintenance`.

Verify parser/completion/metadata on both shell surfaces, per-manager parsers and
partial errors, no mutation from listings, fake-manager cleanup cancel/confirm,
stale/ownership guards, literal Codex argv, fragmented APT output, narrow widths,
color/plain/JSON. Use owned home/config/state/cache roots and private terminals.
Update command/package/safety/schema docs, README/manual and generated wiki.
Native Windows preserves explicit package-operation refusal; native Linux/WSL
and PowerShell 5.1/7 runtime checks remain pending, not inferred from fixtures.

Follow-up verification: 149 core cases passed in the full run; all 20 final
cleanup/update-command cases passed after the layout refinement and added
end-to-end cleanup case (150 distinct core cases). A private terminal with owned
fake pip/FZF proves Escape, default-no/declined confirmation and accepted removal
through the real CLI, preserving manifest/source metadata. All 11 package
integration cases and 17 bundled adapter cases passed; nine presentation cases
passed. The adapter/report suites each skipped one unavailable native PowerShell
case. The updated native-Windows refusal fixture also passed for every new alias,
listing spelling and cleanup. Shared reports fit 40/80/120 columns.

Generated metadata, 244 command routes, 1207 documentation links and whitespace
checks pass. Local wiki rebuilt and healthy, transaction
`a30bd6090a8649c396905b5bc38c92f8`. The user's Codex npm policy was saved with
retained recovery through Config transaction `db0e7df9d6b84a7bb03674d3fdd96761`;
a live-config dry-run displayed the exact requested command without executing it.
No host package mutations, commits or pushes. Existing manifest/weather edits
and unrelated Todo records remain untouched. The completed selected Todo tree
retains all UUIDs, parent relationships, acceptance criteria and done statuses.

Status: implemented and verified in isolated Termux fixtures (2026-10-31). Owner: `dots-pkgs-maintenance`. Native acceptance limits are recorded below.

## Agreed outcome

Both `pkgs` and `dots pkgs` share unattended user-wide upgrades, Go tool updates,
literal package policies, compact human upgrade results, full styled output for
other operations/stdin and raw mode, editable JSON
exports and optional package-first checkout setup. Explicit install commands and
accepted install-picker selections authorize installation without an extra flag.
Removal/restore approval and package-manager protections remain. Package effects have no Dots
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

Human upgrades use compact results and short diagnostics. Other formatted output
keeps full manager messages except the explicitly suppressed APT script advisory,
recognizes events and preserves unknown text. Raw forwarding retains native bytes.
JSON, manifests, completion and ordinary redirected
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
At that stage, install/removal/restore approvals and the Arch refresh refusal remained. The
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

## Install without an extra flag (2026-10-31)

The user explicitly extends unattended execution to install after encountering
the no-controlling-terminal error for `pkgs install bun`. Direct installation
and accepting an install-picker selection authorize execution, including without
a controlling terminal. The common workflow supplies supported native approval
flags, keeps the visible command preview and preserves dry-run, picker
cancellation, skips, literal operands and manager failure statuses. Removal,
restore and manifest replacement retain their own approval boundaries.

Owner: `dots-pkgs-maintenance`. Configuration assessment: **no configuration
integration change needed**; this is the requested command default, and existing
output/policy controls still apply. Menu assessment: **no menu change needed**;
the existing install action reaches the same picker and shared execution path.
Standalone and Dots-prefixed commands share the implementation. Native Windows
keeps its package-operation refusal; no app destinations change.

Acceptance: use isolated fake managers to check named and picker installs without
`--yes` or a controlling terminal, Termux native `-y`/`--noconfirm`, dry-run and
cancel purity, retained removal/restore approval and propagated failures. Run the
package core and relevant entry-point checks, regenerate metadata, verify docs
and rebuild/check the available wiki. Retain the presentation gate's existing
40/80/120-column coverage. Linux/WSL and native PowerShell evidence remains
pending. Record progress through Todo notes without reopening completed goals.

Verification: all 122 package core tests and 10 package integration tests pass.
Bundled entry-point, completion and native-boundary checks pass (17 passed,
one native PowerShell runtime check skipped). The core includes the 37-case
workflow suite and existing real-FZF PTY checks. Generated metadata, all 238
command routes, Bash syntax for 18 package adapters, skill validation, 1205
relative documentation links and whitespace checks pass. The active `pkgs`
entry point resolves to this checkout. Tests used fake managers and owned roots;
no host packages, active shell state or publication targets were changed.

## Concise upgrade output (2026-10-31)

The user requests a simple default after seeing full command arrays, repeated
APT/dpkg progress, pip requirements, uv no-op messages and per-package skips.
For actual upgrades in human terminals/menu readers, or explicit styled mode,
show one heading, shared transient progress and one result per manager. Count
skips; retain short actionable failure/warning details and accurate exit status.
Do not infer upgrade counts or success from log text. Preserve partial prompts,
continue independent managers and restore child terminal settings on exit.
Default redirected output, `--raw`, full dry-run plans, JSON and other commands
retain their contracts. The standalone stdin formatter remains a full formatter.
This supersedes the earlier full-log default for human upgrade runs only.

Owner: `dots-pkgs-maintenance`, with `dots-cli-presentation`. Configuration:
**no configuration integration change needed**; reuse output auto/styled/raw,
shared semantic roles, layout, color/icon and progress controls. Menu: **no menu
change needed**; the existing upgrade preview/Run flow retains its full preview.
No manager selection, npm package policy, package flags or Windows destinations
change. Native Windows retains its package-operation refusal.

Acceptance uses fake managers and owned roots: long APT/pip/uv noise reduces to
bounded results; npm E404 and unknown failures remain actionable; a failure cannot
become success and later managers still run; skips are counted; prompts and
interruptions remain usable; raw/redirected bytes and dry-run commands remain.
Exercise 40/80/120-column PTYs and color/NO_COLOR/progress controls. Run focused
core and integration/report checks, synchronize docs and the local wiki, and
append Todo verification without reopening completed goals. Native Linux/WSL
and PowerShell acceptance remains pending; never run a host upgrade for tests.

Verification: 127 package core cases passed, followed by nine final focused cases
including a new empty-plan/launch-failure case (128 distinct core cases overall).
All 10 package integration checks and nine presentation checks passed; one native
PowerShell presentation check was skipped. Private PTYs at 40/80/120 columns
cover enabled/disabled color, progress, native newline changes, failure and
Ctrl-C restoration. Reviewed rendered compact results at all three widths.
Long fake APT/pip/uv logs reduce to four manager rows; npm E404 stays visible and
pip still runs afterward. Raw output, full previews, unknown failures, warnings
and partial prompts remain covered. Metadata, 238 command routes, skill validation,
1205 documentation links and whitespace checks pass. No host packages changed.

## Manifest update without an extra flag (2026-10-31)

The reported `export --update` invocation must authorize its own merge/write
without an additional `--yes` or controlling terminal. Apply approval only at
this explicit CLI action. Preserve the shared guarded writer, retained backups,
manual pins/disabled/absent entries, profile defaults, complete-inventory
requirement, stale-input refusal, no-op updates and dry-run purity. Ordinary
snapshot replacement, restore and Git publication retain their approval rules.

Owner: `dots-pkgs-maintenance`. Configuration: **no configuration integration
change needed**; the explicit update action supplies authorization. Menu:
**no menu change needed**; its existing preview/Run gate and cancellation remain.
Both standalone and Dots routes share the implementation; native Windows keeps
the existing package-operation refusal. Verify no-TTY updates for explicit and
profile-default paths, retained undo, stale/partial failures and ordinary export
replacement refusal with fake inventory and owned files. Refresh metadata,
documentation and the available wiki; record verified progress through Todo notes.

Verification: all 38 workflow and 10 package integration cases passed. Explicit
file updates run without a controlling terminal or `--yes`, preserve edits and
retain undo; unchanged updates keep their mtime. Profile-default updates of an
existing manifest receive automatic approval without mutating the parsed args.
Stale/partial snapshots and ordinary replacement approval remain covered.
Generated metadata, 238 command routes, skill validation, documentation links
and whitespace checks pass. No live manifest or host packages were changed.
