# Core command updates

Status: implemented and locally verified. Approved through Todo `core-update`
(`fb116bd3fcc448f6a2a39211f9fe875b`).

## Accepted behavior

- Config opens List/Get/Set. List and Get are read-only; Get/Set choose a category
  first. Empty terminal get/set calls use the guided flow; explicit/data calls
  preserve their contracts. Retain scope, inheritance, redaction and guarded saves.
- `files edit OWNER:OLD --id NEW` renames across the core registry, all profile
  mappings and replacement references. Combined mapping edits affect only the
  selected profile; live apply still requires the active profile. One retained
  transaction owns metadata, receipt identities and any requested live changes.
- Registry schema 3 adds flattened historical-ID mappings. Schema 2 remains
  readable and upgrades only on an effective rename. Retired IDs remain reserved
  for receipt recovery; user selectors require current IDs. Preserve original
  installation baselines and immutable historical journals.
- Remove first-party themes/profiles routes. Theme retains every existing action
  and its bare summary. Profile gains list and check --all, retaining check's
  active default and explicit-ID form. Bare profile remains a summary.

Menu assessment: update Config and the existing mapping editor; merge the
Theme/Themes and Profile/Profiles launcher families. Recovery and existing
direct-only source operations remain direct.

## Work packages

The existing config goal owns file-ID work (C1), then config navigation (C2).
The existing command goal owns independent theme (T1) and profile (P1) changes.
Integration/docs verification (V1) depends on all four. Keep full IDs, acceptance
criteria and progress in the scoped Todo store through its CLI.

## Acceptance

Apply the [presentation gate](../docs/presentation.md#acceptance-gate), including
40/80/120-column light/dark/plain PTYs, private two-client tmux, cancellation,
literal values and forced-decoration data preservation. Verify schema migration,
reserved identities, successive renames, all-profile references, original receipt
baselines, selected-profile combined edits, stale review, rollback, recovery,
undo and no-op behavior in owned roots.

Run affected file-platform, registry/profile, mapping, operation/repair/install,
config/menu, theme/profile and Bash/native-controller suites sequentially. Check
metadata, completion, documentation links and whitespace. Measure direct dispatch
if its lookup changes. Synchronize canonical docs and the superseding decision,
then preview/build/check the available wiki.

Completion requires local Termux and shared-controller/platform fixture evidence.
Native Windows PowerShell 5.1/7 and native Linux/WSL runtime/visual acceptance may
remain explicitly pending. Preserve unrelated Termux edits; no live install,
theme publication, reload, commit or push is part of this implementation.

## Verification evidence

The file-platform (5), rename (10), mapping (29), profile backend (14), profile
config (10), profile debug (17, one unavailable runtime skipped), Bash (24),
native-controller (18, one unavailable runtime skipped), file operation (22),
repair (48), catalog (9), legacy identity (8) and profile (14) checks pass in
owned local fixtures. The additional Bash/native profile JSON equivalence case
passes. Config's 15-case suite passes, including native FZF/private tmux at
40/80/120 columns; the final rename-handoff and literal category-order assertions
pass separately. The updated launcher suite passes all 21 cases, the theme picker
passes all 16, and the shared menu suite passes all 24.

The broader theme suite completed 32 cases with 28 passes; theme-command checks
passed 16 of 17; installation passed 27 of 28. Saved pre-change controllers
reproduce all six failing/error outcomes in the same owned fixtures:

- Theme `test_hyphenated_completion_and_zsh_roundtrip`: the failing Vivid stub
  is rejected while generating file colors.
- Theme `test_zsh_refresh_status_and_hooks`: the Gum foreground remains stale
  after refresh (exit 8). The initial baseline hit the 40-second limit; a bounded
  120-second follow-up reached the same assertion.
- Theme `test_neovim_all_native_families` and
  `test_neovim_real_palette_and_focus_reload`: both hit their 40-second limits.
- Theme-command `test_published_zsh_startup_and_prompt_command_refresh`: the
  startup fixture reports unknown template color `fzf_ui_selection_bg`.
- Installation `test_fresh_checkout_wsl_setup_connectors_check_and_restore`:
  repeat installation republishes theme artifacts and reports `complete` rather
  than `unchanged`. The separate bundled-app repeat/restore case passes.

These are recorded baseline limitations outside the accepted command/identity
change. Native Windows PowerShell 5.1/7 and native Linux/WSL runtime/visual checks
remain pending under the agreed completion gate.

Command metadata validates 232 external routes; relative Markdown links and
`git diff --check` pass. The available local wiki was previewed, rebuilt and checked
healthy (transactions `d37e8a0a3e9e4ce395e5dff484d9c65e` and
`c719c6a5b03e4845a552bffe3b98199f`). Dispatch lookup and shell startup are unchanged,
so no new dispatch benchmark was required. Existing Termux edits and unrelated
logo assets were preserved.
