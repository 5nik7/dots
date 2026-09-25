# Anodize

**Status: Implemented core, CLI and local Neovim integration; Android app and TUI deferred.**

Anodize creates and edits Dots themes from local images, seed colors, existing themes and imported palettes. Its reusable Go package performs extraction and color adjustments without filesystem or process access. The CLI reuses Dots presentation, file transactions and theme publication. [Decision 0011](decisions/0011-anodize-authoring.md) defines these boundaries.

## Build and first use

Use installed Go 1.27.1, Python 3.11 or newer, Bash and the existing POSIX theme tools. From the Dots checkout:

```sh
python3 -B tools/verify_anodize.py check
python3 -B tools/verify_anodize.py build
bin/anodize modes
bin/anodize create dusk --color '#725ac1' --dry-run
bin/anodize create dusk --color '#725ac1' --yes
bin/anodize preview dusk
bin/anodize apply dusk --dry-run
```

`dots anodize` exposes the same commands when Dots is on PATH. Building explicitly replaces the ignored `anodize/.build/anodize-engine` artifact. There are no runtime builds, downloads or shell-startup engine calls. `ANODIZE_ENGINE` can point to a prebuilt executable for testing. Help works without the engine; palette operations explain how to build it if missing. Run `anodize` or `anodize --help` for a compact command list and examples, and `anodize COMMAND --help` for described arguments and options. Help adapts to terminal width and uses shared Dots colors, including plain output with `NO_COLOR` or `--color=never`.

Saving a theme does not select or activate it. Review `anodize apply dusk --dry-run`, then use `anodize apply dusk --yes` to publish. Mutating commands prompt on interactive input; without a terminal or with `--json`, omission of `--yes` returns the preview. `--dry-run` takes precedence over `--yes` and creates no persistent state.

## Commands and flags

Authoring commands accept `--json` for a schema-1 response unless they return a raw format. `completion` emits only shell source and does not accept `--json`. Prefix `--color=auto|always|never` and `--icons=auto|always|never` follow the shared presentation policy. `--color HEX` after `create` means the seed color.

| Route | Inputs and behavior |
| --- | --- |
| `completion SHELL` | Print Bash, Zsh or Fish completion source; no engine required. |
| `modes` | List the 23 supported extraction modes. |
| `extract IMAGE` | Inspect colors and foreground/background contrast without saving. Supports `--mode`, `--light`, `--dark`. |
| `create ID` | Exactly one of `--image FILE`, `--color '#RRGGBB'`, `--from THEME`. Supports generation flags, `--adjust NAME=VALUE`, `--set COLOR=HEX`, and `--reference-wallpaper`. |
| `import FILE --name ID --format FORMAT` | Import `anodize`, `aether`, `base16`, or `colors`. Supports generation flags and `--reference-wallpaper`. |
| `list` | List authored themes in the repository. |
| `show ID` | Inspect an authored or existing Dots theme. |
| `edit ID` | Edit an Anodize-owned theme. Supports generation flags, adjustments, overrides, `--reset-adjustments`, `--reextract`, and `--reference-wallpaper`. Derive other themes with `create --from`. |
| `preview ID` | Show colors, or use `--app kitty|tmux|btop|termux|bat|yazi` for raw generated configuration. `--app` cannot combine with `--json`. |
| `export ID` | Raw stdout by default; `--format anodize|aether|colors`. `--output FILE` saves through a journal and refuses existing targets. |
| `apply ID` | Preview/publish with the existing Dots publisher; optional `--background` explicitly requests a subsequent wallpaper action. |

Create, import, edit, export-to-file and apply accept `--dry-run` and `--yes`. Raw stdout export is already read-only; `--dry-run` requires `--output`. Raw exports and app previews never receive ANSI decoration. Diagnostics go to stderr. Exit status is 0 for success/preview, 2 for argument usage errors, and 1 for validation or operational failures.

IDs start with a lowercase letter and contain lowercase letters, digits, `_` or `-`. New IDs refuse repository and installed-user-theme collisions. PNG, JPEG and GIF input is limited to 32 MiB and 20 million pixels; transparent images without sufficiently opaque pixels are rejected. Extraction defaults to normal/dark. `--light` and `--dark` are mutually exclusive. Use `modes` as the authoritative list of modes.

## Shell completion and manual

All three supported shells complete commands, flags, extraction modes, adjustment names, built-in named color keys, theme IDs, formats, app names and file paths. Both `--option value` and `--option=value` work. `edit` suggests only repository themes with an Anodize recipe. New theme IDs and arbitrary hex/numeric values are entered manually. `--color=always` before the command controls presentation; `create --color HEX` remains a seed color.

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

The section-1 manual is [man/anodize.1](../man/anodize.1). From the checkout, read it without installation:

```sh
man -l man/anodize.1
```

To make `man anodize` available, install that file as `anodize.1` in a `man1` directory on your manual search path (for example `$PREFIX/share/man/man1` on Termux or `~/.local/share/man/man1` with a configured user manpath). This change does not install system files automatically.

The adapters are generated from the shared Dots shell adapters; the manual's command/option reference is generated from the CLI parser. After changing either source, run `python3 -B tools/generate_anodize_integration.py`; `--check` verifies checked-in artifacts without writing. Static wrapper headers remain the completion metadata source, with tests checking parser and engine vocabulary consistency.

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

An authored theme is `$DOTS/themes/ID/` containing `colors.toml`, `theme.toml`, `anodize.json`, and an optional `backgrounds/wallpaper.ext`. Without `DOTS`, the CLI uses its own checkout. The schema-1 recipe contains:

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

Native Termux is the tested CLI target. Linux/WSL use the existing POSIX adapter boundaries but are not newly certified by these tests; WSL wallpaper changes remain unavailable. Native Windows authoring, an Android APK and a TUI are future work. The pure Go library has no desktop dependencies; Android packaging and language bindings are not implemented.

Color math and generation are adapted from the pinned local Aether source. See [provenance](../anodize/PROVENANCE.md) for revision, attribution and the upstream README's license declaration. Standard-library image sampling differs from Aether's desktop resampling, so exact image results can differ. No desktop UI, network services or arbitrary theme hooks are included. The separate `~/repos/Anodize.nvim` project owns plugin development; Dots integrates its tested local runtime.

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
See the [nested configuration guide](../config/nvim/README.md#shared-dots-themes-through-anodize)
and [integration validation](testing.md#anodize-neovim-integration).
