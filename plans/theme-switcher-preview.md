# Live theme switcher preview

## Scope

Prefer FZF for `dots theme switcher` catalog browsing so hovering previews the palette. Keep Gum for review when available and as the catalog fallback; retain the numbered fallback and existing explicit Apply safety. Do not change shared backend precedence for other commands, command routes, completion candidates, or publication.

## Presentation and acceptance

Follow the [presentation contract](../docs/presentation.md#acceptance-gate). Use fullscreen FZF with the list at the top and an always-visible bottom preview occupying 70% of the height. Reuse `theme show` for semantic colors/swatches, with explicit preview color policy derived from the terminal; plain mode retains hex values. Inherited FZF options remain disabled; the current published `fzf.sh` supplies colors through the shared read-only literal parser, respecting color controls without executing shell code. Help and nonterminal behavior remain static. Empty catalogs, errors, cancellation, invalid choices and previews must not publish state.

- [x] Implement FZF-first browsing, independent review backend, and visible palette preview.
- [x] Cover FZF/Gum/plain fallback, mixed-tool selection, errors, color policy, and native FZF preview/cancellation at 40/80/120 columns in isolated roots.
- [x] Synchronize help, user/reference documentation and focused verification.

## Verification

On native Termux, the picker suite passed 16 tests, the workflow suite 15, and the Bash dispatcher suite 23. Published-color fixtures additionally verify current-artifact precedence, NO_COLOR/explicit-color policy, and malformed-data refusal without executing shell code; publication still uses the same extracted literal parser. Native FZF PTYs verified hovered palette output without publication at 40/80/120 columns and forced-color preview with NO_COLOR; Gum fallback/review tests also passed. Bash syntax, focused ShellCheck and whitespace checks passed. Command routes/completion candidates are unchanged; dispatcher metadata tests cover the revised help summary.

The broader theme suite passed 28 tests but its unrelated `test_neovim_all_native_families` fixture timed out at 40 seconds, including on an isolated retry. Documentation link verification remains blocked by the pre-existing `docs/testing.md` link to the missing `config/yazi/plugins/dots-symlink.yazi/README.md`. Neither issue was modified in this task. Manual visual review remains unverified.

Native PTY evidence is distinct from manual visual review and does not establish desktop/Windows support. No wallpaper preview or live application of a hovered theme is included.
