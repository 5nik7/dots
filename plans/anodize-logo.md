# Anodize terminal branding

**Status: Implemented, 2026-10-13.**

## Accepted behavior

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
