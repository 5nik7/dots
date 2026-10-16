---
name: dots-cli-presentation
description: Format Dots human CLI output with Git-style layouts, semantic colors, progress, and file-type colors/icons while preserving customized theme views and data interfaces. Use for help, listings, diagnostics and operation results.
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

## Git reference, resources and progress

Use `lib/dots/git/ui.bash` and `status.bash` as the ordinary-view reference:
concise cyan heading, blue identities/labels, grouped items, separate semantic
status text, and an accurate completion or partial-failure summary. Keep a view's
useful domain-specific structure; do not mechanically turn every result into a
Git status table. Audit every requested route through its owning renderer,
including aliases, help, empty results and bootstrap errors. Record already
conforming views and intentional exceptions in the focused plan.

Render actual filesystem resources through `dots::resource_row`/`dots::resource`
or Python `Presentation.resource_detail`/`resource`. Pass the actual path
separately from its display text, and pass a known intended kind for a planned
resource when available. Repository IDs, command examples, URLs, keys and scalar
path APIs are not resource views. Keep statuses independently colored. Use the
published Dots file-style table and the shared icon/MIME registry; never call a
file classifier or spawn a style query per row. Do not read contents or generate
a theme merely to color a filename. Missing/old snapshots have bounded fallbacks.
Resource icons obey `DOTS_ICONS`; full paths remain usable with icons disabled.

Preserve customized surfaces: theme panels keep the addressed palette and exact
swatches; Anodize keeps its authored mark; selectors retain their native widget
style and internal selection labels. Use resource context overrides inside
customized panels, never the active theme accidentally. Do not restyle child or
third-party output forwarded by Dots.

Use existing `progress.bash`/`progress.py` scopes: delayed bars for known counts,
spinners for unknown work, static phases for children that print or prompt.
Clear before results/prompts and clean up on interruption. Do not add animation
to help, dry runs, redirected/data output or ordinary shell startup. The
presentation contract owns delay, controls and lifecycle details.

For cross-renderer changes, run `tools/test_resources.py`, the applicable
presentation/progress and command suites, and actual 40/80/120-column PTYs.
Compare published rules, malformed/older snapshots, color/icon independence,
control-character safety, and machine-output bytes under forced decoration.
Measure representative listings; preserve the dependency-free help/dispatch path.
