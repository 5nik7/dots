# Unified shell initialization

**Implemented, 2026-09-29.** This owner-authorized maintenance change adds `dots init` for Bash, Zsh, Fish, PowerShell, Nushell, and Xonsh. General Go migration remains paused.

## Contract and migration

The [shell initialization reference](../docs/shell-init.md) owns invocation, native defaults, errors, reload behavior, and generated Nushell setup. Startup wrappers delegate to native loaders. Existing interactive bodies remain in separate files; Zsh-specific modules are not ported to other shells. Native `bin/dots.ps1` only emits PowerShell initialization and help. No package installation, new home-directory links, commits, or publication are part of this work.

Preserve the owner's existing environment, completion, theme, nested-repository, and untracked `zprofile` edits. The additional change to the already modified `dot.env` preserves a nonempty `DOTCONFIG` override; `shells.env` also retains an explicit `SHELLS` override.

## Presentation gate

Follow the [shared presentation contract](../docs/presentation.md). Help and invalid/missing-loader diagnostics use the shared Bash renderer. Generated code stays exact under forced color/icons, `NO_COLOR`, redirected output, and `TERM=dumb`. Tests include spaces, Unicode, quotes and shell metacharacters. Native PowerShell uses plain native help/errors. Initialization has no lists, operation previews, confirmations, progress, or mutation summaries; those presentation cases do not apply.

## Acceptance and evidence

- `python3 -B tools/test_shell_init.py`: 19 tests, 17 passed and 2 PowerShell tests skipped. Native Termux Bash, Zsh, Fish, Nushell 0.116.0 and Xonsh 0.24.2 were exercised. Xonsh interactive coverage uses readline and a test-owned PTY because optional prompt-toolkit is absent.
- `python3 -B tools/test_public_fixture.py`: 2 passed. `tools/test_bash_dots.py`: 23 passed. `tools/test_themes.py`: 23 passed after repairing fixture isolation.
- Bash/Zsh/Fish syntax, ShellCheck for the dispatcher/generator/shared environment/bootstrap code, added relative Markdown links and whitespace checks passed. This is not a ShellCheck claim for all historical configuration bodies.
- The existing Zsh suite remains 15/17: two tests expect `ll='ls -la'`, which does not match the current aliases. Its minimal PATH now includes Bash for the new hook. The obsolete `bin/box` copy requirement was removed from its fixture.
- Native Zsh PTY checks reached prompt readiness, reload, completion, directory selection and history selection, but failed on preview callbacks invoking missing `box`. The same failure reproduced against the retained pre-change source snapshot; no full PTY pass is claimed.
- Before/after Zsh public-state comparison preserved all aliases, completion registrations and functions after normalizing plugin-generated session IDs.
- The repository-wide documentation checker remains blocked by its existing link to missing `config/yazi/plugins/dots-symlink.yazi/README.md`. Every newly added relative Markdown link resolves.
- PowerShell is not installed locally. The separate portable `tools/test_powershell_init.py` reports 3 skips; it needs no Bash, POSIX PTY or symlink privilege. Its adapter and native tests are implemented, but PowerShell execution and native Windows startup remain unverified. No Linux/WSL/native Windows runtime support is inferred from Termux tests.

## Fixture isolation repair

The original theme test fixture copied absolute symlinks unchanged, and two mutation tests wrote through to the live Catppuccin latte/mocha palettes. Both files were restored byte-for-byte from the retained pre-change snapshot, with their previous metadata copied back. The owner's symlink targets were not changed. Comparison of all regular theme files confirmed no remaining content drift.

The new public-tree fixture copier preflights links, rebases repository targets into test-owned roots and rejects external targets before copying. Theme, Zsh and shell-init fixtures use it. Regression coverage verifies that writing through a copied absolute link cannot modify the source. The repaired theme suite passes without changing source palettes.

## Performance

Measurements are native Termux, disposable fixtures, sequential execution and warm caches; they are not platform-wide guarantees. No new cache was introduced.

| Check | Before | After |
| --- | --- | --- |
| Zsh warm startup, initial sequential batches (7 samples each) | 854.3 ms median | 928.5 ms median |
| Zsh warm startup, alternating before/after order (8 samples each) | 941.7 ms median | 949.3 ms median |
| Noninteractive Zsh startup (7 samples each) | 9.39 ms median | 8.47 ms median |

The initial batch difference did not persist in the alternating comparison, whose median difference was 7.6 ms (0.8%). The hook adds a Bash generator invocation; timing variance prevents assigning the entire difference to that invocation.

`tools/bench_bash_dots.py --samples 5` measured initialization medians of 18.45, 16.27 and 17.58 ms with 0, 100 and 1,000 extra extensions. Generation does not scale with extension count. Full catalog enumeration still scales separately, as expected.

Retained local evidence: `/data/data/com.termux/files/usr/tmp/dots-init-before-1sqw58t0` (source snapshot), `dots-zsh-ymd4u1mz/timings.json` and `dots-zsh-0kxxvtmq/timings.json` (initial batches), `dots-zsh-w7eew1o5/paired-timings.json` (alternating runs), and `dots-bash-bench-com_tz58/results.json` (CLI scaling); the latter paths share the same Termux temporary directory. These are untracked local artifacts and may expire.

## Environment alias cleanup

The owner retired the repository-local environment aliases on 2026-09-29. Their exports and legacy Zsh `dot` entries are removed from every native environment loader, together with the associated automatic PATH/fpath insertion. Shared initialization now prepends only existing `DOTBIN` and `DOTSCRIPTS` directories while preserving inherited PATH entries and overrides. No directory removal or live environment mutation is involved.

The existing shell and PowerShell fixtures retain an available repository-local binary directory to verify that initialization no longer inserts it. The audit found no retired variable references in 1,814 source files, including tracked/untracked files and initialized nested repositories. The shell-init reference and README describe the remaining defaults.

Verification on native Termux: shell initialization passed 17/19 with two PowerShell skips; the separate PowerShell runner skipped all three tests because the executable is unavailable. Bash/Zsh/Fish syntax, shared-environment ShellCheck and diff whitespace checks passed. Zsh retains the same two baseline alias failures (15/17 passed). The full documentation gate retains the existing broken Yazi plugin link; changed-document links resolve.

The Bash dispatcher suite also passed all 23 tests. An isolated legacy Zsh environment check confirmed the retired associative aliases are absent and binary/script paths remain available.

## Portable startup through symlinks

**Implemented, 2026-09-29; PowerShell runtime verification pending.** This section supersedes the initial implementation's inherited-path override behavior. The owner selected all six shells, relocation of the complete checkout, and actual-file precedence over inherited Dots paths. Native rc files and loaders resolve their source before loading helpers; they directly source adjacent loaders rather than invoking the CLI. Initialization resets the checkout-derived variables documented in [shell initialization](../docs/shell-init.md). Zsh establishes `ZSH` during early startup. Bash's `BASH` executable variable is not repurposed.

Nushell's linked config uses parse-time physical paths and ignores stale generated hooks; separately and explicitly sourced hooks remain supported. Shared POSIX profiles use an available `DOTS` without guessing its location. PowerShell's native resolver covers file links, parent links, and junctions without Bash. No live link installation, standalone-shell distribution, private-module changes, or publication is included.

The [presentation contract](../docs/presentation.md) remains the acceptance gate: startup and generated code remain quiet and undecorated; errors use stderr. Existing uncommitted refactor work is preserved. Validation covers native startup and direct sourcing, unusual paths, link chains, relocation, inherited-variable conflicts, missing files, loops, reloads and working-directory preservation. Current native Termux evidence:

- `tools/test_shell_init.py`: 29 tests, 26 passed and 3 PowerShell tests skipped. This includes native Bash/Zsh/Fish/Nushell/Xonsh startup through linked entry points. Nushell resolves `path self` with strict `path expand` before computing sibling sources; a lexical source path alone failed the symlink fixtures.
- `tools/test_powershell_init.py`: all 6 tests skipped because PowerShell is unavailable. The portable runner includes file/parent links, relocation, missing layout and a native-Windows-only junction case. Neither PowerShell execution nor native Windows behavior is claimed.
- `tools/test_bash_dots.py`: all 23 tests passed. `tools/test_zsh.py`: 15/17 passed; both alias-expectation failures reproduced against the retained pre-change shell fixture. Its minimal fixture now includes the shared environment and dispatcher file required by startup validation.
- `tools/test_themes.py`: all 27 tests passed against the current working tree.
- Native Zsh PTY startup, reload, completion, directory selection and history selection passed. Hook, FZF, fpath and key-binding state were unchanged on reload. The current fixture includes separately maintained utility code; this result does not attribute those utility changes to shell portability.
- Bash/Zsh/Fish syntax and ShellCheck for the Bash startup/shared-environment files passed. The full documentation gate retains its existing missing Yazi-plugin link; newly added relative links resolve. Whitespace checks passed.

Sequential alternating Zsh startup measurements used 8 samples per version, disposable roots, warm caches and the same then-current `bin/util` in both fixtures (before the [common-helper consolidation](common-helpers.md)) to control for concurrent utility maintenance. Interactive medians were 1,075.7 ms before and 1,038.3 ms after. Noninteractive medians were 11.2 ms before and 13.3 ms after; early startup now resolves/checks the checkout and establishes all derived paths using native operations. These noisy Termux observations are advisory and do not establish desktop performance.

Retained local evidence under the Termux temporary directory: `dots-portable-before-tghzsis_` (initial public source snapshot), `dots-zsh-cp_20c_u` (before fixture), `dots-zsh-muq2jn8h/portable-paired-timings.json` (paired timing samples), and `dots-zsh-datu0hwf/interactive.json` (PTY results). These artifacts are untracked and may expire.
