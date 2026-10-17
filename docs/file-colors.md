# Theme file and Git colors

The publisher and `theme colors` require Python 3.11+ for standard-library TOML parsing.
Shells consume published data without Python.

Dots owns one set of file styles for queries, LS_COLORS, exports and dots.yazi.
The default rules preserve the former Vivid template's colors. Vivid supplies its
extension database when installed. Without Vivid, basic filesystem types and
explicit suffix rules still work; exports report `coverage = "basic"`.

## Query and edit

```sh
theme colors
theme colors type
theme colors type dir hex
theme colors type dir --json
theme colors mime image/png --json
theme colors extension .lua --json
theme colors match ./photo.png --mime image/png --json
theme colors parse --env --json
printf '%s' "$LS_COLORS" | theme colors parse --stdin --json
theme colors export lua
theme colors export json
theme colors export ls-colors
```

Scalar queries return the foreground, defaulting to hex. `rgb`, `ansi-24bit` and
`esc` are also supported. `--style` shows the complete style; `--json` includes
its source. Extension queries list explicit rules; use `match` or `parse` for
Vivid database suffixes. Missing keys fail instead of inventing a value. MIME queries accept
an exact type or match its wildcard group. `parse` reads data and reports invalid
entries; it never evaluates input. Suffix order and explicit resets are retained.

Queries use the current published snapshot when available. `--configured` reads
saved rules instead. `--theme ID` resolves another theme without selecting it.
Before the first publication, queries resolve the configured default.

## Human color views

`theme colors` shows named colors, terminal colors (`color0` through `color15`),
file types, MIME rules, configured extension rules and Git styles in separate counted sections.
Palette rows include exact swatches and hex values. Style tables show foreground,
background and attributes; `unset` means no field is specified, while `reset`
explicitly requests the terminal default. Explicit false attributes remain visible.
Empty groups are labeled. Narrow terminals stack fields and wrap long names.

`dots theme show ID` uses the same complete overview in a terminal or with forced
human presentation. It reads configured sources; `theme colors` retains its
published-snapshot default. Both views label their source. For a configured overview
when redirecting output, use `theme colors --theme ID` or `theme colors --configured`.
Redirected, unforced `show` retains its existing heading and
semantic-color TSV rows. Family previews and `show --native` share the table
layout but display only native palette values.

`type`, `mime` and `extension` list full styles as tables. `--style` and `match`
show labeled details and available rule sources. `parse` lists filesystem and
suffix rules, including literal SGR sequences, indexed colors and invalid-entry
diagnostics; suffix order and duplicates remain visible. Attributes such as blink
and hidden are described without being activated. Parsing remains usable without
a configured theme. Generated Vivid suffixes are not expanded in the overview;
use `parse` to inspect them.

Colored views use the addressed theme's foreground/background with readable text
and exact swatches. `--color=none` retains the readable layout without styling.
JSON, scalar queries, exports and edit dry-run JSON keep their existing bytes and
schemas regardless of presentation settings. Configured overviews and style
queries do not require Vivid generation. All views are read-only.

## Save and publish

```sh
theme colors set type dir --fg blue --bold true
theme colors set extension .lua --fg yellow --italic true
theme colors set mime 'image/*' --fg magenta --theme tokyonight-night
theme colors set type dir --fg '#123456' --dry-run
theme colors reset type dir --theme tokyonight-night
theme colors set type executable --fg green --apply
```

Set/reset change shared overrides by default. `--theme ID` edits per-ID overrides.
Edits use the existing file transaction store with backups and drift guards;
`dots files history` shows their journals. Saving does not change running apps.
`--apply` refreshes the **current** selection; it does not select the ID being edited.
If refresh fails, the saved rule remains and the command reports it as unpublished.
`theme refresh` retries publication. `--dry-run` produces a JSON edit preview.

## Rule ownership

Precedence is bundled `default/file-colors.toml`, theme-local `file-colors.toml`,
`$XDG_CONFIG_HOME/dots/file-colors.toml`, then
`$XDG_CONFIG_HOME/dots/file-colors/ID/rules.toml`. The config root defaults to
`~/.config`. Fields merge independently; reset removes the selected override and
reveals lower-priority rules. The setter manages its entire override file and
normalizes its formatting; edit comments outside that generated file if needed.

```toml
[type.dir]
fg = "blue"
bold = true

[extension.".lua"]
fg = "yellow"
bg = "reset"
italic = true

[mime."image/*"]
use = "media"
```

`fg`/`bg` accept a palette name, `#RRGGBB`, or `reset`. `use` inherits a named type
style. Attributes are `bold`, `dim`, `italic`, `underline`, `blink`, `blink_rapid`,
`reversed`, `hidden`, and `crossed`; explicit false clears an inherited attribute.
Vivid-derived category suffixes support [its font attributes](https://github.com/sharkdp/vivid/blob/v0.11.0/src/font_style.rs) (bold, faint, italic,
underline and blinking); reversed, hidden and crossed are preserved in full-style
exports and exact core/explicit-suffix rules. Use explicit suffix rules when those
attributes must apply in `ls`.
Unknown fields, malformed TOML, missing palette references and cycles fail before
publication. Shared native-only color references must exist in each selected theme.

Filesystem/link/device/executable styles precede suffixes. Explicit suffix rules
precede explicit MIME rules, then Vivid suffixes, default MIME groups and the
regular-file style. Exact MIME rules precede wildcard groups. Matching uses file
metadata and optionally supplied MIME; it does not inspect content. Yazi uses its
cached MIME value when available. LS_COLORS has no MIME field: MIME-only overrides
apply to MIME-aware consumers; use suffix rules to customize `ls` too.

## Published interface

Each theme generation contains `colors.json`, `colors.lua` and raw `ls_colors`.
They publish atomically with the existing theme files; no consumer edits them.
The JSON/Lua object has schema 1, id, mode, colors, styles, rules, provenance,
coverage, ls_colors and parsed ls_rules. Named colors are hex strings;
`colors.type.dir` and `colors.mime["image/*"]` are foreground shortcuts.
`styles.type.dir` is the complete style. Native palette colors remain available
through the original palette.json interface if a name collides with a namespace.
Lua is a generated `return { ... }` table, with escaped literal data only.

Bash/Zsh/Fish/Nushell/Xonsh/PowerShell adapters load the published LS_COLORS string.
Older generations retain their prior fallback until refreshed. The default Vivid
template expands the shared style model; explicit custom templates keep their
existing precedence for extension categories, while Dots core and explicit suffix
rules remain authoritative in the exported LS_COLORS.

## Validation

Run `python3 -B tools/test_file_colors.py -v` in owned roots. Existing publication,
FSH, shell-environment and native plugin checks cover the connected paths. Tests
must isolate DDS sockets as well as home/config/state/cache directories.

## Git styles

**Implemented.** The `git` group styles Dots-owned repository identities and Git status metadata. File paths retain their type/MIME styles. It shares the same four configuration layers, field merging, validation, journaled set/reset operations and explicit publication as file rules; `[git.repo]` lives alongside `[type.dir]` in `file-colors.toml`. `use` continues to inherit a named **type** style.

| Roles | Default foreground | Attributes |
| --- | --- | --- |
| `repo` | `magenta` | bold |
| `repo_owned` | `yellow` | bold |
| `branch`, `untracked` | `magenta` | none |
| `modified`, `behind`, `detached`, `missing` | `warning` | none |
| `staged`, `added`, `clean`, `ahead` | `green` | none |
| `deleted`, `blocked` | `error` | none |
| `conflict` | `error` | bold |
| `renamed`, `copied` | `cyan` | none |
| `ignored` | `muted` | dim |

```sh
dots theme colors git
dots theme colors git branch
dots theme colors git modified --style
dots theme colors set git untracked --fg cyan
dots theme colors reset git untracked
dots theme refresh
```

Git role names use lowercase letters, digits and underscores, starting with a letter. Custom keys are supported for querying/export; the Dots Git renderer uses the roles above. Scalar formats, `--json`, `--theme`, `--configured`, `--dry-run` and `--apply` work as for file styles. Complete human overviews include a counted Git section; native palette previews retain their original scope. JSON/Lua exports add `colors.git`, `styles.git`, `rules.git` and `provenance.git` within schema 1. Git rules never affect file matching, Vivid or LS_COLORS.

Older snapshots without Git data remain readable. Their overview explains that Git styles need a refresh; explicit Git queries fail with `theme refresh` / `--configured` guidance instead of mixing configured data into a published snapshot. Ordinary Git views use terminal-color defaults until refreshed. See [Git output](git.md#theme-colors) for role application.
