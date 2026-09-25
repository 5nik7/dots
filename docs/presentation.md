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

## Ownership and Compatibility

`lib/dots/ui.bash` owns the shared Bash helpers. The Python file catalog's `Presentation` renderer mirrors the policy; it is not a generated binding. New Bash commands must reuse the helpers. Other first-party implementations must match this contract through an equivalent renderer and policy tests rather than inventing per-command colors or message conventions. See [architecture](architecture.md#live-bash-framework).

The dispatcher forwards extension streams unchanged. First-party extensions, including relevant Androidots and other submodule commands, follow this contract when added or changed, respecting their local guides. User and third-party extensions are encouraged to use the helpers; the dispatcher does not restyle arbitrary output. Generated app configuration and application UIs retain their own formats and theme contracts.

Preserve existing script interfaces and legacy plural theme APIs. Styling work must not add shell-startup scans, load live user configuration, require optional UI dependencies, or change command semantics. The paused Go core and historical experiments retain their current behavior until separately authorized work applies this contract.

## Acceptance Gate

For each new or changed human view, the focused plan must identify:

1. Its human and data modes, shared renderer, terminology and applicable semantic roles.
2. Representative help, list/detail, success, empty, warning and error output. Add conflict, preview, partial failure and recovery cases where the command supports them.
3. Terminal and redirected stdout/stderr behavior, automatic/forced/disabled color and icons, `NO_COLOR`, `TERM=dumb`, and readable plain output.
4. Narrow and wide layouts, long paths, spaces, Unicode, leading dashes and control-character display safety where relevant.
5. Unchanged structured/scalar/generated output under forced decoration, and parity between implementations of the same policy.
6. Focused automated evidence plus a visual review of representative terminal output. Record native platforms separately from simulated fixtures and disclose remaining gaps.

Mark cases that do not apply with a reason. Existing [presentation tests](testing.md#terminal-presentation) establish the initial coverage, not completion of this entire matrix across all commands and platforms. Use existing runners where appropriate; add missing cases with the corresponding implementation change. A documentation review alone does not establish runtime conformance.
