# Everyday Termux quickstart

Termux has prior native validation; current installer results belong in STATUS.md.
Native Windows remains deferred. The user reported a working installation and
37 migrated themes; the agent has not updated that live installation. Review
[the update plan](TERMUX-INSTALL-PLAN.md) for 0.1.12: `bash install.sh --dry-run`,
then `bash install.sh` when wanted. Native Termux defaults to `$PREFIX` and public
install migrates verified legacy `~/.local` ownership. Native discovery is preferred;
custom prefixes may need owned profile hooks. Linked profiles are never rewritten.
Python 3.11+ and Bash are required; Starship is needed only for presets. fzf/gum
are optional.

## Linked dotfiles storage

Starting with 0.1.6, an existing link such as
`~/.config/blastoff -> ~/dots/config/blastoff` works without an override.
The target must already be a directory. Blastoff leaves the link intact and
stores themes, modules, backups and its operation lock in that target.
`blastoff doctor --json` reports the real storage path.

Only the storage-root path and its ancestors may redirect writes. Do not link
`themes`, `modules`, `backups` or individual stored files separately. Broken
root links fail without creating their targets. Active config protections are
unchanged: if `.config` itself is linked, use a real-path `STARSHIP_CONFIG`;
`--replace-link` applies only to the active config file, not storage.

For an older installed build, this temporary override avoids the root link:

```sh
BLASTOFF_HOME="$HOME/dots/config/blastoff" blastoff doctor --json
```

Use the same prefix with your intended command until you explicitly upgrade.
This does not move storage or edit shell profiles. Source changes alone do not
update an installed command; review `bash install.sh --dry-run` before installing.

## Try the commands without touching your prompt

Run this in Bash or Zsh **after an approved installation**. The parentheses
isolate environment changes; the directory is retained for inspection. Before
installation, replace the `bo` function with `bo() { bash bin/blastoff "$@"; }`
from the repository root.

```sh
(
  sandbox=$(mktemp -d "${TMPDIR:-/data/data/com.termux/files/usr/tmp}/blastoff-demo.XXXXXXXX") || exit
  export STARSHIP_CONFIG="$sandbox/config space/starship.toml"
  export BLASTOFF_HOME="$sandbox/storage space"
  export STARSHIP_CACHE="$sandbox/starship-cache"
  bo() { "$PREFIX/bin/blastoff" "$@"; }
  mkdir -p "$sandbox/config space"
  printf '[directory]\nstyle = "purple"\n' > "$STARSHIP_CONFIG"

  bo                                   # full help, identical to -h/--help
  bo --version                         # blastoff 0.1.12
  bo doctor --json                     # config/storage point inside sandbox
  bo list                              # local themes + available Starship presets
  bo theme save daily                  # snapshot current config as daily
  bo theme copy local:daily spare       # copy stored theme without applying
  bo theme list                        # daily and spare among local themes
  bo theme apply local:spare            # identical bytes retained; no backup needed
  bo current                           # matching local names/config information

  bo module save directory dir-style    # store explicit [directory] table
  bo module list                       # dir-style
  bo module load dir-style              # merge table, preserve unrelated settings

  bo backup create                     # prints a backup ID
  bo backup list                       # inspect IDs; choose the config backup above
  # Replace ID with that actual ID (not the literal word ID):
  # bo backup restore ID                # restores backed-up config, backs up replaced config

  # Optional preset: exact name comes from `bo preset list`:
  # bo preset list
  # bo preset save plain-text-symbols plain  # stores a preset without applying it
  # bo theme apply local:plain          # replaces only sandbox config, with backup

  # Optional interactive picker, from a terminal (not a pipe):
  # bo pick
  printf 'Inspect retained sandbox: %s\n' "$sandbox"
)
```

Expected: mutations stay inside the printed sandbox, and your actual prompt
configuration remains unchanged. Backup IDs are generated, so copy the actual ID
from the output. The `plain-text-symbols` example matches Starship 1.26.0;
check your installed preset list rather than assume all versions have it.

For everyday use after default installation, invoke `"$PREFIX/bin/blastoff"`
(or your actual custom-prefix command) with the same arguments, **without** sandbox
overrides. Until migration, a legacy installation may still be under `~/.local`. A historical observation used
`~/dots/config/starship/starship.toml`; recheck the actual active path rather than
assuming that observation is current. First run `doctor
--json`, save a named theme and create a backup. Do not infer the destination
from the storage directory: `BLASTOFF_HOME` controls storage only.

Existing destination names refuse overwrite unless `--force` is supplied;
forced replacements are backed up. Use `local:NAME` to avoid preset ambiguity.
`theme import /absolute/path/to/file.toml NAME` imports without applying it.
Missing/failing Starship does not hide local themes: combined listing and pick
warn on stderr and continue with locals (a timeout can take ten seconds).
`list --json` instead includes `preset_discovery.status` (`ok` or `unavailable`)
and `preset_discovery.error` in its single stdout object, with no warning on
stderr. Combined listing exits 0 even when empty; pick exits 1 without opening a
picker if no choices remain. Explicit preset requests still fail with status 3
when discovery fails. A successful empty preset list is not a failure.
Quote paths with spaces. Names are portable ASCII letters/digits, `_` and `-`,
up to 96 characters; names start with a letter/digit and Windows device names
are excluded. No custom Starship commands are run by validation.

Bare `pick` uses fancy Unicode; `pick --fzf` or `pick fzf` uses compatible
FZF_DEFAULT_OPTS_FILE/FZF_DEFAULT_OPTS without a Blastoff palette.
`pick --fancy` keeps purple/pink connected Unicode borders; use `--fancy ascii` for
ASCII. Ctrl-X toggles the initially visible TOML preview, which moves below when
a right pane cannot hold 60 columns and responds to resizing. Bat is optional;
plain source works without it. No prompt/custom commands execute. Gum/numbered
fallbacks have labels but no pane. NO_COLOR and --color never suppress colors.

`theme edit --dry-run` reports the active target and selected editor. Actual
`theme edit` backs up and edits a working copy; valid unchanged-baseline results
publish atomically, failed/conflicted work remains at a reported recovery path.
Editor order: nonempty EDITOR, nvim, vim, vi, code, nano. Quoted editor paths and
arguments work without eval. Use wait arguments for unrecognized GUI editors.
`theme save` asks `Save edits to "<theme>"? [y/as/N]` for a known unchanged local
destination. Use y/yes, a/as for save-as, or Enter/no to cancel. The confirmation
replaces --force for that identified theme. Presets/unknown/changed origins need
save-as. `current` distinguishes last-loaded history from current matches.

`module show NAME` views saved TOML without loading; redirected output is raw TOML.
`module show` opens an fzf browser. `backup delete --pick` supports Tab/Shift-Tab;
`backup delete ID1 ID2` or `--all` shows the frozen set/count and asks [y/N].
`backup delete --all --dry-run` writes nothing. Noninteractive deletion needs
explicit IDs/--all and --yes. Bare all and trailing y/yes are aliases; after --
they are literal IDs. Both config and stored-file backups are included. Deletion
is permanent; read [recovery guidance](RECOVERY.md) before removing snapshots.

Every mutation supports --dry-run; -v/--verbose reports diagnostics on stderr.
No dry-run launches an editor/picker or changes provenance.

Picker selection applies a theme. Cancellation exits 130 without changing
config/storage: Escape/Ctrl-C in fzf/gum; blank Enter, Escape then Enter, Ctrl-D
or Ctrl-C in the numbered fallback. Missing fzf/gum automatically falls back.
Use `--help` after any subcommand; use `--json` for machine output, not with pick.
Completion activation and manual commands are in [INSTALLATION.md](INSTALLATION.md).

## Smallest remaining human check

Automated native PTYs have passed; screen appearance and your Android keyboard
still need human confirmation. From the repository in your ordinary terminal:

```sh
python3 scripts/interactive_check.py --backend fzf --expect select
python3 scripts/interactive_check.py --backend fzf --expect cancel
```

Choose alpha/beta in the first; press Ctrl-C in the second. Expect `PASS`, exit
0/130 respectively, and `config/storage unchanged=True` for cancellation.
Report terminal app, width, clipping, and whether cursor/echo return normally.
Use `--backend numbered` instead if that is your intended everyday backend
(blank Enter cancels). The complete optional gum/Escape/narrow-width and
shell-plugin checklist remains in [INTERACTIVE-CHECKS.md](INTERACTIVE-CHECKS.md);
this small check does not claim those remaining human checks passed.

Backup listing in 0.1.9 separates records with blank lines and distinguishes IDs,
labels and values by color. Size moves below Kind on narrow screens. Plain output
keeps the same layout; --json retains its schema. See TERMINAL-UX.md for a read-only
source preview and illustrative output.

In 0.1.10, `bo list` uses quieter source prefixes and highlights `[current]` or
`[last loaded; modified]` beside the tracked theme. An unknown origin is not guessed;
use `bo current` for explicit local matching. Source-only visual review commands
are in [TERMINAL-UX.md](TERMINAL-UX.md#theme-list-readability--0110).
