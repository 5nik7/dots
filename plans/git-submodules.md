# Git info and submodule workflows

**Status: Implemented; Termux/controller verification complete, other native-platform acceptance pending.**

Implemented `git info`, recursive `git submodules` with `--details` and `--depth`,
`git submodules status [PATH] --dirty`, and publication of PATH or explicit
`--all-submodules`. Inspection is local; missing children remain missing.
The default base is Dots, with `-C` selecting another repository. Paths name
registered descendants relative to that base. Owner namespace and configured
ownership are separate facts. URLs are redacted in human and JSON output.

Shared Python inspection and selection serve Bash and native PowerShell.
Existing publication engines accept selected forests, preview once, and confirm
once. Selected roots have no mutable parent outside the selection. Existing
ownership, locks, fingerprints, staged-pointer preservation, partial failure and
explicit-refspec policies apply. Excluded parent pointers are reported for later
recording. `--all` still selects ordinary unstaged files, not repositories.

Presentation uses published Git roles, shared resource styles, host icons,
muted tree connectors, wrapped detail rows and existing progress controls.
Info contains availability counts; the default tree is compact. Dirty status
includes local changes, pointer differences and blockers, not clean ahead-only
repositories. Depth limits are explicit and distinct from incomplete discovery.
JSON is versioned and undecorated. Existing commands/data contracts are retained.

Acceptance: isolated recursive fixtures and bare remotes, selection boundaries,
missing/unsafe children, changed/staged pointers, one confirmation, cancellation,
partial failure and cleanup; metadata/completion on all four shells; forced
decoration JSON, URL redaction, themed 40/80/120-column PTYs, narrow Unicode paths,
and representative inspection timings. Run affected suites sequentially.
Native Windows PowerShell 5.1/7, Linux and WSL runtime/visual acceptance must be
recorded separately from Termux/controller evidence. Windows app destinations
are unchanged. Preserve existing unrelated edits; no live fetch/commit/push.


## Verification record (2026-10-23)

- New feature suite: 20 tests passed across Bash and native controller paths.
  Final targeted reruns covered pending-pointer styling/idempotence (2 tests) and
  indented narrow tree rows plus whitespace-preserving remote URLs (4 tests).
- Existing suites passed: Git operations 27, native Git 24, Git styles 7,
  Bash dispatcher/completion 24, resources 13 and progress 11. Native CLI ran
  12 tests: 11 passed, one PowerShell-engine test skipped. The broad run totals
  137 passes and one skip; targeted reruns are additional verification.
- Owned PTYs cover 40/80/120 columns, light/dark role tables, host icons and
  plain output. Manual 40-column review identified a detached-branch wrap;
  narrow metadata now stays indented under its repository. JSON bytes remain
  independent of forced decoration. Bash SIGTERM and native-controller SIGINT
  fixture checks release locks; actual Windows Ctrl-C/Ctrl-Break remains pending.
- Python/Bash syntax, 89-command metadata validation, changed Git-script
  ShellCheck and catalog lint passed. Full ShellCheck analysis of
  `lib/dots/complete.bash` exceeded bounded runtime/resource limits; its syntax,
  contextual provider and shell-adapter behavior passed. This lint gap is retained,
  not presented as a clean full-recursive ShellCheck pass.
- Relative Markdown links and `git diff --check` passed. No live fetch, commit,
  push, initialization, installation or shell reload was performed.

Warm sequential Termux observations (three samples per command, median ms;
fixture-local, no cold-start or cross-platform claim):

| Registered children | Existing status | Info | Submodule tree |
| --- | ---: | ---: | ---: |
| 0 | 330.2 | 712.4 | 460.4 |
| 4 | 1550.6 | 1063.2 | 2145.9 |
| 9 | 3290.5 | 1488.9 | 4272.5 |

The tree gathers remote, ownership, workflow and pointer facts in addition to
status. Info inspects only the root's detailed status while counting descendant
availability. No persistent cache or startup/discovery work was added to ordinary
dispatch. `--depth` bounds tree traversal, and delayed progress covers longer
inspection. Future optimization should retain these observations and avoid
weakening registered-path or mutation checks.

Native Linux/WSL and Windows PowerShell 5.1/7 runtime, terminal/font rendering,
completion and interactive acceptance remain named pending gates. Portable Python
execution on Termux does not satisfy them. Windows app destinations are unchanged.
See [Git commands](../docs/git.md) for the implemented interface.
