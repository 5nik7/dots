# 0011: Anodize palette authoring

**Status: Accepted and implemented for the core/CLI slice, 2026-09-25.**

## Context

The owner requested an independent Aether-derived theme engine named Anodize, first as a Dots core component and CLI, with a future Android application and possible TUI. A separate repository owns Anodize.nvim. General Go migration remains paused; this is an explicit scoped exception.

## Decision

Keep a standard-library-only Go module in `anodize/`. Its exported package accepts image bytes, seed colors and recipes, and returns colors; it performs no filesystem writes or subprocess execution. A private executable exchanges bounded JSON with the CLI. Adapt the selected upstream color algorithms with [recorded provenance](../../anodize/PROVENANCE.md), excluding the desktop application, caches, downloads and app writers.

Expose `anodize` and `dots anodize` through the live command framework. Python owns authoring orchestration and shares the existing Presentation and transaction Store. Bash retains theme rendering, publication and fixed wallpaper adapters. Saved themes use the established theme directory layout plus an editable baseline/adjustment/override recipe. Mutation requires preview/confirmation or explicit `--yes`; read-only actions create no persistent state.

Add normalized `colors` to published palette JSON without removing existing schema-1 fields. Do not load the Go executable at shell startup. Build explicitly and keep binaries out of Git. Android, TUI and arbitrary hooks are separate follow-up work. The completed Anodize.nvim handoff is integrated through Dots-owned local plugin configuration, compatibility bridge and personal highlights; live activation is left to a normal editor restart.

## Consequences and alternatives

The reusable color engine can support future frontends without importing CLI filesystem policy. The CLI requires the existing Bash/Python environment plus a built engine. A monolithic Go rewrite would duplicate mature safety and publication behavior and expand the paused migration. Reusing Aether's desktop backend would couple the core to Wails, platform paths and side effects. Neither is needed for this slice. The local Theme Hook Plugin Manager reference manages Omarchy theme-set.d scripts that can rewrite application configuration and run reload commands. It informed the separation between color data and app integration; importing its arbitrary hook execution would bypass this bounded publisher, so hooks remain deferred.

## Validation

`python3 -B tools/verify_anodize.py check` isolates toolchain caches and fixture roots, runs Go tests/vet and authoring integration tests. Existing theme, file and dispatcher suites cover shared boundaries. [Anodize documentation](../anodize.md) defines implemented behavior and limitations; [the focused plan](../../plans/anodize.md) records completed integration and its verification limits, and links separately proposed follow-up work.
