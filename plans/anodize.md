# Anodize authoring engine

**Status: Core/CLI implemented and verified on native Termux; local Neovim integration implemented and verified after the completed plugin handoff.**

- [x] Isolated pure Go extraction/adjustment module adapted from local Aether.
- [x] CLI authoring, imports/exports, preview, and existing publisher integration.
- [x] Journaled saves with collision/drift protection and recoverable edits.
- [x] Additive normalized colors in published palette JSON.
- [x] Isolated tests, startup/extraction measurements, documentation.

The CLI adapter reuses Python Presentation and Store rather than duplicating their policies in Go. The Go core accepts image bytes and palette data, and does not access user paths or execute processes. The private engine executable exchanges bounded JSON with the adapter. New themes now default to the user configuration theme root; explicit built-in saves use repository themes/ID; wallpaper copies are the default. Preview and save never activate themes. Read-only commands create no persistent state.

Anodize.nvim lives in the separate `~/repos/Anodize.nvim` repository. Its agent finished the handoff, and Dots-owned configuration now integrates it. This Dots slice does not authorize edits to that separate repository; follow its local guide and obtain task scope before extending it. Preserve DotsThemeReload, personal highlights and dashboard animation in future integration changes. Android APK, TUI, online sources and arbitrary hooks remain deferred.

Acceptance includes all supported modes, light/dark, deterministic results, idempotent adjustments, import round trips, collision and drift refusal, interrupted save/recovery/undo, JSON integrity, and the [presentation gate](../docs/presentation.md#acceptance-gate). All tests own their roots. No commits or live activation.

Verification: isolated Go tests/vet and 14 CLI acceptance tests; existing theme (23), theme workflow (11), file operations (21), file catalog (9), and Bash dispatcher (23) tests passed. ShellCheck warning-level checks and relative Markdown links passed. [Performance evidence](../docs/testing.md#anodize-baseline-2026-09-25) records engine and complete CLI timings. No live theme activation or publication was performed.

- [x] Configure the local Anodize.nvim plugin, preserve compatibility helpers and personal highlights, and switch lualine.
- [x] Verify real fixture publication to editor, focus/manual reload, last-good behavior, inactive gating, raw compatibility, and dashboard repaint/lifecycle with isolated runtimes.

The five dedicated Neovim integration cases and both shared theme suites pass on native Termux. The normal LazyVim UI and live desktop appearance remain unverified; no live editor was launched.

## Standalone shell completion and manual

- [x] Reuse the Bash/Zsh/Fish adapters for `anodize completion SHELL`, backed by static Dots metadata and read-only theme names. Complete modes, adjustment/color keys, format/app choices and paths without an engine.
- [x] Generate a section-1 manual from CLI argument definitions plus documented behavior, with reproducible checked-in artifacts.
- [x] Link adapters into the existing repository shell completion trees; document manual viewing and optional installation.
- [x] Verify isolated three-shell candidates, literal Tab insertion, Zsh/FZF-tab acceptance, manual lint, metadata consistency and the shared presentation gate.

Verification on native Termux: four engine-free integration cases (including real Tab insertion in Bash/Zsh/Fish), 23 Bash dispatcher cases and 14 Anodize cases passed. The Zsh/FZF-tab PTY acceptance passed, including standalone option labels and unchanged reload state. Manual lint, shell syntax, warning-level ShellCheck, artifact freshness and Markdown links passed. The broader Zsh suite passed 15 of 17 cases; its two existing `ll` alias expectations also failed with Anodize completion removed from disposable fixtures. No unrelated alias changes or system manual installation were made.

## Remaining work and ownership

The implemented slice is complete within its recorded fixture scope. [Next steps](anodize-next.md) proposes foundation hardening before a new frontend. Normal LazyVim visual acceptance, real wallpaper APIs, desktop platforms, distribution/release work and frontend selection remain distinct gates. The Anodize.nvim plan predates the additive `colors` field; Dots now publishes it while retaining existing schema-1 fields and role authority. No plugin protocol redesign is implied.

The separately authorized [theme plugin slice](theme-plugins.md) now covers explicitly enabled local post-publication hooks. Earlier arbitrary-hook exclusions remain applicable to downloaded-theme execution and broader hook systems. This does not expand the Anodize.nvim scope.

The owner-approved [interactive authoring slice](anodize-interactive.md) extends
storage and CLI selection; application/TUI work remains deferred.

## Patina image export

The Go engine maps an input raster to a rendered theme or an extracted reference palette. One CLI handler owns the four Patina spellings, staged thumbnails, automatic numbering and journaled image saves. The Anodize installer component delivers the standalone shim. The existing menu gains a guided action because choosing a source image and inspecting the result benefits from a preview. Color policy and presentation preferences use the existing controls. Style, palette and destination belong to each invocation. The root README's introductory setup and navigation already lead to the topic guide.

Acceptance covers pixels and alpha, reference extraction, theme overrides, equal output across routes, concurrent saves and collisions, cancellation, undo, literal paths, installer delivery and engine-free six-shell completion. Desktop Linux, WSL and native Windows PowerShell 5.1/7 require separate runtime acceptance. See [Patina usage](../docs/anodize.md#patina).

On Termux, Go tests and vet passed. The CLI fixtures verified all four routes, concurrent numbering, undo, input drift and preview cancellation at 40, 80 and 120 columns. The installer lifecycle delivered the shim, literal Tab completed in Bash, Zsh and Fish, and the catalog check passed across 1,043 contexts. A single 1920×1080 engine benchmark on Android/arm64 took 3.32 s in exact mode and 5.33 s in shaded mode with other checks running.

### Wallpaper styles

Harmonize was the initial hue-matching default, with missing-hue harmony choices, themed gradient and duotone ramps, strength and named stops. Explicit exact and shaded retain their original mapping. The existing guided style selector previews all treatments from one bounded sample and renders the selected treatment at full resolution for review. These are per-image artistic choices. The existing command, installer component and introductory README already cover entry and delivery. On Termux, the Kanagawa regression and the bundled 3840×2160 fern photograph retained green leaf shadows. Checks cover named ramp order, continuous sky tones, neutral clouds, alpha, source identity at zero strength, all four routes, per-style thumbnail parity and picker cancellation at 40, 80 and 120 columns. The median of three single-iteration 1920×1080 mapping benchmarks on Android/arm64 was 2.53 s for harmonize, 2.51 s for gradient and 2.51 s for duotone (about 16.7 MB allocated each, with concurrent checks). Desktop Linux, WSL and native Windows runtime acceptance remain pending.

### Palette modes, comparison sheets and encoders

The ordered engine catalog supplies 35 modes and their descriptions. The integration generator projects its choices into static command metadata for Bash, Zsh, Fish and native PowerShell. Patina derives temporary variants from distinct rendered theme colors and retains custom stop names. The source image is sampled once per sheet. Numbered style and mode sheets, normal exports and all encoders use the existing staged create-only save and undo path.

The stronger harmonize treatment uses theme shadow, midtone and highlight anchors. Natural preserves the previous treatment. The 17 styles include source-group color transfer, ordered dithering and contour ink. Output suffixes take precedence over the format flag. Optional image writers are preflighted before rendering. CLI and engine fixtures cover image headers, conflicting flags, transparent pixels, collision numbering, theme polarity and repeatable previews.

**Menu update.** The existing interactive picker includes the expanded styles and palette modes with image previews. **No configuration integration change needed.** These choices apply to the current image and output. **No README change needed.** The existing introduction links to the Anodize guide. The installer already delivers all four entry points. Native Linux, WSL and Windows PowerShell 5.1/7 runtime acceptance remain pending.


On Termux, the 17-style Kanagawa fern sheet retained green leaf shadows. The 35-mode Catppuccin Mocha sheet included the original and authored theme beside the numbered alternatives. All eight output encoders passed local fixture checks, including JPEG input with an explicit WebP destination. The revised 1920×1080 harmonize benchmark took a median 4.43 s and about 16.7 MB over three single-iteration runs with a concurrent fixture. The stronger default adds a theme-family midtone blend and maps source lightness through the theme endpoints.

### Palette-led default

Alloy uses palette-blend lightness and blends hue and chroma with a 25% harmonize contribution. The shared renderer handles theme and reference palettes, native shell entry points and thumbnail previews. The menu update places alloy first in the existing picker. It is style 18 on comparison sheets, following the 17 existing entries. No configuration integration change needed because strength and harmony already express the applicable per-image choices. The existing installer and root README cover the same entry points.

Acceptance compares alloy, palette-blend and harmonize on the Kanagawa fern and Catppuccin village scene. Check implicit and explicit alloy, legacy pixel identity, short-arc hue mixing, near-gray colors, 16-bit alpha, zero strength, picker parity, sheet numbering, all four routes and JPEG-to-WebP export. Native desktop Linux, WSL and Windows PowerShell runtime checks remain separate.

On Termux, both explicit parent styles reproduced the pre-change PNGs byte for byte on both photos. The Kanagawa fern’s tenth-percentile brightness was 32/255 in alloy and palette-blend and 69/255 in harmonize. The Catppuccin village scene measured 39/255, 39/255 and 73/255 respectively. The four routes produced identical default PNGs. One 1920×1080 Go benchmark on Android/arm64 took 3.78 s for alloy, 3.21 s for palette-blend and 3.02 s for harmonize with concurrent checks.
