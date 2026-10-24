# Command Model

**Status: Implemented Bash and native PowerShell command families**

Static built-in metadata and external command headers define the live routes. Bash and native PowerShell adapters expose file, Git, environment, theme and Anodize commands through shared controllers. This document describes their implemented interfaces.

The shared Bash/Zsh helper `mkcd <directory>` is separate from the `dots` command family. Its [usage and path handling](../README.md#zsh-configuration) are implemented by `scripts/mkcd`, sourced through the shared function to change the current shell's directory.

## Implemented shell initialization

The sourceable [shell utility functions](shell-utils.md) have their own documented argument, stream and status contracts; they do not add dispatcher routes or completion metadata.

`dots init [bash|zsh|fish|powershell|nu|xonsh]` emits native initialization code. With no argument, the generated code selects Bash or Zsh in the calling shell. `init` is reserved and bypasses extension discovery. Help and shell-name completion use built-in metadata. Native `bin/dots.ps1` supports shell-code initialization plus bounded setup, file inspection and installation recovery. Evaluating a hook loads only Dots integration from `lib/dots/shell/`; personal shell configuration stays separate. Settings use data-only config.env, with explicit environment overrides. Repository rc files resolve symlinks and source their adjacent loaders directly. See [shell initialization](shell-init.md) for the full interface, bootstrap, error statuses and native invocation examples.

`dots init --setup [OPTIONS]` explicitly delegates to `dots files install`; `dots files uninstall` restores installer-owned targets. Install/uninstall accept `--dry-run`, `--yes`, `--json` and shared color/icon controls; install also accepts `--update` and repeatable `--with-source androidots|windots|nvim`. Root shell/PowerShell scripts use the same controller. Setup options are invalid on shell-code generation paths. See [checkout installation](installation.md) for ownership, updater stages, JSON results and recovery.

POSIX setup and `dots theme refresh` check required generated outputs before
reporting an unchanged theme. Setup previews identify an incomplete artifact or
publication pointer in the existing item's target/reason fields. Repair prepares
a new generation; setup additionally installs missing catalog links, including
the FSH directory and connector in fresh checkouts. JSON schemas and flags are
unchanged, and shell-code initialization does not perform repairs.

Theme preparation supports older Vivid releases using [scalar compatibility
mode](file-colors.md#vivid-compatibility). Setup and theme publication emit one
shared-style compatibility warning on stderr when rendering with an older or
unrecognized Vivid version. JSON setup diagnostics remain plain even with forced
color; stdout schemas, raw exports, flags and completion behavior are unchanged.

## Implemented Files and Theme Routes

`dots files stash [RESOURCE...] [--restore]` disables resources and unlinks only
matching destinations; restore enables and relinks. `dots files edit [RESOURCE |
--new]` edits source/target mappings, metadata-only unless `--apply` is selected.
Both offer selection/review, `--yes`, `--dry-run`, `--json`, `--backup` and
`--no-backup`, static help/completion and native PowerShell routing. Edit supports
new-record metadata, strategies and platform target overrides. See
[mapping commands](files.md#stash-and-edit-mappings) for full semantics and JSON.

`dots files check [--yes] [--dry-run] [--json]` reviews absent source paths and
removes approved catalog entries only. It accepts list's platform/filter/sort
options, defaults to per-entry review followed by batch confirmation, and uses
journaled apply/undo. Broken source symlinks and all target objects are preserved.
Dry-run never prompts or writes; JSON requires `--yes` or `--dry-run`. Native
PowerShell routes to the same controller. See [check](files.md#check-missing-sources)
for result fields, exit statuses and the distinction from `files remove`.

The [files reference](files.md) defines `dots files sources|discover|list|locate|show|source|target|track`,
filters, sorting and schema-1 JSON. `track` changes catalog metadata only; bounded
managed operations are documented separately below. The [themes reference](themes.md) defines
`dots theme list|show|current|dir|color|set|refresh|init|switcher|install|update|remove`
and `dots theme bg list|current|set|next|select|switcher`.
The [local plugin manager](theme-plugins.md) implements `dots theme plugins` help,
`list [--json]`, `enable NAME`, `disable NAME`, `run [NAME] [--json]`, and
`doctor [NAME] [--json]`. Selection changes do not apply themes; run requires explicit
enablement. List/doctor are read-only; machine output uses schema-1 JSON. The unified `dots theme` interface uses full IDs; native palette discovery and
queries use `list --families`, `list --flavors FAMILY`, and `show`/`color --native`. Shell completion reads
static route metadata and core-owned data providers; it never executes extensions.
Published `theme init --shell bash|zsh|fish` output includes the FZF
environment colors described in the [template contract](themes.md#flat-themes-and-templates).
Bash/Zsh initialization also emits current-theme color arrays such as `${hint[hex]}`, using resolved Dots values over native palette values, while retaining fixed Catppuccin flavor arrays. Formats, reserved names and switch cleanup are defined in the [shell color API](themes.md#shell-and-neovim-behavior).
`theme set`/`refresh` also render the Pi theme and connect an existing agent themes
directory through the same journal; dry-run previews include that target. See
[Pi setup](themes.md#pi) for selection, custom paths and automatic reload.
The same commands connect the shared syntax theme to an existing Codex themes
directory; dry runs include `dots.tmTheme`. Codex configuration remains unchanged
by publication. See [Codex setup](themes.md#codex-and-codex-termux).
They also render Vivid/FSH templates and journal connectors in existing app config
directories; dry runs include `dots.yml` and `dots.ini`. The Bash/Zsh adapters use
the published colors. See [Vivid and FSH](themes.md#vivid-and-fast-syntax-highlighting).

## Implemented Git and managed-file operations

The [Git reference](git.md) defines `dots git info|submodule|submodules|status|publish|sync`, recursive
semantics, configuration, compact views and JSON. Git synchronization now belongs
to `dots git sync`; the former proposed `dots repo pull` spelling is superseded.
This remains distinct from future bootstrap and optional-source resolution.

Implemented routes: `dots git info`, `dots git submodules`,
`dots git submodules info`,
`dots git submodules status [PATH]`, and
`dots git submodules publish PATH|--all-submodules`.
All accept `-C`/`--directory`, `--json`, and `--full-paths`. The tree accepts
`--details` and positive `--depth N`; collection info also accepts `--depth N`.
Submodule status accepts `--dirty`.
`dots git submodule NAME [info|status|publish|submodules|submodule CHILD]`
provides named navigation; bare NAME defaults to info. Names are direct-child
path basenames and colon-separated names cross registered edges. Its leaf options
and help reuse the canonical action headers. Contextual name, action and option
completion is shared across all four shells; name discovery runs on demand.
Scoped publication retains the existing publish options and one combined approval;
`--all` selects unstaged files, while `--all-submodules` selects child subtrees.
Registered PATH operands are relative to the selected repository and complete in
Bash, Zsh, Fish and PowerShell through the core-owned `git-submodule` provider.
Human info `Path` fields use folder styling; human submodule trees maintain
connected guides through spacing, nesting, wrapping and details. Redirected
text and JSON keep their established formats.
See [Git commands](git.md#repository-info-and-submodules) for schemas, safety,
presentation, dependencies and examples. No new sync route is introduced.

The [files reference](files.md) also defines `locations`, `discover --system`,
`add`, `link`, `remove`/`rm`, `history`, `undo`, `recover` and
`backups list|show|restore`. Metadata-only `track` and existing inventory formats
remain compatible.

`files discover --system` groups config candidates by directory by default and
summarizes managed/excluded entries. `--verbose` shows individual files and source
mappings; `--all` includes the summarized statuses. Both flags require `--system`.
`--repo` filters owners, and `--json` always emits complete schema-1 `items` without
human grouping/filtering or decoration. Repository discovery keeps its existing
filters and format; see [files](files.md#user-configuration-discovery).

## Implemented Bash Command Framework

The live `bin/dots` follows [decision 0006](decisions/0006-bash-command-framework.md).
It requires Bash 4.4+.

### Routing and Roots

`dots-example-apply` is callable as `dots example apply`. Filenames use lowercase
segments matching `[a-z][a-z0-9]*`, separated by hyphens. Probe the longest initial
sequence of route words first, stopping at a flag, `--`, or another non-route
word; remaining arguments, including `--`, pass unchanged. Execute the selected
file directly with its shebang; no shell inference, output interception, or
argument evaluation occurs. Extension status and standard handles are preserved.

Search `$DOTS/bin`, `$DOTS/local/bin`, and repeated prefix
`--command-dir ABSOLUTE_DIRECTORY` additions. Missing default directories are
optional; explicit directories must exist. The same directory selected through
multiple aliases is searched once. `$DOTS` selects the repository; when unset,
infer it from the dispatcher location, resolving executable symlinks. Internal
libraries always come from the dispatcher installation. No PATH-wide or recursive
search occurs. Executable symlinks to regular files are allowed. Duplicate routes
across distinct roots fail; a nonexecutable or broken deeper candidate blocks
fallback. Roots are trusted execution inputs, not a sandbox.

The protected first tokens are `help`, `doctor`, `commands`, `completion`,
`version`, `status`, `spec`, `plan`, `apply`, `undo`, `history`, `backup`, `config`,
`bootstrap`, and `self`, plus the private `__complete` endpoint. Reserved but
unimplemented routes remain unavailable. Reservations do not add features.

### Public Interface

- `dots`, `dots help`, `dots -h`, `dots --help`: global help and visible commands.
- `dots help ROUTE...`, `dots ROUTE... --help`: static contextual help without
  executing an extension. A help flag before the first `--` is intercepted;
  after `--` it belongs to the extension. Groups show their visible descendants, including groups with an executable. An executable group runs normally when called without help.
- `dots commands`: visible built-ins and external commands in deterministic
  root/directory order. `dots commands --check` validates every definition,
  including hidden commands, and reports success only after complete validation.
- `dots completion bash|zsh|fish`: print the native adapter, without installation.
- `dots [-r|--raw] -d|--dir`: repository path, abbreviated beneath HOME unless raw.
- Prefix `--color=auto|always|never|none` and `--icons=auto|always|never`: presentation.
  Flags after the route belong to the extension, except intercepted help.

Success is 0. Unknown routes, collisions, malformed metadata, and access errors
are 1. Invalid dispatcher syntax is 2. `exec` launch failures retain Bash's
126/127 behavior. No `--version`, JSON catalog, or management operation is added.

Existing approval points in file operations, Anodize and Git publish prefer
optional Gum menus with Cancel selected by default. They retain existing text
fallbacks and command-specific JSON behavior; `--yes` and `--dry-run` bypass Gum.
No routes or flags change. See the [confirmation contract](presentation.md#optional-gum-interactions).

For `dots git publish --all`, ignore rules exclude new files; already tracked
files remain eligible even under ignored directories. Staging preserves registered
submodule pointers and may leave partial index changes on failure; see [Git](git.md).

`dots theme switcher` is an interactive-only route: fullscreen FZF selection with
a live bottom palette preview and current published FZF colors, falling back to
Gum or a numbered menu. Palette
review and Back/Apply/Cancel use Gum when available, otherwise a numbered menu. It takes no
arguments. Only Apply calls the existing publisher. Nonterminal input/output is
refused; use list/set for scripts. See the [switcher contract](themes.md#interactive-theme-switcher)
for cancellation and failure statuses. Help and completion remain static and do
not probe or invoke UI tools.

`dots theme bg switcher` uses fullscreen FZF with the prompt and list at the top,
basename-only labels (no extension), and
an optional bottom Chafa image preview occupying 70% of the height. Acceptance applies the selected full
path; hovering and cancellation do not apply changes. Without Chafa it remains a
text picker. See [backgrounds](themes.md) for adapter behavior.

`dots files browse [--repo ID] [--app APP] [--category CATEGORY] [--status STATUS]`
is a terminal-only, single-resource browser of tracked configs on the detected
platform. Its Link/Stop managing actions require an approved guarded preview;
retained backups can be toggled for the session. Explicit Exit succeeds; syntax
errors return 2 and operational errors return 1. Cancellation follows the
[browser contract](files.md#interactive-tracked-config-browser). It adds no JSON,
unattended, platform override or batch interface. Its static header supplies help,
route/flag completion and repository-ID completion without invoking the browser.

### Tmux keybinding reference

**Implemented.** `dots menu tmux keys [--print]`, also available directly as `dots-menu-tmux-keys`, is a read-only human reference for the currently addressed tmux server. It lists bindings with nonempty `-N` notes, including defaults and plugins, but never their command bodies or an executable selection. It does not read tmux configuration files. Sections are `prefix`, `root`, `copy-mode-vi`, `copy-mode`, then other tables lexically, omitting empty sections and preserving tmux's key order within each table. The legend shows distinct enabled `prefix`/`prefix2` values from the current pane's session, or global values when no pane context is available. Custom table names do not imply a particular entry sequence.

With terminal stdin/stdout and a non-dumb terminal, the command opens optional `less -R`: `/` searches, `n` advances, and `q` closes. Short lists remain open. Pager settings are child-local, inherited `LESS` options and preprocessor hooks are cleared, and secure mode disables shell/editor escapes. `$PAGER` is not evaluated. Missing `less` produces a warning and a complete printed view; pager failures do not retry through another backend. `--print` and redirected output bypass paging; empty collections also print directly, with a hint to add `bind -N` descriptions. Printed text is a human interface, not a stable machine schema.

The shared presentation controls apply, including automatic color based on the destination terminal before pager piping, independent stderr styling, `NO_COLOR`, and readable ASCII fallbacks. Keys and descriptions stay on the same logical line even in narrow popups, with a compact per-table key column padded to at most 12 characters. Longer keys and descriptions remain complete and may wrap naturally in the terminal; the prefix legend is also inline. Control characters in queried values are shown as visible escapes, never passed to the terminal. There is no JSON interface.

Requires Bash 4.4+ and tmux with `list-keys -F`, `key_table`/`key_string`/`key_note`, and `q|a` format support; native verification used tmux 3.7c. One formatted listing safely quotes field values, and the command parses it without evaluation. The global tmux `-N` flag prohibits starting a server; `-u` preserves Unicode and separators even under an ASCII client locale. Unsupported/malformed listings, unavailable servers, and failed prefix queries produce no partial stdout. No configuration is sourced, server reloaded, or state written.

`-h`/`--help` works without tmux or less. Static metadata provides route and `--print` completion for Bash/Zsh/Fish without invoking either tool. Success, empty results, and normal pager exit return 0; operational/pager failures return 1; unknown arguments return 2; pager interruption returns 130. The [README](../README.md#tmux-keybinding-reference) shows the popup binding. Its styled bold yellow icon title uses tmux's terminal palette. The shared tmux theme supplies `background` and `foreground` as the default popup content colors, with borders using `lighter_background` on `background`; the binding inherits this border style. These tmux-owned decorations are independent of the viewer's Dots color controls. The direct executable must be on tmux's PATH.

### Optional Metadata

Read the initial shebang/comment/blank-line header only, up to 128 lines and
16 KiB. Stop at the first code line. Metadata is literal text, never sourced.
Control characters are refused in declarations; CRLF line endings are accepted.
Routes come from filenames, not headers. Missing declarations get generic help;
malformed declarations fail help/discovery/validation but do not block ordinary
direct execution. Discovery validates before emitting its catalog.

```bash
#!/usr/bin/env bash
# dots:summary=Manage example themes
# dots:usage=[OPTIONS] DIRECTORY
# dots:example=dots example --flavor mocha ./themes
# dots:option=--flavor|-f|choice:mocha,latte|Palette flavor
# dots:option=--verbose|-v|flag|Verbose output
# dots:argument=1|directory|Theme directory
# dots:hidden=false
```

This is an authoring example, not a shipped theme command. `summary`, `usage`,
and `hidden` may appear once; `example`, `option`, and `argument` repeat. Unknown
fields fail validation. `hidden` is `true` or `false`, defaulting to false.

Option records are `LONG|SHORT|TYPE|DESCRIPTION`, with an empty SHORT allowed.
Long names use `--[a-z][a-z0-9-]*`; short names are one alphanumeric character
preceded by `-`. Option names must be unique. Positional records are
`POSITION|TYPE|DESCRIPTION`: positions start at 1 and are contiguous; a final `*`
applies to remaining positions. Types are `flag` (options only), `string`, `file`,
`directory`, `choice:VALUE,VALUE`, or the core-owned theme data types
`theme`, `flavor`, `palette-color`, `color-format`, `theme-id`, `theme-color`, `theme-plugin`, `file-resource`,
`file-repository`, and `git-submodule`. The latter reads registered descendant paths
relative to Dots or a preceding `-C`/`--directory`, without initialization or network.
`theme-plugin` reads local plugin names without executing hooks;
`theme-id`, `file-resource`, and `file-repository` read flat theme IDs and qualified catalog IDs. Theme ID and native family/flavor enumeration use the data-only shared theme discovery module; current-ID reconstruction is shared with theme queries. Flat completion retains literal filename hints (including duplicates and invalid names); listing validates/deduplicates IDs and selection still validates them. `theme` lists native families for `list --flavors`. `theme-color` reads the selected theme or a preceding `--theme ID`/`--theme=ID`, honoring a preceding `--native`; it suggests native names alone in native mode and semantic/native names otherwise. The retained generic `flavor`/`palette-color` metadata providers use preceding positional family/flavor arguments. All providers read data and never execute
extensions. Fields cannot contain `|`; choice values
cannot contain commas. Descriptions are required. No code callbacks, aliases,
implicit option grammar, or combined-short-option parsing are provided.

### Presentation Helpers

The [presentation contract](presentation.md) defines the required visual language and acceptance gate for every new or changed first-party human view. The helpers and controls below are implemented; broader adoption follows each command's authorized implementation scope.

Bash extensions may `source "$DOTS_LIB_DIR/ui.bash"` when launched through dots.
The sourceable helpers are `dots::heading`, `dots::row`, `dots::kv`, `dots::info`,
`dots::success`, `dots::warning`, and `dots::error`. Rows/kv take label and value;
other helpers take message text. Warnings/errors write stderr, other helpers
stdout. Directly invoked standalone extensions must locate/source the library
explicitly if `DOTS_LIB_DIR` is absent.

`DOTS_COLOR` and `DOTS_ICONS` default to `auto`; explicit prefix flags override
them and are exported to extensions. Automatic color requires the destination
stream to be a terminal, TERM other than dumb, and empty/unset NO_COLOR. Explicit
always can override NO_COLOR. Automatic icons require a usable terminal; there
is no font detection. Use `--icons=never` for ASCII status markers. Stdout and
stderr are styled independently. Directory output and completion data remain
plain. Shared helpers use Bash builtins and ANSI colors, not the shell startup
chain, theme generators, or the general-purpose `bin/lib/common.sh` helper. Common loads this renderer lazily when a human output helper is called. The shared and standalone `dirout` helpers opt into this policy with `-c`; calls without `-c` stay undecorated. They no longer consume legacy BLUE/RST globals. See [shell utilities](shell-utils.md) for their separate shell interfaces.

Global help renders the optional `$DOTS/logo.txt` with a top-to-bottom blue-to-cyan truecolor gradient through `dots::logo`. It preserves the artwork and follows the same color controls; redirected automatic output stays plain. No external coloring tool is required.

`DOTS_PROGRESS=auto|never` controls the [operation progress display](presentation.md#operation-progress), independently of color/icons. Unset means `auto`; invalid values disable progress. There is no new route, flag or completion token. Human terminal work can animate after 500 ms, including read-only scans and `--yes` operations. Data, dry-run and redirected modes bypass the display even with forced decoration.

Theme and file human views share this presentation policy. Terminal listings use
headings, status colors/icons, counts and readable paths; forced color or icons also
enable that layout when redirected. `NO_COLOR` disables automatic color while
retaining the terminal layout. `dots --color=never --icons=never ...` gives a plain
terminal view. Lists piped without forced decoration retain their existing line/TSV
formats. JSON, file source/target queries, theme current/dir/color/background-current
queries, shell initialization and completion keep their data format even when
color is forced (explicit ANSI color-value formats still return ANSI as requested).

`dots::human`, `dots::path` and `dots::swatch` support the Bash theme views. The
Python file catalog implements the same color/icon policy for its own output.
Completion explicitly requests undecorated catalog rows, regardless of global
presentation settings. Neither view loads shell configuration or introduces a
startup scan. Executable-group help lists static child metadata without running
commands, so `dots theme`, `dots files` and `dots theme bg` are discoverable menus.

### Completion

All adapters query the dispatcher on Tab, not on shell startup. A typed route prefix restricts metadata reads to matching filenames; an empty prefix enumerates the full catalog. New commands and
metadata edits are reflected on the next request. Hints cover route words,
built-in flags, declared extension options, fixed choices, and native shell
file/directory completion. Options consuming values, long `--name=value`, `--`,
and cursor position are respected. Completion handles literal quoting without evaluating shell substitutions. Unknown option grammar stops argument hints
rather than guessing. Undeclared arguments do not get inferred file candidates.
Descriptions are supplied where supported. Zsh menu labels show `value -- description`, padding names to a shared column
(including FZF-tab); accepting a match inserts only its value. Hidden routes are omitted from normal
suggestions, but explicit use remains possible.

Repository Bash startup sources its adapter; Zsh and Fish use their existing
completion directories. Zsh does not run another compinit. Fresh shells load the
new files; other installations can source the output of `dots completion SHELL`
using that shell's normal mechanisms. No live-home installation is performed.

The internal `__complete SHELL INDEX -- WORDS...` interface takes the command
word at index 0 and includes an empty current word when appropriate. It emits
literal tab-separated candidate/value/description records or file/directory
instructions; adapters never eval them. It is private to these adapters, not a
versioned public API. Failed queries produce no candidates or diagnostics.

## Implemented Bash Theme Commands

The route, argument, format, compatibility and exit-status contract is maintained
in [Shared themes](themes.md#commands). Static headers on the official
`dots-theme-*` entry points drive dispatcher help and completion. The closed
palette providers augment that metadata with current theme files; they do not
introduce extension callbacks. `theme set` delegates
state publication to the shared helper described in [decision 0007](decisions/0007-data-driven-themes.md).
The supported families include hyphenated `rose-pine` identifiers and native palette
keys such as `sumiInk3`. All three shell providers discover full IDs, families and contextual colors;
pywal16 flavor discovery works without its optional generated input. Palette filtering and native query flags are documented in the shared theme reference.

Television theme publication uses the existing theme routes and their output contracts. See [Television integration](themes.md#television) for the `dots` theme selector, destination overrides, and journaled creation of its themes child directory.

## Implemented Anodize commands

Anodize-specific `--logo=text|auto|kitty|chafa` and `--logo-layout=auto|horizontal|stacked|icon` work before or after its subcommand, including static Dots help. Environment defaults are `ANODIZE_LOGO` and `ANODIZE_LOGO_LAYOUT`. Portable text branding is always present in human views; graphics are optional and data interfaces remain undecorated. Interactive and FZF-tab previews fit the supplied artwork to pane width and scroll vertically in short panes. See the authoritative [logo contract](anodize.md#terminal-logo).

`dots anodize` and standalone `anodize` expose the same authoring commands. The complete [command and flag contract](anodize.md#commands-and-flags) covers modes, extract, create, import, list, show, edit, preview, export, apply, promote and completion. `anodize completion bash|zsh|fish` (also `dots anodize completion`) emits standalone shell integration as plain source. Static choices cover extraction modes, adjustment/color keys, formats and apps; the `anodize-theme` metadata type supplies authored theme IDs from both user and repository roots for edit; `anodize-user-theme` limits promotion suggestions to user-authored themes. See the [completion and manual guide](anodize.md#shell-completion-and-manual). Static wrapper metadata supplies Dots help/discovery/completion without running the engine. Standalone `anodize --help` and `anodize COMMAND --help` use width-aware Dots presentation with command examples and option descriptions; argparse coloring is disabled so only the shared renderer emits ANSI. Mutations preview by default without interactive confirmation or `--yes`; raw exports/app previews remain undecorated. The private engine is built explicitly with `python3 -B tools/verify_anodize.py build`.

## Shared interactive shell commands

Bash and Zsh share the [interactive helper contract](shared-shells.md#commands-and-compatibility). `ff` opens FZF in both shells; `findfiles` preserves Bash's former filename search. `rl`, `rlc` and `rlcs` select native reload/completion implementations. These are shell helpers, not new `dots` command routes.

### Termux default-session launcher

**Implemented.** `androidots/bin/termux-bar [--auto]` creates or reattaches the current Termux tab's default session on the ordinary tmux server. It is a standalone Androidots executable, not a new `dots` route. `--auto` is the guarded Bash/Zsh startup mode; `-h`/`--help` prints plain help without session discovery or tmux. There are no positional arguments. Exit status is 0 for an automatic skip, 1 for launcher failures, 2 for invalid arguments and 130 for interrupted setup; after attachment, 0 means detach or successful manual completion and 1 means attachment failure. Automatic normal session exit returns internal status 20 to the Dots startup hook, which exits the outer shell. This status is not used for skipped startup. Diagnostics go to stderr, and successful attachment hands the terminal to tmux. See [startup and opt-out behavior](shell-init.md#termux-tmux-startup).

### Android status scripts

Androidots provides `termux-wifi-status`, `termux-cell-status`, `termux-notification-status`, `termux-location-status` and `termux-volume-status`, independently of the Dots command dispatcher. Volume is read-only, defaults to media (`music`) and accepts `--stream music|ring|notification|alarm|system|call`. All five support icons, text, JSON, getters, templates, cache controls and static Bash/Zsh/Fish completions. See the [status command contract](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-status.md).

## Unified theme entry points

`theme` is equivalent to `dots theme`. In addition to existing full-ID routes,
`dots theme FAMILY [FLAVOR] [show | set | COLOR [FORMAT]]` is implemented. Generated
`FAMILY` commands forward to this route; bare commands show usage and bare flavors
preview native palettes. `set` is always explicit. `refresh --commands-only`
rebuilds generated commands without activating a palette. Help and completion
read the same theme metadata without executing generated wrappers. See
[family shortcuts](themes.md#unified-commands-and-family-shortcuts) for compatibility
flags, defaults, collision handling and logo behavior.

## Dots environment and theme collection

`dots env [NAME] [--json]` reports resolved Dots settings and paths with provenance.
A named query is a plain scalar; JSON has version 1 and values/source records.
The human view groups current theme, settings and paths, with semantic colors,
boolean explanations and source labels. Narrow terminals stack fields and wrap
complete values, abbreviating the home directory as `~` in human path fields.
Unforced redirected listings retain full paths in `NAME=value [source]`;
color controls never decorate named scalar or JSON results. See
[environment views](shell-environment.md) for presentation details.
`theme` and `dots theme` without arguments show the selected palette; `current`
remains scalar. `dots themes` provides collection help and `list`, `switcher`,
`install`, `update`, `remove`, and `plugins` routes. Existing singular routes
remain aliases. See [shell environment](shell-environment.md) and
[decision 0013](decisions/0013-shell-environment-and-theme-collection.md).
The old standalone `current_theme` wrapper is removed; use `dots theme current`
for the selected ID, `theme` for its palette preview, and `theme init` for shell
color initialization.

## File and Git color operations

`dots theme colors` / `theme colors` exposes `type`, `mime`, `extension`, `git`, `match`,
`parse`, `export`, `set` and `reset`. Queries are read-only; edits save journaled
shared or per-theme overrides, with optional `--apply` to refresh the current theme.
See [file color syntax and data contracts](file-colors.md). Static metadata and
Bash/Zsh/Fish completion include operations, bundled/shared style keys, query
formats and attribute flags. The `file-color-key` metadata provider reads those
rule keys without executing a theme-family extension.

Human `theme show ID` and `theme colors` use consistent, counted palette, file and Git
style sections, with swatches and narrow-terminal layouts. Group listings,
`--style`, `match` and `parse` use tables or labeled details instead of nested
dictionary dumps. Native family previews keep their original palette scope.
Configured/published sources are labeled. JSON/Lua exports add the Git namespace within schema 1. Scalar formats, existing file-style fields, LS_COLORS and
unforced redirected `show` output remain unchanged; see
[human color views](file-colors.md#human-color-views).

Presentation adds `--color=none` as an alias for `never`. The global flag still
precedes Dots routes; family commands also accept it anywhere in their arguments.
The spaced family option `--color NAME` retains its palette-query meaning.

### Human resource fields

First-party human views render file/directory fields with published Dots file-type,
extension and MIME styles plus optional resource icons. Existing `--color` and
`--icons` controls apply; no new flags or routes are introduced. Raw path queries,
JSON, exports, completion, initialization code and documented redirected formats
remain undecorated. Theme panels retain their own palette. The sourceable Bash
helpers `dots::resource PATH [DISPLAY [KIND [MIME]]]` and
`dots::resource_row LABEL PATH [DISPLAY [KIND [MIME]]]` are presentation-only:
they never resolve a theme or alter a resource. See [presentation](presentation.md#filesystem-resources).

Git human output distinguishes owned repositories with the shared `git.repo_owned` role using local fetch-remote ownership metadata; see [Git theme colors](git.md#theme-colors). This does not add fields to JSON output or change publish/sync policy.

The bundled `starship` integration is available through existing `dots theme plugins` routes and completion. Enabling it permits palette-only updates on publication/refresh; it does not activate a Blastoff theme. See the [Starship/Blastoff adapter](theme-plugins.md#starship-and-blastoff-starship).

The existing `dots files link dots:git`, installation, mapping apply and stash
restore paths also preview/select the fixed Git platform companion. Direct Git
linking retains its installation baseline for uninstall even when optional backup
snapshots are disabled. No new public route or catalog field is introduced.

## Implemented verbose operation flags

`-v`/`--verbose` adds human action details to file install/uninstall/add/link/remove (including `rm`), undo/recover/backups restore, stash/edit/check, and explicit `init --setup`. Root setup/restore scripts forward it; PowerShell also accepts `-Verbose`. See [file operations](files.md#verbose-action-details) and [setup](installation.md#options-and-output).

Theme set/refresh (including `--commands-only`) and switcher accept the same flag; `themes switcher` is equivalent. These flags do not apply to scalar/query routes or ordinary shell initialization. Existing discovery verbosity retains its listing semantics. Default output and structured schemas are unchanged; JSON suppresses additional details. [Presentation](presentation.md#verbose-operations) defines streams, progress and resource styling.

## Implemented file selection flags

The implemented `files add`, `link`, `stash`, `edit`, `remove`/`rm` and `show` routes
accept `--pick` and automatically select missing operands in a terminal. The
[interactive file picker contract](files.md#interactive-file-pickers) defines
candidate filtering, multi-selection, previews, `--pick --dry-run`, flag conflicts
and fallbacks. `files browse` shares this selector. Existing explicit-operand and
machine-output routes retain their contracts; recovery still requires IDs.

## Native PowerShell command surface

`bin/dots.ps1` dispatches the first-party file, Git, environment, theme and Anodize families through native Python controllers. `theme.ps1` and `anodize.ps1` are standalone aliases. `dots completion powershell` emits the native completer; static built-in headers are shared under `lib/dots/metadata/`. First-party flags retain their CLI spellings, including `-v`/`--verbose`, `--pick`, `--json` and presentation switches. `dots theme init --shell powershell` emits native palette initialization. See [native PowerShell](powershell.md) for dependencies, platform exceptions and pending acceptance.

Live-framework native extensions may be `.ps1` or `.exe`; `.exe` metadata is read from a sibling `.meta`. Help and completion never execute extension code. Duplicate routes remain errors and direct dispatch resolves the longest prefix. Native Windows refuses extensionless POSIX scripts with an explicit diagnostic. Every future first-party route/flag change must update both native and Bash dispatch/completion tests.

Anodize defaults new saves/imports to the user theme directory. `--builtin` saves
into repository themes; `promote ID` moves there, or `--copy --name NEW_ID` copies
under a distinct ID. Missing terminal inputs and explicit `--interactive` use
FZF-first selectors with separate operation approval. See the
[interactive contract](anodize.md#interactive-authoring-and-previews).

## Androidots location helper

`androidots/bin/termux-geo` is a standalone Android/Termux command, not a new `dots` dispatcher route. It provides device or supplied-coordinate reverse lookup, versioned JSON, scalar/template queries, cache-only reads, and static Bash/Zsh/Fish completion generation and explicit local installation. Its authoritative [command and completion reference](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-geo.md) owns flags, fields, exit statuses, destinations, and service restrictions. Coordinate-only queries bypass geocoding; help/completion never acquire location.

Timeout diagnostics identify device acquisition, address lookup, stdin reading, or cache locking. Overall deadlines and HTTP connection/request timeouts return status 124 with empty stdout in machine modes.

Usage/help colors headings, command syntax, options and examples through the shared Dots presentation tokens. Existing color controls apply; redirected help is plain by default and generated completions remain undecorated.

## Standalone wttr

**Implemented:** `bin/wttr` (Bash) and `bin/wttr.ps1` (native PowerShell) are standalone weather commands, not dispatcher extensions. They share static option metadata in `lib/dots/wttr/metadata.py`, a Python 3.11+ controller, colored help/progress, j1 JSON, scalar fields, widget templates, daylight/cache modes and transactional Bash/Zsh/Fish/PowerShell completion installation. See [the authoritative command/flag reference](wttr.md#commands-and-output) and `wttr -h`; the shared option metadata supplies case-sensitive short aliases to parsing, help and all four completions. Main/completion help has the authored blue-to-cyan theme-gradient banner and an icon-controlled title; completion never queries providers. Stock option groups, `format=VALUE`, moon and canonical single-slash service-page requests use bounded native curl and preserve upstream output. Stock descriptions drive Zsh/FZF-tab menus and other supported completion tooltips. Custom views and widgets support theme-based named temperature/icon colors, literal hex or ANSI 256-color overrides, combinable text attributes and attribution visibility. Temperature scales accept N cutoffs and N+1 styles. Widget/`--format` templates support accumulating style directives, dynamic icon/current-temperature/feels-like styles and reset; templates without directives retain automatic field styling. Human weather labels are aligned with configurable `label_gap` (three spaces by default); `Now` shows icon and temperature with a separate `Condition` row. Wind arrows point downwind, and location/wind/sunrise/sunset/humidity/precipitation icons are shared fields used in human views and templates. Named `[icons]`/`[icon_colors]` entries customize glyphs/styles, and matching widget color directives preserve manual styling. The location icon appears beside the city heading; humidity/wind/precipitation/sunrise/sunset icons follow their values with one separating space. Sunrise/sunset display fields omit leading hour zeros in human rows, widgets and scalar queries without changing raw JSON or daylight calculations; JSON/scalar/daylight output remains free of styling. Explicit location overrides configured `default_location`, then automatic termux-geo city. Android acquisition is Termux-only; manual/default weather works through the shared controller on other platforms.
