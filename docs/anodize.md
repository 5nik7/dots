# Anodize

**Status: Implemented core, CLI and local Neovim integration; Android app and TUI deferred.**

Anodize creates and edits Dots themes from local images, seed colors, existing themes and imported palettes. Its reusable Go package performs extraction and color adjustments without filesystem or process access. The CLI reuses Dots presentation, file transactions and theme publication. [Decision 0011](decisions/0011-anodize-authoring.md) defines these boundaries.

Both `dots anodize` and standalone `anodize` use [terminal progress](presentation.md#operation-progress) for slow loading, extraction, rendering, saves and application. Saves share the file engine's phase counts. `DOTS_PROGRESS=never` disables progress; JSON, raw exports/app previews, completion and dry runs bypass it. No Go engine protocol change is involved.

## Build and first use

Use installed Go 1.27.1 and Python 3.11 or newer. Bash and existing POSIX theme tools apply to the Bash frontend; native Windows uses PowerShell and the Python publication adapter. From the Dots checkout:

```sh
python3 -B tools/verify_anodize.py check
python3 -B tools/verify_anodize.py build
bin/anodize modes
bin/anodize create dusk --color '#725ac1' --dry-run
bin/anodize create dusk --color '#725ac1' --yes
bin/anodize preview dusk
bin/anodize apply dusk --dry-run
```

`dots anodize` exposes the same commands when Dots is on PATH. Building explicitly replaces the ignored `plugins/anodize/engine/.build/anodize-engine` artifact (`anodize-engine.exe` on Windows). Use `python -B tools/verify_anodize.py build` from PowerShell. There are no runtime builds, downloads or shell-startup engine calls. `ANODIZE_ENGINE` can point to a prebuilt executable for testing. Help works without the engine; palette operations explain how to build it if missing. Run `anodize` or `anodize --help` for a compact command list and examples, and `anodize COMMAND --help` for described arguments and options. Help adapts to terminal width and uses shared Dots colors, including plain output with `NO_COLOR` or `--color=never`.

Saving a theme does not select or activate it. Review `anodize apply dusk --dry-run`, then use `anodize apply dusk --yes` to publish. Mutating commands prompt on interactive input; without a terminal or with `--json`, omission of `--yes` returns the preview. `--dry-run` takes precedence over `--yes` and creates no persistent state.

Interactive human confirmations prefer Gum with **Cancel** selected by default and a text prompt when Gum is unavailable. Create, import, edit, single-file export and apply accept `--yes` for unattended use. Patina's all-theme batch asks for one confirmation. JSON and dry runs skip the prompt. Ctrl-C exits 130. See the [interaction contract](presentation.md#optional-gum-interactions).

## Terminal logo

**Authoritative branding contract, updated 2026-10-27.** Every default human Anodize view uses exactly one of the following owner-supplied UTF-8 artworks. Their characters, braille spacing and six rows must be preserved. This rule applies to standalone Anodize, Bash/native Dots help, results, diagnostics, interactive menus, popup readers and completion previews. JSON, raw app configuration, exports and completion data remain undecorated.

### LOGO1: default symbol

```text
⠀⠀⠀⠀⠀⠀⠀⣰⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⣼⣿⣿⣄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠠⢾⡿⠃⠘⣿⣆⠀⠀⠀⠀
⠀⠀⠀⣰⣷⣦⣤⣀⠀⠘⣿⣦⠀⠀⠀
⠀⠀⣴⣿⡟⠙⠻⢿⣿⣶⣾⣿⣧⡀⠀
⢀⣾⣿⠏⠀⠀⠀⠀⠀⠉⠛⠿⣿⣷⡀
```

LOGO1 is `logo.txt` (15 columns). It is the default for results, diagnostics, Preview, Extract and their embedded previews. An exact embedded copy is the final fallback when assets are missing or invalid.

### LOGO2: optional wide help

```text
⠀⠀⠀⠀⠀⠀⠀⣰⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⣼⣿⣿⣄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠠⢾⡿⠃⠘⣿⣆⠀⠀⠀⠀⠀⣠⠟⢧⡀⠀⡟⢦⣸⠀⣾⠉⠉⡇⢸⡏⠉⣧⠀⡇⠈⣩⠝⠃⢸⡯⠭
⠀⠀⠀⣰⣷⣦⣤⣀⠀⠘⣿⣦⠀⠀⠀⠀⠁⠀⠈⠁⠀⠁⠀⠉⠀⠈⠉⠉⠁⠈⠉⠉⠁⠀⠁⠈⠉⠉⠁⠈⠉⠉
⠀⠀⣴⣿⡟⠙⠻⢿⣿⣶⣾⣿⣧⡀⠀
⢀⣾⣿⠏⠀⠀⠀⠀⠀⠉⠛⠿⣿⣷⡀
```

LOGO2 is `horizontal.txt` (42 columns). Help uses it when the content width fits, otherwise LOGO1. Default selection never chooses other artwork. Viewport height, a capture pipe, redirected human output, `TERM=dumb`, disabled icons, color settings or legacy Python output encoding must never replace these marks. Human logo output uses UTF-8; rendering the cells requires a font that contains them. Short panes scroll vertically; even a tiny viewport receives the intact artwork.

### Explicit choices

| Option | Behavior |
| --- | --- |
| `--logo=text` | Supplied text artwork; the default. |
| `--logo=auto` | Explicitly request supported Kitty graphics, then optional Chafa, then supplied text. |
| `--logo=kitty` / `--logo=chafa` | Explicit graphics choice; unavailable rendering falls back to supplied text. |
| `--logo-layout=auto` | LOGO2 for wide help, LOGO1 otherwise. |
| `--logo-layout=base` | Exact LOGO1 at every width. |
| `--logo-layout=horizontal` | LOGO2 when it fits, otherwise LOGO1. |
| `--logo-layout=stacked` / `--logo-layout=icon` | Explicit access to the retained larger braille layouts; fallback is LOGO1. |

`ANODIZE_LOGO` and `ANODIZE_LOGO_LAYOUT` retain explicit persistent preferences. Command options override them and accept both equals and separate-value forms before or after the subcommand. Invalid environment values use the defaults; invalid options are usage errors. Dots menu Help pins text/horizontal, and Preview/Extract pin text/base, overriding inherited preferences for those popup flows.

Text artwork uses a diagonal gradient from **hint at the bottom left**, through **info at the midpoint**, to **accent at the top right**. Each symbol and wordmark receives its own full gradient: LOGO2 restarts the gradient for the ANODIZE wordmark, as does the explicit stacked layout. Blank cells preserve spacing but do not determine the endpoints. Help, lists and diagnostics read the active published theme; palette results, Extract, guided previews and completion previews use the palette being shown. The selected background starts on the first logo row and continues through the heading, Theme/Contrast details, preview body and any result notes. Headings use the panel accent style; details use the selected foreground and statuses use selected semantic colors. Subsequent text returns to the panel foreground. This changes color only, never the supplied artwork.

All three stops must be valid theme colors. If any is unavailable, banners retain solid magenta and embedded previews retain their foreground; a candidate preview never borrows active-theme colors. Three equal stops produce a solid logo; equal outer stops can still blend through a distinct info color. Optional graphics retain their original colors.

`NO_COLOR` and `--color=never` retain monochrome artwork. Icon preferences affect ordinary UI icons and optional graphics eligibility, not the supplied text logo. Optional graphics remain capability-checked: Kitty excludes unverified multiplexer passthrough, and Chafa uses bounded `--fg-only --symbols=braille` output without probing, animation or installation. Graphics capability failures never affect the operation's exit status.

Text width uses the destination terminal, then valid `COLUMNS`/`LINES`, then 80×24, reserving the caller's margin. Explicit larger text layouts have a 16-row asset budget independent of viewport height. PNG graphics keep their existing size limits. [Asset provenance](../plugins/anodize/assets/README.md) records the retained sources.

Static Dots help uses only core-owned renderers and metadata; it never executes the Anodize extension or engine. Bash help retains its builtin text path without a Python requirement; colored Anodize help reads only the bounded published `shell.tsv` snapshot. Python banners read the corresponding `palette.json`. Neither path resolves themes or runs shell initialization, and plain/data paths do not load logo colors. Native help uses the same Python logo policy without Bash.

## Commands and flags

Authoring commands accept `--json` for a schema-1 response unless they return a raw format. `completion` emits only shell source and does not accept `--json`. Prefix `--color=auto|always|never` and `--icons=auto|always|never` follow the shared presentation policy. `--color HEX` after `create` means the seed color.

| Route | Inputs and behavior |
| --- | --- |
| `completion SHELL` | Print Bash, Zsh, Fish or PowerShell completion source; no engine required. |
| `modes` | List the 36 palette modes with descriptions. |
| `extract IMAGE` | Inspect colors and foreground/background contrast. Use `--all-modes` for interactive comparison, or select one with `--mode`. Both support `--light` and `--dark`. |
| `patina IMAGE` | Recolor a PNG, JPEG or first GIF frame using `--theme ID` or `--palette-image FILE`. See [Patina](#patina). |
| `create ID` | Exactly one of `--image FILE`, `--color '#RRGGBB'`, `--from THEME`. Supports generation flags, `--adjust NAME=VALUE`, `--set COLOR=HEX`, and `--reference-wallpaper`. |
| `import FILE --name ID --format FORMAT` | Import `anodize`, `aether`, `base16`, or `colors`. Supports generation flags and `--reference-wallpaper`. |
| `list` | List authored themes in both user and repository storage. Human output and the additive JSON `storage` field identify `user` or `builtin`. |
| `show ID` | Inspect an authored or existing Dots theme. |
| `edit ID` | Edit an Anodize-owned theme. Supports generation flags, adjustments, overrides, `--reset-adjustments`, `--reextract`, and `--reference-wallpaper`. Derive other themes with `create --from`. |
| `preview ID` | Show colors, or use `--app kitty|tmux|btop|termux|bat|yazi` for raw generated configuration. `--app` cannot combine with `--json`. |
| `export ID` | Raw stdout by default; `--format anodize|aether|colors`. `--output FILE` saves through a journal and refuses existing targets. |
| `promote ID` | Move an authored user theme into repository `themes/ID`; `--copy --name NEW_ID` retains the user version under its original ID. Accepts `--dry-run`, `--yes`, `--json`, and `--interactive`. |
| `apply ID` | Preview/publish with the existing Dots publisher; optional `--background` explicitly requests a subsequent wallpaper action. |

Patina, create, import, edit, promote, export-to-file and apply accept `--dry-run` and `--yes`. Raw stdout export is already read-only; `--dry-run` requires `--output`. Raw exports and app previews never receive ANSI decoration. Diagnostics go to stderr. Exit status is 0 for success/preview, 2 for argument usage errors, and 1 for validation or operational failures.

IDs start with a lowercase letter and contain lowercase letters, digits, `_` or `-`. New IDs refuse repository and installed-user-theme collisions. PNG, JPEG and GIF input is limited to 32 MiB and 20 million pixels; palette extraction requires at least one sufficiently opaque sampled pixel. Extraction defaults to normal/dark. `--light` and `--dark` are mutually exclusive. Use `modes` as the authoritative list of modes.

### Compare extraction modes

Run `anodize extract forest.jpg --all-modes` to browse every mode in dark mode. Add `--light` to compare light palettes. The FZF list includes swatches when terminal color is enabled. Its preview shows syntax, status colors and the candidate’s background. Enter opens a review where you can view the palette, return to the list, or save it as a new personal theme. **Save and apply** saves the accepted palette and opens the normal activation review. Declining activation keeps the saved theme. Plain `extract` prints its result directly.

The default `normal` mode measures the actual area occupied by neighboring hues and uses darker shades of the dominant family for dark backgrounds or lighter shades for light backgrounds. It pairs this with a subtly tinted near-white or near-black foreground, targeting 7:1 contrast. It looks for red, green, yellow, blue, cyan, magenta, orange and brown in the image. Missing hues take related shades with enough color to remain recognizable even on a grayscale source. Error, warning, success, info and hint follow red, yellow, green, blue and cyan, targeting at least 4.5:1 before user adjustments. Use `--mode source-tonal` to reproduce the earlier default. A saved theme uses its stored baseline until you regenerate it.

## Patina

`patina`, `dots patina`, `anodize patina` and `dots anodize patina` accept the same arguments.
The first image supplies the pixels. Choose a theme with `--theme` or extract a palette from another image with `--palette-image`.

```sh
patina reflekt.jpg --theme catppuccin-mocha --output reflect.webp
patina reflekt.jpg --theme catppuccin-mocha --compare
patina reflekt.jpg --theme catppuccin-mocha --compare-modes --style palette-blend
patina forest.jpg --theme kanagawa-wave --mode jewel-tones --style vivid --format jpg
dots patina coast.png --palette-image sunset.jpg --style gradient --stops background,blue,cyan,foreground --output coast-themed.webp
```

For a single image, use `--yes` to save unattended. The command asks for confirmation at a terminal. A noninteractive single-image invocation or `--json` returns a preview until you pass `--yes`. Use `--dry-run` to preview even with `--yes`.

### Save an image for every theme

```sh
patina reflekt.jpg --all-themes --yes
patina reflekt.jpg --all-themes --yes --style palette-blend --output reflect.webp
patina reflekt.jpg --all-themes --all-styles --yes --output walls/reflect.webp
```

Patina shows the number of themes, styles and images, then offers **Save images** or **Cancel**. Cancel is the default. Save images renders the source once per selected treatment for every personal and bundled theme. The first example saves `reflekt.png` in each theme’s personal `backgrounds/ID/` folder. The second saves `reflect.webp` there. With `--all-styles`, filenames include the compatible style, such as `walls/reflect_alloy.webp` and `walls/reflect_palette-blend.webp`. Occupied batch filenames get the first available suffix, such as `reflect_1.webp`.

Saving requires a terminal. Add `--dry-run --json` to list the intended paths without rendering or writing. Each saved image has its own undo transaction. If a theme or style fails, Patina reports it and continues with the others. A change to the input image stops the remaining exports.

### Compare treatments

To choose one full-resolution result interactively, use any of these forms:

```sh
patina reflekt.jpg --all-themes --style palette-blend
patina reflekt.jpg --theme catppuccin-mocha --all-styles
patina reflekt.jpg --all-themes --all-styles --output reflect.webp
patina coast.png --palette-image sunset.jpg --all-styles --output coast-themed.png
```

`--all-themes` includes personal and bundled themes and defaults to alloy. `--all-styles` includes the styles compatible with the supplied settings. Together they open a single searchable list of theme and style pairs. In FZF, type words such as `mocha palette-blend` to narrow the list and see a recolored thumbnail. Enter reviews the selected image and its destination. **Back to results** restores the FZF search and position. **Save image** writes the reviewed file using the usual encoding and collision rules. The Dots Anodize menu offers the same comparisons under Patina. These shortcuts require a terminal. For a saved sheet, use the comparison flags below.

`--compare` saves a labeled sheet of the original image and all 18 styles at their defaults, with the chosen palette visible above each image. Compare **01 harmonize**, **07 palette-blend** and **18 alloy** to see how they handle the same shadows and hues. The interactive style picker starts with alloy. The sheet accepts `--mode`. `--compare-modes` holds the style and its settings fixed and shows each of the 36 palette modes. A named theme also gets an **as-authored** panel. Both sheets default to PNG beside the input, named `reflekt_styles.png` or `reflekt_modes.png` in these examples. Subsequent saves use the first free numbered suffix. Use the printed style or mode name for the full-resolution export.

| Style | Appearance |
| --- | --- |
| `alloy` (default) | Keeps the shadow depth and highlights of palette-blend. For colored pixels, 75% of the hue and chroma comes from palette-blend and 25% from harmonize. Near gray, the two tints blend smoothly. |
| `harmonize` | Maps shadows and highlights to the theme’s dark and light colors. Midtones take a compatible palette hue so dark foliage can keep its green character. |
| `natural` | The earlier harmonize treatment. Preserves source lightness while gently matching hues. |
| `palette-blend` | Blends neighboring palette swatches for a painterly result. |
| `color-transfer` | Matches the image’s most common distinct color groups to different palette swatches and keeps shading within each group. |
| `gradient` | Runs from the darker to the lighter of background and foreground, through an accent or interior midtone when available. |
| `duotone` | Maps lightness between two palette colors. |
| `split-tone` | Tints shadows and highlights separately. |
| `muted` | Softens saturated colors with the theme’s neutral tones. |
| `vivid` | Increases chroma and contrast along the theme’s hue families. |
| `pastel` | Lifts the image toward a pale tint of the theme foreground or background. |
| `night` | Compresses highlights into the dark end of the palette. |
| `accent` | Keeps colors near the theme accent and subdues the rest of the image. |
| `posterize` | Separates shades into six flat tone levels. |
| `dither` | Uses a repeating ordered-dot pattern to bridge five tone levels. |
| `ink` | Draws dark contours and a shadow wash on tinted paper. |
| `exact` | Chooses the nearest original palette swatch for each visible pixel. |
| `shaded` | Restores source lightness after choosing the nearest swatch. |

`--strength 0–100` blends the treatment with the source in OKLab. The default is 100. Zero preserves source pixels before encoding. The original `exact` and `shaded` styles use fixed strength. For `gradient` and `duotone`, supply ordered palette names with `--stops`. Gradient takes at least two names and duotone takes exactly two. For example, `--stops yellow,blue` gives yellow shadows and blue highlights. Both accept custom theme color names.

For `alloy`, `harmonize` and `natural`, `--harmony auto` fills missing hues using nearby, split-complementary or opposite hues. Choose `analogous`, `complementary`, `palette` or `source` to change that rule. In `alloy`, this rule affects the harmonize contribution. Use `natural` for the full source-lightness effect.

### Choose palette colors

A theme supplies all rendered colors, including its overrides and custom names. Adding `--mode` generates a temporary palette from those colors for this export. It inherits the theme’s light or dark setting, which you can override with `--light` or `--dark`. A reference image defaults to `normal` and dark. Extracted source colors carry their sampled image coverage. Named-theme colors each contribute once.

Run `anodize modes` for all names and descriptions. Modes such as `dominant`, `hue-balanced` and `tonal-range` emphasize different aspects of the source. Try `teal-orange` for a warm/cool pairing, `cyanotype` for a blue print or `risograph` for vivid inks. The same modes work with `create`, `edit`, `import` and `extract`.

### Choose the output file

A recognized `--output` extension chooses the encoder, including when `--format` gives another valid type. For an extensionless output path or automatic filename, `--format` supplies the extension. The default is PNG. Unknown output extensions produce an error.

| Output | Encoding behavior |
| --- | --- |
| `png` | Lossless, with source transparency and up to 16-bit channels. |
| `jpg`, `jpeg` | Composites transparency over the theme background. Default quality 90. |
| `gif` | One indexed frame with binary transparency. |
| `svg` | A self-contained SVG containing the recolored PNG raster. |
| `webp` | Requires Pillow with WebP support. Default quality 90. Accepts `--lossless`. |
| `bmp`, `tif`, `tiff` | Require the corresponding Pillow encoder. BMP composites over the theme background. |
| `avif` | Requires Pillow with AVIF support. Default quality 80. |

`--quality 1–100` applies to JPEG, lossy WebP and AVIF. `--lossless` selects lossless WebP and takes no quality setting. PNG, JPEG and GIF inputs can be up to 32 MiB and 20 million pixels. Animated GIFs supply their first frame.

With a theme, omitting `--output` saves a wallpaper under the personal Dots configuration directory in `backgrounds/ID/`. For example, the default for `forest.jpg --theme nord` is `~/.config/dots/backgrounds/nord/forest.png` on POSIX. PNG inputs keep their extension case. If that name exists, the next saves use `forest_1.png`, then `forest_2.png`. Dots respects `XDG_CONFIG_HOME` and defaults to the roaming application-data directory on Windows. An explicit single-image or comparison-sheet output path must be unused. With a reference image, ordinary exports require an explicit output path.

The interactive style picker previews the treatments on your image. Final review shows the selected render and destination. A saved result includes a transaction ID for `dots files undo`. The theme background selector lists its supported wallpaper formats. See the [theme guide](themes.md) for activation.

## Shell completion and manual

Bash, Zsh, Fish and native PowerShell complete commands, flags, extraction modes, adjustment names, built-in named color keys, theme IDs, formats, app names and file paths. Both `--option value` and `--option=value` work. `edit` suggests themes with an Anodize recipe in either storage root. New theme IDs and arbitrary hex/numeric values are entered manually. `--color=always` before the command controls presentation; `create --color HEX` remains a seed color.

The repository shell completion trees include `anodize` alongside `dots`. To load completion in an existing shell session:

```bash
# Bash
source <(anodize completion bash)
```

```zsh
# Zsh: run compinit only if it has not already initialized completion.
autoload -Uz compinit
compinit
source <(anodize completion zsh)
```

```fish
# Fish
anodize completion fish | source
```

For persistent use outside Dots shell configuration, save the emitted source in your shell's completion directory: `anodize` under Bash's `bash-completion/completions`, `_anodize` in a Zsh `fpath` directory, or `anodize.fish` under Fish's `completions`. Loading these files does no discovery; queries read static Dots metadata and theme names only. No engine, theme activation, network access or extension execution is needed. The Zsh adapter preserves values and descriptions for FZF-tab.

The section-1 manual is [man/anodize.1](../plugins/anodize/man/anodize.1). From the checkout, read it without installation:

```sh
man -l plugins/anodize/man/anodize.1
```

Combined Dots setup installs `anodize.1` under `~/.local/share/man/man1`. Configure the user manpath if needed, or use `man -M ~/.local/share/man anodize`. No system manual directory is changed.

The adapters are generated from the shared Dots shell adapters; the manual's command/option reference is generated from the CLI parser. After changing either source, run `python3 -B tools/generate_anodize_integration.py`; `--check` verifies checked-in artifacts without writing. Static wrapper headers remain the completion metadata source, with tests checking parser and engine vocabulary consistency.

## Interactive authoring and previews

In the Dots Anodize menu, **Extract** follows **Create**. Choose an image, lightness and extraction mode to review the palette. **View palette** opens the scrollable LOGO1 result. **Save as theme** reviews a new personal theme, and **Save and apply** also offers activation. Inside tmux, the picker closes before the fitted reader opens. Leaving the reader restores the parent menu search. App preview bytes retain their raw format.

Run `anodize --interactive` for an action menu, or append `--interactive` to
`create`, `extract`, `patina`, `edit`, `show`, `preview`, `apply`, `import`, `export` or
`promote`. Missing required inputs open selectors automatically when all terminal
streams are available; complete commands retain their existing defaults. JSON,
redirected output, `--yes` and `--dry-run` never auto-open selectors. Explicit
`--interactive --dry-run` can collect inputs and show a plan. Explicit interactive
mode refuses `--json`, `--yes` and nonterminal streams.

Selectors prefer FZF, then Gum, then numbered menus. Enter selects for review;
Escape/Ctrl-C cancels. Alt-P toggles the FZF pane and Alt-J/K scroll it. Selecting
an item does not approve saving or applying. Image browsing starts in the current
directory, with parent navigation and typed paths. Creation offers image, seed
color or existing-theme sources and user/built-in storage. Guided editing holds
an in-memory draft with mode/lightness, adjustments, color overrides, reset and
re-extraction; Review save leads to the existing confirmation.

Human show/preview output includes a syntax sample painted with the theme's exact
foreground/background, followed by palette details. Dots theme show and switcher
previews use the same renderer. Printed rows reset terminal styling afterward;
FZF panes use their own dimensions and fill unused rows with the theme background.
Plain mode remains readable. Raw app previews, exports, JSON and scalar interfaces
retain their formats. This sample illustrates the default syntax color mapping;
individual applications can have additional highlighting rules.

Mode pickers temporarily generate all supported modes for the chosen source and
lightness, retaining adjustments and overrides. Hovering renders cached candidates;
the selected candidate becomes the draft. Temporary directories are removed when
the picker exits, including cancellation. Source drift during review refuses a save.

The repository's Zsh FZF-tab integration previews Anodize and Dots theme IDs and
Anodize `--mode` choices. Mode previews require a usable source earlier on the
command line. The displayed completion menu owns its temporary cache; ordinary
completion and shell startup never call the engine. Completing a value only
inserts it into the command line.

```sh
anodize create --interactive
anodize edit dusk --interactive
anodize extract ./picture.jpg --interactive
anodize create dawn --image ./picture.jpg --builtin --dry-run
anodize promote dusk --dry-run
anodize promote dusk --yes
anodize promote dusk --copy --name dusk-bundled --yes
```

Promotion uses a retained file transaction: it stages the repository copy before
removing the user directory and supports rollback, recovery and undo. It preserves
backgrounds and unrelated regular files. Copies require a distinct unused ID and
update recipe/metadata receipts. Duplicate user/built-in IDs, occupied targets,
generated-file drift and unsafe trees are refused. Built-in storage does not select
the theme or commit it to Git.

## Repeatable editing

```sh
anodize edit dusk --adjust saturation=12 --adjust gamma=1.1 --set accent='#b48ead' --dry-run
anodize edit dusk --adjust saturation=12 --adjust gamma=1.1 --set accent='#b48ead' --yes
anodize edit dusk --reset-adjustments --yes
anodize create dawn --from dusk --light --yes
```

Adjustments are absolute values applied to the saved baseline, followed by explicit color overrides. Repeating an edit does not compound it. Reset clears adjustments and retains overrides. Named keys are used for overrides; for example use `background`, not the derived `color0` alias. All colors are six-digit hex values. Supported adjustments are `vibrance`, `saturation`, `contrast`, `brightness`, `shadows`, `highlights`, `temperature`, `tint`, `blackPoint`, `whitePoint` (-100 through 100), `hueShift` (-360 through 360), and `gamma` (0.1 through 10). Defaults are zero except gamma, which is 1.

Changing mode or light/dark regenerates from the saved wallpaper or seed when available, otherwise from the existing baseline palette. `--reextract` explicitly requires the saved source. Overrides remain applied after regeneration. Foreground/background contrast is informational; Anodize does not claim that every mode or adjustment combination meets an accessibility standard.

## Recipe and ownership

A new authored theme defaults to `${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes/ID/`, containing `colors.toml`, `theme.toml`, `anodize.json`, and an optional `backgrounds/wallpaper.ext`. `create --builtin` and `import --builtin` instead save into `$DOTS/themes/ID/`; without `DOTS`, the CLI uses its own checkout. Native Windows uses `%APPDATA%/dots/themes` unless XDG is explicit. Existing themes stay where they are and edits update their current location. The schema-1 recipe contains:

- `id`, `schema`, and `options` (`mode`, boolean `light`).
- `baseline`: unadjusted named colors; `adjustments`: numeric settings; `overrides`: explicit named hex colors.
- Optional `seed`, `wallpaper`, and `provenance`.
- `generated`: local SHA-256 receipts for generated files. Exports omit receipts; imports create fresh receipts.

The baseline requires the 16 named ANSI slots: background, red, green, yellow, blue, magenta, cyan, foreground, muted, bright_red, bright_green, bright_yellow, bright_blue, bright_magenta, bright_cyan, bright_foreground. Rendering preserves extra named colors, fills semantic defaults, and derives `color0` through `color15`. `mode` is reserved for TOML metadata.

Edits validate receipts and refuse changed generated files. Unrelated regular files in the theme directory survive edits. Theme trees containing symlinks or special objects are refused. Saves stage a complete replacement and use the existing transaction Store with retained snapshots, drift guards, reverse rollback and recovery. The result includes a transaction ID and `dots files undo ID` hint; existing `dots files history`, `recover`, and `backups` inspect those records. See [file recovery](files.md) and [safety](safety.md).

Wallpaper files are copied by default. `--reference-wallpaper` keeps an explicit absolute external dependency, which must remain available. Relative references in imported Anodize blueprints resolve against the blueprint location. Exported recipes turn copied wallpaper references into absolute source paths; the JSON is not a self-contained image archive. Sharing it requires transferring the image too and updating its path.

## Interoperability and publication

Aether JSON imports require `palette.colors` with 16 colors and preserve supported `extendedColors`. Imported colors are treated as already adjusted; Aether adjustment settings are retained as provenance, not applied again. App settings, native app overrides, locked colors, extra images, URL downloads and wallpaper effects are not imported. Aether exports contain rendered colors, not an editable reconstruction of its complete desktop state. Base16 import supports flat `base00` through `base0F` JSON or simple YAML color entries; arbitrary YAML structures and tags are not evaluated. Colors import/export uses Dots flat `colors.toml`.

Apply preflights the current publisher's target set and renders templates into disposable storage before approval. Publication retains the existing atomic generation, connector and recovery behavior. Published schema-1 `palette.json` now has an additive `colors` map, alongside the existing `palette`, `roles`, and `adapter` fields. This supplies normalized named colors and ANSI aliases for consumers such as Anodize.nvim; older consumers continue reading their existing fields.

`--background` preflights image availability, session support and adapter executable availability. It then invokes the existing wallpaper adapter after theme publication. GIF extraction is supported, but GIF wallpaper activation is not. If the external wallpaper command fails after publication, the CLI returns an error and states that the app theme remains published. It does not claim to undo desktop wallpaper side effects.

## Portability and provenance

Native Termux is the tested CLI target. Linux/WSL use the existing POSIX adapter boundaries but are not newly certified by these tests; WSL wallpaper changes remain unavailable. Native PowerShell authoring and publication adapters are implemented with Windows runtime acceptance pending; see [native PowerShell](powershell.md). An Android APK and a TUI remain future work. The pure Go library has no desktop dependencies; Android packaging and language bindings are not implemented.

Color math and generation are adapted from the pinned local Aether source. See [provenance](../plugins/anodize/engine/PROVENANCE.md) for revision, attribution and the upstream README's license declaration. Standard-library image sampling differs from Aether's desktop resampling, so exact image results can differ. No desktop UI, network services or arbitrary theme hooks are included. The separate `~/repos/Anodize.nvim` project owns plugin development; Dots integrates its tested local runtime.

## Neovim integration

The Dots Neovim configuration declares the local `~/repos/Anodize.nvim` checkout,
with `ANODIZE_NVIM_DIR` as an optional path override. Restart Neovim normally to load
the updated specification. Startup selects `anodize`; `:AnodizeStatus` reports its
source and generation. `:DotsThemeReload` remains an alias for active-only reload.
To return after manually choosing another scheme, use `:colorscheme anodize`.

The editor reads published JSON only; saving an authored theme without applying it
does not change the editor. Anodize owns watchers/focus/resume, replacing the old
bridge lifecycle. Dots retains personal highlights, Mocha exceptions, transparent
main windows, opaque floats, disabled terminal assignments and inactive dimming.
The dashboard animation source is unchanged; its palette access uses normalized
roles and repaint preserves elapsed time. Lualine selects `anodize` without layout
changes. Legacy raw palette helpers remain available for private consumers.

The local plugin must be present; no remote is invented or fetched. Missing plugin
source gives a warning and bundled habamax fallback. Missing shared state uses
Anodize's built-in palette. Invalid updates preserve the last working colors.
See the [nested configuration guide](https://github.com/5nik7/nvim/blob/1ae8641e206927ee12572a28a5082992ae5e7981/README.md#shared-dots-themes-through-anodize)
and [integration validation](testing.md#anodize-neovim-integration).

## Explicitly enabled local theme plugins

Apply uses the shared Dots publisher's [plugin runner](theme-plugins.md). A new
publication runs enabled plugins once; create/edit/save/export/preview and dry-run
never execute them. Unchanged apply is a no-op; `dots theme refresh` or
`dots theme plugins run` retries integrations explicitly. Automatic hook failures
leave the theme published and report retry guidance on stderr without corrupting
Anodize JSON. The separate Anodize.nvim project is unchanged.


Selecting Anodize in checkout setup now prepares its engine in owned build storage, runs its Go tests, and journals publication into `engine/.build`. The checked-in `go.mod` determines the minimum toolchain. Verified artifacts are reused on repeats. Missing Go is offered through reviewed dependency preparation; help and ordinary shell startup never build.
