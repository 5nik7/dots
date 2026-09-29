# Shared shell utilities

**Implemented.** Source `bin/lib/common.sh` from Bash or Zsh to define the shared helpers. Loading uses shell builtins and does not run optional tools or load presentation code. These are shell functions, separate from the `dots` command routes. Case conversion requires Bash 4 or newer; global associative array builders require Bash 4.2 or newer. `bin/util` has been removed without a forwarding file. Bash startup retains the exported `UTIL` variable, pointing to common.

## Paths and commands

- `prepath DIRECTORY` and `extpath DIRECTORY` prepend or append one existing directory. Membership is literal, existing entries keep their order, and repeated additions do nothing. An empty or unset PATH gains no empty entry. Missing directories return 1; missing, empty or extra arguments return 2.
- `has [-v] COMMAND...` checks every command with `command -v`, including functions and builtins. It accepts the existing `"command arguments"` shorthand by checking the first space-delimited word. No arguments or an unavailable command returns 1; verbose diagnostics go to stderr.
- `chcmd COMMAND [ARG...]` invokes the command exactly once, retaining its output, side effects and status. No command returns 2. This fixes the old double execution of successful commands.
- `shell` prints the basename of the configured `$SHELL`. `shellmod` selects the running interpreter independently.
- `upper [TEXT...]` and `lower [TEXT...]` join arguments with the shell's `$*` convention and convert case with builtins. Literal backslashes and leading dashes are preserved; locale controls character conversion.
- `is_installed PACKAGE` uses optional `dpkg-query` to require the actual package state `installed`, including held packages. Residual configuration alone does not count as installed. It returns 1 when the tool/package is unavailable or the status differs, and 2 for invalid arguments. It never installs or changes packages and is not a cross-platform package-manager adapter.

## Loading and checking files

`so FILE...` sources readable, nonempty regular files, preserving separate arguments and source side effects in the current shell. Relative filenames are sourced from the current directory without a PATH search. `shellmod NAME...` sources readable modules from `$DOTS/shells/bash/NAME.bash` or `$DOTS/shells/zsh/NAME.zsh`, falling back to `$HOME/dots` if DOTS is unset or empty. Empty module files are allowed. `zieces` remains an alias for `shellmod`.

`check PATH...` succeeds if any path exists; `checkdir PATH...` requires any directory. Broken symlinks do not match. All four helpers accept `-v`/`--verbose` (and the legacy `--verboss`), `-1`/`--first`, and `--` before literal names. A nonempty `buggin` value other than `0` enables verbose output. `--first` stops at the first matching candidate, including a file whose source returns failure.

No matches returns 1. Source helpers otherwise return the first nonzero source status, continuing through later candidates unless `--first` was requested. Missing optional files do not change success when another candidate loads. Sourced scripts should return an explicit nonzero status to report failure; normal shell rules apply to sources evaluated in a conditional. Verbose output reports each found, missing, sourced or failed candidate without invoking display tools.

`addir [-v|--verbose|--verboss] [--] DIRECTORY...` creates missing directories with `mkdir -p --`. Existing directories succeed without mutation; regular files and broken symlinks are refused. It continues through requested paths and returns a failure if any creation or refusal fails. No arguments prints usage to stderr and returns 2. Quiet calls do no display work. This is an ordinary shell helper, not a managed-file installation operation.

## Output helpers

`err`, `warn` and `ok` render one message per argument. They lazily use the shared [presentation renderer](presentation.md), including `DOTS_COLOR`, `DOTS_ICONS`, `NO_COLOR` and terminal detection. Warnings/errors use stderr; success uses stdout. Pipes become readable separators, and terminal controls in messages are escaped. A standalone copy without `lib/dots/ui.bash` falls back to plain ASCII markers. The removed `box` utility is no longer required.

`pathout [-r|--raw] [--] PATH...` emits one path per argument. Normally a literal HOME prefix becomes `~`; raw output retains the exact input. `dirout [-r|--raw] [-j|--join] [-c|--color] [--] PATH...` computes directory names with builtins, defaulting to the current directory's parent when no path is provided. `-j` appends a slash; explicit `-c` requests shared blue/reset styling, honoring `DOTS_COLOR`, `NO_COLOR` and terminal detection. Without `-c`, presentation settings never decorate path output. `-r` only disables home abbreviation and may be combined with `-c`. Caller BLUE/RST values are ignored and left untouched. The standalone `scripts/dirout` applies the same styling policy and preserves its path behavior; it locates the renderer relative to its resolved script location and falls back to plain output when unavailable.

`filename PATH...` emits basenames in argument order, optionally colored by eza when available, with a plain builtin fallback when eza is absent or fails. `fileicon PATH...` extracts optional eza icons and emits an empty line if eza is absent or fails. These two helpers are for explicit display; checks and source operations do not call them. Use `pathout --raw` for literal path data.

See [utility verification](testing.md#shared-shell-utilities) for isolated tests, benchmarks and platform limits.

## Color arrays and retired globals

Source common and call `build_color_arrays` to initialize the global associative arrays `COLOR`, `FG`, and `BG`. The individual builders `color_array`, `fg_array`, and `bg_array` rebuild only their corresponding array. Every array has keys 0 through 255; repeated construction replaces its contents without leaking loop counters. FG contains `ESC[38;5;Nm`, BG contains `ESC[48;5;Nm`, and COLOR contains `ESC[38;5;Nmcolor N`, where ESC is the literal escape byte and N is the key. These are raw color values, independent of `DOTS_COLOR`, icons, and terminal detection.

`bin/colors.env` has been removed without a forwarding file. Bash/Zsh startup and the compatibility profiles explicitly build arrays after sourcing common. Startup no longer initializes named palette/terminal globals such as RED, BLUE, BOLD, RST or rst, and Bash no longer exports a COLORS path. Existing caller variables are neither unset nor overwritten; a fresh shell simply omits these Dots-provided values. Independently defined colors in other scripts remain local to those scripts. Merely sourcing common does not initialize arrays or colors, launch tools, change traps, or print output.

## Logging, formatting and spinners

`setup_colors [FD]` initializes shared renderer values lazily; it does not overwrite or make named shell colors readonly. `log_info`, `log_success`, `log_warning`, and `log_error` use the shared message policy. Warnings/errors go to stderr, and information/success go to stdout. `fmt_key`, `fmt_value`, `fmt_cmd`, and `fmt_path` print inline values; `fmt_title`, `fmt_title_underline`, and `fmt_title_border` print title lines. All have plain fallbacks and escape embedded terminal controls.

`spinner PID [STYLE [MESSAGE]]` monitors a positive process ID. `run_with_spinner COMMAND [STYLE [MESSAGE [SHOW_RESULT]]]` evaluates one trusted shell command string exactly once and returns its status; SHOW_RESULT=1 adds a success/failure message. This legacy string interface is shell code, so do not interpolate untrusted input into it. The command runs in a child shell; for a long-running external job, `exec command ...` makes that job the directly owned process. Arbitrary detached descendants are the command's responsibility.

Animation starts after 500 ms, uses stderr, and requires terminal stdout/stderr, a non-dumb terminal, and `DOTS_PROGRESS=auto` (the default). `never`, invalid values, redirected streams, or missing sleep disable animation. Color and icon controls follow the shared presentation policy. Completion and interruption clear the display; the helper reaps its owned command/rendering processes and restores caller signal traps. Interrupt and terminate return 130 and 143 respectively. The cursor remains visible.
