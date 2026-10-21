# Lean PowerShell profile repair

**Implemented, 2026-10-21.** The initial lean profile was subsequently extended at the owner's request: both Core and Desktop use Starship and their own terminal integration; Blastoff stays Core-only. The original lean measurements below remain a historical baseline.

## Initial implementation

- Preserved the owner's consolidated `profile.ps1` and component deletions; restored the installer-compatible host entry as a wrapper. Existing profile links and Windows app destinations are unchanged.
- Replaced the broken interactive body (missing closing brace at line 119 of the original) and duplicate startup work with one guarded setup. Dots initializes once, preserves prompt exit status and reads published colors without Vivid generation.
- Added explicit optional integrations, lazy fuzzy completion on Alt+F, deferred editor discovery, native listing fallback, nontruncating touch, literal backup paths and Yazi cleanup. Other optional module imports and completion generators remain deferred; the later Starship update is recorded below.
- Fixed native evaluation of the extensionless completion source and avoided exceptions when no theme has been published. Bash routes and shared data formats are unchanged.
- Presentation acceptance follows [the shared contract](../docs/presentation.md): plain directory prompt, native errors, no startup banner, animation or decoration subprocess. No new Dots routes, flags or machine installation operations were added.

## Initial verification

- `python -B tools/test_powershell_init.py`: 15 passed under PowerShell 7.6.7 and 15 passed under Windows PowerShell 5.1.26100.9711. Includes source parsing, direct/linked/junction paths, missing checkout, noninteractive isolation, repeated loading, prompt exit status, theme refresh/last-good data, optional retries/generated-code failure and helper fixtures.
- Native console checks under both engines: input was not redirected, Vi editing was selected, Tab mapped to `TabCompleteNext`, Alt+F mapped to the lazy handler, and the PowerShell error collection was empty. System PSReadLine was used with fixture homes; personal modules were excluded.
- WSL Bash environment/reload and Zsh environment: 3 focused tests passed. The broader shell-environment suite ran 8 tests with 7 assertions failing across Unicode display/wrapping cases and 4 skips. Those failures occur in unchanged Bash presentation code under the fixture locale; they are not evidence of PowerShell failure and are not repaired by this change.
- Relative Markdown links passed (788 links in 107 files), and `git diff --check` passed. Full FZF selection/cancellation, optional third-party integrations and light/dark 40/80/120-column desktop rendering remain owner acceptance checks. No live theme publication, package operation, personal Git operation or profile installation was performed.

## Initial timing evidence

`python -B tools/bench_powershell_profile.py` uses copied public files, isolated homes, one initial sample and ten warm fresh-process samples, sequentially. These measurements use redirected input and exclude PSReadLine, optional integrations and terminal rendering. They are advisory, not full window-opening times.

| Engine / metric | Initial ms | Warm median ms | Warm maximum ms |
| --- | ---: | ---: | ---: |
| PowerShell 7 profile load | 161.74 | 134.67 | 173.90 |
| PowerShell 7 load through first prompt | 166.03 | 138.72 | 177.75 |
| PowerShell 7 whole process | 697.15 | 672.67 | 842.93 |
| PowerShell 7 `-NoProfile` whole process | 571.52 | 545.02 | 568.85 |
| Windows PowerShell 5.1 profile load | 296.61 | 262.63 | 473.74 |
| Windows PowerShell 5.1 load through first prompt | 301.78 | 267.55 | 479.04 |
| Windows PowerShell 5.1 whole process | 617.52 | 577.59 | 924.18 |
| Windows PowerShell 5.1 `-NoProfile` whole process | 449.75 | 429.99 | 499.83 |

The original interactive source does not parse, so no valid before/after startup speedup is claimed. The original personal files were copied to a task-owned temporary recovery directory before edits; the runner never sources the live profile or its hard-coded personal module path.

## Core/Desktop, Starship and Blastoff follow-up

- Both engines' actual all-host profile paths were queried natively. Core's existing link was correct; Desktop's missing all-host link was created using the file transaction store. Both resolve to the repository profile. Desktop's current-host integration file and all existing backups remain unchanged. A repeat plan is a no-op; create/no-op/rollback were exercised in a temporary store.
- Startup initializes Starship once with `--print-full-init`, installs the stable Dots refresh wrapper, then loads the integration file beside the executing engine's all-host profile. Reloading settings never captures an outer terminal wrapper as the renderer. Failure status and native exit codes reach the renderer. Missing/failed Starship uses a plain prompt.
- Both installed integration files had identical SHA-256 values and were left unchanged. Native tests use copies. Core-only optional features refuse Desktop before module import: Blastoff requires 7+, and WinGet CommandNotFound requires 7.4+.
- `BLASTOFF_HOME` defaults to the checkout's `config/blastoff`, with explicit overrides preserved. A read-only `blastoff list --json` through the actual Core frontend and shared profile returned all 27 repository themes with no stderr. No theme selection or Blastoff state was changed.
- Native real-Starship rendering with a synthetic configuration and copied integration succeeded in Core 7.6.7 and Desktop 5.1.26100.9711: one rendered prompt, one OSC start marker, stable wrapper identity after reload, preserved exit code 29, and empty error collections. Job discovery was stubbed to avoid Windows workflow persistence outside the fixture. The live Desktop job query itself passed.
- Current console/keyboard acceptance is pending: the execution tool's PTY launcher resolves to the installed PowerShell Preview app alias and was denied by Windows before process creation. Redirected native checks passed; earlier Vi/keybinding evidence does not establish the full new terminal chain's keyboard behavior.

Current automated acceptance: 20 tests passed on Core 7.6.7 and 20 passed on Desktop 5.1.26100.9711. The tests cover edition guards, correct engine-specific integration paths, generated prompt failure, reload cycles, theme refresh, explicit Blastoff overrides and failure-signal propagation.

Final focused Bash environment/reload and Zsh environment checks passed (3 tests). Relative Markdown links passed (790 links in 107 files), and `git diff --check` passed.

### Follow-up timing evidence

Duplicate-installation correction: the live PATH contained both the Scoop Starship shim and its installed executable. Unbounded `Get-Command` returned an array, causing the invocation error `starship.exe starship.exe`. Prompt discovery, optional initialization and completion generation now request only the first application match (`-TotalCount 1`). A regression test with two fixture executables failed before the fix and passed afterward. All 21 tests passed under both Core and Desktop; both actual installed Starship paths also rendered successfully with isolated configuration and cache directories. Bash behavior and live theme files are unchanged.

The final sequential run used `tools/bench_powershell_profile.py --starship --integration <engine-specific integration file>`, one initial sample and ten warm fresh-process samples per mode. Starship used a synthetic configuration, system PSReadLine, copied terminal integration and stubbed job discovery in isolated roots. Input was redirected; these are not live window-opening times or timings of the personal Starship configuration.

| Engine / Starship metric | Initial ms | Warm median ms | Warm maximum ms |
| --- | ---: | ---: | ---: |
| Core 7.6.7 profile load | 706.89 | 560.16 | 610.36 |
| Core load through first prompt | 884.20 | 746.52 | 808.17 |
| Core whole process | 1333.47 | 1186.96 | 1280.80 |
| Desktop 5.1 profile load | 543.32 | 536.22 | 587.93 |
| Desktop load through first prompt | 743.84 | 729.68 | 791.37 |
| Desktop whole process | 1089.34 | 1080.46 | 1150.40 |

Same-run `-NoProfile` whole-process medians were 452.04 ms (Core) and 373.98 ms (Desktop). Missing-Starship fallback profile medians were 282.45 ms and 993.39 ms respectively. Restricting executable discovery to applications with module autoload disabled did not measurably reduce that fixture's missing-tool latency; no fallback speedup is claimed. The requested automatic integrations add measurable startup work; unrelated optional integrations remain deferred.
