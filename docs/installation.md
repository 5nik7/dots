# Checkout installation

Setup includes the standalone `todo` command (`todo.ps1` on native Windows) and the catalog-managed `dots:todo-skill`, `dots:todo-planning-skill` and `dots:todo-maintenance-skill` resources. They use the existing backup, receipt, idempotence and uninstall rules. Project and global goal documents are user data, remain outside the installation receipt, and survive uninstall. See [todo](todo.md) for scopes and the separate goal transaction history.

**Implemented: bounded catalog-backed setup and restore.** Run these entry points from an existing public checkout. Python must already be installed. Optional preparation can install explicitly selected packages and mapped prerequisites through an existing manager; it does not bootstrap package managers or download a Dots release.

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

Install/uninstall accept `-v`/`--verbose`, `--dry-run`, `--yes`, `--json`, `--color=auto|always|never`, `--icons=auto|always|never`, and `--help`. Install additionally accepts `--update`, repeatable `--with-source termux|windows|nvim`, and optional `--packages FILE` for the [package-first stage](packages.md#optional-setup-stage). The PowerShell equivalents are `-Verbose`, `-DryRun`, `-Yes`, `-Json`, `-Color`, `-Icons`, `-Update`, `-WithSource`, and `-Packages FILE`. Remaining arguments allow the long-option forms as well.

A terminal invocation opens the shared setup wizard by default. It clears the visible screen once (preserving scrollback), shows `logo.txt` with the available semantic palette gradient, and offers component and individual file/package/font choices. Preparation and final managed publication have separate reviews. `--yes` approves that plan without prompting; nonterminal execution otherwise refuses mutation. Dry-run creates no directories, locks, caches, journals or capability probes, and performs no downloads or fetches. Link capability is therefore verified during approved preparation, before live replacement.

Human views use the shared semantic colors, full wrapped paths and explicit statuses. The PowerShell bridge enables terminal presentation when its host advertises virtual-terminal support and no TERM override is set. Delayed spinners and counted phases follow the [presentation contract](presentation.md#operation-progress), including `DOTS_PROGRESS=never`. Git runs with visible stderr so credentials and diagnostics retain the terminal. JSON, dry-run, redirected output and shell-code generation never animate. `--json` produces a schema-1 result containing `action`, `status`, `items`, and, for file setup, `platform` and a completed `transaction` ID when applicable. Diagnostics remain on stderr. Items distinguish planned actions, unchanged/skipped resources, installed/restored targets and preserved drift. Exit 0 means complete/unchanged/cancelled, 1 means failed/blocked/incomplete, and 2 means invalid arguments.

`./install.sh --verbose`, `dots files install -v`, and `dots init --setup -v` show live file actions, recovery copies, retained backup locations/IDs, and unchanged/skipped reasons alongside existing progress. Uninstall supports the same option, as do `./install.ps1 -Verbose` and `./uninstall.ps1 -Verbose`. Verbosity survives `--update` restarting setup. JSON suppresses the extra trace; dry-run uses planned-action labels. See [verbose output](presentation.md#verbose-operations).

## Component selection and preferences

The wizard shows `Profile    termux (~/dots/profiles/termux)`: a blue label, bold yellow active profile ID, and parenthesized directory in dim terminal foreground. It abbreviates the directory's home prefix as `~` and wraps long values without dropping the path. Its introductory instruction uses shared green styling and the Setup preferences heading uses shared cyan styling; disabled color retains the same text.

The default components are `core`, `files`, `themes`, `anodize`, `blastoff` and `pkgs`. Optional components are `packages`, `fonts` and `leaf`. Repeated `--component NAME` replaces defaults; repeated `--resource ID` implies Files and narrows it to enabled applicable catalog IDs without changing their link/copy strategy. Excluding an installed component does not remove it. Use selective uninstall to restore its owned paths.

`--interactive` explicitly requests the wizard; it conflicts with `--yes`, `--json` and `--dry-run`. `--non-interactive` skips it and requires `--yes` to write. Help, dry-run, JSON and redirected output never show the wizard, clear the screen or display branding. `--no-clear` and `--no-logo` disable those entry effects. Optional Gum uses the shared selector; numbered selection remains available.

Packages reads the active profile's `packages.json`; `--packages FILE` selects a different manifest and implies Packages. Fonts reads the active profile's `fonts.json`; `--fonts FILE` implies Fonts and repeated `--font-target TARGET` narrows its saved selections. Missing profile documents mean an empty selection. The wizard also offers retained font faces. It does not reload applications.

Save choices is unchecked initially. `--save-choices` (or that wizard toggle) saves successful component/resource/dependency choices through `apps.setup`, packages through the active profile manifest, and font preferences through Fonts. Run-only selections do not replace those documents. `apps.setup.logo`, `clear_screen`, `components`, `resources` and `dependencies` activate on the next setup invocation; `resources: []` means all applicable files. Shared semantic styles and progress settings remain authoritative.

Native PowerShell exposes `-Interactive`, `-NonInteractive`, `-Component NAME,...`, `-Resource ID,...`, `-WithDependencies`, `-SaveChoices`, `-NoClear`, `-NoLogo`, `-Fonts FILE` and `-FontTarget TARGET,...`. Install and Uninstall actions under the Files menu open these same terminal workflows without implicit approval.

## Preparation and final publication

Read-only preflight checks destination ownership and selected inputs first. `--with-dependencies` offers mapped missing prerequisites through an already installed manager. The standalone bootstrap can prepare Python and Git explicitly before this shared phase. Unmapped prerequisites, missing managers, native Rust toolchain/Clippy setup and Python fontTools environment selection require explicit installation outside the shared phase. No provider bootstrap, repository registration, trust change or elevation is implicit.

After preparation approval, setup processes prerequisites, packages, the optional pinned Leaf build, inactive theme generation and staged font payloads. It stops at the first failure. Completed package/module/build effects remain; they are never undone by file rollback. Stage records live in `state/dots/setup-runs/` and their writes have Store journals. The final review shows the exact combined file/theme/Leaf/font/preference writes. `--yes` approves the declared preparation and publication stages in batch mode. Changed input guards or conflicting writes stop publication.

Leaf uses the [pinned source and patch](leaf-build.md), owned cache storage and locked Rust tests, Clippy, release compilation and consumer checks. Only a verified artifact is published to the user command directory. Installer integration has isolated fixture coverage; the outstanding real Termux build and consumer checks are [tracked separately](../plans/installer-update.md#deferred-real-leaf-verification). Fonts uses exact saved versions/hashes/faces and its existing native registration planner. Font libraries and registrations remain after installer removal; installer-owned app font settings are restored when unchanged.

An expected `.termux` directory symlink is resolved only when it matches the enabled effective catalog mapping. Child writes use the physical managed source with guards for the lexical link and catalog. Older lexical child receipts retain their original backup references when reconciled. Foreign, broken, changed and nested directory links remain protected. The earlier `symlinked parent requires manual review: .../.termux` error came from the general parent-link guard, which could not recognize this specific managed mapping.

## Declared ownership

The existing [file catalog](files.md) is the installation inventory. Missing optional sources, missing resource files and unmapped targets are reported as skipped. No inference from `.gitignore` or arbitrary symlinks is used to choose installation targets. Catalog ownership conflicts, directory copy preferences and unsafe parent paths block installation. Reviewed foreign leaf destinations are backed up before replacement. An explicit `strategy: "copy"` installs a regular file through the same receipts and retained backups; there is no silent link fallback.

Setup links mapped configurations by default and creates their missing parents. Reviewed installation can replace edited files, directories and foreign links after retaining their current objects. Repeating an unchanged install is a no-op. Existing regular files/directories receive verified retained backups before replacement. A validated selection made through the normal theme publisher can be reconciled explicitly by setup; reviewed edited destinations retain both their edited content and the first uninstall baseline. Correct pre-existing links remain unchanged and are not claimed by the installer. Sources stay editable in the checkout. The managed command entry lives in the user's `.local/bin`; existing shell integration adds the checkout's command paths to PATH. Core setup does not edit the Windows registry or system PATH. The optional Fonts component uses its existing transactional current-user font registrations.

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

Use `dots files history`, `dots files recover ID`, `dots files undo ID`, and `dots bak list` for transaction inspection and recovery. The native adapter exposes these as `dots.ps1 files ...`. An interrupted file transaction blocks new installation until recovered. POSIX durability uses flushed files and directories; native Windows flushes files and journals but does not claim POSIX directory-fsync or power-loss guarantees. Windows symbolic-link privilege is required; copying, elevation, Developer Mode changes and reparse-point traversal are never automatic.

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

No old standalone installer runs. Ordinary setup/removal runs no package manager; explicit `--packages FILE` installation previews and restores the declared packages before applying configuration. A failed package phase prevents configuration writes; completed package changes survive later failure or file rollback. Missing managers are reported, never silently bootstrapped. Native Windows supports the opt-in WinGet workflow through an existing manager, with exact community-source IDs, user scope by default and explicit machine scope; Microsoft.WinGet.Client preparation requires explicit dependency approval. Native Windows PowerShell 5.1/7 runtime acceptance remains pending. Reviewed foreign command links and regular files are backed up; replacements retain their first-install baseline. Uninstall preserves application data and drift while restoring unchanged owned targets. See [destinations and migration](bundled-applications.md#one-installation-and-removal).

## Previous application installations

Combined setup installs Anodize, Blastoff and pkgs from `plugins/`. Protected legacy links can be reconciled with `dots files migrate-apps`, which previews by default and applies only with `--yes`. This bounded operation installs application assets without reinstalling other configurations or publishing themes. Backups and original baselines remain available to normal uninstall/undo. See [supported migration layouts](plugins.md#legacy-application-migration).

## Complete command manual

Core setup installs the generated `man/dots.1` as `dots:manual`. Termux uses the detected native prefix's `share/man/man1/dots.1`; Linux and WSL use `~/.local/share/man/man1/dots.1`. Read it with `man dots`; viewers with a custom manual search path may need that directory added explicitly, or can read the repository artifact directly (`mandoc man/dots.1`, or `man -l man/dots.1` with man-db).

The manual is linked by default through the same installer receipt as the command. Existing files and reviewed foreign leaf links are backed up, and correct preexisting links remain unowned. Core-only removal includes an installer-owned manual, restores its original target, and refuses post-install drift. A missing/nonregular manual in a declared `man` directory blocks setup; older/minimal checkouts without that directory remain compatible. Native Windows creates no POSIX manual link and uses the generated wiki command reference. No system package or shell search-path setting is changed. Configuration/menu review: no additional integration is needed beyond existing core selection and preview.


## Fresh-machine bootstrap

Use standalone `sh bootstrap.sh --dry-run` or native `./bootstrap.ps1 --dry-run`,
then run with `--yes` or interactive approval. Existing checkouts expose
`./install.sh --bootstrap` and `./install.ps1 -Bootstrap`.
Defaults are public `https://github.com/5nik7/dots.git`, ref `main`, destination
`~/dots` (or the current valid checkout). Override `--source`, `--ref`, or
`--destination` explicitly. A valid existing checkout is reused without a fetch,
reset or update. Fresh acquisition records the commit, uses owned staging and
never replaces an occupied destination or initializes submodules.

Prerequisites are separately reviewed. POSIX uses a supported existing package
manager. Windows prefers WinGet and otherwise offers official, verified Git and
Python installers. The baseline is Python 3.11+ and a compatible native shell.
Anodize selection tests and builds the engine against its checked-in `go.mod` in
owned storage before managed publication. External package changes remain if
later setup fails or is cancelled. `--offline` refuses network preparation;
`--dry-run` acquires nothing. Missing Python can trigger bootstrap delegation.

Windows bootstrap probes link capability after approval. It can explicitly offer
Developer Mode with the operating system's administrator prompt. `--yes` alone
does not approve this setting: separate interactive approval or
`--developer-mode` is required. Shell configuration never changes the login shell.
Setup discovers each installed PowerShell engine's all-hosts profile and links
`shells/powershell/profile.ps1`, retaining host-specific profiles. Native scripts
and shared controllers remain the architecture, with portable navigation, Git,
listing, editor and backup helpers and no eager whole-command module import.

Dots `bin`, `scripts`, and generated theme commands lead shell PATH. Selected old
user `~/bin` launchers are reviewed and backed up; package installations and
optional libraries are retained. Core installs `bak` and `dots-link`. Existing Git
mappings include the guarded `gitplatform` companion.

Fresh theme fallback is Catppuccin Mocha; repeats retain the selected theme.
Theme preparation generates family/full-ID POSIX and PowerShell shortcuts.
Blastoff setup prepares the saved theme's Dots palette and links the active
Starship path directly to the selected saved theme (default `dots`). Nonempty
`STARSHIP_CONFIG` selects the destination; otherwise it is
`~/.config/starship.toml`. An existing saved-theme link retains its selection.

New setup backups share [the backup catalog](backups.md). `--no-backup`
(`-NoBackup` in `install.ps1`) explicitly discards newly replaced originals,
keeps temporary rollback protection, and preserves older uninstall baselines.
Uninstall reports when a deliberately discarded original cannot be recreated.
Old transaction receipts remain readable.
