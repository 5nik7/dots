# Shared themes

**Status: Implemented flat themes, application templates, Git theme sources, explicit wallpapers and opt-in local theme plugins.**

The sole theme CLI is `dots theme`, using `bin/dots-theme-*` commands.
Standalone palette helpers remain available; the plural CLI was removed under
[decision 0012](decisions/0012-unified-theme-cli.md). The layout follows the local
Omarchy reference while retaining Dots' shell and Neovim palette APIs; see
[decision 0008](decisions/0008-config-catalog-and-theme-apps.md).

Theme preparation, rendering, bat caches, publication, quiet reloads and installed-source validation use [terminal progress](presentation.md#operation-progress). Batch updates show processed checkout counts. Downloads, tmux reloads and wallpaper adapters use static phase messages to keep child output readable. `DOTS_PROGRESS=never` disables these displays. Raw queries, shell initialization and dry runs stay undecorated.

## Local theme plugins

`dots theme plugins list|enable|disable|run|doctor` adds explicitly enabled GTK 3,
Qt6ct and trusted local hooks. The shared post-commit publisher covers theme set,
refresh and Anodize apply; unchanged refresh retries integrations. Enable/disable
only persist selection. Bundled app writes use journaled copies; arbitrary local
hook effects are outside publication rollback. See [plugin authoring and safety](theme-plugins.md).
Downloaded themes remain data-only and never provide executable hooks.

## Flat themes and templates

Selectable variants live at `themes/ID/`, normally with `colors.toml`, `theme.toml`,
optional native `palette.toml`, and `backgrounds/`. There are 33 flat variants plus
the dynamic `pywal16-current` selection (34 bundled selections in total).
The flat variants include the previous palette variants and Omarchy imports, merging six overlaps.
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
Yazi and Pi data; Zsh/Fish and Neovim data come from the palette generator.

`fzf.sh.tpl` supplies FZF colors to published Bash/Zsh and Fish initialization.
Bash and Zsh refresh them at the next prompt; Fish users can explicitly load
`dots theme init` output for their shell. Running FZF processes retain their
existing environment. Personal templates override the defaults, and a bundled
`fzf.sh` application file takes precedence over both. Refresh tracks these edits.
Zsh completion and fzf-tab file colors resolve `LS_COLORS` at each completion, rather
than retaining startup colors. After updating the shell adapter or completion
configuration itself, open a fresh shell or reload your shell configuration once.

The FZF template accepts one `export _FZF_COLORS_="..."` assignment (including
backslash-newline continuations), blank lines, comments, and the optional exact
`export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"` line. Colors
must be `#RRGGBB`, `-1`, or ANSI indices 0–255, optionally combined with style
attributes such as `regular`, `bold`, `strip`, `italic` and `underline`. Selectors
use literal lowercase names, hyphens and plus signs. Other statements or malformed
values refuse publication. Dots parses this file as data; it never sources it.

Shell initialization preserves the original FZF options and replaces its generated
color option on repeat loads. Dots' Bash/Zsh adapters also preserve configured bindings
and preview settings. Published template colors supersede the legacy Catppuccin
FZF adapter; other legacy adapters remain. Older generations and session-only
`set_theme ID` retain the existing FZF behavior. FZF needs no app connector. Bash/Zsh use their native prompt hooks; Fish remains explicit.

`gum_env.sh.tpl` renders to `gum_env.sh` under the active theme path. It exports
all 116 Gum color variables directly in Bash or Zsh, without Lua or Hilbish.
Interactive Bash/Zsh startup automatically sources the readable published file
at `${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh`.
Missing files are optional; loading needs no Gum executable or theme regeneration.
Both shells reload it through their published-theme refresh hooks and configuration reloads. Publication itself never
executes the artifact. Personal `gum_env.sh.tpl` templates and bundled
`gum_env.sh` overrides follow the same rendering precedence as other app files.
To publish and explicitly load the current colors:

```bash
dots theme refresh
source "${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh"
```

The explicit source command also updates an already-running Bash session immediately.
Bash and Zsh pick up published generation changes at their next prompt. Session-only
`set_theme ID` calls do not load a different Gum artifact. Noninteractive startup,
CLI data paths and generated `dots theme init` output do not source this file.
Already-running Gum processes retain their environment. The generic Gum Style
exports include `FOREGROUND`, `BACKGROUND`, `BORDER_FOREGROUND` and
`BORDER_BACKGROUND`; automatic and explicit sourcing set these alongside `GUM_*` variables.
Sourcing runs trusted user-owned shell configuration, including any overrides.
The shell template replaces `gum_env.lua.tpl`; existing personal Lua templates
or bundled Lua overrides are not converted. Move custom color assignments to
`gum_env.sh.tpl` or `gum_env.sh` using `export NAME='#RRGGBB'` syntax.
This consumer targets Bash/Zsh; Fish and PowerShell need their own export syntax.

The bundled `bat.tmTheme.tpl` provides 70 syntax rules, including language-specific,
Markdown and diff scopes. Comments and brackets use `muted`, selection and line
highlights use `selection`, and diff headers use `blue`. Its rendered `bat.tmTheme`
is also copied to `yazi/tmtheme.xml` in the same generation; `yazi.toml` becomes
`yazi/flavor.toml`. The Yazi `flavors/dots.yazi` connector points to that generated
`yazi` directory, so both applications share the syntax theme. Edit the template
and run `dots theme refresh` to publish changes; generated files are replaced on
publication. Personal templates and bundled application overrides retain the
precedence described above.

```bash
dots theme list
dots theme show nord
dots theme color accent --theme catppuccin-mocha
dots theme dir nord
dots theme set nord --dry-run
dots theme set nord
dots theme current
dots theme refresh
dots theme switcher                 # Gum, FZF or a plain terminal menu
```

`set ID` publishes colors only. `--background` additionally requests an explicit
wallpaper action after successful publication; wallpaper failure leaves colors
selected. `--dry-run` prints the selection, publication path and planned connectors
without creating state. `refresh` rebuilds changed inputs and retries available app
reloads even when generation inputs are unchanged. `init [--shell bash|zsh|fish]`
prints sourceable initialization. Theme IDs complete from local data on Tab.

## Interactive theme switcher

`dots theme switcher` requires terminal input and output. It prefers fullscreen
FZF with the prompt/list at the top and a visible live palette preview below,
occupying 70% of the height. Hovering shows the theme's semantic colors and hex
values via `theme show`, with swatches when terminal color policy allows them.
Browsing never applies a theme. Without FZF it uses `gum filter`, or a numbered
menu when neither tool is available or `TERM=dumb`; these fallbacks show the palette
after selection. Backends are chosen once per invocation; selector failures never
launch another backend. FZF ignores inherited
`FZF_DEFAULT_OPTS` and `FZF_DEFAULT_OPTS_FILE` so user bindings cannot bypass the
single-selection interface or Dots presentation controls. It reads the published
`$XDG_STATE_HOME/dots/current/theme/fzf.sh` (default
`~/.local/state/dots/current/theme/fzf.sh`) through the shared literal color parser,
not by sourcing shell code, and supplies its colors explicitly to FZF. Unpublished
theme edits and stale shell color variables do not affect the picker. Missing
published colors leave FZF defaults; malformed color data refuses selection.
`NO_COLOR` and Dots color controls still apply, including explicit `always` precedence.

After selection, Dots shows the palette and offers **Back**, **Apply** and **Cancel**,
using Gum when available (even after FZF browsing), otherwise a numbered menu.
Back is the default. Only Apply invokes the existing `set ID` publisher and app
reloads; no wallpaper change is requested. Back returns to the catalog, and Cancel
exits successfully without changing state. Selector output must match an offered
ID, and preview failure prevents publication. The plain menu accepts a numbered
choice, Enter for the indicated default, and Escape or Ctrl-D to abort.

Explicit Cancel exits 0; plain-menu Escape/EOF and Ctrl-C exit 130. Gum 2.0 returns
1 for Escape as well as runtime errors (Escape leaves filter input first, then
another Escape quits); Dots preserves this ambiguity. Other selector failures,
invalid selections, empty catalogs and noninteractive calls exit 1. In scripts use
`dots theme list` and `dots theme set ID` instead. Gum widgets honor inherited Gum
colors and Dots color/icon controls; the switcher does not source `gum_env.sh`.

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
intentional ANSI output. Native palette queries use the same output policy.

## Application connections

The stable path is `${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme`, a symlink
to a complete generation. Kitty includes `~/.local/state/dots/current/theme/kitty.conf`
and a local `dots-theme.conf` connector for nondefault XDG state roots. Tmux uses its
local connector. Btop selects `dots.theme`; Yazi selects the `dots` flavor. Bat reads
the generated `Dots` theme and per-generation cache through shell initialization.
Existing app settings and Neovim transparency remain in their source configurations.

On selection, fixed connector links are created only for configured applications:
Kitty/tmux `dots-theme.conf`, btop `themes/dots.theme`, Yazi `flavors/dots.yazi`, and
Termux `~/.termux/colors.properties`, and Pi's `themes/dots.json` (see below). Existing regular files or symlinks are saved in
the generation's connector journal before replacement; real directories are refused.
Parent application directories must exist. If an application directory itself is
linked into a repository, the connector lives in that source directory. It is
machine state, not a configuration to commit. No generic files installer is involved.

Termux settings reload when available; an existing tmux server reloads the generated
colors; Kitty remote control is used only when KITTY_LISTEN_ON is supplied. Reload
failures report that colors were published and can be retried with `refresh`. Apps
without a running reload adapter pick up the files through their normal startup.
No terminal/editor process is restarted and no plugin or package is installed.

### Pi

`default/themed/pi.json.tpl` renders a custom Pi theme named `dots` to `pi.json`
in each generation. It maps UI, Markdown, syntax and export colors to the shared
palette, including light/dark appearance. Panels use `lighter_background` rather
than fixed Mocha tints. Personal `pi.json.tpl` templates and bundled `pi.json`
overrides follow normal precedence and invalidate the publication fingerprint.

When `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/themes` exists, publication links
`dots.json` there to the active generation's `pi.json`. The agent directory must
be absolute, without `.`/`..` components; `~` and `~/` are expanded. It is not an
XDG config path. No Pi executable is required, and no settings file is rewritten.
For first-time setup with the default directory:

```bash
mkdir -p ~/.pi/agent/themes
dots theme refresh
```

In Pi, run `/reload` and select **dots** under `/settings` → **Theme**. Alternatively,
set `"theme": "dots"` in Pi's settings. With a custom agent directory, create its
`themes` subdirectory and supply the same `PI_CODING_AGENT_DIR` to both applications.
Missing themes directories are skipped, not created by the publisher.

Pi watches its own themes directory, not Dots' active-state pointer. On changed
publication, Dots atomically renews the Pi connector through the existing backup
journal, notifying Pi to hot-reload the selected `dots` theme. Unchanged refresh
preserves the connector and generation. Other selected Pi themes are unaffected.
The installed Pi 0.99.1 loader/watcher was verified in an isolated Termux fixture;
older versions may require `/reload`. No live Pi process is restarted.

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
The background picker uses fullscreen FZF with the prompt and list at the top,
overriding inherited height, layout, margin and padding settings.
It displays and searches only basenames without their final
extension, retaining full paths internally (including for duplicate labels).
Optional Chafa renders the hovered image as terminal symbols in a bottom
preview occupying 70% of the height, scaled to the largest fit while preserving
aspect ratio (no stretching or cropping), and explicitly shown by default even when
inherited FZF options hide previews. Without Chafa, selection works without a
preview. Hovering does not apply the wallpaper; accepting a selection does.
Cancellation or an invalid selection makes no wallpaper/state changes. Raw
`bg list` and `bg current` output retains full paths.
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

## Shared discovery

`lib/dots/themes/discovery.bash` is the data-only reader shared by listing, the switcher, current-ID queries, native palette views and completion. Loading it performs no scans or command dispatch; discovery happens only when requested. Flat listing validates and deduplicates IDs, while completion retains its existing literal filename hints, including duplicates and invalid names. These hints do not authorize selection: the loader still rejects invalid IDs and duplicate bundled/user themes. Native flavor views retain metadata validation. No discovery cache or shell-startup scan is added.

## Native palette queries

`dots theme list --families` lists native family names. `dots theme list --flavors FAMILY` lists that family's flavor names; these two filters are mutually exclusive. Plain redirected output is one identifier per line. Human views use the shared theme presentation. Pywal16 flavor discovery does not require generated input. Unknown families fail with a diagnostic.

`dots theme show ID --native` previews upstream palette names and values. `dots theme color COLOR [FORMAT] [--theme ID] --native` queries that map exclusively. Without `--native`, color queries prefer application semantic colors, falling back to native names. This distinction matters when the same name has different upstream and application values. Generic themes use their existing engine palette representation. Formats and scalar bytes remain unchanged, including explicitly requested ANSI formats.

## Migration from plural commands

The `dots themes` and `dots-themes-*` commands have been removed without aliases. Update scripts using these replacements:

| Removed syntax | Replacement |
| --- | --- |
| `dots themes list` | `dots theme list --families` |
| `dots themes list catppuccin` | `dots theme list --flavors catppuccin` |
| `dots themes set catppuccin mocha` | `dots theme set catppuccin-mocha` |
| `dots themes show catppuccin mocha` | `dots theme show catppuccin-mocha --native` |
| `dots themes color catppuccin mocha blue rgb` | `dots theme color blue rgb --theme catppuccin-mocha --native` |
| `dots themes current` | `dots theme current` |
| `dots themes init --shell zsh` | `dots theme init --shell zsh` |

Use full selectable IDs for `set`, `show`, and `color --theme`; family-only shortcuts and separate family/flavor arguments are rejected. `current` returns the selectable full ID, including generic names such as `nord`. Direct executables use `dots-theme-*`. Shell palette helpers (`catppuccin`, `current_theme`, `set_theme`, and `change_theme`) retain their APIs; their implementation uses the unified engine and routes. Existing state paths, generation schemas, and active selections need no migration.

Exit statuses remain 0 for success, 1 for data/publication errors, and 2 for invalid arguments. Diagnostics use stderr. Initialization defaults to Zsh and remains sourceable with `--shell bash|zsh|fish`.

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
dots theme set pywal16-current
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
`change_theme ID` persists through `dots theme set`, then updates the calling Zsh.

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

Bash and Zsh load generated initialization at startup. Their prompt hooks check the
published generation with builtins on the unchanged path and reload only when it
changes. Bash compares the active link with the loaded generation directory;
resolving a changed link may invoke readlink once. The hooks preserve the previous
command's status, existing hooks and FZF options; Zsh also retains autosuggestion
styling. Existing Catppuccin shell sources remain in use. Fish receives explicit
initialization output and does not install an automatic theme hook.

The local Anodize.nvim plugin renders shared native and generic palettes in
`config/nvim`. Its source defaults to `~/repos/Anodize.nvim`, overridden by
`ANODIZE_NVIM_DIR`. It reads validated JSON without CLI calls, watches stable state
parents and handles focus/resume. `:DotsThemeReload` delegates to its active-only
reload; after manually choosing another colorscheme, use `:colorscheme anodize`
to return. No old native-adapter focus loader runs alongside it.

Dots owns transparent main windows, opaque floats, terminal-color opt-out,
15% inactive foreground dimming, Mocha exceptions and other personal highlights.
Lualine uses the Anodize palette without layout changes. Dashboard role updates
preserve animation phase and lifecycle. Missing/invalid shared state uses the
plugin fallback initially and retains last-good colors on reload. An unavailable
local plugin reports its path and falls back to bundled habamax. Optional native
plugins remain available for manual selection; they are not Anodize dependencies.
See [Neovim integration](anodize.md#neovim-integration) and the nested configuration
README. No downloaded theme code is executed and no plugin is installed by the
reader or CLI.

The sourceable compatibility `themes/bin/theme` delegates to `lib/dots/themes/shell.bash`.

## Anodize authoring and consumer colors

[Anodize](anodize.md) creates editable themes using the existing flat theme layout and publisher. Saving and applying are separate operations. Published schema-1 `palette.json` includes an additive `colors` object containing normalized named hex colors and ANSI aliases; existing `palette`, `roles`, and `adapter` fields remain available. The publisher fingerprint includes engine source changes, so a subsequent explicit apply creates an updated generation when necessary. No automatic live theme switch is performed by this source update.
