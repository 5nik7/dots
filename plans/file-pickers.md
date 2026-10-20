# File workflow pickers

**Status: Implemented, 2026-10-20.** Approved scope: FZF-first selection for add, link,
stash/restore, edit, remove/rm, show and browse. Recovery retains explicit IDs.

## Contract

Missing operands open a terminal picker; `--pick` explicitly requests one.
Explicit operands retain their meaning, except `add --pick PATH...` narrows the
discovery inventory. `--pick --dry-run` selects then previews; JSON and unattended
execution never select. Existing transaction plans and approvals remain authoritative.

Use the shared interaction layer and Python Presentation/resource renderer.
FZF has multi-selection, metadata-first previews and an explicit content toggle.
Gum and numbered menus provide fallbacks. Content is bounded and sanitized;
opaque selection tokens preserve literal paths. Preserve progress and verbosity.
The [presentation acceptance gate](../docs/presentation.md#acceptance-gate)
applies, including 40/80/120-column native PTYs and forced-decoration API checks.

## Acceptance

- [x] Shared selector, safe previews and command integration.
- [x] Metadata, completion and user/reference documentation.
- [x] Isolated selection, cancellation, output and transaction regressions.
- [x] Native FZF keys/layouts and focused existing suites.

No live installation, theme activation, commit or publication is part of this work.

## Verification

Native Termux: 201 focused cases passed across file pickers (19), browser (17),
mappings (28), catalog (9), operations (21), missing-source checks (16), installation
(23), confirmations (8), resources (11), progress (11), verbose operations (14),
and Bash dispatcher (24). Final focused mapping/browser checks also passed.
Native FZF exercised 40/80/120 columns, details/source/target cycling, batch keys,
exact ID search, cancellation, independent colors/icons, published light/dark
widget colors and temporary snapshot cleanup. Native Gum/plain browser checks and
journaled Apply passed. Selection never changed the existing approval or Store
contracts; selected add/stash/restore/edit/remove completed five fixture journals.

Validated 84 external command records, 735 relative Markdown links in 101 files,
Python/Bash syntax, scoped ShellCheck and `git diff --check`. Fixtures and PTYs used
owned roots. Native Windows/PowerShell picker behavior was not tested; no new
platform support is claimed. Gum retains its documented Escape/error ambiguity.
