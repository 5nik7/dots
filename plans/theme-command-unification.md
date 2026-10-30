# Dots theme command unification

Status: Implemented. Owner approved and locally activated 2026-10-16.

Unify `theme` and `dots theme`; generate family and standalone palette commands,
retain native query compatibility, support palette-only data, and load published
Dots state directly in Zsh. Family usage reads optional `logo.txt`; data output
remains undecorated. Existing full-ID routes remain supported.

Generated commands live in owned state generations and publish through journaled
pointers. Set/refresh and imports reconcile them; `refresh --commands-only` does
not activate a palette. Preserve collisions, current selection, existing arrays,
Vivid/FSH integration and unrelated source work. No Git publication.

Acceptance: isolated query/dispatch/completion, palette-only resolution, logo
presentation, publication/rollback/drift/idempotence, imports and native startup.
Apply the [presentation gate](../docs/presentation.md#acceptance-gate), measure
startup and dispatch, then refresh the existing local selection. Record results
and limitations here before completion.

## Verification and local publication

### Command collisions (implemented, 2026-10-29; live activation deferred)

Use one shared allocator for Bash and native generation: keep an available name, otherwise try `name-theme`, otherwise skip with an explicit route. Reserve canonical theme names and Dots action names; exclude verified owned commands from PATH probes. Recompute on set/refresh/import and native unchanged refresh. No numeric alternatives or parent-shell alias discovery.

Publish a manifest-covered `map.tsv` alongside actual executable `names`; wrappers and completion address the original theme. Old generations without maps retain identity lookup until refreshed. Preserve transaction recovery, drift guards and current selection. Retire only Dots completion registrations; PowerShell lacks public unregistration, so retired registrations decline and subsequent reloads do not overwrite replacement providers. Fish preserves mixed positional registrations and the shared reader returns no palette candidates for retired names. Exported Bash/Zsh adapters include the shared registration loader and preserve the Zsh autoload header.

Menu review: no menu change; existing menus address theme identities. Windows application destinations are unchanged. Native PowerShell 5.1/7 execution/completion and native Linux/WSL acceptance are pending where unavailable. Apply the presentation gate to skipped notices at 40/80/120 columns and preserve exact scalar/JSON/completion bytes. Verify isolated allocation, wrapper arguments, name transitions, completion, legacy upgrade, idempotence and rollback before documentation/wiki checks. No live activation, commit or push is part of this slice.

Verification on Termux, with owned fixtures:

- Allocation: 4 cases passed. Theme commands: 15-case suite passed, plus terminal-width and self-contained export cases (17 distinct cases); affected reload/export cases passed again after final loader changes. Actual Zsh Tab completion passed. Bash/Zsh/Fish registration checks preserve replacement providers.
- Native controller: the 16-case suite passed with one unavailable-engine skip; the additional empty-legacy-generation upgrade case and affected publication/drift cases passed. The dedicated PowerShell mapping/retirement case was skipped because no engine is installed.
- Dispatcher: 23 cases passed in the full run; its completion-export expectation was updated for the shared loader and that case passed separately. Six shell-init cases passed. Atomic publication, failed publication and first-selection drift cases passed; the 15-boundary durability test passed separately in 309.956 seconds after the combined safety batch exceeded its 240-second cap.
- Python and Bash/Zsh/Fish syntax checks passed. Warning-level per-file ShellCheck with extended dataflow disabled passed for the changed publishers, loader, adapter and dispatcher. `lib/dots/complete.bash` exceeded the 30-second cap; its syntax/completion behavior checks passed, but full lint coverage remains pending. An earlier combined default-analysis run was stopped for resource use.
- Documentation links, command metadata and whitespace checks passed. Wiki pages were rebuilt with retained transaction `e2eebbcbe4a0478baa92f6da4fa58136`; wiki check passed, preserving the pre-existing generated Environment changes.

Completion-loading measurement: seven alternating baseline/current samples per shell, 24 synthetic shortcut names, owned HOME/XDG roots, no other Dots verification batch running. The baseline used HEAD adapters; measurements include process launch and Zsh compinit. Final medians in milliseconds were Bash 27.68/41.11, Zsh 1142.24/1044.88 and Fish 35.52/42.41. Ranges overlapped substantially (Bash 16.09–90.82/24.16–65.76; Zsh 807.52–1391.01/910.45–1806.47; Fish 25.53–71.21/17.30–75.05), so these are local observations, not a general speed claim. Initial Bash measurement exposed roughly 52 ms of per-name subprocess overhead; a single builtin registration snapshot replaced those subprocesses. The remaining bounded work validates published names and preserves other providers; startup performs no theme discovery or PATH allocation.

### Original local publication

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
