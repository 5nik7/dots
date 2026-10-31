---
name: dots-pkgs-maintenance
description: Maintain the bundled pkgs command family, manager adapters, package selection and completion. Use for dots pkgs or shared standalone implementation, not as permission to install or remove host packages.
---

# Dots Packages Maintenance

Preserve grammar aliases `in`, `un`, `up`, `xup`, `upls` across standalone/Dots
entry points. `upgrade ls` / `upgrade --list` query native candidates without
transactions or recipes, using cached system indexes and bounded language
queries; failures cannot become empty success. Cleanup is an explicit manifest
review: current pip/source and negative system ownership evidence, FZF selection,
separate confirmation, then guard/provenance rechecks and native uninstall.
`--yes` cannot bypass cleanup review; dry-run/JSON only inspect. Keep source trees
and disabled manifest records. Test with fake managers and private terminals.

Default Go upgrades compare installed build versions with native latest-module
queries, then use `go install PACKAGE@latest` only for newer eligible tools.
Do not automatically select `go-global-update` or reinstall current/newer builds.
Preserve source/skip guards, literal build flags and explicit replacement recipes;
name the current tool in compact progress before native output arrives.

Read the plugin's [agent contract](../../../plugins/pkgs/AGENTS.md), [application guide](../../../plugins/pkgs/README.md) and [Dots integration](../../../docs/bundled-applications.md). `plugins/pkgs/pkgs_lib/cli.py` and `grammar.py` own commands; backends/detect own manager selection and arguments, catalog owns package data, and completion/fzf/reports own their distinct interfaces. Standalone `pkgs` and `dots pkgs` use the same core. Termux's `pkg` is a backend frontend, not a new alias.

Keep package identity separate from display labels and pass literal subprocess argument arrays. Preserve selected-manager scope, installed-only uninstall candidates and exact dry-run semantics. Explicit install commands and accepted install-picker selections authorize installation without an extra flag; bare upgrade authorizes unattended user-wide work; refresh authorizes repository metadata updates. Supply supported native confirmation flags automatically. Remove/restore still require approval. Explicit export --update authorizes the guarded merge/write without another flag, preserves manual decisions and backups, and defaults to the active profile root. Ordinary snapshot replacement retains approval; explicit Git publication can include it with --update-packages. Read [package workflows](../../../docs/packages.md) for scope, ownership, recipes, Go metadata and manifest contracts. Policies/scopes/workflows own plans; streams owns output/status; manifests and package_setup own restoration. Termux never receives sudo. Package effects have no Dots filesystem rollback. Tests use mocked managers and owned cache/config roots; never modify host packages to verify a change.

Help/static Dots completion and manifest inspection must not run managers or searches. Standalone package candidates retain their local behavior; previews may fetch metadata, and opening a URL requires its explicit picker action. Preserve human output, JSON, raw bytes, ordinary redirects, inherited FZF preferences and NO_COLOR. Actual human upgrades show compact progress/results with bounded diagnostics and skip counts; raw/redirected output and dry-run retain full detail. Other formatted operations and stdin retain full messages. The formatter never infers process status. Restore child terminal settings and preserve prompts/interruption. Native Windows uses the WinGet community backend with a structured PowerShell bridge, exact IDs, user scope by default and explicit machine scope. Preserve disabled reasons for ambiguous/unmatched installed entries; never parse localized tables. Native pickers use shared selectors without Bash. Source agreements, providers, repository trust, elevation and reboot must not be implied. WinGet completion is cache-only; never query remote sources during completion. Setup alone can offer the pinned current-user module prerequisite through its explicit preparation approval.

Use [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu review and [dots-config](../dots-config/SKILL.md) when exposing Dots settings. Retain native application config ownership. [Plugin maintenance](../dots-plugin-maintenance/SKILL.md) owns command/completion/manual installation and migration; application completion management must respect installed Dots links and receipts.

Run affected plugin-local tests plus `tools/test_pkgs_integration.py`, `tools/test_bundled_apps.py`, `tools/test_bundled_app_cores.py` and `tools/test_plugin_reports.py` where relevant. Check grammar-generated adapters with `python3 -B tools/generate_bundled_apps.py --check`. Verify literal operands, backend flags/scope, confirmation/cancellation, partial errors, exact data and manager-free discovery. Synchronize docs through [documentation maintenance](../dots-documentation-maintenance/SKILL.md); imported standalone release records are historical, not current Dots platform evidence.
