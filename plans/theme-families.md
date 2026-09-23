# Additional shared theme families

**Status: Implemented**

Add TokyoNight (night/storm/moon/day), Rosé Pine (main/moon/dawn), Kanagawa
(wave/dragon/lotus), Gruvbox (dark/light), and a pywal16 current-palette source.
Keep native color names, add per-flavor role mappings where needed, and support
hyphenated family names without ambiguous selection parsing. All commands and
three-shell completion must work with these families.

Extend the Neovim adapter and declared lazy.nvim plugins, including startup,
focus refresh, light/dark transitions, failure rollback and dashboard palette
selection. Preserve Catppuccin behavior and legacy arrays. Pywal16 input is read
as strictly validated color data, never executed; publish an immutable snapshot
through the existing transaction helper. No wallpaper generation, live selection
changes, package installation, commits or pushes are included.

Use official upstream palette/plugin sources with recorded provenance. Test in
owned fixtures with public plugin sources, then run existing theme/Bash/Zsh suites,
PTY acceptance, lint/format/docs checks and sequential benchmarks. Baseline:
`/data/data/com.termux/files/usr/tmp/dots-theme-bench-xg662a8p/results.json`.

## Result and verification

The [theme reference](../docs/themes.md) owns the available flavors, input format,
shared shell/editor behavior and dependencies. All requested families are present;
Go development remains paused. Native palettes and license/provenance files stay in
the existing theme tree. Neovim changes are in the separate `config/nvim` repository.
No live selection or installed plugin directory was changed.

Native Termux verification:

- Theme suite: 23 tests passed, including all-family tests with copied official
  public plugin sources; no editor skips in this run. Focused tests were rerun after
  final shell compatibility and Catppuccin startup changes (four shell/query cases
  and two actual-plugin editor cases).
- Bash dispatcher: 21 tests passed. Zsh regression suite: 17 tests passed.
- Real PTY acceptance: Tab, `cd <Tab>`, history picker, and reload equality for
  hooks/FZF/fpath/keybindings passed; fixture `dots-zsh-ycg50p48` under Termux temp.
- ShellCheck warning-level checks passed with existing dynamic-source/external-global
  exclusions (`SC1090`, `SC1091`, `SC2034`, `SC2154`). Lua formatting, shell syntax,
  relative documentation links and both repositories' diff whitespace were checked.
- Pywal16 tests cover missing/malformed/duplicate/incomplete data, NUL/oversize
  input, mismatched quotes, nonexecution, explicit refresh and retained snapshots.
- Neovim tests cover native highlights, all variants, focus/manual reload, palette
  edits, missing-plugin rollback, and avoiding duplicate Catppuccin setup at startup.

## Performance evidence

Sequential five-sample minimal-fixture measurements, seconds unless noted:

| Measurement | Before | After |
| --- | ---: | ---: |
| Catppuccin warm cached initialization | 0.04457 | 0.04000 |
| Catppuccin published initialization | 0.02838 | 0.02990 |
| Minimal editor, options-only bridge | 0.04972 | 0.05237 |
| Minimal editor, shared startup adapter | not measured | 0.05415 |
| TokyoNight warm cached initialization | not present | 0.05267 |
| TokyoNight published initialization | not present | 0.02808 |

An intermediate measurement found duplicate Catppuccin setup changing its cache
hash: shared startup took 0.09323 seconds. Reusing already configured palette
options removed that redundant work; a regression assertion covers it.

The unchanged prompt path still uses only builtins and reads one small token. The
baseline was 0.069 ms/call; initial post-change measurement was 0.076 ms/call. A later
run varied substantially (0.811 ms), so five isolated 10,000-call samples were taken:
0.055–0.285 ms/call, median 0.184 ms. The code path is unchanged apart from literal
comparison quoting; these variable wall-clock observations do not establish a
speedup or a portable performance budget. Single cold Catppuccin initialization
observations ranged 0.525–0.677 seconds after, versus 0.485 seconds before; each still
generates the full legacy four-flavor arrays, plus semantic directory rules.

Artifacts under `/data/data/com.termux/files/usr/tmp/`:

- Baseline: `dots-theme-bench-xg662a8p/results.json`.
- Intermediate measurement: `dots-theme-bench-dhpco8mu/results.json`.
- Final measurement: `dots-theme-bench-s4ag_1fa/results.json`.
- Repeated prompt measurement: `dots-theme-prompt-lphkbnke/results.json`.

Public test plugin revisions are recorded in each added family's `SOURCE.md`;
the temporary test-source map is `dots-theme-upstream-cc7w6emh/sources.json`.
These are actual plugin tests under isolated minimal Neovim, not full live LazyVim
startup or native Linux/WSL/MSYS/Windows verification. Normal Lazy plugin installation
and live focus/UI acceptance remain user-environment checks. No documentation is
intentionally deferred.

## Authorized follow-up

See [Omarchy-style themes](omarchy-themes.md), [files catalog](files-catalog.md), and [configuration path migration](config-path-migration.md). The completed results above describe their original implementation; the follow-up has separate acceptance.

The authorized [Omarchy theme expansion](omarchy-themes.md) and [files catalog](files-catalog.md) are now implemented under [decision 0008](../docs/decisions/0008-config-catalog-and-theme-apps.md). Earlier completed-slice evidence remains historical; current contracts are in the linked references.
