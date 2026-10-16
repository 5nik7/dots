---
name: dots-cli-presentation
description: Design or improve Dots human CLI output with consistent layouts, semantic colors and readable terminal/plain views while preserving data interfaces. Use for help, listings, diagnostics and result presentation.
---

# Dots CLI Presentation

Read the [presentation contract](../../../docs/presentation.md) and inspect the
command's renderer and nearby commands before choosing a layout. For route,
metadata or completion changes, also follow
[command maintenance](../dots-command-maintenance/SKILL.md).

## Choose the view

Identify which outputs are human views and which are APIs before editing.
Scalar queries, JSON, raw exports, completion and generated shell code bypass
presentation even when color is forced. Preserve documented redirected formats;
disabled color in a terminal should retain a useful human layout.

Use a concise heading and meaningful sections. Prefer aligned rows for comparable
records, labeled details for explanations, and stacked fields when columns do not
fit. Show provenance or status as text rather than relying on color alone. Keep
exact identifiers and complete values available; never truncate the only usable
path or recovery instruction. Avoid adding banners or a pager to routine output.

## Reuse the right renderer

- Ordinary Bash commands use `lib/dots/ui.bash`: shared settings, human-mode
  detection, headings and semantic style tokens. Keep command-specific layouts
  in their owning library. Add missing shared tokens there rather than scattering
  ANSI literals across commands.
- Palette and theme previews use `lib/dots/themes/presentation.py` and its explicit
  theme foreground/background and exact swatches. Do not load a theme or introduce
  a Python dependency merely to decorate an ordinary Bash diagnostic.
- Other implementations should follow the same contract through their existing
  renderer. Do not start a second styling framework for a single command.

Honor color/icon settings, `NO_COLOR`, destination TTY detection and explicit
overrides. Use headings, label accents, path accents and secondary text consistently;
reserve success/warning/error colors for those meanings. Plain views must explain
the same facts. Sanitize display values without changing machine-output bytes.
Authored theme-logo colors have an existing scoped exception; preserve it.

## Apply and verify

Review representative populated, empty and error output as applicable. Check
40/80/120-column layouts, long values, Unicode, plain output and color resets.
Use owned PTYs for automatic terminal behavior and compare scalar/JSON/raw bytes
with decoration forced. Test only applicable cases; do not invent mutation or
interaction flows for a read-only view.

Run the affected suites sequentially on Termux with test-owned roots. Update the
command's user documentation and reference docs alongside the implementation.
Report actual native coverage separately from fixture-only checks. This skill
does not authorize publication, installation, commits or changes to other commands.
