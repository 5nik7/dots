# Decision 0003: picker defaults, human output and PowerShell lifecycle

Status: accepted for the 0.1.8 review build; verification status is in STATUS.md.

Supersedes the 0.1.7 basic-default picker and its bat configuration isolation.
Fancy Unicode is the shared browser default; --fzf requests compatible user
presentation. Preserve numeric-ID selection, fixed source-preview commands,
bounded sanitized output, cancellation and frozen deletion scope. Config parsing
must preserve fzf hex colors; bat owns normal theme/config/cache discovery.
No rendered prompt execution is introduced.

Human output is the default throughout the application. JSON needs explicit
--json; the shared emitter must not guess JSON when a human renderer is missing.
Redirecting human output removes decoration, not its format. Raw content remains
raw where contracted. Diagnostics use stderr.

PowerShell stays a thin PowerShell 7+ frontend to the Python 3.11+ core. A private
versioned argv envelope avoids native legacy quoting loss without eval or global
preference changes. Import/static completion remain free of tool processes.

The root PowerShell lifecycle uses a self-contained CurrentUser module payload,
with a discoverable manifest and independently owned runtime/resources. This
avoids shared-file reference counting with the shell-prefix installation. Both
layouts reuse the same inspect/plan/atomic-write/lock/profile-backup engine.
Exact owned profile integration imports a pinned version. Foreign imports are
conflicts, not automatic migration authority. Modified files and user data survive
uninstall. No dependency downloads or execution-policy changes.

Per-file atomicity and cooperating locks are not a multi-file power-loss
transaction or protection against malicious final-window path swaps. Native
Windows, WSL, PowerShell versions and human visuals require their own evidence.

Compatibility refinement: PowerShell 7.0 Unix without UnixMode uses a bounded
shared-Python filename-only helper on dynamic completion, with an in-memory cache.
This avoids enabling experiments or returning unsafe file kinds; import/static
completion and modern-host filename completion still launch no subprocesses.
