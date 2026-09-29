# Unified theme CLI

**Status: Implemented; broader baseline verification failures retained.** Owner-authorized consolidation of the Bash theme interface; general Go migration remains paused.

## Contract

`dots theme` is the sole first-party theme family. Remove plural executables without aliases, migrate repository callers to full selectable IDs, and retain palette browsing through `list --families`, `list --flavors FAMILY`, and `show`/`color --native`. Preserve palette helper APIs, generation storage, transaction semantics, and existing application integrations.

## Implementation

- [x] Consolidate CLI helpers and remove the plural parser and executables.
- [x] Migrate shell/editor callers, fixtures, benchmarks, metadata, and completion.
- [x] Synchronize active documentation and record the superseding compatibility decision.
- [x] Validate migration, existing publication/recovery behavior, and initialization in disposable roots.

## Acceptance

Follow the [presentation gate](../docs/presentation.md#acceptance-gate): use shared Bash presentation, review help and palette views in terminal and redirected modes, exercise forced/disabled decoration, and preserve scalar/generated output. Test full-ID validation, native color collisions, empty/invalid family queries, Pywal discovery without input, completion across Bash/Zsh/Fish, and removed-route discovery. Existing picker fixtures cover narrow/wide terminal interaction. No new interactive flow is introduced.

Capture pre-change failures separately. Run affected theme, workflow, picker, plugin, dispatcher, shell initialization, Zsh and Anodize integration suites. Run syntax/ShellCheck, relative documentation links, diff whitespace checks, and sequential isolated theme benchmarks. Do not activate a live theme. Record native Termux evidence separately from unavailable desktop/Windows checks.

## Verification result

The implementation and focused migration acceptance are complete. See the [verification record](../docs/testing.md#unified-theme-cli) for passing suites, native terminal review, timings, and baseline failures. All tests used owned roots. No live theme, generation schema, storage layout, or application activation was changed; no commit or push was performed.

The reference audit found no active plural callers in the root checkout or initialized public Androidots, Windots, and Neovim configurations. Remaining plural names are explicit migration documentation, negative tests, historical link anchors, or retained independent Go protocol fixtures. Existing unrelated working-tree edits were preserved, including shell completion changes made during this task.
