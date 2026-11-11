# Checkout Setup Work Guide

Read this guide before changing checkout-local installation, update, uninstall or source selection. The implemented contract is [checkout installation](../../docs/installation.md).

## Entry Points and Ownership

The root `install.sh`, `uninstall.sh`, `install.ps1` and `uninstall.ps1` scripts delegate to shared Python controllers. Standalone `bootstrap.sh` and `bootstrap.ps1` can acquire a checkout and explicitly prepare required runtimes before delegation. Installers delegate when Python is missing/old or bootstrap is requested. Existing checkouts are reused without updates. Bash and native PowerShell expose matching options and preserve machine-readable output.

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

Termux does not imply `sudo`, systemd, `/usr/local/bin` or GNU utilities. Native Windows works without Bash or WSL. Bootstrap may offer Developer Mode with separate explicit approval and UAC; ordinary `--yes` does not authorize that policy change. Official Git/Python fallback installers require verification before execution. Shared setup never silently changes policy.

New setup backups compose into `files/backup_catalog.py`, protecting the first
uninstall baseline. Reviewed replacement retains later edited destinations as
additional backups. `--no-backup` discards only the newly replaced original after
successful commit, preserving temporary rollback and existing retained baselines.
Selected Anodize builds use owned caches; Starship palette publication coordinates
with Blastoff writers. Keep shell startup free of prerequisite acquisition.

## Verification

Use disposable homes, repositories, config, state and cache roots. Run `python3 -B tools/test_file_platform.py`, `python3 -B tools/test_installation.py` and `python3 -B tools/test_installation_adapters.py` (`python` on Windows). Cover first install, repeated install, update, pre-existing unrelated destinations, drift, interrupted operations, read-only source files, missing optional sources and paths containing spaces. Record actual native evidence separately from injected platform fixtures.

Update `docs/installation.md`, `docs/platforms.md`, `docs/safety.md`, `docs/testing.md`, README and the focused plan when behavior changes.

## Selective setup

Maintain the shared wizard and preparation coordinator together across root scripts, Files and init --setup. Keep dry-run pure, Save choices opt-in, separate preparation/final approval, stop-on-first-failure and receipt baselines. Test managed-directory child translation without relaxing general parent-link checks. Run the selective setup suites listed in [testing](../../docs/testing.md#selective-setup-and-winget); record unavailable real build/native acceptance explicitly.

For each new command/script, audit bootstrap and core publication of its wrappers, completions and preference inputs. Core already exposes the checkout command directory and `lib/dots` adapters; do not add redundant acquisition steps for repository-local features. Record add/update/no-change reasoning in the focused plan and make fresh-machine setup discoverable in README.
