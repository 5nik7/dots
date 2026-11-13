# Git output modes and shared progress

**Status: Implemented and locally verified; native host checks remain pending.**

Approved scope: the whole Git family, including named/collection submodules and Wiki routes, gains default/short/verbose human views. `apps.git.view` defaults to `default`; `--view default|short|verbose`, `-s`/`--short` and `-v`/`--verbose` override it. Tree `--details` remains a verbose compatibility spelling. Conflicting selectors are errors. Saved views apply to terminals/menu captures; ordinary redirected text retains its existing layout unless a view is explicitly selected. JSON and operation events remain unchanged.

Default status has a compact repository header and one readable file list, combining index/worktree states and rename paths. Short uses XY rows. Clean repositories remain one line. Verbose adds metadata and action detail, never patches. Info/tree retain their domain structure. Publish lists selected files once during review, then progress/outcomes; sync lists actual changed paths once after each update. Blockers and recovery guidance stay visible in every view. Presentation does not change approvals, Git safety checks, traversal or mutation order.

`apps.cli.progress` defaults to `both` and controls existing shared consumers. Modes: none (no display), spinner (spinner plus real counts when known), bar (counted or indeterminate bar), both (spinner and counted bar when known, spinner otherwise). `DOTS_PROGRESS=auto` follows Config; `never` aliases none; explicit mode names override Config. Keep 500 ms delay, terminal gates, data/dry-run suppression, prompt/child suspension, interruption cleanup and inert phase labels. Counts represent processed work, not success. No transfer-percentage parser or persistent cache is added.

Dependencies: implement Config/policy and shell projections first; then Git presentation projections and operation integration; then isolated acceptance and documentation. Git maintenance owns command behavior; Config and CLI presentation own preferences/progress. Configuration assessment: add both controls to existing inheritance, constraints, completion, browser and next-invocation activation. Reuse Git/file/UI styles and CLI layout. Menu assessment: existing report entries consume the saved view and Config exposes controls; no new launcher is needed. Installer assessment: existing checkout-linked/native launchers deliver helpers/defaults; no new component or Windows destination is required.

Acceptance: all three views across Bash/Python controllers and routed aliases; exact legacy redirects and JSON/events; partial staging, renames, conflicts, missing/duplicate/detached/unborn repositories and gitlinks; one file row per repository/path; all progress modes, real/unknown totals, nesting, prompts, interruption and renderer failure; Config save/reset/override and startup invalidation; six-shell completion; 40/80/120-column light/dark owned PTYs and long/Unicode/control paths. Run affected Git/native/submodule/Wiki/progress/Config/startup/completion suites sequentially in owned roots and local bare remotes. Measure before/after representative status trees. Native Windows PowerShell 5.1/7 and Linux/WSL evidence remains explicitly pending when unavailable.

Update README, canonical Git/command/presentation/configuration/data/testing references and available generated Wiki. Preserve unrelated work. No live Git mutation, commit, push, installation or application reload is part of implementation verification.

## Verification evidence

All mutations in acceptance used disposable repositories and local bare remotes. No live repository synchronization/publication, application reload, commit or push was performed. Initial completed suites: Git operations 27/27; native Git 24/24; Git platform 6/6; Wiki Git 11/11; Config values 18/18; native Tab completion 5/5; shell init 31 cases with 3 availability skips; Bash dispatcher 32/32; package styles 3/3. The package publication suite verifies manifest selection once in the human review while retaining its original JSON events.

The broad submodule suite has five existing failures: connected-tree Reason indentation (both frontends), ownership fixture configuration (both frontends), and the native fixed-ANSI pending assertion. Shared-shell tests have five existing bootstrap/alias failures. Package publication has one existing Windows-refusal fixture failure (missing active profile is rejected first). All eleven reproduce with the pre-change HEAD source snapshot; they are not silently counted as passing and remain outside this change. The snapshot omits external installation symlinks and uses only test-owned homes, state and repositories.

Final focused Git display checks cover seven cases across both controllers, including dark/light 40/80/120-column PTYs, six-shell completion records and an unavailable post-sync file report that preserves the completed update. The package publication case also verifies manifest deduplication. Progress passes 14/14, style/configuration startup passes 9/9, and common Bash/Zsh helpers pass 29/29. The compiled preference test changes both new defaults, then proves the warm bundle works with a Python executable that deliberately fails. Python/Bash parse checks, focused ShellCheck (external-source warnings excluded) and `git diff --check` pass. Native Windows PowerShell 5.1/7 and native Linux/WSL terminal acceptance remains pending; local controller/PTY evidence does not substitute for those hosts.

## Status timing observations

Three warm samples per view, run sequentially on Termux with test-owned repositories/homes and no live remotes. Before is the pre-change source snapshot. Legacy is current redirected text; Default/Short explicitly select their human layouts while capturing output. All eight repository/file/controller combinations produced byte-identical legacy text and JSON against Before. These are command observations, not cold-start or cross-host performance guarantees. No cache or per-file formatter process was added.

Times below are median milliseconds. File counts are additional untracked files; the 5/10-repository cases have clean nested submodules.

| Controller | Repositories | Files | Before | Legacy | Default | Short |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bash | 1 | 0 | 870.3 | 584.3 | 587.3 | 659.0 |
| Bash | 5 | 0 | 1761.9 | 1632.0 | 1578.6 | 1601.2 |
| Bash | 10 | 0 | 3131.1 | 3610.3 | 4361.6 | 3123.7 |
| Bash | 1 | 500 | 1375.5 | 1255.0 | 1687.6 | 1695.2 |
| Python | 1 | 0 | 442.4 | 332.3 | 456.1 | 402.1 |
| Python | 5 | 0 | 1418.0 | 1360.1 | 1454.3 | 1377.3 |
| Python | 10 | 0 | 3521.7 | 3539.2 | 3513.2 | 3780.9 |
| Python | 1 | 500 | 497.2 | 544.8 | 539.3 | 541.5 |

Explicit Bash file views add complete-value wrapping/resource layout work compared with the old redirected fast path (about 0.31 seconds for 500 files in this sample). The native 500-file samples overlap. The noisy 10-repository Bash result is checked with alternating Before/Default runs below; no speedup is claimed.

Alternating 10-repository Bash verification (one warm-up pair excluded): Before samples 2988.3/2904.3/2848.4 ms, Default 2710.9/2819.1/2855.0 ms; medians 2904.3 versus 2819.1 ms. The earlier slow Default sample did not repeat. No meaningful discovery regression was established; these timings remain host/load observations.

## Documentation delivery

Canonical README, Git/command/configuration/presentation/data/testing/PowerShell references and plan indexes are synchronized. The initially clean local Wiki was previewed and rebuilt with transaction `da073be75ba344f497331f595869ddf3` (9 generated/manifest files); its freshness check passes. Relative Markdown validation passes 1396 links in 173 files. No documentation commit or publication was performed.
