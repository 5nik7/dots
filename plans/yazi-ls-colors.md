# Yazi LS_COLORS integration

**Status: Implemented, including target-style header; isolated native Termux verification complete**

## Accepted behavior

Read inherited `LS_COLORS` once during `dots.yazi` setup and use a shared resolver for file panes and the header's hovered icon/name. Preserve the full foreground/background/attribute style, including explicit resets. Enable through `ls_colors.enabled`; `hover.styles.name.source = "file"` selects the same base style in the header. The personal config uses that default for the name, `styles.icon.source = "name"` for its icon, and `styles.link.source = "target"` for the basename after the arrow, with `styles.link_dir` independently styling its directory portion, using the target’s basename and available metadata. Ordinary files, broken links, unavailable metadata and disabled/unset LS_COLORS retain the existing file-style fallback. File-pane matching stays unchanged. Keep explicit header colors supported. Empty/unset/disabled LS_COLORS retains native Yazi styling. Restart Yazi after changing the environment.

Use filename suffix and available file metadata with GNU ls precedence. No subprocesses, filesystem probes, or environment parsing during redraw. Capability/door detection remains unsupported. Preserve cursor indicators, search highlights, selection and Git decorations. Generated theme outputs and live state are outside this source edit.

## Implementation and acceptance

- [x] Shared parser, matching, style conversion and file-pane integration.
- [x] Header full-style support and explicit color compatibility.
- [x] Lua parser/matching/style regressions and GNU ls oracle checks.
- [x] Isolated native Termux style, cursor overlay and narrow/wide rendering checks.
- [x] Documentation, relative links and whitespace checks.

## Presentation gate

Apply the [presentation acceptance gate](../docs/presentation.md#acceptance-gate) to the Yazi UI: colored filenames, icons, selection/search overlays, header isolation and 40/80/160-column fitting. CLI structured output and Gum do not apply. Keep native Termux evidence distinct from Lua fixtures and other platforms. Automated style assertions do not establish visual equivalence for every font/terminal.

## Evidence

- Lua tests cover parser/matching, ANSI/indexed/RGB styles, resets, escaped delimiters, malformed input, setup/fallback, and header style isolation.
- GNU coreutils 9.11 oracle: 350 comparisons passed on Termux, including mixed-case collisions, overlapping suffixes, permissions, symlinks, FIFOs and sockets. Native hard-link creation is refused by this filesystem; hard-link and device branches have Lua metadata coverage.
- A read-only inherited-palette sample (657 suffixes) measured about 14 ms per parse over 50 runs and 0.107 ms per unmatched file over 10,000 resolver calls before the final case-collision refinement. These are Lua microbenchmarks, not end-to-end UI latency claims.

- Native Yazi 26.9.1 on Termux: parent/current/directory-preview style values, ANSI/indexed/RGB colors, header parity, cursor overlays, disabled fallback, 40/80/160-column redraws, existing bundle workflows, and clean exit without errors or deprecation notices passed.
- Lua syntax, changed Markdown links, repository documentation verification, and whitespace checks passed. Native Windows/desktop Linux and owner visual/font comparison remain unverified.

## Separate symlink/target styles and preview padding

- [x] Use `styles.name.source = "file"` in the personal config and `styles.link.source = "target"` for the path after the arrow. Optional `name_color = "target"` and explicit colors remain supported.
- [x] Resolve target metadata/basename without mutating shared rules or adding filesystem/subprocess work.
- [x] Treat reset backgrounds on non-reversed rows as unfilled when computing indicator caps; retain normal filled/reversed caps and disabled fallback.
- [x] Verify directory/executable/extension targets, relative and absolute paths, broken/missing-metadata fallbacks, span isolation and unchanged listings.
- [x] Verify native separate symlink/target styles, preview spacing with block padding, filled caps, narrow/wide rendering, documentation and whitespace.

Evidence: Lua checks cover separate name/target styles at 0–100 columns. Native Termux confirms symlink color before the arrow and `.txt` target styling after it, verifies reset-background preview rows use spaces while highlighted current rows retain caps with their effective background color, and passes 40/80/160-column rendering and existing bundle checks. Matching is unchanged from the 350 GNU ls comparisons above; native hard-link creation remains unavailable as recorded there.

The [hover styles follow-up](yazi-hover-styles.md) makes file styling the default and provides explicit per-part sources/overrides while retaining legacy color options. Its native test exercises the actual copied config without forced hover colors.
