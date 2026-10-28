# Termux installation / source update plan

The 0.1.12 Battery-style installer is implemented; this plan is not evidence of a
live installation or passing tests. The user previously reported a working
installation, 37 migrated themes and 12 presets. Do not assume historical path
observations still describe the live system. Native Windows remains deferred.

## Review first

From the repository:

```sh
cd /data/data/com.termux/files/home/repos/blastoff
bash install.sh --dry-run
```

Native Termux now defaults to `$PREFIX` (on this device,
`/data/data/com.termux/files/usr`), not `~/.local`. An explicit `--prefix` overrides
that selection. The public installer automatically migrates verified ownership
from `~/.local` when the target differs. Review both prefixes and all profile/file
changes shown. Dry-run writes nothing and does not execute profiles or probes.

Stop on checksum failures, modified owned files, unowned collisions, unsafe linked
paths, locks or unrelated command shadowing. Preserve any existing
`~/dots/scripts/blastoff`; do not overwrite it to resolve discovery. Follow the
diagnostic and review PATH ordering. Never delete manifests to bypass ownership.
Only after reviewing deliberate source differences may `bash scripts/build.sh`
refresh source checksums; installation never does so automatically.

## When a live install is wanted

These are user-run commands, not authorization for an agent to install:

```sh
bash install.sh
"$PREFIX/bin/blastoff" --version
"$PREFIX/bin/blastoff" --help
"$PREFIX/bin/blastoff" doctor --json
man blastoff
```

Use the same explicit `--prefix /absolute/path` for review and installation if
choosing a custom location. Expected source version: 0.1.12. Config, migrated
themes, modules and application backups remain untouched; applying a theme is a
separate action. Try the sandbox in [TERMUX-QUICKSTART.md](TERMUX-QUICKSTART.md).

Native completion/man locations are preferred. Termux Zsh needs the owned
`share/zsh/functions/Completion/Unix/_blastoff` discovery copy because its compiled
`fpath` omits the canonical `share/zsh/site-functions` directory; both copies are
installed. Custom prefixes may require minimal owned PATH/MANPATH/completion
hooks. Linked profiles and their targets are preserved: unsafe integration is
refused with manual setup instructions instead of rewriting links. Regular
profile changes preserve encoding and unrelated content, with recoverable backups
under `<prefix>/share/blastoff/profile-backups`. Fish uses a conf.d drop-in.

Open a fresh shell after reviewing installation output. Existing Bash/Zsh command
caches may need `hash -r`/`rehash`; the installer does not run activation commands
or profiles for you. PowerShell, if available, gets an absolute versioned manifest
import; this does not establish native Windows support.

Runtime versions remain immutable; repeated install can restore missing support
or refresh unmodified supported output, but cannot overwrite changed runtime bytes
or automatically downgrade. Migration commits the target before legacy removal;
rerun the same install to resume pending cleanup before uninstalling. Locks are
never automatically broken. See [INSTALLATION.md](INSTALLATION.md) for recovery
and legacy entry-point syntax.

## Removal plan

Review first, then remove only when wanted (use the original selected prefix):

```sh
bash uninstall.sh --dry-run
bash uninstall.sh
```

If the source is gone, the default Termux installed wrapper is:

```sh
bash "$PREFIX/share/blastoff/versions/0.1.12/uninstall.sh" --prefix "$PREFIX" --dry-run
```

Only verified owned files and exact owned profile blocks are removed. User data,
unrelated profile edits, original dotfile links/targets, recovery profile backups
and empty directories remain. Modified owned files cause refusal. In-memory
completion definitions can remain until a fresh shell. No live install, removal
or real-profile change was performed by this documentation update.

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

## 0.1.8 follow-up

Manual review remains paused at step 5 (backup deletion); preceding checks and
review-build installation are not assumed passed. Follow INTERACTIVE-CHECKS.md.
The shell installer leaves independently managed CurrentUser PowerShell imports
alone; root PowerShell lifecycle is documented separately in POWERSHELL.md.
