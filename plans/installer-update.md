# Interactive checkout installation

**Status: Implemented; final acceptance blocked on the real Leaf build.** Parent Todo: `022292f71f29492c8d9e1a3ddad7f556` (`installer-update`). The owner approved this plan on 2026-10-31. Existing checkout changes remain independent; implementation does not authorize live installation, package changes, source updates, commits or pushes on the developer's machine.

## Agreed experience

All root shell/PowerShell scripts, `dots files install/uninstall` and `dots init --setup` share a terminal wizard. The initial selection is core, files, themes, Anodize, Blastoff and pkgs; packages, fonts and patched Leaf are optional. Explicit saved profile choices replace these defaults. Files can be narrowed to enabled applicable catalog IDs, retaining their declared strategies. Exclusion during install does not remove existing components. Uninstall selects owned components and preserves drift, user data, packages, font libraries/registrations, build caches, source checkouts, saved preferences and recovery records.

Clear the visible screen once (retain scrollback) and render `logo.txt` with a horizontal semantic-color gradient on wizard entry. Reuse shared presentation, optional Gum, numbered fallback, configuration inheritance and progress. Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate), including 40/80/120-column views, plain output, cancellation and literal arguments. JSON, help, dry-run and redirected output never enter the wizard, clear, brand or animate. Dry-run does not write, download, fetch or build.

Expose equivalent native parameters and long options: `--interactive`, `--non-interactive`, repeated `--component NAME`, repeated `--resource ID`, `--with-dependencies`, `--save-choices`, `--no-clear`, `--no-logo`, `--fonts FILE`, repeated `--font-target TARGET`, and existing setup options. Component arguments replace component defaults; resource arguments imply and narrow files; `--packages FILE` and `--fonts FILE` add their stages. Noninteractive writes require `--yes`; explicit interactive mode conflicts with JSON, dry-run and yes. Preserve existing result fields/statuses with additive selection/stage records.

The unchecked Save choices option persists component/resource/dependency defaults through `apps.setup`, and package/font choices through their existing active-profile owners. Run-only customization never replaces saved preferences. Missing profile manifests/preferences produce an empty, explained selection. Setup controls activate on the next invocation; no theme refresh is needed for behavioral controls. Shared colors/icons/alignment/progress remain authoritative.

## Sequencing and safety

Read-only preflight and selection precede preparation approval. Preparation covers declared dependencies/packages, source/font acquisition and builds. Then display the exact final managed plan for separate approval. `--yes` approves declared stages in batch mode. Changed inputs or unexpected scope stop the run. Stop at the first failed stage; preserve/report completed external effects. Compose final file/theme/Leaf/font/preference/receipt operations through the existing Store, reject conflicting writes, and retain reverse rollback and original uninstall baselines. Record stage outcomes and recovery IDs.

Fix the expected `.termux` directory-link case by validating the exact effective catalog mapping, guarding the link and catalog, and writing the physical source target. Never weaken general parent-link/reparse-point refusal. Reconcile legacy lexical receipt entries transactionally with original backup references intact. Verify unchanged second install, including the pre-existing fresh-checkout WSL theme fingerprint regression.

Use installed package managers and reviewed platform prerequisite mappings. Python required to start setup remains preinstalled. Never silently bootstrap managers/providers or alter trust. WinGet is the only new Windows backend: full existing package workflow, community source only, exact IDs, user scope by default, explicit machine scope. Use a fixed structured PowerShell bridge with Microsoft.WinGet.Client, offering explicit current-user module installation when needed. No automatic elevation, source registration, unrelated agreements or reboot. Unknown/uncorrelated packages remain visible with unsupported reasons. Scoop, Chocolatey, Store/private sources and other Windows backends are excluded.

Leaf acquisition uses commit `140e55858c98df50ba52fc4ab7bad277a31ab73f` and the retained patch for `1.28.2+dots.1`, in owned build storage outside Dots and existing user checkouts. Run locked Rust tests, Clippy and release compilation, plus consumer checks. Reuse artifacts only with verified source/patch/platform/architecture/toolchain identity. Publish a managed user command with retained original-file backup; foreign links are protected.

Fonts restores reviewed exact saved versions/hashes/faces/targets through the existing planner, with cached/retained customization and staged downloads. Merge native user registration and app edits into final publication. Suppress app reloads. Save preferences only when requested. Uninstall restores installer-owned app font settings and retains registrations and libraries.

## Goal tree

All children have high priority and the parent above. Dependency IDs are also saved in their Todo notes.

| Package | Full UUID | Dependencies | Acceptance |
| --- | --- | --- | --- |
| P1 Selective lifecycle and safe managed destinations | `6113f2bd98d1481e80223382f3fb911a` | None | Selective ownership, legacy baselines, expected/foreign/stale Termux links, no-op repeats, rollback and recovery pass. |
| P2 Interactive wizard, presentation, and saved choices | `f425a79c3a804ae098a86949220da979` | P1 | All entry points, granular choices, two reviews, Config/menu consumers, cancellation and terminal/data contracts pass. |
| P3 Native WinGet package workflows | `2f9fedc99c7c4f0282d1edb31ae8db71` | None | Full shared workflows, exact IDs/scope, native bridge, completion/config/menu capability handling and fixtures pass. |
| P4 Dependency and package preparation | `e3ebfd22ce7d4020a5ed713ab3d2c94e` | P1, P3 | Profile selection, explicit prerequisites, stop-on-failure, retained effects, idempotence and dry-run purity pass. |
| P5 Reproducible patched Leaf installation | `82c7cde3a20840de8457470aaa74c760` | P1, P4 | Locked verified build, artifact reuse, safe publication/restoration and isolated real Termux consumer checks pass. |
| P6 Profile font restoration and safe removal | `5134f1c395cd45ba836613e7346756c2` | P1, P4 | Exact choices, staging, merged native operations, run-only preferences, no reload, drift/failure/repeat and app-setting restoration pass. |
| P7 Installation audit, documentation, and acceptance | `aa24de9d866c479e8e97b70d253eb917` | P2-P6 | Combined scenarios, both regressions, both shells, documentation/metadata/wiki and native acceptance record are complete. |

## Integration review and verification

Profile-row presentation follow-up: show the active leaf profile ID in bold yellow with its parenthesized home-abbreviated directory in dim terminal foreground and the shared blue label. Reuse `Presentation.detail_spans` for wrapping and styling in both shell entry points. Files maintenance owns this display change. Configuration review: **no configuration integration change needed**, because existing color and row-layout controls apply. Menu review: **unchanged**, because selection and handoff behavior are unchanged.

Profile-row verification: all seven setup wizard tests passed. Owned terminal checks at 40/80/120 columns verified the separate blue label, bold yellow ID and dim default-foreground directory spans, home abbreviation, plain output and mutation-free cancellation. Native PowerShell terminal acceptance remains pending.

Primary lifecycle owner: Files maintenance. Package, Fonts, Theme and Plugin maintenance own their boundaries. Configuration review: **add** `apps.setup` controls; **update** WinGet package choices/capabilities. Reuse semantic color/icon/layout settings without duplicate controls. Menu review: **add** Install/Uninstall terminal actions under Files; **update** Windows package capabilities. No implicit approval in menu handoff.

Tests own all home/config/state/cache/repository roots, fake managers/network and private terminals. Run file-platform checks before lifecycle tests; select affected installation/adapters, bundled apps, packages, fonts, Config/menu, presentation and metadata suites. Cover preflight, original backups, rollback/interruption, stale inputs, selective removal, paths with spaces/Unicode/leading dashes, broken links, missing parents, build/package/font failures, Windows registration and exact structured output. No tests may target host package managers or real configuration.

Update canonical installation, package, fonts, Leaf, commands, architecture, specification, safety, platform/testing and README documentation as affected; rebuild/check the available wiki through its managed workflow. Run relative-link and whitespace checks. Native Windows PowerShell 5.1/7, Linux and WSL runs unavailable locally may be documented pending, not reported as passes or hidden behind fixture evidence.

## Evidence

- Planning baseline: basic isolated install/restore idempotence passed. `test_fresh_checkout_wsl_setup_connectors_check_and_restore` failed because the second install republished the theme and active/selection pointers (two tests, 78.132 seconds).
- Saved the seven goals through Todo CLI and verified IDs, parents and acceptance before implementation. P1, P2, P3, P4 and P6 are complete. P5, P7 and the parent remain blocked on the required actual Leaf build, with their original criteria retained.
- Full installation lifecycle: 28/28 pass, including original baselines, drift, rollback/recovery and the fresh WSL theme repeat regression. File-platform: 5/5. Component selection/mapped destinations: 5/5. The checkout's own `./install.sh --dry-run --json` succeeds with 78 Termux items and no conflicts; it did not apply an installation.
- The five new `test_setup_*.py` runners cover 24 cases: component ownership, exact directory mapping, real 40/80/120-column wizard cancellation, two reviews, Config activation, menu handoff, explicit saved choices, stages, build orchestration, exact fonts, Windows copy/registration fixtures and combined install/repeat/selective removal. All cases pass; the final wizard rerun is 6/6 after supplying its missing fixture commands. Staging cleanup is explicit on success, cancellation and failure, and checked with ResourceWarning treated as an error.
- Package core: 167/167 pass; final WinGet fixtures: 7/7, including shared export/restore pins, repeat, upgrade/refresh, ambiguous inventory and native picker Details without a shell. Package integration's functional cases pass; the metadata/completion defect was fixed and the affected case rerun successfully. Adapters: five passes and five explicitly unavailable native checks. Bundled apps: 17 passes and one unavailable PowerShell check.
- Fonts: 21/21; font workflows: 18/18; Config values/profile checks: 12/12; Config live-consumer checks: 11/11. Generated bundled metadata, changed Python syntax, Bash syntax, skill validation, whitespace and canonical relative-link checks pass. Wiki generation/check results are recorded in the final audit Todo note.
- Required actual Termux Leaf build: **blocked**. GitHub Git HTTPS, codeload.github.com, index.crates.io and static.crates.io return proxy CONNECT HTTP 403, including an escalated read-only Git probe. The local pinned source exists, but the Rust registry cache is empty. The attempt used an owned temporary root; no installed command was replaced. Fixture build checks are not evidence of actual compilation. Resume the isolated locked test/Clippy/release build and real consumers when downloads are available, then complete P5, P7 and the parent in order.
- Native Windows PowerShell 5.1/7, Linux and WSL runtime/build/visual acceptance remains pending as agreed. Windows path, registration and package fixtures do not establish native runtime acceptance. No host package installation, application reload, commit or push was performed.
