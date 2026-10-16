# Consistent theme color views

**Status: Implemented, 2026-10-16.**

Use one structured renderer for full palette/style overviews, native previews,
style details and parsed LS_COLORS. Full human `theme show` includes resolved named
colors, terminal aliases, file types, MIME rules and configured extension rules.
Family views remain native-only. Existing scalar, JSON, export and redirected
`show` interfaces remain unchanged. Configured and published sources are labeled.

Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate):
readable plain fallbacks, explicit theme foreground/background, exact swatches,
40/80/120-column layouts, safe display of parsed attributes, empty sections and
invalid-entry reporting. Preserve authored help logos. Do not generate Vivid
rules solely to display a configured overview or publish a live theme during testing.

- [x] Shared renderer and command integration.
- [x] Updated command and user documentation.
- [x] Isolated focused tests, representative layout review, documentation links
      and whitespace checks. Run suites sequentially on Termux.

Verification: all 8 file-color tests, 12 theme-command tests, 24 Bash dispatcher
tests and 8 selected existing theme regressions passed. The file-color suite
covers native Termux PTYs at all three widths with dark/light palettes, inert
LS_COLORS display, Unicode wrapping, native-only previews, and forced-color data
boundaries. Representative plain/colored table layouts were also reviewed in
owned fixtures. Bash syntax and ShellCheck passed (SC1091 dynamic-source lookup
notices excluded); relative Markdown links and `git diff --check` passed.
Other native platforms were not exercised. No live theme was published.
