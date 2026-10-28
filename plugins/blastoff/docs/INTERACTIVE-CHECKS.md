# 0.1.10 theme-list visual check

Before resuming the paused step-5 backup-deletion review, use the read-only source
preview in TERMINAL-UX.md. Verify dim prefixes, prominent names and pink markers,
then compare --color never and redirected output. In disposable fixtures, review
current and modified local/preset origins, source changes and unknown tracking.
Do not change live configuration to manufacture these states. Automated coverage:
`python3 -B -m unittest discover -s tests -p test_list_output.py -v`.
Native PowerShell parity includes plain/color/JSON and modified-origin cases;
availability and actual execution must be recorded separately. Earlier acceptance
steps and installation are not implied; human appearance remains unverified.

# 0.1.9 backup-list visual check

Manual acceptance remains paused at step 5; preceding checks and installed identity
are not inferred. Review complete bright-white IDs, purple labels, pink values,
dim separators and reset behavior. Check blank lines between records, two-space
metadata indentation, and Size moving to its own line as the terminal narrows.
Use the read-only source command in TERMINAL-UX.md; compare --color never,
NO_COLOR and automatic redirected output. Record human appearance separately
from automated PTY assertions. No backup creation/deletion or installation is
needed to preview an existing list. Earlier checkpoints below remain historical.

# 0.1.8 acceptance resumption

Manual acceptance is paused at **step 5, backup deletion**. Do not mark steps 1–4
passed without their own evidence or assume the review build was installed.
First record source VERSION, resolved `type -a blastoff` / PowerShell Get-Command,
command/module --version, fzf/bat versions and relevant color/config diagnostics.
Planning found source 0.1.7 but this session's PATH launcher at 0.1.6; that is a
historical observation to recheck, not a claim about the current live command.

5. Disposable backups: human/JSON listing, explicit IDs, literal all/y/yes after
   --, default No, negative/empty confirmation, Escape/Ctrl-C, Tab/Shift-Tab,
   frozen all-selection, dry-run and partial-error reporting. Check untouched data.
6. Fancy/default/Unicode/ASCII and basic --fzf across all browsers: Ctrl-X, resizing,
   safe settings precedence, actual bat themes. Run fixture checks then --tool-config
   user appearance checks from TERMINAL-UX.md. Human appearance is its own evidence.
7. Named/raw module viewing, human vs JSON, verbose stderr and no accidental load.
   Recheck edit/save/provenance only as affected; earlier results remain explicit.
8. Fresh PowerShell session completion/argv/streams and Ctrl-C; when unavailable,
   retain pending gates from POWERSHELL.md and WINDOWS-CHECKS.md.
9. Isolated shell/PowerShell lifecycle: WhatIf, install/repeat/upgrade/uninstall,
   coexistence and data retention. No live installation is implied.
10. Reconcile help/manual/completion/docs/version/installed resources and retain
    every unresolved native or human gate in STATUS.md.

The detailed checks below remain useful; current defaults supersede older review
expectations. No helper result certifies steps that were not run.

# Native terminal checks

Automated PTYs exercise real native executables, controlling terminals, keys and
exit status. They do **not** establish visual quality, touch-keyboard behavior,
or compatibility with a user's terminal/plugins. Windows remains a separate gate.
All commands below run from the repository. Nothing installs or edits live config,
profiles, PATH or reference assets.

## Automated checks

```sh
python3 -m unittest discover -s tests -p test_completions.py -v
python3 -m unittest discover -s tests -p test_shell_tty.py -v
python3 -m unittest discover -s tests -p test_picker.py -v
python3 -m unittest discover -s tests -p test_assets.py -v
python3 -m unittest discover -s tests -p test_preview.py -v
python3 -m unittest discover -s tests -p test_edit.py -v
python3 -m unittest discover -s tests -p test_theme_save.py -v
python3 -m unittest discover -s tests -p test_backup_delete.py -v
python3 -m unittest discover -s tests -p test_provenance.py -v
python3 -m unittest discover -s tests -p test_dry_run.py -v
python3 -m unittest discover -s tests -p test_module_show.py -v
```

Picker tests isolate optional tools using a **child-only** PATH in a temporary
root. They expose the actual installed fzf or gum, or neither; no executable is
installed and the caller's PATH is unchanged. PTY children restore normal SIGINT
handling rather than inherit a background launcher's ignored signal disposition.
The local Fish build creates its own temporary XDG scaffold even with
`--no-config --private -c true`; completion tests initialize that empty-shell
state first, then assert no completion-triggered changes. Shell-editor tests
use an empty child PATH and a sentinel `blastoff` function so an accidental
submitted line cannot launch an installed application.
No Starship executable is exposed in picker cancellation tests, so their byte/
directory snapshots measure Blastoff config/storage without Starship cache noise.

## Human picker check (still required)

Resize your terminal to 40 columns, then repeat at 50 columns. Run each available
backend with both outcomes:

```sh
python3 scripts/interactive_check.py --backend fzf --expect select
python3 scripts/interactive_check.py --backend fzf --expect cancel
python3 scripts/interactive_check.py --backend gum --expect select
python3 scripts/interactive_check.py --backend gum --expect cancel
python3 scripts/interactive_check.py --backend numbered --expect select
python3 scripts/interactive_check.py --backend numbered --expect cancel
```

Fzf in 0.1.8 is fancy Unicode by default; --fzf selects compatible user styling.
Ctrl-X toggles an initially visible source preview. Resize from 40/50 to 100/120
columns: the pane should move right only when readable code/list space fits.
Repeat with `--fancy unicode` and `--fancy ascii` on the helper, and use
`--feature module` or `--feature backup` for viewing/multi-selection checks.
Gum and numbered fallback have labels/instructions but no preview pane.
See TERMINAL-UX.md for source bounds and inherited-option precedence.

Select alpha or beta (number 1 or 2 in the fallback). For cancellation, repeat
with Escape and Ctrl-C in fzf/gum. In the numbered **line-oriented** menu, test
blank Enter, Escape **then Enter**, Ctrl-C, and Ctrl-D on an empty line.
The checker should print `PASS`, with child exit 0 for selection or 130 for
cancellation. Cancellation must report `config/storage unchanged=True`.
The helper checks outcomes and removes only its own temporary sandbox on exit.
It exposes no real Starship executable and does not render any prompt commands.

Report: backend/version, terminal app, column count, keys pressed, PASS/FAIL,
any clipped/unreadable labels, unexpected selection, cursor/echo problems after
exit, and whether the Android keyboard could send Escape/Ctrl-C. Screenshots are
optional; the fixtures contain no live configuration.

## Human shell completion check (still required)

From Bash or Zsh, create this disposable fixture:

```sh
repo=/data/data/com.termux/files/home/repos/blastoff
sandbox=$(mktemp -d)
mkdir -p "$sandbox/store/themes" "$sandbox/store/modules" "$sandbox/functions"
printf 'x=1\n' > "$sandbox/store/themes/alpha.toml"
printf '[directory]\nstyle="purple"\n' > "$sandbox/store/modules/compact.toml"
printf 'x=1\n' > "$sandbox/import with spaces.toml"
cp "$repo/completions/blastoff.zsh" "$sandbox/functions/_blastoff"
printf 'Sandbox: %s\n' "$sandbox"
```

Launch **one** isolated shell (exit it before choosing another):

```sh
env HOME="$sandbox" BLASTOFF_HOME="$sandbox/store" STARSHIP_CONFIG="$sandbox/active.toml" bash --noprofile --norc -i
env HOME="$sandbox" ZDOTDIR="$sandbox" BLASTOFF_HOME="$sandbox/store" STARSHIP_CONFIG="$sandbox/active.toml" zsh -f
env HOME="$sandbox" XDG_CONFIG_HOME="$sandbox/xdg" BLASTOFF_HOME="$sandbox/store" STARSHIP_CONFIG="$sandbox/active.toml" fish --no-config --private
```

Inside Bash:

```sh
source /data/data/com.termux/files/home/repos/blastoff/completions/blastoff.bash
```

Inside Zsh:

```zsh
fpath=("$HOME/functions" $fpath)
autoload -Uz compinit
compinit -D -u
```

Inside Fish:

```fish
source /data/data/com.termux/files/home/repos/blastoff/completions/blastoff.fish
```

Type these prefixes and press Tab; **do not press Enter to run them**:

- `blastoff --json th` → `theme`
- `blastoff theme --color never ap` → `apply`
- `blastoff theme apply local:al` → `local:alpha`, without duplicating `local:`
- `blastoff module load co` → `compact`
- `blastoff module show co` → `compact`
- `blastoff pick --fancy ` → `unicode`, `ascii`
- `blastoff backup delete --` → `--all`, `--pick`, `--yes` and global flags
- `blastoff theme copy alpha ` → no existing-theme destination suggestion
- `blastoff theme import ` followed by the absolute sandbox path and `/imp`
  → one correctly quoted/escaped path containing spaces
- `blastoff --color ` → `auto`, `always`, `never`

Report shell/version, line before/after Tab, literal quoting inserted, unexpected
files/options, and 40/50-column readability. Use Ctrl-U to clear each trial line.
Exit to return to the original shell. Fixtures may be retained for inspection;
remove only the printed sandbox when finished. No live profile was sourced or
modified. fzf-tab/plugin integration is not covered by this clean-shell exercise.

## Editor, save and destructive-selection checks

Use only an isolated fixture HOME/config/storage. Exercise EDITOR paths/arguments
with spaces; atomic-save behavior; retained invalid/failed edits; concurrent active
changes; and --replace-link preserving its target. No-name save must accept all
case variants of y/as/no, reprompt unknown input and default to cancellation.
A changed stored destination must never be silently overwritten.

Backup picker Tab/Shift-Tab selects multiple entries. Verify displayed count/kinds,
negative/empty confirmation, Escape/Ctrl-C, and --all snapshot exclusion of a newly
created backup. Module browsing must leave active bytes and storage unchanged.
Dry-run tree snapshots include absent directories, locks, backups and provenance.
Human checks remain unverified until actually performed; fixtures are not visual
approval. See the focused test files for automated cases and STATUS.md for results.
