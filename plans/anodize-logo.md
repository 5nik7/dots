# Anodize terminal branding

**Status: Implemented; unified usage-artwork follow-up on 2026-10-21.**

The follow-up at the end of this plan supersedes the historical compact-text policy below.

## Text asset update — 2026-10-16

**Status: Implemented.** Both renderers use the owner's UTF-8 braille `horizontal.txt`, `stacked.txt`, `logo.txt` and numbered `logo-<width>.txt` assets without modifying their contents. Text help may use half the terminal height, capped at 16 rows; routine views use the six-row base logo within one-third of terminal height. Selection uses measured cell width and row count, retaining a tiny ASCII fallback for explicit ASCII mode, dumb/non-Unicode terminals, redirected output and missing/non-fitting assets. Chafa uses `--fg-only --symbols=braille` and is skipped in ASCII-only modes. Existing Kitty sizing/source policy and data output are preserved. Both renderers, documentation/manual and focused tests are synchronized.

Validation on native Termux:

- `verify_anodize.py check`: Go tests/vet, 18 isolated CLI tests and 11 logo tests passed. This includes unchanged JSON/raw exports/configuration and new supplied-asset selection cases.
- `test_anodize_integration.py`: five tests passed, including three-shell completion and generated-manual checks. `test_bash_dots.py`: 24 tests passed.
- Python/Bash syntax, ShellCheck for the logo adapter, generated-manual freshness, mandoc lint, changed-document relative links and `git diff --check` passed. The full docs audit still fails the pre-existing `docs/testing.md` link to the removed `dots-symlink.yazi/README.md`.
- Native PTY review confirmed exact supplied artwork for horizontal 80×24, stacked 40×24 and numbered icon 80×32. Python/Bash parity covers layout overrides, future variants, malformed files, ASCII/Latin-1 output, explicit ASCII mode, dumb terminals and narrow/short dimensions. Chafa produced foreground-only braille with no non-SGR escape sequences. Actual Kitty display was not newly tested.
- Hash comparisons preserved every supplied artwork file, the deleted `icon.txt`, and unrelated pre-existing changes. The shared README/architecture wording changes were separately verified by reversing only this task's replacements against their initial hashes.
- Default redirected-help medians (10 samples after two warmups) were 258.27/157.86 ms before/after for standalone and 26.29/17.70 ms for Dots. Timing is noisy; no speedup is claimed. Current 40×24 PTY medians (five samples after two warmups) were 163.36 ms standalone and 41.20 ms Dots. No persistent cache or new renderer subprocess was added to default text help.

Changes remain uncommitted. No live theme was applied and no tool was installed.

## Original behavior (2026-10-13)

Portable bundled ASCII branding is the default in both Anodize entry points. Help gets a responsive horizontal/stacked/icon header; routine human views and diagnostics get compact branding. JSON, raw exports/configuration, completion source and candidates stay unchanged. Optional `--logo=text|auto|kitty|chafa` and `--logo-layout=auto|horizontal|stacked|icon` override `ANODIZE_LOGO` and `ANODIZE_LOGO_LAYOUT`. Missing graphics capability, assets or tools falls back to text. No downloads, runtime builds, terminal queries or new required dependencies.

## Implementation

- [x] Bundle eight original PNGs (163,936 bytes total) with provenance and ASCII derivatives.
- [x] Add stream-aware sizing, bounded Kitty/Chafa rendering, help/result/error integration and metadata-only Dots help branding. Default Bash help does not launch Python or Chafa; optional `stty` supplies terminal dimensions.
- [x] Synchronize options, completion, generated manual and user/reference documentation.
- [x] Validate isolated CLI, metadata, presentation, data-output and failure cases; record measurements and visual limitations.

## Presentation acceptance

Follow the [presentation gate](../docs/presentation.md#acceptance-gate). Cover help, list/detail, empty, preview, success, error and interruption; retain semantic colors and complete recovery details. Test 40/80/120 columns, tiny/short terminals, destination-stream sizing, redirected output, color/icon policies and renderer failures. Verify data bytes under forced decoration and keep default help free of renderer subprocesses. Existing transaction tests cover conflict, partial failure and recovery; branding does not change transaction behavior. Review native Termux text/Chafa separately from simulated Kitty protocol checks.

## Verification

Before-change isolated redirected help medians (12 samples after 3 warmups, native Termux): standalone 215.26 ms; Dots static help 14.21 ms. Timing is advisory.

Native Termux verification:

- `python3 -B tools/verify_anodize.py check`: Go tests/vet and 18 isolated authoring/CLI tests passed, followed by seven logo tests. Raw JSON, exports and app previews remain identical under every renderer setting.
- `python3 -B tools/test_anodize_integration.py`: five tests passed, including static metadata, generated manual, Bash/Zsh/Fish candidates and real Tab insertion for the new flags.
- `python3 -B tools/test_bash_dots.py`: 24 tests passed. Changed Bash/Python syntax, ShellCheck (existing SC1091/SC2034 exclusions for shared dynamic-source files), manual freshness/lint and `git diff --check` passed. The new Bash logo adapter passes ShellCheck without exclusions.
- Native PTY review covered 40-column stacked text, 80-column horizontal text, 120-column parity and tiny fallback. Chafa 1.18.3 produced the supplied horizontal mark/wordmark; polite mode suppresses cursor hiding and probing. Kitty tests validate chunking, decoded PNG bytes, sizing and conservative fallback, but actual Kitty display remains unverified.
- The wider `python3 -B tools/zsh_interactive.py --samples 3` check reached reload and then stopped at FZF-tab because `fzf` is absent (`command not found: fzf`). Ordinary three-shell completion acceptance passed; FZF-tab remains unverified in this environment.
- Repository-wide `python3 -B tools/verify_core.py docs` still fails the pre-existing `docs/testing.md` link to `config/yazi/plugins/dots-symlink.yazi/README.md`, also present in `HEAD`. A changed-document relative-link audit found no newly broken links. No unrelated link repair was made.

Alternating unchanged-HEAD/current help measurements in disposable roots (12 samples each, three warmups) were 358.42/318.27 ms for standalone help and 20.77/30.79 ms for Dots static help. Treat the standalone difference as noise, not a speed claim. Static branding adds text rendering, option validation and two metadata options, costing about 10 ms in this run without launching an image renderer. No cache was added. The shared dispatch benchmark (five samples) retained repository-size-independent direct lookup: 23.40/26.55/24.78 ms at 0/100/1000 fixture extensions. Linux/WSL/native Windows and actual Kitty graphics were not newly verified.

Source and assets are left uncommitted; no live theme was applied and no tool was installed.


## Unified usage artwork — 2026-10-21

Owner-approved follow-up: all text banners use usage’s responsive asset selection
and half-height budget capped at 16 rows. Ordinary results/diagnostics no longer
force the base symbol; interactive and completion previews no longer draw a
separate ASCII triangle. Preview workers use pane geometry, preserve panel colors,
and carry layout/icon preferences across captured output. Static Bash error help
uses the same renderer with validated text options. Supplied assets, graphics
policies and machine-output boundaries remain unchanged.

Acceptance: exact artwork parity across help/results/errors/drafts and previews,
40/80/120-column native PTYs, narrow/short panes, layout/icon/encoding fallbacks,
no wrapping of artwork, no renderer process for preview text, static-help
nonexecution and unchanged data bytes. Native PowerShell uses shared Python;
Windows runtime acceptance remains pending on this Termux host. Preserve all
existing work, with no theme activation, installation or Git publication.

Verification on native Termux:

- `python3 -B tools/verify_anodize.py check`: Go tests/vet passed; 18 authoring/CLI
  checks passed (257.015s), 11 interactive checks completed with one FZF-tab skip
  (63.367s), and all 15 logo policy/PTY checks passed (51.905s).
- The interactive suite verifies supplied braille artwork in native FZF panes at
  40/80/120 columns, plus cancellation without publication. The verifier's isolated
  home cannot discover the host FZF-tab plugin. A separate owned-home native
  Zsh/FZF-tab run, using a copied local plugin and the existing private engine,
  passed all five theme/mode preview scenarios (42.565s).
- All five Anodize integration checks passed (70.827s), including completion and
  generated-manual freshness; all 24 Bash dispatcher checks passed (32.069s).
- Exact usage/result/error artwork parity includes valid layout options preceding
  an invalid option. Captured preview tests cover pane geometry, theme text,
  layout/icon controls, malformed height fallback and absence of graphics calls.
- Bash syntax, ShellCheck for the changed adapter, Python compilation without
  bytecode, manual lint, generated-artifact freshness, changed Markdown link
  targets and `git diff --check` passed. Supplied artwork has no changes.
- Native Windows/PowerShell and actual Kitty graphics remain unverified. Windows
  uses the shared Python text selector; graphics-backend policies are unchanged. No live theme was
  applied, no installation performed and no commit/push made.

## Short FZF preview follow-up — 2026-10-21

The prior half-pane-height budget still selected the ASCII triangle below 12
preview rows. Owner-approved correction: interactive and FZF-tab previews select
the supplied usage artwork by available width, with the existing 16-row maximum
artwork budget independent of pane height. Short previews scroll vertically.
Ordinary usage sizing, explicit layout/icon preferences, capability fallbacks,
artwork spacing, theme colors and data interfaces retain their existing behavior.

Acceptance includes exact artwork at 40/80/120 columns and preview heights below
12 rows, native Zsh/FZF-tab mode and theme completion with configured FZF defaults,
preview scrolling and cancellation without publication. Shared Python covers
POSIX and PowerShell preview consumers; native Windows visual acceptance remains
pending. No installation, activation or Git publication is required.

Implemented and verified on native Termux:

- All 15 engine-free logo checks passed (25.336s), including exact supplied
  artwork at preview heights 1/6/8/10/11/12/24 and unchanged ordinary usage sizing.
- Native Zsh/FZF-tab passed seven mode/theme completion scenarios (42.126s)
  at 40/80/120 columns in 24-row terminals. Tests source the configured FZF
  defaults, reveal the initially hidden preview with Ctrl-X, check supplied
  artwork rows, scroll with Shift-Down and cancel without saving or activation.
- The other ten interactive checks passed (39.633s), including native FZF
  cancellation. These tests reuse the existing private engine in isolated roots;
  no engine source changed and no new Go build was required.
- All five integration checks passed (46.701s). Generated-manual freshness,
  mandoc lint, Python syntax, all 235 relative links in the affected Markdown
  files and git diff --check passed. Supplied assets and generated completion
  adapters have no changes. Native Windows visual verification remains pending.
