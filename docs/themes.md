# Shared themes

**Status: Implemented for the families below, Zsh, and the repository's Neovim configuration.**

| Family | Flavors (default first) |
| --- | --- |
| `catppuccin` | `mocha`, `macchiato`, `frappe`, `latte` |
| `tokyonight` | `night`, `storm`, `moon`, `day` |
| `rose-pine` | `main`, `moon`, `dawn` |
| `kanagawa` | `wave`, `dragon`, `lotus` |
| `gruvbox` | `dark`, `light` |
| `pywal16` | `current` (imported generated colors) |

Fixed palettes retain upstream color names. Each fixed family has `SOURCE.md`
and upstream license text beside its metadata. Pywal16 has no fixed palette: see
[its import contract](#pywal16-import).

## Commands

| Route | Output or effect |
| --- | --- |
| `dots themes` | Theme command help |
| `dots themes list [THEME]` | Plain theme identifiers, or a theme's flavor identifiers |
| `dots themes show THEME [FLAVOR]` | Palette table with terminal-aware color swatches |
| `dots themes color THEME FLAVOR COLOR [FORMAT]` | One color value; default format is `hex` |
| `dots themes current` | Plain `theme-flavor` identifier |
| `dots themes init [--shell bash\|zsh\|fish]` | Sourceable initialization; default shell is Zsh |
| `dots themes set THEME [FLAVOR]` | Journaled shared selection; omitted flavor uses the declared default |

The executable names follow the same routes (`dots-themes-set`, for example).
Arguments are positional except `init --shell`. Exit statuses are 0 for success,
1 for data/publication errors, and 2 for invalid arguments. Diagnostics use stderr.
`list`, `current`, `color`, and `init` never decorate their output. `show`, help,
and switch status use the existing color/icon policy. Escape-code color formats
intentionally return ANSI bytes, even when normal UI decoration is disabled.

Formats are `name`, `hex`, `rgb`, `r`, `g`, `b`, `rgb-r`, `rgb-g`, `rgb-b`,
`luminance`, `brightness`, `cmyk`, `ansi-8bit`, `ansi-8bit-value`,
`ansi-8bit-escapecode`, `ansi-24bit`, `ansi-24bit-escapecode`, and `esc`.
RGB and CMYK channels are space separated; CMYK channels are integer percentages.

## Palette source format

Each theme has `themes/IDENTIFIER/theme.toml` and `flavors/FLAVOR.toml`.
The root can be selected with `DOTHEMES`, then `THEMES`; otherwise it is relative
to the installed engine. Family identifiers allow internal hyphens (`rose-pine`);
flavor identifiers use `[a-z][a-z0-9_]*`. Native color keys use
`[a-zA-Z_][a-zA-Z0-9_]*`, including Kanagawa's `sumiInk3` and Rosé Pine's `_nc`.
Persisted `theme-flavor` identifiers split at the final hyphen.

A flavor contains only ordered color assignments:

```toml
rosewater = "#f5e0dc"
blue = "#89b4fa"
base = "#1e1e2e"
```

The example is abbreviated; Catppuccin requires its existing 26 named colors.
Its flavors are Mocha, Macchiato, Frappé (`frappe`), and Latte.

Metadata separates names and integrations from color values:

```toml
name = "Catppuccin"
default_flavor = "mocha"
[roles]
background = "base"
foreground = "text"
muted = "overlay0"
accent = "mauve"
selection = "surface1"
error = "red"
warning = "yellow"
info = "blue"
hint = "teal"
[integrations]
nvim = "catppuccin"
vivid = "catppuccin"
```

All nine roles are required and must reference colors in the selected flavor.
Optional `[roles.FLAVOR]` tables override individual mappings, useful when a light
variant has different native names. Querying, previewing and initialization discover
theme files without hardcoded family lists. Persisted switching requires a supported
family/flavor and its matching Neovim adapter. Adding another app integration is an
explicit adapter change; metadata cannot run commands. `vivid` records the integration
identity; Catppuccin retains its Vivid path with a semantic-color fallback when
unavailable. Other families generate basic
RGB directory/file rules directly from roles, retaining original custom LS_COLORS
entries without requiring Vivid.

The supported TOML subset includes bare keys, double-quoted strings without
escapes, single-quoted literal strings, blank lines, full-line/trailing comments,
and the `roles`, `roles.FLAVOR` and `integrations` tables in metadata. CRLF is accepted. Colors
must be six hex digits prefixed with `#`. Duplicate keys/tables, unknown metadata
keys, missing roles, control characters, arrays, numbers, multiline strings,
escapes and other unsupported TOML constructs fail with file/line diagnostics
where applicable. Palette input is never sourced or evaluated.

## Pywal16 import

Generate a palette using your existing pywal16/wal installation, then publish it:

```bash
dots themes set pywal16
# After generating another wallpaper palette, run the same command again.
```

`themes/pywal16/theme.toml` declares `source = "pywal16"`; the comment-only
`flavors/current.toml` is a discovery marker. Input is `DOTS_PYWAL_FILE` when set,
otherwise `$PYWAL_CACHE_DIR/colors.sh`, otherwise
`${XDG_CACHE_HOME:-$HOME/.cache}/wal/colors.sh`. The reader accepts literal,
single- or double-quoted `#RRGGBB` assignments for `background`, `foreground`,
`cursor` and `color0` through `color15`. All 19 are required and unique. It rejects
NUL, exports over 64 KiB, malformed recognized assignments, and missing colors;
other export lines are ignored. It never sources shell/Vimscript, executes `wal`,
changes wallpapers, or watches the cache.

Missing/invalid input refuses publication before state creation. Source changes
during generation refuse the switch. Published snapshots keep working after the
cache changes or disappears. `show`/`color` query the current export, while `init`
loads the published selection. Bash/Zsh/Fish can list and complete the `current`
flavor without an export; color completion requires valid input.

## Selection and generated data

Read-only selection uses the active shared generation if present, otherwise
`$HOME/.theme`, the theme root's `.theme`, then `.default`. These legacy files
are never automatically rewritten or imported. `DOTS_THEME_SELECTION=theme-flavor`
is an explicit session-only override used by the existing `set_theme ID` function.
`change_theme ID` persists through `dots themes set`, then updates the calling Zsh.

State lives in `${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes`. `current` holds
one validated generation token. Each `generations/g.*` directory contains its
selection, fingerprint, `palette.json` (schema 1), `init.zsh` (also Bash compatible), `init.fish`,
previous-generation token, and journal status. Readers load one complete generation.
The JSON carries theme, flavor, native palette values and resolved hex `roles`; it contains no executable
Lua or machine paths. Neovim uses its JSON decoder, not a second TOML parser.

Generations are immutable snapshots. After editing palette files, run `set` again
to publish the changes, including when keeping the same theme/flavor. The fingerprint
covers all flavor files, metadata and Bash generator modules, plus the input export
for pywal16. Unchanged selection
and fingerprint cause no changes to the generation or active pointer. `current` and initialization read the published snapshot even if palette source
files are temporarily invalid. Explicit palette queries read the source files. Previous
complete generations are retained; no automatic pruning or general undo command
is provided. To return to a previous flavor, use `set` with that flavor.

Legacy initialization caches live under `${XDG_CACHE_HOME:-$HOME/.cache}/dots/themes`.
These are disposable generated data, keyed by content and shell. Publication uses
a temporary file and rename. Bash arithmetic handles integer conversions; AWK
batches fractional conversions for each palette while preserving legacy rounding.
Basic help and hex/RGB queries do not require AWK. Initialization needs AWK and
`sha256sum`; switching additionally requires `flock`, `sync -f`, and standard
file utilities. Dependencies are required only on the paths using them.

## Shell and Neovim behavior

`catppuccin` retains its positional/flag interface, format ordering, raw/array
output, Bash/Zsh completion generators, and all flavor-prefixed initialization
arrays. `current_theme` resolves the selected family. For non-Catppuccin families,
it supports native color/flavor/format positional arguments, `-c`/`-f`/`-F`, raw/array
output and initialization; the Catppuccin-specific all-flavor and completion-generator
options remain on `catppuccin`. Generic initialization exposes
`dots_palette` and `dots_roles` associative arrays in Bash/Zsh; Fish receives
`dots_color_NAME` and `dots_role_NAME` variables plus `THEME` and `FLAVOR`.
The Catppuccin Bash/Zsh initialization also includes the legacy color arrays.

Zsh loads generated initialization at startup. Its prompt hook reads the small
active token with builtins and reloads only when it changes. It preserves the
previous command's status, hooks, FZF options, and autosuggestion styling. Existing
Catppuccin shell sources remain in use. Bash/Fish receive command completions and
explicit initialization output; automatic shell theme hooks are Zsh-only.

The adapter in `configs/nvim` reads shared data at startup and on `FocusGained` or
`VimResume`. `:DotsThemeReload` explicitly retries/reapplies it when focus reporting
is unavailable. Native plugin adapters apply each palette through the corresponding
plugin's configuration API; pywal16 uses upstream highlights with validated snapshot
colors through `dots-pywal16`, avoiding the plugin's live Vimscript import. Light/dark
background follows the variant (or pywal16 background brightness). Colorscheme events
update the dashboard palette without changing its animation. Without shared state,
existing Mocha configuration remains the default. Invalid data or missing/failing
plugins retain previous colors and report a bounded warning; manual reload retries.

The additional plugins are declared in `lua/plugins/dots_themes.lua` and lazy-loaded
when needed. Install missing declarations through your normal `:Lazy` workflow, then
use `:DotsThemeReload`. Publishing with the CLI validates adapter support, not local
plugin installation. Neither the CLI nor the adapter installs plugins itself.

Mocha keeps its existing custom highlights. Other Catppuccin flavors use their own `surface0`
for selected lines, `surface1` for visual selections and line numbers, `surface2`
for comments, and `mauve` for dashboard icons. Transparency and plugin options remain
in the Neovim configuration. Switching never rewrites that configuration, installs
plugins, contacts another editor process, or edits other application configs.
