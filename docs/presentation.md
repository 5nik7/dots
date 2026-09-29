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

Keep status text alongside color; a green marker alone cannot explain whether an item is linked, tracked or selected. Use the shared marker vocabulary with an ASCII fallback. Palette previews may display their actual swatch colors, but diagnostic meanings remain consistent across selected themes. Color may emphasize facts; it must never imply success before an operation succeeds.

## Layout and Wording

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

The [theme switcher](themes.md#interactive-theme-switcher) uses Gum, then FZF,
then a numbered menu. The [tracked-config browser](files.md#interactive-tracked-config-browser)
uses the same adapters and requires operation review before Apply.

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

## Operation progress

**Implemented, 2026-09-29.** Slow human views in the Git, theme, file and Anodize command families use a shared transient display on stderr. Animation starts after 500 ms; fast work remains quiet. Both stdout and stderr must be terminals, and `TERM` must not be `dumb`. `DOTS_PROGRESS=auto|never` controls progress independently of colors and icons; unset means `auto`, and an unrecognized value disables it. There is no progress CLI flag or required optional tool.

Known operation counts use a bar with `completed/total` for the named phase. Unknown work uses a spinner. Counts describe processed items, not elapsed time or successful publication. Cyan marks activity and blue marks the phase; permanent result views remain authoritative for success, unchanged work, failure and recovery. No success is inferred from a full preparation bar. Finalization and integrity checks use a spinner.

| Family | Progress coverage |
| --- | --- |
| Git | Repository discovery, status inspection, publication input collection and local sync/publish phases; status/publication use known repository counts. |
| Themes | Preparation, rendering, bat cache generation, publication, quiet application reloads and installed-theme validation; `update --all` uses the selected checkout count. |
| Files | Discovery, catalog/browser loading, planning and integrity checks; transaction preparation, replacement and reverse recovery use operation counts. |
| Anodize | Theme loading/import, image/seed generation, rendering, preparation, save and application through both entry points; saves share file transaction progress. |

Prompt-capable or directly outputting external commands use a static phase message instead of animation: Git fetch/init/commit/push, theme downloads, tmux reloads and wallpaper adapters. These messages appear immediately before the child starts so prompts and child output remain readable, even when a child takes a long time. Progress does not capture, reroute or replay child output. Existing timeout and exit-status behavior is retained.

`--yes` retains progress but bypasses confirmation. JSON, raw paths, scalar queries, raw exports/app previews, generated shell code, initialization, completion, help, dry runs and redirected output bypass the progress UI, including static phase messages. Explicit color/icon settings never override this gate. Slow human read-only discovery is eligible and does not write progress files or application state.

The existing color and icon policy applies. ASCII mode uses `|/-\` and `#` bars; disabled color removes ANSI color sequences while carriage returns and spaces update the line. Neither renderer hides the cursor or changes terminal input mode. Transient labels are sanitized and shortened to fit; final result and recovery text keeps complete paths. Bash escapes non-ASCII path characters for predictable cell widths, while Python measures combining and wide characters. Bash uses optional `stty` to read the initial terminal width and otherwise falls back to `COLUMNS` or 80 columns.

Clear and stop the display before results, diagnostics, confirmation or selection. Nested work shares the active renderer; captured private bridges disable their own progress. Renderer errors disable presentation without approving, cancelling or retrying work. File notifications run at existing journal boundaries and never alter transaction ordering or schemas. Rendering workers must release inherited locks, terminate on completion/interruption, and preserve the operation's result.

## Ownership and Compatibility

`lib/dots/ui.bash` owns the shared Bash helpers. The lazy `lib/dots/interactive.bash` adapter owns optional UI selection, Gum invocation policy and numbered prompts; interactive callers reserve fd 3 for the visible terminal before capturing selector output. The Python file catalog's `Presentation` renderer mirrors the policy; it is not a generated binding. New Bash commands must reuse the helpers. Other first-party implementations must match this contract through an equivalent renderer and policy tests rather than inventing per-command colors or message conventions. See [architecture](architecture.md#live-bash-framework).

The dispatcher forwards extension streams unchanged. First-party extensions, including relevant Androidots and other submodule commands, follow this contract when added or changed, respecting their local guides. User and third-party extensions are encouraged to use the helpers; the dispatcher does not restyle arbitrary output. Generated app configuration and application UIs retain their own formats and theme contracts.

Preserve the unified theme data interfaces and palette helper APIs. The plural CLI removal is explicitly authorized in [decision 0012](decisions/0012-unified-theme-cli.md); styling changes do not independently authorize API removal. Styling work must not add shell-startup scans, load live user configuration, require optional UI dependencies, or change command semantics. The paused Go core and historical experiments retain their current behavior until separately authorized work applies this contract.

## Acceptance Gate

For each new or changed human view, the focused plan must identify:

1. Its human and data modes, shared renderer, terminology and applicable semantic roles.
2. Representative help, list/detail, success, empty, warning and error output. Add conflict, preview, partial failure and recovery cases where the command supports them.
3. Terminal and redirected stdout/stderr behavior, automatic/forced/disabled color and icons, `NO_COLOR`, `TERM=dumb`, and readable plain output.
4. Narrow and wide layouts, long paths, spaces, Unicode, leading dashes and control-character display safety where relevant.
5. Unchanged structured/scalar/generated output under forced decoration, and parity between implementations of the same policy.
6. Focused automated evidence plus a visual review of representative terminal output. Record native platforms separately from simulated fixtures and disclose remaining gaps.

Mark cases that do not apply with a reason. Existing [presentation tests](testing.md#terminal-presentation) establish the initial coverage, not completion of this entire matrix across all commands and platforms. Use existing runners where appropriate; add missing cases with the corresponding implementation change. A documentation review alone does not establish runtime conformance.
