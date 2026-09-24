# Shared themes

**Status: Implemented flat themes, application templates, Git theme sources and explicit wallpapers.**

The live interface is `dots theme`, using `bin/dots-theme-*` commands. The older
`dots themes` and palette commands remain compatible. The layout follows the local
Omarchy reference while retaining Dots' shell and Neovim palette APIs; see
[decision 0008](decisions/0008-config-catalog-and-theme-apps.md).

## Flat themes and templates

Selectable variants live at `themes/ID/`, normally with `colors.toml`, `theme.toml`,
optional native `palette.toml`, and `backgrounds/`. There are 33 bundled selections:
the previous 17 variants plus Omarchy's additional variants, merging six overlaps.
Overlapping semantic colors use Omarchy's appearance. Its Rosé Pine import is Dawn;
Main and Moon remain separate. Import provenance and license text are retained beside
the themes and under `default/themed`. Background assets are bundled (54.6 MB across 92 files).

`colors.toml` is the shared application palette: quoted `#RRGGBB` assignments plus
optional `mode = "light"` or `"dark"`. Foreground/background are required; ANSI and
semantic roles are resolved from supplied keys with deterministic fallbacks. No
TOML is executed. Desktop-only Omarchy gradient decorations are inert. The native
`palette.toml` retains upstream names for the legacy color-query API. Compatibility
family `flavors/*.toml` files link to these native palettes. Edit `colors.toml` to
change shared application appearance, then publish again with `set` or `refresh`.

Templates under `default/themed/*.tpl` render into a fresh generation. Literal
`{{ color }}`, `{{ color_strip }}` (hex without #) and `{{ color_rgb }}` (comma-separated
RGB) are supported; unresolved variables refuse publication. Personal templates in
`${XDG_CONFIG_HOME:-$HOME/.config}/dots/themed` override bundled templates by filename.
A trusted bundled theme's explicit application file takes precedence over both.
Downloaded themes contribute colors and backgrounds only. Templates never evaluate
shell substitutions, Lua or hooks. Outputs include Kitty, Termux, tmux, btop, bat,
and Yazi data; Zsh/Fish and Neovim data come from the palette generator.

```bash
dots theme list
dots theme show nord
dots theme color accent --theme catppuccin-mocha
dots theme dir nord
dots theme set nord --dry-run
dots theme set nord
dots theme current
dots theme refresh
dots theme switcher                 # optional fzf
```

`set ID` publishes colors only. `--background` additionally requests an explicit
wallpaper action after successful publication; wallpaper failure leaves colors
selected. `--dry-run` prints the selection, publication path and planned connectors
without creating state. `refresh` rebuilds changed inputs and retries available app
reloads even when generation inputs are unchanged. `init [--shell bash|zsh|fish]`
prints sourceable initialization. Theme IDs complete from local data on Tab.

## Presentation

`dots theme` and `dots theme bg` show colored help with subcommand descriptions,
derived from the same static metadata as completion. In terminals, `list` marks the
current theme and shows a count, `show` displays true-color swatches beside hex
values, `set --dry-run` formats the planned paths, and background listings show
readable names/paths. Successful wallpaper actions report the chosen image.
Theme operations use the existing success/error styles.

Automatic color honors NO_COLOR, TERM and the output stream. Override it with
`dots --color=always theme show nord` or disable decoration with
`dots --color=never --icons=never theme list`. Forced color/icons select the human
view even when redirected. Unforced piped listings retain their plain formats.
`current`, `dir`, `color`, `bg current` and `init` retain their machine-consumable
values under every presentation setting; explicit ANSI color formats remain
intentional ANSI output. Legacy plural interfaces retain their existing formats.

## Application connections

The stable path is `${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme`, a symlink
to a complete generation. Kitty includes `~/.local/state/dots/current/theme/kitty.conf`
and a local `dots-theme.conf` connector for nondefault XDG state roots. Tmux uses its
local connector. Btop selects `dots.theme`; Yazi selects the `dots` flavor. Bat reads
the generated `Dots` theme and per-generation cache through shell initialization.
Existing app settings and Neovim transparency remain in their source configurations.

On selection, fixed connector links are created only for configured applications:
Kitty/tmux `dots-theme.conf`, btop `themes/dots.theme`, Yazi `flavors/dots.yazi`, and
Termux `~/.termux/colors.properties`. Existing regular files or symlinks are saved in
the generation's connector journal before replacement; real directories are refused.
Parent application directories must exist. If an application directory itself is
linked into a repository, the connector lives in that source directory. It is
machine state, not a configuration to commit. No generic files installer is involved.

Termux settings reload when available; an existing tmux server reloads the generated
colors; Kitty remote control is used only when KITTY_LISTEN_ON is supplied. Reload
failures report that colors were published and can be retried with `refresh`. Apps
without a running reload adapter pick up the files through their normal startup.
No terminal/editor process is restarted and no plugin or package is installed.

## User themes and wallpapers

```bash
dots theme install https://example.org/owner/theme.git --name my-theme
dots theme update my-theme
dots theme update --all
dots theme remove my-theme
dots theme bg list
dots theme bg next
dots theme bg set /absolute/image.png
dots theme bg set /absolute/image.png --lock-screen
dots theme bg current
```

Git themes live in `${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes/ID`. Installation
accepts HTTPS/SSH Git sources, validates color data in a staged clone, and never
selects automatically. Updates require a managed, clean checkout and fast-forward
history. Removal refuses the current theme. Updates/removals retain prior sources
under `.archives`; `.transactions` records interrupted publication for recovery on
the next lifecycle action. Git hooks and global/system Git configuration are disabled
for these operations. Downloaded scripts/configuration are never sourced. Manual
bundled/user ID collisions refuse selection. Recovery is bounded to theme sources;
there is no generic Git repository manager.

Background discovery includes the selected theme's `backgrounds/` and personal
`~/.config/dots/backgrounds/ID` (with XDG_CONFIG_HOME respected). `next` cycles images;
`select` reapplies the remembered image or the first; `switcher` uses optional fzf.
PNG, JPEG, WebP and BMP are supported. Android uses `termux-wallpaper` (Termux:API),
Wayland uses `swww img`, and X11 uses `feh`; adapters are capability-checked and have
a 15-second timeout. `--lock-screen` is Android-only and does not replace the stored
home-wallpaper selection. WSL/native Windows and video wallpapers are unsupported.
A failed adapter preserves the previous successful record, but an external API may
have changed the device before failing; prior wallpapers are not backed up. Actions
are explicit and journaled, never automatic consequences of ordinary palette set.

## Native palette compatibility


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

## Legacy commands

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

## Native palette source format

Each legacy family has `themes/IDENTIFIER/theme.toml` and `flavors/FLAVOR.toml` links. Flat variants own the native data in `palette.toml`.
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
theme files without hardcoded family lists. Native families use their matching Neovim adapter. Other flat variants use the
built-in generic highlight adapter without executing downloaded code. Adding another app integration is an
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

State lives in `${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes`. Its legacy `current`
token is maintained for compatibility; readers prefer the stable sibling
`dots/current/theme` link. Publication journals restore both pointers on failure. Each `generations/g.*` directory contains its
selection, fingerprint, `palette.json` (schema 1), `init.zsh` (also Bash compatible), `init.fish`,
previous-generation token, and journal status. Readers load one complete generation.
The JSON carries theme, flavor, ID, adapter, mode, native palette values and resolved hex `roles`; it contains no executable
Lua or machine paths. Neovim uses its JSON decoder, not a second TOML parser.

Generations are immutable snapshots. After editing palette files, run `set` again
to publish the changes, including when keeping the same theme/flavor. The fingerprint
covers native flavor files, selected semantic palette and app data, personal/default
templates, metadata and Bash generator modules, plus the input export for pywal16.
Background images do not invalidate palette generations. Unchanged selection
and fingerprint, with all connectors correct, cause no changes to the generation or active pointer. `current` and initialization read the published snapshot even if palette source
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
active link with builtins and reloads only when it changes. It preserves the
previous command's status, hooks, FZF options, and autosuggestion styling. Existing
Catppuccin shell sources remain in use. Bash/Fish receive command completions and
explicit initialization output; automatic shell theme hooks are Zsh-only.

The adapter in `config/nvim` reads shared data at startup and on `FocusGained` or
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

Native plugins retain their syntax highlighting and custom options; shared foreground,
selection and dashboard accent follow the semantic palette. Transparency remains
in the Neovim configuration. Generic themes apply core/editor/plugin highlight groups
from the validated palette. Switching does not rewrite Lua or install plugins.
The sourceable compatibility `themes/bin/theme` delegates to `lib/dots/themes/shell.bash`.
