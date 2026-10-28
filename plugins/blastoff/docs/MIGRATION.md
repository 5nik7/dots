# Move legacy themes safely

The old Bash source uses `~/dots/config/starship/themes` and a config inside
that Starship directory. The old PowerShell source uses `~/.config/starship/themes`
or `STARSHIP_THEMES` and sometimes an active config symlink. Do not infer which
layout Nick currently uses on his device; inspect it first.

1. Identify the actual legacy themes directory and active config, including any
   links. Save a separate recovery copy before changing real files.
2. Run the new command's `doctor --json` to inspect its resolved paths. It uses
   nonempty `STARSHIP_CONFIG`, even if that file has not been created yet.
3. Copy legacy themes explicitly, using the actual absolute source path:

```sh
blastoff migrate "$HOME/dots/config/starship/themes"
# Or the PowerShell-era directory, if that is the actual source:
blastoff migrate "$HOME/.config/starship/themes"
blastoff --list
```

Migration never moves/removes legacy files or rewrites the active config.
Resolve name collisions explicitly; existing destination files cause refusal.
Only portable named regular `.toml` files are discovered. Symlinked theme files
are not migrated automatically. Use an inspected real source with `theme import`
when a stored source is a link. Copying is per-file atomic; an I/O failure midway
may leave a partial copied set. Compare source/destination before retrying.

4. If the current active config is at the old custom location, explicitly choose
   either to keep that location via `STARSHIP_CONFIG` or to put a backed-up regular
   config at Starship's default `~/.config/starship.toml`. The rebuild does not edit
   your exported environment or prompt startup configuration.
5. Apply a copied theme only after review. An existing regular active config is
   automatically backed up. For an active symlink, opt in to conversion:

```sh
blastoff theme apply local:example --replace-link
```

This records the old link text and snapshots its content, replaces the link
with a regular active config and leaves the old target untouched. If you use a
linked `.config` directory, supply real absolute storage/config paths first;
writes through linked parent directories are refused in this build.

6. Keep the original directories and old script/module until the new setup has
   passed your native-host checks. Switching entries in PATH/profiles and later
   deleting legacy files are separate explicit actions, not automatic migration.


## 0.1.7 tracking and backup compatibility

No existing theme/module/config path is moved. Provenance is created lazily after
successful apply/save/edit/load/restore under `<storage>/state/provenance`.
An unknown origin is not guessed from byte-identical theme files: use an explicit
apply or save-as to establish the intended association. Old config backups restore
content with unknown provenance. Root storage links remain supported; linked
children are still refused. Uninstall retains tracking and editor recovery data.
Preview migration with `blastoff migrate /absolute/source --dry-run`.

## 0.1.8 follow-up

Root PowerShell installation uses independent CurrentUser ownership; legacy prefix
integration must be reviewed with its owning installer before changing profiles.
There is no automatic Windows/WSL path or data migration. See POWERSHELL.md.
