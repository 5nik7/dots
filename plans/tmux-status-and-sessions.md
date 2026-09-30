# Tmux battery status and named sessions

**Status: Implemented; focused verification passes, with unrelated baseline failures recorded below.** Scoped maintenance; no general CLI migration or battery-repository changes.

## Contract

- Keep the exact blue COPY/PREFIX/ZOOM indicators, then `%H:%M`, two spaces, and the percentage-colored battery icon and percentage. No hostname; retain the five-second refresh.
- A Bash adapter calls `~/repos/battery/battery` once, preserving configured thresholds and charging icons. Translate only its red/yellow/green ANSI output to tmux styles. Missing or invalid output clears the segment without diagnostics. No cache, service, package installation or live-server reload.
- The main tmux config owns `status-right` after the theme include. Generated theme templates must not replace the layout; do not edit existing generated artifacts.
- Shared Bash/Zsh `t [session-name]` infers the Git worktree root's basename when called without arguments, even from nested directories. New inferred sessions start at the root; explicit names bypass detection and use the caller's directory. Missing Git/non-repository directories fall back to Work. Normalize dots/colons/control characters only in inferred names to hyphens. Same resulting names reuse one session; explicit names disambiguate. Attach/create outside tmux; switch/create inside, without nesting or renaming. Exact targeting, quoted arguments, explicit invalid-name refusal, error propagation and legacy-alias reload safety are required.
- Preserve all unrelated working-tree changes and the existing config-directory link.

## Acceptance

- [x] Battery adapter and main/theme configuration agree on layout ownership.
- [x] Bash/Zsh named-session and reload tests pass.
- [x] Isolated battery fixtures cover color, icon, thresholds, failure clearing and single invocation.
- [x] Disposable native tmux verifies config loading, legacy-theme override, asynchronous output and named-session behavior.
- [x] Applicable shell/theme suites, syntax checks and documentation links are checked; unrelated baseline failures are distinguished.
- [x] README, shared shell, architecture and testing documentation reflect implemented behavior.

Apply the [presentation acceptance gate](../docs/presentation.md#acceptance-gate). The adapter is a tmux-format data interface, intentionally colored even under `NO_COLOR`, not human CLI output; no banners, ANSI leaks or unsafe format text. Percentage text preserves meaning without color; Nerd Font glyph appearance needs manual review. Native tests use Termux-owned disposable homes and sockets, never the live tmux server. No desktop or native Windows verification is claimed.

## Repository-aware default follow-up

Requested after initial implementation: plain `t` in this checkout must select `dots`, while explicit arguments still win. Detection is one on-demand Git query, not a startup scan or cache; linked worktrees retain their own names. Shared mock regressions and native Git/tmux fixtures cover these cases. Follow-up verification passes: 19 shared-shell tests, three native tmux tests (Bash and Zsh), and 30 shell-init tests with three existing skips. Bash/Zsh syntax, Bash ShellCheck and `git diff --check` pass. The initial verification record below remains historical.

## Verification record

Native verification ran on Termux. Live reload and visual font review remain manual.

- All 17 shared-shell tests pass, including Bash/Zsh argument, exact-target, failure, race and legacy-alias cases.
- All six status tests pass, including the optional copied upstream battery script with owned PREFIX/API mocks and native tmux rendering.
- Both native session tests pass (6.380 seconds), each exercising Bash and Zsh clients, exact-prefix collisions, attach/create/switch/reuse and working directories.
- Broader suites pass: common helpers (29), shell init (30, three skips), Bash dispatcher (24), Zsh (22), themes (29), theme workflow (22, one skip). Native Bash and Zsh PTY runners pass. Full logs are retained in `/data/data/com.termux/files/usr/tmp/dots-tmux-checks-r71nlkhc`.
- An isolated definition/alias-load microbenchmark used a t-only reconstructed pre-change baseline and seven alternating warm batches of 50 loads per shell, with optional tools disabled. Median milliseconds per load pair: Bash 2.455 before / 2.432 after; Zsh 2.932 / 2.708. These advisory figures show no observed regression, not a speedup claim, full-startup measurement or Android API timing.
- Bash/Zsh syntax, explicit Bash ShellCheck and `git diff --check` pass.
- The global Markdown checker stops on the pre-existing `docs/testing.md` link to `config/yazi/plugins/dots-symlink.yazi/README.md` (also present in HEAD). The other 132 local targets in affected docs resolve.
- The existing tmux-key suite passes 18/19 checks. Its popup test expects blue/cyan, whereas the pre-existing user binding uses brightblack/yellow; neither the binding nor that unrelated test is changed here.
- The first optional upstream battery test inherited the real Termux `PREFIX`, bypassing its PATH mock and timing out during a read-only battery API request. Its owned remaining processes were terminated. The corrected fixture now owns `PREFIX/bin` and kills its complete adapter subprocess group on timeout; all six rerun checks pass.
