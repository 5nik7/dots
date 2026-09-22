# 0007: Data-driven themes and bounded Bash selection state

Status: Accepted
Date: 2026-09-22

## Context

The owner approved extracting Catppuccin's four palettes into TOML, preserving
legacy script APIs, adding theme commands and completion, and synchronizing Zsh
and Neovim while further Go implementation remains paused.

## Decision

Use a strict documented TOML subset parsed as data in Bash, semantic role mappings,
and a shared engine under `lib/dots/themes`. Keep native palette names. Neovim
consumes generated JSON and Zsh consumes generated initialization, avoiding repeated
CLI execution on editor focus and ordinary prompts. Keep Mocha's appearance and
adapt other flavors' custom highlights to their own palette.

A bounded shared Bash publisher owns only the theme state subtree. It preflights,
locks, records previous selection, prepares and flushes immutable generations,
and atomically changes the active token. Failure restores the previous token;
the next switch recovers interrupted prepared journals. This is an explicit
addition to decision 0006, not a general filesystem transaction engine or an
exception allowing arbitrary extensions to overwrite application configs.

Completion adds four closed core-owned data types to Bash metadata: `theme`,
`flavor`, `palette-color`, and `color-format`. They read palette data without
executing extensions. The separate Go protocol remains unchanged.

## Consequences

No TOML runtime package or Python runtime dependency is introduced. Full TOML is
not supported. Basic help stays dependency-light; fractional conversions need
AWK and durable switching needs `flock` and `sync -f`. Native Windows support is
not claimed. Previous generations remain available; retention and general undo
are deferred. See [theme behavior](../themes.md) and [safety](../safety.md#theme-selection-publication)
for the exact boundaries and recovery rules.
