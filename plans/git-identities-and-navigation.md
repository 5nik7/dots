# Git identities and named submodule navigation

**Status: Implemented; Termux/controller checks passed, native-platform acceptance pending.**

Add branch glyphs (`main`, no space) and host glyphs (`󰊤 dots`, one space)
to Dots-authored human Git identities. Icons inherit adjacent text styles and
respect independent icon/color controls. Detached HEAD and unavailable values
have no branch glyph; unknown/local hosts use ``. Preserve machine output,
redirected data, ordinary resource styling, and forwarded third-party output.
Cover Git views/events and applicable file sources/details/discovery/browser
labels, with one cached local host lookup per repository per invocation.

Add recursive `git submodules info [--depth N]` and a dynamic
`git submodule NAME [info|status|publish|submodules|submodule]` family.
Names are direct-child path basenames; colons cross registered submodule edges.
Repeated singular navigation is equivalent. Default to info. Refuse ambiguous
siblings and show exact-path alternatives. Resolve once to registered paths,
then reuse existing guarded action controllers. Never initialize missing nodes.
Named publish retains child-first, staged-only, preview/confirmation and excluded
parent boundaries; plural publish retains explicit --all-submodules selection.

Reuse static action headers for help and contextual completion on Bash/Zsh/Fish
and PowerShell. Help has no Git discovery or extension execution. Named JSON
uses underlying action schemas; collection info has selectors, depth/completeness
and per-repository descendant counts from one discovery traversal.

Verification: disposable nested repos/local remotes; names versus paths, action
word names, duplicate siblings, absent/unsafe children, colon and repeated
navigation, literal argv, publication boundaries/drift/cancellation, exact icon
spacing/styles, JSON/redirected byte contracts, 40/80/120-column PTYs, and cached
lookup counts. Run affected suites sequentially and record native evidence
separately. Windows app destinations are unchanged. Native Linux/WSL/Windows
PowerShell runtime and interactive acceptance remain pending where unavailable.
Preserve existing checkout work; no live commit/push/fetch or activation.

## Presentation and route audit

Git info, tree, collection info, status, sync/publish events, confirmation previews
and pending-parent details use human identity renderers. File source names/roots,
repository detail fields, discovery groups, browser notices and picker previews
use cached optional host lookup. Resource IDs and ordinary source/target paths
retain resource styling. Transient Git progress uses action/count labels; permanent
results identify repositories. Third-party Git output and scalar/JSON/completion
interfaces remain outside decoration.

Named actions project canonical static headers rather than defining executable
routes for names. Dispatch retains longest-prefix resolution and collision checks.
Help does not resolve repositories. Literal leading-dash names use the existing
`--` separator; internal helper modes do not reserve ordinary submodule names.
Collection info counts descendants in one traversal and reports depth boundaries.

The canonical usage and safety boundaries are documented in [Git commands](../docs/git.md).

## Verification record (2026-10-23)

- Git feature suite: 30 tests passed across Bash and native-controller paths,
  covering named/colon/repeated navigation, action-word and literal names,
  ambiguity, missing children, scope-preserving publication, cancellation,
  selection drift, interruptions, and exact JSON values under forced decoration.
- Affected regression suites: 200 passed, one PowerShell-engine test skipped.
  Counts: Git operations 27, native Git 24, Git styles 7, Bash CLI 24,
  native CLI 11 plus one skip, resources 14, files 9, browser 17, check 16,
  pickers 19, file operations 21, progress 11. Final Git-style/resource reruns
  passed after renderer changes. Two final contextual-help/completion rechecks
  also passed after the nested-help usage correction.
- Owned PTYs verified 40/80/120-column layouts with light/dark role tables,
  including collection info and named info. Icons share their identity span,
  NO_COLOR and icon controls remain independent, and JSON confirmation previews
  use stderr without changing stdout records. These are fixture/PTY checks,
  not native Windows or terminal-font visual acceptance.
- Both metadata validators accepted 91 commands. Python/Bash syntax, changed
  Git/wrapper/dispatcher ShellCheck, relative Markdown links and diff whitespace
  checks passed. Full ShellCheck analysis of the existing completion module
  retains the earlier runtime/resource limit; syntax and completion behavior
  passed. Actual native Linux/WSL/Windows PowerShell 5.1/7 and interactive
  Zsh/FZF-tab/font acceptance remain pending where unavailable.
- Cached identity tests verify one local host-resolution sequence per root per
  renderer invocation and an optional-Git generic fallback. No startup Git query
  or persistent cache was added. Windows application destinations are unchanged.
- Warm dispatch medians with 0/100/1000 additional fixture commands were
  55.810/55.339/52.914 ms (three samples, sequential Termux benchmark). Catalog
  and full completion enumeration scale with catalog size; direct dispatch and
  prefix completion remain independent of unrelated command count. Benchmark
  evidence is local and does not claim cross-platform or cold-start performance.
- All mutation tests used disposable repositories and local transports. No live
  fetch, initialization, commit, push, activation or shell reload was performed.
  Existing checkout work, including concurrent unrelated edits, was preserved.

## Path and tree correction (2026-10-24)

Implemented. Git info Path fields use the shared folder icon and directory style, including collection/named info. Human trees connect their header, separators, nested entries, wrapped rows and details with muted topology-aware gutters; final branches close and summaries remain outside the tree. Keep ordinary redirected output and JSON exact. Use the shared span renderer with opt-in continuation prefixes, and test both front ends at 40/80/120 columns. Native-platform visual acceptance remains pending; no Windows application destinations change.

Verification for this correction: 14 focused Git inspection tests passed across Bash and native-controller paths, including 40/80/120-column owned PTYs, nested/final siblings, depth limits, empty/missing children, long paths, folder colors, ASCII fallback and data-output checks. All 15 shared-resource tests and 7 Git-style tests passed (36 checks total, plus two initial targeted checks). Python syntax, both 91-command metadata validators, relative Markdown links and diff whitespace passed. The human-only renderer adds no discovery queries; ordinary redirected rendering keeps its prior path. Native Windows/Linux/WSL terminal/font acceptance remains pending. No live Git mutations or shell reloads were performed.
