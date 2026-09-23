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
