# Checkout installation

**Implemented: bounded catalog-backed setup and restore.** Run these entry points from an existing public checkout. They do not bootstrap Python, Bash, Git, applications, or a remote release.

```sh
./install.sh --dry-run
./install.sh
./install.sh --update --yes
./install.sh --with-source nvim
./uninstall.sh --dry-run
./uninstall.sh
```

Once Dots is available, `dots init --setup` and `dots files install` run the same installer. `dots files uninstall` restores installer-owned paths. Plain `dots init [shell]` still emits shell code without installing anything. Shell startup never scans or repairs the installation. Open a new shell after setup to load the installed startup files and PATH integration.

PowerShell provides native parameters and a native adapter:

```powershell
./install.ps1 -DryRun
./install.ps1 -Yes
./install.ps1 -Update -Yes
./install.ps1 -WithSource nvim,windows
./uninstall.ps1 -DryRun
./uninstall.ps1
```

The file controllers require Python 3.9+; complete setup with theme preparation requires Python 3.11+. POSIX setup additionally requires Bash 4.4+ and the existing publisher utilities. Updating or acquiring external sources requires Git; selecting bundled Termux/Windows resources does not. Native Windows invokes Python directly and prepares themes without Bash. Universal and bundled Windows catalogs map app-specific Windows paths; ambiguous and unsupported destinations remain unmapped. See [native PowerShell](powershell.md) for the app inventory, requirements and pending native acceptance.

## Options and output

Install/uninstall accept `-v`/`--verbose`, `--dry-run`, `--yes`, `--json`, `--color=auto|always|never`, `--icons=auto|always|never`, and `--help`. Install additionally accepts `--update` and repeatable `--with-source termux|windows|nvim`. The PowerShell equivalents are `-Verbose`, `-DryRun`, `-Yes`, `-Json`, `-Color`, `-Icons`, `-Update`, and `-WithSource`. Remaining arguments allow the long-option forms as well.

Normal execution displays a plan and requests approval. `--yes` approves that plan without prompting; nonterminal execution otherwise refuses mutation. Dry-run creates no directories, locks, caches, journals or capability probes, and performs no downloads or fetches. Link capability is therefore verified during approved preparation, before live replacement.

Human views use the shared semantic colors, full wrapped paths and explicit statuses. The PowerShell bridge enables terminal presentation when its host advertises virtual-terminal support and no TERM override is set. Delayed spinners and counted phases follow the [presentation contract](presentation.md#operation-progress), including `DOTS_PROGRESS=never`. Git runs with visible stderr so credentials and diagnostics retain the terminal. JSON, dry-run, redirected output and shell-code generation never animate. `--json` produces a schema-1 result containing `action`, `status`, `items`, and, for file setup, `platform` and a completed `transaction` ID when applicable. Diagnostics remain on stderr. Items distinguish planned actions, unchanged/skipped resources, installed/restored targets and preserved drift. Exit 0 means complete/unchanged/cancelled, 1 means failed/blocked/incomplete, and 2 means invalid arguments.

`./install.sh --verbose`, `dots files install -v`, and `dots init --setup -v` show live file actions, recovery copies, retained backup locations/IDs, and unchanged/skipped reasons alongside existing progress. Uninstall supports the same option, as do `./install.ps1 -Verbose` and `./uninstall.ps1 -Verbose`. Verbosity survives `--update` restarting setup. JSON suppresses the extra trace; dry-run uses planned-action labels. See [verbose output](presentation.md#verbose-operations).

## Declared ownership

The existing [file catalog](files.md) is the installation inventory. Missing optional sources, missing resource files and unmapped targets are reported as skipped. No inference from `.gitignore` or arbitrary symlinks is used to choose installation targets. Catalog ownership conflicts, unsupported copy preferences, unrelated links and unsafe parent paths block installation.

Setup links mapped configurations and creates their missing parents. Existing regular files/directories receive verified retained backups before replacement. A validated selection made through the normal theme publisher can be reconciled explicitly by setup; arbitrary changed configuration targets remain protected. Correct pre-existing links remain unchanged and are not claimed by the installer. Sources stay editable in the checkout. The managed command entry lives in the user's `.local/bin`; existing shell integration adds the checkout's command paths to PATH. Setup does not edit the Windows registry or system PATH.

Catalog omissions found in the audit are now explicit: Fish, Nushell, Zsh's login profile, Ruby dotfiles, Blastoff, Git prompt configuration and Starship's file-level destination. Internal completion, palette and Rofi links are relative to their containing directories. Fixed generated connectors are listed in `lib/dots/themes/connectors.tsv`; btop's `dots.theme` is now generated and ignored alongside the existing connectors.

On each platform, setup prepares the selected theme (or `DOTS_THEME_DEFAULT`) using the normal renderer and command generator. It publishes pointers and fixed connectors through the file transaction, without app reloads, wallpaper changes or theme hooks. Required connector parents are created. Codex/Pi retain their existing-directory opt-in boundary. Immutable generated payloads remain in state for recovery; no pruning is automatic.

Fresh checkouts retain `config/fsh` through tracked documentation. Setup links it to `${XDG_CONFIG_HOME:-$HOME/.config}/fsh` and creates its ignored `dots.ini` connector; installing the FSH plugin is not a prerequisite for rendering. Stashed catalog resources remain excluded.

Setup checks generated output completeness as well as input fingerprints. Missing or nonregular required palette, shell, template or connector artifacts cause a new generation to be prepared. A missing managed active pointer is also repaired. The preview names the first incomplete path; dry-run performs no repairs. Existing generations are retained, and failed preparation or publication preserves the prior pointers and installation receipt through the existing rollback mechanism. Foreign pointers and unsafe state still require inspection rather than automatic replacement.

After pulling a repair, run `./install.sh --dry-run`, then `./install.sh` (or `dots init --setup`) and open a new shell. `dots theme refresh` repairs incomplete generated theme data; checkout setup also installs missing catalog links. Plain `dots init` does neither.

Older Vivid releases use [scalar compatibility mode](file-colors.md#vivid-compatibility) during preparation, avoiding the `Color value should be a string` panic from generated font-style lists. Setup displays the compatibility notice once on stderr, including with `--json` (plain diagnostics, unchanged JSON stdout). Failed custom templates identify their source and Vivid version and still block publication without changing the installation receipt. Dry-run does not render themes or execute Vivid version/generation probes.

## Update and optional sources

Ordinary install is local. `--update` requires a clean attached checkout with an explicit upstream and a fast-forward history. It fetches that branch without recursive submodule downloads, refuses changed submodule topology, and never stashes, resets, cleans, rebases or pushes. Initialized applicable public sources advance only to the parent repository's recorded commits; local changes or commits that would be abandoned are refused.

Missing public sources are initialized only with `--with-source`. Secrets and unrelated nested submodules are never initialized. Source updates and file installation are separate observable stages: the updated implementation is loaded and a fresh configuration plan is presented after updating. Without `--yes`, both stages require their own approval. If setup then fails, the completed Git update remains. Dry-run of a source operation reports the source stage using local information; it cannot predict the post-fetch configuration plan.

## Restore and recovery

The installation record is `${XDG_STATE_HOME:-$HOME/.local/state}/dots/installation.json` on POSIX, or `%LOCALAPPDATA%/dots/installation.json` on Windows unless `XDG_STATE_HOME` is set. It is written in the same transaction as the target changes. The first installation baseline and retained backup references survive later reconciliation. Text receipts use the same UTF-8/LF preparation and preserved target permissions as publication, so theme reconciliation remains restorable across different process umasks. A second checkout cannot silently take over the same installation record.

Uninstall restores unchanged installer-owned targets to their pre-install objects, removes links created where no target existed, and prunes only empty installer-created directories. Changed targets are preserved and reported as incomplete. Source edits made through a managed link remain in the checkout. Pre-existing matching links, source repositories, catalogs, generated payloads and recovery records are retained. Uninstall is distinct from `dots files remove`, which still materializes a config copy and removes its catalog entry.

Use `dots files history`, `dots files recover ID`, `dots files undo ID`, and the existing backup commands for transaction inspection and recovery. The native adapter exposes these as `dots.ps1 files ...`. An interrupted file transaction blocks new installation until recovered. POSIX durability uses flushed files and directories; native Windows flushes files and journals but does not claim POSIX directory-fsync or power-loss guarantees. Windows symbolic-link privilege is required; copying, elevation, Developer Mode changes and reparse-point traversal are never automatic.

`dots files check` (also `dots.ps1 files check`) can remove approved catalog entries
whose source paths are absent. This metadata-only cleanup preserves installation
receipts and target objects; it does not uninstall or restore anything. See
[missing-source checks](files.md#check-missing-sources) for review and dry-run options.

## Validation

`python3 -B tools/test_file_platform.py` covers native file flushing, read-only backup metadata, flush-error refusal before replacement, permission-sensitive undo and text preparation under different POSIX umasks. This suite runs in both Linux and Windows installation CI. Machine-local `config/bat/themes/Dots.tmTheme` is ignored rather than shipped as an absolute link; the fresh-checkout test continues to reject escaping links.

`python3 -B tools/test_installation.py` owns all home/config/state/cache roots and local Git remotes. It covers backup/restore, no-op reconciliation, drift, crash recovery, theme preparation, updates and optional-source boundaries. `python3 -B tools/test_installation_adapters.py` covers entry points and native adapter boundaries. On Windows use `python -B`. Linux/Windows CI runs these tests; Windows positive link cases explicitly skip when the runner lacks link capability. Native Termux evidence, Windows CI results and owner-run WSL verification must be reported separately.

## Bundled platform sources

Androidots and Windots are bundled under `profiles/termux` and `profiles/windows`.
Their catalog IDs and legacy `--with-source` selections remain compatible, but
source acquisition no longer fetches either repository. Application installation
still uses managed-file previews, backups and receipts. See
[migration compatibility](profiles.md#androidots-and-windots-migration).

## Bundled application setup

The same root setup scripts and `dots files install/uninstall` manage Anodize, Blastoff and pkgs. Their public scripts inside the bundled directories delegate to this combined lifecycle. The installation receipt includes standalone launchers, POSIX Bash/Zsh completion files and manuals; Fish completion is part of the managed Fish configuration. Native Windows installs PowerShell launchers and uses Dots' native completion adapter. Missing declared payload files block the complete plan.

No old standalone installer or package manager runs during setup/removal. Foreign command links remain protected; replaced regular files retain their first-install baseline. Uninstall preserves application data and drift while restoring unchanged owned targets. See [destinations and migration](bundled-applications.md#one-installation-and-removal).

## Previous application installations

Combined setup installs Anodize, Blastoff and pkgs from `plugins/`. Protected legacy links can be reconciled with `dots files migrate-apps`, which previews by default and applies only with `--yes`. This bounded operation installs application assets without reinstalling other configurations or publishing themes. Backups and original baselines remain available to normal uninstall/undo. See [supported migration layouts](plugins.md#legacy-application-migration).
