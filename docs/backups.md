# Backups and safe links

`bak` and `dots bak` share a journaled catalog. **Creation moves the original by
default.** Use `--copy` to retain it. The default store is `~/.bakstore`;
`--in-place` uses `filename.YYYYMMDDTHHMMSS.microsecondsZ.bak` beside the original.
Full UUIDs distinguish repeated backups and identical basenames. Directories and
symbolic links retain their object identity.

```sh
bak settings.toml
bak --copy settings.toml
bak --in-place old-directory
bak list
bak show FULL_ID
bak restore FULL_ID
bak restore FULL_ID --to ./recovered
bak delete FULL_ID --dry-run
bak delete FULL_ID --yes
bak prune --keep 3 --older-than 30 --dry-run
bak import ./legacy.bak --original ./settings.toml
bak -- list
```

Restore copies the saved object back and **retains the backup**. An occupied
destination receives another backup. `--no-backup` explicitly permits replacement
without retaining that current object; temporary rollback protection still applies.
Import registers an existing backup in place. Without `--original`, restore needs
`--to`; filenames are never used to guess the original location.

Bare `bak` opens the browser in a terminal and prints help otherwise. `bak browse`
is available from the Dots root and Files menus. Browser actions show details and
confirm restoration/deletion. Delete and prune require terminal confirmation or
`--yes`; neither runs automatically. Prune combines its supplied count and age
limits, protecting required uninstall baselines. Restoring a managed baseline
releases only the matching receipt entry in the same transaction.

Delete and prune also remove the backup's UUID directory when its creating
transaction proves ownership and it contains only the selected payload. This
also cleans an empty owned directory after its payload was removed externally.
Directories containing other files, adjacent/import parents and the store root
remain intact. Changed payloads still require review; cleanup never guesses from
a directory name. Payload, directory and catalog removal share rollback protection.

Configure `apps.bak.store`, `apps.bak.location` (`store` or `adjacent`), and
`apps.bak.mode` (`move` or `copy`) through `dots config browse --query apps.bak`.
They follow normal profile inheritance and affect the next invocation. Explicit
flags override defaults. There is no persistent backup opt-out.

Installers, `dots link`, and Blastoff use this same backend for new retained user
backups. Automatic snapshots explicitly copy before replacement; `bak PATH`
still moves by default. Blastoff content snapshots carry their app metadata in
the shared catalog and appear in both `bak list` and `blastoff backup list`.
`blastoff backup restore ID` restores content into the active Starship config;
`bak restore ID` restores the recorded original object. Switching an existing
active link additionally preserves that exact link as a separate Bak record.
Old Blastoff `.toml`/`.json` pairs remain readable through its backup commands;
they are not migrated during inspection. Internal transaction recovery copies,
build staging and failed editor work are separate from retained user snapshots.

## Safe symbolic links

`dots link`, `dots-link`, and `.ln` after initialization use the same controller.
All six shell adapters expose `.ln`; PowerShell uses the native bridge.

```sh
dots link ./source ~/.config/target
dots link ./one ./two ./existing-directory
dots link -T ./source ./exact-destination
dots link --relative ./source ./target
dots link --allow-missing ./future-source ./target
dots link --dry-run ./source ./target
```

Like `ln`, a directory destination receives each source basename; `-T` names an
exact destination. Sources become absolute by default; relative links are
explicit. The final source symlink is preserved rather than dereferenced.
Missing sources require `--allow-missing`. Correct links are no-ops.

Replacement applies immediately with backups, including occupied directories and
broken links. Whole-batch preflight, guarded linked parents, overlap refusal and
reverse rollback use the existing file Store. Missing parents are created.
`--no-backup` explicitly permits replacement without retention. Native link
capability is required; copying is never a silent fallback.

Human output uses `󰡯 ~/source -> ~/target`, shared resource colors and
`icons.operations.link`. `-q` suppresses routine output, keeping errors. JSON uses
full undecorated paths; dry-run writes nothing. Reports follow the shared
[presentation contract](presentation.md). Recovery uses `dots files history`,
`dots files recover ID`, and `dots files undo ID`.

Windows accepts the same options through `dots.ps1 bak` and `dots.ps1 link`.
Native Windows 5.1/7, Linux and WSL evidence remains separate from Termux fixtures.

## Completion

Dots shell initialization registers `bak`, `dots-bak` and `dots bak` completion
for Bash, Zsh, Fish, PowerShell, Nushell and Xonsh. Complete commands/options,
`--color`/`--icons` choices, source/destination paths and saved IDs for show,
restore and delete. IDs come from the bounded catalog without reading backup
payloads, prompting or changing state; malformed/missing catalogs yield no IDs.
Start a new initialized shell to load updated adapter registrations. PowerShell
also registers the `.ps1` wrappers. Native Windows acceptance is recorded
separately from shared-controller tests.
