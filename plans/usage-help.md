# Concise root help

**Status: Implemented; native Windows PowerShell 5.1/7 and Linux/WSL terminal acceptance pending.**

Selected Todo goal: `2acf2a75677e47dfa286c06e4f499edc` (`usage`).

## Accepted behavior

Root help (`dots`, `dots help`, `dots -h`, `dots --help`) shows one row per visible top-level command or group. Preserve each renderer's existing rows, built-in usage synopses, branding, usage and global options. Keep family/leaf help and `dots commands` exhaustive. Add the footer: “Use dots help COMMAND for details; dots commands for all commands.”

Group visible entries by the first route component without modifying the catalog. Prefer a visible parent's summary; use “Command group” otherwise. Deeper-only extensions remain discoverable; hidden-only groups remain absent and hidden metadata is never displayed. Preserve ordering, discovery roots, validation, collision behavior, direct dispatch, completion records and generated references. No new runtime dependency or extension execution.

Bash, the shared native Python CLI and Python-free PowerShell help implement the same projection through their existing renderers. Windows app destinations, installation and shell startup remain unchanged. Menu review: **unchanged**, because static help adds no selectable workflow.

## Work packages

1. `52a77005a6de4c2d83283bd6b76107e9`: compact root help across all three frontends; isolated regressions for aliases, real/implicit/hidden groups, full contextual help/inventory, completion, validation and nonexecution.
2. `4ab948cfe97349c39797a8f7874def2c`: depends on package 1; verify presentation and synchronize canonical docs and the local wiki while preserving existing changes.

Both children inherit high priority. Todo CLI mutations own progress, notes, recovery and child-before-parent completion; the selected goal's original title, alias, tags and notes are retained.

## Acceptance and evidence

Follow the [presentation gate](../docs/presentation.md#acceptance-gate): existing semantic roles, successful stdout/error stderr, readable plain/redirected output, color/icon controls, `NO_COLOR`, `TERM=dumb`, 40/80/120 columns, Unicode/long summaries and inert metadata. Mutation/recovery and interactive prompt cases do not apply to static help. Completion/generated data must remain undecorated and unchanged.

Run the Bash CLI and native CLI suites sequentially in owned roots, relevant syntax/ShellCheck checks, documentation link validation and `git diff --check`. Extend the native PowerShell runner to cover all four root-help forms, implicit groups, full family help and wrapped footers with Python absent from PATH. Record unavailable engines as pending, not native evidence.

Verification on Termux:

- Bash CLI: 27/27 tests passed, including actual Bash/Zsh/Fish completion and all new root-help cases.
- Native CLI: 23 tests ran; 21 passed and two PowerShell runtime cases skipped because no engine is available. Shared-controller fixtures do not establish native Windows execution.
- 52 exact before/after comparisons passed for full inventory/validation, family/leaf/implicit-group help, generated completion source for all four shells and deep route/option-value completion, with forced and disabled color. Extension markers remained absent.
- 30 owned PTY captures passed across Bash/Python, 40/80/120 columns and automatic, disabled, `NO_COLOR`, dumb-terminal and forced styling. Unicode/long summaries and footer wrapping remained readable; fixture homes stayed empty. Reviewed representative narrow/wide captures. Actual Windows/Linux/WSL terminal and light/dark display acceptance remains pending.
- Bash/Zsh/Fish syntax checks passed. The changed Bash file has the same seven pre-existing ShellCheck diagnostics as its saved baseline (six unresolved dynamic sources and one externally consumed metadata variable); no new diagnostics. The broader framework ShellCheck run was stopped after exceeding three minutes and is not claimed as passing.
- Command validation passed for all 232 current external commands. Root help displays 16 external groups plus four built-ins. This is dynamic metadata, not a fixed list. Dispatch/startup paths and discovery algorithms are unchanged; no performance improvement is claimed.
- Relative Markdown validation passed (1125 links in 146 files), as did whitespace checks. Wiki preview selected its manifest and the generated Commands, PowerShell and Testing pages. The final build reported unchanged, and `dots wiki check` reported `Healthy yes`; the generated pages contain the updated root-help documentation. Concurrent menu/documentation edits were preserved.

Saved source snapshots, lint comparisons, output comparison counts and terminal captures are retained at `/data/data/com.termux/files/usr/tmp/dots-usage-help-pdw_8bjo`. Existing source and wiki edits were preserved. No commit, push, installation or reload is part of this change.
