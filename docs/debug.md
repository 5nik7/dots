# Debugging Dots

`dots debug` lists diagnostics and examples in a nested tree. Human reports use depth markers, resource icons, semantic colors and wrapped paths, with ASCII/plain fallbacks. Inspection never sources a cache,
executes a discovered command, repairs configuration, or activates a profile.

```sh
dots debug check
dots debug check --only startup
dots debug path bat
dots debug command -- profile paths --kind bin
dots debug cache --shell zsh
dots debug test --list
dots debug test startup
```

`check` groups platform, profile, command, startup, and environment checks.
`path` explains inherited PATH order, missing directories, duplicates and
executable shadowing; optional session evidence adds change history; it observes executables, not parent-shell aliases or
functions. `command` explains longest-prefix resolution in the current default
command roots, selected candidates and the count of forwarded arguments. It does
not print forwarded argument values or execute the selected route. Without an opted-in recording or explicit child trace, nonexported shell state and caller-specific extra command directories are not reconstructed.

`cache` reads generation manifests and input metadata. It does not execute guard
scripts or rebuild caches. Old generations without comparable metadata are
reported as needing verification/preparation. A valid report covers recorded
input metadata; the native loader additionally checks its own shell version and
runtime guards. `check` treats malformed caches as failures and reports ordinary
staleness as a need for normal startup preparation.

## Startup order and timings

```sh
dots debug startup --shell zsh
dots debug startup --shell zsh --isolated
dots debug startup --shell zsh --live
dots debug startup --shell zsh --live --view slowest
dots debug startup --shell bash --isolated --runs 5 --view summary
dots debug startup --shell zsh --live --login --timeout 60
dots debug startup --shell powershell --isolated --json
```

Without `--live` or `--isolated`, this command explains declared Dots module
traversal without executing startup. Conditional branches are shown as potential
modules; this is not an observation of the caller's complete rc chain.

`--live` launches a child shell through its normal interactive startup. This
executes the usual private hooks, tool/plugin initialization, cache preparation
and any other startup side effects. The command does not edit startup files or
clear caches. `--login` additionally enables POSIX login initialization; it is
rejected for PowerShell. The configured startup might initialize a different
checkout; emitted source paths identify what was actually loaded.

`--isolated` uses a disposable public checkout and owned HOME/config/state/cache
roots, excludes private modules and profile hooks, and exposes a controlled set
of tools. Optional plugins, downloads and device services are absent. It models
Dots startup rather than the developer's complete configuration. Bash fixtures
suppress system profiles and explicitly load their owned login file when requested; Zsh fixtures suppress optional global rc files.

Shell selection prefers an identifiable invoking Bash/Zsh/PowerShell process,
then the configured supported login shell, then Bash on POSIX or PowerShell on
Windows. `--shell` selects explicitly; the report always identifies the shell.
PowerShell uses installed `pwsh` first, otherwise `powershell`.

`--view tree` is the default; `sequence` remains its chronological compatibility alias. `slowest` sorts paired measurements by inclusive
duration; `summary` shows totals. `--runs` accepts 1–20 sequential runs (default 1),
with median/min/max over available startup measurements. `--timeout` accepts
1–300 seconds per run (default 30). A failed, timed-out or interrupted run stops
further samples and retains completed events. Runs reuse the fixture cache;
initial preparation and later warm starts remain distinguishable in events.

The timeline distinguishes:

- **Inlined:** original authored modules inside a generated Bash/Zsh bundle.
- **Source:** instrumented runtime imports, including private-hook boundaries.
- **Phase:** startup, preparation and selected plugin/prompt-hook setup.
- **Source-entry:** Zsh's native filename-only source observations.

Paired native markers supply inclusive elapsed times. Parent/child times overlap
and must not be added. Zsh source-entry timestamps are observer timestamps; they
have no invented duration. In default files mode, nesting describes measured Dots scopes, not a complete third-party source call tree. Bash and PowerShell default to Dots markers. Deep Bash/Zsh tracing additionally reports observed native file scopes with explicit approximate interval timings. A
missing marker or early return remains incomplete. A nonzero module return is
reported separately from the child shell's overall failure; optional tools often
return nonzero without aborting startup.

Startup time ends at the command immediately after rc processing. Process time
also includes shutdown and diagnostic cleanup. Streams are redirected and prompt
rendering is excluded: terminal-dependent initialization can differ from a real
terminal session. Instrumentation adds overhead; these are diagnostic timings,
not an uninstrumented benchmark. Shell timestamps use their native clock; negative
clock adjustments do not produce an elapsed measurement.

## Output and self-tests

Diagnostic reports support `--json`; recording start/stop instead emit exact native shell code for explicit evaluation. Records carry `version: 1`; startup reports
include mode, shell, individual runs, events, coverage and summary measurements.
Event records include name, kind, offset, optional duration, nesting, status and
process identity. Source offsets identify observer versus shell timestamps.
Human views use the shared Dots renderer and resource styles, wrapping complete
paths at narrow widths. Color/icon settings never decorate JSON.

The `profiles`, `environment`, `dispatch`, and `startup` self-test suites use
runtime-owned fixtures. Bare `dots debug test` runs all four sequentially. They
are a small diagnostic check, not unrestricted discovery of repository tests.
Unavailable optional native shells are reported as skipped. Test output contains
named cases, elapsed time, status and a readable explanation.

Files-only traces retain source/module names and timing/status metadata. Detailed traces add sanitized state changes. They never enable command xtrace or retain child stdout/stderr, function bodies or alias expansions. Selected non-sensitive scalar values require explicit `--show-values NAME`; sensitive names/private-hook metadata remain redacted. Source paths and PATH entries remain visible. On Bash/Zsh, raw native declarations cross only an anonymous pipe into the parent’s bounded in-memory comparison; they are never written to trace files. PowerShell compares definitions in memory before writing sanitized records. Events and changes share a bound of 10,000 records and 8 MiB of retained metadata per run; truncation is explicit. Temporary diagnostic artifacts are
removed after reporting. POSIX runs own a process group; Windows runs own a Job
Object. Cleanup targets those diagnostic children, not existing user sessions.
Normal live hook effects are not transactional or automatically reversible.

Successful inspection/tests return 0, failed checks/execution return 1, invalid
invocations return 2, timeouts return 124, and interrupted traces return 130.

Native PowerShell 5.1/7 Job Object behavior, full profile-chain and terminal
acceptance require Windows checks. Portable/native-controller fixtures on Termux
are not native Windows, Linux or WSL acceptance evidence.


## Detailed startup changes

```sh
dots debug startup --shell zsh --isolated --detail changes
dots debug startup --shell zsh --live --detail deep --changes path,aliases,options
dots debug startup --shell zsh --live --detail deep --changes variables --name 'EDITOR' --show-values EDITOR
dots debug startup --shell bash --isolated --detail deep --file '*environment*' --depth 4 --limit 100
```

`--detail files` is the lightweight default. `changes` compares visible state at instrumented boundaries; `deep` observes native execution locations between commands. `--changes` selects comma-separated `path,variables,functions,aliases,options` (all by default). Selecting fewer capture categories reduces diagnostic cost. Full deep state capture can be very expensive on large startup chains; retain the default 30-second bound or explicitly increase `--timeout` up to 300 seconds. These timings include observer work and must not be compared as ordinary startup benchmarks.

Changes include variable creation/change/removal and attributes, function/alias creation/redefinition/removal, options and PATH additions/removals/reordering/deduplication. Volatile shell internals and observer implementation state are excluded. Variable snapshots describe visible state; entering or leaving local scopes can change visibility without executing `unset`, and scope transitions are marked. Function bodies and alias expansions are compared privately and never displayed. `--show-values NAME` is repeatable and applies only to selected non-sensitive scalar variables; arrays and other non-scalar values are omitted. Values use bounded native representations, which are data and are never evaluated.

Bash and Zsh debug hooks provide observation intervals, not a guarantee of a hook for every language construct. In particular, Bash function definitions need not trigger a DEBUG callback. Reports show the interval’s start and observation endpoint instead of assigning an invented exact line. Compiled bundles have an inert source map for unchanged authored lines; unmatched generated lines retain their generated location. Measured module timing and observed native-scope timing remain distinguishable. Self-time appears only where paired children permit subtraction; inclusive parent/child times must not be summed.

`--file GLOB` and `--name GLOB` are repeatable human-view filters. `--min-ms N` filters short timing rows while preserving ancestors and matching changes. `--depth N` and `--limit N` collapse displayed rows with a count. JSON retains the full bounded capture and summary, independent of display filters.

Observers begin at the earliest supported Dots entry point. Earlier global/user initialization is outside coverage. Deep tracing refuses conflicting debug instrumentation and reports a missing/replaced observer. It preserves existing traps instead of silently replacing them. PowerShell compares supported global primitive/environment variables, function/alias definitions and preference settings; deep breakpoints cover script files registered at Dots boundaries. Dynamic files outside those boundaries, opaque objects and function-local PowerShell state are not claimed as complete coverage. Adapter capabilities identify whether native line observations were actually seen. Native PowerShell runtime acceptance remains pending when its engine is unavailable.

## Current-session PATH history

An external executable cannot install a hook into its parent shell. Start and stop therefore print native code, just like shell initialization:

```sh
# Bash or Zsh: select the shell you are currently using.
eval "$(dots debug record start --shell zsh)"
dots debug path
dots debug path --history
dots debug path bat
dots debug path --entry "$HOME/.local/bin"
eval "$(dots debug record stop --shell zsh)"
dots debug record status --json
```

For PowerShell, dot-source the generated script block in the current scope:

```powershell
. ([scriptblock]::Create((dots debug record start --shell powershell | Out-String)))
dots debug path --history
. ([scriptblock]::Create((dots debug record stop --shell powershell | Out-String)))
```

Alternatively set `DOTS_DEBUG_RECORD=path` before a new Dots shell starts. This is opt-in; no setting is installed automatically. Only PATH remains recorded after startup. Full variables/functions/aliases/options capture is confined to explicit startup diagnostics.

Recordings contain PATH snapshots and observed location/time metadata. Entries present before recording are labeled **inherited; origin unknown**. Recognizing a profile directory indicates ownership, not proof of its history. Repeated/empty entries and reorder/deduplication operations remain visible. A recording never treats a subshell’s PATH as the parent’s PATH. `status` reports the last recorded state; a child CLI cannot independently verify the parent’s currently installed hooks. If current PATH differs from the last snapshot, the report explicitly identifies unrecorded changes.

Stopped history remains readable until normal shell exit. Private temporary files are deleted on normal exit, and dead-owner/missing references are treated as stale. Abrupt termination can leave disposable temporary files. The recording is bounded to 10,000 changes and approximately 8 MiB, with an explicit limit marker that remains visible after stopping. Repeated stop is harmless, and starting again resumes a new observation interval without filling in the stopped gap. Existing incompatible debug/exit hooks prevent activation rather than being overwritten.

For a fresh startup reconstruction instead of current-session history:

```sh
dots debug path --shell zsh --isolated --history
dots debug path --shell zsh --live --history
```

These commands explicitly run a child with PATH-only deep observations. The result identifies the child mode and never claims to reconstruct unrecorded parent history. Normal `dots debug path` remains read-only and does not launch a shell.
