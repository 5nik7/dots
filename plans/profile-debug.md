# Profile inspection and debug toolkit

**Status: Implemented; native desktop acceptance pending.**

Implement the approved read-only profile routes and `dots debug` toolkit. Reuse
shared resolvers, metadata and presentation; keep machine output undecorated.
Bare startup diagnostics explain the declared sequence. `--live` explicitly runs
normal startup and its side effects; implementation testing uses only disposable
public fixtures. Source and phase events contain no command arguments, values or
private contents. Native Windows uses PowerShell adapters without Bash.

Acceptance covers profile selection/inheritance/validation, PATH and dispatch
resolution, cache changes, secret sentinels, timing attribution, nested and repeated
sources, failure/interruption/timeouts, command and completion parity, and human
views at 40/80/120 columns. Measure disabled startup instrumentation sequentially.
Preserve existing migrations and unrelated edits. No activation, package changes,
profile management, automatic repair, commit or push is part of this work.

Native Windows PowerShell 5.1/7 process ownership, normal profile-chain execution,
and terminal acceptance remain pending when unavailable. Linux/WSL fixtures are
not native execution evidence. Instrumented startup uses redirected streams and
excludes prompt rendering; terminal-dependent startup can differ.


## Termux verification (2026-10-24)

- New diagnostic suite: 14 passed, one unavailable PowerShell engine skipped.
  Includes owned 40/80/120-column PTYs, color/plain output, Unicode and escaped
  controls; nested/repeated sources, early exit, timeout and interruption; JSON
  and raw-path boundaries; Bash and native completion and dispatch.
- Existing suites: 13 profile tests, 9 environment tests, 24 dispatcher tests,
  and 13 native-controller tests passed (one native-engine skip). Three focused
  Bash/Zsh environment and reload checks also passed.
- Curated runtime suites (`dots debug test`): all four passed in owned fixtures.
- Both command validators recognize 116 routes. Focused shell syntax/ShellCheck,
  changed Python syntax, whitespace and relative Markdown links pass.
- No live startup was executed. Native Windows PowerShell 5.1/7, desktop Linux,
  WSL and actual light/dark terminal acceptance remain separate pending checks.

## Disabled instrumentation measurement

`python3 -B tools/bench_debug_startup.py` compares the same public fixture with
instrumentation calls removed against disabled instrumentation. It is a controlled
comparison, not a reconstruction of all historical checkout changes. Seven warm
samples run sequentially in alternating order; optional plugins are absent.

| Native shell | Calls removed | Tracing disabled |
| --- | ---: | ---: |
| Bash | 168.242 ms | 169.202 ms |
| Zsh | 110.845 ms | 112.928 ms |

Inactive markers use a native no-op function; they open no channel and start no
tracing process. Enabled traces include measurement overhead and must not be
presented as uninstrumented startup benchmarks. Native desktop timings are pending.
