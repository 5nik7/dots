# Testing Strategy

**Status: Implemented focused suites; native evidence and remaining platform checks recorded per feature**

Run checks appropriate to the changed files from the existing checkout, using test-owned home, config, state and cache roots. Documentation changes require `python3 -B tools/verify_docs.py` and `git diff --check`.

Testing must prove that `dots` protects user data, resolves specifications deterministically, behaves consistently across adapters, and remains fast on representative machines.

## Shared shell utilities

Run `python3 -B tools/test_common.py` for sourceable `bin/lib/common.sh` behavior in disposable Bash/Zsh homes. The suite covers literal PATH membership, idempotence, empty PATH, multiple source arguments, source status and side effects, running-shell module lookup, broken links, mkdir refusal/failure, single command execution, filename/dirname oracles, optional eza, raw data, case conversion, message policy and stubbed package queries. It also covers quiet loading, exact/repeated global array construction, independence from retired color globals, dirout policy for the shell helper and standalone script (including symlinked invocation and missing-renderer fallback), formatting, and spinner status, interruption, cleanup and trap preservation. It never reads the live package database. Missing interpreters are explicit skips. Also run shell syntax checks, `shellcheck -x bin/lib/common.sh`, the shell-init/dispatcher/Zsh suites below and the isolated Zsh PTY runner.

Use `python3 -B tools/bench_common.py --before /path/to/saved-helper.sh --samples 5 --iterations 100` to compare a saved pre-change source with current helpers; omit `--before` for current-only measurements. The saved helper must provide the utility API used by the benchmark; the pre-consolidation utility snapshot is also supported. The runner copies each source into owned runtime roots and retains source hashes, platform identity and every sample in the printed temporary directory. Warm batches measure utility loading, PATH membership, directory formatting, case conversion and single-file sourcing, including shell process startup. Run sequentially without other tests or builds. These are advisory microbenchmarks, not full startup or desktop-platform claims. Results and integration limits for the current change are recorded in [the common-helper plan](../plans/common-helpers.md).

## Shell initialization

Run `python -B tools/bench_powershell_profile.py` for one initial and ten warm fresh-process samples of the isolated lean profile and `-NoProfile`. Set `DOTS_TEST_POWERSHELL` to `pwsh` or `powershell` for either engine. Results include profile load, first prompt and process wall time. `--starship --integration /path/to/shell-integration_v7.ps1` additionally runs installed Starship against a synthetic configuration and a copied integration script; job discovery is stubbed, caches remain temporary, and no personal theme commands run. The baseline excludes PSReadLine; the Starship scenario includes its module initialization but uses redirected input, not keyboard/desktop rendering. Run sequentially, outside other tests/builds. Native terminal checks and the current evidence are recorded in the [profile plan](../plans/powershell-profile.md).

The shell-init suites also verify direct and linked startup, relative/absolute/chained links, symlinked parent directories, relocation, stale inherited checkout variables, working-directory preservation, and missing or cyclic links in test-owned roots. The native PowerShell runner includes capability-gated link tests; missing runtimes and unavailable link privileges are reported as skips.

Run `python3 -B tools/test_shell_init.py` for native emission/evaluation, literal quoting, common defaults, overrides, repeat initialization, nested shells, optional tools and native metadata. All runtime roots are disposable; private modules are synthetic, and no live startup files are sourced. The Xonsh interactive fixture uses a PTY and readline. Missing interpreters are explicit skips. Environment fixtures verify repeat initialization adds only the existing repository binary/script directories and does not insert the retired repository-local binary directory. Use `python3 -B tools/test_powershell_init.py` for native PowerShell acceptance, including on Windows without Bash or POSIX PTYs. It owns all runtime paths, parses the native sources, and evaluates both noninteractive initialization and the lean interactive body with redirected input. It checks repeated startup, prompt exit status, absent optional dependencies, generated-code failure, literal-path helper behavior and cleanup. It does not load personal modules or live profiles. Native Windows evidence remains separate from Unix or emitted-text checks.

The shared `tools/public_fixture.py` copier rebases repository symlinks into fixture roots and rejects external targets before copying. Run `python3 -B tools/test_public_fixture.py` for write-through isolation regressions.

Also run `python3 -B tools/test_bash_dots.py`, `python3 -B tools/test_zsh.py`, `python3 -B tools/zsh_interactive.py --samples 3`, shell syntax checks and ShellCheck. Existing theme checks cover preserved shell/theme behavior. Measure startup sequentially with `tools/zsh_fixture.py` against a retained public source snapshot, and initialization generation with `tools/bench_bash_dots.py`. Known baseline failures and measured results belong in the [focused plan](../plans/shell-init.md).

Gum automatic loading is covered by the shell-init and theme/workflow suites: interactive Bash/Zsh startup and reload, child exports, XDG paths with spaces/Unicode, HOME fallback, optional missing files, noninteractive exclusion and Zsh generation refresh. Publication and generated theme initialization continue to leave shell overrides unexecuted. Fixtures own all state roots; do not source live user startup or activate a live theme for these checks.

Run `python3 -B tools/test_shared_shells.py` for shared command, fallback, cancellation, reload and Bash prompt/theme contracts. `python3 -B tools/bash_interactive.py` exercises actual Bash prompt status, FZF Ctrl-R, Readline vi cursor transitions, Tab completion and reload stability with native tools in a disposable public fixture. The Bash fixture disables Atuin sync/update checks and substitutes private modules; it does not install tools or initialize real configuration. `tools/bash_fixture.py` provides the reusable public fixture. Retain the existing Zsh PTY runner for ZLE/FZF-tab acceptance. Use `python3 -B tools/bench_shared_shells.py --baseline /path/to/public-snapshot --samples 5` for sequential, alternating startup measurements against a retained public source tree. The baseline must include the public Bash and Zsh trees and their library/template dependencies; do not provide private snapshots. Evidence and startup comparisons are recorded in the [shared-shell plan](../plans/shared-shells.md).

## Tmux status and named sessions

Run `python3 -B tools/test_android_status.py` for the Android-cluster boundary: Wi-Fi/data precedence, strict connectivity fields and a neutral muted unknown-network fallback, equal network widths, disabled-helper nonexecution, theme signal colors, unknown/stale states, quoting, suppressed stderr, unsafe/oversized/invalid output, concurrent deadlines and helper-descendant cleanup. Its integration case copies the real scripts and library, overriding only the copied provider-command boundary to test cache freshness, cold reads, permission gates, Wi-Fi/device failure suspension, expiry and explicit successful recovery. Unknown Wi-Fi is tested against active/inactive/unknown data; stale negative decisions stay visible, and device freshness remains independent of registered-cell signal. This also intercepts location's absolute `/system/bin/settings` path; PATH mocks alone are insufficient. All caches and provider processes are test-owned, and no Android permission API is accessed.

The tmux status suite renders the battery and daylight clock with stubbed helpers at 40/80/120 columns, including stable battery placement, day/night/unknown clock colors, bounded failures, repeated reloads, focused overflowing session lists, theme/config reloads and missing Python. Network helpers remain independently covered by the adapter suite above, while the shipped bar asserts zero calls to those helpers. Run `python3 -B androidots/tests/test_termux_status.py`, `python3 -B androidots/tests/test_termux_sessions.py`, and `python3 -B androidots/tests/test_termux_bar.py` for Androidots regressions. Theme/workflow publication tests preserve layout ownership and publish upper/lower/inactive/current and daylight semantic colors. Androidots tests additionally cover read-only volume commands, stream selection, rounding, cache validation, stale/failure recovery and completion candidates.

Run `python3 -B tools/test_tmux_status.py` for battery-to-tmux color translation and the Termux session adapter. Fixtures cover one JSON query per shared before/after job, joined current-number/project badges, exact per-segment padding, case-sensitive full-name window shortening, hidden default names, literal Unicode/format punctuation, creation order, per-client highlighting, unmatched clients, session removal, malformed/unsafe data, missing tools and timeout clearing. Native checks use disposable servers and an outer tmux terminal to capture the actual rendered inner status rows at 40, 80 and 120 columns. They verify the Termux two-row/non-Termux one-row layouts, two independent clients, overflow around the current entry, clock/battery placement, both row colors and resets, bounded number strips and long project badges, window mouse targets, no current-window underline, legacy-theme overrides, idempotent reloads, and theme-only refreshes. Deterministic platform `strftime` checks cover midnight, morning, noon and evening; native rendering separately checks the current time. All homes, config paths, source-script stubs and sockets are test-owned. They never query real Termux sessions or reload the live server.

Optionally run `DOTS_TEST_BATTERY_SOURCE="$HOME/repos/battery/battery" python3 -B tools/test_tmux_status.py` to copy that upstream script into the fixture and verify configured threshold boundaries and charging icons against a fake `termux-battery-status`. This opt-in reads source only; the test owns its battery configuration and Termux `PREFIX` as well as `PATH`, and mocks every API request. Adapter subprocess groups are terminated on timeout. Without the variable this integration is an explicit skip. No Android API call is made by tests.

`python3 -B tools/test_shared_shells.py` covers `t` in Bash/Zsh with stubbed tmux: exact default/custom names, inside/outside behavior, concurrent creation, failure propagation, invalid arguments and legacy-alias reload. `python3 -B tools/test_tmux_sessions.py` adds native Bash/Zsh PTY clients on a private socket, checking exact names against prefix collisions, create/attach/switch/reuse, spaces/Unicode/leading dashes, working directories and no nested clients. Repository-default coverage uses owned Git repositories and linked worktrees to verify root/nested invocation, inferred-name normalization, explicit overrides and root working directories; stubbed tests also cover missing Git and non-repository fallback. Also run the existing shell-init/shared-utility/dispatcher/Zsh suites, Bash/Zsh PTY runners, theme/workflow suites, `bash -n config/tmux/battery-status.sh`, shared-shell syntax checks and ShellCheck. Theme connector tests assert publication preserves user status layout. Native font appearance and live reload remain manual; no desktop or Windows acceptance is implied. See the [focused plan](../plans/tmux-status-and-sessions.md) for results and baseline limitations.

## Operation progress

Run `python3 -B tools/test_progress.py` for isolated native Unix PTY coverage of Bash/Python progress. The suite owns home/config/state/cache roots and checks delayed/fast work, counted phases, nested rendering, output modes, color/icon policy, 40/80/120 columns, control-character labels, prompt suspension, child exit status, interruption, renderer failure and worker cleanup. Disposable file transactions verify progress during real apply and injected rollback; controller tests prohibit animation for JSON/dry-run paths. PTY tests require Bash and Python; Gum is unnecessary.

Run the existing Bash, Git, files, browser, theme, picker, confirmation and isolated Anodize suites for integrations. Keep sequential Git/file benchmark intervals separate from tests. Native Termux PTY results do not establish native Windows, Linux or WSL acceptance. See [the focused plan](../plans/progress.md) for actual results and pre-existing suite failures.

## Yazi Plugin Bundle

From the standalone `dots.yazi` source checkout, run `lua test.lua`, `lua test-preview.lua`, `lua test-githead.lua`, `lua test-hover.lua`, `lua test-ls-colors.lua`, `python3 -B test-ls-colors.py`, `python3 -B test-native.py`, and `python3 -B test-preview-native.py`. Python runners belong to the source repository, not the installed package. Both native runners accept `--config-dir /path/to/dots/config/yazi` to validate a copied personal configuration. The Lua fixtures check dispatcher forwarding, setup order, pane restoration, combined Git refresh/stale-result rejection, remote metadata validation and helper failure fallbacks, independent ownership/branch colors and command-free redraws, hover layout, independent style sources/overrides/visibility, configuration precedence, independently colored target directory/basename spans with preserved fitting, and style isolation, and LS_COLORS parsing/matching/reset/fallback behavior. The GNU ls oracle runner compares disposable filesystem fixtures; unavailable native hard links are explicitly skipped while Lua metadata fixtures cover that branch. The native Unix PTY runner copies the repository's Yazi config into temporary home/config/state/cache/data/runtime roots, isolates the DDS socket directory and Git configuration, and installs only the combined plugin plus a test probe. It requires Python, Git, git-it, and Yazi. The copied live hover configuration is exercised directly, so hardcoded color overrides cannot mask a configuration regression. Additional temporary getter checks verify native override/reset semantics and disabled-color fallback before restoring that getter. It exercises Git callbacks/fetching, local remote host/ownership fixtures through installed git-it (GitHub, GitLab, Bitbucket, unknown hosts, no remote, aliases and nested owner namespaces), distinct module state, project save/load/last/delete/delete-all and merge event dispatch, folder sorting, pane shortcuts, ANSI/indexed/RGB style values, separate symlink/target header styles, unchanged symlink listing colors, reset-background preview spacing, filled cursor caps, native-style fallback, icon inheritance/overrides, directory-prefix styling, and 40/80/160-column redraws.

Preview acceptance covers platform/list overrides, renderer fallbacks/deadlines/output limits, literal arguments, image caching, Alt+m, per-tab identity/reordering/closure, stale-result rejection, scrolling and 40/80/120-column resize behavior. Preview tests own an explicit image cache as well as HOME/XDG/TMPDIR/DDS roots. mdcat, Bat and Chafa run natively; Glow/Rich use command fixtures when unavailable. The package and live-theme regressions remain in the standalone testing guide. After a package upgrade, run `python3 -B tools/check_yazi_bundle.py --source /path/to/dots.yazi`.

Native verification covers Termux with Yazi 26.9.1. Windows paths in Lua fixtures are simulated; no native Windows or desktop Linux claim follows. Redraw checks catch runtime errors but do not prove pixel-perfect visual equivalence. See the [plugin README](../config/yazi/plugins/dots.yazi/README.md#verification) and [focused plan](../plans/yazi-plugin-consolidation.md) for evidence and boundaries. The [remote metadata plan](../plans/yazi-githead-remote.md) records the optional helper integration.

## Bash Command Framework

Run `python3 -B tools/test_bash_dots.py` for disposable routing/metadata/output and
native Bash/Zsh/Fish completion tests. All three shells are required; missing
interpreters must be installed by the owner, not silently skipped. The suite
includes real controlling-terminal Tab presses and live command additions.
`tools/bash_dots_pty.py` provides the owned-terminal helper. Use
`shellcheck bin/dots lib/dots/*.bash lib/dots/completion/bash` plus `bash -n`,
`zsh -dfn`, and `fish --no-config -n` for the corresponding sources.

`python3 -B tools/bench_bash_dots.py --samples 20` measures help, directory lookup,
dispatch, discovery, completion, and adapter registration in owned roots. Catalog
sizes are 0/100/1,000 additional commands plus one dispatch probe. It keeps raw
samples in the printed temporary directory. Run timing sequentially, without other
tests competing for the device. These advisory measurements are not CI/native
coverage for other platforms. Also run `python3 -B tools/test_zsh.py` and
`python3 -B tools/zsh_interactive.py --samples 3` when changing integration; the
latter exercises dots completion with the copied public FZF-tab setup, including
aligned command/option labels alongside descriptions and literal insertion.

## Tmux keybinding reference

Run `python3 -B tools/test_tmux_keys.py`, `python3 -B tools/test_bash_dots.py`, `bash -n bin/dots-menu-tmux-keys lib/dots/tmux-keys.bash`, and `shellcheck -x bin/dots-menu-tmux-keys lib/dots/tmux-keys.bash`. The focused suite copies the public dispatcher/helpers and viewer into owned roots, uses fake tmux/less tools for deterministic failure and presentation cases, and checks both command spellings, static help, metadata, and all three completion protocols. Fixtures cover notes-only grouping, prefixes, quoting, Unicode/control safety, malformed output, missing tools, pager errors/interruption, early exit, redirected output, forced/disabled color, `NO_COLOR`, and `TERM=dumb`.

PTY captures check compact inline key/description rows at 40/50/80/120 columns, including the prefix legend and long-key preservation; C/C.UTF-8 fixtures cover arrows, emoji, combining characters and C1 controls. When installed, native tmux uses a disposable socket, config, home and session to validate formatted records, session prefixes, the repository popup binding and emitted blue-border/cyan-title colors, its test-owned working directory, and return to tmux after `q`; native less verifies short-list persistence and search/exit input on a controlling terminal. Cleanup kills only test-owned clients/servers. No live config is loaded or server altered. Missing native tools are reported as skips, not coverage. Preserve Termux's inherited `LD_PRELOAD` when invoking the runner through a sanitized environment.

Termux verification used tmux 3.7c; native Linux/WSL and graphical visual review are not established by these PTYs. JSON, mutations, rollback, previews and recovery are not applicable to this read-only human view. See the [focused plan](../plans/tmux-keys.md) for scoped evidence.

## Existing Zsh Configuration

`python3 -B tools/test_zsh.py` checks the shell configuration in owned temporary roots. `python3 -B tools/zsh_fixture.py --samples 10` measures isolated startup; `python3 -B tools/zsh_interactive.py --samples 5` exercises native PTY interaction, reloads, and input-ready timing using copied public plugins and synthetic private modules. No dependencies are installed and fixture Git refuses remote operations. The [Zsh guide](../shells/zsh/README.md) specifies prerequisites and evidence limits; the [focused plan](../plans/zsh-startup.md) records results.

Default-engine Deja acceptance uses `python3 -B tools/test_deja.py --binary /path/to/deja --plugin /path/to/deja.plugin.zsh`. It requires the same public plugins plus explicitly supplied, reviewed Deja inputs, copies them into owned roots, leaves the selector unset to test default activation, seeds synthetic history, and owns/stops its daemon. General Zsh timing/PTY fixtures explicitly select autosuggestions so they do not require a Deja binary. It checks real right-arrow acceptance, vi transitions, Tab completion, highlighting configuration, reload stability, and sequential warm engine timings. The ordinary Zsh suite tests selector defaults, fallbacks, load failures and overrides without Deja. Preserve Termux's `LD_PRELOAD` when invoking these runners. See the [trial evidence](../plans/deja-trial.md); these checks do not establish other native platforms or visual palette accuracy.

## Yazi Symlink Component

From `config/yazi/plugins/dots-symlink.yazi`, run `lua test.lua` for isolated layout checks. The fixtures cover changing width budgets, whole-directory shortening, independent caps, colors, root separators, empty directories, and simulated Windows paths. The Lua text adapter approximates terminal widths; it does not establish native rendering or Windows support. See the [plugin guide](../config/yazi/plugins/dots.yazi/README.md).

## Documentation Verification

Run `python3 -B tools/verify_docs.py` for relative links and `python3 -B tools/test_verify_docs.py` for checker regressions. The checker uses only Python and works in parent-only checkouts without optional submodules. It covers README, AGENTS, guides, docs and plans.

Documentation changes require:

- `git diff --check`.
- Relative Markdown link validation.
- Search for stale proposed/implemented status labels.
- Search for renamed commands and paths.
- Confirmation that README examples only show implemented safe behavior.

Once command metadata generation exists, CI should regenerate output and fail on a dirty diff.

## Platform Evidence

For manual checks that CI cannot reproduce, record:

- Date.
- Platform and version.
- Architecture.
- Filesystem location/type.
- CLI revision and build mode.
- Command or test case.
- Result and observed limitation.

Do not upgrade a support-matrix status based on an undocumented one-off success.

## Development Worktree Lifecycle Tests

`python3 -B tools/test_worktree_lifecycle.py` runs isolated development-helper tests without package changes, network requests or live-home mutations. It covers eligible removal, preview/fetch refusal, staged/modified/untracked/ignored/empty local content, unmerged and freshly merged heads, registration/identity/capacity, active/uncertain use, original/session/helper/live paths and Git refusal. Portable removal tests inject an idle process snapshot; native Unix tests check a disposable live child and eligible removal when process inspection is available. Native Windows process inspection/removal is deferred and fails closed; Windows symlink privilege is never enabled for tests. The development-tooling CI workflow runs this suite and documentation/whitespace checks; existing native CLI gates are unchanged. See [the lifecycle guide](../agents/guides/worktrees.md) for optional use, metadata and deliberate cleanup triggers.

Lifecycle review regressions verify preview/apply retain native FIFO and filesystem socket fixtures where supported, and that a fresh remote-main fetch ignores an additional configured recovery-branch mapping while preserving every local branch. Device/unknown modes and metadata denial use injected `lstat` results; they do not establish native device-node coverage. Native Windows FIFO/socket fixtures are unavailable and skipped. Positive portable removal still injects an idle process snapshot; native process coverage remains separate.

## Shared Themes

The shared-theme suite also verifies current-theme Bash/Zsh color arrays against resolved colors, derived RGB/ANSI/metrics, native extras, generic and pywal palettes, fixed-flavor compatibility, stale-name cleanup and reserved-name publication refusal.

Run `python3 -B tools/test_themes.py` for palette validation, all-flavor legacy
initialization compatibility, cache invalidation, command/completion contracts,
publication idempotence, lock contention, injected durability failures, SIGKILL
recovery, drift refusal, Zsh prompt refresh, and Neovim focus integration. All
mutable roots and executed official commands are copied into disposable fixtures.
The Neovim tests copy the local Anodize.nvim public runtime from
`ANODIZE_NVIM_DIR` or `~/repos/Anodize.nvim`; absent sources report a skip.
They never run live LazyVim startup or download dependencies. Coverage includes
all 17 native variants, generic themes, raw compatibility helpers, light/dark,
focus/manual reload, invalid-update retention and manual colorscheme gating.
Native family plugins are not required by these editor fixtures.
The committed legacy digest
was captured from the previous script's ordered 4 × 26 × 15 initialization values;
it detects numeric rounding and ANSI-byte changes as well as palette drift.

Run `python3 -B tools/bench_themes.py --samples 10` for isolated cold/warm
initialization for Catppuccin/TokyoNight, unchanged Zsh prompt checks and minimal
Neovim startup (Anodize standalone and the shared Dots startup bridge). An optional
`--baseline-script /path/to/preserved/catppuccin` compares the former implementation
in a separate owned cache. Measurements are sequential, retained in a temporary
JSON artifact, and do not establish full LazyVim startup performance.

This change also requires the Bash dispatcher suite, Zsh suite, real Zsh/FZF-tab
PTY acceptance, Bash/Zsh syntax checks, ShellCheck, StyLua, and documentation links.
Native Termux tests do not establish WSL/Linux/MSYS/Windows execution or power-loss
recovery guarantees.

### Shared discovery refactor

The [shared discovery plan](../plans/theme-discovery.md) records the behavior-preserving extraction into `lib/dots/themes/discovery.bash`. `tools/test_themes.py` includes inert-source, current/native-ID parity, cleared-result, alternate checkout root and bundled/user discovery fixtures. Tests retain the distinction between validated/deduplicated listing and literal completion hints, including invalid and duplicate names, symlink/broken palettes and next-request freshness across Bash/Zsh/Fish. Workflow inventory/count checks derive their expectations from fixture data rather than a hardcoded theme count; the accent assertion compares the source palette. Native Termux verification, benchmark evidence and pre-existing Neovim deadline/Markdown-link limitations are recorded in the plan. No test runner or platform claim is added.

## Unified Theme CLI

The [migration plan](../plans/theme-cli.md) and [decision 0012](decisions/0012-unified-theme-cli.md) consolidate the live interface under `dots theme`. `python3 -B tools/test_themes.py` now checks removed plural routes, full-ID validation, native family/flavor discovery, semantic/native color collisions, undecorated scalar values, generic palettes, contextual completion, and preserved helper APIs alongside the existing state/recovery and editor tests. No live theme is selected by verification.

On native Termux Android/ARM64, 2026-09-29, the unified theme suite passed 27 tests, Bash dispatcher 23, theme picker 14, local theme plugins 20, file operations 21, Anodize Neovim bridge 5, and Anodize completion/manual integration 4. `tools/verify_anodize.py check` passed Go tests/vet and all 17 CLI integration tests. Shell initialization passed 17 tests with two PowerShell cases skipped. Targeted tests also passed after final color-name validation and silent `has_theme` error handling adjustments.

Changed palette views were exercised and reviewed in native PTYs at 40/80/120 columns. Tests cover forced/disabled/automatic color, `NO_COLOR`, `TERM=dumb`, native color formats, and redirected values. Bash/Zsh/Fish dispatcher Tab tests passed. Syntax, targeted StyLua, focused ShellCheck with existing core diagnostic exclusions, and diff whitespace checks passed. Native desktop and Windows behavior was not verified.

The workflow suite passed 12/14 with its two pre-existing 33-versus-34 theme-count assertions. Zsh passed 15/17 with its two pre-existing alias expectations. The broader Zsh/FZF-tab PTY run reached the completion/history checks but failed its diagnostic gate because reload invokes missing `box`; the saved pre-migration source reproduces that failure. The repository-wide Markdown gate still fails the pre-existing `docs/testing.md` link to the removed `config/yazi/plugins/dots-symlink.yazi/README.md`; the full relative-link audit found no newly broken links. These failures were retained rather than weakening acceptance or changing unrelated behavior.

`tools/bench_themes.py --samples 3` completed before and after the migration, sequentially in owned roots. All later timings, including unchanged editor/helper controls, were slower, so these snapshots do not establish a regression attributable to this change. A follow-up alternating comparison of the original plural init parser and unified init against one fixture generation and the current shared engine measured 29.24 ms versus 30.86 ms warm medians over 20 samples each. The observed difference was approximately 1.62 ms; no scanning or subprocess was added to the unchanged prompt path. Measurements are advisory mobile-device evidence, not a cross-platform performance guarantee.

## Files Catalog and Omarchy-Style Themes

Run the focused suites from the parent checkout:

```bash
python3 -B tools/test_files.py
python3 -B tools/test_theme_workflow.py
python3 -B tools/test_themes.py
python3 -B tools/test_bash_dots.py
```

The file suite covers read-only observation, unavailable sources, exact/nested
ownership conflicts, broken links, metadata round trips/idempotence/refusal,
static help/completion and journaled config-link migration/rollback/drift. Fixtures
include spaces, Unicode, leading-dash filenames and missing target parents.
The workflow suite covers all 33 flat selections, personal template precedence,
failed-render atomicity, generic Neovim highlights, semantic cache invalidation,
connector backup/recovery, all application connector paths, native tmux relative
include loading through an owned socket, staged-link interruption, local Git install/update/remove,
dirty refusal and data nonexecution. Theme fixtures explicitly isolate TMUX_TMPDIR;
the native tmux test starts and stops only its own server. Android, Wayland and X11 wallpaper adapters are
fake executables: their argument/failure contracts are tested, not actual rendering.

`python3 -B tools/test_file_themes.py` covers generated Vivid/FSH connectors,
backup/rollback, refusal, idempotence and override refresh; native Vivid colors
across dark/light/generic palettes; Zsh cache invalidation and fallback; and real
FSH highlighting, nested syntax, overlays and last-good session fallback. Native
FSH startup checks cover saved `njen` migration, compiled-code invalidation,
private backups (including symlinks), unchanged reloads, directory refusal and
injected replacement failure. A fresh plugin-only shell must load Dots and report
it on both `fast-theme --show` lines before any Dots hook. It uses
owned roots and a copied installed FSH plugin with network bootstrap disabled.
The public Zsh fixture excludes the live Vivid connector while retaining its refusal
of other links escaping the public repository. Native dependency checks skip when
unavailable. Run alongside the theme/workflow
and Zsh suites, plus the isolated Zsh startup and PTY runners for adapter changes.

The Vivid tests also use `tools/vivid_fixture.py` to enforce the older scalar-only
font-style grammar and exercise unknown-version compatibility. These fixtures
cover complete core/explicit-suffix attributes, modern combined categories,
custom-template refusal and unchanged publications. Installation tests cover
fresh FSH publication with legacy Vivid behavior, the captured compatibility
notice, plain JSON diagnostics under forced color, repeat setup and receipt
preservation after a template failure. Version-probe and absent-tool cases live
in `tools/test_file_colors.py`. Fixture evidence is separate from tests using an
installed Vivid binary and does not establish native WSL execution.

The workflow suite checks Codex's shared plist across bundled palettes, byte
identity with Yazi's syntax artifact, default/custom homes, absent directories,
control-character/path refusal, personal/bundled overrides, unchanged refresh,
connector backups, rollback, staged interruption and drift. Codex settings are
asserted unchanged. Native Codex picker checks must use a disposable home without
real credentials or model requests; an XML parse alone is not native loader proof.
The existing Neovim `tests/codex_colors.lua` probe uses `nvim -u NONE -i NONE`
and a test-owned PTY child rather than live LazyVim or Codex. See the
[Codex theme plan](../plans/codex-theme.md) for native loader evidence and limits.

The workflow suite also checks Pi JSON rendering, light/dark selection, custom agent
paths, optional absent directories, template/override refresh, connector backups,
rollback and directory refusal. Set `PI_THEME_MODULE` to an installed Pi package's
`dist/modes/interactive/theme/theme.js` to enable its optional native loader/hot-reload
test (requires Node). It imports only the theme module with a disposable agent directory;
it never starts live Pi or loads user settings/extensions. Without that path it reports
a skip. The completion regression reproduces a Nord → Latte prompt refresh and verifies
that Zsh/fzf-tab's `list-colors` style follows `LS_COLORS`, preserving exit status and
literal values. Run the existing Zsh PTY suite for interactive plugin acceptance.

On native Termux, 2026-09-23, these suites passed 7 + 10 + 23 + 22 tests (62 total).
All native-family Neovim fixture cases ran using available public plugin sources.
ShellCheck, targeted StyLua, Bash syntax, route metadata, relative Markdown links
and parent/child `git diff --check` passed. No live theme, wallpaper, editor startup,
plugin installation or remote theme download was used for verification.

The separate `tools/test_zsh.py` suite passed 15/17. Its two `ll == 'ls -la'`
expectations fail identically against an exported HEAD baseline: the unchanged
alias source only defines `ll` in its eza branch. This pre-existing discrepancy is
retained rather than changing unrelated shell behavior in this task. Isolated PTY
acceptance passed reload equality (hooks, fzf options, fpath and keys), Tab/FZF-tab,
directory completion and history picker checks. Its first timing interval overlapped
a separate test, so those PTY timings are not used as performance evidence below.
Native desktop application reload/rendering, WSL and native Windows remain unverified.

On 2026-09-28, the FZF/Hilbish template follow-up passed all 23 shared-theme tests
and 23 Bash dispatcher tests. The expanded workflow suite passed 12/14, including
three new tests for published FZF colors in Bash/Zsh/Fish, idempotent reload,
personal/bundled overrides, fingerprint refresh, malformed/injected FZF input
refusal, and Gum Lua rendering without publication-time execution. Its two
failures still expect 33 themes while the current catalog contains 34. Zsh passed
15/17 with the two alias expectations described above. All four failures were
reproduced against original HEAD code in disposable fixtures.

Installed FZF 0.74.4 accepted the generated color list, and Gum 2.0.0 rendered the
expected colors using assignments captured through a Lua `os.setenv` test double.
All 116 Gum mappings were preserved. Hilbish is unavailable locally: this verifies
Lua syntax/assignments and Gum rendering, not native Hilbish execution. Shell
syntax checks, focused ShellCheck (with existing core diagnostic exclusions),
relative documentation links and whitespace checks passed. Isolated Zsh startup
and PTY checks passed, including equal hooks/FZF options/fpath/keys after reload,
Tab/FZF-tab, directory completion and history selection. No live theme was activated.

The subsequent Gum shell conversion on 2026-09-28 passed all three focused
application-environment workflow checks on native Termux. The full workflow suite
passed 12/14, with the same two existing 33-versus-34 theme-count failures noted
above. All 23 shared-theme tests passed. Bash and Zsh both
exported all 116 colors to a child process, tolerated repeat sourcing, and loaded
the new accent after a theme change. Personal and bundled shell overrides retained
precedence and fingerprint refresh while remaining unexecuted during publication.
An exact comparison against the previous Lua template preserved every mapping in
order. Bash/Zsh syntax, relative Markdown links and whitespace checks passed.
This evidence covers explicit shell consumption in disposable roots; no live
shell configuration or active theme was changed, and desktop/Windows execution
was not tested.

Sequential three-sample advisory theme measurements recorded selected Catppuccin
initialization at 19.1 ms before and 23.2 ms after, and the unchanged prompt check
at 36.6 µs before and 44.1 µs after; the unchanged prompt path still adds no new
process or template reads. These small, noisy samples establish no speedup or
controlled regression claim. The final isolated Zsh startup median was 871 ms
(three samples), and PTY input readiness was 1.436 s (two samples). Temporary
evidence directories are `dots-theme-bench-kzvh8gfx` (baseline),
`dots-theme-bench-1ed12yt9` (after), `dots-zsh-re6ezv4b` (startup), and
`dots-zsh-n3r9kdfe` (PTY), under the Termux temporary directory.

For sequential advisory measurements:

```bash
python3 -B tools/bench_files.py --samples 5
python3 -B tools/bench_themes.py --samples 10
python3 -B tools/bench_bash_dots.py --samples 10
python3 -B tools/zsh_fixture.py --samples 5
```

The 2026-09-23 Termux theme comparison used exported parent/Neovim HEAD source in
owned roots, then current source with the same fixture and installed public plugins.
Theme measurements use 10 warm samples; prompt cost is averaged over 10,000 calls.

| Operation | Before | After |
| --- | ---: | ---: |
| Cached Catppuccin initialization | 27.5 ms | 31.5 ms |
| Published initialization | 19.2 ms | 20.3 ms |
| Unchanged Zsh theme prompt check | 0.041 ms | 0.038 ms |
| Minimal Neovim with shared startup | 35.7 ms | 35.8 ms |
| Unpublished TokyoNight initialization | 39.3 ms | 49.8 ms |

The unpublished paths now validate semantic data and fingerprint templates as well
as native palettes. Batched hashing removed an intermediate 200–247 ms regression;
published snapshots avoid this work during normal startup. These are small fixture
measurements, not full LazyVim startup or guarantees for another device.

File JSON inventory medians were 107 ms / 308 ms / 2,220 ms for 100 / 1,000 / 10,000
records (five warm samples, Linux observation targets on a native Termux host).
No persistent catalog cache is added. Direct Bash dispatch was 18.7 / 22.5 / 19.9 ms
with 0 / 100 / 1,000 additional commands; narrow-prefix completion was 17.9 / 19.3 /
18.9 ms. Full discovery scales with command count; shell adapter registration added
approximately 0.4–0.6 ms in these fixtures. Timing intervals were sequential.

Raw benchmark JSON is retained outside Git under
`~/.local/state/dots/verification/config-themes-20260923/` on the implementation host.
The config migration separately retains its home-link rollback journal and original
repository-link text under `~/.local/state/dots/migrations/`. The 14 migrated live
links were checked against their recorded targets; all 897 old config paths still
have corresponding objects in `config/`. No managed install/undo acceptance is implied.

Full public Zsh fixture startup was also compared sequentially (five warm samples):
830 ms before versus 843 ms after, with noninteractive startup 9.4 ms versus 8.8 ms.
Application-cache cold startup was 3.56 s versus 3.14 s. The warm difference is about
1.6%; these samples do not establish a general speedup. Raw before/after JSON is
in the same retained verification directory.

## Terminal Presentation

The [presentation acceptance gate](presentation.md#acceptance-gate) applies to all new or changed first-party human views. The evidence below covers the initial implementation only. Future changes must add applicable missing state, stream, layout and renderer-parity cases, including visual review at 40, 80 and 120 columns. Record automated checks separately from visual review, and native results separately from simulated platform fixtures. Do not infer complete cross-command or desktop coverage from these Termux results.

The existing file, theme workflow and Bash suites cover presentation in disposable
roots: colored/undecorated terminal output, NO_COLOR and TERM=dumb through an actual
PTY, forced color/icons, narrow file views, empty results, theme swatches, active
selection markers, dry-run output, and static executable-group menus. They verify
plain piped listings, JSON, path/scalar queries, shell initialization and completion
under forced decoration. Hidden child commands remain hidden and help never runs
extensions. Use the existing `tools/test_files.py`, `tools/test_theme_workflow.py`
and `tools/test_bash_dots.py` runners; no live theme activation is needed.

On native Termux, 2026-09-24, presentation validation passed 9 file tests, 11 theme
workflow tests, 23 Bash framework tests and 23 theme compatibility tests (66 total).
ShellCheck, relative Markdown links and `git diff --check` also passed.

## Git and Managed File Operations

Run `python3 -B tools/test_git_submodules.py` for both entry paths: isolated
info/tree/status fixtures, depth/dirty semantics, redacted URLs, completion and
publication selection boundaries. Local bare remotes and the fixture-only SSH
transport exercise child-first publication and safe sibling continuation while
asserting excluded parent index/HEAD/remote preservation. No live repository is
published. Run `tools/test_git_operations.py`, `tools/test_native_git.py`,
`tools/test_git_styles.py`, dispatcher/native CLI and progress/resource suites
sequentially for regressions. Native Windows PowerShell engines and real terminal
acceptance remain separate gates; fixture SSH publication requires Bash locally.

Run `python3 -B tools/test_git_operations.py` and
`python3 -B tools/test_file_operations.py`. Both use disposable owned roots.

`python3 -B tools/test_files_check.py` covers catalog-only absent-source cleanup:
selection/cancellation, dry-run/JSON, filters, preserved targets and broken source
links, strict absence/error handling, drift, multi-catalog rollback, abrupt-exit
recovery, undo and owned 40/80/120-column PTYs. Catalog tests verify the new route
and Bash/Zsh/Fish completion; adapter tests cover native PowerShell when available.

`python3 -B tools/test_file_mappings.py` covers stash/restore, mapping edits/new
entries, disabled-state integration, backup/receipt continuity, drift, rollback,
abrupt-exit recovery, undo, cancellation and owned terminal widths. Its Git
migration fixtures validate common/alias/Android loading without a live home or
credential-helper execution. Run catalog, operations, installation, browser,
confirmation, progress, resource, dispatcher and adapter regressions sequentially.
Git fixtures use local bare remotes with test-only SSH transport; no network or
personal publication is required. File fixtures isolate HOME, config/state and
source repositories, including actual abrupt process exit after a replacement
rename followed by journal-driven recovery. The engine has no production test
failure switches.

Git checks include cached status, explicit roots and initialization, unusual
submodule paths, staged-only/all publication, preserved deliberate pointers,
child-first ordering, rejected pushes, independent siblings, pinned/remote sync,
local edits/divergence and unsafe topology. File checks cover discovery, verified
adoption, per-file/whole-directory links, removal, backup defaults/overrides,
restore, undo drift, copy/preview failures, interrupted recovery, idempotence,
credential exclusions and terminal/plain/JSON views.

Also run existing file inventory and Bash framework suites for shared metadata,
completion and rendering contracts; ShellCheck and shell syntax checks for Git
modules and route wrappers; documentation links and whitespace checks. Native
Termux results are distinct from simulated fixtures; no native Windows management
or desktop filesystem guarantees follow from these tests.

### Native Termux results (2026-09-25)

The new Git suite passed 25 tests and file-operation suite passed 18 tests. Existing
inventory (9) and Bash framework (23) suites also passed, for 75 tests. ShellCheck,
Python/shell syntax, static help/completion and relative documentation links were
checked separately. Tests include actual PTY preference/cancellation checks and
an abrupt file-operation process exit; no live config or remote publication was
performed. Native Linux/WSL and Windows operation validation was not run.

The subsequent system-discovery readability change passed 21 file-operation tests,
9 inventory tests and 23 Bash framework tests (53 total). New fixtures cover compact
directory grouping, verbose/all modes, complete JSON under forced decoration,
pruned cache/session/dependency/preview trees, preserved settings/custom assets,
scan eligibility, unchanged source/home trees, terminal controls and 40/80/120-column
layouts. Representative output was reviewed at those widths. This follow-up did
not change or rerun the Git engine suite.

The 2026-09-28 publication staging correction passed 27 Git, 8 confirmation and
23 Bash dispatcher tests on native Termux. The ignored-directory regression
failed before the fix and passed afterward: tracked edits/deletions remain
eligible while ignored new files stay untracked. A separate fixture verifies
literal special-character gitlink exclusions and preserves a staged pointer when
the child HEAD differs. All publication used disposable local remotes. A read-only
staging dry-run on the owner checkout passed, with unchanged index hash and HEAD;
no live publication was retried. Syntax, ShellCheck, docs links and whitespace
checks passed. See the [focused plan](../plans/git-and-file-operations.md#publish-staging-correction-2026-09-28).

`python3 -B tools/bench_git_operations.py` measures sequential warm status on
owned trees with 1, 5 and 10 repositories (three samples each). Median times before
removing repeated registration scans were 194.5, 1109.9 and 2678.9 ms; afterward
188.8, 991.8 and 2109.8 ms. Final samples in milliseconds: 194.1/185.0/188.8,
991.8/959.7/1218.8, and 1925.6/2118.5/2109.8. This is a small native timing sample,
not a cold-start or general performance guarantee. Status still performs real Git
inspection per repository; no persistent cache or startup scan was introduced.

## Anodize verification

`tools/anodize_build_support.py` owns the isolated offline build environment. Run `python3 -B tools/test_anodize_build_support.py` when changing it; the regressions cover owned paths, inherited-environment isolation, offline settings, telemetry configuration and missing prerequisites.

`python3 -B tools/test_anodize_logo.py` runs engine-free logo policy and native PTY checks in disposable roots, and is included in `python3 -B tools/verify_anodize.py check`. It covers narrow/wide/tiny layouts, destination sizing, usage/result/error and Bash/Python parity, exact width-fitted preview artwork through captured output (including panes below 12 rows), completion layout/icon options, metadata help without extension execution, optional-renderer failures, ASCII/color policies, Kitty transmission fixtures and data-output bypass. Integration tests cover logo completions and manual freshness; the engine suite checks unchanged raw exports/app configuration. The interactive suite checks native Zsh/FZF-tab artwork, preview scrolling and cancellation in short terminals with the configured FZF defaults; it requires a local FZF-tab plugin source. Kitty protocol fixtures do not establish native graphics rendering. See [branding verification](../plans/anodize-logo.md#verification).

Run `python3 -B tools/verify_anodize.py check` for an isolated offline Go build, package tests, vet and `tools/test_anodize.py` integration tests. `build` explicitly replaces the ignored private engine artifact; `bench` runs repeated engine benchmarks in temporary build/cache roots. The verifier retains Termux executable compatibility while isolating HOME/XDG/config/cache/temp roots. No network downloads or live publication occurs.

Coverage includes all 23 modes in light/dark, deterministic generation, bounded image decoding, repeatable adjustments, import/export round trips, receipt drift and collision refusal, retained undo, injected failure rollback, abrupt-exit recovery, template preflight, additive palette JSON, raw output, narrow/normal/wide presentation, static metadata and three-shell completion. Wallpaper tests use a fixture executable. Existing `test_themes.py`, `test_theme_workflow.py`, `test_file_operations.py`, `test_files.py`, and `test_bash_dots.py` verify shared boundaries. Android APK, TUI, desktop wallpaper tools and the separate plugin are not certified by this suite.

### Anodize baseline (2026-09-25)

Native Termux Android/arm64, installed Go 1.27.1, ordinary device load. Three Go benchmark repetitions: 32×32 PNG extraction 2.98–4.63 ms/op (~1.89 MB allocated/op); seed generation 0.268–0.290 ms/op (~30.7 KB/op); 1920×1080 synthetic PNG extraction 103.6–107.7 ms/op (~29.2 MB/op). These are in-process engine measurements, not app latency or peak memory claims.

CLI measurements include Bash/Python/engine process startup, with 20 samples after three warmups in isolated fixture roots:

| Read-only operation | Median | p95 |
| --- | ---: | ---: |
| Standalone help | 257.95 ms | 384.10 ms |
| Standalone modes | 269.11 ms | 286.54 ms |
| `dots anodize modes` | 229.41 ms | 318.80 ms |
| One-pixel image extraction | 294.94 ms | 335.75 ms |

Device load and process startup dominate these small commands. The different route samples are not a controlled route-speed comparison. No startup cache was introduced; ordinary Dots dispatch and shell startup never invoke the Anodize engine. Cold-cache, desktop, APK and editor integration timings remain unverified.

## Anodize Neovim integration

Run `python3 -B tools/test_anodize_nvim.py` for five focused Dots/editor cases.
The fixture copies only public runtime sources and selected Dots helpers, sets
isolated HOME/XDG/config/state/cache/data/runtime/log/temp roots, and starts Neovim
with `-u NONE -i NONE -n --noplugin`. It stubs the dashboard interface, not its
animation code. The Lazy-order test copies the installed public lazy.nvim Lua
source and enables plugin loading only after restricting runtime/package paths;
its two local specifications exercise early colorscheme loading without LazyVim
bootstrap. Process calls are rejected during that startup test.

Coverage includes missing-state/plugin fallback, active-only compatibility reload,
manual selection, opaque floats and transparent main windows, terminal opt-out,
Mocha overrides, inactive dimming, lualine layout and palette refresh, dashboard
elapsed-time continuity, hidden-window pause/resume, animation opt-out and cleanup.
The authored-theme case uses the prebuilt core to save/publish only into fixture
roots, then verifies editor colors. Build the engine with
`python3 -B tools/verify_anodize.py build`; this case reports a skip if unavailable.
The Lazy test similarly reports a skip if public loader source is unavailable.

On native Termux, the five focused cases, 23 shared-theme tests and 11 workflow
tests pass without skips. Those suites cover real fixture publication and all 17
family/flavor combinations. Formatting and parent/nested Git whitespace checks
are required. This evidence does not establish the appearance of a live Snacks
UI, a full normal LazyVim startup, or native desktop/Windows support.

The updated `python3 -B tools/bench_themes.py --samples 5` measured minimal isolated
Neovim startup on 2026-09-25: Anodize standalone median 65.59 ms (first 72.32 ms),
Anodize with Dots startup median 75.65 ms (first 79.49 ms). These include complete
editor process startup and all configured Anodize highlight integrations; they
are not comparable to an in-process reload benchmark or full LazyVim startup.
The earlier native-plugin measurements used a different runtime workload and
sampling session. No new cache was introduced to mask that difference.

### Anodize completion and manual verification

Run `python3 -B tools/test_anodize_integration.py` without the Go engine. It requires Bash, Zsh, Fish and mandoc, and tests parser/header consistency, static mode choices, generated-artifact freshness, manual lint, root presentation prefixes versus seed colors, theme providers, file paths, descriptions and literal insertion via real Tab presses. Each shell owns disposable HOME/XDG/config/cache/state/repository roots. A sentinel engine verifies completion never runs it. Run the Bash dispatcher suite for shared metadata/provider changes and the existing Zsh/FZF-tab acceptance for shell registration.

`python3 -B tools/generate_anodize_integration.py --check` verifies generated adapters/manual without writing. `mandoc -Tlint man/anodize.1` checks the section-1 manual. Native Windows shell completion remains outside the implemented POSIX CLI scope.

Native Termux verification (2026-09-25): all four Anodize integration cases, 23 Bash dispatcher cases and 14 authoring cases passed. Zsh/FZF-tab acceptance includes standalone Anodize option labels and unchanged reload state. The broader Zsh suite has two unrelated `ll` alias expectation failures, reproduced after removing Anodize from its disposable fixtures (15/17 passed).

## Optional interactive theme picker

`python3 -B tools/test_theme_picker.py` exercises the FZF-first live-preview switcher under
owned PTYs and disposable home/config/state/repository roots. Fixture tools cover
backend precedence, Back/Apply/Cancel, one publication on Apply, selection validation,
preview failure, empty catalogs, tool errors, missing tools, plain-menu input,
color precedence and noninteractive/data-interface bypass. Installed Gum enables
native filtering, review/cancellation and interruption checks; missing Gum skips
those native checks without installing anything. Width checks use 40, 80 and 120
columns. Installed FZF also enables live hovered-palette cancellation checks at
40/80/120 columns and forced-color preview/review coverage. Mixed FZF/Gum fixtures
verify FZF browsing, Gum review, no fallback after failure, and one publication
only on Apply. Published FZF color fixtures verify current-artifact precedence over
unpublished edits/stale shell variables, color controls and refusal without shell
execution for malformed data. Run the shared theme/workflow and Bash suites for adjacent contracts.

On 2026-09-28, all 14 picker tests passed on native Termux, including real Gum
2.0.0 filter/review/cancellation at 40/80/120 columns, forced color over NO_COLOR,
ASCII/Unicode modes, Ctrl-C and Escape, and installed FZF filtering/review/cancel.
A separate 40-column terminal transcript review confirmed readable palette rows
and the Back/Apply/Cancel menu. Deterministic fixture cases covered failure paths
and all backend choices; plain-menu Apply and Gum-fixture Apply each published
exactly one disposable generation. Bash dispatcher and shared-theme checks each
passed 23/23. The
workflow suite passed 12/14 with its previously documented 33-versus-34 theme-count
failures. Shell syntax, focused ShellCheck, documentation links and whitespace
checks passed. No live theme, wallpaper or shell configuration was changed. Native
Linux, WSL and Windows interaction remain unverified. Existing ordinary dispatch
and shell-startup paths do not load the interaction adapter; no performance claim
is made for the new interactive path.

## Interactive tracked-config browser

Run `python3 -B tools/test_files_browser.py` for the browser controller, guarded
plans and Python/Bash UI bridge. Tests use disposable repository/catalog/home and
state roots. Scripted choices cover preview, backup toggles, mutations, drift,
refusals and refresh; private PATHs select bridge backends deterministically.
Installed Gum/FZF enable native PTY checks, otherwise those cases are skipped.
Run `tools/test_files.py`, `tools/test_file_operations.py`,
`tools/test_bash_dots.py` and `tools/test_theme_picker.py` with `python3 -B` for
adjacent contracts. Native runtime evidence does not establish other platforms.

On 2026-09-28, browser checks passed 17/17, catalog checks 9/9, file-operation
checks 21/21, Bash dispatcher checks 23/23 and theme-picker checks 14/14. Native
Termux Gum/FZF PTYs verified details/exit and Gum Apply against a disposable target;
Gum details ran at 40/80/120 columns. A separate 40-column forced-color/icon
transcript was reviewed. The common POSIX catalog fixtures identify as Linux with
isolated platform inputs, not as evidence of native Linux execution. Syntax,
focused ShellCheck, documentation links and whitespace checks passed. Browser
checks cover source/target/catalog/composition drift, protected links, directory
materialization refusal, no-op links, backup-required replacement and metadata-only
browsing with control characters displayed literally. No real configs or state
were modified; other native platforms remain unverified.

## Optional operation confirmations

Run `python3 -B tools/test_confirmations.py` for file/Git approval integration and
shared adapter checks. Fixtures own all home/config/state/cache/data and Git
roots; publication uses only disposable local bare remotes. Cases cover default
Cancel, approval, selector failure and interruption, invalid labels, drift while
reviewing, missing tools, dumb/redirected terminals, JSON and explicit approval
bypass, and inherited theme/presentation policy. Installed Gum enables native PTY
checks; fixture tool results are distinct from native tool evidence.

Anodize confirmation cases live in `tools/test_anodize.py`; run them through
`python3 -B tools/verify_anodize.py check`, which supplies the isolated engine.
Also run the existing browser, theme-picker, file catalog/operation, Git and Bash
suites for changes to this shared layer. No verification applies live configs,
activates themes or publishes the developer's repositories.

On 2026-09-28, native Termux confirmation checks passed 8/8, Anodize's isolated
Go checks and 16/16 CLI tests passed, and browser 17/17, picker 14/14, file
operations 21/21, Git operations 25/25, catalog 9/9 and Bash dispatcher 23/23
passed. Real Gum PTYs verified default Cancel, Apply/Publish, Escape and Ctrl-C at
40/80 columns, including forced color/icons; a plain 40-column transcript was
reviewed. Anodize's new prompts used fixture Gum. Syntax, focused ShellCheck,
Markdown links and whitespace checks passed. Other native platforms remain
unverified; see the [focused plan](../plans/gum-confirmations.md).

The accompanying shared-theme suite passed 23/23. Theme workflow remained 12/14:
the existing flat-catalog and presentation assertions expect 33 themes, while the
current catalog contains 34. Those unrelated assertions remain unchanged.

## Theme plugins

Run `python3 -B tools/test_theme_plugins.py` for isolated discovery, selection,
execution/recursion/concurrency, clean output, managed app preservation and
interruption/recovery/undo. Fixtures use copied public trees with rebased links,
owned HOME/XDG roots and stub GTK/Qt commands. No real application config is changed.
Run the existing theme/workflow, file-operation and Bash-framework suites alongside
it; `python3 -B tools/verify_anodize.py check` includes shared-publication and inert
authoring acceptance. Use `python3 -B tools/test_anodize_integration.py` for the
shared shell metadata boundaries and existing Zsh/FZF-tab checks when completion
changes. Syntax/ShellCheck, Markdown links and `git diff --check` remain required.
Report native Termux separately from simulated platform skips and desktop fixtures.
Live GTK/Qt visual behavior and native Windows execution require separate evidence.

### Termux automatic tmux startup

Run `python3 -B androidots/tests/test_termux_bar.py` for mocked launcher identity, PID reuse, child-shell guards, discovery errors, missing tmux, timeout and collision/race cases. Run `python3 -B tools/test_termux_autostart.py` for native Bash/Zsh PTYs and a private tmux server: separate tabs, project switching without nesting, default reattachment, surviving detach, final-pane `exit`/`q` closing the outer shell, multiple panes and project switches, another tab surviving, server-loss fallback, reload idempotence, startup guards and launcher failure fallback. Identity/discovery in these PTYs is simulated with owned procfs files and a stub script; this is not proof of actual Android app startup. No real Termux process discovery, Android APIs, live shell initialization or live tmux changes are used.

Also run the existing tmux status/session and shared-shell/init suites, Bash/Zsh syntax checks and ShellCheck for the shared startup hook. Status verification covers marker-dependent name visibility across config/theme reloads and narrow rendered terminals. Measure guarded shell-startup cost separately from first attachment and document the fixture boundary. Real new-tab startup and font appearance remain manual acceptance.

## Unified theme command acceptance

Run `python3 -B tools/test_theme_commands.py` alongside the shared theme, workflow,
Bash dispatcher, file-theme and Zsh suites. It uses disposable public fixtures to
cover entry-point equivalence, native query compatibility, palette-only activation,
metadata grouping, logos/data boundaries, generated completion registrations,
idempotence, rollback, interrupted publication and drift refusal. Native Windows
execution of the POSIX wrappers is not claimed.

## Dots shell environment

`python3 -B tools/test_starship_defaults.py` tests default config discovery,
recognized legacy override cleanup, custom overrides and repeated initialization
in disposable homes. It checks the managed HOME-relative destination and runs
Clink cleanup against a stubbed Windows environment. Unavailable native shell
runtimes are skipped; stubs do not certify native Windows. The Starship palette
suite below also covers a default-path link with a nondefault XDG config root.

Run `python3 -B tools/test_shell_environment.py -v` for isolated settings, reload, diagnostic and native adapter contracts. Use small sequential cases on resource-constrained Termux hosts. Tests source library integration without personal rc files; unavailable native runtimes must be reported separately.

Environment presentation cases use owned native PTYs at 40/80/120 columns and
cover automatic/plain/forced colors, value sources, long Unicode paths, inert
control-character display, unchanged redirected lines and undecorated scalar/JSON
queries. They verify inspection creates no state or cache. Run the Bash dispatcher
suite as well when shared UI helpers change.

## File styles and theme panels

`python3 -B tools/test_file_colors.py -v` checks saved/published boundaries, journaled
rules, full styles, MIME/suffix precedence, inert parsing, family panels and raw
output. It also compares full `show`/`colors` overviews, preserves native scope,
checks JSON/scalar/export bytes under forced color, and renders dark/light full
overviews through owned native PTYs at 40/80/120 columns. Configured overviews
are tested with a failing Vivid stub to prove generation is unnecessary. Run
sequentially with the existing theme publication and shell-environment
suites. Standalone dots.yazi adds `python3 -B test-theme-native.py` for private DDS
notification, dark/light publication, N/V/U mode redraws, narrow layouts and
last-good snapshot recovery. Its ordinary native runner accepts `--config-dir`
and defaults to bundled fixture configs rather than assuming a parent checkout.

## Checkout installation

Run `python3 -B tools/test_file_platform.py` (`python` on Windows) for native file
durability before the lifecycle suites. It covers writable and read-only payloads,
Unicode paths, flush-error propagation before replacement, permission-sensitive
undo and text fingerprints under POSIX umasks `022` and `077`. Installation's
real theme switch/reconcile/uninstall regression also runs under both umasks.

Native CLI fixtures redirect module-analysis caches to test-owned paths and allow
only known PowerShell startup-profile files in their native cache directories.
Unexpected Dots home/config/state/cache writes still fail read-only checks. Git
worktree fixtures explicitly establish stale remote-tracking state rather than
assuming URL pushes never update it. Documentation checks retain strict link
validation with submodules absent; parent references into optional submodules use
public revision-pinned links. See the [repair evidence](../plans/ci-repairs.md).

The installation suite also exports versioned public source paths into an owned
checkout, excluding ignored connectors and optional submodule contents (with
explicit new-source additions before their first commit). It simulates WSL
detection and verifies all enabled fixed connectors, template outputs, FSH
catalog retention, reinstall and uninstall. Recovery cases remove outputs and
the active pointer, reject incomplete preparation and foreign pointers, and
inject failure after pointer publication to verify rollback of the receipt and
selection. These fixtures do not establish native WSL runtime support.

`python3 -B tools/test_file_themes.py` additionally covers missing-output refresh,
custom template outputs, unsafe artifact links, cold native FSH caches and
actionable, deduplicated failures. Native FSH cases copy the installed public
plugin into owned roots and skip when unavailable; cold-cache tests disable
network helpers explicitly.

Run `python3 -B tools/test_installation.py` and `python3 -B tools/test_installation_adapters.py` (`python` on Windows). Fixtures own HOME/XDG/AppData/profile roots, configuration sources and local Git remotes. Coverage includes dry-run, retained baselines across updates, idempotence, preview drift, process interruption/recovery, link refusal, explicit optional-source initialization, actual POSIX theme generation and native entry-point/data interfaces. PowerShell runtime and native Windows cases skip when unavailable; skipped capability checks are not positive platform evidence. The installation CI workflow covers Linux and Windows without initializing project submodules. Run existing file/catalog, theme, shell-init, dispatcher and progress regressions for their affected shared components.

### Shared resource presentation

Run `python3 -B tools/test_resources.py` for isolated Bash/Python resource matching,
published and legacy snapshots, case-colliding suffixes, invalid data, path safety,
icon/color independence, narrow layout and theme-context preservation. It also checks
sanitized heading spans, optional detail label width/gap, continuation alignment and
unchanged default spacing. The existing
shell-environment, Git/file operations, theme/file-color, Anodize/logo, installation
and progress suites cover their owning views and undecorated interfaces. Keep
native PTY evidence distinct from platform-simulated tests; PowerShell changes
require native verification where the runtime is available. See the
[presentation rollout](../plans/cli-presentation.md) for results and baseline limits.

## Git theme styles

Run `python3 -B tools/test_git_styles.py -v` for published Git-role consumption, porcelain-state priority, old/malformed/unsafe projections, color policy, resource-style independence, native 40/80/120-column PTYs, tracking counts, and sync/publish success and failure output. All Git mutations and remotes are fixture-owned. `tools/test_file_colors.py` covers Git defaults, layered edits, publication, additive exports, older snapshots and Bash/Zsh/Fish completion. Run these with `tools/test_resources.py`, `tools/test_git_operations.py` and relevant theme publication cases sequentially on Termux. Native Termux acceptance does not establish native Windows console support.

The standalone Yazi color-reference and Git-indicator fixtures (`test-color-refs.lua` and `test-git-colors.lua`) cover token resolution, complete style attributes, fallback and refresh. Its package regression validates dirty-upgrade refusal and clean upgrades in an offline test-owned repository. The native theme runner exercises references and optional Git-group validation; see the [plugin README](../config/yazi/plugins/dots.yazi/README.md).

For the Starship palette adapter, run `python3 -B tools/test_starship_palette.py` and `python3 -B tools/test_theme_plugins.py`, plus affected theme-workflow tests. The focused runner owns all HOME/XDG/Starship/Blastoff paths, exercises section scanning, separate module edits, symlinks, locks, concurrent changes and injected rollback, and validates installed-module coverage and native Starship output in a synthetic repository. The plugin suite verifies dark/light publication, resolved Git aliases, opt-in discovery, unchanged refresh and skipping other active palettes. `python3 -B tools/test_theme_workflow.py Workflow.test_codex_shared_template_all_palettes` also checks the Starship palette against exported shared colors for every selectable theme. No live prompt, custom module command or version detector is executed as a validation step.

### Git template and platform selector

Run `python3 -B tools/test_git_theme.py` for native Git/Delta dark/light rendering,
custom syntax-cache loading, reset/override colors, fallback and refresh
idempotence. It isolates HOME/XDG/Git roots and does not execute credentials or
user hooks. The all-palette workflow case also parses every generated Git include.
Run `python3 -B tools/test_git_platform.py` with the file-mapping, file-operation,
catalog and installation suites for companion selection, protected objects,
receipts, stash/restore, rollback and uninstall. The Git migration cases in
`tools/test_file_mappings.py` exercise legacy and consolidated layouts. Platform
selection fixtures are not native Windows/WSL execution evidence.

## Verbose operation verification

Run `python3 -B tools/test_verbose_operations.py` for isolated file/setup/theme action notifications, backup retention and cleanup, rollback and observer failure, metadata-only operations, JSON compatibility, option completion, switcher Apply/Cancel, and native PTY rows with progress at 40/80/120 columns. Fixtures own home/config/state roots; no live installation or theme refresh is used. Pair it with the existing progress/resources, file operation/installation/mapping/check and theme workflow/picker suites for changes to shared presentation. Native PowerShell wrappers remain a separate platform gate.

## File workflow pickers

Run `python3 -B tools/test_file_pickers.py` for automatic/explicit selection,
argument conflicts, exact token/path round trips, discovery subsets, enabled and
disabled resource filters, bounded credential-safe previews and read-only dry runs.
The suite includes native FZF PTYs at 40/80/120 columns, preview cycling, selection
keys, cancellation, color/icon controls, inherited-option isolation and temporary
snapshot cleanup. Missing native FZF is reported as a skip.

Also run the browser, file-mapping, catalog, file-operation and installation suites,
plus shared interaction/confirmation, resource, progress and verbose regressions.
The browser suite covers native Gum and numbered-menu fallbacks and guarded Apply.
Run sequentially with owned roots; native Termux evidence is not Windows evidence.

## Native PowerShell parity

`python3 -B tools/test_native_cli.py` covers static route coverage, encoded literal arguments, file preview/completion, Windows path validation and app variants, palette comparison with Bash, native publication idempotence/drift/undo, setup inspection and available PowerShell engines. Set `DOTS_TEST_POWERSHELL=powershell` or `pwsh` to require an engine; absence becomes a failure. Otherwise unavailable engines are explicitly skipped. Use `python` on Windows. All roots and mutation targets are disposable fixtures.

`python3 -B tools/test_native_git.py` runs the existing portable Git safety cases against `lib/dots/git/cli.py`. It excludes three tests that explicitly launch Bash/PTYS; it does not claim native terminal cancellation coverage. The existing Bash Git runner remains unchanged by default. Run these suites sequentially on Termux.

The checkout-installation workflow includes a native CLI job with required Windows PowerShell 5.1 and PowerShell 7 entries, plus Linux controller coverage. A configured workflow is not a completed CI run. Record its actual result before promoting Windows support claims. Owner-run desktop, link privilege, FZF interaction and terminal checks are listed in [native PowerShell](powershell.md#acceptance-and-remaining-limits).

`python -B tools/test_native_anodize.py` exercises native authoring, raw export, the native read-only bridge and publication with desktop reloads stubbed. It uses a prebuilt native engine; `DOTS_TEST_ANODIZE=1` makes a missing engine a failure. The native CI job builds the existing engine with `tools/verify_anodize.py build`, whose Windows output has the `.exe` suffix. On Windows, `verify_anodize.py check` runs Go tests/vet and the native authoring suite; `bench` reports engine benchmarks only. POSIX verification retains the Bash frontend suites and timings. No Go engine behavior changes are involved.

### Anodize interactive authoring

`python3 -B tools/verify_anodize.py check` also runs
`tools/test_anodize_interactive.py` with its isolated engine. It covers user/built-in
storage, promotion and renamed copies, rollback/recovery/undo, all mode candidates,
completion cache reuse, temporary cleanup, exact preview colors/dimensions, and
native FZF cancellation at 40/80/120 columns. Set `DOTS_TEST_FZF_TAB` to an installed FZF-tab source directory to require its copied-source Zsh preview check; this does not initialize or download plugins. All roots are disposable. Run the
Anodize integration, theme-picker, theme-command, file-color, Bash dispatcher and
Zsh suites for shared surface changes. PowerShell controller fixtures are distinct
from native Windows PowerShell 5.1/7 terminal acceptance.

## User-local completion paths

Run `python3 -B tools/test_local_completions.py` for user-local Bash/Zsh/Fish discovery and precedence. It uses disposable home/config/data/cache/state/repository roots, synthetic colliding providers and installed native shells; it covers custom XDG and home fallbacks, spaces/Unicode, reload deduplication, exported Zsh FPATH, lazy Bash loading, Fish provider selection and noninteractive boundaries. Pair it with the existing Androidots path and shell startup/environment suites. Unavailable native shells are skips; Termux execution does not establish Windows PowerShell 5.1/7 startup acceptance.

## Termux location helper and completion paths

Run `python3 -B androidots/tests/test_termux_geo.py` and then `python3 -B tools/test_termux_geo_shells.py` from the parent checkout. The first suite mocks device/HTTP providers and exercises normalized output, cache freshness, strict failures, deadlines, rate limits, concurrent calls, cancellation, guarded completion installation, and native 40/80/120-column PTYs. The second uses disposable public-shell fixtures for native Bash/Zsh/Fish local discovery, autoloading, repeated initialization, preserved paths, and platform/noninteractive exclusions. All HOME/config/state/cache/install paths are test-owned. Neither suite performs live GPS/network lookups or loads owner shell configuration. Also run affected shell-init, shared-shell, and Zsh regressions for startup edits. Actual Android permission/provider/service-cancellation acceptance remains separate.

Acquisition regressions check the inherited file-size resource limit, the 64 KiB device-output boundary, phase-specific deadline errors, HTTP timeout status, pipeline cleanup, and cache-lock release. Separate native Android acceptance must preserve the Android process environment while redirecting mutable roots; mock-only environments do not establish native API compatibility. Do not print device coordinates in acceptance reports.

## wttr and daylight clock

Run `python3 -B tools/test_wttr.py`, then `python3 -B tools/test_tmux_status.py` and `python3 -B tools/test_android_status.py` sequentially. Weather fixtures own home/config/cache/state and mock geo/HTTP/curl; they check city/config precedence, city-versus-neighborhood labels, cache-version recovery, exact stock URLs/bytes, parser conflicts and provider-free service routes; they cover cache expiry, bad data, deadlines, cooldown/recovery, undecorated data, completion backup/undo, native shell completion and terminal presentation. Help tests assert exact artwork, gradient endpoints/interpolation/fallbacks, title icon controls and provider/config independence. Alias tests compare every short/long form, attached/grouped parsing, stock conflicts, native bridge data bytes and case-sensitive completion contexts. Styling tests use explicit fixture temperature scales, named detail glyphs/styles and label gaps independent of owner config edits. Solar-field tests cover padded/unpadded hours, noon/midnight, preserved provider/cache data and unchanged daylight boundaries; terminal assertions check trailing detail icons. They cover variable band counts, boundaries/conversion, combined attributes and bright variants, widget directive preflight/manual mode/accumulation/reset, published palette changes and bounded malformed-snapshot fallbacks, named/hex/index overrides, forecast icons, attribution, ANSI/plain/tmux widgets, configurable aligned label gaps and single-space icon gaps, named detail glyphs/colors/directives, independent location-heading styling, shared-span wrapping and actual FZF-tab descriptions/insertion. Plain and data paths bypass palette reads. Tmux widget tests check escaped literals and restoration of incoming colors and text attributes. Tmux tests attach clients on private sockets at 40/80/120 columns, check day/night/unknown colors and repeated reloads, and assert no Android network module calls. Run the Androidots geo/status/session/bar regressions and affected theme/file/native-adapter suites. Never use live weather, real coordinates, permissions or the live tmux server as fixtures. Native Windows PowerShell 5.1/7 cases must be recorded as pending/skipped when unavailable. See [the focused plan](../plans/wttr.md).

## eza theme

Run `python3 -B tools/test_eza_theme.py -v` for isolated Bash/native-renderer palette equivalence, eza schema and real ANSI output, Git overrides/reset translation, path precedence/refusal, bundled/personal overrides, fingerprints, connector idempotence, interruption recovery, rollback and drift. PyYAML enables structural comparisons; eza enables native consumer checks. Missing optional consumers are reported as skips. All home/config/state/cache/repository roots are disposable; no real shell startup, credentials or hooks execute. Run the existing file-color, theme/workflow, native-controller and installation suites sequentially for shared publisher changes.

Native eza consumer checks require eza 0.23.5 or a compatible theme schema. The PowerShell frontend uses the same Python renderer and native transaction engine, but controller fixtures on Termux do not prove native Windows behavior. Pending acceptance: run publication/undo and dark/light eza output in disposable roots from Windows PowerShell 5.1 and PowerShell 7, including APPDATA/EZA_CONFIG_DIR paths and unavailable symlink privileges. No privilege changes or silent copy fallback are allowed.

## Television theme

Run `python3 -B tools/test_television_theme.py -v` for isolated all-palette Bash/Python TOML equivalence, destination precedence, Windows destination fixtures, personal/bundled overrides, fingerprints, missing app/parent handling, backup/rollback, interruption recovery, directory identity and drift checks. All mutable roots are disposable; Pywal uses a synthetic export. Installed `tv` enables dark/light PTY checks at 40/80/120 columns with synthetic entries, asserting actual RGB background and selection colors. No user channels or hooks are executed. Run affected theme/workflow and native-controller suites sequentially after the focused suite.

The native consumer case targets Television 0.15.9. Native Windows PowerShell 5.1/7, Linux and WSL acceptance remains pending: validate publication/undo in disposable roots, native app destinations and unavailable link privileges, and dark/light Television rendering. Termux Python fixtures are not Windows execution evidence. Windows does not require Bash and never silently substitutes copies for links.

`tools/test_git_submodules.py` also covers named and repeated navigation, ambiguous basenames, collection-info counts, contextual help/completion, identity glyph/data separation and named-publication parent protection through both front ends. These use disposable repositories; native Windows terminal acceptance is separate.


## Leaf theme

Run `python3 -B tools/test_leaf_theme.py -v` for all-palette Bash/Python TOML equivalence, semantic contrast, shared syntax destinations, personal/bundled overrides, missing optional apps, fingerprints, two-connector recovery, directory creation, backup and drift checks. Set `LEAF_TEST_BIN` to an absolute custom Leaf executable to enable actual inline token-color assertions and dark/light Termux PTY checks at 40/80/120 columns, including theme-picker preview/cancel, resize and document reload. Missing consumer checks are explicit skips. Every mutable home/config/state/cache/repository path is disposable. Run the native-controller, installation, file-color and Television regressions sequentially after shared publisher changes.

The [custom Leaf build](leaf-build.md) has Rust tests for relative/absolute syntax paths, embedded themes, missing/malformed files, noncolliding ThemeSet keys, symlink-relative resolution and picker cancellation. Native Windows PowerShell 5.1/7 publication/undo, missing symlink privileges and native Leaf dark/light rendering remain pending, as do Linux and WSL acceptance. Controller fixtures on Termux do not establish those claims.
