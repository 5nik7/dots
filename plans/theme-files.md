# Generated theme file inspection

**Status: Implemented; local verification complete with the limits below.**

Implement the approved active-generation-only `dots theme files` list, info, show, path, check and browse interface through a shared Python controller. Both Bash/standalone theme and native PowerShell use the same data and rendering. No editing, repair, history selection, publication, or live reload belongs to this change.

## Contract

Inventory generated application and shared data, summarize caches, exclude journals/backups/bookkeeping. Trace current template precedence and derived artifacts, stable/resolved paths, fixed and supplementary managed connectors, and known non-link consumers. Source resolution is for the next refresh, not historical provenance. Observe only known paths and bounded retained transaction metadata; do not scan the home directory or execute consumer applications/hooks. The optional bounded bat preview renderer is the sole inspection subprocess.

## Acceptance

- [x] Shared controller, command metadata and four-shell contextual completion.
- [x] Isolated inventory, source, pointer, connector, preview and browser tests.
- [x] Structured/scalar/raw byte contracts under forced decoration.
- [x] Presentation gate from [the shared contract](../docs/presentation.md): shared Python Presentation, populated/empty/error views at 40/80/120 columns, light/dark/plain, safe paths and cancellation.
- [x] Relevant dispatcher/theme/native controller regressions and documentation checks.
- [x] Command/theme/schema/architecture/README/testing documentation synchronized.

Native Windows PowerShell 5.1/7 engine, destination, symlink and terminal acceptance remains pending unless explicitly recorded below. Linux/WSL fixtures are not native platform acceptance. Existing unrelated `.dots/files.json` edits are preserved.

## Verification

The implementation uses `lib/dots/themes/inspection.py` for both frontends, and the shared Python Presentation/Selector adapters. [Commands and limitations](../docs/themes.md#generated-theme-files) and [schema 1](../docs/specification.md#generated-theme-file-inspection) are synchronized with the implementation.

- Focused inspection suite: 15 tests passed. Tests include Bash publication/native rendering in owned roots, all completion protocols, exact data output, live generation replacement, source precedence, destination drift, linked parents, supplementary completed journals, and no-write snapshots.
- Native Termux PTYs cover 40/80/120-column detail/empty/error/content views with light/dark resource palettes and plain output. The shared numbered browser is exercised with real input and Escape cancellation; optional Gum/FZF behavior is reused, without claiming new native tool-specific key acceptance.
- Existing Bash dispatcher (24 tests), theme-command (12 tests), native CLI (13 passed, one PowerShell-engine skip), and resource (15 tests) suites passed.
- Native Windows PowerShell 5.1/7 engines are unavailable here. Their runtime, actual app destinations/link privileges, interactive selectors and terminal rendering remain pending acceptance. Termux and synthetic Windows-path fixtures do not establish Linux/WSL/Windows native evidence.
- No live refresh, activation, repair, commit or push was performed. The pre-existing `.dots/files.json` change remains untouched.

Shell syntax and ShellCheck of all seven new wrappers passed; the changed theme command adapter also passed standalone ShellCheck. The existing catalog/family modules retain SC2034 and SC2153/SC2015 findings reproduced from HEAD. Recursive ShellCheck was stopped after more than two minutes, the grouped source check exceeded 30 seconds, and the isolated completion module exceeded 10 seconds; full completion-module ShellCheck acceptance remains unverified. No unrelated lint cleanup was included. Static metadata validation passed for 98 external commands, relative Markdown verification passed for 698 links across 109 files, and `git diff --check` passed.

## Preview and evidence refinement

**Status: Implemented; focused local acceptance passed.** The approved follow-up adds bounded directory previews, optional bat syntax highlighting, spaced artifact blocks and read-only consumer evidence. `check --consumers` opts into failures for confirmed mismatches; ordinary file/link health remains unchanged. No application activation or persistent runtime tracking is added. The only new child process is the optional bounded text renderer.

- The 15 inspection tests and 12 preview/evidence tests passed. Additional reruns cover populated listings and directory previews at 40/80/120 columns, `--consumers` completion in Bash/Zsh/Fish/native protocols, and real bat output through both command adapters using owned PTYs. The renderer leaves test home/config/state/cache metadata unchanged. Raw and redirected regular-file bytes remain exact.
- Evidence tests cover inherited values, literal references, plugin content/receipts, disabled automation, malformed and drifting configuration, publication ancestry, opt-in failure status, and verification without subprocesses or persistent writes. Directory cases cover empty/truncated listings, binary children, literal links and source fallback; renderer cases cover timeout/output limits, invalid output, missing tools/cache and disabled color.
- Bash dispatcher (24), resource presentation (15), native CLI (13 passed, one unavailable PowerShell-engine skip), theme commands (12), and four selected plugin/Starship parser regressions passed. The regression invocation also loaded the 32 underlying theme tests: 30 passed, one Zsh round-trip test failed during Vivid generation, and one all-family Neovim test exceeded its 40-second timeout. Both failures reproduced in disposable baseline fixtures with changed code restored from HEAD and the new inspection files removed; no unrelated fixes were included.
- Changed wrappers passed Bash syntax and ShellCheck with source following. Static metadata validated 98 commands; relative Markdown verification passed 699 links across 109 files; `git diff --check` passed. The earlier full completion-module ShellCheck limitation remains unchanged.
- Five read-only observations of the live 32-artifact generation measured median inventory time of 120.8 ms and consumer evidence time of 115.3 ms, excluding process startup. No persistent cache or ordinary-dispatch work was added.
- Native Windows PowerShell 5.1/7, native Windows bat and app-config acceptance remain pending. No live theme publication, activation, repair, commit or push occurred; unrelated `.dots/files.json` changes remain intact.
