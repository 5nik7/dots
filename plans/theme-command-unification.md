# Dots theme command unification

Status: Implemented. Owner approved and locally activated 2026-10-16.

Unify `theme` and `dots theme`; generate family and standalone palette commands,
retain native query compatibility, support palette-only data, and load published
Dots state directly in Zsh. Family usage reads optional `logo.txt`; data output
remains undecorated. Existing full-ID routes remain supported.

Generated commands live in owned state generations and publish through journaled
pointers. Set/refresh and imports reconcile them; `refresh --commands-only` does
not activate a palette. Preserve collisions, current selection, existing arrays,
Vivid/FSH integration and unrelated source work. No Go migration or Git publication.

Acceptance: isolated query/dispatch/completion, palette-only resolution, logo
presentation, publication/rollback/drift/idempotence, imports and native startup.
Apply the [presentation gate](../docs/presentation.md#acceptance-gate), measure
startup and dispatch, then refresh the existing local selection. Record results
and limitations here before completion.

## Verification and local publication

- Published 23 generated family/standalone commands while retaining the local
  `catppuccin-mocha` selection. Verified generated Catppuccin and Rosé Pine queries,
  `theme current`, published Zsh arrays and reset variables. Existing `ristretto`
  keeps PATH precedence; use `theme ristretto` for the palette command.
- Focused command cases passed across isolated runs: shared routing, palette-only
  activation, explicit metadata grouping, logos/data boundaries, native shell
  completions, idempotence, interruption/rollback/drift, palette-only imports and
  failed import publication. Native Zsh startup and actual ZLE/Tab completion passed.
- Complete suites: dispatcher 24, Vivid/FSH 11, Zsh 22, shared shells 19. Shell init
  passed 30 cases with seven skips; the installed Xonsh launcher references absent
  Python 3.13 and was treated as unavailable by a process-local test override.
- Shared-theme regressions passed 31 distinct cases across the original run and
  focused rechecks. The pre-existing all-family Neovim test still exceeds its
  40-second timeout. Workflow cases passed after the import-state expectation was
  updated for generated commands; one optional native integration remains skipped.
- Syntax checks, warning-level per-file ShellCheck and whitespace checks passed.
  Checked 289 changed-document links excluding the existing broken Yazi link in
  `docs/testing.md`, which still blocks the global documentation checker.
- Five alternating isolated warm Zsh samples: median 1.977 seconds before and
  2.080 seconds after, with overlapping ranges. Ten `theme current` samples:
  medians 56.14 ms before and 55.29 ms after. No startup theme-directory scan.
- Native Windows/desktop appearance is unverified. The final completion-reload
  recheck was stopped or interrupted when the owner reported Termux crashes;
  no further resource-intensive validation was attempted.

The old command files are compatibility shims, not independent implementations.
The text logo was moved byte-for-byte. No commits, pushes, or unrelated cleanup
were performed. Open a new shell or use `rl` to load the new PATH and completion
wiring in an existing session.
