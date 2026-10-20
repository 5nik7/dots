# Shared themes

**Status: Implemented flat themes, application templates, Git theme sources, explicit wallpapers and opt-in local theme plugins.**

`theme` and `dots theme` inspect and change the current theme. `dots themes`
manages the collection; singular collection routes remain aliases. Both use one
engine. See [decision 0013](decisions/0013-shell-environment-and-theme-collection.md).

Theme preparation, rendering, bat caches, publication, quiet reloads and installed-source validation use [terminal progress](presentation.md#operation-progress). Batch updates show processed checkout counts. Downloads, tmux reloads and wallpaper adapters use static phase messages to keep child output readable. `DOTS_PROGRESS=never` disables these displays. Raw queries, shell initialization and dry runs stay undecorated.

## Tmux

The linked tmux configuration has two top rows on Termux (detected from `TERMUX_VERSION`): the clock on the upper left with Android indicators and battery on the upper right; Termux numbers run in order along the lower row, with the current number joined to its optional tmux session name (` 1:dots `), followed by windows and then later numbers. Matching window/session names render only the window number; differing names render ` number:name `. Equality uses full, case-sensitive names before display clipping, including when the default session name is hidden. Every badge and window owns one space at each end, with no additional separator. Other environments show only the tmux row. `default/themed/tmux.conf.tpl` supplies color options, while the main config owns both layouts and prevents inherited current-window underlining. Theme refreshes preserve layouts.

| Element | Background | Foreground |
| --- | --- | --- |
| Upper row | `background` | `foreground` |
| Clock | `dark_background` | Bold `info` |
| Lower tmux row on Termux | `background` | `foreground` |
| Other windows on Termux | `dark_background` | `light_foreground` |
| Current window on Termux | `selection` | Bold `info`, no underline |
| Inactive Termux entry | `background` | Bold `hint` |
| Current Termux number and project | `hint` | Bold `darker_background` |

Outside Termux, the tmux session badge retains its `accent` background and window labels keep their names. On Termux, the project name extends the current number's teal badge with a colon, and the active pane border uses `selection`. Default sessions created by `termux-bar` have a session-local `@dots-termux-default=1` marker that hides the project-name suffix while retaining the Termux number, including across theme refreshes; project sessions keep their joined labels. Battery thresholds and charging icons remain owned by the existing battery command; the adapter maps its red/yellow/green classifications to theme colors. Missing published colors use the config's terminal-color fallbacks until a theme is applied.

The session adapter requires Python 3 and the optional `androidots/bin/termux-sessions` script in the same checkout. Keep the normal directory link for `config/tmux`: the adapter resolves that link to locate the script without relying on the working directory or scanning PATH. It performs one JSON query per job and matches `client_tty`, so different attached clients highlight their own Termux session. Unmatched clients show inactive entries; failed or unavailable queries clear the numbers. Numbers follow live creation order and may be renumbered after a session closes. The lower-row number strip uses at most one quarter of the client width, capped at 20 columns. The adapter keeps complete labels around the current entry and uses `<`/`>` for hidden entries; unmatched clients show the first entries without highlighting. Its internal `--split-badge` mode returns three controlled fields: styled numbers before the current entry, the plain current number, and styled numbers after it. The config reuses the same asynchronous job for all three fields, joins the number and optional name in tmux's formatting layer, and places later numbers after the native window list but before right-aligned modes. Names never cross the helper's delimiter or shell boundary. The numeric width budget still includes the current number and its two padding spaces. No literal brackets or divider are printed, and independent native window scrolling and mouse ranges are preserved. Unmatched clients keep all visible numbers before a standalone project badge/windows; failed discovery clears the numbers. The complete joined badge uses at most one quarter of client width, capped at 30 columns, including the number, colon and padding. If no name fits, only the number is shown, without a dangling colon. The older `--split-current` and unsplit modes remain compatible with configurations not yet reloaded. Labels have one space at each end, but no fixed-width fill.

`config/tmux/android-status.py` is a separate upper-row adapter. It reads only Wi-Fi and cellular scripts with `--json`, concurrently with one-second helper deadlines and a 2 MiB response limit per helper. Paths resolve through the directory-linked config back to the checkout. Connected Wi-Fi takes precedence; cellular appears only when Wi-Fi is explicitly disconnected and mobile data is enabled with state `connected`. Missing, failed, expired or indeterminate Wi-Fi shows a neutral muted `?` regardless of cellular state. Disconnected Wi-Fi with absent, incomplete, expired or invalid cellular activity also shows `?`. This marker claims neither a transport nor internet access. Only fresh disconnected Wi-Fi plus fresh confirmed inactive telephony data leaves the network slot empty; device freshness is independent of registered-cell signal freshness. Retained positive cached observations remain eligible with `~`, including cellular selection based on stale disconnected Wi-Fi. Uncertain decisions involving either retained stale snapshot show `?~`; otherwise `?` is padded to the existing two-character slot. Notification, volume and location helpers are not invoked. The adapter emits validated private-use icons and controlled tmux styles. Wi-Fi and fixed-glyph cellular share an equal-width icon/marker slot, followed by one separator space when visible. Signal levels 0–1 use theme `red`, 2 `yellow`, and 3–4 `green`; unknown/stale signal is muted. Battery has exactly one space between icon and percentage, then pads the percentage to four cells on the right. Style resets retain the upper-row background.

Normal reads reuse Androidots caching and bounded background refreshes; the adapter adds no cache or daemon. Never add `--refresh` to a recurring status job or switch it to cache-only reads without a separate refresher. Cellular requires successful explicit initialization. Either provider requires explicit recovery after failure, using only the affected command:

```sh
"$HOME/dots/androidots/bin/termux-wifi-status" --refresh --both
"$HOME/dots/androidots/bin/termux-cell-status" --refresh --both
```

Run this interactively using the same HOME/XDG cache location as the tmux server. If Android requests access, grant it and retry. Cellular signal does not establish internet routing. See [Androidots' status contract](../androidots/docs/termux-status.md). Icon rendering requires a Nerd Font; actual glyph appearance remains a device check.

Existing directory-linked installations pick up the network adapter repair on the next status refresh (normally five seconds). For joined badges and the new colors, run `dots theme refresh` and then reload the canonical configuration: `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"`, or tmux **prefix + q**. Tests use disposable servers; live reload and font/color appearance remain separate manual checks.

## Local theme plugins

`dots theme plugins list|enable|disable|run|doctor` adds explicitly enabled GTK 3,
Qt6ct and trusted local hooks. The shared post-commit publisher covers theme set,
refresh and Anodize apply; unchanged refresh retries integrations. Enable/disable
only persist selection. Bundled app writes use journaled copies; arbitrary local
hook effects are outside publication rollback. See [plugin authoring and safety](theme-plugins.md).
Downloaded themes remain data-only and never provide executable hooks.

## Unified commands and family shortcuts

`theme` forwards to `dots theme`, including help, exit statuses and existing full-ID
routes. Generated family and standalone commands use that same Dots handler:

```sh
theme list
catppuccin                         # Usage, logo and flavors
catppuccin mocha                   # Native palette preview
catppuccin mocha blue hex          # Native scalar query
catppuccin mocha set               # Journaled activation
rose-pine dawn set --dry-run
nord show
dots theme catppuccin mocha set    # Equivalent family route
```

No flavor-specific executables are generated. Family/flavor membership comes from
`theme.toml`; names are not split heuristically. A declared `default_flavor` wins;
a sole flavor is the default, while multiple flavors without a default require
an explicit choice. A bare family or standalone command shows usage. Explicit
`set` is required to activate. Native queries use `palette.toml`; ordinary
`dots theme color` and application templates use resolved colors.

Set/refresh and successful theme install/update/remove reconcile thin executable
wrappers under `${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes/commands`.
`dots theme refresh --commands-only` rebuilds wrappers without selecting a theme.
Shells append the stable `commands/current/bin` path, preserving unrelated command
precedence. Reserved Dots/action names do not get wrappers; explicit full-ID
routes remain available. Startup reads generated completion registrations rather
than discovering palettes. Bash/Zsh refresh registrations at the next prompt;
Fish reads them when its completion adapter loads.

Optional regular `logo.txt` files appear only above human help/usage. Flavor help
prefers the variant's file, then its family file. Catppuccin's artwork lives at
`themes/catppuccin/logo.txt`. Artwork with embedded ANSI foreground/background colors keeps its own SGR
colors and formatting; only logos without embedded colors use the addressed
palette. Plain output strips styling. Other terminal control sequences are not accepted as
artwork. Scalar queries, previews, initialization and completion never include logos.

`palette.toml` alone is enough for discovery, previews and native queries. Its
supported syntax is flat named `#RRGGBB` assignments with quoted strings and
comments; duplicate keys, unsupported TOML and invalid colors fail validation.
For activation, recognized semantic names and `[roles]` mappings in metadata
must resolve background and foreground; existing Dots defaults fill other roles.
If `colors.toml` exists it remains authoritative for application colors. Both
bundled and installed palettes use these rules. Pywal retains its explicit export
reader. Legacy family flavor links remain readable as a fallback when a variant
has no native palette file.

Zsh and Bash source the Dots shell adapter directly and load the published theme.
`set_theme`, `change_theme` and `has_theme` remain compatibility helpers.
`theme` is an executable command; use `theme init --shell zsh` for generated shell
code. The old `themes/bin` wrappers have been removed; generated family commands
use the published command directory. Catppuccin-specific startup snippets are no longer sourced.

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
Yazi, Codex, Pi, Vivid and FSH data; Zsh/Fish and Neovim data come from the palette generator.

The [mdcat configuration](../config/mdcat/config.toml) uses `base = "auto"` for dark/light detection and ANSI color names for its overrides. Its colors follow the terminal palette, so the terminal must have the Dots theme applied; mdcat does not read the published Dots palette directly. Existing heading markers, alert labels and text styles are preserved. Code-block highlighting continues to use mdcat's `BAT_THEME` integration. Explicit `--theme` or `MDCAT_THEME` selections override the base, with config style overrides still applied on top.

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
and preview settings. Published template colors and the Dots shell adapter replace the Catppuccin
startup snippets; mdcat follows its terminal-palette configuration. Older generations and session-only
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
Termux `~/.termux/colors.properties`, Pi's `themes/dots.json`, and Codex's
`themes/dots.tmTheme`, Vivid `themes/dots.yml`, and FSH `dots.ini` (see below). Existing regular files or symlinks are saved in
the generation's connector journal before replacement; real directories are refused.
Parent application directories must exist. If an application directory itself is
linked into a repository, the connector lives in that source directory. It is
machine state, not a configuration to commit. No generic files installer is involved.

Termux settings reload when available; an existing tmux server reloads the generated
colors; Kitty remote control is used only when KITTY_LISTEN_ON is supplied. Reload
failures report that colors were published and can be retried with `refresh`. Apps
without a running reload adapter pick up the files through their normal startup.
No terminal/editor process is restarted and no plugin or package is installed.

### Vivid and Fast Syntax Highlighting

`default/themed/vivid.yml.tpl` and `default/themed/fsh.ini.tpl` generate `vivid.yml`
and `fsh.ini` in each published generation. Both follow the shared palette and the
normal template/override precedence. With the existing config directories present,
publication connects `${XDG_CONFIG_HOME:-$HOME/.config}/vivid/themes/dots.yml` and
`${XDG_CONFIG_HOME:-$HOME/.config}/fsh/dots.ini` through the same backup journal.
These machine-local links are ignored when config directories link into this repository.

Checkout setup installs the FSH directory and connector even on a fresh clone;
the tracked `config/fsh/README.md` preserves its source directory. Theme refresh
keeps the existing-directory opt-in rule for standalone app connectors. Both
setup and refresh verify required generated outputs before reusing a matching
input fingerprint, and validate new outputs before publication. Missing or
nonregular artifacts trigger a new generation without editing the old payload.

Directories use blue, executables and shell commands green, links/options/escapes
cyan, ordinary files and paths foreground, comments and unimportant files muted,
source files and archives yellow, configuration files and numeric syntax orange,
and media and shell keywords magenta. Broken links and syntax errors use `error`.
FSH strings use `bright_green`, matching the shared bat syntax template. Special
permissions and devices have separate styles using the same palette. Vivid's
filetype database supplies extension and filename coverage; a custom database
continues to control classification.

After `dots theme refresh`, open a new shell or reload the shell configuration once
to load the updated adapters. All shell adapters read the published `ls_colors`
artifact; Bash/Zsh update it at the next prompt after publication. Completion and
fzf-tab consume that value. Vivid generation happens during publication, so shell
startup does not run Vivid for new generations. `vivid generate dots` remains
available through the connector. Without Vivid, publication supplies basic file
types and explicit suffixes. A present but failing Vivid aborts publication and
retains the previous generation. Older generations and session-only selections
retain their compatibility fallback. FSH is a Zsh-only integration.

Generated font styles support older Vivid parsers through scalar compatibility
mode; Vivid 0.10+ retains combined category attributes. Setup/publication emits
one compatibility notice on stderr, while exact core and explicit suffix styles
remain intact in the final LS_COLORS. Custom templates retain precedence and are
not rewritten. See [Vivid compatibility](file-colors.md#vivid-compatibility) for
the selection order, diagnostics and recovery commands.

FSH's native INI loader builds validated theme data in the Dots Zsh cache. The
adapter saves a regular copy to `$FAST_WORK_DIR/current_theme.zsh`, so FSH loads
Dots directly at the next startup, before the Dots hook. Both lines from
`fast-theme --show` report `dots`. After plugin initialization and on published
theme changes, the adapter checks for updated colors and saves them atomically;
identical copies are left untouched. The configured `FAST_WORK_DIR` is retained.

FSH failures identify unavailable generated data, loader/cache compilation or
startup-cache persistence, and show the relevant path and repair action. The
same failure is reported once per generation in a shell; success resets that
suppression. A missing artifact retains last-good saved colors when available.
Explicit session-only palettes retain their fallback without a setup warning.
No theme generation or installation runs during startup or prompt refresh.

Before replacing a non-Dots startup selection, the adapter preserves its script
and compiled companion (including symlink identity) in a private
`$FAST_WORK_DIR/.dots-theme-backup.XXXXXXXX` directory. It invalidates stale
`current_theme.zsh.zwc` code so an older compiled selection cannot override the
new source. Directory conflicts and preparation failures refuse replacement.
Backups are retained; restoring one requires disabling automatic Dots FSH loading
first, otherwise a later successful theme load will save Dots again.

Explicit FSH overlays remain in the work directory and are reapplied. Secondary
theme styles are included in the saved script; the default empty `secondary`
keeps nested command substitutions and `eval` expressions on the same palette.
Malformed input keeps the previous theme and reports an error. Missing current
artifacts and session-only palette selections retain the last successfully saved
Dots colors without overwriting the startup file. The saved script works even if
the separate Dots build cache has been removed. Neither integration installs
dependencies.

### Codex and Codex-Termux

Codex uses the shared `default/themed/bat.tmTheme.tpl`, including its normal
personal-template and bundled-theme override precedence. No separate syntax
palette or duplicate template is maintained. When
`${CODEX_HOME:-$HOME/.codex}/themes` exists, publication links `dots.tmTheme` there
to the stable active `bat.tmTheme`, also used by bat and Yazi. `CODEX_HOME` must be
an absolute path without control characters or `.`/`..` components; a literal
`~/` is not expanded. Supply the same home to Dots and Codex.

For first-time setup:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/themes"
dots theme refresh
```

Select **dots** in Codex's `/theme` picker, or set `theme = "dots"` under `[tui]`
in that Codex home's `config.toml`. The publisher never edits this setting or
creates Codex directories. It backs up existing connector files/links, refuses
real directories, and retains the connector on unchanged refresh. Future theme
publications change the shared artifact; open a new Codex session to load it.
Automatic reload inside running Codex sessions is not guaranteed.
Custom-theme discovery and selection were verified with Codex 0.162.1 in an
isolated native Termux session; visual contrast across all palettes remains a
manual check.

Codex-Termux and Neovim's Codex launcher inherit the same Codex configuration;
there is no wrapper-specific theme setting or launcher override. The existing
Neovim OSC foreground/background adapter remains responsible for terminal color
queries. Custom `.tmTheme` files control code-block and diff syntax highlighting,
not every TUI widget or desktop-app appearance. See the
[official Codex theme documentation](https://learn.chatgpt.com/docs/cli-customization).

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
home-wallpaper selection. WSL and video wallpapers are unsupported. Native PowerShell provides a Windows desktop wallpaper adapter; see [native PowerShell](powershell.md).
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

`dots themes` now owns collection management: `list`, `switcher`, `install`,
`update`, `remove`, and `plugins`. Existing `dots theme` collection routes still
work. Bare `dots themes` shows collection help without opening a picker.

Use `theme` for a current-theme summary, `theme current` for the plain full ID,
and `theme color`, `show`, `set`, `refresh`, or `bg` for current-theme operations.
`theme show` defaults to the selected theme; an explicit ID previews another.
Its human view shows all resolved named and terminal colors, file types, MIME
rules and configured extension rules using the shared `theme colors` tables.
The source is labeled because `show` reads configured sources while `colors`
defaults to the published snapshot. Native previews retain their native-only
scope. See [human color views](file-colors.md#human-color-views) for details and
redirected-output compatibility.
`theme list` and `dots themes list` list the same selectable IDs; `--families`
and `--flavors FAMILY` provide the corresponding filters. Full IDs remain the
selection interface. Family commands retain native flavor queries and explicit
`set`. Internal callers use `dots-theme-current`; the old `current_theme`
wrapper has been removed.

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
identity for compatibility. Published generations use the shared Vivid Dots template
for every palette. Old generations and session-only Catppuccin selections retain
their named Vivid theme and inherited-entry fallback. New generations follow the
[file-color publication contract](file-colors.md).

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

Read-only selection and startup use the published generation, otherwise
`DOTS_THEME_DEFAULT` from [Dots settings](shell-environment.md). Legacy `.default`
and `.theme` files are not read or imported. `DOTS_THEME_SELECTION` remains an
explicit session-only override used by `set_theme ID`.
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

Generated family commands retain the positional/flag query interface, formats,
raw/array output and completion generators for Bash, Zsh and Fish. Current-theme
queries use `theme color`; the bare command previews the selected palette. `--all` queries every flavor;
`init` emits the selected palette's initialization. Catppuccin's fixed
flavor-prefixed arrays remain available. Generic initialization exposes
`dots_palette` and `dots_roles` associative arrays in Bash/Zsh; Fish receives
`dots_color_NAME` and `dots_role_NAME` variables plus `THEME` and `FLAVOR`.
Bash/Zsh initialization also exposes a global associative array for every current-theme color: `${blue[hex]}`, `${hint[esc]}`, `${background[rgb]}`, and so on. It combines native palette names with the resolved Dots template colors and roles; resolved values win on overlap. This includes terminal aliases (`color0` through `color15`) and native extras such as `rosewater` or `blue1`, but excludes `mode`. Thus `${cyan[hex]}` can differ from `${dots_palette[cyan]}`: the former follows the template palette, while the latter retains the native palette API.

Each color array contains `name`, `hex`, `rgb`, `r`, `g`, `b`, `luminance`, `brightness`, `cmyk`, `ansi-8bit`, `ansi-8bit-value`, `ansi-8bit-escapecode`, `ansi-24bit`, `ansi-24bit-escapecode`, and `esc`. Escape fields contain actual terminal foreground sequences. Global Bash/Zsh scalars `$rst` and `$RST` both contain the SGR reset sequence `ESC[0m`, restoring terminal colors and text attributes. For example: `printf '%sHello%s\n' "${blue[esc]}" "$rst"`. The values are calculated during initialization generation and cached, not recalculated on each prompt. Bash requires `${blue[hex]}`; Zsh also accepts `$blue[hex]`.

Switching removes obsolete unprefixed arrays owned by Dots. The first reload from the older Catppuccin initializer uses its palette-name list to remove stale colors. Catppuccin initialization still supplies fixed-flavor arrays such as `${mocha_blue[hex]}` and `${latte_blue[hex]}` with their original values; switching away does not remove them. Fish retains its scalar initialization interface.

Direct array names must start with a lowercase ASCII letter (optionally preceded by one underscore) and contain only ASCII letters, digits, or underscores. Shell special parameters, Dots control names, adapter locals, `rst`, and the `_dots_`, `dots_`, `catppuccin_`, `mocha_`, `macchiato_`, `frappe_`, and `latte_` prefixes are reserved. A conflicting color name fails Bash/Zsh initialization and publication before replacing the active generation; rename that palette key. Existing shared color names intentionally occupy global shell variables.

The library-owned shell adapters load published initialization at startup. Native
Fish, Nushell, Xonsh and PowerShell also consume the published `shell.tsv` data;
see [the shell environment contract](shell-environment.md). Bash and Zsh retain
their sourceable initialization. Their prompt hooks check the
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

Shared sourceable theme helpers live in `lib/dots/themes/shell.bash`; shell
configuration normally loads them through `dots init`.

## Anodize authoring and consumer colors

[Anodize](anodize.md) creates editable themes using the existing flat theme layout and publisher. Saving and applying are separate operations. Published schema-1 `palette.json` includes an additive `colors` object containing normalized named hex colors and ANSI aliases; existing `palette`, `roles`, and `adapter` fields remain available. The publisher fingerprint includes engine source changes, so a subsequent explicit apply creates an updated generation when necessary. No automatic live theme switch is performed by this source update.

## Theme-owned usage colors and file styles

Family help and native palette previews use the addressed theme's explicit
foreground/background. Bare family help follows the active flavor when it belongs
to that family, otherwise the family's default. This changes presentation only;
existing palette-query and activation defaults remain unchanged. Explicit flavors
always choose their own palette. Themed help lines reset styling, wrap on narrow
terminals, and use readable text contrast while preserving actual swatch colors.
`logo.txt` artwork retains its authored SGR colors when it contains ANSI
foreground/background colors; otherwise it receives the theme color. Bold and
reset codes alone do not count as embedded colors. Width checks ignore SGR codes,
and authored multiline styling is isolated with a reset before and after the logo.
Other terminal controls are sanitized; disabled color strips all styling.

`--color=none` aliases `never`; family commands accept the equals form anywhere.
`--color NAME` / `-c NAME` still query palette colors. Raw values, JSON, Lua,
completion and init output never acquire decoration. Plain help remains usable
if the palette is unavailable. See [file colors](file-colors.md) for the new
`theme colors` commands, customization layers, full styles and portable exports.

## Explicit checkout setup

[Checkout installation](installation.md) reuses immutable theme and generated-command preparation, then publishes state pointers and fixed connectors through the shared file Store. Prepared generations carry `staged` status; normal theme recovery leaves them to the owning file journal. The current theme/default is preserved. Fixed app connector definitions are shared through `lib/dots/themes/connectors.tsv`; btop's generated connector is now ignored. Setup creates declared missing parents and suppresses application reloads, wallpaper actions and plugin hooks. Normal theme commands keep their existing publication behavior.

### CLI file-style projection

Theme publication now also writes internal `file-styles.tsv` beside `colors.json`,
`colors.lua` and `ls_colors`. The header is `dots-file-styles<TAB>1`. Subsequent
rows have four tab-separated fields: group, literal key, numeric SGR sequence and
case mode (`-`, `exact`, `fold`). Groups are `type`, `extension`, `mime`, `suffix`
and `default_mime`, in matching-priority order. Suffix case collisions are resolved
by the existing file-style matching policy before publication. The projection is
data, never executable shell source; it does not change export JSON/Lua schemas.
Ordinary CLI views only read published artifacts. A normal refresh supplies the
new projection; older publications remain usable through the documented fallback.

### CLI Git-style projection

Theme publication also writes `git-styles.tsv` atomically with the same generation. Its header is `dots-git-styles<TAB>1`; subsequent rows contain a lowercase role key and numeric SGR sequence separated by one tab. This output name is reserved against custom templates. Git styles use the existing fingerprinted rule inputs. `file-styles.tsv` and LS_COLORS remain independent.

The shared Bash presentation layer lazily reads this bounded regular data file once per colored Git command. It rejects symlinked payloads, oversized data, malformed rows and duplicate keys, and never sources the contents or invokes Python/theme resolution to render a row. Missing roles use terminal defaults. The [Git styles reference](file-colors.md#git-styles) owns the role list and public export interface.

The Dots Yazi plugin exposes live Lua references such as `dots.colors.background`, `dots.colors.git.repo`, `dots.colors.type.dir`, and `dots.colors.mime["image/*"]`. These resolve from the existing `colors.json` publication at setup and refresh; no second Lua template is needed. The existing `colors.lua` export remains available to other Lua consumers. `dots.colors()` and `dots:colors()` still return the loaded palette. Header defaults and per-file Git indicators use shared Git roles; explicit configuration and `th.git` overrides retain precedence. Update remote-installed plugin runtime through `ya pkg`, so its revision and hash remain package-manager owned.

The default `blastoff.toml.tpl` publishes a Starship-compatible Dots palette. `{{ git_colors_starship }}` is a data-only expansion of resolved Git foreground shortcuts into flat `git_*` entries; palette names otherwise match the semantic theme names. The optional [Starship plugin](theme-plugins.md#starship-and-blastoff-starship) merges the palette into existing configuration after publication, including explicit unchanged-theme refreshes. It never replaces module configuration with the template.

### Git and Delta default template

`default/themed/gitconfig.tpl` publishes a theme-only Git include, connected as
`${CONFIG}/git/dots-theme.gitconfig` when the Git config directory exists. The
common Git config includes it after fallback colors; the platform overlay remains
last. Personal settings are not regenerated. See the [Git config guide](../config/git/README.md).

Literal `{{ git_<role> }}` tokens resolve configured Git foregrounds. Their
`_delta` variants translate `reset` to Delta's `normal`. For semantic colors and
Git foregrounds, `<name>_blend_10` and `<name>_blend_25` blend that percentage into
`background`, rounding each RGB channel with integer half-up rounding. A reset
foreground blends as background. These template-only expansions do not change
exported palette namespaces and do not execute expressions. Normal attributes
remain explicit in the template. Unknown tokens still fail preparation.

Prepared generations expose the existing bat cache at `delta-cache/bat`; Git's
Delta commands set a process-local XDG cache root and request Dots syntax. Missing
cache uses the normal Delta invocation. The standard bat cache is never replaced.
Use the [template skill](../.codex/skills/dots-theme-template/SKILL.md) when adding
other default consumers.

## Verbose application output

`dots theme set ID -v`, `dots theme refresh --verbose`, `dots theme refresh --commands-only -v`, and `dots theme switcher -v` add action details on stderr. The plural `dots themes switcher` alias, standalone `theme` forwarding, and family/flavor `set` helpers preserve the flag. The switcher passes it into Apply; selection previews and cancellation remain read-only.

Verbose output shows preparation/render/cache phases, source -> destination links, connector recovery copies retained in generation journals, publication, reload/plugin outcomes and concise unchanged/skipped reasons. Already-current generations are explained without claiming new backups or links. Rollback is reported separately from completed writes. Default output, selector styling, approvals and mutation behavior remain unchanged. Resource colors/icons and progress use the [shared contract](presentation.md#verbose-operations). `set --dry-run -v` describes planned connections without writes; this does not add dry-run support to refresh or switcher. Theme collection downloads/removal, background selection and data-query routes do not gain verbosity.

## Native PowerShell publication

The native frontend provides literal palette queries, theme/family commands, generated `.ps1` commands, native initialization, selection/refresh, source operations and background selection. It shares file-color rendering, semantic presentation, progress, FZF snapshot previews and the guarded file transaction engine. Setup renders without desktop effects; explicit publication may run enabled native hooks and supported app notifications. Windows wallpaper uses its desktop API; Android lock-screen, GTK/Qt and tmux actions retain explicit platform limits. User `.ps1` hooks are native Windows-only; downloaded themes remain inert. See [native PowerShell](powershell.md) for implementation status, state paths and native acceptance requirements.
