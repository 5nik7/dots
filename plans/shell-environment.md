# Dots-owned shell integration

Status: Implemented, including owner-approved legacy cleanup.

## Delivered

- `dots init` emits integration-only hooks for Bash, Zsh, Fish, Nushell, Xonsh
  and PowerShell. Personal configuration stays in `shells/`.
- `lib/dots/shell/settings.tsv` and `paths.tsv` define settings and derived paths
  for every adapter. Literal user config.env supports validated overrides without
  exporting derived defaults back into the override namespace.
- `dot`, native palette/role values, color formats and reset codes are library-owned.
  Legacy 256-entry maps are no longer allocated by startup.
- `dots env [NAME] [--json]` exposes bounded diagnostics and provenance.
- `theme` shows the current palette; `theme current` stays scalar. `theme show`
  defaults to the current selection. `dots themes` owns collection management;
  singular routes remain compatible.
- Published `shell.tsv` carries native palette/format data without executable
  configuration. Theme publication retains its transaction and rollback path.
- Default selection comes from settings; legacy .default/.theme inputs are ignored.
  The active local selection was refreshed and remains catppuccin-mocha.

## Verification

Focused tests ran sequentially in owned roots, avoiding concurrent full suites:

- Five shell-environment tests passed, including native Bash/Zsh/Fish/Nushell
  settings, atomic reload refusal, diagnostics, default selection, completion,
  Fish/Nushell prompt refresh, stale-color removal and failed-update retention.
- Fourteen selected shell-init cases passed across runs: native environments,
  undecorated read-only generation, invalid/missing loaders, interactive reload,
  literal control characters, and portable links/relocation. The Xonsh subcase
  correctly skips its installed launcher's missing Python 3.13 interpreter.
- Native Zsh noninteractive startup with empty PATH and startup without optional
  tools passed. Published startup plus FSH and registry/completion reload passed.
  Native ZLE Tab completion passed.
- Theme route compatibility, atomic publication/idempotence and failed-publication
  rollback passed. The portable snapshot contains the selected identity and colors.
- Three focused dispatcher/metadata/completion cases passed. The live catalog
  validates 78 external commands. New Bash/Fish syntax and per-file warning-level
  ShellCheck passed; whitespace checks passed.
- Xonsh's installed Python package was parsed and executed with the available
  Python 3.14 interpreter in an isolated home. Published Mocha colors, reset codes
  and repeated initialization passed. The normal launcher remains unrepaired.
- PowerShell is unavailable here: native Windows execution, prompt composition,
  completions and junction behavior remain unverified. No packages were changed.
- Changed-document relative links: 320 resolve; the existing unrelated
  docs/testing.md link to dots-symlink.yazi/README.md remains broken. The global
  documentation checker reports that same failure.
- Three sequential noninteractive process-plus-integration samples per shell:
  medians Bash 19.90 ms, Zsh 21.01 ms, Fish 25.87 ms, Nu 39.07 ms. These are new
  integration-only measurements, not a before/after full-startup comparison.

No full Neovim or broad concurrent regression suite was run. Prior Termux crashes
motivated bounded batches, not relaxed isolation. No commits or pushes were made.

## Approved cleanup

The owner approved deletion after reviewing the exact list. Consumers, fixtures
and benchmarks now use Dots commands or the shared library. Removed:

```text
dot.env
shells/shells.env
themes/themes.env
themes/.default
themes/.theme
themes/bin/theme
themes/bin/catppuccin
themes/bin/current_theme
bin/current_theme
lib/dots/themes/legacy.bash
lib/dots/themes/current.bash
shells/zsh/completions/_catppuccin
```

Moved `themes/bin/logo.png` to `themes/catppuccin/logo.png`; SHA256 matched
before and after the move. A recovery copy of all 12 removed files and the PNG
was retained outside the repository under the local Dots source-backups directory.
The home-directory `.theme`, private modules and unrelated work are preserved.


Cleanup verification: 15 focused cases passed across the theme, Zsh, workflow
and shell-environment suites. Native interactive Zsh now verifies the library-owned
prompt hook, status preservation and duplicate prevention. Bash/Zsh and changed
Python syntax checks passed. Warning-level ShellCheck passed for theme views and
shell helpers; completion analysis exceeded a bounded run and is not claimed.
Changed-document checking resolved 332 links, with only the known unrelated
Yazi README link failure. `git diff --check` passed.
The command catalog validates all 78 external commands. The final theme refresh
succeeded and retained `catppuccin-mocha`.
