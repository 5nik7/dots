# Install, uninstall, completions and manual

Lifecycle operations are offline and preserve Starship config, themes, modules
and application backups. Python 3.11+ and Bash are required for the public shell
entry points; dependencies are not installed automatically.

## Root PowerShell lifecycle

PowerShell 7+ users run `.\install.ps1 -WhatIf`, `.\install.ps1`,
`.\uninstall.ps1 -WhatIf`, and `.\uninstall.ps1` from reviewed source.
-Verbose is supported; -DryRun is equivalent to WhatIf. This uses a self-contained
CurrentUser module layout, not the prefix layout below. See [POWERSHELL.md](POWERSHELL.md)
for redirected Documents/custom paths, -ModuleRoot, -ProfilePath/-NoProfile,
owned import blocks, independent frontend removal and deferred native checks.
Legacy `scripts/install.ps1` remains a compatibility bridge with its original
syntax; it does not silently migrate to the CurrentUser root-script layout.

## Public installation

From the extracted/reviewed source directory:

```sh
bash install.sh --dry-run
bash install.sh
blastoff --version
blastoff doctor --json
```

No action word or `--yes` is needed. To choose a different destination, use
`bash install.sh --prefix /absolute/path --dry-run`, then the same command without
`--dry-run` after reviewing its plan. Defaults for shell and legacy prefix lifecycle entry points (root PowerShell uses
the separate CurrentUser layout in POWERSHELL.md):

| Host | Default prefix |
|---|---|
| Native Termux | `$PREFIX` (required unless `--prefix` is supplied) |
| WSL / Linux | Linux `~/.local`; use the host's native Python |
| Other POSIX | `~/.local` |
| Windows | `$LOCALAPPDATA/Programs/Blastoff`, otherwise `~/.local` |

The plan shows SYSTEM, version, prefix, migration, file/profile changes and activation
instructions. `--color auto|always|never` controls decoration; presence of
`NO_COLOR` wins. Dry-run verifies source integrity and destinations without
writes, shell probes or executing profiles. Installing also never executes
profiles automatically; start a fresh shell or review the printed activation
commands for your current session. Bash may need `hash -r`, Zsh `rehash`.

`SYSTEM` distinguishes `Termux (Android)`, `WSL (Linux)`, `Linux`, `Windows`,
macOS and other host identities. `--verbose` includes detection evidence and the
selected Python executable. Detection reads runtime/kernel/environment identity,
without running shell probes, reading profiles or starting a second interpreter.
Native Android plus Termux identity is required for the Termux default; an inherited
PREFIX alone does not establish Termux. WSL markers apply only to Linux runtimes.
PowerShell uses its actual host even when MSYSTEM or WSL variables are inherited.

MSYS2/Git Bash and Cygwin Bash lifecycle entry points stop with status 3 before
launching Python, even when Python is absent. Open PowerShell 7+ in the source
directory and run `.\install.ps1 -WhatIf` (or `.\uninstall.ps1 -WhatIf`). This is
guidance, not automatic execution or a migration of shell-prefix ownership.
Bash with a Windows Python runtime is refused before destination planning.
Use Linux Python inside WSL; no Windows/WSL path translation is performed.
Other POSIX labels preserve existing defaults without certifying new native hosts.

The payload is `<prefix>/share/blastoff/versions/0.1.12`. On POSIX the launcher
uses the discovered absolute Bash path, avoiding Termux's absent `/usr/bin/env`.
`BLASTOFF_PYTHON` selects an interpreter executable, not a command with flags.
Missing Python reports an actionable diagnostic and status 3 in both frontends.
Fresh native Windows installs omit the POSIX launcher even if Git Bash exists.
Native Windows runtime verification remains deferred; see `WINDOWS-CHECKS.md`.

## Discovery and profile safety

Public installation prefers native discovery directories:

- Bash: `share/bash-completion/completions/blastoff`.
- Zsh: canonical `share/zsh/site-functions/_blastoff`, plus an owned copy at
  `share/zsh/functions/Completion/Unix/_blastoff` when the native directory exists.
  Termux Zsh's compiled `fpath` omits site-functions; the second copy provides
  discovery without rewriting profiles just to add that directory.
- Fish: `share/fish/vendor_completions.d/blastoff.fish`.
- Manual: `share/man/man1/blastoff.1`.

Custom prefixes or missing native discovery can require minimal owned hooks for
PATH, MANPATH and completion. Bash/Zsh use marked profile blocks and helpers
under `<prefix>/share/blastoff/integration`; Fish uses a `conf.d/blastoff.fish`
drop-in and, when needed, a user completion copy. Unless an independent CurrentUser managed PowerShell block already exists,
available `pwsh` integration imports the absolute versioned `powershell/blastoff.psd1`
through an owned profile hook. Module import registers offline completion without
starting Python or Starship; it is not a native Windows verification claim.

Regular profile encoding, newline style and unrelated content are preserved.
Changed existing profile bytes are backed up under
`<prefix>/share/blastoff/profile-backups`. Linked profiles/targets and unsafe
parents are never rewritten: installation refuses with manual setup instructions.
Do not replace a dotfile link merely to bypass this guard. Ambiguous/dynamic
ZDOTDIR settings also require manual resolution, not profile execution.

Completions never launch Blastoff/Starship or discover live presets. They offer
static grammar, local names and paths; see `CLI-CONTRACT.md` for exact limits.

## Upgrade, repair and legacy migration

Versioned runtime payloads are immutable. Different bytes under an installed
version require a new release identity, not an integrity bypass. Repeating an
install restores missing support files and refreshes unmodified supported output;
identical installations need no changes. Newer installed or legacy versions are
not automatically downgraded. Upgrades retain previous target-prefix runtimes.

Public install automatically migrates a verified owned `~/.local` installation
when the selected prefix differs. It commits the target before retiring legacy
owned files and records pending cleanup so rerunning the same install can resume.
Finish pending migration cleanup before uninstalling. This is installation
migration, not the separate `blastoff migrate` command for theme copying.

Modified owned files, unowned collisions, unsafe destinations and unrelated
shadowing commands block installation before changes. Preserve the conflicting
content and follow the diagnostic; never delete manifests or break locks to force
an upgrade. Neither migration nor uninstall recursively deletes user directories.

## Uninstall

Use the same selected prefix as installation:

```sh
bash uninstall.sh --dry-run
bash uninstall.sh
# Custom prefix:
bash uninstall.sh --prefix /absolute/path --dry-run
```

If the source is unavailable, use the installed public wrapper, for example on
Termux with the default prefix:

```sh
bash "$PREFIX/share/blastoff/versions/0.1.12/uninstall.sh" --prefix "$PREFIX" --dry-run
# Remove --dry-run only when removal is wanted.
```

Uninstall removes verified owned files and exact owned profile blocks, retaining
unrelated profile edits, user data, empty directories and recovery profile backups.
Modified owned output is refused. Already-missing owned files are tolerated on
retry. An interrupted migration must first resume through install. Inspect stale
locks manually. Per-file atomic writes and rollback of ordinary write failures
are not a full multi-file/power-loss transaction; inspect unexpected staged files
against ownership records before manual recovery.

## Source integrity and deliberate development changes

Source checksums remain mandatory, including for dry-run. Installation never
refreshes them automatically. Stop on unexpected source differences. Only after
reviewing deliberate source changes, rebuild with:

```sh
bash scripts/build.sh
bash install.sh --dry-run
```

Rebuilding checksums does not establish archive provenance or permit overwriting
an immutable installed runtime. Reference assets in `.local/src` and `.local/logo`
are source inventory, not automatically executed or installed commands.

## Compatibility: legacy entry points and manual activation

These remain supported, but a fresh legacy installation leaves integration manual
unless it already owns integration. Prefix defaults are the same as above.

```sh
bash scripts/install.sh install --dry-run
bash scripts/install.sh install --yes
bash scripts/install.sh uninstall --dry-run
bash scripts/install.sh uninstall --yes
```

Native PowerShell 7+ (no Bash/WSL needed):

```powershell
./scripts/install.ps1 install --dry-run
./scripts/install.ps1 install --yes
./scripts/install.ps1 uninstall --dry-run
# Only when removal is wanted:
./scripts/install.ps1 uninstall --yes
```

For manual activation, substitute your actual absolute prefix below. PowerShell
can import `<prefix>/share/blastoff/versions/0.1.12/powershell/blastoff.psd1`
explicitly. Bash can source `<prefix>/share/bash-completion/completions/blastoff`;
Fish can source `<prefix>/share/fish/vendor_completions.d/blastoff.fish`.
For Zsh, add `<prefix>/share/zsh/site-functions` to `fpath` before your existing
`compinit`; in an already initialized shell, autoload `_blastoff` and run
`compdef _blastoff blastoff`. These are manual choices, not commands executed by
the installer. Source completion can also be inspected with
`bash bin/blastoff completion bash` (or `zsh`/`fish`).

Use `man blastoff` after discovery is active. For a custom prefix, a one-command
lookup is `MANPATH="/absolute/prefix/share/man:" man blastoff`; alternatively
`man -l /absolute/prefix/share/man/man1/blastoff.1` where supported.

## Validation boundary

Use disposable HOME/config/storage/prefix roots for lifecycle testing, not these
real-install examples. Installed-package rehearsals live in
`tests/test_installed_package.py`; native shell/human checks are documented in
`INTERACTIVE-CHECKS.md`. Current results belong in `STATUS.md`; this documentation
update does not claim new test passes, a real installation or profile changes.

## 0.1.8 retained user state and verification

The versioned payload includes operations, provenance, editor, backup and preview
helpers beside the Python core. Ownership tracking covers these installed files;
source-checkout removal must not break previews. Installation/uninstallation never
creates or deletes application provenance under `<storage>/state/provenance`, or
editor recovery directories beside the active config. These remain user data.
No automatic migration is needed: old config backups remain readable with unknown
origin when they lack provenance. Bat and fzf remain optional; no dependencies are
installed. -v/--verbose shows detailed lifecycle actions on stderr.

Rehearse 0.1.11 to 0.1.12 upgrades in temporary prefixes using the actual old source,
then verify helper resolution, completions, manual/version and retained data after
uninstall. Final checksums/packages follow final code and documentation edits.
Native Windows and human visual checks remain separate gates in STATUS.md.
