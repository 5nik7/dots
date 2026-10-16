# Anodize terminal branding

**Status: Implemented, 2026-10-13.**

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
