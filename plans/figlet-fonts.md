# Dots FIGlet fonts

Status: Complete; fonts, managed Termux links and local acceptance verified.

## Delivery

- Keep the approved five-row `dots.flf` capitals and six-row `dots-mixed.flf` in `config/figlet`. Both include Unicode extras; the mixed font has distinct lowercase.
- Register separate file links under the Termux profile, owned by the root Dots repository. Discover the installed directory with `figlet -I2`; do not replace the package-owned font directory.
- Add the Termux-only `${PREFIX}` destination token needed to describe these links portably. Missing PREFIX is unmapped; relative, root-only, traversal and control-containing values are refused. Other platforms do not resolve this token.
- Use the existing mapping CLI and Store for catalog/profile/link/receipt changes. Preserve occupied targets, unrelated profile edits, the original `logo.txt` and existing fonts.
- Document usage and destination behavior, then rebuild/check the available Wiki.

## Integration assessment

Primary owner: `dots-files-maintenance`, with profile and documentation maintenance. No configuration integration change needed: font artwork is static and FIGlet already owns layout options. No menu changes: these are assets selected with existing FIGlet options. Command routes, completion providers and human renderers remain shared and unchanged; the existing `files edit --target` help is clarified. Bash and native PowerShell use the same catalog controller; native Windows has no mapping for the Termux prefix. Installer integration consists of the two ordinary profile mappings; no package installation, startup work or automatic FIGlet invocation is added. The [presentation gate](README.md#presentation-gate-for-every-plan) applies to existing Files views; this change adds no Dots renderer.

## Acceptance

- Isolated token tests cover Termux resolution, inactive platforms, invalid roots, traversal and reverse target conversion.
- Isolated registration verifies a prefix link, central identity/profile mapping, receipts, repeat no-op and undo.
- Run file-platform, catalog, registration, mapping and profile-backend suites sequentially, plus metadata and relative-link checks.
- Verify the installed fonts resolve to repository sources and render by name, including `25°C`. The prior full glyph and 40/80/120-column Termux acceptance remains valid when the copied bytes match.
- Native Windows, Linux and WSL font rendering remain unverified; only Termux receives installed font mappings.

## Completed verification

File-platform (5), catalog (10), registration (17), profile-backend (14) and mapping (29) cases passed in owned roots. The new registration test checks semantic JSON restoration because existing undo canonicalizes JSON formatting. Command metadata validation, generated-manual freshness, relative Markdown links and `git diff --check` passed. The local Wiki was rebuilt and reports healthy.

Both installed links resolve to the repository fonts; initial installation preserved the fully validated preview bytes. Rendering by installed name, including `25°C`, matches direct-path rendering. A second live link preview reports both unchanged. Removing the two added entries from the resulting profile/registry documents reproduces their pre-install data, confirming unrelated mappings and fields were preserved. The durable usage reference is [Fonts](../docs/fonts.md#figlet-lettering).

The subsequent artwork revision uses the user's five-row R design and gives K/X stepped box-drawing strokes. Outer ends are capped on K/X and, following the user's bottom-height correction, on R's bottom row. Both fonts share the revised capitals; the all-uppercase font's lowercase aliases follow them. Y and the mixed font's distinct lowercase remain unchanged. Verification covers the changed glyphs through installed FIGlet names, font structure, unchanged remaining bytes and wrapping at 40/80/120 columns; the R baseline correction was additionally verified through both installed fonts.
