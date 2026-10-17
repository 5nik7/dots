# Blastoff / Starship Dots palette

Status: Implemented and activated on Termux, 2026-10-17.

Create a palette-only default template and a saved `dots` theme copied from the current Starship config. Use exact semantic color names and flat `git_*` aliases; cover all built-in style fields in installed Starship while retaining the current prompt layout and enablement.

The opt-in bundled Starship adapter updates only Dots palettes in the active config and saved theme. Preserve separate module edits, additional palette colors and symlinks. Use journaled writes, Blastoff locks, concurrency guards, no-op detection and truthful provenance.

Validate isolated TOML edits, module coverage, rendering, publication, plugin discovery, failure/rollback and idempotence. Activate via Blastoff after checks, enable the adapter, and refresh without changing the Dots selection. No commits or pushes. Follow the [presentation gate](../docs/presentation.md#acceptance-gate).

## Delivered

The default `blastoff.toml.tpl` generates 48 shared semantic/ANSI names plus 18 resolved Git foreground aliases. The saved `config/blastoff/themes/dots.toml` covers all style-bearing modules supported by installed Starship 1.26.0. Battery settings remain a commented preset because this Termux build omits that module. The palette adapter uses the existing plugin presentation and leaves structured output intact; it adds no prompt-time processes or public command routes.

Activation used `blastoff theme apply local:dots` with the canonical active path, retaining the existing config symlink and creating backup `20261017T052613Z-bebb747aade9`. The Starship plugin is enabled. Two refreshes retained `catppuccin-mocha`, matched all 66 palette values, preserved both configurations byte-for-byte, and left their modification times unchanged on the second refresh. Plugin doctor reported no problems or pending targets; Blastoff reported tracked `local:dots` with matching source. The previous saved `blastoff.toml` remains byte-identical to its pre-task copy.

## Verification

- Palette updater/native Starship: 8 tests passed, including refusal, rollback, symlink guards, module-style coverage and a full prompt in an isolated Git repository.
- Theme plugins: 21 tests passed, including dark/light publication and independent module edits.
- Selected workflow tests passed: every selectable palette renders matching Starship colors, template precedence/atomic output, and connector rollback.
- Git color override/export regression and all 24 Bash dispatcher tests passed.
- Relative Markdown links, `git diff --check`, Bash syntax and ShellCheck passed. ShellCheck used existing-source exclusions including the unrelated SC2015 warning in `render.bash`.

Native evidence is Termux only. No live custom module commands were executed for validation. Future palette changes remain truthful external edits in Blastoff provenance. No commits or pushes were made.
