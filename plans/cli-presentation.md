# Live CLI presentation

**Status: Implemented, 2026-10-16.** Scope: all live first-party Dots routes,
Anodize aliases and root setup adapters. Preserve the installation and Deja work.
Standalone scripts and nested repositories are excluded.

## Audit and ownership

| Surface | Renderer and action | Data/customization boundary |
| --- | --- | --- |
| Dispatcher help, commands, validation | Shared Bash headings/rows; verify | Static metadata, JSON, completion and init remain exact |
| Git status/sync/publish | Reference layout; add file resources to status/events | JSON and subprocess streams unchanged |
| Files catalog/browser/history/backups/operations | Python Presentation; resource fields and wrapping | IDs/status remain semantic; JSON/raw paths unchanged |
| Setup/install/uninstall | Same Python renderer plus native bootstrap diagnostics | Native wrappers preserve machine streams and return codes |
| Environment | Shared Bash; resource fields | Scalar/JSON/redirected NAME=value unchanged |
| Themes/collection/plugins/backgrounds | Shared renderers; resource fields | Family palette panels and exact swatches preserved |
| Anodize | Python Presentation; resource fields | Authored logo and palette samples preserved |
| tmux key menu | Existing shared headings and rows; verify | Key/action text is not a filesystem path |

## Design

Expand the existing project skill. Publish a versioned data-only file-style table
from resolved theme rules. Bash and Python consume it lazily once per command;
older snapshots fall back to published LS_COLORS, then shared resource defaults.
A shared icon/MIME table describes common filename and suffix categories. No
content sniffing, theme generation, shell evaluation or per-path subprocesses.
Use filesystem observations or caller-supplied intended types for planned paths.
Keep resource colors separate from operation statuses and repository headings.
All resource text is sanitized and complete; narrow views wrap instead of losing
paths. Icon/color preferences are independent. Preserve customized theme context.

Progress retains its 500 ms delay, count bars, unknown-work spinners, static child
phases, stream gating and cleanup. No animation in help, dry runs, data, redirected
output or shell startup. Do not restyle arbitrary third-party output.

## Acceptance

Owned fixtures cover resource parity, MIME/extension precedence, old/malformed
snapshots, missing/planned paths, links, Unicode/control characters and preferences.
Review 40/80/120-column PTYs and theme exceptions. Check data bytes with decoration
forced, progress cleanup, relevant suites, skill validation, docs and diff checks.
Record baseline failures, native coverage and timing limits below.

## Verification and limits

- Resource renderer suite: 11 passing checks, including Bash/Python rule parity,
  literal/case-colliding suffixes, disabled executable styling, legacy/malformed
  snapshots, actual Git rows versus JSON, and owned 40/80/120-column PTYs.
- Shared command coverage passed: dispatcher (24), environment (8), common shell
  helpers (29), file catalog (9), Git operations (27), file operations (21),
  progress (11), file colors (8), theme commands (12), file browser (17),
  Anodize presentation/data cases (3) and engine-free logo checks (11).
- Installation: all 16 cases passed across the suite and focused reruns after
  updating disposable checkout fixtures to include the resource module. Adapter
  suite: 5 passed, 2 skipped for unavailable native PowerShell/Windows. Seven
  PowerShell initialization/presentation checks are skipped locally; no native
  Windows claim is made. Anodize checks used the existing prebuilt test engine.
- Tmux key suite: 18 passed; the existing popup test fails before invoking the
  renderer because it expects a blue border and text title, whereas committed
  `config/tmux/tmux.conf` uses brightblack and a yellow icon. That deliberate
  customization is preserved. Native popup acceptance remains blocked by this
  stale assertion; the other native private-server/key views pass.
- Reviewed populated resource views at 40/80/120 columns, including long paths,
  spaces and Unicode. Paths wrap at suitable slash/space boundaries without
  dropping delimiters. Existing theme-logo/palette tests preserve authored colors.
- A three-sample synthetic Bash listing with 100 rows and 500 rules took 2.897 s
  with a linear rule scan, then 0.577 s after indexing suffix lengths and MIME
  priority once per command. Original undecorated-style rows took 0.033 s; richer
  resource formatting has a bounded cost and no subprocess per entry. A final
  five-sample forced-human help comparison measured 0.269 s before / 0.235 s after;
  three-sample dispatch medians were 0.0224 / 0.0217 s. These are advisory mobile
  timings, not evidence of a general speedup. Plain/data paths skip style reads.
- Skill validation, 81-command metadata validation, Python/Bash syntax, scoped
  ShellCheck, relative documentation links and `git diff --check` pass.

No live publication, installation, commit or push was performed. Existing theme
snapshots use the documented fallback until the next ordinary refresh writes the
new projection. All earlier installation and Deja work remains uncommitted and
preserved; nested repositories were not changed by this presentation task.
