# Command Model

**Status: Implemented Bash and native PowerShell command families**

Static built-in metadata and external command headers define the live routes. Bash and native PowerShell adapters expose file, Git, environment, theme and Anodize commands through shared controllers. This document describes their implemented interfaces.

Contributors select the [command family's maintenance skill](../.codex/README.md#command-family-owners) and follow the [command guide](../agents/guides/commands.md), including recorded configuration and menu assessments for every command change. Skill ownership does not replace the route metadata or interfaces documented here.

For a new family or subcommand, [command authoring](../.codex/skills/dots-command-authoring/SKILL.md) coordinates the implementation workflow and provides a reusable plan template. It carries current presentation preferences through the shared renderers and requires useful configuration and popup integrations to reach their consumers.

The shared Bash/Zsh helper `mkcd <directory>` is separate from the `dots` command family. Its [usage and path handling](shared-shells.md#zsh-configuration-and-directory-helpers) are implemented by `scripts/mkcd`, sourced through the shared function to change the current shell's directory.

## Find a command or workflow

Start with `dots` for grouped root help, `dots help files` for a family, and `dots commands` for the full live command inventory. `dots commands --check` validates metadata and route collisions without executing extensions. The [generated command reference](https://github.com/5nik7/dots/wiki/Command-reference) and `man dots` document public first-party routes from static metadata.

Use `dots menu` for guided selection. Escape returns, Ctrl-C exits, and F1 opens help. Interactive root choices sort alphabetically; nonempty searches use relevance, while curated submenus and printed/JSON listings keep their intended order. Reports open in the shared scrollable reader. Choose a starting workflow in the [core guide](core.md), or search current documentation with `dots wiki search 'files rollback' --topics`.

Use `--color=never`, `--icons=never` and `DOTS_PROGRESS=never` independently when desired. JSON, raw/scalar output and completion remain data interfaces. Prefix global options precede the command; route options follow it. Help and completion read metadata without running extension commands.

## Personal font commands

`dots fonts` and `fonts` expose the same controller and flags through Bash and
native PowerShell. The [fonts guide](fonts.md) defines library lifecycle, exact
version selection, application targets, compatibility wrappers and glyph actions.
`fonts installed` browses installed fonts; `--json` and `--print` list them without interaction. `copy INSTALLED_ID... --directory NAME` and `migrate INSTALLED_ID... --directory NAME` transfer selections. `install FONT... --from SOURCE [--directory DESTINATION]` supports batches. Plain interactive `fonts` opens the action menu; `set` without operands opens its app-first selector. `browse --downloaded` selects retained fonts across stores. `defaults` reports active-profile preferences and `restore [TARGET...]` reapplies exact saved choices after review.

Static route metadata comes from `fonts/commands.py`; run
`python3 -B tools/generate_fonts_commands.py --check` to check generated adapters.

Fonts human reports/help/reviews and nested menus honor shared output preferences.
Configuration is available from the main Fonts menu and Alt-O in catalog/glyph
pickers. `apps.fonts` controls list detail, provenance, menu descriptions and
preview visibility/sample/position/size/wrapping; see [font output preferences](fonts.md#output-preferences).
No font command flags or machine-output schemas change for these preferences.

`fonts directories` lists backend font destinations. `--directory NAME_OR_PATH` selects `DOTFONTS`, a profile `*FONTS` name/alias, or its absolute path. Directory install/download/import stores versions; `update FONT [--version VERSION]` and `upgrade [FONT]` store updates without activation. Bare `update` continues catalog refresh. `use FONT` explicitly activates a stored directory version, while `set --target APP` includes its requested apps. Directory uninstall/remove requires `--version` and retains history. See the [directory workflow](fonts.md#store-versions-in-a-dots-directory) for flags, output and recovery.

Contextual completion reads directory names, saved family IDs, versions and faces without fetching
metadata or running extensions. The launcher adds a Fonts submenu for the font
browser with a directory chooser, glyph browser, current selections, directory report and available app targets; mutations
retain their normal review. JSON, raw icon formats and exact paths remain data.

## Implemented shell initialization

The sourceable [shell utility functions](shell-utils.md) have their own documented argument, stream and status contracts; they do not add dispatcher routes or completion metadata.

`dots init [bash|zsh|fish|powershell|nu|xonsh]` emits native initialization code. With no argument, the generated code selects Bash or Zsh in the calling shell. `init` is reserved and bypasses extension discovery. Help and shell-name completion use built-in metadata. Native `bin/dots.ps1` supports shell-code initialization plus bounded setup, file inspection and installation recovery. Evaluating a hook loads only Dots integration from `lib/dots/shell/`; personal shell configuration stays separate. Settings use profile.json, with explicit environment overrides and legacy config.env compatibility. Repository rc files resolve symlinks and source their adjacent loaders directly. See [shell initialization](shell-init.md) for the full interface, bootstrap, error statuses and native invocation examples.

`dots init --setup [OPTIONS]` explicitly delegates to `dots files install`; `dots files uninstall` restores installer-owned targets. Install/uninstall accept `--dry-run`, `--yes`, `--json` and shared color/icon controls; install also accepts `--update` and repeatable `--with-source termux|windows|nvim`. Root shell/PowerShell scripts use the same controller. Setup options are invalid on shell-code generation paths. See [checkout installation](installation.md) for ownership, updater stages, JSON results and recovery.

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

`dots files repair [RESOURCE...] [--repo ID] [--app APP] [--category CATEGORY]` scans catalog destinations on the current platform. It queues missing links and verified broken managed links. Bare terminal use opens a helper for unresolved issues, allowing explicit relink or backed-up replacement of ordinary destinations, queue review and one final Cancel/Apply confirmation. `--yes` applies automatic repairs only; `--dry-run`, `--json` and `--verbose`/`-v` are supported. JSON requires `--yes` or `--dry-run`; data/preview/nonterminal modes never open the helper. Generated-theme connections and conflicting ownership remain protected. Bash and native PowerShell use the same controller, static help and contextual completion. See [repair](files.md#repair-managed-destinations) for ownership, recovery and exit statuses.

`dots files stash [RESOURCE...] [--restore]` disables resources and unlinks only
matching destinations; restore enables and relinks. `dots files edit [RESOURCE |
--new]` edits source/target mappings, metadata-only unless `--apply` is selected.
Both offer selection/review, `--yes`, `--dry-run`, `--json`, `--backup` and
`--no-backup`, static help/completion and native PowerShell routing. Edit supports
new-record metadata, strategies, base-profile selection and registry platform eligibility.
`--id NEW` also renames an existing qualified resource across all profiles and
retains recovery history; it can be combined with selected-profile mapping edits
and explicit live apply. See [ID renames](files.md#file-id-renames) and
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
`version`, `status`, `spec`, `plan`, `apply`, `undo`, `history`, `backup`,
`bootstrap`, and `self`, plus the private `__complete` endpoint. Reserved but
unimplemented routes remain unavailable. Reservations do not add features.

### Public Interface

Root help preserves the existing built-in usage synopses, logo, usage and global options. It ends with a pointer to `dots help COMMAND` and the complete `dots commands` inventory. A deeper-only extension such as `dots-example-sync` contributes one `example` row with the summary “Command group”; a visible top-level command supplies its own summary. Hidden-only groups are omitted, and hidden parent metadata is not displayed. This is a help-rendering projection only: catalogs, contextual family/leaf help, validation, generated references and completion retain their full route information. Bash, the shared native controller and Python-free PowerShell help use the same grouping rule while retaining their existing layouts. Menu review: unchanged, because static help adds no selectable action.

- `dots`, `dots help`, `dots -h`, `dots --help`: global help with one row per visible top-level command or group.
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

`dots menu tmux keys` and the direct `dots-menu-tmux-keys` executable delegate to `dots keys tmux`. They retain `--print` and add the shared picker/data/filter options. The running tmux server supplies tables, descriptions and prefix settings without starting a server. The FZF popup replaces the old less pager. See [keybindings](keys.md#tmux-compatibility).

### Dots workflow menu

`dots menu [--print|--json|--browse] [--query TEXT] [--client CLIENT]` opens the curated launcher. Bash and native PowerShell share its controller, static help, flags and completion. Interactive default invocation requires terminal input/output and a usable `TERM`; `--browse` also supports a validated background tmux context. Printed, JSON and redirected default views only list choices. Their query matches all whitespace-separated terms, case-insensitively; interactive queries seed FZF. Missing FZF or popup support produces a filtered listing and a stderr explanation without dispatching an action.

The fixed registry in `lib/dots/menu_cli.py` owns labels, icons, command arrays, terminal behavior, submenu order and data-listing order. The interactive root view sorts its choices by label. Descriptions come from the selected first-party static headers. The launcher checks command-file/tool presence and platform limits without running extensions, collecting session/file/theme/Git inventories or reading pane contents. Unavailable entries remain visible with a reason; selection rechecks availability and refuses unavailable actions. There is no automatic extension enrollment or user-defined menu schema.

Interactive rows show just an icon and lowercase name. The root menu uses a stable case-insensitive A–Z label order, ignoring icons; for example, `weather` sorts under W while retaining its `wttr` identity. Unavailable choices retain their alphabetical position. A nonempty query uses FZF relevance ranking; clearing it restores A–Z order. Family submenus keep their curated order. The plain fallback from interactive browsing uses the alphabetical root choices, while `--print`, `--json` and redirected default output keep registry order and content. The table below describes action mappings. Launcher prompts use `dots: ` at the root and middle-dot breadcrumbs such as `dots·files: ` and `dots·theme·plugins: `, with one space after the colon. This applies only to launcher menus; delegated pickers keep their prompts. Printed headings and JSON titles are unchanged. Descriptions remain in printed/JSON views and static help. Family submenus show common workflows; each also ends with `help`. These are internal navigation choices, with no extra public routes or flags.

| Root ID and label | Selection and submenu actions |
| --- | --- |
| `fonts` | Installed and downloaded fonts, Set, catalogs, saved defaults, glyph search, current selections, directory report, available app targets and output configuration; mutation actions retain review and confirmation. |
| `keys` | `dots keys --browse` opens the existing category/binding browser. |
| `tmux` | `sessions` opens the existing session picker; `keys` opens `dots menu tmux keys --browse`; help uses `dots help menu tmux`. |
| `files` | `browse`, `list`, `history`, `sources` use the corresponding `dots files` workflows. |
| `git` | `status`, `info`, `submodules`, `wiki`, `publish`, `sync`; see the nested choices and approval rules below. |
| `theme` | `show`, `list`, `switcher`, `files` (`dots theme files browse`), `backgrounds` (`dots theme bg switcher`), `plugins`; plugins contains `list`, `doctor`, `help`. |
| `anodize` | `create`, `edit`, `preview`, `apply` use `--interactive`; `list` shows authored palettes. |
| `debug` | `check`, `startup`, `path`, `cache`; no live tracing is enabled. |
| `profile` | `show`, `list`, `paths`, `layers`, `files`, `commands`, `env`, `check`, `check all` (`profile check --all`). |
| `wiki` | `browse`, `list`, `check`. |
| `env` | Opens the existing environment report. |

The Git submodules menu contains `list` (runs `dots git submodules`), `info`, `status` and `help`. Git wiki contains `status`, `info`, `publish`, `sync` and `help`. Reports use the reader. The Git and Git wiki publish choices run `dots git publish --all` and `dots git wiki publish --all`, respectively, retaining the existing terminal review and confirmation. They include ordinary unstaged and untracked files under the existing ignore and gitlink rules; direct CLI publication remains staged-only by default. Each sync first runs its existing `--dry-run` command in the reader. Only a successful preview dismissed normally (q in less or Enter in FZF) opens a Cancel/Sync confirmation with Cancel selected; only explicit Sync runs the normal command. Closing the preview popup, Escape/Ctrl-C in FZF, failed previews or canceled confirmation never sync. Sync adds no `--all`, `--init`, `--remote` or `--yes`; publish adds only `--all`. Repository selection and direct CLI semantics are unchanged.

Enter opens a choice. Escape goes back one menu level; Escape at the root closes with 130. Ctrl-C at any menu closes the launcher with 130. F1 opens contextual help (general help at the root). Returning preserves that menu's search query; a newly opened submenu starts empty. Completed or canceled workflows return to their launching menu. Completed session selection, including selecting the current session, closes the launcher successfully; cancellation, empty inventories and failures return to the tmux submenu.

The chooser closes before the selected workflow starts. Actions preserve the caller's working directory and pass literal arguments. Normal terminal invocation inherits the terminal; background tmux invocation targets the exact originating client. `--client CLIENT` disambiguates clients sharing the originating session; it requires inherited server/pane context when browsing and is ignored by data views. File/theme/Anodize workflows retain their existing review, confirmation and transaction paths.

Help, reports and other output actions execute once, then open a scrollable reader containing their complete stdout and stderr. Less supports arrows, Page Up/Down, mouse scrolling, `/` search and `q` to return, including for short output. A read-only FZF line browser provides scrolling and search when less is missing or fails; Enter/Escape returns from that fallback. The reader renders Nerd Font private-use glyphs directly while continuing to escape control characters. Less prompts and standout text follow the [global less color policy](shell-environment.md#global-less-colors), including background tmux launches. Failures show their exit status. Reader dismissal does not replace the command's result. In tmux, output commands run once in a compact cancellable loading window, then open a fitted reader after capture finishes. Readers retain 90% client width; height counts displayed rows, wrapping, title/status, controls and borders, with a six-row minimum and 90% height cap (clamped on tiny clients). Long content remains fully scrollable. Already prepared messages open directly. Private captures are removed after use. Interactive `wiki browse` closes its selection host before opening the fitted document reader; direct `wiki show`, raw/JSON and redirected data output retain their contracts.

The repository tmux configuration binds Prefix m to `dots menu --browse` and Prefix s to the session picker. Each `run-shell -b` binding passes explicit server, pane, client and cwd context, quotes shell-bound format values and maps only status 130 to success. Other statuses and diagnostics remain visible. These replace stock mark-pane and session-tree bindings; Prefix ? is unchanged. Configuration activation requires loading the configuration in the running server; source edits alone do not activate it.

Listings and successful session navigation return 0; invalid invocations and unrecoverable context/selector errors return 2. Launcher cancellation returns 130. Workflow failures display their status before returning to the menu; they do not become a successful workflow or close the launcher. Native Windows uses ordinary terminal FZF and keeps the unavailable tmux entry visible; it never invokes WSL. The JSON envelope is the shared [schema-1 menu record](specification.md#shared-menu-records), with no command arrays or private transport fields.

### Tmux session menu

With the optional attention bridge running, interactive rows/previews show unread Codex counts and window/pane locations. **F1 → Codex alerts** opens a bounded overview across registered servers. Select a pane, then choose Open this pane (same server), Acknowledge this alert, or New Termux tab (Termux only, also for other servers). Actions recheck socket/session/pane identity; opening the overview does not acknowledge anything. **Prefix a** acknowledges only the invoking Codex pane. Existing `--json`, `--print`, completion and redirected output contracts are unchanged.

`dots menu tmux sessions [--print|--json|--browse] [--query TEXT] [--client CLIENT]`
browses projects and manages sessions. The direct executable is
`dots-menu-tmux-sessions`; Bash and native PowerShell metadata/help/completion
share this route. Native Windows returns status 2 without invoking tmux or WSL.

With terminal input/output and a usable `TERM`, the default opens FZF. `--browse`
also accepts an explicit background tmux context. The prompt is
`dots·tmux·sessions:` with a project breadcrumb in its submenu. Rows use the same
semantic palette and aligned names as the key browser. Projects use ``,
with icons matching the adjacent name color. Non-current project names with sessions
use bold theme accent in both the list and preview; non-project session names
use bold theme blue. Current names retain their magenta emphasis.
Empty-project names use `light_foreground`, normal-weight in the list and bold
in the preview. The preview header reads `battery · [1 session]`, with a muted
dot. Totals use theme orange for positive counts in both current and non-current projects
(including menu `[N]`/expanded counts),
and red for preview `[0 sessions]`; menu `no session` stays muted. Window counts
are green and client counts read `N attached`, yellow when positive and muted
when zero. Counts use normal weight; the full `·  current` / `· current` marker
uses bold theme `bright_green`. The path line uses `Project: 󰉋 ~/path`, with the icon matching its
directory style and following icon preferences. Current state remains readable
without color or icons. The colored inert preview
sits below the list, normally five rows including borders, capped at eight and
bounded by the terminal. Its stable height fits the largest preview line count in
the current view. Each session occupies one row; long lines, including project
paths, clip at the right edge instead of wrapping. Alt-P toggles it and Alt-J/K
scroll it vertically. Paths use `~` for home;
counts use singular/plural wording and a matching single-session name is not
repeated. Search and selection survive returning from actions.

The header shows only `Alt-H: keys`. Alt-H opens a separate fitted, read-only
shortcut popup, including when no rows match. Escape or Alt-H restores the
search, selected row and any pending project action; Ctrl-C exits the browser.
Enter in the reference executes nothing. F1 remains the contextual action menu.

The browser discovers Git checkouts immediately under `~/repos`, includes Dots, and reads optional [additional project paths](specification.md#session-browser-projects). Active projects come first, inactive projects next, then generic sessions. Managed workspaces use their live all-pane project snapshot; a single root may be outside those discovery directories, while zero/multiple roots remain generic. Legacy unadopted startup sessions stay generic. Other sessions retain explicit-tag/start-directory/pane-directory association. Every session appears once and duplicate project basenames include disambiguating paths. The preview retains full unique session names internally; the visible text clips to its width.

| Key | Action |
| --- | --- |
| Enter | Switch/open a session. A project with several sessions opens its session submenu; an inactive project creates a fresh workspace at its root. |
| Alt-N | Create and enter a new session in the project, selected generic session's directory, or invoking directory when no row matches. |
| Alt-R | Rename the selected session. |
| Alt-D | Show Cancel/Delete with the name, windows and attached clients. Delete terminates that session and its processes. |
| Alt-T | Termux only: open a new Termux terminal tab attached to the selection, creating a session for an inactive project first. |
| F1 | Open the contextual action menu, including Switch/Open. |
| Alt-H | Show the shortcut reference; Escape or Alt-H returns. |
| Escape / Ctrl-C | Back / exit. |

Session-specific actions on a multi-session project first select a session.
New sessions use a fresh immutable ID: `projectname-ID` in a project or
`termux-ID` outside projects, without a name prompt. Prefix C uses the same
creation rule in the invoking pane directory and switches only that client.
Automatic names follow all live pane projects; manual rename opts out.
Rename starts with the existing name. Optional Gum provides editable input, with
plain terminal input otherwise. Empty/blank names, periods, colons, control
characters and existing names are refused. Rename, canceled actions and deleting
another session refresh the browser. Switching, creation/opening, new Termux and
deleting the invoking session close the launcher. Last-session deletion follows
tmux's normal detach/exit behavior; it can close a Termux tab using automatic
startup. Deletion does not remove project directories or registration.

Inspection never starts a server; explicit creation may start the default one.
Existing-server actions retain the pinned socket/server PID, session ID/creation
time and exact invoking client identity. Stale or ambiguous identities fail
without substituting another target. Selecting the current session is a no-op.
`--client CLIENT` disambiguates clients on the originating session and requires
inherited `TMUX`/`TMUX_PANE`. Outside tmux, attachment uses the caller's terminal
without detaching other clients. New Termux first probes `termux-am --am-help`,
then the Termux-installed legacy `am --help` if needed (never system `am`). These
bounded read-only probes run only for that action, before creating an inactive
project session. One launch request invokes the fixed attach helper without shell
startup; it is never retried after failure or timeout. Diagnostics identify the
adapter and status with bounded, sanitized detail. Unavailable transport or Android launch failure
reports an error, leaves any created session available and never changes app
permissions/settings. A successful launch request is not proof of attachment.

`--print`, `--json` and redirected defaults remain read-only **live-session**
listings: no project discovery, actions, FZF probes or client capture. Their
query matches all whitespace-separated terms case-insensitively; interactive
queries use FZF syntax. The [schema-1 JSON](specification.md#shared-menu-records)
remains unchanged. Missing FZF/popup support prints interactive choices and an
explanation without executing an action. Empty interactive inventories still
support Alt-N/F1/Alt-H; empty data listings succeed. Errors return 2; Escape at the
root and Ctrl-C return 130. Attachment preserves tmux's exit status. Prefix s
normalizes cancellation quietly. Existing key routes and Prefix ? are unchanged.

### Keybinding browser

`dots keys [APP]` supports `--query TEXT`, `--mode MODE`, `--source live|configured|all`, `--no-defaults` and mutually exclusive `--print|--json|--browse`. Interactive `dots keys` opens the category menu; `dots keys all` and `dots keys APP` open bindings directly. Interactive `dots keys apps` offers an app chooser with counts for nonempty apps; `--print`, redirected output and `--json` preserve the provider coverage report. Menus fit their contents; tmux binding browsers use a 99% popup and 45% preview. Bash/Zsh and native PowerShell share the controller and static metadata; on-demand native shell adapters supply caller keymaps. `:DotsKeys` is the separate Neovim bridge. Defaults and coverage are described in [the keybinding reference](keys.md). Success and empty results return 0; invalid invocations or failed inspection/picker operations return 2, and cancellation returns 130. Missing providers are recorded as coverage notes.

Key pickers put match counts inline on the right. The main menu shows All and
nonempty apps as `app · [47]`, using muted counts from one captured snapshot;
selecting an app reuses that snapshot. Apps is retained as an explicit route,
with no redundant main-menu entry. Main/All prompts are `󰌆 :`; specific apps use
`󰌆 APP:`. A selected mode uses `󰌆 APP·MODE:` (or `󰌆 all·MODE:` across apps).
App-specific lists omit the app column; a selected mode hides the mode column.
Visible app/mode/key columns align within 12/18/16-cell caps and shorten with `…`.
Modes use orange in lists and previews. The preview starts at the left edge with
Keys, Action, Mode and no heading. Alt-M opens a compact mode chooser; selecting
or cancelling returns to the binding list with its search preserved. Ctrl-C
cancels browsing. Provider and mode banners are omitted from picker headers.
`--mode MODE` selects the initial interactive mode; print/JSON keep exact mode
filtering. See [picker controls](keys.md#browsing-and-notation).

The keybinding app choices include `codex`. `dots keys yazi` includes the complete pinned shipped defaults; `dots keys codex` includes CLI defaults and user `tui.keymap` overrides. Both work offline and honor the same filters and output options. `--no-defaults` excludes bundled as well as installed reference rows. See [provider coverage](keys.md#live-versus-configured-evidence).

The tmux shortcut requests live Zsh maps from its originating pane before opening
the counted main menu; direct Zsh, All and Apps routes also request them.
This requires an integrated Zsh prompt; unavailable capture
uses configured rows with explanatory print/JSON coverage notes. Existing caller snapshots
take precedence, and `--source configured` bypasses the request. No new public
flag or JSON version is introduced. See [live Zsh capture](keys.md#live-zsh-bindings-from-the-tmux-shortcut).

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

Global help renders the optional `$DOTS/logo.txt` using `apps.cli.logo_gradient`: `classic` (default) retains the vertical blue-to-cyan gradient; `installer` uses the horizontal theme hint/info/accent gradient shared with setup. `dots config set apps.cli.logo_gradient installer` applies on the next invocation without a theme refresh. Bash and native PowerShell use the shared core renderer when Python is available and retain a builtin classic fallback for basic help without Python. Artwork and plain redirected output are preserved; JSON, scalar and completion output bypass branding. Configuration review: **add** the finite gradient choice through normal profile inheritance and Config editors/completion. Menu review: **unchanged**; existing Config editing exposes both values, and root help adds no action. Command maintenance owns the root renderer; Config owns the preference.

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
in [Shared themes](themes.md#unified-commands-and-family-shortcuts). Static headers on the official
`dots-theme-*` entry points drive dispatcher help and completion. The closed
palette providers augment that metadata with current theme files; they do not
introduce extension callbacks. `theme set` delegates
state publication to the shared helper described in [decision 0007](decisions/0007-data-driven-themes.md).
The supported families include hyphenated `rose-pine` identifiers and native palette
keys such as `sumiInk3`. All three shell providers discover full IDs, families and contextual colors;
pywal16 flavor discovery works without its optional generated input. Palette filtering and native query flags are documented in the shared theme reference.

Television theme publication uses the existing theme routes and their output contracts. See [Television integration](themes.md#television) for the `dots` theme selector, destination overrides, and journaled creation of its themes child directory.

## Implemented Anodize commands

Anodize-specific `--logo=text|auto|kitty|chafa` and `--logo-layout=auto|base|horizontal|stacked|icon` work before or after its subcommand, including static Dots help. Environment defaults are `ANODIZE_LOGO` and `ANODIZE_LOGO_LAYOUT`. Default human branding is exactly LOGO1, or LOGO2 for wide help, including pipes and disabled icons. `base` selects LOGO1 exactly; graphics and larger layouts require an explicit choice. Colored text logos use bottom-left hint through midpoint info to top-right accent, with separate gradients for symbol and wordmark and candidate colors in previews. Palette results use the selected background and text colors for the logo, header, details and body. Data interfaces remain undecorated. Interactive and FZF-tab previews default to LOGO1 and scroll vertically in short panes. The Anodize menu includes Extract after Create; interactive Preview/Extract retain their results in the shared reader and return to the parent search without saving or applying a theme. See the authoritative [logo contract](anodize.md#terminal-logo).

`dots anodize` and standalone `anodize` expose the same authoring commands. The complete [command and flag contract](anodize.md#commands-and-flags) covers modes, extract, create, import, list, show, edit, preview, export, apply, promote and completion. `anodize completion bash|zsh|fish` (also `dots anodize completion`) emits standalone shell integration as plain source. Static choices cover extraction modes, adjustment/color keys, formats and apps; the `anodize-theme` metadata type supplies authored theme IDs from both user and repository roots for edit; `anodize-user-theme` limits promotion suggestions to user-authored themes. See the [completion and manual guide](anodize.md#shell-completion-and-manual). Static wrapper metadata supplies Dots help/discovery/completion without running the engine. Standalone `anodize --help` and `anodize COMMAND --help` use width-aware Dots presentation with command examples and option descriptions; argparse coloring is disabled so only the shared renderer emits ANSI. Mutations preview by default without interactive confirmation or `--yes`; raw exports/app previews remain undecorated. The private engine is built explicitly with `python3 -B tools/verify_anodize.py build`.

## Shared interactive shell commands

Bash and Zsh share the [interactive helper contract](shared-shells.md#commands-and-compatibility). `ff` opens FZF in both shells; `findfiles` preserves Bash's former filename search. `rl`, `rlc` and `rlcs` select native reload/completion implementations. These are shell helpers, not new `dots` command routes.

### Termux default-session launcher

**Implemented.** `profiles/termux/bin/termux-bar [--auto]` creates or reattaches the current Termux tab’s managed workspace on the ordinary tmux server, finding its stored origin even after renaming. It is a standalone Termux executable, not a new `dots` route. `--auto` is the guarded Bash/Zsh startup mode; `-h`/`--help` prints plain help without session discovery or tmux. There are no positional arguments. Exit status is 0 for an automatic skip, 1 for launcher failures, 2 for invalid arguments and 130 for interrupted setup; after attachment, 0 means detach or successful manual completion and 1 means attachment failure. Automatic normal session exit returns internal status 20 to the Dots startup hook, which exits the outer shell. This status is not used for skipped startup. Diagnostics go to stderr, and successful attachment hands the terminal to tmux. See [startup and opt-out behavior](shell-init.md#termux-tmux-startup).

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
remains scalar. `dots theme` also provides `list`, `switcher`, `install`, `update`, `remove`,
and `plugins`. Plural first-party routes have been removed. See
[decision 0016](decisions/0016-core-command-families-and-file-identities.md).
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

Generated theme shortcuts use `name-theme` when an existing executable owns `name`; for example, `ristretto-theme` forwards to `dots theme ristretto`. If both names are occupied, no shortcut is generated and explicit theme routes remain available. `dots theme refresh --commands-only` reconciles names and completion without selecting a theme. See [shortcut allocation](themes.md#unified-commands-and-family-shortcuts). This adds no static Dots route, flag or menu action.

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

Theme set/refresh (including `--commands-only`) and switcher accept the same flag; standalone `theme switcher` is equivalent. These flags do not apply to scalar/query routes or ordinary shell initialization. Existing discovery verbosity retains its listing semantics. Default output and structured schemas are unchanged; JSON suppresses additional details. [Presentation](presentation.md#verbose-operations) defines streams, progress and resource styling.

## Existing-source registration

`dots files add PATH...` registers existing file/directory links into eligible repositories and sources already in those repositories, alongside ordinary configuration imports. `--target DESTINATION` resolves one explicit source without a known destination; repository directories use directory-link automatically. `files discover`, the Add picker and `add --scan` include registration candidates. Scans skip unresolved candidates and report their reasons. Correct pre-existing links stay intact and unowned by uninstall; new links receive normal installation recovery. See [registration](files.md#register-files-already-in-the-repository) for inference, profile ownership, output and safety contracts. The Files launcher includes Add. Both shell frontends share these options and their completion metadata.

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

## wttr weather

**Implemented:** `bin/wttr` (Bash) and `bin/wttr.ps1` (native PowerShell) and `dots wttr` expose the same weather controller; `get`, `completion` and `browse` are discoverable Dots routes. They share static option metadata in `lib/dots/wttr/metadata.py`, a Python 3.11+ controller, colored help/progress, j1 JSON, scalar fields, widget templates, daylight/cache modes and transactional Bash/Zsh/Fish/PowerShell completion installation. See [the authoritative command/flag reference](wttr.md#commands-and-output) and `wttr -h`; the shared option metadata supplies case-sensitive short aliases to parsing, help and all four completions. Main/completion help has the authored blue-to-cyan theme-gradient banner and an icon-controlled title; completion never queries providers. Stock option groups, `format=VALUE`, moon and canonical single-slash service-page requests use bounded native curl and preserve upstream output. Stock descriptions drive Zsh/FZF-tab menus and other supported completion tooltips. Custom views and widgets support theme-based named temperature/icon colors, literal hex or ANSI 256-color overrides, combinable text attributes and attribution visibility. Temperature scales accept N cutoffs and N+1 styles. Widget/`--format` templates support accumulating style directives, dynamic icon/current-temperature/feels-like styles and reset; templates without directives retain automatic field styling. Human weather labels are aligned with configurable `label_gap` (three spaces by default); `Now` shows icon and temperature with a separate `Condition` row. Wind arrows point downwind, and location/wind/sunrise/sunset/humidity/precipitation icons are shared fields used in human views and templates. Named `[icons]`/`[icon_colors]` entries customize glyphs/styles, and matching widget color directives preserve manual styling. The location icon appears beside the city heading; humidity/wind/precipitation/sunrise/sunset icons follow their values with one separating space. Sunrise/sunset display fields omit leading hour zeros in human rows, widgets and scalar queries without changing raw JSON or daylight calculations; JSON/scalar/daylight output remains free of styling. Explicit location overrides configured `default_location`, then automatic termux-geo city. Android acquisition is Termux-only; manual/default weather works through the shared controller on other platforms.

`wttr browse [LOCATION] [options]` and `dots wttr browse` open a cached-preview action menu with current/daily/hourly reports, session location/units and Refresh. The Weather entry in `dots menu` opens this browser. Report selection refreshes as needed; previews remain read-only. Failed refreshes may display clearly aged stale data within configured `max_stale`. Missing FZF/terminal support prints the ordinary report with a stderr explanation. Browser options, cancellation, context and fallback contracts are defined in [the weather browser reference](wttr.md#weather-browser).

### Generated theme file inspection

`dots theme files` defaults to `list [--app APP] [--json]`. Its read-only actions are `info FILE [--json]`, `show FILE [--source] [--raw]`, `path [FILE] [--source|--resolved]`, `check [--app APP] [--consumers] [--json]`, and `browse [--app APP]`. Standalone `theme files` and native PowerShell use the same controller. Artifact/app completion is data-only across Bash, Zsh, Fish and PowerShell. See [generated theme files](themes.md#generated-theme-files) for sources, destinations, status meanings and content limits, and [schema 1](specification.md#generated-theme-file-inspection) for machine contracts. The family command name `files` is reserved to keep this route unambiguous.


Theme-file `show` now supports directory entries and optional terminal syntax highlighting through the captured Dots bat cache. `check --consumers` opts into failures for confirmed read-only consumer differences; ordinary `check` retains file/link health behavior. Runtime activation is distinct from configuration evidence. Raw regular-file output is unchanged; see [previews and evidence](themes.md#directory-and-highlighted-previews).

## Platform profile and bootstrap commands

`dots profile [--json]` inspects current platform facts and resolved inheritance.
`dots profile list [--json]` lists available definitions and active layers. Both are
read-only. `dots env [NAME] [--json]` now includes application defaults, context,
PATH contributions and observed hook provenance in addition to settings/paths.
`dots init --bootstrap bash|zsh|powershell` emits a standalone startup snippet;
printing it does not clone or install anything. See [profiles](profiles.md).

## Profile and debug diagnostics

The implemented `profile show|layers|paths|env|files|commands|check [ID]` and
`profile list|check` routes provide read-only inspection. Their flags and
selection semantics are described in [profiles](profiles.md#profile-inspection-subcommands).
`debug check|startup|path|command|cache|test|record` uses the shared native controller,
static command headers and contextual completions; see [debug commands](debug.md).
Bare `debug` shows group help. No diagnostic silently activates or repairs state.

File selectors use `termux:NAME` and `windows:NAME`, with `--repo termux|windows` for source filters. Legacy `androidots`/`windots` CLI names are rejected with a replacement hint; historical receipts remain recoverable. See [platform file identities](specification.md#canonical-platform-file-identities).

### Detailed debug and PATH recording

Debug human reports use nested trees. `startup` adds `--view tree` (with `sequence` as a compatibility alias), `--detail files|changes|deep`, `--changes LIST`, repeated `--file`/`--name` filters, `--depth`, `--limit`, `--min-ms`, and explicit `--show-values NAME`. Display filters preserve the full JSON capture. `path` adds `--history`, `--entry PATH`, bounded display depth/rows, and explicit `--live|--isolated` startup reconstruction with shell/login/run/timeout options. `record start|stop --shell SHELL` emits native code for explicit evaluation; `record status [--json]` reads existing session evidence. See [debugging](debug.md) for coverage and sensitivity limits.

## Wiki commands

`dots wiki` shows navigation and checkout freshness. Its routes are `list`, `show`, `search`, `browse`, `open`, `edit`, `path`, `check`, `build` and `init`; exact options, data modes and examples are in [wiki maintenance](wiki.md). Page/section completion reads the static page manifest. `dots git wiki info|status|sync|publish` selects the separate wiki repository; top-level Git info/status/sync/publish accepts `--no-wiki`. No command runs extensions merely to generate the command reference. The complete `dots(1)` manual shares that same public static inventory, including global options and declared operands.

`dots wiki search QUERY --topics` ranks current source pages/sections offline; ordinary search retains literal exported-file matching and its JSON contract. `dots wiki browse [--query QUERY]` reads source pages, sections and whole documents without requiring an exported checkout. Topic JSON and ranking are documented in [wiki search](wiki.md#wiki-search-and-topic-browsing). Menu review: **update** Wiki's Browse/Search selectors and add Configuration through the existing Config browser. Configuration review: **add** [Wiki output preferences](wiki.md#output-preferences), reusing shared semantic status, resources, CLI/menu formatting and popup controls. `dots-wiki-maintenance` owns the behavior and both frontends share the same controller.

## Blastoff and pkgs

Go upgrades query latest module versions and run `go install PACKAGE@latest` only
for newer eligible tools. Current/newer installed versions are left alone; the
compact progress line names each tool before Go emits output and shows quiet time.
Dry-run performs the same bounded version checks without installation. Native
flags remain literal; explicit replacement recipes retain their own semantics.

Package aliases: `in` → `install`, `un` → `uninstall`, `up` → `upgrade`, `xup` →
`export --update`, `upls` → `upgrade --list`. Both `upgrade ls` and `upgrade --list`
report available updates without transactions; `--json` exposes per-manager query
status and version rows. `cleanup [FILE] [--dry-run | --json]` reviews the active
profile manifest by default; removal requires eligible current pip ownership,
FZF selection and separate confirmation. Its `--yes` bypass is intentionally
unavailable. These routes share standalone/Dots parsing and static completion;
native Windows retains package-operation refusal. Configuration review: **update**
existing native npm recipes for custom Codex installs, no new controls for these
routes. Menu review: **add** upgradable report and reviewed cleanup terminal action;
aliases reuse canonical actions. Owner: `dots-pkgs-maintenance`.

`dots blastoff [ARGUMENTS...]` and `dots pkgs [ARGUMENTS...]` expose every bundled application subcommand, with equivalent standalone `blastoff` and `pkgs` entry points. Both routes preserve argument boundaries, stdout/stderr and application exit codes; application help works at any supported position. `dots help blastoff` and `dots help pkgs` expose static Dots metadata without executing the applications. Metadata, the generated command reference and contextual Dots completion derive from the bundled grammars through `tools/generate_bundled_apps.py`.

Examples: `dots blastoff theme list`, `dots blastoff --dry-run theme apply local:dots`, `dots pkgs install --manager npm --global typescript --dry-run`. Application color flags follow the route; raw and JSON output are forwarded without decoration. See [application commands and platform boundaries](bundled-applications.md). Native Windows pkgs uses `--manager winget` with `--scope user|machine`; community-source exact IDs and version pins share the existing workflows. See [package workflows](packages.md) for installation without an extra `--yes` (named targets or accepted picker selections), unattended user-wide `upgrade` and repository `refresh`, Go support, native `apps.pkgs` configuration, `format [--manager]`, `export [--output FILE] [--update] [--include-dependencies] [--pin-versions]`, `manifest FILE [--json]` and `restore FILE [--dry-run] [--yes] [--json]`. Human upgrades show compact progress, one result per manager, short diagnostics and skip counts; dry-run retains full plans. Pip shows packages, native download bytes (25.1+) and build stages. Npm shows native metadata/fetch/script activity; both add elapsed silence after 15 seconds without output. Selected global npm upgrades use targeted installs without a blanket force flag; project upgrades retain native update semantics. `--raw` selects full command/skip details and byte forwarding; ordinary redirects retain their full output. `--ignore-skip` explicitly overrides direct-target exclusions. Metadata/completion cover these routes on both frontends. Menu review: **update** upgrade with review/Run, add export/update-manifest/inspect/restore/Config, use the current profile root for filenames, and return on Escape. Leave the stdin formatter CLI-only. `export --update` defaults to the active profile manifest and authorizes the guarded merge/write without an extra `--yes`, preserving edits and backups; `git publish --update-packages` includes an explicit manifest refresh without expanding staging for other files. Configuration review: **add** guarded native `apps.pkgs` controls, owned by `dots-pkgs-maintenance`.

Current/theme-list/save/backup-list/doctor views in Blastoff and help/operation-preview/list/managers/doctor views in pkgs share [Dots report formatting](presentation.md#application-reports) in terminals and popup readers. Use `dots --color=always blastoff current` or `blastoff current --color always` to force report colors; a route-local application flag takes precedence over the Dots prefix setting. `DOTS_ICONS` controls resource icons independently. Ordinary redirected text, JSON, raw TOML and completion output retain their existing formats.

## Application plugin migration and menus

`dots files migrate apps` (also `dots files migrate-apps`) previews supported legacy application installations. `--yes` applies through the installation receipt and Store; `--dry-run` always wins and `--json` uses schema 1. It installs only application assets, retains backups and leaves unrelated configuration/themes untouched. `dots menu blastoff` and `dots menu pkgs` open common workflow families with the existing menu modes, terminal handoff and native availability rules. See [plugins](plugins.md).

Codex attention setup is an explicit repository maintenance helper, documented under [tmux notifications](themes.md#codex-attention-notifications); it adds no public `dots` route or completion entry. Menu review: setup stays a direct maintenance operation because installing lifecycle hooks requires its preview and Codex's `/hooks` review. The existing session picker is updated for everyday attention navigation and acknowledgement; it does not install or trust hooks.

## Todo goals

`dots todo` always selects the active Dots checkout. Standalone `todo` automatically selects the nearest Git/configured project or global goals; only standalone invocation accepts scope overrides. The command family provides add/list/show/edit/note/start/done/reopen/remove/restore/next/brief/plan/browse/path. Bare terminal invocation browses, while redirected output lists active goals. The tmux goal browser keeps a one-cell outer margin and grows its bottom preview into the space left by current search matches. Crowded or empty results use the compact four-row preview, shrinking further on short terminals. Project mutations retain the project-name tag and backfill missing tags throughout only the selected project, including completed/removed records; reads never repair tags. Todo human views use a two-space base indent. Human lists put aliases (or short UUIDs) above titles, use compact Project/Goals fields and separate goals with a blank line. Titles, aliases and high priority use bold theme bright_magenta, accent and warning respectively; open status uses bold theme bright green throughout human views. See [todo](todo.md) for the authoritative workflow and options; static help/completion headers are generated from the shared todo command definitions.

`plan ID [--new] [--dry-run]` opens/resumes a named Codex planning thread for the goal's complete subtree; the normal command launches, while `--dry-run` only previews. `brief ID` exports an undecorated `/plan` interview, save and implementation prompt with an optional `$dots-todo-planning` reference and complete fallback instructions. Neither generating a brief nor launching planning changes goal status. After leaving Plan Mode, **Implement the plan** saves/reconciles linked subgoals and implements the work with progress tracking; **Save these goals** saves only. Popup-launched tmux windows use the Todo icon while Codex retains the descriptive thread name; see [Codex planning](todo.md#plan-a-goal-in-codex).

Menu review: **update** the cooperating Todo popup and its launcher handoff with Plan in Codex (Alt-C), Print brief (Alt-O), and Copy brief (Alt-Y), available on selected goals and in the brief reader. Print and launch close the containing menu; copy preserves browsing. Stable IDs, inert previews, explicit removal confirmation, query/focus restoration and exact-client handoff use the shared menu adapters. No new tmux binding is installed. Bash, Zsh/FZF-tab, Fish and native PowerShell complete commands, fields, tags, goal aliases and UUIDs in the invocation's scope; help and static completion perform no project discovery.

## Profile configuration commands

`dots config set KEY [VALUE]` opens the existing Config value picker/editor when VALUE is omitted in a usable terminal. It goes directly to the selected key, preserves profile/default scope and `--no-refresh`, and returns after reviewed Save or cancellation. Color options list active-theme colors with hex values, standard roles and custom input; nonstandard palette entries save literal hex values. Data/dry-run/JSON-value calls and noninteractive streams still require VALUE. Missing picker support produces an explicit-value diagnostic. No new route or completion provider is introduced; see [Config popup editing](profiles.md#configuration-popup).

`config get`, `set`, `unset` and `explain` complete keys at an empty argument and by prefix through a read-only provider, including native weather keys. Invalid optional weather TOML leaves unrelated core keys available. Shared CLI/popup row alignment uses `formatting.apps.{cli,menu}.label_width` (character cells, percentages, or `0` for spacing only), `label_gap` and `alignment`; see [examples and activation](profiles.md#shared-row-alignment). Width presets are available in value completion and Config editors. Human layout does not change scalar/JSON/completion records.

`dots config explain KEY` shows effective typed values, provenance, activation, allowed choices and applicable input syntax/examples. Its JSON adds `constraints` for application/formatting controls; scalar `get` stays exact. Config previews/details and enum editors use these declarations, as does `config set KEY VALUE` completion through the `config-value` metadata kind on both frontends. Size editors offer `auto`, `fit`, `fill`, percentage presets and custom values. `apps.menu.popup.width`/`height` accept percentages or bounded fixed dimensions; `auto` preserves the existing layout.

`apps.menu.popup` controls Dots popup position, border style and colors independently of shell FZF defaults. Placement defaults to `center`, the frame to `rounded` and its color to the theme `accent`. Set/unset use the ordinary config workflow and take effect when the next popup opens; no theme publication or tmux reload is required. See [popup settings and supported values](profiles.md#dots-popup-appearance).

`dots config` opens the config browser in a terminal and lists configuration when redirected. Implemented routes are `browse`, `list`, `get KEY`, `set KEY [VALUE]`, `unset KEY`, `path [NAME]`, `check`, and `migrate`. Every route accepts `--profile ID` and `--json`. Except migration, routes also accept `--defaults` for shared colors, icons, formatting and application defaults; it cannot be combined with `--profile`. Set/unset accept `--dry-run`; set accepts `--json-value`. Migration previews by default and applies only with `--apply --yes`; `--dry-run` always prevents writes. Metadata and contextual key/profile completion are shared by Bash and native PowerShell. See [configuration contracts and examples](profiles.md#profile-configuration).

Human results use the shared renderer; scalar paths/get values and schema-1 JSON remain undecorated. JSON contains `schema`, `profile`, and `path`, plus `config` for lists, `key`/`value` for gets, or `status`, `items`, and optional `transaction` for mutations. Invalid argument syntax returns 2, validation/operation failures 1, success 0, and interruption 130. The main `dots menu` launcher includes Config as a cooperating popup. Explicit key/value edits and migration retain their direct workflows.

Configuration objects and arrays render as Dots sections and resource cards. Use `dots config get files.termux --json` for a structured envelope. Scalar `get` and `path` outputs remain exact. `icons.*` and `colors.*` support get/set/unset, validation, dry-run, contextual completion and retained undo. `dots config path icons` and `path colors` locate the TOML files. `dots config browse` supports `--query TEXT` and `--client CLIENT`, plus profile/default selection. `browse --json` emits the ordinary configuration document without probing FZF or tmux. Bare `dots config --json`, explicit `list`, `get`, `path`, `check`, help and completion remain noninteractive. Missing FZF/popup support produces a styled report with an explanation.

The browser opens List/Get/Set. List is a searchable read-only inventory; Get and Set first choose All, Icons, Colors, Formatting, Apps, Files, Profile, Settings or Environment. Get shows details; Set opens editing actions. Alt-G selects a category, Alt-S selects a profile or shared defaults, Alt-N adds an environment declaration in Set only, and F1 opens help. Escape returns from nested dialogs and closes the root successfully; Ctrl-C returns 130. Typed edits and resets review the saved value, proposed result and destination before default-Cancel Save. Review sizing reserves both action rows before allocating the scrollable preview; Alt-P toggles it, including when a short popup starts with it hidden. The exact reviewed plan retains its drift guards and undo transaction. File actions hand off to existing workflows only for the active profile, without approval flags. Query/focus is retained by action, scope and category. Bare `config get` and `config set` open their guided flows in a usable terminal; missing operands in data/noninteractive calls remain errors. See [the config popup](profiles.md#configuration-popup).

`dots config get|set|unset profile.alias --profile ID` inspects or edits an additional profile namespace; it is also editable under Profile in the config popup and completes as a config key. Aliases do not inherit. `dots profile env [ID]` includes generated path values alongside literal application declarations.

For schema-2 file compositions, `dots files edit --platform NAME` edits that base profile; omitting it edits the active leaf. `--platforms` changes registry eligibility for both new and existing resources. `track` journals registry/profile updates together and returns a transaction for undo; it still installs no files. See [mapping semantics](files.md#stash-and-edit-mappings).


### Effective visual configuration

`dots config explain KEY [--app cli|tmux|yazi|fzf|gum|starship|gitmux]`
reports an individual icon/color field’s effective values, sources and supported
consumers. It accepts `--profile`, `--defaults` and `--json` and remains read-only.
`dots config refresh [--dry-run] [--json]` refreshes the active profile’s visual
preferences while preserving the current theme. It also retries failed consumer
notification. Visual `config set` and `config unset` refresh affected active
consumers automatically; `--no-refresh` saves only. Existing scalar and get/list
JSON contracts are unchanged; mutation JSON adds a `refresh` result when used.
Attempted publication or consumer failures return nonzero after preserving the
saved setting. Missing optional consumers and absent theme publication are
reported explicitly. The existing Config browser adds effective Details and a
reviewed Refresh action. See [visual configuration](profiles.md#effective-visual-values-and-refresh).

Configuration reads resolve recognized keys through their effective layers and return null when unset; unknown keys remain errors. Native `apps.wttr` uses its active TOML. See [typed controls](profiles.md#application-and-formatting-controls). Todo list/browse accept `--list-type tree|regular` for human views; JSON/Markdown remain unchanged.

### Selective checkout setup

`dots files install/uninstall` and `dots init --setup` share the terminal-default wizard. Repeated `--component` and `--resource` select components/catalog IDs; `--interactive`, `--non-interactive`, `--no-clear` and `--no-logo` control invocation. Install also accepts `--with-dependencies`, `--save-choices`, `--fonts FILE` and repeated `--font-target`, alongside existing source/package options. See [installation](installation.md#component-selection-and-preferences) for exact defaults, native parameters, approval and output contracts. Configuration review: **add** `apps.setup` controls with next-invocation activation; **update** WinGet manager choices. Menu review: **add** Files Install/Uninstall terminal actions without `--yes`; **update** native package capability checks. Owners are Files, Package and Fonts maintenance.
