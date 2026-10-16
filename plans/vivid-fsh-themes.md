# Shared Vivid and Fast Syntax Highlighting themes

**Status: Implemented and activated on native Termux, 2026-10-15.**

## Design

- Render `vivid.yml.tpl` and `fsh.ini.tpl` from the shared semantic palette, with the existing personal-template and bundled-app override precedence.
- Journal connectors to existing Vivid themes and FSH config directories. Published artifacts remain generation-local; do not commit live connector links.
- Apply generated Vivid colors for every published palette in Bash/Zsh, retaining optional-tool and old-generation/session-only fallbacks. Track the generated input in the Zsh data cache.
- Apply FSH after plugin loading and on generation changes, using its native loader and Dots-owned rebuildable cache. Preserve explicit overlays and retain last-good Dots styles for session-only palettes. Empty secondary keeps nested syntax on the same palette.
- Keep directories blue, commands/executables green, links/options cyan, errors red, and other file/syntax categories on shared semantic colors.
- Publish and activate locally after isolated acceptance, retaining the current palette. No new CLI routes, dependencies, commits or pushes.

## Acceptance

- Verify dark/light/generic renders, native Vivid output and actual FSH highlighting, refresh invalidation, cache reuse, optional dependencies and session-only behavior.
- Exercise journaled connector backup/rollback, idempotence, conflict refusal and template precedence in owned roots.
- Run theme/workflow/Zsh suites, startup and PTY checks, syntax, documentation links and whitespace validation. Compare startup measurements.
- Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate) for existing connector previews, errors and plain/data outputs. Distinguish native Termux evidence from other-platform and visual limitations.

## Evidence and limits

- Nine focused cases pass across the complete eight-case run and the added fixture-isolation case. Coverage includes native Vivid 0.11.1, FSH 1.55, generated-file cache invalidation, full native highlighting (including nested commands and directory arguments), optional-tool/native-only fallback, custom secondary themes and overlays, startup order, connector recovery, drift and idempotence.
- The public Zsh fixture explicitly excludes only the machine-local Vivid connector before copying; other links escaping the public repository are still refused. This was verified after local activation.
- Zsh regression suite: 22 passed. Workflow suite: 26 passed, one optional Pi check skipped. Shared-theme suite: 28 cases passed across the full run and targeted retries; the all-family Neovim case exceeded its existing 40-second limit. The timeout also reproduces with the original theme library/templates substituted only inside an owned fixture. One timeout retry also raced fixture cleanup after the child exited; no lingering fixture process remained. The concurrency-lock case passes in an isolated retry after failing under competing suites; the fallback roundtrip now explicitly supplies unavailable Vivid because all published palettes use Vivid when installed.
- Native PTY startup and prompt-driven dark/light publication correctly select FSH `dots` and update command/directory colors; the shell's `LS_COLORS` matches native Vivid generation. Tests own all state and plugin copies. The general Zsh PTY runner stops at an existing Anodize completion-column spacing assertion; it fails identically with the pre-change public fixture.
- Initial five-sample warm startup medians were 1.947 s baseline and 2.185 s updated, with overlapping ranges. A seven-pair alternating comparison measured 2.335 s baseline and 2.163 s updated (median paired delta -0.264 s). Variance prevents a speed claim; no consistent regression was observed. Both comparisons used the published Catppuccin Mocha palette and copied public plugins, with no competing test suites during measurement.
- Bash/Zsh syntax and `git diff --check` pass. ShellCheck retains only existing guard/source-resolution findings. Relative-link checking of changed documents found only the existing `docs/testing.md` link to the removed Yazi symlink-plugin README; the full audit stops at that same pre-existing link.
- Local publication retained `catppuccin-mocha`, created the two journaled connectors, and native `vivid generate dots` exactly matched the published artifact. Generated links are ignored by Git. Open a new shell or reload once to load the updated adapter code; later palette publications follow automatically. The initial activation made no direct rewrite of FSH's plugin theme state; the authorized follow-up below now persists its startup selection. No commit, push or dependency installation was performed. Native desktop/WSL/Windows rendering remains unverified.

## Saved FSH startup theme follow-up

**Status: Implemented and activated on native Termux, 2026-10-15.**

Persist the validated Dots cache as a regular `$FAST_WORK_DIR/current_theme.zsh`
file. Back up a non-Dots selection and its compiled companion into a unique private
recovery directory, invalidate stale `.zwc` code, and atomically replace the source.
Identical reloads do not replace the script. Failed generation/preparation keeps the
saved theme. Startup and missing-artifact/session-only fallback use the last saved
Dots palette. Preserve overlays and secondary styles. Verify fresh native startup,
`fast-theme --show`, light/dark updates, backups, idempotence and failure handling
before updating the current local `njen` selection.


Follow-up verification:

- All 11 focused file-theme tests and 22 Zsh regressions pass. Coverage includes
  exact source/compiled backups, private permissions, symlink recovery, paths with
  spaces/Unicode, directory conflicts, failed atomic replacement, unchanged-file
  reuse, invalid/missing input, overlays and secondary styles.
- A fresh native FSH-only shell reports `dots` for both active and startup themes,
  including after removal of the separate Dots build cache. An isolated native PTY
  verified prompt-driven dark/light publication updates colors and both selections.
- Five alternating warm startup pairs measured medians of 1.593 s before and
  1.723 s after (median paired delta +0.194 s); ranges overlap. This sample shows a
  modest increase but does not establish a stable regression. Persistence adds a
  saved-file comparison on theme initialization; unchanged prompts bypass it.
- Local activation retained Catppuccin Mocha and now reports `dots` on both lines
  of `fast-theme --show`. Original `njen` source and compiled bytes were verified
  against the backup in `$FAST_WORK_DIR/.dots-theme-backup.FkDuEcqI`; the directory
  is private (0700), the saved source is 0600, and stale `.zwc` is absent. Existing
  shells need one reload to install the updated adapter for subsequent switches.
- Zsh syntax and whitespace checks pass. The documentation audit still finds the
  pre-existing removed Yazi symlink-plugin README link in `docs/testing.md`.
  Native desktop/WSL/Windows behavior remains unverified.
