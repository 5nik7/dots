# Theme presentation, file colors and Yazi

Status: Implemented and verified on native Termux.

Implement the owner-approved plan: family-scoped foreground/background presentation;
shared file styles with per-theme overrides; query, edit, explain and export commands;
atomic JSON/Lua/LS_COLORS publication; live Dots-aware Yazi; self-contained plugin
documentation and tests; repository-local skills with discoverable links.

Decisions: bare family help follows its active flavor, otherwise the family default.
`--color=none` disables decoration; `--color NAME` remains a query. Color edits save
shared overrides by default and per-ID overrides with `--theme`; `--apply` refreshes
the current selection without switching it. Yazi refreshes while running. Full
styles include foreground, background and boolean attributes. MIME information is
supplied or already cached, never detected in redraws. Data output stays undecorated.

Preserve existing dirty work in both repositories. Use sequential isolated tests,
including native light/dark redraws and publication recovery. No commits, pushes,
package installs, private-module changes or extra cleanup are authorized.

## Implementation and evidence

The shared TOML model now owns core, suffix and MIME full styles. The command
provides saved/configured/published boundaries and file-store journals. Publication
reserves JSON/Lua/LS_COLORS artifacts, fingerprints all rule inputs and Vivid, and
notifies Yazi after success. Shells load the matching generation's LS_COLORS.
Theme-family panels use addressed foreground/background, sanitized logo artwork,
readable accents and plain/data fallbacks. Standalone and bundled Yazi share 14
runtime modules; configuration enables Dots colors with explicit light/dark pairs.

Human acceptance includes dark/night and light/day help, a 40-column panel review,
active-family flavor selection, forced/auto/disabled color, NO_COLOR, dumb terminals,
plain fallback for incomplete palettes, and unchanged scalar/JSON/Lua output.
File edits show saved/dry-run outcomes, parser diagnostics and source provenance;
invalid publication retains the current generation. No new interactive selector
was added, so a Gum adapter is not applicable.

Evidence (native Termux, isolated homes and DDS roots):

- Four file-color cases cover edits, precedence, MIME/suffix matching, full SGR
  attributes, missing Vivid, Lua consumer validation, panels and completion.
- Five shell-environment cases cover Bash/Zsh/Fish/Nushell, including native
  palette and LS_COLORS refresh. Published Bash/Zsh initialization and FSH also pass.
- Ten theme-command cases pass after updating the logo expectation and adding
  the new default rule file to the owned Zsh fixture. Dispatcher: 24 tests pass.
- Atomic generation/idempotence and failed-publication rollback pass. A present
  failing Vivid retains the previous generation; absent Vivid uses basic coverage.
- Native plugin checks pass in both standalone and copied main-config fixtures:
  live dark/light refresh, cached MIME and explicit suffix precedence, N/V/U,
  40/80/120 and 40/80/160 layouts, Git/projects/panes, malformed data and recovery.
  GNU ls comparison: 350 cases pass; native hard-link creation is unavailable on
  this filesystem, with that case retained in Lua fixtures.
- Five repository-local skills validate; relative discovery links point from
  .agents/skills to canonical .codex/skills. Documentation links and diff whitespace
  checks pass. Python/Bash/Lua syntax checks pass. Bounded ShellCheck identified
  and fixed a new single-item-loop diagnostic; full completion-file analysis
  exceeded its eight-second bound, while native completion tests pass.

Five sequential warm process-plus-set_theme samples per mode: Bash published
74.48 ms versus legacy Vivid 98.94 ms; Zsh published 49.62 ms versus legacy Vivid
59.67 ms. These measure the source/load path in an owned fixture, without the
optional Zsh Vivid cache helper; they are not full interactive startup benchmarks.
No new prompt scan or redraw-time I/O was added.

PowerShell is absent and the installed Xonsh launcher lacks its Python interpreter;
those adapter edits have no new native-runtime verification. No tools were installed.
Vivid's font grammar omits reversed/hidden/crossed on database-derived suffixes;
exact core and explicit suffix rules plus JSON/Lua preserve all attributes.

Live publication completed with the existing `catppuccin-mocha` selection retained:
`g.loZkugfX`, Vivid coverage, directory foreground `#89b4fa`. JSON, Lua and raw
LS_COLORS are present and mutually consistent. The existing `ristretto` executable
retains PATH precedence. Reopen Yazi once to load the changed plugin; subsequent
publications refresh colors in place. No commits, pushes or extra removals occurred.
