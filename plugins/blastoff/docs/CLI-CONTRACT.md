# Blastoff command contract — 0.1.12 review build

## Paths

| Purpose | Resolution |
|---|---|
| Active config | Nonempty `STARSHIP_CONFIG`, otherwise `~/.config/starship.toml` |
| Storage root | Nonempty `BLASTOFF_HOME`, otherwise `~/.config/blastoff` |
| Themes | `<storage>/themes/<name>.toml` |
| Modules | `<storage>/modules/<name>.toml` |
| Backups | `<storage>/backups/<id>.toml` plus `<id>.json` |

Configured/import/migration paths must be absolute; leading `~` expands to home.
The user specifically requested `~/.config`; this build does not reinterpret
`XDG_CONFIG_HOME` or the Windows AppData directory. `STARSHIP_THEMES` and the old
`~/dots/config/starship` path are not implicitly adopted. The storage root may be
linked, for example `~/.config/blastoff -> ~/dots/config/blastoff`, with no flag or
environment override required. Relative targets, link chains and linked ancestors
of the storage root are supported. Windows directory symlinks and junctions use
the same policy; other reparse types are refused. Each link must resolve to an
existing directory. Broken links, loops, inaccessible/non-directory targets fail
with exit 1; ordinary missing, non-linked directories are created only by mutations.

The root is resolved once per invocation. Themes, modules, backups and the storage
lock use that canonical path; aliases share a lock. Retargeting an alias after
resolution does not redirect that invocation. Storage paths in doctor, mutation
results and new stored-file backup metadata use the canonical target; JSON keys
are unchanged and old backup metadata remains readable. Neither links nor existing
data are moved or converted. More than 40 directory-link redirects are refused.

This is a root-only exception: write destinations beneath storage still refuse
linked `themes`, `modules`, `backups`, lock paths and stored files. Existing
read-only child discovery is unchanged. Active config and installer/profile writes
still refuse symlink/reparse parents. A linked `.config` directory can locate
storage but requires a real-path `STARSHIP_CONFIG` for active writes. The separate
active-file `--replace-link` contract below is unchanged.

## Installer contract

Public commands are `bash install.sh [--dry-run] [--prefix PATH]` and
`bash uninstall.sh [--dry-run] [--prefix PATH]`; no action word or `--yes` is needed.
Shell/legacy prefix entry points default to native Termux `$PREFIX`, other POSIX `~/.local`, or
Windows `$LOCALAPPDATA/Programs/Blastoff` (fallback `~/.local`). These installation
paths do not change application storage/config resolution above.

Public install migrates verified legacy `~/.local` ownership if the selected
prefix differs. Target commit precedes legacy retirement; recorded cleanup resumes
on rerun. Modified owned files, unowned collisions, unsafe paths and unrelated
command shadowing block changes. No automatic downgrade or recursive removal.
Runtime versions are immutable; repeat installs restore missing support or refresh
unmodified supported output. Source checksums are mandatory even for dry-run and
never auto-refreshed. After reviewing deliberate source changes only, rebuild with
`bash scripts/build.sh`; rebuilding cannot bypass runtime immutability.

Discovery prefers native Bash/Fish/man locations. Zsh gets canonical
`share/zsh/site-functions/_blastoff` plus an owned native
`share/zsh/functions/Completion/Unix/_blastoff` copy where available, because
Termux's compiled fpath omits site-functions. Custom prefixes may require minimal
owned PATH/MANPATH/completion hooks. Regular profile encoding and unrelated content
are preserved; linked profiles/targets are refused with manual setup instructions,
not rewritten. Fish uses conf.d; available pwsh gets an absolute versioned manifest
import. Uninstall removes exact owned blocks/files, retaining unrelated profile
edits, user data and `<prefix>/share/blastoff/profile-backups` recovery copies.

Plans show SYSTEM, version, prefix, changes and activation; `--color auto|always|never`
and NO_COLOR precedence apply. Dry-run writes nothing and runs no shell probes
or profiles. Installation never executes profiles automatically. Legacy
`bash scripts/install.sh install --yes` and native `scripts/install.ps1` remain
supported; fresh legacy installs leave activation manual unless already owning
integration. See INSTALLATION.md for compatibility/removal syntax and limitations.
Native Windows runtime verification remains pending.

Lifecycle host detection distinguishes native Termux, WSL, Linux, Windows and
other POSIX hosts; verbose output includes evidence and the interpreter path.
WSL retains Linux paths and ~/.local. Native Termux retains PREFIX; explicit
--prefix bypasses only default-prefix selection, never host compatibility guards.
MSYS2/Git Bash and Cygwin Bash installers return 3 before Python, with instructions
to open native PowerShell 7+ and review .\install.ps1 -WhatIf or .\uninstall.ps1
-WhatIf. They never invoke another shell automatically. Incompatible Bash/Python
hosts return 3 before destination planning. Detection starts no probes/profiles
and is excluded from ordinary application help/version and module import.
Missing Python is status 3 in both frontends, including the Bash command launcher.
The PowerShell lifecycle's private plan includes platform metadata; public
application JSON and ownership formats are unchanged.

## Commands and aliases

| Command | Behavior |
|---|---|
| No arguments; `-h/--help` | Identical full root help on stdout, exit 0, empty stderr; no state reads or dependency subprocesses |
| Global flags without a command | Full root help using the selected color policy; `--json` retains the JSON welcome object; invalid options still fail |
| `--version` | Plain version without state reads or dependency subprocesses |
| `list`, `-l/--list`, `theme list` | Local themes plus optional Starship presets |
| `current`, bare `-t/--theme` | Config/link status, exact local matches, and independently tracked origin |
| `theme apply NAME`, `-t NAME`, `--theme NAME` | Local first, preset fallback; `local:NAME` and `preset:NAME` select explicitly |
| `theme save [NAME]` | Save active edits to an explicit name, or choose interactively using provenance |
| `theme edit` | Back up, edit a private working copy, validate and atomically publish active configuration |
| `theme copy SOURCE NAME` | Copy local/preset source without applying it |
| `theme import ABSOLUTE-PATH NAME` | Validate/import external TOML |
| `theme delete NAME --force` | Back up then delete a stored theme; protect active-file identity |
| `preset list/apply NAME/save NAME AS` | Discover/generate built-in presets; explicit failures remain errors |
| `pick [--fancy [unicode\|ascii] \| --fzf]`; `pick fancy`; `pick fzf` | Select/apply; fancy Unicode default, basic explicit, Gum/numbered fallback |
| `module list`; `module show [NAME]` | List or view saved snippets; no-name show opens an fzf browser |
| `module save MODULE [NAME]` | Extract an explicit module table and descendants |
| `module load NAME`; `module delete NAME --force` | Merge selected table or back up/delete stored snippet |
| `backup create/list/restore ID` | Snapshot, inspect or restore config content |
| `backup delete ID [ID ...]` | Permanently delete explicitly selected backups after confirmation |
| `backup delete --pick` | fzf multi-selection with Tab/Shift-Tab, then confirmation |
| `backup delete --all` | Freeze all eligible backup IDs, then confirmation |
| `migrate ABSOLUTE-DIRECTORY` | Copy valid themes without removing originals; preflight collisions |
| `completion bash\|zsh\|fish` | Static completion script; PowerShell completion registers on module import |

PowerShell retains exact legacy `-help`, `-list`, `-theme` mappings. All other
arguments are forwarded literally. Bash returns the child process status;
PowerShell sets `$LASTEXITCODE`, without terminating the calling shell.

## Shared output, verbose and dry-run

Global `-v/--verbose`, `--dry-run`, `--json`, `--color auto|always|never`,
`--force`, and `--replace-link` work before/after commands and operands.
`--` stops option and alias processing. Names retain the portable 1–96 ASCII
letter/digit/underscore/hyphen rule, start alphanumeric, and exclude device names.

Current/theme-list/save/backup-list/doctor reports use [Dots presentation](../../../docs/presentation.md#application-reports) in human terminals and captured menu readers. Color precedence is explicit application `--color`, then `DOTS_COLOR`, then automatic detection. Nonempty NO_COLOR disables automatic color; explicit always overrides it. DOTS_ICONS independently controls resource icons. Help artwork and application pickers retain their existing color policy, including NO_COLOR overriding forced color. JSON is
undecorated: one result object on stdout; errors are objects on stderr. Verbose
adds stderr diagnostics (JSON records with --json), never configuration contents.
Help/version/completion retain their native text formats; help with --json is
plain text. Existing bounded optional branding is unchanged.

Dry-run validates local inputs and intended destinations and reports `dry_run`,
`operation`, `targets`, `actions`, and `unresolved`. It creates no directories,
locks, backups, temporary editor/preview files or tracking metadata. It never
prompts, opens a picker/editor, or generates a preset. Preset mutations report
that generation/availability remains unresolved; this avoids Starship cache
side effects. Pick dry-run reports unresolved selection. No-name save reports
its known destination or missing name. Read-only commands retain their ordinary
behavior. Installer/uninstaller also accept -v/--verbose and --dry-run.

## Backup deletion

Use IDs, --pick, or --all exclusively. `-y/--yes` bypasses confirmation; --force
does not authorize deletion. No targets returns 2. Both config and stored-file
backups inhabit this namespace; kind is shown with every selected ID.

Before --, sole-target bare `all` is --all; a trailing `y` or `yes` is --yes.
Aliases are case-insensitive. Affirmative aliases alone/in the middle, or all
mixed with IDs, are usage errors. Escape literal IDs using --:

```sh
blastoff backup delete ID1 ID2
blastoff backup delete all yes
blastoff backup delete --all --dry-run
blastoff backup delete --yes -- all y yes
```

Print the selected set/count before `Delete N selected backups permanently?
[y/N]`. Accept y/yes case-insensitively; n/no/Enter/EOF/Escape cancel. Explain
other input and reprompt. Non-TTY or JSON deletion requires explicit IDs/--all
and --yes; dry-run needs no confirmation. Missing fzf never broadens --pick:
use explicit IDs or --all --dry-run instead.

Freeze --all before confirmation; later-created backups are excluded. Derive
paths only from validated IDs beneath backups, never metadata source/link paths.
Require trustworthy matching metadata, regular unlinked members, checksum match,
and no active-config identity alias. Invalid TOML bytes can still be recovery
backups. Valid metadata whose payload is already absent may be removed with a
warning. Missing/malformed metadata and unsafe/mismatched pairs require manual
inspection. Preflight the whole set and abort before deletion on any unsafe item.

After confirmation acquire the storage lock and recheck the frozen fingerprints.
Delete payload before metadata. Per-item failures after deletion starts retain
completed work and report deleted/failed IDs with exit 1. Interruption reports
partial progress; it is not a batch rollback. Cancellation before execution,
empty picker selection and negative confirmation delete nothing (130). --all
with no backups is a successful no-op. No recursive deletion or backups-of-backups.
Backup list reports errors per entry instead of aborting at the first bad record;
its JSON adds `errors` and `missing_payload`, with diagnostics on stderr.
Listing does not hash payloads.

## Editing, provenance and saving

Editor order: nonempty EDITOR, nvim, vim, vi, code, nano. EDITOR may be an exact
executable path with spaces or a quoted executable with arguments. No shell eval,
expansion or shell=True; Windows uses double-quote/backslash argv rules. A broken
explicit editor fails with guidance, never silently falls back. Shell/batch
launchers (.cmd/.bat/.ps1) are refused; choose a directly executable editor.
Known code/code-insiders/codium CLIs get --wait, GUI Vim gets -f; supply waiting
arguments for other GUI editors. Editing requires human terminal input/output
and refuses JSON, except dry-run which only reports target/editor/actions.

Back up the original before launching. Edit a private `.blastoff-edit-*` directory
beside the active path. Reopen the editor's result to support atomic-save editors;
validate bounded regular UTF-8 TOML and the unchanged original before publishing.
The editor receives a private copy beside the physical target. Normal publication
preserves the active link; --replace-link explicitly authorizes conversion, records
its old link and leaves its target alone. A config pathname inside the
stored theme/module directory is refused. Missing config starts empty; invalid
original content may be backed up for repair, but only valid output is published.
Failed, invalid, interrupted or concurrently conflicted edits remain at an exact
reported recovery path. Editors may leave additional artifacts, which are retained
rather than recursively removed. See [recovery](RECOVERY.md).

State is `<storage>/state/provenance/<normalized-physical-target-hash>.json`, version 1.
Explicit --replace-link uses the configured pathname instead.
It records the pathname, last-loaded kind/name/source digest, local source
fingerprint, separate local save destination/baseline, and last-confirmed active
digest/fingerprint. It is atomically written only after content succeeds.
A `.pending` sibling marks an incomplete multi-file operation. Such tracking
cannot authorize automatic save; reads do not repair it. On post-content state
failure, report the failure and inspect content rather than assume rollback.
Explicit successful apply/save/restore reestablishes completed state.

Apply/pick record the actual local/preset source, even for identical-content
apply. Edit and module load retain origin. Saving active content establishes a
local save destination without changing last-loaded history. Copy/import/preset
save/migration do not reassociate active configuration. Config backup metadata
optionally snapshots provenance. Restore uses valid same-path/store provenance;
older/foreign/corrupt snapshots give unknown origin. External active edits retain
history but are marked changed. Missing/corrupt/future state never triggers a
library-wide guess or a write. Source/destination identity changes invalidate
implicit overwrite authority.

`current` preserves config/exists/symlink/matching_themes and adds `provenance`:
status, origin, last_loaded, save_target, changed_since_load, external_change,
and matches_source. Last loaded is history, not a current-match claim. Its
existing explicit exact-match query still reads local themes; edit/save and
provenance inspection never depend on that library scan.

`theme save NAME` remains explicit; collisions need --force and are backed up.
No-name save requires a human terminal. If a valid unchanged local target is
known, ask `Save edits to "<theme>"? [y/as/N]`. Case-insensitive y/yes authorizes
that backed-up replacement without another force flag; a/as requests another
name; n/no/Enter cancels with `Save cancelled.` (130). Unknown input reprompts.
Missing/renamed/deleted/changed/unknown targets and preset origins lead to a local
save-as name or cancellation. Never overwrite a built-in preset.

Save-as asks `Save as theme name (empty cancels):`; invalid names reprompt and
collisions require `Replace existing theme "<name>"? [y/N]`. Capture/recheck both
active and destination fingerprints, plus tracking state, across prompts. --force without a name does
not skip this decision. Explicit NAME --force retains explicit overwrite behavior
but warns about a detected change since loading and refuses concurrent changes.

## Mutations and recovery

Apply copies validated bytes into a regular config; it never links or edits the
stored source. Changed active writes are backed up; identical regular content
needs no content backup. Forced stored replacements and stored deletions are
backed up. Theme/module deletion refuses active-file identity, including hardlinks.
Normal active-file symlinks are preserved, including relative/chained links to
regular files. Link retargeting, missing targets, loops, special objects, library
targets and unsupported reparse types are refused. Active leaf conversion needs
--replace-link; linked parents remain refused.

Backups contain UTC/random IDs, SHA-256, original source and optional link text.
No automatic pruning. Restore accepts config backups only and restores regular
content, not a link relationship. Recover stored themes with theme import of an
inspected backup; inspect/validate module backup bytes before copying them.

Canonical storage locks serialize writers; active writes and active-save/edit
also lock beside the physical config target, so aliases share a lock. Stale locks are never broken automatically. Expected
fingerprints detect cooperating/concurrent changes. Per-file atomic writes and
pending provenance markers are not multi-file crash transactions or protection
against a malicious final-window path swap. Files are fsynced before replacement;
parent-directory fsync remains outside the existing contract.

## Modules

A snippet contains one explicit table such as `[directory]`, `[git_branch]`,
`[custom.clock]`, plus its nested tables. A store name can differ from the module
path, e.g. `module save directory compact-directory`.
Loading replaces the whole saved module table, not just its supplied keys.
Settings outside that module remain equal and their text is retained. Table
blocks can move to the end; trailing comments within a removed block move with
that block or are replaced along with it. This is not a format-preserving editor
for comments associated with replaced tables.

The parser validates the complete config before and after merging and verifies
unrelated values. Headers are found outside strings/comments/array values, then
parsed as TOML. Root dotted keys and inline module tables are refused where the
selected module cannot be extracted/replaced losslessly. Convert them to an
explicit `[module]` table after a backup. No regex-only TOML rewriting, no
normalizing the whole document and no execution of Starship custom commands.
Syntax validation does not guarantee the installed Starship version recognizes
every option or module. Palettes/formats referenced by a snippet must already
exist in the target config; module loading does not rewrite global prompt format.

## Module viewing and pickers

Named module show is read-only. Human terminals get name plus bat/plain TOML;
redirected output is the complete original bytes without headings or decoration,
even with forced color. JSON returns name/path/toml. Display reads require bounded
regular files and UTF-8, but viewing does not validate Starship schema or merge.
Without NAME, fzf browses saved modules; Enter displays one, Escape/Ctrl-C cancels.
No modules is exit 1; no fzf is 3 with named-command guidance; noninteractive/JSON
browsing is 2. Viewing never loads a module.

Pick requires human terminal input/output except dry-run. fzf is preferred, then
Gum, then a numbered menu for ordinary/fancy invocation. Explicit --fzf requires
fzf (exit 3 when unavailable) and never falls back. Escape/Ctrl-C cancels; numbered fallback accepts empty
input, Escape then Enter, EOF or Ctrl-C. Empty choices return 1. Basic fzf honors
compatible user appearance/search/navigation settings, selected by --fzf or
`pick fzf`. Fancy is the default; --fancy [unicode|ascii] keeps the Blastoff palette and connected borders; Unicode falls back on non-UTF/dumb
terminals. `pick fancy` aliases bare --fancy. Assets/branding remain unchanged.

Both styles show TOML previews initially; Ctrl-X toggles. Fzf's responsive
`right,60%,border-left,wrap,<60(down,45%,border-top,wrap)` switches below when the
right pane would have fewer than 60 columns, including terminal resizing. This
normally leaves about 40 columns for the list and 60 for code. Short terminals also begin with visible previews. Gum/numbered fallbacks have source labels but no pane.

Read FZF_DEFAULT_OPTS_FILE then FZF_DEFAULT_OPTS (bounded 64 KiB, shell-style quotes
without execution; embedded hex-color # is preserved). Allow reviewed appearance/search options and simple
nonexecuting navigation/query-edit bindings. The consumed FZF_DEFAULT_OPTS_FILE/FZF_DEFAULT_OPTS and candidate-source
FZF_DEFAULT_COMMAND are removed from the child environment to prevent replay. Drop automatic selection/filter/exit, history writes, walkers/default
commands, listeners, command/event actions, output/field remapping, inherited
preview/shell commands, and unknown options. Report omissions briefly, with
verbose details. Enter/Escape/Ctrl-C/Ctrl-X and multi-select Tab/Shift-Tab are
reserved. Precedence: file, environment, selected fancy styling,
then safety/keybindings and color controls. GUM settings remain isolated.

Only fixed shipped helpers with numeric IDs form preview commands; paths are
shell-quoted, labels/names are data on stdin, and selected IDs are checked against
the supplied inventory. Helpers resolve beside installed core under isolated
Python. Shell startup hooks are removed. Windows requires a native PowerShell preview shell, using the invoking host when
available; a missing shell is an explicit dependency error. Native execution remains deferred.

Previews are sanitized source, never rendered prompts or theme commands. Local
reads retain 4 MiB bounds; displayed content is limited to 64 KiB/200 lines/512
characters per line. Bat reads sanitized stdin with explicit TOML/plain style,
no paging; normal bat configuration/theme/cache discovery is retained. CLI preview
requirements override paging/language/style/wrapping/color only; failure/missing bat
uses plain text. BAT_THEME, BAT_CONFIG_PATH, BAT_CONFIG_DIR and BAT_CACHE_PATH remain
available; no bundled theme or user cache rebuild is forced. Only trusted SGR color is
retained. Preset previews run only `starship preset NAME` with bounded pipe reads
and a two-second deadline. Successful/failed previews cache only within a private
session: at most 64 visited entries of at most 256 KiB each (16 MiB total).
Normal exit removes the temporary session; forced death can leave OS-temp files.
Apply rereads and validates the selected source. A timeout is not a command sandbox;
rendered prompts are deliberately excluded. See TERMINAL-UX.md and RECOVERY.md.

## Optional presets, completion and status

Combined list/theme-list/pick preserve local choices if preset discovery fails.
Human output warns once on stderr; JSON listing adds preset_discovery status/error
without a separate warning. An available empty preset list is distinct from
unavailable discovery. Combined listing exits 0 even empty; pick with no choices
exits 1. Explicit preset requests fail with 3 on missing/failed/timed-out/unusable
Starship, 1 on unknown preset or invalid TOML. Interruption remains 130.
Preset names must satisfy portable-name validation; lists are sorted/deduplicated.
Discovery has a ten-second timeout. Ordinary generated preset output retains the
4 MiB post-collection bound and assumes a trusted installed Starship executable.

All four shell completions are positional/offline, never invoke an application
command, Starship, an editor or the network, and never create storage. PowerShell
7.0 Unix without regular-file metadata uses a bounded private Python filename
helper only for dynamic names; static completion/import starts no tools. Complete commands,
flags, color/fancy values, local names/source prefixes, module show/load/delete,
paired backup filenames for restore/delete (including repeated IDs), delete aliases,
and shell-appropriate paths. Destination names and module-save routes remain free
text; live preset names are not discovered. Backup names are unverified until
execution. Reserved alias IDs are offered as literal IDs only after --. Root
storage links work; linked child directories/files and unsafe names are excluded.
PowerShell retains network-root/reparse guards and uses native TabExpansion2 tests
where an engine exists; native Windows remains deferred.

| Exit | Meaning |
|---|---|
| 0 | Success/no-op or reported dry-run (possibly with unresolved choices) |
| 1 | File/TOML/collision/lock/safety or partial-operation failure |
| 2 | Usage/invalid name/required interaction or authorization missing |
| 3 | Required tool/preset/editor/picker process failure |
| 130 | Cancellation/interruption; irreversible deletion may report partial progress |

Native wrappers inherit streams and cancellation. PowerShell's function sets
$LASTEXITCODE, not its parent's process code. Native Windows, version-range and
human terminal checks remain separate from Termux fixtures.

## Presentation and output rules

The same exclusive --fancy [unicode|ascii] / --fzf options apply to `module show`
without NAME and `backup delete --pick`. No bare presentation aliases are added to
those commands: module names/backup IDs keep their meanings. Supplying presentation
flags with named module show or non-picker deletion is usage error 2. Opposing
pick aliases/flags also fail before discovery. Dry-run needs no optional tool.
Fancy owns height 90%, reverse layout, border/label and purple/pink colors. Basic
sets no Blastoff palette, height or layout. Both reserve safe candidate fields,
Enter/Esc/Ctrl-C/Ctrl-X, preview command, and multi-select Tab/Shift-Tab. Compatible
bindings survive individually when another binding conflicts.

Human output is the default, including backup list and redirected output. JSON
is explicitly requested: `backup list --json` or `--json backup list`. Backup
human entries show complete ID, creation time derived from a recognized ID (unknown
otherwise), kind, stat size, source and any existing reason. Missing payload and
malformed entries are identified; partial errors retain exit 1. JSON schemas are
unchanged; errors/verbose records stay on stderr. No automatic JSON fallback is
allowed in the shared emitter. Help/completion and redirected module TOML retain
their documented raw formats. Report color follows the Dots precedence above.

Human terminal/popup backup lists have a heading/count and separated records with blue IDs/labels, resource-styled source paths and semantic missing/invalid notices. Complete IDs and values wrap at narrow widths. Ordinary redirected output retains its existing unindented IDs, two-space metadata and combined Kind/Size row when it fits. Preserve Source/Reason and missing/invalid-entry notices.
Dates are parsed from recognized UTC ID timestamps, never local time or file mtimes,
and displayed as YYYY-MM-DD HH:MM:SS UTC; unknown dates stay unknown. Sizes are
exact integer bytes. No metadata migration or JSON fields are added. Automatic
redirected output is plain; explicit --color always selects the styled human report even with NO_COLOR. Shared formatting sanitizes text before adding accents.

Root PowerShell commands are `.\install.ps1 [-WhatIf] [-Verbose]` and
`.\uninstall.ps1 [-WhatIf] [-Verbose]`, with -DryRun equivalent to WhatIf.
-ModuleRoot chooses a CurrentUser Modules parent; install accepts -ProfilePath or
-NoProfile. This self-contained layout is independent of shell-prefix ownership.
See POWERSHELL.md for exact profile, upgrade/repair, retention and parity rules.
PowerShell 7+ import/static completion launches no runtime/tools; dynamic filename
completion is bounded and cached in memory. Native platform gates remain separate.

## Theme-list identity and readability — 0.1.10

Human `list`, `theme list`, `-l` and `--list` retain grouped, sorted complete
identifiers. Human terminal/popup reports use muted prefixes, blue names, cyan headings/counts, green current markers and yellow modified/history markers. The Dots report color policy above applies; ordinary redirected output retains its existing readable format.

Trusted path-associated provenance supplies the identity, keyed by kind and name.
Unchanged active bytes receive `[current]`; edits receive `[last loaded; modified]`.
A local source whose bytes differ from the loaded digest adds `source changed`;
a missing/unsafe source adds `source unavailable`. Missing active content is
marked `last loaded; active configuration missing`. These markers describe
history, not authorization to overwrite. Save-as does not change last-loaded
history or move the marker to the saved copy. No preset contents are regenerated
to verify the installed Starship version's current preset definitions.
If an identified source is absent from the choices, an `Origin:` line includes
its complete identifier and `not listed`, including when discovery is unavailable.

Missing/corrupt/pending/unknown provenance never guesses a theme from library
contents. Show a concise unknown/unavailable status; `blastoff current` remains
the explicit local exact-match query. Unreadable configuration does not suppress
choices or fail the listing; verbose diagnostics explain the cause on stderr.
Stat changes during inspection suppress a definitive current marker and suggest
retrying. Like any listing, this is an observation, not a lock or future guarantee.

Human inspection reads only the record, active config and at most one tracked
local source, with stat snapshots around inspection; no writes, extra subprocesses
or library-wide content hashing. Existing preset name discovery remains unchanged.
JSON skips this annotation entirely and retains its existing schema and diagnostics.

### Default-path and alias compatibility (0.1.12)

`~/.config/starship.toml` remains the default regardless of XDG_CONFIG_HOME. Explicit
STARSHIP_CONFIG overrides remain supported. `current` and `doctor` retain the
configured `config` field and add `resolved_config` (null when doctor cannot safely
resolve it). Human views and active-write dry runs identify the physical target.
Read-only commands do not create tracking or migrate records.

Canonical target history is preferred. Compatible legacy configured-path history
is readable when canonical history is absent; conflicting, invalid or pending
records do not authorize implicit save. Successful explicit operations preserve
superseded alias records/markers under unique `.legacy-*` names before completing
canonical tracking. Interrupted publication retains the pending marker. Backups
include configured/physical paths and the observed link text as evidence; restore
never uses recorded paths to recreate or retarget a link.
