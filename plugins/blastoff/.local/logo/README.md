#  blastoff — terminal wordmark

Unicode block artwork adapted from the purple-to-pink blastoff logo. The rocket is negative space in the **o**; the fine exhaust ribbons are simplified for terminal legibility.

## Run

The renderer is a self-contained Bash script. It does not need Python, an image converter, font downloads, or the other files in this package. Your terminal must display UTF-8 block characters; the color gradient requires 24-bit/true-color support.

```bash
bash blastoff-logo.sh
bash blastoff-logo.sh --size compact
bash blastoff-logo.sh --size wide
bash blastoff-logo.sh --size compact --no-color
bash blastoff-logo.sh --help
```

It emits foreground colors only, so your terminal background shows through the spaces and rocket cutout. The preview PNGs use a dark background solely to illustrate the output. Appearance can vary slightly with your terminal font.

## Layouts

| Layout        | Columns | Rows |
| ------------- | ------: | ---: |
| Compact       |      60 |    8 |
| Wide          |      96 |   11 |
| Word fallback |       8 |    1 |

The default `--size auto` chooses wide at 96 or more columns, compact at 60–95 columns, and the small word fallback below 60. Set `COLUMNS` to override detection. When available, `tput cols` supplies the terminal width; otherwise it defaults to 60. Choosing an explicit size disables automatic fitting.

## Color and export

The horizontal gradient runs from `#651eff` to `#ff43bf`. Automatic color is enabled only for terminal output, with `TERM` other than `dumb` and without a nonempty `NO_COLOR` variable. Use `--color always` to force color; it takes precedence over `NO_COLOR`.

```bash
# Redirect plain text, without escape sequences.
bash blastoff-logo.sh --size wide --no-color > logo.txt

# Save real ANSI escape sequences for later display.
bash blastoff-logo.sh --size wide --color always > logo.ansi
cat logo.ansi

# Read the prebuilt assets directly.
cat blastoff-compact.ansi
cat blastoff-wide.ansi
```

The `.ansi` files contain real escape characters, not printable `\\e` sequences. A text editor may show those codes literally; display the files in a true-color terminal.

## Optional Termux installation

Run these commands from the extracted package directory:

```bash
install -m 755 blastoff-logo.sh "$PREFIX/bin/blastoff-logo"
blastoff-logo
```

To display it when opening an interactive Zsh shell, add this line to `~/.zshrc` after installing:

```bash
[[ -o interactive && -t 1 ]] && blastoff-logo
```

The script should be executed, not sourced.

## Package contents

- `blastoff-logo.sh`: standalone renderer with automatic sizing and color controls.
- `blastoff-compact.txt` / `blastoff-wide.txt`: plain UTF-8 block artwork.
- `blastoff-compact.ansi` / `blastoff-wide.ansi`: precolored terminal artwork.
- `preview-compact.png` / `preview-wide.png`: block-cell previews on a dark background.

## Validation

Checked with Bash syntax validation and 26 automated scenarios covering exact artwork round-tripping, column widths, color channels, foreground-only escape sequences, ASCII-locale and UTF-8-locale handling, size selection, invalid options, redirected output, and pseudoterminal color behavior. These checks were run in the build environment, not on an Android device.
