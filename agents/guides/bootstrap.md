# Checkout Setup Work Guide

Read this guide before changing checkout-local installation, update, uninstall or source selection. The implemented contract is [checkout installation](../../docs/installation.md).

## Entry Points and Ownership

The root `install.sh`, `uninstall.sh`, `install.ps1` and `uninstall.ps1` scripts delegate to shared Python controllers. They operate from an existing checkout with installed runtimes; no hosted release downloader or package bootstrap is provided. Bash and native PowerShell must expose the same options and preserve machine-readable output.

Setup resolves catalog resources, previews changes and uses the file Store for installation and receipts. Theme setup prepares inactive generations and publishes them transactionally. Preserve the first-install baseline across updates, pre-existing-link nonownership and drift-aware uninstall.

## Safety

- Inspect existing ownership before replacing any destination.
- Never force-reset, clean, stash or discard an existing repository.
- Keep source updates, configuration installation and optional reloads explicit.
- Never recursively initialize all submodules or request private credentials by default.
- Do not install missing runtimes or packages silently.
- Never silently fall back from linking to copying.
- Preserve backups and receipts for interrupted recovery and uninstall.
- Do not translate Windows and WSL paths or share their state stores.

Termux does not imply `sudo`, systemd, `/usr/local/bin` or GNU utilities. Native Windows must work without Bash or WSL and must report unavailable link capabilities without changing system policy.

## Verification

Use disposable homes, repositories, config, state and cache roots. Run `python3 -B tools/test_file_platform.py`, `python3 -B tools/test_installation.py` and `python3 -B tools/test_installation_adapters.py` (`python` on Windows). Cover first install, repeated install, update, pre-existing unrelated destinations, drift, interrupted operations, read-only source files, missing optional sources and paths containing spaces. Record actual native evidence separately from injected platform fixtures.

Update `docs/installation.md`, `docs/platforms.md`, `docs/safety.md`, `docs/testing.md`, README and the focused plan when behavior changes.

## Selective setup

Maintain the shared wizard and preparation coordinator together across root scripts, Files and init --setup. Keep dry-run pure, Save choices opt-in, separate preparation/final approval, stop-on-first-failure and receipt baselines. Test managed-directory child translation without relaxing general parent-link checks. Run the selective setup suites listed in [testing](../../docs/testing.md#selective-setup-and-winget); record unavailable real build/native acceptance explicitly.
