# User-local shell completions

**Completed, with native-platform and pre-existing regression limits recorded below.** The owner selected user-local directory precedence on 2026-10-23. This is bounded personal shell maintenance.

## Scope and behavior

- Register the existing XDG Zsh site-functions directory after plugin setup, before compinit, and on completion refresh; deduplicate fpath and export FPATH. Remove the repository completion directory's explicit executable PATH insertion.
- Preserve caller-supplied Bash completion bases in order, append the existing XDG user base if absent, and place optional Termux Androidots last. Keep bash-completion lazy loading and its default base when unset.
- Order Fish's existing user config and user vendor completion directories before Androidots, repository and remaining native paths. Preserve native fallback order and deduplicate on reload.
- Keep generic hooks, noninteractive startup, explicit tool-generated registrations and executable directories unchanged. Do not install completion files, restore backups, create completion directories, initialize optional repositories or reload live shells.
- PowerShell, Nushell and Xonsh retain native integrations. No equivalent Zsh fpath change applies to Windows PowerShell; Windows app destinations are unchanged. Native Windows PowerShell 5.1/7 startup acceptance remains pending on a Windows host.

The durable contract is [local completion directories](../docs/shell-init.md#user-local-completion-directories). This change has no new human output or data interface; the [presentation gate](README.md#presentation-gate-for-every-plan) is inapplicable to rendering. Paths and completion results remain literal and undecorated.

## Acceptance

- [x] Inspect current checkout, active configuration links, native loader behavior and optional Androidots boundary.
- [x] Implement fixed-path registration and user-local precedence.
- [x] Verify actual native discovery, collisions, fallback, missing paths, custom XDG roots, spaces/Unicode, idempotence, exported FPATH and noninteractive boundaries in owned fixtures.
- [x] Run affected regression suites, syntax and documentation checks; record startup measurements and platform limits.

## Evidence

Before-change medians from seven sequential warm samples in disposable roots with minimal tools and no Zsh plugins: Bash 104.080 ms, Fish 57.500 ms, Zsh 444.247 ms. These are native Termux measurements without a PTY, not desktop or Windows evidence.

Focused checks: `test_local_completions.py` 6/6, `test_termux_geo_shells.py` 6/6, `test_shell_environment.py` 8/8, and `test_bash_dots.py` 24/24 pass. Bash/Zsh/Fish syntax, Bash ShellCheck, whitespace and documentation links pass. Bash PTY acceptance passes reload equality, status preservation, history picker, vi cursor and Tab completion.

Broader checks are not all green: Zsh has 28/29 passing (the theme fixture omits `default/file-colors.toml`); shared shells have 15/19 passing (four older generic-hook expectations); shell-init has two assertion failures, five Xonsh launch errors and unavailable-runtime skips across 30 tests. All seven assertion failures reproduce with the four changed production files restored from HEAD only inside disposable fixtures. The Xonsh launcher requires an unavailable interpreter; PowerShell is absent. These unrelated suite limitations are retained, without widening the completion-path change.

After-change medians using the same seven-sample procedure: Bash 111.102 ms (+7.022 ms), Fish 59.977 ms (+2.477 ms), Zsh 447.263 ms (+3.016 ms). The change adds fixed directory checks and short native path-list operations, with no new subprocesses or directory scans. These small sequential samples are observations, not a speedup claim or a cross-platform performance guarantee.

Zsh PTY acceptance also passes Tab/FZF-tab, directory completion, history picker and reload equality for hooks, fpath, FZF settings and keys. Native Termux PTY evidence is retained in the test-owned `interactive.json` files under `/data/data/com.termux/files/usr/tmp/dots-zsh-x8ly4yf7` (Bash) and `/data/data/com.termux/files/usr/tmp/dots-zsh-ev_ou7p_` (Zsh); temporary evidence may expire. The final local-completion suite is 6/6 after all source edits. No live shell was reloaded, no completion file was installed or restored, and Androidots has no changes.
