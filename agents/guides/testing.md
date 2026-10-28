# Testing Work Guide

Read this guide before adding tests, changing test runners, touching mutation code, or claiming platform support or a performance improvement.

Run checks appropriate to the changed files from the existing checkout, using test-owned home, config, state and cache roots. Documentation changes require `python3 -B tools/verify_docs.py` and `git diff --check`.

## Isolation Is Mandatory

For transaction copy/flushing or installation receipt changes, run
`python3 -B tools/test_file_platform.py` before the affected installation and file
operation suites (`python` on Windows). Retain read-only source metadata,
permission-sensitive drift checks and `022`/`077` umask regressions. Native
PowerShell runtime caches must stay test-owned; never ignore all cache changes to
make a read-only test pass. See [checkout tests](../../docs/testing.md#checkout-installation).

Tests must receive explicit test-owned roots for home, repository, config, data, state, cache, and executable installation. A test must fail closed if any resolved mutation target escapes those roots.

Never let a test:

- Write to the developer's real home or platform config directory.
- Change the active shell, environment, registry, Developer Mode, or package database.
- Initialize private submodules or prompt for credentials.
- Depend on the current repository being clean.
- Delete a broad directory through an empty or unresolved variable.

## Test Layers

- Unit tests: route resolution, catalog parsing, precedence, path normalization, classification, and inverse-operation construction.
- Golden tests: human plans, JSON plans, help, command discovery, and generated documentation.
- Filesystem integration tests: apply, interruption, rollback, undo, drift, and repository relocation in a temporary sandbox.
- Adapter contract tests: every platform adapter produces equivalent normalized behavior from fixtures.
- Checkout setup tests: disposable platform environments and failure injection.
- Performance tests: dispatcher startup, command discovery, catalog resolution, and large-plan generation.
- Manual platform checks: gaps that hosted CI cannot reproduce faithfully, recorded with environment and result.

## Required Safety Cases

- No-op idempotent apply.
- Existing regular file and directory.
- Correct, incorrect, and broken links.
- Permission failure before and during apply.
- Process interruption after each journal boundary.
- Rollback failure with actionable recovery instructions.
- Undo after the managed target has drifted.
- Link unavailable with copy fallback disabled.
- Path traversal and destination escape attempts.
- Secret redaction in human and structured output.

## Performance Method

- Establish a baseline on at least Termux and one conventional desktop platform before setting hard budgets.
- Measure cold and warm runs separately where the distinction matters.
- Benchmark with representative small and large command/resource sets.
- Record environment, build mode, sample count, and statistical summary.
- Do not call a change faster based on one interactive run.

## Yazi Configuration

For the local symlink header component, use the isolated Lua checks described in [the testing reference](../../docs/testing.md#yazi-symlink-component). Keep simulated text widths and Windows paths distinct from native Yazi rendering evidence.

## Documentation

Run `python3 -B tools/verify_docs.py` and `git diff --check` for documentation changes. The checker validates relative Markdown targets in README, AGENTS, guides, docs and plans without Go or optional submodules. Its fixture regressions run with `python3 -B tools/test_verify_docs.py`.

The [repository checks workflow](../../.github/workflows/repository-checks.yml) runs documentation and wiki-generation regressions, source-only wiki validation, the link checker and latest-commit whitespace check on Linux and Windows. Its path filters cover Markdown, documentation checkers, wiki inputs/controllers/tests, command metadata and the workflow. The separate [worktree lifecycle workflow](../../.github/workflows/worktree-lifecycle.yml) runs helper tests and the whitespace check only when the helper, its test script or its workflow changes; documentation-only changes do not run helper tests.

The test commands in `docs/testing.md` must exist before they are presented as runnable. Keep support claims limited to actual native results and distinguish skipped cases and simulated platform fixtures.

## Bash Command Framework

Use the [Bash test entry points](../../docs/testing.md#bash-command-framework) for
`bin/dots`, `lib/dots`, and its three shell adapters. Test all installed Bash/Zsh/Fish
interpreters with owned homes and fixture commands, including real Tab input and
changes visible without reloading. Never execute existing `dots-*` extensions as
test fixtures. Keep sequential benchmark intervals free of other tests. Preserve
the existing Zsh cache/reload regression coverage and FZF-tab acceptance.

For new or changed human views, apply the [presentation acceptance gate](../../docs/presentation.md#acceptance-gate) using the existing command suites and test-owned roots. Cover the applicable output modes and states, review representative terminal layouts, and report gaps. Cross-renderer policy checks and forced-decoration data checks are required when shared presentation behavior changes; current evidence does not establish every command or native platform.

## Shared menu library

Application report changes also require `python3 -B tools/test_plugin_reports.py -v` and the affected plugin core suite. The report fixture owns all home/config/state/cache paths and mocks package queries; popup acceptance uses private clients. Preserve ordinary redirected formats and compare JSON/raw/completion bytes with decoration forced. See [application plugin testing](../../docs/testing.md#application-plugins).

Run `python3 -B tools/test_menu_launcher.py` for the launcher and Prefix m/s. Load only the selected binding lines into private fixture servers, and use harmless stand-ins for workflows that could mutate files or themes. Verify exact-client handoff, no nested key/session popup hosts, cwd, cancellation, original exit statuses and ordinary native-frontend dispatch. Use harmless Git command stand-ins for native publish/sync handoff, and cover failed/canceled previews, default Cancel and explicit Sync without network or live repository writes. Measure fitted reader terminals at 40/80/120 columns, including wrapped content, long-output caps, loading cancellation and deferred wiki documents. Include navigation/query restoration, empty-search Back, F1 help and the session-success exit exception. Run `python3 -B tools/test_menu_pager.py` for capture, scrolling/fallback, private cleanup and command-status checks, plus `tools/test_wiki.py` for paged document selection. Key-context changes also require key/browser/IPC regressions; never reload the live tmux configuration as a test.

Run `python3 -B tools/test_menus.py` for `lib/dots/menus.py`, `menu_tmux.py` and `menu_host.py`. Use the [shared-menu testing contract](../../docs/testing.md#shared-menu-support), including private two-client tmux fixtures, literal argument/transport checks, cancellation and data nonexecution. Changes to `RichSelector` also require affected existing picker regressions. Keep fixture Windows argument checks distinct from actual native PowerShell acceptance; the family launcher is implemented. Run `python3 -B tools/test_menu_sessions.py` for session inventories, both dispatcher routes/help/completion, typed JSON and private native switch/attach behavior. Also run the existing shared `t` helper suite (`tools/test_tmux_sessions.py`) when session interaction changes.

## Tmux status and named sessions

For automatic Termux attachment and exit/detach lifecycle changes, run `python3 -B tools/test_termux_autostart.py`; include optional Androidots launcher tests when that checkout is available. For managed workspace identities, run `python3 -B tools/test_tmux_workspaces.py -v`, including sustained two-client rendering, all-pane project transitions, manual opt-out, failure retention, literal names and exact-client creation. Syntax-check `shells/shared/tmux-workspaces.sh` in Bash/Zsh and run ShellCheck. Use owned procfs/session-discovery fixtures and private tmux servers; real app startup remains a manual gate. Syntax-check the shared startup hook with both Bash and Zsh and run ShellCheck in Bash mode.

For the status adapter/configuration, run `python3 -B tools/test_tmux_status.py`, `python3 -B tools/test_android_status.py` and the theme/workflow suites. Run the Androidots status/session/launcher regressions as described in the testing reference. The Android integration fixture overrides the copied provider-command boundary, including the absolute location command; never depend on PATH mocks alone to prevent Android access. Assert Wi-Fi/data/neutral uncertainty visibility, fresh inactive hiding, independent telephony-device freshness, disabled-helper nonexecution, fixed network positions across transitions, stale markers and the single-space battery gap across percentage changes. Capture unknown/stale/recovery transitions and repeated reloads at every required width. Verify the upper Termux tab strip after the clock, per-client highlights, clipping and failure clearing; lower tmux numbering is independent and local to project/label groups. For the lower row, verify current-only number/project badges, no other-session indicators or overflow marks, no session underlining, single-space number/name joins, dark_background boundary bars, padding around current and inactive windows, compact warnings and stable spacing on selection, full-name/case-sensitive window shortening, literal Unicode/format punctuation, long badge limits, native window scrolling/mouse targets and COPY/PREFIX/ZOOM placement. Retain separate legacy adapter before/after and clipping coverage. Androidots regressions retain read-only volume/cache coverage. The status suite mocks Termux session discovery and uses owned inner/outer tmux servers for per-client and narrow-screen checks; never use the real session script or Android APIs as a test backend. The optional `DOTS_TEST_BATTERY_SOURCE` integration copies only upstream source into the fixture, mocks all battery API calls and never loads real battery configuration. For `t`, run `python3 -B tools/test_tmux_sessions.py`, the shared-shell regressions and applicable shell suites/PTY runners below. Keep tmux sockets, sessions, homes and configurations test-owned; never source into the live server. See [status testing](../../docs/testing.md#tmux-status-and-named-sessions).

For Codex window coloring, run `python3 -B tools/test_codex_status.py -v` plus the existing status, keybinding and focused theme-connector checks. Use owned procfs fixtures and private tmux sockets; native panes must run harmless named sleepers rather than Codex. Verify Working/Waiting/idle aggregation and title precedence, explicit Waiting and Action Required versus misleading title fields, trailing ``/`` marker styling and spacing and numberless visibility, bold magenta inactive Codex digits versus dark_foreground ordinary/fallback digits, bold bright_foreground current names on selection_background, bold, dimmed foreground inactive Codex names and dark_foreground ordinary names with no dimming on markers, padding or current/alert names, alert/current priority, padding around current and adjacent inactive labels across selection changes, all three widths, foreground stop/exit and failure clearing. Never read real credentials/session history or signal non-fixture processes. See [status testing](../../docs/testing.md#tmux-status-and-named-sessions).

For gitmux configuration/status changes, run `python3 -B tools/test_gitmux.py -v` with `DOTS_TEST_GITMUX` pointing to the installed binary when it is outside PATH, followed by file-operation/catalog, tmux status/keybinding and focused connector regressions. Keep Git configuration/hooks, homes and tmux servers isolated. Verify actual output, clipping and failure clearing separately from all-palette Bash/Python template parity; see [gitmux verification](../../docs/testing.md#gitmux-status).

## Tmux keybinding reference

For `dots keys` and `dots menu tmux keys`, run `python3 -B tools/test_keys.py`, `python3 -B tools/test_keys_defaults.py`, `python3 -B tools/test_tmux_keys.py`, the Bash dispatcher suite, and the syntax/ShellCheck commands in the [testing reference](../../docs/testing.md#keybinding-browser-and-tmux-reference). Cover category/app navigation, content-sized menus, 99% binding popups, 45% previews, field colors and cancellation. Keep native tmux sockets, sessions, configs and PTYs test-owned; tests must never load the user's config or modify the live server. Preserve Termux's inherited `LD_PRELOAD`. Record missing tmux/FZF native checks as skips and retain static-help/completion nonexecution coverage.

For tmux-to-Zsh capture, also run `python3 -B tools/test_keys_ipc.py` and the native
Zsh popup case in `tools/test_tmux_keys.py`, then affected shell/startup checks.
All socket paths, tmux servers, homes and terminals must be test-owned. Preserve
buffer/cursor/status, request deadlines, exact-pane routing, explicit coverage,
and the absence of startup/prompt snapshots. Measure startup sequentially.

For mode menus and aligned key rows, run `python3 -B tools/test_keys_browser.py` plus the existing key/tmux/IPC, shared-menu/launcher, resource and affected file/theme picker regressions. Preserve stable identities, counted menus and snapshot reuse, binding searches, cancellation, exact-client context and temporary cleanup. Cover capped columns, Unicode ellipsis, conditional fields, palette colors and left-aligned previews at 40/80/120 columns. Use owned PTYs and native PowerShell preview checks when an engine is available; argv fixtures do not establish Windows acceptance.

## Existing Yazi Configuration

For preview changes, run the standalone source repository's `lua test-preview.lua` and `python3 -B test-preview-native.py`, including `--config-dir` against a staged personal config. Keep its image cache and TMPDIR/DDS roots explicit and private; native Glow/Rich checks remain unavailable unless those tools work. Run the existing regression/package suites and Dots bundle consistency checker after package upgrade.

For `config/yazi/plugins/dots.yazi` changes, run its Lua dispatcher, Git-head metadata, hover and LS_COLORS fixtures, GNU ls oracle comparisons, and isolated native PTY runner as documented in [Testing Strategy](../../docs/testing.md#yazi-plugin-bundle). The native runner needs Python, Git, git-it, and Yazi on a Unix PTY and owns all home/config/state/cache/runtime and DDS storage. Never test project saves, deletions, or merge events against the live configuration. Keep fixture results, native platform evidence, and visual review limits distinct.

For Vivid/FSH theme adapter changes, additionally run `python3 -B tools/test_file_themes.py`
with the theme/workflow and Zsh suites. Native plugin tests must copy installed FSH
into an owned root and disable its optional secondary-theme download.

## Missing-source catalog check

For stash/edit and the Git overlay migration, run
`python3 -B tools/test_file_mappings.py` with catalog, operation, installation,
browser, confirmation, progress, resource, dispatcher and adapter regressions.
Own every source/target/state root; verify disabled claims, original backup
continuity, receipt undo, source permissions and interruption. Never use live Git
configuration as a fixture. Report actual native adapter coverage separately.

For `files check`, run `python3 -B tools/test_files_check.py` with catalog, file
operation, confirmation, progress, resource and dispatcher regressions. Fixtures
must own every catalog and target; test metadata-only undo, source reappearance,
filesystem errors and multi-catalog interruption. Never exercise cleanup against
the real tracked catalog. Native PowerShell cases require the adapter suite and
must be reported as skipped when its runtime is absent.

## Existing Zsh Configuration

For personal ZLE/keybinding changes, also run `python3 -B tools/test_zsh_keys.py` and `python3 -B tools/test_keys_zle.py`; use synthetic history and mocked clipboard commands.

For Zsh startup changes, run `python3 -B tools/test_zsh.py` plus the isolated startup and PTY runners described in [the Zsh guide](../../shells/zsh/README.md). Capture the baseline before editing and keep timing runs sequential. Never profile the live startup chain against the real home; private/platform modules use synthetic substitutes. Treat native Termux results and other-platform fixtures separately.

For Deja integration changes, also run `tools/test_deja.py` with explicit native binary/plugin paths as described in the Zsh guide. Never use live history or let test daemons escape cleanup; keep upstream test limitations separate from native PTY results.

## Development Worktree Helper

Use `python3 -B tools/test_worktree_lifecycle.py` for the separate local lifecycle helper; see [the workflow guide](worktrees.md). Tests use disposable repositories, local bare remotes and owned environment roots. Preserve refusal cases and distinguish injected idle snapshots from native process detection. Do not run the helper against live fixtures to test deletion.

Lifecycle review regressions verify preview/apply retain native FIFO and filesystem socket fixtures where supported, and that a fresh remote-main fetch ignores an additional configured recovery-branch mapping while preserving every local branch. Device/unknown modes and metadata denial use injected `lstat` results; they do not establish native device-node coverage. Native Windows FIFO/socket fixtures are unavailable and skipped. Positive portable removal still injects an idle process snapshot; native process coverage remains separate.

For shared palette, state publication, Zsh refresh, or Neovim theme adapter changes,
run `python3 -B tools/test_themes.py`; use `python3 -B tools/bench_themes.py` for performance.
The theme suite also covers the unified full-ID CLI, singular and plural routes, native palette filtering/querying, and contextual color completion. Preserve these migration checks alongside publication/recovery tests. Shared discovery fixtures verify inert sourcing, cleared enumeration results, alternate inherited checkout roots, listing/completion eligibility and next-request freshness; keep enumeration in-process for completion and measure changes before adding subprocesses.
The editor tests copy public plugin sources and never start live LazyVim or download
plugins. Missing sources report skipped tests; the optional source-map input for all
families is documented in [Shared Themes](../../docs/testing.md#shared-themes).

For the optional Gum adapter or theme switcher, run
`python3 -B tools/test_theme_picker.py` plus the shared theme/workflow and Bash
suites. This runner owns its PTYs, tool fixtures, homes and publication roots;
installed Gum enables native selection/cancellation checks at 40/80/120 columns.
Keep native tool evidence distinct from deterministic fixture backend tests.

For the tracked-config browser and Python/Bash interaction bridge, run
`python3 -B tools/test_files_browser.py`, the file catalog/operation suites, the
Bash dispatcher suite and the existing theme picker tests. Keep preview and
cancellation free of state writes; exercise metadata/source/target drift between
review and Apply. Native Gum/FZF PTY checks must use disposable catalogs and homes.

For inventory/catalog or config-link migration changes, run
`python3 -B tools/test_files.py`. For flat theme templates, connectors, imports and
wallpaper adapters, also run `python3 -B tools/test_theme_workflow.py`. This includes
Codex connector and shared syntax-theme coverage. Native Codex discovery checks
require disposable homes and no real credentials or model requests; see the
[testing reference](../../docs/testing.md#files-catalog-and-omarchy-style-themes). For Pi connector
changes, enable its optional native loader/watcher check with `PI_THEME_MODULE` as
described in [testing](../../docs/testing.md#files-catalog-and-omarchy-style-themes). These suites
own their home/config/state/source roots; local Git fixtures and fake external
adapters require no network or live app changes. Use `python3 -B tools/bench_files.py`
for inventory scaling, sequentially with other benchmarks.

## Git and managed file operations

For Git info/submodule routes, also run `python3 -B tools/test_git_submodules.py`;
keep publication in disposable repositories and local bare remotes. Record native
PowerShell terminal/engine acceptance separately from shared-controller tests.

Use `python3 -B tools/test_git_operations.py` and `python3 -B tools/test_file_operations.py` for the bounded operation engines. Fixtures own configuration/state/Git roots; publication uses local bare remotes through a test-only transport. Include abrupt interruption, snapshot drift, partial failure and optional backup cases. Run existing file and Bash suites for shared contracts and completion; never test sync, publish, import or restore against live repositories or configs.

## Anodize

`tools/anodize_build_support.py` owns the isolated offline build environment. Run `python3 -B tools/test_anodize_build_support.py` when changing it; the regressions cover owned paths, inherited-environment isolation, offline settings, telemetry configuration and missing prerequisites.

For logo changes, use `python3 -B tools/test_anodize_logo.py` for engine-free policy/PTY checks; the main Anodize check also runs it. Cover both Python help and static Dots metadata help without executing an extension. Keep Kitty protocol fixtures distinct from real graphics-terminal visual evidence.

Use `python3 -B tools/verify_anodize.py check` for the isolated core/CLI suite and `bench` for engine measurements. `build` writes only the ignored private executable. Keep all integration roots disposable and retain Termux LD_PRELOAD compatibility in spawned environments. Run existing theme/file/dispatcher suites for shared changes. Do not run the real Neovim startup or apply a live theme as a test.

The Anodize check includes `tools/test_anodize_interactive.py` for user-theme storage, promotion/recovery and transient mode/FZF previews; keep engine-free completion assertions in the separate integration suite.

For the Dots Neovim bridge, run `python3 -B tools/test_anodize_nvim.py` plus the existing theme suites. Set `ANODIZE_NVIM_DIR` to a completed local plugin checkout when needed. The shared helper copies public runtime files; do not replace it with a normal editor startup. Preserve dashboard timing and test manual colorscheme inactivity explicitly.

For Anodize completions or manual changes, run `python3 -B tools/test_anodize_integration.py` (Bash, Zsh, Fish and mandoc required), generated-artifact freshness, and the shared Bash/Zsh/FZF-tab checks when their integration changes. Completion must work without the private Go engine.

For shared operation confirmations, run `python3 -B tools/test_confirmations.py`
and the existing file/Git, browser, theme-picker and Bash suites. Anodize cases
must run through `python3 -B tools/verify_anodize.py check`. Preserve each command's
JSON/plain fallback and approval semantics; test selector failure without retry
and drift while the prompt is open. Native Gum checks require disposable PTYs and
local-only publication fixtures; see [testing](../../docs/testing.md#optional-operation-confirmations).

For shared progress or its integrations, run `python3 -B tools/test_progress.py` and the affected command suites. Follow the [progress testing contract](../../docs/testing.md#operation-progress), including data-mode suppression, native PTY cleanup, prompt-capable children and transaction rollback. Keep benchmark measurements sequential.

## Shell initialization

The PowerShell suite also executes the lean interactive profile with redirected input and stubbed optional integrations. Run it with `DOTS_TEST_POWERSHELL=pwsh` and `powershell` on Windows. Use `tools/bench_powershell_profile.py` sequentially for isolated load/first-prompt measurements; record native PSReadLine keyboard evidence separately.

For `dots init` or native startup-loader changes, run `python3 -B tools/test_shell_init.py` on Unix and `python3 -B tools/test_powershell_init.py` for portable native PowerShell acceptance, the Bash dispatcher and Zsh suites, affected theme tests, and native syntax checks. Use the isolated PTY and timing fixtures for interactive/startup changes. Use `tools/public_fixture.py` when copying these public trees so absolute symlinks cannot write through to the live checkout. Preserve synthetic private modules and distinguish unavailable PowerShell/Windows evidence from verified native Termux shells. See [initialization testing](../../docs/testing.md#shell-initialization).

For local theme plugins, run `python3 -B tools/test_theme_plugins.py` plus the existing theme/workflow, file-operation, Bash-framework and Anodize suites described in [testing](../../docs/testing.md#theme-plugins). Preserve test-owned roots, stub desktop apps, non-execution in read-only paths, and explicit desktop/native-Windows limitations.

For `bin/lib/common.sh`, run `python3 -B tools/test_common.py`, Bash/Zsh syntax checks and `shellcheck -x bin/lib/common.sh`, then the shell-init, dispatcher and Zsh regressions. Use the isolated PTY runner for reload changes. Preserve a pre-change utility snapshot and run `tools/bench_common.py` sequentially for hot-path changes; see [utility verification](../../docs/testing.md#shared-shell-utilities). Keep package checks stubbed and all directory creation inside fixtures.

For shared Bash/Zsh interactive configuration, run `python3 -B tools/test_shared_shells.py`, the shell-init/shared-utility/dispatcher/Zsh suites, affected theme suites, and both native PTY runners (`tools/bash_interactive.py` and `tools/zsh_interactive.py`). Use their owned public fixtures and synthetic private modules. Capture source/interface baselines before edits and measure comparable startup modes sequentially; report optional-tool and native-platform gaps. See [shared shells](../../docs/shared-shells.md) and the [focused plan](../../plans/shared-shells.md).

For unified theme commands and generated family wrappers, also run
`python3 -B tools/test_theme_commands.py`; retain isolated publication/recovery
and native shell completion coverage alongside the existing theme suites.

## Dots shell environment

For Dots environment changes, run `python3 -B tools/test_shell_environment.py -v` and affected shell-init/theme tests in small sequential batches. Do not use the real home or personal shell startup to validate integration-only hooks.
For `dots env` presentation, retain the owned PTY, control-character and exact
scalar/JSON/redirected-output cases; run the dispatcher suite for shared UI changes.

For file-style/publication and family presentation changes, run the focused
`tools/test_file_colors.py` suite plus publication and shell-environment cases.
Human color-view changes also retain that suite's owned native PTY width checks
and forced-color scalar/JSON/export compatibility assertions.
Yazi theme work additionally requires the plugin's `test-theme-native.py` with
private DDS/runtime roots. Keep the standalone fixture runner independent of the
main checkout and synchronize shared plugin sources deliberately.

## Checkout setup

For managed destination repair, run `python3 -B tools/test_files_repair.py` after the file-platform suite, then the affected picker, catalog, file-operation, mapping, installation and adapter suites. Keep ownership/supersession, absent replacement declarations, explicit old-link/occupied-object choices, queue cancellation and tool failure, drift after review, retained receipt baselines, partial results and no-write previews covered. Native PowerShell 5.1/7 acceptance is separate from portable controller fixtures.

For root installer, installation receipt or native file-adapter changes, run `python3 -B tools/test_installation.py` and `python3 -B tools/test_installation_adapters.py` (`python` on Windows), plus the affected existing file/theme/shell suites. Never invoke installer apply against the working home as a test. Native Windows capability refusals and skipped PowerShell cases must be reported separately from successful native execution.

For shared file/path presentation, run `python3 -B tools/test_resources.py` and the
owning command suites. Test forced-decoration data interfaces, old publications,
resource matching parity and 40/80/120-column PTYs; never generate a live theme to
validate a display-only change.

For Starship/Blastoff palette-only integration, additionally run `python3 -B tools/test_starship_palette.py` and the theme-plugin suite. Preserve byte-exact non-palette content, user palette extensions, lock/link drift guards and transaction rollback. Native rendering must use test-owned configs and synthetic repositories with no custom commands or language version probes.

For Git default templates and consolidated platform selection, run the focused
Git consumer and selector suites described in [testing](../../docs/testing.md#git-template-and-platform-selector),
plus affected publication and managed-file suites. Keep credential helpers and
Git hooks inert, and verify actual syntax-cache loading rather than config parsing
alone.

For verbose file/setup/theme action changes, run `python3 -B tools/test_verbose_operations.py`
alongside the affected existing lifecycle and presentation suites. Preserve JSON,
private bridge bytes, default output, observer failure isolation and progress cleanup.

For interactive file selection or previews, run `python3 -B tools/test_file_pickers.py`
and the affected file/browser/interaction suites as described in
[testing](../../docs/testing.md#file-workflow-pickers). Exercise native FZF keys and
40/80/120-column layouts, exact literal path selection, credential/special-file
preview refusal, noninteractive/data bypass and cancellation without managed state.

## Dual-shell maintenance

Every first-party change must cover Bash on Termux/Linux/WSL and native Windows PowerShell 5.1/7: routes, flags, aliases, contextual completion, exact data output, styled human output, progress and optional pickers. Keep native filesystem/app differences in adapters and reuse transactions. Read [native PowerShell](../../docs/powershell.md); update its capability limits and the [parity plan](../../plans/powershell-parity.md) when affected. Run focused isolated tests for both controller paths, require actual PowerShell engines in Windows CI, and report missing native/desktop evidence explicitly.

For Androidots `termux-geo` and local Termux completion paths, run `python3 -B androidots/tests/test_termux_geo.py` and `python3 -B tools/test_termux_geo_shells.py`, then affected shell startup regressions. Keep Android/HTTP mocked and completion installs inside owned fixture roots. See the [location test contract](../../docs/testing.md#termux-location-helper-and-completion-paths).

For standalone wttr and the Termux daylight clock, use `tools/test_wttr.py`, the parent tmux/Android adapter suites and Androidots geo/status/bar regressions sequentially. Mock HTTP, curl and location, test real Zsh/FZF-tab descriptions when completion metadata changes, isolate every home/cache/state/install destination, and validate attached private tmux clients at 40/80/120 columns. Verify help artwork/gradient controls and short/long alias parity, including case-sensitive PowerShell completion. Keep fixture temperature bands explicit and independent of the editable config. Check variable bands, combined attributes, widget directive validation before cache/provider access and style restoration. Use synthetic published palettes for named weather colors, check literal hex/index overrides and snapshot fallbacks, and assert exact icon/label gaps with icons on/off. Follow [the weather test contract](../../docs/testing.md#wttr-and-daylight-clock); never execute live acquisition or reload a live server for verification.

For default eza templates/connectors, run `python3 -B tools/test_eza_theme.py -v` and the affected file-color, theme/workflow, native-controller and installation suites sequentially. Keep actual eza ANSI acceptance separate from YAML parsing and simulated Windows destination checks; see [eza verification](../../docs/testing.md#eza-theme).

For Television templates/connectors, run `python3 -B tools/test_television_theme.py -v`, followed by affected theme/workflow and native-controller tests sequentially. Keep synthetic PTY inputs and all home/config/data/state/cache roots isolated; see [Television verification](../../docs/testing.md#television-theme).

For user-local completion directory discovery or precedence, run `python3 -B tools/test_local_completions.py` with the affected startup/environment suites. Use synthetic colliding providers to verify actual loading, preserving XDG overrides, native fallback paths and noninteractive boundaries. See [local completion checks](../../docs/testing.md#user-local-completion-paths).

For Leaf templates/connectors, run `python3 -B tools/test_leaf_theme.py -v`; set `LEAF_TEST_BIN` to the tested custom executable for actual syntax and PTY checks. Follow [Leaf verification](../../docs/testing.md#leaf-theme) and keep Rust and Python test/build batches sequential on Termux.

For generated theme-file inspection, run `python3 -B tools/test_theme_files.py` and affected Bash dispatcher, theme-command, native CLI and resource tests sequentially. Keep source resolution distinct from historical provenance, read only known destinations/transaction metadata, and verify inspection and cancellation create no persistent state. Follow [the test contract](../../docs/testing.md#generated-theme-file-inspection); do not refresh the live theme to test inspection.

For theme-file directory/highlighted previews and consumer evidence, also run `python3 -B tools/test_theme_file_views.py`, plus relevant plugin/Starship pure-parser and presentation regressions. The only permitted inspection subprocess is the bounded optional text renderer; configuration/environment verification must remain inert. Preserve ordinary `check` status separately from explicit `--consumers`.

For shared tmTheme reference or color-token changes, run `python3 -B tools/test_syntax_theme.py` and the explicitly selected regressions in [shared syntax verification](../../docs/testing.md#shared-syntax-reference). Preserve pinned source attribution, dynamic colors, all-palette renderer parity and isolated real-consumer evidence. Font declarations alone are not proof of rendered attributes.

For Bat cache inputs or compilation, run `python3 -B tools/test_bat_cache.py`,
the shared syntax suite and focused publication/recovery, file-color and native
controller checks. Preserve owned input roots, immutable snapshots, refusal of
preparation drift and the shell-startup boundary. See [Bat cache verification](../../docs/testing.md#custom-bat-cache-inputs).

For profile, environment bundle or bootstrap changes, run `python3 -B tools/test_profiles.py` and the focused shell/environment/installation regressions. Use only local bootstrap repositories and owned caches. See [profile verification](../../docs/testing.md#platform-profiles-and-startup-bundles).

For profile/debug changes, run `python3 -B tools/test_profile_debug.py` with
owned roots. `dots debug startup --live` is not an automated acceptance test;
use disposable fixtures. Record diagnostic overhead separately from ordinary
startup, and native PowerShell evidence separately from controller fixtures.

For retired environment variables or platform file-ID compatibility, run `python3 -B tools/test_platform_retirement.py` and the affected shell/file suites sequentially. Follow the [retirement checks](../../docs/testing.md#retired-environment-and-platform-file-ids); never use live receipts as fixtures.

For wiki changes, follow [the wiki guide](wiki.md) and run its isolated generation/Git suites sequentially. Use `dots wiki check --source-only` for source-only CI; never publish or fetch live repositories as a test.


For detailed startup/PATH recording, run `python3 -B tools/test_debug_tracing.py` and the affected suites in the debugging section of the testing reference. Use owned native shells and temporary record files; never activate a recorder in the developer shell. Preserve interval/coverage distinctions, selected-value redaction and terminal/data-output checks.

For keybinding browser changes, run `tools/test_keys.py`, `tools/test_tmux_keys.py` and `tools/test_keys_zle.py` sequentially with Python. Use caller-owned native maps, public plugin copies and private tmux sockets. Keep configured/live coverage separate and never inspect by starting personal app profiles. Follow [keybinding verification](../../docs/testing.md#keybinding-browser-and-tmux-reference).


For project/session menu actions, also run `python3 -B tools/test_menu_projects.py`
and the session, launcher, shared-selector and affected key/file/theme picker
suites sequentially. Use owned project/config roots and private tmux sockets;
mock Android service launches. Never test deletion against a live user session.
See [menu tests](../../docs/testing.md#shared-menu-support).

For less style changes, run `python3 -B tools/test_less_style.py` and affected shell-environment, shell-init, menu-pager and theme snapshot publication cases. Keep PTYs and HOME/XDG roots test-owned; do not reload a live shell or tmux server for validation. See [global less checks](../../docs/testing.md#global-less-style-checks).

For Blastoff/pkgs absorption, run `python3 -B tools/test_bundled_apps.py -v`, the metadata generator with `--check`, and the affected dispatcher/native/installation suites sequentially. Keep original application release/installer evidence separate from combined Dots lifecycle checks; see [bundled verification](../../docs/testing.md#bundled-applications).

Application relocation and migration use `tools/test_bundled_apps.py` and `tools/test_app_migration.py`; synthetic legacy roots must never inherit the host Termux prefix. Keep core application checks and shared menu/native checks alongside them. See [application plugins](../../docs/plugins.md).

For Codex attention hooks, queue or activation changes, follow the [notification maintenance guide](codex-notifications.md), run `python3 -B tools/test_codex_alerts.py -v` and the existing Codex/status regressions, and validate setup/undo with the file-platform checks. Mock Android calls, use private sockets and all-owned HOME/CODEX_HOME/XDG roots, and keep real hook trust/device acceptance separate.
