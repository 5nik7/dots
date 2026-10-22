# Default Television theme

Status: Implemented and locally activated on 2026-10-22 with owner authorization.

- [x] Add the semantic default template, both renderer overrides and shared destination resolver.
- [x] Add the journaled connector, including safe creation of a missing themes child in an existing app directory.
- [x] Verify all palettes, both controllers, rollback/recovery, and native dark/light Television in disposable roots.
- [x] Preview and publish the existing live Dots selection, then select dots in the linked Television config.

No new command routes or completion interfaces are introduced. Existing publication views and data output follow the [presentation gate](README.md#presentation-gate-for-every-plan). Preserve unrelated working-tree changes. No commit or push is authorized.

Windows uses LOCALAPPDATA/television/config with Television/XDG/explicit Dots overrides, shared Python rendering and native Store transactions. Native Windows PowerShell 5.1/7, Linux and WSL acceptance remains pending. The theme guide owns the [destination and color behavior](../docs/themes.md#television).


## Verification

All 34 selectable palettes produce matching TOML through Bash and Python, including an isolated Pywal export. All 11 focused cases passed across the initial and targeted reruns. The first run had a test expectation mismatch for forced human presentation (home abbreviation); the corrected case passed without a production presentation change. Native Television 0.15.9 passed dark/light PTY checks at 40/80/120 columns, including actual background and selection RGB sequences. Interrupted parent creation before identity recording refuses ambiguous recovery; a replaced directory and new user content remain intact. Generation without tv, bat or Vivid also passed.

Shared regressions passed: 11 file-color tests, 11 native CLI tests (plus one PowerShell availability skip), four selected publication/recovery tests, and two installation/restore tests. The installation checks passed after correcting the test class name in the invocation. Relative Markdown links, whitespace and Bash/Python syntax checks passed. ShellCheck reports the same SC2015 and source-resolution SC1091 diagnostics as HEAD, with no additions.

## Local activation

Previewed the existing selection and all connector paths, then ran `dots theme refresh`. Generation `g.fmdulVqA` is committed and retains `catppuccin-mocha`; the prior generation `g.SMWiLa3x` remains available. The Television journal records creation of `~/.config/television/themes` and its `dots.toml` connector. The live config links to the repository source; only `[ui] theme` changed from `default` to `dots`. The existing Starship palette plugin reported unchanged. Checksums of all 46 pre-activation modified regular source files were unchanged by refresh.

The original untracked Television config and before/after activation records are retained at `/data/data/com.termux/files/usr/tmp/dots-television-activation-evg6iav2` (temporary recovery evidence, not a permanent backup guarantee). The durable publisher recovery journal is in `~/.local/state/dots/themes/generations/g.fmdulVqA/connectors`; previous generations were retained. Television uses the new theme on its next launch. No commits or pushes were made.
