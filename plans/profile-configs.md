# Profile configuration

**Status: Implemented; native acceptance limits recorded below.** Goal `profile-configs` (`765a9e892a1547cd994aad89c7132f87`).

## Scope and design

Use the existing inheritance resolver and each profile's `profile.json` for literal environment declarations, validated Dots settings and repository-scoped file mappings. The follow-up [profile backend plan](profile-backend.md) makes `.dots/files.json` the permanent ID/platform registry; profile `files` maps repository IDs to complete resource lists, using the existing resource schema and source ownership. The most specific list wins. File editors save into the active profile without changing another platform's defaults. Legacy catalogs remain readable for independent sources and older fixture checkouts.

Add `dots config list|get|set|unset|path|check|migrate`, with explicit `--profile`, JSON inspection, literal values, preview and guarded transactions. Settings preserve explicit environment precedence. Environment declarations never execute code. Saved values do not reload running shells or install resources. File installation, update, undo and recovery continue through the existing Store.

Move configuration under the legacy Dots config directory into the active profile, excluding `themes` and runtime state. Incorporate `config.env` and file backup preferences into `profile.json`; retain format-specific files such as `file-colors.toml`, `git.conf`, `theme-plugins.json`, hooks and per-theme file colors beside it. Migration previews first, refuses conflicts/unsafe objects, retains recovery copies, and never publishes a theme or runs hooks. The owner explicitly requested this live migration. Existing unrelated checkout edits remain intact.

## Implementation and acceptance

- [x] Shared profile configuration validation, selection, inheritance and path resolution.
- [x] File catalog readers, editors, installation guards and profile inspection.
- [x] CLI metadata/completion and Bash/native PowerShell controller parity.
- [x] Settings in every shell adapter, preserving cached warm startup.
- [x] Git, theme plugins, file colors and file preference consumers.
- [x] Isolated migration, idempotence, stale preview, rollback/undo and secret refusal tests.
- [x] Focused existing profile, shell, file, theme, Git and native controller regressions; startup measurements where affected.
- [x] Canonical documentation, relative links, command validation and generated wiki.
- [x] Reviewed live migration and recorded recovery transaction; goal evidence before completion.

Presentation uses the shared Python renderer for human help/list/result/error views, readable plain output and exact scalar/JSON modes. Review 40/80/120 columns, color/icon controls and safe display of Unicode/controls. The [presentation gate](../docs/presentation.md#acceptance-gate) applies. The original slice used direct CLI workflows. The later [configuration popup](config-popup.md) adds browsing and per-change review; direct edits, migration and existing file/theme workflows remain available.

Both Bash and native PowerShell dispatch to shared Python. Windows configuration belongs in `profiles/windows`; WSL remains separate. Existing Windows app destination tokens are unchanged. Native Windows PowerShell 5.1/7, Linux and WSL shell/terminal acceptance remain named pending checks when unavailable; Termux tests and fixtures do not establish native acceptance.

Explicit regular-file `copy` installation now uses the same retained baselines and guarded updates as links. The copy lifecycle test covers repeat installation, source updates, target drift and uninstall restoration. Directory copies remain unsupported; existing link/edit menus keep their link semantics, so no menu route changes are needed.

## Verification evidence

Termux verification on 2026-10-29:

- Configuration suite: 10 tests passed, including owned PTYs at 40/80/120 columns, redacted machine output, stale previews, injected migration rollback, undo drift and copy lifecycle. Bash/Zsh/Fish setting readers and the Xonsh Python reader resolve the profile configuration path; native-controller CLI parity passed. Profile bundle invalidation and Python-free warm Bash/Zsh/Fish startup passed.
- Related passes: file platform 5, file catalog 9, file operations 22, mappings 29, file check 16, repair 48, profiles 13 plus the added startup invalidation case, profile debug 16 (one skip), shell environment 11, file colors 11, Git operations 27, native Git 24, native CLI 17 (one skip), Bash CLI 24. Focused project-registration/menu cases also passed.
- The installation suite passed 26/27; its existing fresh-checkout WSL theme-repeat case still reports `complete` instead of `unchanged`. Broader shell startup had two assertion failures, both reproduced against the pre-task source snapshot, plus five unavailable-Xonsh launcher errors. PowerShell initialization has 24 unavailable-runtime skips. These do not establish native Windows, Linux, WSL, Nushell or Xonsh execution acceptance.
- Theme plugins passed 20/21; the remaining test's ten-second cold-publication deadline failed in the full run and alone. A bounded comparison against the pre-task snapshot measured hook start at 24.89 seconds before and 13.90 seconds after; the committed-publication marker, competing publisher/plugin refusal, read-only inspection and eventual hook completion assertions passed for both. This is timing-limited evidence, not a claim that the full suite passed or publication became faster.
- Sequential startup measurements used separate owned fixtures, one cold run and five measured warm samples after warmup. Bash cold/warm median was 637.7/64.3 ms before and 801.9/68.5 ms after; Zsh was 682.9/64.5 ms before and 726.2/61.5 ms after. Cold compilation now includes profile setting validation and literals. Shared-device load makes single cold samples and small warm differences exploratory; no performance improvement is claimed. The separate warm-path tests prove Python is not launched. Timing and bounded plugin checks are retained in `/data/data/com.termux/files/usr/tmp/dots-profile-performance-xwmlb4fc/results.json`.
- The legacy shell-environment fixture initially wrote its config.env sample into the checkout's Linux profile because it followed the newly resolved configuration path. The run was stopped, the profile was restored to its intended JSON, and the fixture now explicitly selects its owned legacy settings file. The corrected suite passed; subsequent writes stayed inside fixture roots.
- Live migration transaction `788862fbf9a64ab6994680b1419a783e` moved `file-colors.toml`, `git.conf` and `theme-plugins.json` into `profiles/termux`. SHA-256 comparisons matched every source/destination pair, the complete `themes` tree metadata was unchanged, consumer paths resolved to the profile, and repeat migration had zero operations. Recovery remains available with `dots files undo 788862fbf9a64ab6994680b1419a783e`.
- Final source checks passed: 211 command definitions, all four profile checks, 1036 relative links in 137 documents, Python AST parsing, Bash/Fish syntax, ShellCheck for the config wrappers/reader, and `git diff --check`. Wiki build transactions `8c43c5cbb7b841b1a06f683f4543a4dd` and `253d53977e4b4be18b7d5a24343e3a91` refreshed the local export; the second incorporated concurrent Todo metadata changes, and `dots wiki check --json` returned `healthy: true`. No documentation is deferred. No commit, push, shell reload or theme publication was performed.

Retained local evidence: `/data/data/com.termux/files/usr/tmp/dots-profile-regressions-0y6hiicw`, `/data/data/com.termux/files/usr/tmp/dots-profile-regressions-final-pmb1ysfq`, `/data/data/com.termux/files/usr/tmp/dots-profile-shell-baseline-d7mqg4zc/result.log`, and `/data/data/com.termux/files/usr/tmp/dots-profile-migration-1q0ebefr`. The pre-task diff/status snapshot remains at `/data/data/com.termux/files/usr/tmp/dots-profile-config-baseline-qzpz02f6`.
