# Pi theme and completion colors

**Status: Implemented and verified on native Termux, 2026-09-30.**

## Scope

- Convert the supplied `default/themed/pi.json.tbl` into `pi.json.tpl`, preserving Pi role mappings while replacing fixed colors with shared semantic palette tokens.
- Render `pi.json` with normal personal-template/bundled-override precedence and fingerprinting.
- Connect an existing Pi themes directory (`${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/themes/dots.json`) through the existing connector journal. Never modify Pi settings or install Pi. Require an absolute agent directory (also accept `~/`).
- Renew the Pi connector on changed publication so Pi's directory watcher sees `dots.json`; unchanged refresh remains a no-op. Preserve backups, rollback and drift refusal.
- Replace the startup snapshot of Zsh completion `list-colors` with a builtin dynamic style so fzf-tab uses current `LS_COLORS`.

## Verification

- [x] Reproduce stale completion colors in an isolated Nord → Latte prompt-refresh test; FZF UI colors already change correctly.
- [x] Regression test dynamic completion lookup, prompt status and repeated refresh.
- [x] Test Pi rendering across all 34 selections, overrides, refresh fingerprints, default/custom paths, absent directory, backup/rollback, interrupted recovery and drift refusal; verify the installed Pi loader/watcher without starting live Pi.
- [x] Run theme/workflow/Zsh suites, syntax checks, documentation links and diff checks (pre-existing lint/link findings below).
- [x] Synchronize README, command/theme/platform/safety/testing references.

Verification used only disposable homes and state roots. Native Termux evidence does not establish desktop or Windows support. No live theme publication is a test.

## Presentation gate

Reuse existing dry-run connector rows, diagnostics and publication summaries under the [presentation contract](../docs/presentation.md#acceptance-gate). No new route, UI renderer or data format. Plain/forced-color previews cover a custom path containing spaces and Unicode; Pi visual appearance still needs user review.

## Evidence and limits

- Workflow: 22 tests passed, including optional installed Pi 0.99.1 theme-loader/hot-reload acceptance. Pi source docs and directory-watcher implementation were checked locally; Context7 CLI lookup was unavailable in this environment.
- Shared themes: 29 tests passed. Zsh: 17 passed. Bash dispatcher: 24 passed. Isolated Zsh PTY (`--samples 1`) passed Tab/FZF-tab, directory/history pickers and reload checks.
- Bash and Zsh syntax passed; `git diff --check` passed. ShellCheck findings in `apps.bash`/`core.bash` match HEAD (SC2015 and unresolved source SC1091); no new findings. `render.bash` is clean.
- Full relative Markdown audit: 559 links, only the pre-existing `docs/testing.md` → removed `config/yazi/plugins/dots-symlink.yazi/README.md` failure. The standard docs gate remains blocked by it; no newly broken link.
- Alternating isolated Zsh style-query measurements (3 × 20,000 lookups, 40 LS_COLORS entries) gave median 5.74 µs for the old static style and 24.73 µs for the dynamic style. The roughly 19 µs lookup cost buys fresh colors; no subprocess, scan or unchanged-prompt work was added. This is a synthetic Termux measurement, not desktop/startup performance evidence.
- Pi settings and live theme state were not changed. Setup requires publication and selecting `dots` in Pi once. Native desktop/Windows behavior and visual contrast across all palettes remain unverified.
