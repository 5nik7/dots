# Command Presentation

**Status: Accepted project-wide requirement, 2026-09-24; live Bash, theme and file views provide the initial implementation.**

Every new or changed first-party human-facing command must provide polished, cohesive output by default. Presentation is part of command acceptance, including help, empty results and failures. This contract governs future work in every plan under [decision 0009](decisions/0009-cohesive-command-presentation.md); it does not resume paused work or claim that every existing executable already conforms.

## Output Modes

| Output | Required behavior |
| --- | --- |
| Human terminal view | Clear hierarchy, concise wording, consistent spacing, semantic colors and status markers; adapt to narrow terminals. |
| Explicitly undecorated human view | Preserve the readable layout and all meaning without ANSI or font-dependent icons. |
| Redirected human/list output | Default to clean plain output; preserve each command's documented line or TSV format. Explicit presentation settings may enable decoration for human views. |
| Structured or script-facing output | Preserve exact documented data regardless of presentation settings: JSON, raw paths, scalar queries, completion candidates, generated shell code and machine-readable helper reports. |

Choose and document a command's output modes before implementation. Do not assume every non-JSON response is human prose. Color-value queries explicitly requesting ANSI are data interfaces whose requested bytes remain intentional. Do not add banners, summaries, path abbreviations or status markers to data interfaces. Keep structured schemas versioned and separate from human formatting.

## Color and Icons

### Help syntax and tagline

First-party help and usage, including bundled applications and shipped standalone aliases, use shared semantic spans. The executable, first command, deeper subcommands, options/flags and arguments have separate roles throughout synopses, rows, examples, explicit inline references and parser-error usage. Option values and finite choices are arguments; brackets, equals signs, separators and ellipses are punctuation. Ordinary prose is not colored merely because a word matches a command. Existing section layouts, root command grouping, authored logos and theme-preview palettes retain their owners.

| Config role under `colors.apps.cli.help` | Default |
| --- | --- |
| `executable` | Theme cyan, terminal cyan fallback |
| `command` | Theme blue, terminal blue fallback |
| `subcommand` | Theme magenta, terminal magenta fallback |
| `option` | Theme yellow, terminal yellow fallback |
| `argument` | Theme green, terminal green fallback |
| `heading` | Existing CLI heading style |
| `description` | Existing CLI foreground style |
| `punctuation` | Existing muted style |
| `tagline` | Theme accent when present, otherwise ordinary foreground |

All roles support the existing foreground, background and text-attribute fields. These syntax hues identify token types; they do not indicate success, warning or error. Help-only saves take effect on the next invocation without publishing a theme or reloading applications. `apps.cli.tagline` controls the phrase beneath root artwork and defaults to `Manage your dotfiles and more...`; empty text hides the line, and reset inherits. Artwork remains governed by its existing controls. See [help configuration](configuration.md#help-and-usage-preferences).

Structured views wrap inert spans before painting. Parser adapters preserve their existing plain grammar layout and apply spans only when emitting to the selected stream. Examples are never evaluated. Successful help uses stdout; parser-error usage follows stderr's own terminal/color policy. Plain output, completion, JSON, scalar/raw output and generated shell code preserve their contracts. Basic Bash and PowerShell help use built-in default text/colors when Python preference resolution is unavailable; this fallback does not read arbitrary saved appearance overrides.

Config's human list uses compact color/style samples, such as
`fg:warning,bold,underline`, rendered with the represented style and reset before
the next span. Icon samples use their resolved style with muted color names or
supplying configuration keys. Menu icons follow the shared menu icon accent and
role-specific overrides; ordinary foreground fallbacks have no annotation.
Samples retain selected-profile inheritance and
symbolic names; the plain view retains the same information. These are explicit
configuration previews, separate from the report's semantic labels and headings.

Existing Config rows may show a published or consumer fallback with a muted
source annotation. FZF colors preview their native color and attributes;
runtime-dependent settings name their owner without claiming a concrete value.
These annotations do not add keys or alter stored, JSON or scalar values.

Fonts reports, help, reviews, diagnostics and compatibility human listings reuse
the CLI field/resource renderer. Nested choices and catalog/glyph rows reuse menu
spans and shared popup appearance. `apps.fonts` controls human detail and previews;
`colors.apps.fonts.*` provides nullable font field styles and `icons.menu.fonts` supplies
the font symbol. See [font output preferences](fonts.md#output-preferences).
Preview snapshots render at the actual pane width without invoking providers.
JSON, exact paths/glyphs and ordinary redirected output bypass these preferences.

Root usage artwork keeps its classic vertical blue/cyan coloring by default. `apps.cli.logo_gradient=installer` selects the same horizontal published hint/info/accent gradient as setup, through a shared renderer; missing palette stops leave the artwork plain. Config saves apply on the next invocation. The optional Python renderer preserves a builtin classic fallback for dependency-free basic help. Setup's Profile display uses a blue label, bold yellow profile ID, and parenthesized directory in dim terminal foreground, abbreviating only the home prefix to `~`. These owner-requested accents and green guidance/cyan preference heading remain separate from completion statuses.

Use the live [presentation controls](commands.md#presentation-helpers): prefix `--color=auto|always|never` and `--icons=auto|always|never`, backed by `DOTS_COLOR` and `DOTS_ICONS`. Flags precede the route. These are the implemented controls; draft future flags are not aliases.

Automatic color requires a terminal on the destination stream, `TERM` other than `dumb`, and empty or unset `NO_COLOR`. Explicit `always` overrides `NO_COLOR` for human output. Automatic icons require a usable terminal independently of color. There is currently no font detection; `--icons=never` selects ASCII markers. Evaluate stdout and stderr independently. Respect user preferences even when a terminal supports color.

| Role | Shared visual treatment | Meaning |
| --- | --- | --- |
| Heading | Bold cyan | Command or section identity |
| Label or information | Blue | Field names and neutral context |
| Success or active selection | Green | Confirmed success, available/linked state, current selection |
| Warning or attention | Yellow | A condition needing attention or a skipped operation requiring explanation |
| Error or conflict | Red | Failure, blocked operation, conflict or unavailable required resource |
| Secondary or inactive detail | Dim/muted | Supporting context, exclusions and inactive selections |
| Resource path accent | Magenta | Distinguishes paths from blue repository names and labels |
| Collection count accent | Cyan | Highlights quantities without implying success or failure |

Dots Git metadata has a scoped [theme-role integration](file-colors.md#git-styles): repository identities, branches, file-status labels and tracking counts consume published Git styles through the shared Bash layer. Filenames retain their type/MIME resource styles. Generic headings, informational messages and final diagnostic summaries retain the shared treatment above.

Default Git status groups files under one semantic heading per complete index/worktree state, independently for each repository. Repository rows use two leading spaces, status headings four, and file icons/paths and wrapped continuations six. Heading glyphs use `icons.git.status.*`, follow the icon policy, and share the heading's Git status color; empty glyphs omit the separating space. Combined states keep complete labels and one dominant type icon as defined in [Git views](git.md#output-views). The list avoids key/value label padding and retains directory/basename colors and rename pairs. Short/verbose file rows retain their existing layout.

Human Git identities add `` directly before named branches (including upstreams)
and a host glyph plus one space before repository names/paths: `󰊤 dots` for
GitHub, `` for GitLab, `` for Bitbucket, and `` for local/unknown hosts.
Each glyph shares its adjacent identity's style. Detached HEAD, commit hashes and
unavailable values have no branch glyph. These rules cover Git views/events and
repository labels in file sources, details, discovery, browser and picker previews.
Filesystem `Path` fields in Git info use the shared directory-resource icon and
color, including collection and named info. Repository identities retain host
icons. Ordinary resource paths and resource IDs retain their own styling. Icon and color
controls remain independent; cached local host lookup is optional outside Git
commands. JSON, scalars, completion records and ordinary redirected output remain
undecorated. Forwarded third-party output is unchanged.

Keep status text alongside color; a green marker alone cannot explain whether an item is linked, tracked or selected. Use the shared marker vocabulary with an ASCII fallback. Palette previews may display their actual swatch colors, but diagnostic meanings remain consistent across selected themes. Color may emphasize facts; it must never imply success before an operation succeeds.

## Layout and Wording

Wiki reports and source selectors follow this contract through the shared Python and menu renderers. Page/section/snippet/URL spans have nullable Wiki style overrides, while statuses and filesystem resources retain their semantic/type styles. See [Wiki preferences](wiki.md#output-preferences) for consumer-backed settings and the [route audit](../plans/wiki-output.md) for intentional data and external-output exceptions.

- Use a concise command heading and meaningful count for collections, then repeat the same row or detail layout for each item. Avoid large banners and decorative borders on routine subcommands.
- Use aligned labels when space allows and stacked or wrapped values on narrow screens. Review at 40, 80 and 120 columns. Do not truncate the only usable resource ID, path or recovery instruction.
- Reuse vocabulary across commands: `Source`, `Target`, `Status`, `Platform` and `Repository` refer to the same concepts. Distinguish repository metadata tracking from installation, and planned work from completed work.
- Abbreviate home-relative paths only in human views. Render filenames and other untrusted display text without executing or passing through terminal control sequences. Preserve spaces, Unicode and literal arguments in data interfaces.
- Make empty results explicit and useful. Explain filters or unavailable optional sources when relevant; do not present an empty collection as a failure unless the command contract requires it.
- State a result directly. For failures, identify the operation and affected item, explain the cause when known, and provide an actionable next step when one exists. Never invent a recovery command.
- Previews must say that no changes were made and distinguish intended actions. Mutating commands must distinguish completed, unchanged, skipped and failed actions, including partial completion and recovery evidence when applicable.
- Keep ordinary output concise. Optional interactive tools, progress displays and pagers must not be needed for a useful result; do not prompt or animate through a data stream.

Successful help and result views belong on stdout. Warnings, errors and diagnostics belong on stderr. Preserve documented exit statuses and keep diagnostics out of structured stdout. A successful result summary may describe skipped items, but it must not hide failures reported on stderr.

## Optional Gum interactions

**Accepted convention, 2026-09-28; theme switcher, tracked-config browser and operation confirmations are implemented.**
Prefer Gum for new or changed first-party interactions when a searchable selector,
confirmation, text entry or bounded progress display improves usability. Adopt it
incrementally within the task's scope. Keep routine help, rows and messages in the
shared renderer; do not add a Gum subprocess merely to decorate static output.

Gum is optional. Check availability only on the interactive path and provide a
useful fallback. Require suitable terminal streams before launching a UI, preserve
noninteractive arguments and explicit approval semantics, and never prompt or
animate through data streams. Cancelling, empty selection or UI failure must not
approve an operation. Do not retry a failed UI through a different backend.
Preserve meaningful tool exit statuses; Gum 2.0 uses status 1 for both Escape and
runtime errors, so do not label every such result as a user cancellation. See its
[filter result handling](https://github.com/charmbracelet/gum/blob/v2.0.0/filter/command.go)
and [exit handling](https://github.com/charmbracelet/gum/blob/v2.0.0/main.go).

Use a shared adapter, the existing color/icon controls and readable plain output.
Honor `NO_COLOR` under automatic color and explicit `always` precedence. ASCII
mode also disables tool help that embeds Unicode key glyphs. Inherited Gum color
variables may style widgets; never source shell configuration implicitly to get
them. Semantic diagnostics remain owned by Dots. Tool availability, redirected
streams, cancellation and failures belong in focused tests alongside native PTY
acceptance. No runtime package installation or general command conversion is
implied by this convention.

The [theme switcher](themes.md#interactive-theme-switcher) prefers FZF for live
palette previews, then Gum, then a numbered menu. This scoped exception preserves
Gum-first Back/Apply/Cancel review; shared backend precedence is unchanged. The [tracked-config browser](files.md#interactive-tracked-config-browser)
and [file pickers](files.md#interactive-file-pickers) also prefer FZF for live file previews, then Gum and numbered menus. This is scoped to selection; operation review and confirmation retain their existing adapters.

Managed-file operations and Anodize offer **Cancel / Apply**; Git publish offers
**Cancel / Publish**. Cancel is selected by default. These confirmations use Gum
only with terminal stdin, stdout and stderr, a non-dumb terminal, and the required
executables (Gum, plus Bash for Python callers). Otherwise each command retains
its existing text prompt. There is no FZF confirmation fallback. An explicit
Cancel preserves the command's existing cancellation result; selector errors
stop before approval, and Ctrl-C exits 130. JSON, `--yes` and `--dry-run` paths
bypass Gum entirely and preserve their command-specific semantics. No preview or
operation plan is rebuilt by the interaction layer.

The background switcher and other existing prompts retain their documented
behavior until scoped follow-up work changes them.

## Shared menu selection

Keys category/mode and Weather main/Location/Units selectors use shared menu icon/label/description spans with profile and per-entry overrides. Category count separators/brackets belong to the description span. An explicitly styled icon span is not repainted by generic glyph detection, so its per-entry override remains authoritative. Selected rows retain these span colors through the existing picker color adapter; ordinary menu callers opt in through `preserve_row_styles`. Render-local menu formatting does not change a caller's subsequent report layout. See [menu preferences](configuration.md#keys-and-weather-menu-appearance).

**Implemented shared support, launcher and session picker.** `lib/dots/menus.py` uses the existing Python `Presentation` renderer and scoped FZF adapter. Choosers fit their labels, title and header within the invoking terminal; tmux sizing uses a verified exact client. FZF colors come from the published literal palette adapter. Icons remain optional, and control characters in titles/labels are displayed literally. Listing rows wrap by display cells; JSON bypasses rendering entirely. Session choices show names, window/attached-client counts and a current marker; empty inventories use the shared empty-choice view.

The shared parser supports auto/browse/print/JSON modes for menu controllers. Auto requires terminal streams and a usable terminal; explicit browse can use a validated background tmux context. Missing FZF or popup capability lists choices with a stderr explanation; a failed running selector never falls back or chooses another action. CLI cancellation remains 130, and shortcut-specific normalization belongs to the Prefix m/s wrappers.

After selection has returned, `run_action` either inherits a normal terminal, opens a targeted terminal host for an interactive workflow/static output, or forwards context to a cooperating popup-owning browser. It never opens a nested selector itself. Launcher prompts use lowercase, unspaced middle-dot breadcrumbs (`dots:`, `dots·files:`, `dots·themes·plugins:`), followed by one space. The shared chooser accepts an optional interactive `prompt` override, uses it for sizing, and retains the menu title for printed/JSON views. Delegated pickers retain their own prompts. Family menu rows use lowercase names and optional icons without descriptions; printed/JSON views retain descriptions. Back, contextual help and per-frame queries are owned by the launcher. Reader popups retain 90% client width and fit displayed rows, including title/status, blank lines, wrapped text, tabs, Unicode cell widths, reader controls and borders. Height has a six-row minimum and a 90% client-height cap, clamped to the available size. ANSI styling does not count as text. Commands capture once in a compact cancellable loading popup; it closes before the fitted reader opens. Prepared messages skip loading, and wiki selection closes its host before handing back the document for reading. Interactive workflow hosts and their confirmations retain normal sizing. Static results in ordinary and hosted terminals use the scrollable less reader, with a read-only FZF fallback, and remain until dismissed. The less subprocess uses UTF-8 and marks the three Unicode private-use ranges printable (`LESSUTFCHARDEF=E000-F8FF:p,F0000-FFFFD:p,100000-10FFFD:p`) so Nerd Font glyphs render directly. These settings are reader-local; captured bytes, safe control-character display, caller icon preferences and global less configuration are preserved. Reader status is separate from the command's result; failures from interactive hosted commands remain visible too. Closing a host before a result exists is cancellation. The selected page in interactive wiki browsing uses the same reader. Direct output/data paths and unrelated picker defaults remain unchanged. See the [menu plan](../plans/popup-menus.md) and [shared-menu checks](testing.md#shared-menu-support).

## Application reports

Blastoff current, theme list (including list aliases), theme save, backup list and doctor, plus pkgs help, operation previews, list, managers and doctor, use the shared Python presentation layer in terminals and menu readers. Reports have cyan headings/counts, blue labels/identities, quiet source prefixes, green current/success markers, yellow attention states and red errors. Paths use published resource styles and optional icons. Theme provenance retains its distinction between exact current content and last-loaded history. Package doctor expands FZF and completion records into labeled sections; package lists retain their installed/external markers. All views wrap complete values at narrow widths.

Compact package transactions use profile-aware `colors.apps.pkgs` roles across reports, previews, formatted streams and progress; package identities default to theme accent and manager labels to `colors.apps.pkgs.manager` (magenta), independently of warning/identity roles. Statuses, labels and muted skip counts retain their own styles. Bounded diagnostics and the exact npm/pip noise filters are described in [package output](packages.md#output).

The private capture context selects a human layout independently of color/icons; disabling both still leaves a readable popup. Existing application color flags override Dots color settings, then pkgs configuration supplies its fallback. Dots automatic/forced color and independent icon rules apply to these reports. Ordinary redirected output, JSON, raw TOML and generated completion bytes retain their formats. Save prompts keep their existing choices and cancellation behavior. Blastoff help artwork and application pickers retain their own presentation. Package help derives commands/options from its grammar without manager probes; plain terminal help retains the same layout. Owned pkgs subprocess streams use the shared semantic palette in terminal/menu contexts; `pkgs format` explicitly formats stdin. Raw mode and ordinary redirected subprocess bytes remain unchanged. Formatted APT output suppresses its exact unstable-CLI advisory. Other warnings, full unknown messages and partial prompts remain visible; formatting never determines process status. See [package output](packages.md#output).

## Operation progress

Slow human views use a shared transient display on stderr. Animation starts after 500 ms; fast work remains quiet. Both stdout and stderr must be terminals, and `TERM` must not be `dumb`. `apps.cli.progress` controls existing consumers, independently of colors and icons, and defaults to `both`.

The first row shows only a full-width bar and overall percentage, such as `[━━--------] 27%`. The second row orders the spinner, bare current-step count (`1/2`), activity, bar and measured percentage. It omits the `Overall` label, root manager/repository counts and count unit words. Equal sibling managers, repositories or groups receive equal shares; known steps divide their parent's reserved share. Totals are fixed before crediting work. Later discovery happens inside a reserved step, so it cannot reset or expand the overall denominator.

| Mode | Overall row | Current-step row |
| --- | --- | --- |
| `none` | Hidden | Hidden |
| `spinner` | Percentage | Spinner, bare step count, activity and measured percentage when available |
| `bar` | Bar and percentage | Bare step count, activity, measured or indeterminate bar and percentage when known |
| `both` | Bar and percentage | Spinner, bare step count, activity, bar and percentage when measured |

`DOTS_PROGRESS=auto` (also the unset behavior) follows Config. Explicit `none|spinner|bar|both` overrides it; `never` remains an alias for `none`. Invalid values disable the optional UI. There is no new global progress CLI flag or required optional tool. Existing command-specific switches remain compatible.

Overall progress measures completed work, not elapsed time. Opaque commands hold their reserved share until they return. Native download percentages describe only the current transfer; finishing one archive cannot complete an enclosing command that may fetch more archives. Verification and finalization have reserved steps. Handled failures and skips can count as processed; final results remain authoritative for success. Cancellation freezes reached progress, and recovery activity does not complete the failed operation. No remaining-time estimate is inferred, and Git does not parse transfer percentages.

Bars fill the available terminal width, reserving its last column to prevent wrapping. The current row reserves eight interior bar cells when possible, truncates transient activity first, and expands the bar into unused space. Only extremely narrow rows shrink or omit the bar. Both rows follow terminal resizing; actual terminal dimensions take priority over stale `COLUMNS`. Unknown activity has no invented percentage.

`icons.progress.bar.filled|empty|left|right` defaults to `━`, `-`, `[` and `]`. Each is one printable display cell; only surrounds may be empty. Config offers individual glyph suggestions, not presets. `colors.apps.cli.progress.filled|empty|surround|percentage` supports foreground, background and shared attributes. Filled cells and percentages retain the heading color (aqua in the current theme); surrounds and empty cells use theme muted. Spinner and activity styles stay separate. These controls use normal Config inheritance and apply at the next invocation without publishing a theme. See [progress appearance](configuration.md#progress-appearance).

| Family | Progress coverage |
| --- | --- |
| Git | Repository discovery, status inspection, publication input collection and local sync/publish phases; status/publication use known repository counts. |
| Themes | Preparation, rendering, bat cache generation, publication, quiet application reloads and installed-theme validation; `update --all` uses the selected checkout count. |
| Files | Discovery, catalog/browser loading, planning and integrity checks; transaction preparation, replacement and reverse recovery use operation counts. |
| Packages | Compact install/remove/upgrade tracks managers, preparation, returned commands and finalization. Native pip transfers and pacman-family transactions supply local byte/package measurements. Export and upgrade lists track inspected managers. Package styles and quiet/raw suppression remain authoritative. |
| Fonts | Preparation counts families/files within a reserved phase, followed by application and finalization. Provider byte totals describe the current download. File transactions divide the reserved application phase. |
| Wiki and weather | Page builds reserve render/apply/finalize work; clone and forecast fetch remain opaque steps. Weather completion installation reserves generation and transaction work. |
| Cleanup | Scan, approved groups and receipt finalization use reserved scopes; cancellation freezes progress and receipt totals remain authoritative. |
| Anodize | Theme loading/import, image/seed generation, rendering, preparation, save and application through both entry points; saves share file transaction progress. |

Prompt-capable or directly outputting external commands use a static phase message instead of animation: Git fetch/init/commit/push/checkout/merge, theme downloads, tmux reloads and wallpaper adapters. These messages appear immediately before the child starts so prompts and child output remain readable, even when a child takes a long time. Progress does not capture, reroute or replay child output. Existing timeout and exit-status behavior is retained.

`--yes` retains progress but bypasses confirmation. JSON, raw paths, scalar queries, raw exports/app previews, generated shell code, ordinary shell initialization, completion, help, dry runs and redirected output bypass the progress UI, including static phase messages. Explicit color/icon settings never override this gate. Slow human read-only discovery is eligible and does not write progress files or application state.

The existing color and icon policy applies. ASCII mode uses `|/-\` spinners; configured ASCII bar glyphs remain, while non-ASCII glyphs fall back to `#`, `-`, `[` and `]`; disabled color removes ANSI color sequences while terminal cursor/erase controls update both rows. Neither renderer hides the cursor or changes terminal input mode. Transient labels are sanitized and shortened to fit; final result and recovery text keeps complete paths. Bash escapes non-ASCII path characters for predictable cell widths, while Python measures combining and wide characters. Bash uses optional `stty` to read terminal width and handles resize notifications and otherwise falls back to `COLUMNS` or 80 columns.

Python progress also accepts structured inert text/style spans. Resolve palette styles once per operation, clip by display cells before applying color, and keep the existing string API for other callers. Package progress uses this for configurable identities and activity colors; plain/NO_COLOR views contain the same clipped text. Nested phases restore the prior activity state while retaining monotonic overall progress. Activity-only updates cannot overwrite overall completion.

Clear and stop the display before results, diagnostics, confirmation or selection. Nested work shares the active renderer; captured private bridges disable their own progress. Renderer errors disable presentation without approving, cancelling or retrying work. File notifications run at existing journal boundaries and never alter transaction ordering or schemas. Rendering workers must release inherited locks, terminate on completion/interruption, and preserve the operation's result.

## Verbose operations

File-changing commands, checkout setup, and theme set/refresh/switcher accept `-v`/`--verbose`. Default previews and summaries remain unchanged. Verbose output adds permanent action rows on stderr while preserving delayed progress: clear and join the active renderer before each row, then resume the same phase/count without resetting its delay. Prompts and outputting children retain exclusive terminal access.

Rows distinguish planned actions (`Would …`), completed writes, unchanged/skipped reasons, rollback, and cleanup. Link/copy arrows read `source -> destination`; backup arrows read `original -> recovery copy`. Paths use the shared resource icons and published type/MIME colors, separately from semantic action colors. Only the current home prefix is abbreviated to `~`; escaped complete paths wrap at narrow widths. No content or raw internal trace is printed. Redirected verbose output remains static and honors explicit color/icon controls.

Temporary verified recovery copies are reported when prepared. After successful finalization, rows identify retained payloads and their backup ID, or temporary-copy cleanup. Theme connector copies belong to generation journals and are labeled accordingly; they are not file-backup registry entries. A completed individual action does not imply transaction success: subsequent rollback rows and the final result remain authoritative.

`--json` suppresses added verbose output on both streams, preserving existing JSON and diagnostics. Dry-run details describe intended actions without animation or claims of completed writes. Private theme bridges, scalar queries, generated shell code and previews inside selectors receive no operation trace. Verbosity is per invocation, not a persistent environment setting. File observers are optional and cannot change mutation ordering, journal schemas, approval or recovery behavior; display failures disable optional details.

## Ownership and Compatibility

Anodize has an owner-requested [branding exception](anodize.md#terminal-logo): default human views use only exact LOGO1/LOGO2, including captured and redirected output, disabled icons and dumb terminals. Wide help uses LOGO2; narrow help, results and previews use LOGO1. Color controls affect color only. Short panes preserve the full artwork with vertical scrolling. Text artwork gradients run from bottom-left hint through midpoint info to top-right accent, restarting for each symbol/wordmark. Banners use the published active theme; palette results and embedded previews use the addressed palette, using its background from the first logo row through headings, details and notes, and restoring its foreground after artwork. Missing gradient stops retain solid magenta for banners or the preview foreground. Explicit graphics and larger braille layouts remain opt-in. Data output stays undecorated. Both static-help adapters use core-owned renderers without executing an extension or engine.

`lib/dots/ui.bash` owns the shared Bash helpers. The lazy `lib/dots/interactive.bash` adapter owns optional UI selection, Gum invocation policy and numbered prompts; interactive callers reserve fd 3 for the visible terminal before capturing selector output. The Python file catalog's `Presentation` renderer mirrors the policy; it is not a generated binding. New Bash commands must reuse the helpers. Other first-party implementations must match this contract through an equivalent renderer and policy tests rather than inventing per-command colors or message conventions. See [architecture](architecture.md#live-bash-framework). The Python renderer provides `heading_spans` for independently styled heading parts and `detail_spans(..., label_width=10, label_gap=1, indent=4)` for aligned details. Both sanitize text and wrap by display cells before styling; command-specific spacing overrides leave the shared defaults unchanged. Key previews use `indent=0` and matching list colors, including orange modes, as a scoped keybrowser presentation.

The dispatcher forwards extension streams unchanged. First-party extensions, including relevant Androidots and other submodule commands, follow this contract when added or changed, respecting their local guides. User and third-party extensions are encouraged to use the helpers; the dispatcher does not restyle arbitrary output. Generated app configuration and application UIs retain their own formats and theme contracts.

Preserve the unified theme data interfaces and palette helper APIs. The singular/plural theme split is defined by [decision 0013](decisions/0013-shell-environment-and-theme-collection.md); styling changes do not independently authorize API removal. Styling work must not add shell-startup scans, load live user configuration, require optional UI dependencies, or change command semantics.

## Todo views

Todo human views use a scoped semantic mapping: titles are bold theme `bright_magenta`, alias values are bold theme `accent` (including parent aliases), open status is bold `bright_green` (bold ANSI bright green when the palette role is unavailable), and high/normal/low priorities are respectively bold `warning`, regular `orange`, and bold `muted`. Missing warning roles fall back to bold ANSI yellow. Notes and acceptance text keep normal foreground. Other statuses retain their blue/green/yellow/muted roles. List rows, expanded details, mutation results, popup rows and previews share these spans; identifiers and separators remain independent. Todo uses a two-space base indent for help, detail/result fields, notes, acceptance items and popup previews, with flush-left headings. Human lists put the alias or short UUID above the title/status/priority summary at that same indent; Project/Goals fields have single label/value gaps. One blank line separates goal blocks, including implicit/`--print` lists and the missing-FZF fallback. Wrapped title/identifier lines retain the two-space base indent, other labeled views retain value alignment, and popup selection rows stay compact. Shared presentation defaults for other command families are unchanged. Alias labels fall back to short UUIDs, while detail views retain full UUID metadata and readable notes/acceptance blocks. Argparse coloring is disabled where available; Todo help renders plain usage definitions through Dots, avoiding nested ANSI sanitization. See [todo](todo.md).

Shared human detail/resource rows in Python and Bash read `formatting.apps.cli`; shared menu rows and Config browser details read `formatting.apps.menu`. Use the [existing width, gap and alignment controls](profiles.md#shared-row-alignment) rather than introducing per-command padding settings. Python `row_layout.py` resolves display-cell widths, percentage columns and padding; Bash uses builtins and validated literal settings. Explicit domain column overrides remain supported. CLI and Config-browser keys longer than their columns stack above aligned values, retaining their complete text. Config selector display lines may be multiline; numeric selection identities and search keys remain separate inert data. Verify ordinary redirected output and scalar/JSON contracts independently of human layouts.

## Acceptance Gate

For each new or changed human view, the focused plan must identify:

1. Its human and data modes, shared renderer, terminology and applicable semantic roles.
2. Representative help, list/detail, success, empty, warning and error output. Add conflict, preview, partial failure and recovery cases where the command supports them.
3. Terminal and redirected stdout/stderr behavior, automatic/forced/disabled color and icons, `NO_COLOR`, `TERM=dumb`, and readable plain output.
4. Narrow and wide layouts, long paths, spaces, Unicode, leading dashes and control-character display safety where relevant.
5. Unchanged structured/scalar/generated output under forced decoration, and parity between implementations of the same policy.
6. Focused automated evidence plus a visual review of representative terminal output. Record native platforms separately from simulated fixtures and disclose remaining gaps.

Mark cases that do not apply with a reason. Existing [presentation tests](testing.md#terminal-presentation) establish the initial coverage, not completion of this entire matrix across all commands and platforms. Use existing runners where appropriate; add missing cases with the corresponding implementation change. A documentation review alone does not establish runtime conformance.

## Theme-family panels

Family help and native previews use the addressed palette, including explicit
foreground and background. Preserve authored SGR colors and formatting for logo
files containing ANSI foreground/background colors; apply the theme palette only
to logos without embedded colors. Isolate authored logos with a reset before and
after the entire block so multiline formatting survives without leaking into help.
Strip styling in plain modes and sanitize other terminal controls. Measure visible
logo width without SGR codes. Reset each themed help line, wrap at narrow widths
and retain usable full IDs. Text accents fall
back to readable foreground when contrast is insufficient; swatches remain exact.
`--color=none` aliases `never`; spaced `--color NAME` remains a family color query.
Data output bypasses panels even when decoration is forced. This scoped palette
presentation does not change semantic status meanings in other command families.

Explicit checkout setup (`dots init --setup`, files install/uninstall and root scripts) is a human managed-operation workflow, eligible for the same file/theme progress policy. Ordinary `dots init [shell]` remains an undecorated code stream. Setup uses the shared Python renderer through both native wrappers; Git child output stays visible on stderr.

## Filesystem resources

**Implemented.** Live first-party human views use published Dots type, extension
and MIME colors for filesystem resource fields. Operation statuses and repository
identities keep their semantic colors. Magenta is the fallback resource accent,
not an override of a published file style. `--icons=never` omits resource glyphs;
paths and status words remain readable without a Nerd Font. Colors and icons are
independent. Explicitly forced decoration applies only to human views.

Bash `dots::resource` and `dots::resource_row`, and Python
`Presentation.resource` and `resource_detail`, separate actual paths from display
labels. Known intended types may be supplied for missing/planned resources.
Automatic classification covers ordinary files, directories, executables, links,
broken links, FIFOs, sockets and devices. More specific metadata types can be
supplied by the owning command. MIME comes from known metadata or the shared
filename/suffix registry; presentation never reads file contents. Explicit
extension rules precede custom MIME rules, published suffix rules, default MIME
rules and the ordinary file fallback. Non-file types take precedence.

The versioned `file-styles.tsv` publication is parsed as data and read lazily once
per renderer. No subprocess per resource, implicit theme generation or startup
scan is added. Older or malformed snapshots fall back to the published
`ls_colors`, then shared terminal defaults. Escaped legacy LS_COLORS keys are
ignored in this conservative fallback; a normal theme refresh publishes the full
literal rules. Missing snapshots do not prevent output or require a refresh.

The shared `lib/dots/resources.tsv` owns resource glyphs and common filename/MIME
hints. Names, URLs, repository IDs, shell examples and scalar path responses are
not automatically interpreted as paths. All display text is escaped; paths wrap
without losing spaces or characters. Theme-panel paths use shared icons while
retaining the addressed panel's foreground/background. Selectors keep their native
widget styling and internal plain selection labels. Child streams remain intact.

The live surface audit is in [the implementation plan](../plans/cli-presentation.md).
Standalone scripts, nested-project tools are outside
this rollout. Native bootstrap adapters follow the same semantic color controls
without requiring Python or Bash merely to print a missing-dependency error.

## Bash and native PowerShell acceptance

Every future human-view change must preserve matching semantic colors, file/MIME icons, verbose backup/link events, progress and optional picker interactions in Bash and native Windows PowerShell 5.1/7. Reuse the Python renderers/resource/progress adapters where available; keep machine outputs undecorated. Verify quoted/Unicode paths, NO_COLOR, redirected output, cancellation and narrow layouts on each actual host. Fixture parity and successful Python execution do not establish native Windows terminal rendering. See [PowerShell acceptance](powershell.md#acceptance-and-remaining-limits).

Anodize authoring selectors are another scoped FZF-first workflow, followed by
Gum/plain fallbacks and the existing separate approval prompt. Theme previews use
the shared renderer with exact candidate foreground/background and the default
syntax mapping, preserving low contrast for faithful review. Preview rows reset
SGR styling; FZF dimensions bound and fill the preview pane. No terminal-global
color changes are made. Plain and existing data/redirected formats remain intact.


The project/session browser shares `picker_style.py` semantic field colors and
cell fitting with the keys popup. Project rows use ``; generic sessions retain
their tmux icon. Each icon shares its adjacent name style. Non-current project
names with at least one session use bold theme `accent` in the list and preview;
non-project session names use bold theme `blue`. Current names retain magenta emphasis. A project
containing the current session uses emphasis, while each individual preview
name follows its own session state. Empty-project preview titles use bold
`light_foreground`; their menu icon/name use normal-weight `light_foreground`,
while the `no session` label remains muted.
Positive project counts use theme orange in both list forms (compact `[N]` and
expanded counts), including projects containing the invoking session.
Counts use normal weight. The complete `·  current` / `· current` marker uses
bold theme `bright_green`, separately styled from its preceding count and any following
path. Selected rows retain their field colors. At narrow widths the count
uses compact numeric notation; full session counts, names, paths and window/client
counts remain in the inert preview. Its project header uses a muted separator,
for example `battery · [1 session]`. Preview totals use theme orange for all
positive totals, including projects containing the current session, and red
for `[0 sessions]`. Window counts stay green. Client counts read `N attached`,
with yellow for positive counts and muted zero. Other separators and labels stay
muted. The path line reads `Project: 󰉋 ~/path`, with the folder icon and path
sharing the published directory style; icon-disabled views omit the folder
without extra spacing. Home paths use `~`; a matching single-session name is
not repeated. Palette roles use bounded terminal fallbacks; missing
`light_foreground` falls back to resolved foreground. The preview stays below
the list. Its stable per-view height fits wrapped display cells,
normally five rows including borders, capped at eight and terminal bounds.
Alt-J/K scroll longer content and Alt-P toggles it. Prompts use
`dots·tmux·sessions:` breadcrumbs. The sole header hint is `Alt-H: keys`; a
separate fitted read-only reference styles the key labels. Escape/Alt-H returns
with search and focus intact. Color/icon policy and plain fallbacks remain
independent; JSON and existing session data are unchanged.

### Less standout text

The shared less style uses exact theme `foreground` on `lighter_background` at normal weight, with an explicit reset. It applies to prompts, search highlights and other standout messages. Shell refresh and popup readers preserve user overrides and existing color controls; redirected content is unchanged. See [global less colors](shell-environment.md#global-less-colors) for ownership, reload behavior and the native Windows exception.

Shared visual defaults live in `default/icons.toml` and `default/colors.toml`, with per-key profile overrides. Python and Bash renderers consume the same named roles; resource matchers resolve icon tokens. See [visual preference bindings](profiles.md#icons-and-semantic-colors). Objects and resource arrays from `dots config get` use readable sections by default; explicit `--json`, scalar/path queries, completion, shell output and raw interfaces remain data contracts. Exact palette previews keep their own candidate colors. Config icon samples trace the named consumer, including shared menu and per-entry styles, semantic statuses and native weather controls. Published file/Git samples use the resource matcher and label their rule owner and representative context; Vivid suffixes are identified without guessing a color key. A generic foreground fallback receives no annotation. Samples use exact spans so repeated glyphs do not repaint one another.

Typed spacing/alignment and application controls are documented under
[configuration controls](profiles.md#application-and-formatting-controls).
New human spans must assess both icon and adjacent text styles, foreground and
background, labels/values, gaps, indentation/tab stops and native placement.
Expose only fields that the consumer uses; absent icon colors inherit their
enclosing span. Keep configuration reads and raw/data output free of decoration,
except muted human `null`. Future formatting additions require typed validation,
CLI/popup discovery, actual consumer checks and an explicit activation contract.

Dots selector frames use [dedicated popup controls](profiles.md#dots-popup-appearance): centered placement, a rounded frame and a theme-accent border by default. Generic shell FZF border flags do not remove this frame. Popup colors override inherited picker colors only where configured; row-specific field styles remain intact. Terminal fallbacks retain the frame, plain mode stays readable, and native tmux hosts use the same applicable position/frame/colors without changing server defaults.

## Interactive shell completion

Color belongs in the shell's rendered menu, after literal candidates have been
captured. Completion records and inserted words remain undecorated. Zsh/FZF-tab
uses separate semantic candidate, description, separator and heading spans;
selected rows retain those spans. Files keep LS_COLORS. Escape untrusted control
characters for display without changing insertion or preview identity. Unknown
completion types stay neutral. Honor the shared color policy and the feature
switch. Use the [completion acceptance](testing.md#shell-completion-colors) for
40/80/120-column menus, literal insertion and plugin compatibility.
