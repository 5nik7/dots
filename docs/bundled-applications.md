# Blastoff and pkgs

Blastoff and pkgs are first-party application plugins under `plugins/` in Dots. A Dots checkout contains their Python implementations, shell adapters, completion files, manuals and application tests; neither command depends on a separate checkout or submodule. The import versions and original commits are recorded in [the source provenance manifest](../plugins/manifest.json). All tracked source files are retained, including reference assets and historical project workflow files. Git internals and untracked machine-local files are excluded. The original repositories are retained and are not updated or deleted by Dots.

## Commands

Both forms use the same application core and preserve arguments, output, exit status and subcommands:

```sh
blastoff --help
dots blastoff --help
blastoff theme list
dots blastoff theme list
blastoff --dry-run theme apply local:dots
dots blastoff --dry-run theme apply local:dots

pkgs --help
dots pkgs --help
pkgs install --manager npm --global typescript --dry-run
dots pkgs install --manager npm --global typescript --dry-run
```

Before installation, use `./bin/blastoff`, `./bin/pkgs` or `./bin/dots` from the Dots checkout. On PowerShell, use `./bin/blastoff.ps1`, `./bin/pkgs.ps1` or `./bin/dots.ps1`.

Blastoff manages Starship themes, modules, backups and active configuration. It requires Python 3.11+; Starship and interactive picker tools are capability-checked when needed. Its [application command contract](../plugins/blastoff/docs/CLI-CONTRACT.md#commands-and-aliases) describes the existing subcommands. `STARSHIP_CONFIG` selects the active configuration, otherwise `~/.config/starship.toml`; `BLASTOFF_HOME` selects storage, otherwise `~/.config/blastoff`. Absorption does not move either location or apply a theme. Existing active-file and storage-root symlink safeguards remain in the application core.

pkgs provides package browsing, install/remove, unattended user-wide upgrades, Go tools, configurable recipes/skips, stream formatting, manifest export/inspection/restore and diagnostics. It requires Python 3.9+ and Termux/Linux/WSL for package operations. Install/remove/restore retain approval; bare upgrade authorizes unattended execution. See [package workflows](packages.md) for scopes, output, configuration and manifests. Its [application guide](../plugins/pkgs/README.md) explains these workflows. `pkgs uninstall NAME` removes selected packages; Dots checkout uninstall removes the installed application entry points and restores managed configuration. These are separate operations.

Native Windows has Blastoff dispatch through the shared Python core, without Bash. Dots reuses Blastoff's native argument transport, preserving its `-help`/`-list`/`-theme` compatibility aliases and picker shell context. pkgs help/version, static discovery, `format` and `manifest` are available, but package operations return status 3 with an explanation that native Windows backends are not implemented. Use a separate WSL installation for those operations; Dots never translates paths or launches WSL automatically. Native PowerShell 5.1/7 and WSL runtime acceptance for this integration remain pending.

## One installation and removal

Use the [Dots setup scripts](installation.md) for the complete installation:

```sh
./install.sh --dry-run
./install.sh
./uninstall.sh --dry-run
./uninstall.sh
```

PowerShell uses `./install.ps1 -DryRun` and `./uninstall.ps1 -DryRun`, then the same scripts without `-DryRun` to review and approve changes. The public scripts under `plugins/blastoff/` and `plugins/pkgs/` delegate to this combined lifecycle and accept Dots setup options. Old standalone `--prefix` options are not Dots setup options. Required setup runtimes must already be installed. Default setup installs no packages; explicit `--packages FILE` restores declared packages before configuration, without inventing prerequisites. Native Windows refuses the package stage.

| Asset | POSIX destination | Native Windows destination |
| --- | --- | --- |
| Commands | `~/.local/bin/blastoff`, `~/.local/bin/pkgs` | `~/.local/bin/blastoff.ps1`, `~/.local/bin/pkgs.ps1` |
| Bash completion | `${XDG_DATA_HOME:-~/.local/share}/bash-completion/completions/NAME` | Not applicable |
| Zsh completion | `${XDG_DATA_HOME:-~/.local/share}/zsh/site-functions/_NAME` | Not applicable |
| Fish completion | Existing managed Fish configuration, `completions/NAME.fish` | Not applicable |
| Manuals | `~/.local/share/man/man1/NAME.1` | Included in source; no native man installation |
| PowerShell completion | Dots PowerShell completion adapter | Dots PowerShell completion adapter |

Open a new Dots shell after setup for PATH/completion integration. Bash and Zsh use the existing user-local directory discovery; Fish autoloads the shipped completions. PowerShell registers the standalone names alongside the Dots routes during normal Dots initialization. On a shell configured independently of Dots, add `~/.local/bin` to PATH and configure the shell's completion loader as needed. If man does not discover the user-local directory, use `man -M ~/.local/share/man blastoff` (or `pkgs`).

`pkgs completion SHELL status` reports the linked completion content, including Fish autoloading. The application's completion install/update/uninstall commands preserve links to bundled Dots source and direct you to Dots setup or a separate `--directory`; they do not bypass the Dots receipt.

Command links, Bash/Zsh completion links and manuals share `installation.json`, preflight, retained backups, rollback and drift-aware uninstall with the rest of Dots. Fish completion belongs to the existing Fish catalog mapping. Correct pre-existing links stay unowned. A foreign symlink blocks setup; regular files are previewed for replacement with backup. Use `dots files migrate-apps` to inspect and explicitly migrate supported legacy installations with retained backups. Dots does not infer ownership from a command name; see [application migration](plugins.md#legacy-application-migration).

Uninstall retains source repositories and application data, including Blastoff themes/backups and pkgs configuration/cache. It restores the pre-install baseline of installer-owned configuration targets under the usual Dots contract. It never runs a package-manager removal or the old standalone uninstallers.

## Discovery, completion and maintenance

`dots help blastoff`, `dots help pkgs`, `dots commands`, shell completion and the generated command reference use inert metadata generated from the bundled grammars. `dots blastoff ... --help` and `dots pkgs ... --help` use the applications' own help. Dots-prefixed completion provides subcommands, flags, enumerated values and declared file operands without running applications or package managers. Standalone Bash/Zsh/Fish completion retains each application's existing local-name and package candidate behavior.

Application output retains its existing visual and data contracts. Pass application color options after `blastoff` or `pkgs`; Dots prefix presentation options style Dots-owned metadata views. No wrapper decorates JSON, generated completion code or forwarded streams.

Regenerate metadata with `python3 -B tools/generate_bundled_apps.py`; use `--check` for verification. Run the [bundled integration checks](testing.md#bundled-applications). The imported standalone release checksums, packaging/install helpers and historical device reports are provenance for those releases, not proof of the Dots lifecycle. Public Dots setup does not execute those legacy helpers. Any future standalone release would need its own reviewed packaging and lifecycle work.

The shared layout, migration workflow and popup menus are documented in [application plugins](plugins.md).
