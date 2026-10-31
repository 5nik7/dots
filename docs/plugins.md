# Application plugins

Anodize, Blastoff and pkgs are first-party application plugins in `plugins/`. They install together with Dots and use the same standalone and Dots-prefixed commands. Plugins are source modules within the checkout, not separately downloaded distributions or an enable/disable system. This directory is distinct from theme hooks and editor plugins.

## Ownership and portability

Each application owns its runtime, assets, completion sources, manual and core tests. Anodize's independent Go module lives in `plugins/anodize/engine`; its Python application adapter lives alongside that engine. Shared menus, presentation, catalogs and installation transactions remain Dots services. Dots integration tests and stable build/test entry points remain under `tools/`.

The [manifest](../plugins/manifest.json) declares installed assets, runtime requirements, platform support and source provenance. Paths are relative to the selected plugin, with no parent traversal or absolute destinations. Setup validates the declaration and required files before applying changes. Generated launchers and metadata resolve the selected checkout directly; dispatch, help and shell startup do not scan plugins or run package backends.

`anodize`, `blastoff`, `pkgs` and their `dots` command families retain their arguments, output, exit codes and documented environment overrides. Shell adapters remain under `bin/`. Code resolution follows the checkout; application configuration and data retain their existing locations. Moving source does not move or activate themes. Use the normal setup/migration lifecycle to install links from a new checkout; an existing installation receipt still protects its owning checkout.

Root and application public install/uninstall scripts use the combined Dots lifecycle. All three applications receive user-local launchers, Bash/Zsh completions and POSIX manuals; Fish uses the managed shell configuration and PowerShell uses its native completion adapter. Native Windows pkgs supports help/version, `format` and `manifest`; package operations remain unavailable. Anodize's existing offline build command remains `python3 -B tools/verify_anodize.py build`; ordinary setup installs no runtime or manager. Optional `--packages FILE` restores only the declared packages before configuration; existing setup runtimes are still prerequisites.

## Legacy application migration

Inspect a previous application installation with:

```sh
dots files migrate-apps
dots files migrate-apps --json
dots files migrate-apps --yes --dry-run
dots files migrate-apps --yes
```

The canonical space-separated route is `dots files migrate apps`; `migrate-apps` is an equivalent convenience spelling. Both shell frontends use the same controller. Without `--yes`, this command only previews, including on an interactive terminal. `--dry-run` always prevents writes.

Discovery is bounded to known standalone layouts under the user-local prefix, the native Termux prefix, and `/usr/local` on Linux/WSL. It reads Blastoff installation receipts, pkgs release checksums and completion ownership records. It does not execute legacy uninstallers, scan arbitrary filesystem trees, launch package managers, acquire elevated privileges or infer ownership from a filename alone. Native Windows plugin installation is supported; retirement of former PowerShell module/profile installations requires manual reconciliation and native acceptance.

The preview distinguishes verified legacy artifacts, current Dots assets, conflicts and retained files. Receipt paths are constrained to supported installer destinations. File hashes and guarded inputs bind the proposed changes. Supported historical pkgs README hashes are recorded separately from current application source. Edited or unsupported receipts and changed owned files block application before any replacement.

Migration installs only application assets and retires verified obsolete launchers, manuals, completions and payloads. It does not apply the full configuration catalog or republish themes. It reconciles obsolete completion ownership when an exact link already points to Dots. Unrecorded payloads, existing installation backups and edit-recovery files remain in place and are reported. User configuration, themes, application backups, package databases and caches are not removed.

All changes use the existing installation receipt, durable journals and retained backups. A failure rolls back completed reversible operations. Repeat migration is unchanged. Normal Dots uninstall restores the pre-migration baseline, including legacy artifacts, unless a target has changed since migration; drift is preserved. Use `dots files history`, `dots files undo ID` and `dots files recover ID` for the existing inspection/recovery workflows. Retained backups are not automatically pruned.

## Menus and maintenance

`dots menu blastoff` and `dots menu pkgs` open application families directly; both also appear in `dots menu`. Blastoff provides its theme picker, current/list views, edit/save, module browser, backups and diagnostics. pkgs provides search, installation/removal, installed packages, upgrade/refresh, export, manifest inspection/restore, configuration, managers and diagnostics. Both include help. Advanced subcommands remain available through the CLI.

Menus reuse Dots navigation, semantic presentation and terminal handoff. Reports remain scrollable; editors and package workflows retain their normal terminal and confirmations. Opening a family or a preview never approves an operation. Package upgrade/export/restore first show a successful dry-run review and a default-Cancel Run choice; only explicit Run supplies `--yes`. Opening the menu or preview grants no approval. No menu adds `--force`. Back exits a directly opened family, or returns to its parent when opened from the main menu. Missing tools have useful plain fallbacks; native Windows marks unsupported package workflows unavailable.

The current/theme-list/save/backup-list/doctor views in Blastoff and list/managers/doctor views in pkgs use the same [Dots report formatting](presentation.md#application-reports) in popups and direct terminal commands. Disabling color preserves the layout. JSON/raw output and ordinary redirected formats stay unchanged. These source changes take effect on the next invocation; no theme activation, migration or tmux reload is required.

For a new or changed command, record whether a menu should be added, updated or left unchanged, with a reason. Keep assessment in the focused plan or change notes, not in runtime discovery. Use [plugin maintenance](../.codex/skills/dots-plugin-maintenance/SKILL.md) for integration and [menu authoring](../.codex/skills/dots-menu-authoring/SKILL.md) for popup behavior. Application grammar remains the source for command metadata; the manifest owns installation assets, not a second subcommand list.

Run the [plugin and migration checks](testing.md#application-plugins) and refresh canonical docs and the generated wiki together. Local fixtures do not establish native Windows or WSL acceptance.
