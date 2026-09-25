# Anodize authoring engine

**Status: Core/CLI implemented and verified on native Termux; local Neovim integration implemented and verified after the completed plugin handoff.** Scoped owner-authorized Go exception; general Go migration remains paused.

- [x] Isolated pure Go extraction/adjustment module adapted from local Aether.
- [x] CLI authoring, imports/exports, preview, and existing publisher integration.
- [x] Journaled saves with collision/drift protection and recoverable edits.
- [x] Additive normalized colors in published palette JSON.
- [x] Isolated tests, startup/extraction measurements, documentation.

The CLI adapter reuses Python Presentation and Store rather than duplicating their policies in Go. The Go core accepts image bytes and palette data, and does not access user paths or execute processes. The private engine executable exchanges bounded JSON with the adapter. New themes live in themes/ID; wallpaper copies are the default. Preview and save never activate themes. Read-only commands create no persistent state.

Anodize.nvim lives in the separate `~/repos/Anodize.nvim` repository. Its agent finished the handoff, and Dots-owned configuration now integrates it. This Dots slice does not authorize edits to that separate repository; follow its local guide and obtain task scope before extending it. Preserve DotsThemeReload, personal highlights and dashboard animation in future integration changes. Android APK, TUI, online sources and arbitrary hooks remain deferred.

Acceptance includes all 23 modes, light/dark, deterministic results, idempotent adjustments, import round trips, collision and drift refusal, interrupted save/recovery/undo, JSON integrity, and the [presentation gate](../docs/presentation.md#acceptance-gate). All tests own their roots. No commits or live activation.

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
