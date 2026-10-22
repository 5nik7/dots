# Default eza theme

Status: Implemented and locally activated (2026-10-22). Owner approved implementation and local activation.

Use `config/eza/themes/catppuccin-mocha-mauve.yml` as the structural reference for `default/themed/eza.yml.tpl`. Preserve its attributes and file categories, normalize SELinux fields to the current eza schema, and replace fixed colors with semantic palette and resolved Git roles. Keep the reference and catalog entry intact.

- [x] Render all selectable palettes in Bash and the native Python controller; support personal templates and trusted bundled overrides, including fingerprints.
- [x] Publish `eza.yml` through the existing connector journal. Resolve `DOTS_APP_EZA_CONFIG`, then `EZA_CONFIG_DIR`, then the platform default (XDG on Unix, APPDATA on Windows). Normal publication requires an existing directory.
- [x] Verify path validation, overrides, ANSI output from installed eza, idempotence, interruption/rollback and missing optional tools in isolated roots.
- [x] Synchronize documentation, preview the current local selection, and activate it with the existing refresh route.

No command, completion, human layout or shell startup changes are needed. Existing publication output follows the [presentation gate](README.md#presentation-gate-for-every-plan). LS_COLORS and EZA_COLORS retain eza's normal precedence. Windows uses the existing native transaction and link adapter without a copy fallback. Native Windows PowerShell 5.1/7 and eza acceptance remain pending when those engines are unavailable locally.

Implementation note: the all-palette check exposed native pywal loading its empty bundled placeholder before the JSON export. Native loading now bypasses both placeholder paths, and the export participates in its fingerprint. Bash pywal import behavior is unchanged.


## Verification

- All 34 bundled palettes render matching eza YAML in Bash and native Python, including a disposable pywal export. The focused eza cases cover real eza 0.23.5 ANSI colors, custom Git colors/reset, environment precedence, backup/undo, interruption/drift, overrides, fingerprints and generation without eza/Vivid/bat.
- Shared file colors: 11 passed. Native CLI: 11 passed, one PowerShell availability skip. Installation: 23 passed initially; the fresh-checkout fixture omitted the new uncommitted template, then passed after including it. Installation adapters: five passed, four platform/engine skips.
- Existing theme workflows: six focused connector/template/recovery cases passed. Theme state: two atomic/idempotence/rollback cases passed. Python/Bash syntax, whitespace and relative Markdown link checks passed.
- Native Windows PowerShell 5.1/7, Linux and WSL runtime/visual acceptance remains pending. Simulated Windows destinations and WSL installation fixtures do not establish native execution.

Local activation: previewed `dots theme set catppuccin-mocha --dry-run`, then ran `dots theme refresh`. The selection remains Catppuccin Mocha; the existing eza directory now contains the journaled `theme.yml` connector. The generation is committed, live eza emits RGB colors without warnings, and the reference YAML checksum is unchanged. Previous generations and recovery records are retained.
