# Terminal UX — 0.1.12

Bare `blastoff`, `-h`, and `--help` produce identical full root help, exit 0,
and empty stderr. Global flags without a command also show full help, except
`--json`, which retains the JSON welcome object. Invalid flags/values still fail.
Root and nested help share the supplied
`lib/artwork/logo`: a 37-column, 13-row Braille wordmark. Its bytes remain unchanged;
the renderer applies the left-to-right purple (`101,30,255`) to pink (`255,67,191`)
gradient at display time. It fits terminals at least 37 columns wide, including
40-column Termux screens. Older artwork and `.local/logo` originals are retained
unchanged but no longer selected for the header. No logo scripts or ANSI assets
are executed/replayed. Reads are bounded to 8 KiB/16 rows and a safe character
allowlist; missing/invalid artwork cannot break help. Narrow/dumb/non-Unicode
terminals and redirected output use a compact ASCII fallback. No Nerd Font is
required; Braille patterns use ordinary Unicode terminal glyphs.

Implicit and explicit help never discover presets, read application configuration or launch
subprocesses. Help now has task-based command groups, colored headings and names,
readable plain descriptions, and no duplicated brace-enclosed command list.
All grammar/options/descriptions/aliases remain sourced from the actual parser.
Color follows the existing policy: auto only on TTYs, NO_COLOR always wins, and
`--color always` may force ANSI when redirected. Both `-h --color always` and
`--color always -h` work, including nested help. `--json` suppresses decoration;
help remains text, while no-command JSON remains the welcome object.

## Picker and source display

Bare `pick` uses fancy Unicode. Explicit `pick --fzf` / `pick fzf` uses basic
fzf without forcing a palette, border or reverse layout.
Compatible FZF_DEFAULT_OPTS_FILE settings precede FZF_DEFAULT_OPTS. Reviewed
appearance/search/navigation settings survive; executable/event actions,
auto-selection/filtering, listeners, history writes, field/output changes,
preview commands and unknown settings are omitted. A warning explains omissions;
-v adds detail. Final safety/keybindings and NO_COLOR override conflicts.

`pick --fancy`, `pick --fancy unicode` and `pick fancy` select purple/pink styling
with connected Unicode borders. `pick --fancy ascii` selects ASCII; non-UTF/dumb
terminals fall back. Both styles show previews initially. Ctrl-X toggles them.
A 60-percent right pane needs at least 60 columns; otherwise fzf uses a 45-percent
lower pane. Native alternative-layout handling responds to resizing without a
layout subprocess. User margins/height reduce the available area. Short terminals
retain a visible preview until the user toggles it.

`module show` uses the same fzf source browser; Enter displays the selected module
without loading. `backup delete --pick` adds Tab/Shift-Tab multi-selection and a
separate default-No confirmation showing IDs/kinds/count. Missing fzf for these
commands explains explicit-target alternatives. Theme pick retains Gum/numbered
fallbacks with source labels and cancellation, but without preview panes.

Previews show sanitized TOML, never rendered prompts. Numeric row IDs address a
private inventory; theme names, paths and labels never form shell commands.
The shipped helper resolves next to the installed core. Starship is used only for
on-demand preset generation, with bounded reads/timeouts and session-local caches.
Bat reads sanitized stdin, with TOML/plain style, normal configuration and no pager;
missing/failing bat uses plain source. Display bounds are 64 KiB/200 lines/512
characters per line. Cache at most 64 visited results of 256 KiB each (16 MiB).
Both failed and successful results cache; application rereads the chosen source.

Rendered prompts remain excluded because custom conditions/commands can execute.
Temporary paths and timeouts do not provide an execution sandbox. No preview
applies a theme, modifies the active config, or updates provenance.

Named `module show NAME` displays full bounded source with a terminal heading;
redirected output is original TOML bytes without heading/ANSI or a bat subprocess.
JSON returns name/path/toml. Current status shows history separately from matches;
known origin survives edits. Doctor remains read-only availability information.

## Isolated human checks

Run the disposable helper, never a live picker merely to test it:

```sh
python3 scripts/interactive_check.py --backend fzf --expect select
python3 scripts/interactive_check.py --backend fzf --fancy unicode --expect cancel
python3 scripts/interactive_check.py --backend fzf --fancy ascii --expect cancel
python3 scripts/interactive_check.py --backend fzf --feature module --expect select
python3 scripts/interactive_check.py --backend fzf --feature backup --expect cancel
```

At 40, 50, 100 and 120 columns, check readable source/list regions and resize while
open. Toggle Ctrl-X twice. Check connected Unicode corners/separators and ASCII
fallback, Tab/Shift-Tab selection, Escape/Ctrl-C, default-No confirmation, and
terminal cursor/echo restoration. Record terminal app, dimensions, tool versions
and touch-keyboard behavior. Automated PTYs do not establish font quality or human
approval. Native fzf may be unavailable on a particular host; record that gap.

Welcome/help still need the existing 37-column logo versus narrow ASCII check,
NO_COLOR, redirected help and reset-color checks. Branding assets are unchanged.
Native Windows rendering/editor/preview behavior remains deferred.

## Updating an installed runtime

The current version is 0.1.12; source edits alone do not upgrade an installation.
After source/archive verification, review `bash install.sh --dry-run` and use
`bash install.sh` only when a real upgrade is wanted. Native Termux defaults to
PREFIX; custom prefixes and ownership/profile safeguards remain unchanged.
See INSTALLATION.md, RECOVERY.md and STATUS.md for scope and actual evidence.

## Configuration inheritance and diagnostic checks

The 0.1.7 audit confirmed bat configuration was explicitly disabled and its BAT
overrides were filtered. The fzf option lexer also treated embedded color `#`
as a comment. These application bugs are corrected in 0.1.8. Separately, the
previous HOME/XDG test scaffold could hide user configuration and custom caches;
NO_COLOR and a stale installed runtime can also change observed appearance.
No installed fzf is available in this implementation environment, so its native
option/version compatibility and the user palette remain acceptance gates.

Both browser styles preserve bat's normal theme/config/cache discovery, including
BAT_THEME, BAT_CONFIG_PATH, BAT_CONFIG_DIR and BAT_CACHE_PATH. Previews disable
paging, use TOML/plain decoration and sanitize bounded output; they do not disable
bat configuration. The fzf options file precedes environment options, followed by
fancy-owned presentation (if selected), then selection/preview/cancellation and
color controls. Inline # in color values is preserved. Executable/listener/history/
auto-accept/output-remapping hooks remain filtered; verbose stderr names omissions.
Fancy owns palette, reverse layout, 90% height and connected borders/label. --fzf
adds no Blastoff palette. Neither style overrides the user's bat theme.

Use --verbose to see resolved tool/config/cache paths and relevant overrides once
per browser session. Shell aliases/functions are not executable configuration or
exported environment; child processes cannot inherit them. Blastoff never sources
a profile or uses eval to discover them. NO_COLOR is reported and honored.

The visual helper defaults to deterministic fixture isolation. That mode changes
HOME/XDG and intentionally hides real tool configuration. To check your appearance
without using live Blastoff data:

```sh
python3 scripts/interactive_check.py --backend fzf --tool-config user --fzf --expect cancel
python3 scripts/interactive_check.py --backend fzf --tool-config user --fancy unicode --expect cancel
python3 scripts/interactive_check.py --backend fzf --tool-config user --feature module --fzf --expect select
python3 scripts/interactive_check.py --backend fzf --tool-config user --feature backup --expect cancel
```

User mode preserves actual HOME, XDG, BAT/FZF settings and PATH, while active config,
store, provenance and Starship cache are disposable. It does not rebuild bat's
cache, edit settings, or change the calling shell. A fixture-only appearance
failure is not proof of broken inheritance. Record command/module identity too:
source edits do not upgrade a PATH-resolved installed command.

## Backup-list readability — 0.1.9

Use distinct colors for identifiers, labels, and values where that improves
readability. Reuse the shared Blastoff accents, sanitize data before styling,
reset each segment, and keep the same understandable layout without color.

The backup ID uses bright white; labels (including Source/Reason) use purple;
values use bright pink; | uses dim terminal foreground. Each accent resets.
The following example shows only the main fields; actual source/reason and
missing-payload information are retained when applicable:

```text
20261013T160722Z-68908267f7dd
  Created: 2026-10-13 16:07:22 UTC
  Kind: stored | Size: 6056 B

20261014T000001Z-123456789abc
  Created: 2026-10-14 00:00:01 UTC
  Kind: config | Size: 128 B
```

At narrow widths, Size moves to a separate two-space-indented line and | disappears.
IDs and timestamps are not truncated. Very small terminals can still naturally
wrap a complete ID or timestamp. Width is measured before adding ANSI. UTC comes
from the writer's UTC ID, not relabeled local time; byte counts are exact. JSON and
error behavior stay unchanged. The plain layout has the same spacing and values.

Read-only source preview (NO_COLOR is removed only for this child):

```sh
env -u NO_COLOR bash /data/data/com.termux/files/home/repos/blastoff/bin/blastoff backup list --color always
```

Also review --color never and a redirected/default-auto listing. Nothing here
installs the source or changes backups, active configuration, profiles or storage.

## Theme-list readability — 0.1.10

`list`/`theme list` now keep `local:` and `preset:` dim purple while names use
bright white. The identified name and its marker use bold Blastoff pink. Resets
separate every segment. No fonts, new palette or completion syntax are required.

```text
THEMES
  local:aurora
  local:blastoff  [current]
PRESETS
  preset:pastel-powerline
```

After an active edit the same origin is `[last loaded; modified]`. Independently
changed sources receive `source changed`; unavailable sources/configuration are
reported without a false current claim. Untracked configurations show unknown;
`blastoff current` explicitly checks local exact matches. Preset markers refer
to loaded bytes, without regenerating preset definitions. Saving a copy retains
the loaded origin. Unknown/absent origins may appear in a status/Origin line.

Read-only source preview (uses existing storage/config paths; never applies):

```sh
env -u NO_COLOR bash /data/data/com.termux/files/home/repos/blastoff/bin/blastoff list --color always
bash /data/data/com.termux/files/home/repos/blastoff/bin/blastoff list --color never
```

Check prefix/name contrast, full identifiers, pink markers and clean subsequent
output. Compare plain and redirected output. `env -u NO_COLOR` applies only to
that child command. Source edits do not update an installed command. Human visual
acceptance and native PowerShell appearance remain pending until actually reviewed.
