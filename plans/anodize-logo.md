# Anodize supplied logos and Extract popup

**Implemented, 2026-10-27.** Implements the [authoritative LOGO1/LOGO2 contract](../docs/anodize.md#terminal-logo). This replaces earlier branding selection instructions in this plan. The supplied six-row assets are the only defaults: LOGO2 for wide help, LOGO1 for narrow help, other human views and previews, independent of pipes, icon/color settings and viewport height. Explicit larger/graphics choices remain supported. Missing assets use exact embedded LOGO1.

Add `--logo-layout=base`, synchronize metadata/completion and both static-help frontends without executing extensions or the engine. Pin popup Help to text/horizontal and Preview/Extract to text/base. Add Extract after Create, reuse its guided read-only image/lightness/mode flow, and retain interactive Preview/Extract results via the existing document handoff and reader. Raw app and machine output stay undecorated. Reuse the shared palette renderer and [presentation acceptance gate](../docs/presentation.md#acceptance-gate).

Audit all Anodize documentation, asset notes, manual generation, plans and relevant skills for conflicting branding instructions. Update canonical sources and rebuild/check the local wiki. Preserve original assets and unrelated changes. No theme saving, publication, live reload, commit or push is required.

## Acceptance

Verify exact asset content in Python/Bash/native static help, errors/results, captured popup Help, guided previews, Extract results and real FZF-tab paths. Cover 40/53/80/120 columns, short/tiny panes, plain/color/icon settings, pipes, legacy encodings, missing/malformed assets and explicit alternatives. Test menu Back/cancellation, result scrolling, no persistent Extract state, metadata/completion and byte-identical data paths. Native Windows PowerShell 5.1/7, Linux/WSL and real graphics acceptance remain distinct from Termux/shared-controller evidence; Windows app destinations do not change.

## Verification

Native Termux checks use owned homes, configuration/state roots, PTYs and private tmux servers. Exact captured popup Help passed at 40/53/80/120 columns, including narrow LOGO1 fallback and inherited alternative renderer preferences. Guided Extract/Preview, retained readers, scrolling, query restoration, cancellation and no persistent Extract state passed. Real short-pane Zsh/FZF-tab previews showed all six LOGO1 rows. Data/raw-output, optional-renderer failure and explicit layout checks retain their separate contracts.

An isolated offline Go build, package tests and vet passed. Across the logo (16), launcher (19), interactive (12), integration (5), authoring (18), reader (15), Bash dispatcher (24), native Anodize (3), native CLI (14), wiki (18) and wiki Git (10) suites, 153 tests passed and one native PowerShell engine test was skipped because PowerShell is unavailable. Added native completion and exact supplied LOGO2 checks also passed on targeted reruns. Python parsing, Bash/Zsh/Fish syntax, manual freshness/lint and 910 relative links across 128 files passed. Both documented artwork blocks match their supplied assets exactly, and the source audit found no old triangle artwork or conflicting default policy. The logo adapter passed ShellCheck. Standalone completion lint matches its baseline diagnostics; recursive ShellCheck was stopped after excessive resource use, so it is not claimed as complete.

Native Windows PowerShell 5.1/7 UTF-8, keyboard/reader behavior, native Linux/WSL and actual Kitty rendering remain pending platform acceptance. Shared controller fixtures and protocol tests do not establish those native results.

Canonical docs, relevant skills, static command metadata and the generated manual are synchronized. The local wiki was rebuilt in retained transaction `f1e59144466c44c8b9ce43fbeab3b107`; `dots wiki check` reports healthy. No live theme publication, configuration reload, commit or push was performed. Reopening the menu loads the source changes.

## Theme-gradient follow-up

**Superseded by the three-stop follow-up below, 2026-10-27.** Initially applied a diagonal accent-to-bright-magenta foreground gradient to supplied text artwork, preserving every character and layout. Normalize horizontal and upward positions equally over visible cells, then interpolate RGB with integer half-up rounding. LOGO2's symbol and wordmark restart independently; the optional stacked layout likewise separates the two parts. Blank spaces and blank braille cells preserve their bytes without defining endpoints.

Use bounded published palette data for help/list/diagnostic banners, and explicit addressed colors for palette results, interactive and completion previews. Keep equivalent Python/shared-panel and builtin Bash rendering, existing color controls and solid-color fallback for missing/invalid endpoints. Restore panel foreground before padding and preserve its background. Optional graphics, data interfaces, menu behavior, routes, schemas and Windows app destinations do not change.

Verify endpoint/direction/rounding/region and exact-art parity, missing/malformed snapshots, equal colors, independent stdout/stderr modes, legacy locales, and Python-free Bash help. Exercise real Help/Preview/Extract readers and short Zsh/FZF-tab panes with active and candidate palettes deliberately different. Run affected suites in owned roots, update canonical docs/manual/skills and rebuild/check the wiki. Native PowerShell 5.1/7 and Linux/WSL visual acceptance remain separate from Termux/shared-controller fixtures.

Gradient verification: 196 tests passed across logo (20), interactive (12), launcher (19), shared menus (24), reader (15), integration (5), authoring (18), Bash (24), native Anodize (3), native CLI (14), resources (15), wiki (18) and wiki Git (10); one native PowerShell case was skipped because the runtime is unavailable. Strengthened FZF-tab artwork-color and palette-fallback cases passed on targeted reruns. FZF fixtures use distinct synthetic endpoints because some bundled themes correctly have identical accent/bright-magenta values. Real RGB popup clients, candidate-versus-active palettes, separate component endpoints, data contracts and background/foreground restoration passed. Python parsing, logo ShellCheck/Bash syntax, manual generation/lint, whitespace and 911 relative Markdown links passed.

The local wiki was rebuilt in retained transaction `14b3d0783f2846ad962758bb6e85eb13`. Reopening a menu/preview loads the gradient; no live theme publication or shell/tmux reload is needed. Native platform acceptance limits above remain in force.

## Three-stop gradient and complete palette panels

**Implemented, 2026-10-27.** Supersedes the two-stop gradient above: all text-logo paths use hint at bottom left, info at the midpoint, and accent at top right. Keep exact artwork, independent symbol/wordmark regions and equivalent integer interpolation in Python/Bash. Published banners use active colors; results, guided draft review and completion previews use addressed colors.

Compose palette-bearing results through one shared ColorView from the first logo row through headings, metadata, body and notes. Preserve selected background, foreground restoration, wrapping, color controls and explicit graphic options. Data interfaces, command flags, Windows destinations and publication state do not change. Update docs, manual and skills, then rebuild/check the local wiki.

Acceptance: three stops and both interpolation halves, malformed/missing roles, exact artwork, Bash/native-controller parity, selected-versus-active colors, full-row backgrounds including header/status/footer, plain/data contracts, real popup and FZF-tab paths. Use owned Termux fixtures; native Windows PowerShell 5.1/7 and Linux/WSL terminal acceptance remain pending.

The focused logo suite passed 22 cases, including three-stop interpolation, selected headers/notes/status colors and draft-review palette ownership. Thirteen interactive cases passed, including standalone/Dots Show with Kanagawa Wave at 40/80/120 columns, real short-pane Zsh/FZF-tab previews, and Preview/Extract readers. Popup Help passed at 40/53/80/120 columns. Shared theme picker (16), resource (15), authoring (18), integration (5), launcher (19), native authoring (3) and native CLI (14, one unavailable PowerShell runtime skip) checks passed. The final interpolation edge cases passed a targeted rerun.

Python parsing, logo ShellCheck/Bash syntax, manual generation/freshness/lint, whitespace and 911 Markdown links passed. The local wiki was rebuilt in retained transaction `472a1f3dfac0415fa5d2cc4841f1153c`; its check reports healthy. Existing native Windows PowerShell 5.1/7 and Linux/WSL terminal acceptance limits remain. Reopening a menu or running Show loads the changes without theme publication or a live reload.

Final gates also passed: Bash dispatcher (24), wiki (18) and wiki Git (10). Across the twelve suites, 176 tests passed and one native PowerShell runtime case was skipped; the targeted interpolation rerun also passed. Final wiki freshness, documentation links and whitespace checks remain clean.
