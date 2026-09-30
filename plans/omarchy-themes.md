# Omarchy-style themes

The theme CLI is now consolidated under `dots theme`; see the [migration plan](theme-cli.md) and [current command contract](../docs/themes.md#migration-from-plural-commands). Earlier compatibility and test results below describe their original scope.

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

Verification and advisory timings are recorded in [testing](../docs/testing.md#files-catalog-and-omarchy-style-themes). The new focused checks pass; existing theme-count and Zsh alias failures reproduce with original code. At that stage Gum was Hilbish-only per owner direction; native Hilbish execution is unverified because the executable is unavailable. No live theme was selected.

## Gum without Hilbish (2026-09-28)

Owner-requested follow-up: replace `gum_env.lua.tpl` with `gum_env.sh.tpl` for explicit Bash/Zsh sourcing. Preserve all 116 palette mappings, bundled/personal override precedence and fingerprint refresh. Dots renders the shell file without executing it or adding it to automatic initialization. Existing Lua overrides are not converted automatically. The presentation gate above applies to the preserved app colors and undecorated exports.

- [x] Convert the template and update bundled override discovery/fingerprinting.
- [x] Verify Bash/Zsh exports, reload, overrides and publication-time nonexecution in disposable roots.
- [x] Synchronize usage, architecture, safety and verification documentation.

Verification: all three focused workflow checks and all 23 shared-theme tests passed on native Termux. The complete workflow suite passed 12/14 with the two previously documented theme-count failures. All 116 mappings match the former Lua template. Shell syntax, documentation links and whitespace checks passed; no live theme was activated. See [testing](../docs/testing.md#files-catalog-and-omarchy-style-themes).

## Gum-first theme picker (2026-09-28)

Owner-approved scope: establish Gum as the preferred optional interaction tool and implement `dots theme switcher` with Gum, FZF and numbered-menu backends. Selection leads to palette review and Back/Apply/Cancel; only Apply calls the existing publisher. Preserve explicit Gum environment loading, scripting interfaces, the earlier shell-template work and the paused Go boundary. The presentation acceptance gate above applies at 40/80/120 columns, with plain/color/icon modes and native versus fixture evidence distinguished.

- [x] Add a lazy shared interaction adapter and the theme review loop.
- [x] Test backend preference, review/apply, cancellation, errors, noninteractive refusal and presentation controls in owned roots; exercise installed Gum in a native PTY.
- [x] Update the authoritative presentation convention, contributor pointers, command metadata and behavior/safety/testing documentation.

Compatibility finding: Gum 2.0 returns 1 for both Escape cancellation and runtime errors. Preserve that ambiguous status instead of masking tool failures as cancellation; Ctrl-C retains 130. Explicit Cancel returns 0; plain-menu Escape/EOF returns 130. No failure starts a fallback backend or publishes a theme.

Completed evidence: picker checks passed 14/14, including native Gum 2.0.0 and
FZF PTY interaction; shared-theme and Bash dispatcher suites each passed 23/23.
Workflow checks passed 12/14 with the two existing theme-count expectations.
A 40-column native transcript review, shell syntax, focused ShellCheck, relative
links and whitespace checks passed. No live state was activated. Full coverage
and platform limits are recorded in [testing](../docs/testing.md#optional-interactive-theme-picker).

## Automatic Gum environment loading — implemented, 2026-09-29

The owner requested automatic sourcing of the published Gum environment, superseding the earlier explicit-only loading boundary. A shared guarded Bash/Zsh adapter at the XDG state path is invoked by interactive Bash startup and the published `set_theme` path used by Zsh startup and prompt refresh. Missing files remain optional, no Gum/tool probe or subprocess is added, and noninteractive startup, generated init output and publication remain inert. Treat custom shell overrides as trusted configuration. No new selector or presentation layout is introduced; existing Gum presentation policy remains authoritative.

Native Termux verification: all 116 exports from a copied active artifact matched in isolated Bash/Zsh environments. Shell initialization passed 27 tests with 3 PowerShell skips; dispatcher passed 23/23. Workflow passed 12/14 with the existing catalog-count failures; Zsh passed 15/17 with the existing alias expectations. Theme tests passed 26/27, including generation refresh; the Neovim all-family case exceeded its 40-second timeout in the full suite, alone, and in a fixture restored to the original theme adapter with the new loader removed. Native Zsh PTY checks passed completion, history, cursor transitions and reload equality for hooks, FZF options, completion paths and key bindings. PTY timing output overlapped the theme suite and is not performance evidence.

Separate sequential, alternating before/after startup measurements used HEAD source snapshots in disposable fixtures, the copied 116-export artifact, seven warm samples per version, interactive shells without a PTY, minimal Bash tools and Zsh without plugins. Median Bash startup was 79.052/78.912 ms; Zsh was 1956.666/1976.411 ms. These are advisory native Termux measurements, not desktop/Windows evidence or a speed claim.

Bash/Zsh syntax, the new adapter's ShellCheck and whitespace checks passed. The existing theme adapter retains its baseline SC2153 informational warning. The documentation gate remains blocked by the existing retired Yazi plugin link in docs/testing.md; this change introduces no new relative-link targets. No live theme was activated or user shell reloaded.
