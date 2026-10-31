---
name: dots-pkgs-maintenance
description: Maintain the bundled pkgs command family, manager adapters, package selection and completion. Use for dots pkgs or shared standalone implementation, not as permission to install or remove host packages.
---

# Dots Packages Maintenance

Read the plugin's [agent contract](../../../plugins/pkgs/AGENTS.md), [application guide](../../../plugins/pkgs/README.md) and [Dots integration](../../../docs/bundled-applications.md). `plugins/pkgs/pkgs_lib/cli.py` and `grammar.py` own commands; backends/detect own manager selection and arguments, catalog owns package data, and completion/fzf/reports own their distinct interfaces. Standalone `pkgs` and `dots pkgs` use the same core. Termux's `pkg` is a backend frontend, not a new alias.

Keep package identity separate from display labels and pass literal subprocess argument arrays. Preserve selected-manager scope, installed-only uninstall candidates, native confirmation and exact dry-run semantics. Termux never receives sudo. Package-manager effects are not Dots managed-file transactions and have no filesystem rollback guarantee. Tests use mocked managers and owned cache/config roots; never modify host packages to verify a change.

Help/static Dots completion must not run managers or searches. Standalone package candidates retain their existing local behavior; previews may fetch metadata, and opening a URL requires its explicit picker action. Preserve human default output, explicit JSON, inherited FZF preferences and NO_COLOR. Native Windows supports help/version and static discovery; unsupported application actions retain the documented refusal rather than silently invoking WSL.

Use [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu review and [dots-config](../dots-config/SKILL.md) when exposing Dots settings. Retain native application config ownership. [Plugin maintenance](../dots-plugin-maintenance/SKILL.md) owns command/completion/manual installation and migration; application completion management must respect installed Dots links and receipts.

Run affected plugin-local tests plus `tools/test_bundled_apps.py`, `tools/test_bundled_app_cores.py` and `tools/test_plugin_reports.py` where relevant. Check grammar-generated adapters with `python3 -B tools/generate_bundled_apps.py --check`. Verify literal operands, backend flags/scope, confirmation/cancellation, partial errors, exact data and manager-free discovery. Synchronize docs through [documentation maintenance](../dots-documentation-maintenance/SKILL.md); imported standalone release records are historical, not current Dots platform evidence.
