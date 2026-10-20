# Verbose operations

Status: Implemented; verified on native Termux. Native Windows/PowerShell execution remains unverified.

Add `-v`/`--verbose` to file mutations, checkout setup wrappers and theme
set/refresh/switcher. Preserve default previews, summaries, data streams,
approval semantics and journals. Git, Anodize, collection downloads and wallpaper
selection are outside this slice.

Use optional transaction notifications and the existing Bash/Python resource
renderers for source -> destination rows, recovery copies, retained backups,
cleanup, rollback and unchanged/skipped reasons. Suspend progress around permanent
rows and resume its previous phase. No configuration contents or child output
capture is added. Setup's private theme bridge stays a data protocol.

Acceptance: isolated lifecycle and theme workflows, observer failure and rollback,
JSON/default-output compatibility, aliases/completions, and native Termux
40/80/120-column PTYs with colors, icons and plain fallbacks. Run affected suites
sequentially. No live setup, theme activation, publication or commit is authorized
by verification. Native Windows coverage must be reported separately.

Durable behavior belongs in [presentation](../docs/presentation.md),
[files](../docs/files.md), [installation](../docs/installation.md) and
[themes](../docs/themes.md).

## Verification

The focused verbose runner passed all 14 tests, including real install and switcher
PTY paths, backup cleanup/retention, undo/restore/recovery, observer failure,
metadata-only changes, JSON suppression, interruption, published file styles and
independent color/icon controls. Native PTYs covered 40/80/120 columns; layouts
were also inspected with complete wrapped paths and resource icons.

Affected regressions accounted for 242 cases in total (237 passed, five skipped):
progress 11, resources 11, file operations 21, catalog 9, mappings 28, check 16,
installation 23, installation adapters 9, theme workflow 27, picker 16, generated
theme commands 12, plugins 21, dispatcher/completion 24, and verbose operations 14.
The workflow runner reached its 420-second aggregate cap after 21 completed cases;
the remaining six cases passed individually. Four native Windows/PowerShell checks
and Pi's optional native loader/hot-reload check were skipped. This does not claim
native Windows, WSL, PowerShell or Pi runtime verification.

Command metadata validation passed for 84 external commands. Changed Python/Bash
sources passed syntax checks. Scoped ShellCheck found no new warnings; the four
SC2034 warnings in the completion library also occur on unchanged HEAD. Recursive
source-following lint exceeded its time bound; individual libraries were checked
without following their dependencies. Relative Markdown links and whitespace were
checked. Verification used disposable roots; no live setup, theme activation,
commit or push was performed.
