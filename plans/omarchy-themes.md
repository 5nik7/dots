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
