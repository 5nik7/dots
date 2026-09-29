# Hover styles and file-color integration

Status: implemented and verified on native Termux, 2026-09-29.

The live config still sets literal white/cyan header colors. The native runner
overrides them, masking the difference between tested and configured behavior.
Make the hovered name use file styles and the target use target styles by default,
and migrate the live configuration to explicit per-part style sources.

Provide `hover.styles` entries for path, name, icon, arrow, and link. Each selects
a base source and optional foreground/background/attribute overrides. Support
file, target, directory, native file, custom, and icon/name inheritance where
applicable; retain legacy color options with documented precedence. Keep the
directory prefix a single style using available current-directory metadata or
the ordinary directory category, without ancestry probes. Add independent
visibility controls and icon spacing. Preserve existing fitting options.

Use the shared LS_COLORS resolver; do not run ls/eza, probe the filesystem, or
parse environment variables on redraw. Eza-specific theme formats are outside
this integration. Unknown/disabled LS_COLORS uses native file styles. Explicit
overrides must not mutate shared base styles or leak into other parts.

Apply the [presentation gate](../docs/presentation.md#acceptance-gate): preserve
readable spacing, narrow-window fitting, style isolation, and plain fallbacks.
Exercise per-part sources, resets, false attributes, precedence, icons, hidden
parts, and malformed settings in Lua; run native Yazi against the actual copied
configuration without header overrides. Re-run bundle regressions, documentation
links, and whitespace checks. Native evidence is Termux only. Leave edits
uncommitted and preserve unrelated work.

## Evidence

- Lua layout/style fixtures pass for independent parts, base-style isolation,
  false attributes and color resets, indexed/RGB overrides, native/custom modes,
  icon inheritance, visibility, spacing, legacy precedence, and invalid options.
- Directory resolver fixtures cover ordinary directories, sticky/write metadata,
  and disabled-color native/fixed fallbacks.
- Native Yazi 26.9.1 passes with the actual copied configuration: path directory
  styles, listing/name/icon parity, separate symlink/target colors, and narrow/wide
  rendering. Additional native checks verify attribute removal, icon overrides,
  style isolation, and fallback to the file theme. Existing Git, project, pane,
  folder-rule and preview-padding checks pass as well.
- No subprocess, filesystem lookup, or environment parsing was added to redraws.
  Directory ancestry is not individually styled. Eza-specific rules and native
  Windows/desktop Linux rendering remain outside this evidence.

## Target directory style

`styles.link_dir` independently styles the target directory, including its last
separator; `styles.link` styles the basename. Omitted settings inherit the final
link style for compatibility. The personal config selects ordinary directory
colors. Literal `link_dir_color` and all existing style overrides are supported.
Split after fitting to preserve the combined path cap and shortening behavior;
no target-parent filesystem lookups are added. Lua fixtures cover Unix/Windows
separators, Unicode, root/basename-only/trailing-slash targets, inheritance,
override isolation, and narrow widths; the native fixture uses an absolute
symlink target to check directory/basename colors independently.
