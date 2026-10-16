# Bounded checkout installation

**Status: Implemented and verified in isolated native Termux fixtures; Linux/Windows CI added, native Windows and WSL execution not yet verified.** This owner-requested slice adds checkout-local setup, update and restore without resuming the Go migration or general module/profile installation. The behavioral source of truth is [checkout installation](../docs/installation.md).

- [x] Audit tracked/ignored links and catalog omissions; repair absolute internal links.
- [x] Add explicit `dots init --setup`, `dots files install/uninstall`, and root shell/PowerShell entry points.
- [x] Share native filesystem primitives and the existing transaction engine; retain original backups and installation ownership across updates.
- [x] Reuse theme rendering with inactive preparation and transaction-owned publication; suppress reloads, hooks and wallpaper actions during setup.
- [x] Add explicit fast-forward updating and named public-source downloads without recursive/private initialization.
- [x] Complete focused lifecycle, adapter, shell, theme, catalog, presentation and documentation checks; record native verification limits.

The [presentation acceptance gate](../docs/presentation.md#acceptance-gate) applies to help, preview, unchanged/empty results, conflicts, successful setup, drift-preserving uninstall and recovery. Review 40/80/120-column terminals, forced/disabled colors, ASCII icons, JSON, dry-run and redirected output. Reuse the existing delayed progress renderers and optional Gum confirmation with a plain fallback.

Native Windows initially maps the current PowerShell profile, Neovim and VS Code settings. Unmapped Windots applications and native theme publication are explicitly deferred. WSL and Windows retain separate paths and state. Runtime dependencies must already be installed. No live activation, commit or publication is included in implementation verification.

## Verification evidence

- Installation lifecycle: 16 cases passed, including real theme generation, original backups across local Git updates, ignored-file preservation, source drift, interrupted recovery and explicit optional-source initialization. A focused follow-up also proves normal theme switching followed by setup reconciliation preserves the selected theme and original baseline.
- Adapter/presentation suite: five checks passed; native PowerShell and Windows execution checks skipped because those runtimes are unavailable here. Owned PTYs cover 40/80/120 columns and delayed progress; forced-color JSON and ordinary shell-code output stay undecorated.
- Existing regressions: file operations 21 passed, catalog 9 passed, Bash dispatcher 24 passed, progress 11 passed. Focused shell initialization had six passes, one unavailable-PowerShell skip and one baseline fixture failure.
- Broader themes: 30 of 32 checks passed. The Zsh/Vivid fallback check fails and the all-native-family Neovim check exceeds its 40-second timeout. Both, plus the shell-loader fixture failure, reproduce when the changed shared libraries are restored from HEAD inside disposable fixtures. They remain outside this installation change.
- Command metadata validation, shell/Python parsing, focused ShellCheck, Markdown links and Git whitespace checks passed. No live install, uninstall, source update, theme publication, commit or push was performed.
