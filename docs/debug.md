# Debugging Dots

`dots debug` lists diagnostics and examples. Inspection never sources a cache,
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
executable shadowing; it observes executables, not parent-shell aliases or
functions. `command` explains longest-prefix resolution in the current default
command roots, selected candidates and the count of forwarded arguments. It does
not print forwarded argument values or execute the selected route. Nonexported
shell state and caller-specific extra command directories are not reconstructed.

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

`--view sequence` is the default. `slowest` sorts paired measurements by inclusive
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
have no invented duration. Nesting describes measured Dots scopes, not a complete
third-party source call tree. Bash and PowerShell report Dots markers only. A
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

Every diagnostic supports `--json`. Records carry `version: 1`; startup reports
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

Traces record source/module names and timing/status metadata only. They do not
enable command xtrace, retain child stdout/stderr, dump environment values, or
record private source contents. Source paths remain visible. Events are bounded
to 10,000 and 8 MiB of retained metadata per run; truncation is explicit. Temporary diagnostic artifacts are
removed after reporting. POSIX runs own a process group; Windows runs own a Job
Object. Cleanup targets those diagnostic children, not existing user sessions.
Normal live hook effects are not transactional or automatically reversible.

Successful inspection/tests return 0, failed checks/execution return 1, invalid
invocations return 2, timeouts return 124, and interrupted traces return 130.

Native PowerShell 5.1/7 Job Object behavior, full profile-chain and terminal
acceptance require Windows checks. Portable/native-controller fixtures on Termux
are not native Windows, Linux or WSL acceptance evidence.
