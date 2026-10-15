# Shared Codex syntax theme

**Status: Implemented and activated on native Termux, 2026-10-14.**

## Design

- Name the selectable theme `dots` and follow the active Dots palette.
- Reuse `default/themed/bat.tmTheme.tpl` and the rendered `bat.tmTheme` shared with Yazi.
- Connect an existing `${CODEX_HOME:-$HOME/.codex}/themes/dots.tmTheme` through the current journal. Validate absolute homes without control characters or dot components; skip missing themes directories.
- Preserve Codex settings during publication and the existing Neovim color-query adapter. Codex-Termux needs no source change.
- Activate locally only after isolated validation: privately record directory creation and back up configuration, publish the current palette, then set only `tui.theme = "dots"` with drift checks. Keep records outside Git.
- No new route, completion grammar, model/auth setting, desktop theme, restart or wrapper release.

## Verification

- [x] Shared plist/all palettes, default/custom paths, absence, conflicts, override refresh and idempotence.
- [x] Backup, rollback, interrupted recovery and drift refusal.
- [x] Theme/workflow/dispatcher suites, isolated Neovim color test, native Codex custom-theme discovery (timeout finding below).
- [x] Documentation links, syntax and whitespace checks (pre-existing findings below).
- [x] Local activation and read-only confirmation.

## Presentation gate

Follow the [presentation contract](../docs/presentation.md#acceptance-gate): reuse connector preview/error rendering; check plain and forced-color paths with spaces, Unicode and leading-dash components. Scalar/generated APIs remain unchanged. No new help/list UI is introduced. Record native loader evidence separately from visual appearance and other-platform limitations.

## Evidence and limits

- Five focused Codex workflow cases pass, including all bundled palette renders.
- Dispatcher: 24 tests pass. Existing Neovim color probe: 85 assertions pass, including real PTY replies, under an isolated home with no LazyVim startup.
- Installed Codex 0.162.1 was launched in an owned PTY with a disposable home and loopback-only provider, no real credentials and no model prompt. `/theme` displayed `dots (custom) (current)` and selection persisted as `tui.theme = "dots"`. This confirms native custom-theme discovery/loading; it is not a full visual-contrast review or a hot-reload guarantee.
- Bash syntax and whitespace checks pass. ShellCheck reports only SC2015 on the existing connector preparation guard, also present in HEAD.
- Full Markdown audit: 588 links, one pre-existing broken `docs/testing.md` link to the removed Yazi `dots-symlink.yazi` README. All newly added links resolve.
- Workflow: 27 tests ran, 26 passed and the optional Pi native-loader check skipped. Shared themes: 28 passed, with the all-family Neovim case timing out at its existing 40-second limit. The same timeout reproduces with the original HEAD connector code substituted only inside a disposable fixture; the same case passes in 36.8 seconds with a diagnostic-only 90-second subprocess allowance. Repository test limits are unchanged. Local activation completed: the current Catppuccin Mocha generation published successfully, the connector resolves to the shared syntax artifact, and only `tui.theme` changed from `ansi` to `dots`. A private configuration backup and recovery record remain outside Git. Config and backup modes are 0600; the recovery directory is 0700. Existing unrelated Dots and Neovim changes remain intact. Native desktop/WSL/Windows appearance is unverified.
