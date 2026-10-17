# Git theme template and platform configuration

Status: Implemented and activated on Termux, 2026-10-17.

Create the project-local `dots-theme-template` skill and apply it to a Git/Delta
template based on `config/git/gitppuccin`. Preserve personal settings while
publishing theme-only includes with shared Git colors and tinted diff backgrounds.
Expose the existing Dots syntax cache to Git's Delta processes through an isolated
XDG cache root; retain fallback behavior when the generated cache is absent.

Keep the Git directory mapping and automatically select its ignored `gitplatform`
link for Termux, Windows, WSL or a comment-only Linux overlay. Use bounded companion
planning and existing transactions/receipts, without weakening general mapping
overlap rules. Retire the stale Androidots Git resource/import records and verified historical link
through the guarded migration; preserve unrelated nested-repository work.

Validate all palettes, native Git/Delta output in owned roots, selector lifecycle,
rollback, undo, drift refusal and idempotence. Apply the scoped migration here and
refresh the current theme after checks. Update the relevant source-of-truth docs
and apply the [presentation gate](../docs/presentation.md#acceptance-gate). No
commits, pushes, package changes or unrelated cleanup.

## Verification and activation

Created and applied the project-local template skill. The Git include follows
resolved Git foregrounds and shared palette colors; native status uses Git's
supported staged/changed groups rather than separate deletion/rename slots.

Final focused verification passed: 2 native Git/Delta tests, 6 selector lifecycle
tests, 28 file-mapping tests, and 3 theme workflow tests covering every selectable
palette, personal-template precedence and connector rollback. Earlier in this
implementation, the installation (16), catalog (9), file-operation (21) and Bash
dispatcher (24) suites passed. Skill validation, Python/Bash syntax, focused
ShellCheck, 84-command metadata validation and 707 Markdown links passed.
Task-scoped whitespace checks passed; the existing extra blank line at the end of
`config/starship/starship.toml` remains outside this change.

Applied the guarded consolidation migration with transaction
`54779ed7859741b1b6dad0e7eabcec4a`; its recovery command is
`dots files undo 54779ed7859741b1b6dad0e7eabcec4a`. This reverses the migration's
catalog/link/receipt changes, not source edits or theme publication. The obsolete
Androidots resource/import entries and matching dangling overlay link were
retired. The existing `gitplatform -> termux` link remains unowned and unchanged.

Refreshed the current `catppuccin-mocha` theme and verified the active Git colors,
Delta's Dots syntax cache and generated include. Repeated migration and theme
refresh made no changes; direct Git linking previews as unchanged. Platform
source files and Starship/Blastoff configuration bytes remained identical.
Cross-platform selector fixtures passed; native Windows/WSL execution remains
unverified. No commits or pushes were made.
