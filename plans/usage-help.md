# Dots help and usage

## Configurable help follow-up

**Status: Implemented and locally verified; local Wiki synchronized. Native Windows PowerShell 5.1/7 and Linux/WSL terminal acceptance pending as agreed.**

Selected Todo goal: `6e3fcbc7f08140a39f4306010b4706a5` (`usage output update`). Preserve the earlier root-grouping implementation and evidence below. This follow-up covers all first-party help, bundled applications and shipped standalone aliases, including error usage and explicit syntax references. Ordinary reports/results are outside this scope. Existing layouts, authored branding and addressed theme palettes remain owned by their current renderers.

The agreed shared syntax roles are executable (theme cyan), command (blue), subcommand (magenta), option/flag (yellow) and argument (green), with corresponding ANSI fallbacks. Help heading, description, punctuation and tagline styles are independently configurable through `colors.apps.cli.help.*`. The root tagline is controlled by `apps.cli.tagline`, defaults to `Manage your dotfiles and more...`, has no `dots —` prefix, and is hidden by an empty string. Its default color is the theme accent when present, otherwise foreground. Help-only preferences activate on the next invocation without theme publication or consumer reload.

Saved high-priority children (all directly attached to the selected goal):

| UUID | Work package | Dependencies and acceptance |
| --- | --- | --- |
| `03ed8c6c6a2b4199bdae3e2bdc42ab28` | Shared help styles and Config integration | Foundation; actual consumer output, all style fields, tagline hiding/fallback, inheritance/reset and next-invocation saves. |
| `15a3616d45424474b9747c56e72167a2` | Core help across Bash and native frontends | Depends on shared integration; root/family/leaf syntax, root content parity, grouped discovery, inert metadata and Python-free defaults. |
| `764284d0a4924c33b0d9daa0f44ba555` | Bundled apps and standalone help | Depends on shared integration; every public help/error-usage path and aliases retain layout, branding, stream/status and data contracts. |
| `bd4b1a3697d1402eb9b4dd5efa13002d` | Verification, documentation and delivery | Depends on all above; isolated suites, 40/80/120-column checks, performance, Config/completion, documentation and local Wiki synchronization. |

Command maintenance owns shared help, Config owns preference storage/editor/activation, and each family retains its existing maintenance owner. Configuration assessment: **add/update**, with rendered consumer checks. Menu assessment: **update existing Config browser/editor discovery**, with no new static-help launcher. Installer/bootstrap assessment: existing core/application components deliver the shared helpers, defaults and wrappers; verify this through owned installations. Windows application destinations are unchanged. Six-shell completion and aliases remain synchronized; completion/JSON/scalars/raw/generated shell output must stay undecorated. Basic Bash and PowerShell help retain builtin defaults when Python preference resolution is unavailable.

Completion review preserves the existing grammar and alias registrations. All six Dots shell adapters use the shared Config key/value providers, so the added preferences need no generated command grammar. Existing Nushell/Xonsh standalone completion allowlists omit `todo` and `fonts`; their `dots todo` / `dots fonts` routes remain available. This pre-existing registration limit is recorded rather than claimed as newly implemented. Bash/Zsh/Fish and native-provider alias checks retain their existing coverage. Installer review confirms linked/native launchers point into the complete checkout, so the shared helpers accompany existing core/application components without a new payload manifest.

Apply the [presentation acceptance gate](../docs/presentation.md#acceptance-gate), with isolated source/home/config/state/cache roots and sequential Termux suites. Test explicit syntax spans, quoted/Unicode paths, flags and values, `--`, controls, missing palettes, plain/redirected output, separate stdout/stderr color policy and extension nonexecution. Measure help, direct dispatch and affected startup projections without adding caches. The owner explicitly accepts named pending native Windows PowerShell 5.1/7 and Linux/WSL terminal checks after local/shared-controller acceptance; fixtures are not native evidence. Rebuild/check the available Wiki from canonical sources. No commit, push, live installation or application reload is authorized by this implementation.

Todo updates use scoped CLI operations and full UUIDs, with rereads before writes, progress notes, and verified child-before-parent completion. Preserve existing unrelated changes and reconcile resumed work instead of recreating goals.

### Local verification

The full Bash CLI suite passed all 31 tests; subsequent focused checks passed for command alternatives and configured roles. The native-controller suite ran 26 tests: 23 passed and three native PowerShell runtime cases were skipped because no engine is available. A final focused regression passed for all four manual native usage errors. The shared span suite passed nine tests, including repeated standalone/Dots invocations. The specialized adapter suite passed all eight tests, including manual stderr usage, native theme action/operand roles, addressed palette backgrounds, weather browser help, Wiki argument errors and unchanged data/plain contracts. Both focused weather-browser help/completion/width checks passed. Focused Config/style/browser/completion and compiled-startup checks cover saved preferences, previews, inheritance/reset, activation and warm Bash/Zsh startup without Python.

The bundled suite covered 18 cases: 17 have passing evidence from the full run plus the targeted installed-help rerun; one native-runtime case remains skipped. The rerun verifies minimal-checkout help, repeat-install idempotence and restoration after correcting the absent-profile fallback. Blastoff's 15 help cases have passing evidence across the full run and targeted reruns; focused Anodize, Fonts and weather help checks also passed. These are isolated fixtures, with no live application installation, provider calls or profile edits.

Thirteen exact baseline/current comparisons passed for command inventory, scalar/JSON preferences, four completion scripts and six shell initialization snippets, including forced-decoration checks on data routes. All six Config completion providers expose the new keys without ANSI. Metadata validation passed for 291 fixture commands, including the owned probe. Twenty-four owned PTY captures cover root/family help through Bash/Python at 40/80/120 columns with light/dark palettes; each uses the expected palette foreground and fits its terminal width, and representative narrow/wide output was reviewed. Existing layouts and branding remain intact.

Python syntax checks passed for 57 changed/new files; Bash syntax passed for six. The new Bash helper passes ShellCheck, and `git diff --check` passes. Markdown validation passed for 1385 relative links in 172 files. Blastoff manual lint retains the same six pre-existing line-length style diagnostics, with no new diagnostics. Canonical docs, README, the focused plan and maintenance guidance are synchronized. The available local Wiki was previewed and rebuilt through transaction `2a0007269e3348999fecd1123f7c31f7`; its final check reports `Healthy yes`. No publication was performed.

The accepted remaining native checks are Windows PowerShell 5.1/7 and real Linux/WSL terminal output, including configured/default help, stream color policy and narrow/light/dark readability. They remain pending and are not represented by Termux or shared-controller results.

### Performance evidence

Measurements use owned baseline/current source snapshots, synthetic profiles and temporary homes on Termux. Initial sequential batches were affected by changing host load: alternating samples did not reproduce the apparent plain-root or direct-dispatch regression. Duplicate `Controls` construction was removed from the shell-settings/startup projections, and Bash token extraction now uses builtin regex matching. Ten before/after token-span comparisons and four full help captures retained exact bytes through that optimization. No persistent cache was introduced.

Final medians from three alternating samples per variant, in milliseconds:

| View | Baseline wall / CPU | Current wall / CPU |
| --- | --- | --- |
| Plain family help | 666 / 646 | 669 / 653 |
| Colored root help | 2377 / 2249 | 2759 / 2671 |
| Colored family help | 694 / 686 | 816 / 807 |
| Settings projection | 316 / 312 | 364 / 358 |

Colored syntax/layout retains about 0.12 seconds of family-help CPU overhead and 0.42 seconds for root help in this fixture; settings projection adds about 46 ms. Plain family help is effectively at baseline, and no direct-dispatch regression was established. These small local samples are not cross-platform guarantees. Evidence, source snapshots, timings and settings profiles are retained at `/data/data/com.termux/files/usr/tmp/dots-help-evidence-uv9tdoel`.

## Previous root-grouping implementation

**Status: Implemented; native Windows PowerShell 5.1/7 and Linux/WSL terminal acceptance pending.**

Selected Todo goal: `2acf2a75677e47dfa286c06e4f499edc` (`usage`).

## Accepted behavior

Owner-requested follow-up (2026-10-31): add `apps.cli.logo_gradient` with `classic` (existing vertical blue/cyan; repository default) and `installer` (horizontal theme hint/info/accent). Config owns typed validation, profile inheritance, editor/value completion and next-invocation activation without publication; Command maintenance owns root rendering. Apply `installer` to the active Termux profile through Config after an isolated consumer check. Preserve basic help without Python via classic fallback, existing artwork/plain output and data interfaces. Menu review: unchanged, because the existing Config editor exposes the setting. Installer-only changes abbreviate the Profile home prefix and apply green instruction/cyan preference-heading spans. Cover Bash/shared native output, finite choices/reset, 40/80/120-column setup terminals and metadata; real PowerShell remains a named pending check. Windows destinations and direct dispatch are unaffected.

Follow-up verification: all 28 Bash CLI tests passed, including exact shared gradient output, classic fallback without Python, finite value completion and undecorated data. The focused Config test passed for validation, popup choices, profile saves, reset and activation without refresh. All seven setup wizard tests passed; actual Gum additionally passed green guidance, cyan heading and cancellation at 40/80/120 columns. The native controller suite ran 23 tests with 21 passing and two unavailable PowerShell runtime tests skipped. Python/Bash syntax, ShellCheck, all 244 external command metadata entries, 1217 relative links and whitespace checks passed. The authorized Termux preference was saved through Config transaction `01366f899efa456c8a650c3a60dc857c`; comparison confirmed every other profile field was preserved. Active root usage matches the shared installer renderer. Wiki transaction `743c1f55afc5485b9909ae7cbeefed81` rebuilt the affected pages and the final check is healthy.

Performance evidence for this follow-up: five serial colored root-help runs had a 1.7558-second median, compared with an earlier 0.6842-second observation before this change. The standalone shared logo helper measured 0.3254 seconds median; profile/palette resolution now adds this subprocess to colored Bash root help. The measurements were taken at different times on the active Termux device and do not isolate the entire difference from host load. Direct dispatch, shell startup and plain Bash help do not invoke the helper. No cache or performance improvement is claimed. Test logs are retained at `/data/data/com.termux/files/usr/tmp/dots-logo-checks-6ybr8rdb`.

Root help (`dots`, `dots help`, `dots -h`, `dots --help`) shows one row per visible top-level command or group. Preserve each renderer's existing rows, built-in usage synopses, branding, usage and global options. Keep family/leaf help and `dots commands` exhaustive. Add the footer: “Use dots help COMMAND for details; dots commands for all commands.”

Group visible entries by the first route component without modifying the catalog. Prefer a visible parent's summary; use “Command group” otherwise. Deeper-only extensions remain discoverable; hidden-only groups remain absent and hidden metadata is never displayed. Preserve ordering, discovery roots, validation, collision behavior, direct dispatch, completion records and generated references. No new runtime dependency or extension execution.

Bash, the shared native Python CLI and Python-free PowerShell help implement the same projection through their existing renderers. Windows app destinations, installation and shell startup remain unchanged. Menu review: **unchanged**, because static help adds no selectable workflow.

## Work packages

1. `52a77005a6de4c2d83283bd6b76107e9`: compact root help across all three frontends; isolated regressions for aliases, real/implicit/hidden groups, full contextual help/inventory, completion, validation and nonexecution.
2. `4ab948cfe97349c39797a8f7874def2c`: depends on package 1; verify presentation and synchronize canonical docs and the local wiki while preserving existing changes.

Both children inherit high priority. Todo CLI mutations own progress, notes, recovery and child-before-parent completion; the selected goal's original title, alias, tags and notes are retained.

## Acceptance and evidence

Follow the [presentation gate](../docs/presentation.md#acceptance-gate): existing semantic roles, successful stdout/error stderr, readable plain/redirected output, color/icon controls, `NO_COLOR`, `TERM=dumb`, 40/80/120 columns, Unicode/long summaries and inert metadata. Mutation/recovery and interactive prompt cases do not apply to static help. Completion/generated data must remain undecorated and unchanged.

Run the Bash CLI and native CLI suites sequentially in owned roots, relevant syntax/ShellCheck checks, documentation link validation and `git diff --check`. Extend the native PowerShell runner to cover all four root-help forms, implicit groups, full family help and wrapped footers with Python absent from PATH. Record unavailable engines as pending, not native evidence.

Verification on Termux:

- Bash CLI: 27/27 tests passed, including actual Bash/Zsh/Fish completion and all new root-help cases.
- Native CLI: 23 tests ran; 21 passed and two PowerShell runtime cases skipped because no engine is available. Shared-controller fixtures do not establish native Windows execution.
- 52 exact before/after comparisons passed for full inventory/validation, family/leaf/implicit-group help, generated completion source for all four shells and deep route/option-value completion, with forced and disabled color. Extension markers remained absent.
- 30 owned PTY captures passed across Bash/Python, 40/80/120 columns and automatic, disabled, `NO_COLOR`, dumb-terminal and forced styling. Unicode/long summaries and footer wrapping remained readable; fixture homes stayed empty. Reviewed representative narrow/wide captures. Actual Windows/Linux/WSL terminal and light/dark display acceptance remains pending.
- Bash/Zsh/Fish syntax checks passed. The changed Bash file has the same seven pre-existing ShellCheck diagnostics as its saved baseline (six unresolved dynamic sources and one externally consumed metadata variable); no new diagnostics. The broader framework ShellCheck run was stopped after exceeding three minutes and is not claimed as passing.
- Command validation passed for all 232 current external commands. Root help displays 16 external groups plus four built-ins. This is dynamic metadata, not a fixed list. Dispatch/startup paths and discovery algorithms are unchanged; no performance improvement is claimed.
- Relative Markdown validation passed (1125 links in 146 files), as did whitespace checks. Wiki preview selected its manifest and the generated Commands, PowerShell and Testing pages. The final build reported unchanged, and `dots wiki check` reported `Healthy yes`; the generated pages contain the updated root-help documentation. Concurrent menu/documentation edits were preserved.

Saved source snapshots, lint comparisons, output comparison counts and terminal captures are retained at `/data/data/com.termux/files/usr/tmp/dots-usage-help-pdw_8bjo`. Existing source and wiki edits were preserved. No commit, push, installation or reload is part of this change.
