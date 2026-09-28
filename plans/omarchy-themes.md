# Omarchy-style themes

**Status: Implemented; isolated verification recorded in docs/testing.md**

- [x] Flatten palettes and import Omarchy colors and backgrounds.
- [x] Render default/themed and personal templates into immutable generations.
- [x] Publish the stable XDG state dots/current/theme path and connect applications.
- [x] Preserve legacy APIs; add singular routes, Git lifecycle and explicit wallpapers.
- [x] Validate publication recovery, application outputs and compatibility.

Go implementation remains paused. No commits, pushes, package installation or live theme/wallpaper activation are included. Existing user changes and independent submodule histories are preserved.

The contract is in [docs/themes.md](../docs/themes.md) and decision 0008. Native
Termux fixture checks cover all 33 selections, compatibility, state recovery and
application data. Android/desktop wallpaper APIs use fake adapters in tests; actual
wallpaper rendering and native desktop application reloads remain unverified.
No real theme or wallpaper was selected during implementation.

## Terminal presentation follow-up (2026-09-24)

Implemented colored human output using the dispatcher's color/icon policy, static
subcommand menus and terminal-aware layouts. Plain pipelines, JSON, scalar/path
queries, initialization and completion retain their data contracts. Validation is
recorded in [testing](../docs/testing.md#terminal-presentation).

## Presentation Acceptance for Follow-up Work

Future theme and wallpaper changes must meet the [presentation contract](../docs/presentation.md) and its acceptance gate. Keep list/detail, preview, selection, import/update/remove and failure messages cohesive. Palette swatches show theme colors while diagnostics retain shared semantic roles; preserve scalar queries, generated initialization, app configuration and legacy APIs.

## FZF and Gum templates (2026-09-28)

Scope: connect `fzf.sh.tpl` to published shell initialization, and retain `gum_env.lua.tpl` for explicit loading in Hilbish. Preserve palette mappings and template filenames. Read FZF assignments as restricted literal data; render Gum with Hilbish's `os.setenv` API without executing Lua during publication. Keep existing template precedence and transaction boundaries. No live activation, Hilbish configuration installation, package installation or Go work is included.

- [x] Validate FZF assignments before publication; emit Bash/Zsh and Fish initialization. Render the Gum Lua consumer separately.
- [x] Use the generated FZF palette during shell refresh, preserve non-color options and prevent duplicate color flags. Keep the legacy fallback for unpublished/session-only themes.
- [x] Verify template overrides, refresh, invalid-input refusal and shell consumption in isolated roots; record native runtime and performance evidence.
- [x] Update theme documentation and README. Apply the presentation gate above to generated app colors and preserve undecorated initialization output.

Verification and advisory timings are recorded in [testing](../docs/testing.md#files-catalog-and-omarchy-style-themes). The new focused checks pass; existing theme-count and Zsh alias failures reproduce with original code. Gum remains Hilbish-only per owner direction; native Hilbish execution is unverified because the executable is unavailable. No live theme was selected.
