# Nested debug reports and shell change tracing

Status: implemented; local Termux acceptance complete, native Windows acceptance pending.

Implement the approved Lazy-style debug hierarchy, opt-in startup state changes,
and opt-in current-session PATH recording. Keep lightweight files-only diagnostics
as the default. Names/actions are retained by default; explicitly selected values
respect sensitivity metadata. Never retain expanded commands or function bodies.

Add tree/filter/detail options, source maps for compiled modules, native shell
adapters, recording start/stop/status code generation, and PATH provenance views.
Distinguish observed intervals, exact markers, inherited unknown history, and
coverage gaps. Preserve existing hooks, exit status, JSON fields and normal startup.

Acceptance: isolated Bash/Zsh and PowerShell-adapter cases; nested sources,
state deltas, PATH history, source maps, secret sentinels, conflicts, limits,
timeout/cleanup, 40/80/120-column rendering, metadata/completion parity, and
sequential startup/recording overhead measurements. Follow the
[presentation gate](README.md#presentation-gate-for-every-plan).
Update authoritative docs and the local wiki. Native Windows PowerShell 5.1/7
acceptance remains pending without the native engines. No live traces, recording
activation, commits or pushes are part of implementation verification.


## Verification (2026-10-25)

- Detailed tracing: 15 tests, 14 passed and one unavailable PowerShell test skipped.
  Includes Bash/Zsh state categories, redaction, nested observations, source maps,
  malformed/nonregular maps, limits, recording restart/stop and normal exit cleanup.
- Existing profile-debug checks: 14 passed and one PowerShell skip. The added
  debug completion parity case passed separately on Bash and the native controller.
  Existing PTY cases cover 40/80/120 columns, plain/color/icon modes and control text.
- Dispatcher: 24 passed; native controller: 13 passed, one PowerShell skip;
  resources: 15 passed; profiles: 13 passed; shell environment: 9 passed.
- Both command validators accept 136 external routes. Python parsing, Bash/Zsh
  adapter syntax, relative Markdown links and whitespace checks passed.
- The broad shell-init suite is not green: two assertion failures reproduce with
  original HEAD startup files copied into owned fixtures (optional Bash activation
  and Zsh private-hook/reload theme expectations). Five error records involve the
  installed Xonsh launcher whose interpreter is absent. These are separate from
  this change's focused acceptance. Native Windows PowerShell 5.1/7 and native
  Linux/WSL runtime acceptance remain pending.

Sequential seven-sample warm public-fixture benchmarks, in milliseconds:

| Shell | Without diagnostic calls | Disabled tracing |
| --- | ---: | ---: |
| Bash | 216.082 | 192.576 |
| Zsh | 138.800 | 141.315 |

A separate seven-sample run with `tools/bench_debug_startup.py --recording`:

| Shell | Disabled tracing | PATH recording |
| --- | ---: | ---: |
| Bash | 196.611 | 641.205 |
| Zsh | 134.046 | 464.146 |

These are noisy local process medians, not cross-platform performance guarantees.
Default startup shows no consistent regression; enabled native command hooks add
substantial cost and remain opt-in. Full public boundary-change and PATH-only deep
traces complete on Bash/Zsh. All-category deep public startup can exceed the
30-second default and returns explicit partial timeout evidence. Use narrower
capture categories or an explicitly larger timeout for those diagnostics.

Canonical docs and local wiki export are updated together. No live personal trace,
session activation, commit or push is part of this verification.
