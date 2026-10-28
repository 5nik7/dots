# Recovery, editing and tracking

Blastoff 0.1.12 keeps the active Starship file separate from local theme storage.
Use `blastoff current` to distinguish last-loaded history from exact matches,
and `blastoff doctor --json` to inspect resolved paths. Neither repairs state.

## Backups and permanent deletion

`backup create` preserves even invalid active TOML for recovery. `backup restore ID`
validates checksum/TOML, backs up current content and restores a regular file.
Recorded symlink text is evidence, not an instruction to recreate the link.
Stored-theme backups can be recovered with `theme import /absolute/backup.toml NAME`;
inspect/validate stored-module bytes before copying them to a new module file.

`backup delete --all --dry-run` previews scope. The namespace includes both config
and stored-file backups. Actual deletion shows selected IDs/kinds/count and defaults
to No. IDs/--pick/--all are exclusive; --yes authorizes noninteractive deletion.
Use `backup delete --yes -- all y yes` only to delete those literal IDs.

Malformed metadata, orphan payloads, checksum mismatches, linked members and
active-config aliases are refused. Inspect these files manually; do not turn
metadata source paths into deletion commands. A missing payload with trustworthy
metadata can be cleaned up explicitly. Deletion is permanent: completed IDs cannot
be rolled back after a partial I/O failure or late interruption. No recursive
cleanup or automatic pruning occurs.

## Failed editor sessions

`theme edit` backs up before opening a private working file beside the active
config. Valid successful edits publish atomically. Invalid TOML, editor failure,
interruption or an external active edit preserves the working file and prints
its exact `.blastoff-edit-*/starship.toml` path. Inspect that file and the current
active configuration. To recover, fix/validate the retained TOML, import it with
an explicit new theme name, then apply that local theme after reviewing scope.
Do not delete the recovery directory until its useful content is saved elsewhere.
Extra editor artifacts are retained; Blastoff never recursively removes them.

An active-file symlink normally stays in place while its guarded regular target
is updated. --replace-link explicitly converts the link and leaves its target untouched. Linked
parents remain unsafe for publication. Choose a real absolute STARSHIP_CONFIG
path when `.config` is itself linked. EDITOR parsing never expands shell commands.
Use a quoted executable with arguments, e.g. `EDITOR='nvim --clean'`; quote an
executable path containing spaces. On Windows use double-quoted paths and a
native executable, not .cmd/.bat/.ps1. code/code-insiders/codium CLIs wait; supply
appropriate foreground/wait arguments for other configured GUI editors.

## Unknown or stale provenance

State lives under `<canonical storage>/state/provenance`, keyed by physical target (configured pathname for --replace-link).
Legacy alias records remain readable; a successful mutation archives superseded
records under unique `.legacy-*` names. Conflicting/pending aliases cannot
authorize implicit save.
The source theme and last-loaded digest remain historical when active bytes change.
A separate save target records the local file that no-argument save may replace.
Changing/deleting/renaming that destination invalidates implicit overwrite authority.
Use save-as or an explicit name; no library-wide matching guesses are made.

A corrupt/unsupported record is treated as unknown. A `.pending` record means a
content/state operation did not finish: content may already have changed. Read
current files and backups first. Then a successful explicit apply, save NAME or
backup restore establishes fresh state; never assume automatic rollback. Do not
remove pending records merely to regain an implicit overwrite prompt.

Storage/config locks are never broken automatically. After a killed process,
verify no writer/editor still runs and inspect the affected files before manually
removing a stale lock. Per-file replacement and state markers do not make operations
power-loss transactional or defend against a malicious final-window path swap.

## Optional tools and previews

Missing fzf retains Gum/numbered theme picking. Module browsing and backup --pick
instead explain how to use explicit targets. Missing/failing bat falls back to
plain source. Invalid/incompatible inherited fzf options are omitted with a warning;
-v explains which settings were ignored. Ctrl-X toggles initially visible previews.

Previews show bounded sanitized TOML. They never run a live Starship prompt,
custom commands or conditions. Preset generation is on demand and session-cached.
Temporary preview files disappear on normal exit; forced process death can leave
OS-temporary cache directories. These are not application themes or backups.

Uninstall retains application state, backups and editor recovery files. Source
changes do not update the installed runtime: use the reviewed root-level
installation workflow in INSTALLATION.md when an actual upgrade is wanted.

## 0.1.8 follow-up

For picker appearance, distinguish fixture HOME/XDG isolation from actual fzf/bat
configuration. Use --verbose and the user-tool-config helper in TERMINAL-UX.md.
PowerShell uninstall retains modified owned files/blocks and profile recovery
backups; resolve conflicts explicitly, never delete ownership to force adoption.
See POWERSHELL.md for independent shell/module ownership.
