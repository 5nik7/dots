# androidots

## Location lookup

`bin/termux-geo` obtains the phone's coordinates with Termux:API and resolves city, state, postal code, and address through Nominatim. It defaults to a 60-second device cache and network location. Terminals get Dots-style output and delayed progress; pipes get JSON. `get city`, `format '{city}, {state} {postcode}'`, and `--coords` provide script inputs; coordinate-only queries skip the address service. `--cached` is suitable for nonblocking status consumers. Requires Bash 5.3+ and the documented CLI/Android dependencies. See [options, service restrictions, and setup](docs/termux-geo.md).

`termux-geo completion --all --install` installs static Bash/Zsh/Fish completions under this checkout's `shells/<shell>/completions`. The parent Dots Termux shell configurations load these local directories. Existing changed completion files are backed up; start a new shell after configuration changes. See [completion installation](docs/termux-geo.md#shell-completions).

Timeout errors identify the failing phase and return status 124. Use `termux-geo --coords --refresh` to check device acquisition independently of the address service; device responses are bounded without restricting the native API process's file-size limit.

`termux-geo --help` uses Dots colors for headings, options and examples, honoring the existing color settings. Redirected help and standalone use without the Dots library remain plain by default.

## Android status indicators

`bin/termux-wifi-status`, `bin/termux-cell-status`,
`bin/termux-notification-status`, `bin/termux-location-status` and `bin/termux-volume-status` provide cached
Nerd Font icons, ASCII labels, getters, templates and JSON for tmux or Starship.
They share `lib/termux_status/`. Cellular and notification polling requires an
initial successful `--refresh`; location reports unknown when Android blocks
the toggle query. The parent Dots bar disables all five modules and retains battery with a daylight-colored clock. The standalone network adapter remains available for custom consumers and unreloaded configurations; its uncertainty, stale markers, signal colors and permission gates are unchanged. Registered-cell signal alone does not establish active data or internet access. Volume reads the music stream by default; `--stream ring` selects ringtone volume without changing device settings. See [setup, fields, integrations and completions](docs/termux-status.md).

## Git configuration overlay

The parent `dots:git` resource owns the common Git configuration and its
`config/git/termux` platform overlay. The former Androidots Git resource and
legacy `~/.gitconfig` / `~/.config/git-termux/config` links are handled by the
parent's bounded, journaled `tools/migrate_git_config.py` helper. Historical
receipt IDs remain readable for recovery; current platform resources use
`termux:NAME`. Credential-helper and safe-directory values are preserved, not
printed or executed by migration.

## Default tmux session and bar

`bin/termux-bar` creates or reattaches a default tmux session specific to the current Termux tab. The Dots Bash/Zsh startup hook calls `termux-bar --auto` for original interactive app shells; child shells, tmux panes, SSH and scripts skip automatic attachment. Fish is unchanged. Set `DOTS_TERMUX_AUTOSTART=0` before shell initialization to opt out. `--help` works without tmux or session discovery.

With the Dots tmux configuration, the default session shows the daylight-clock/battery row and the Termux-number/window row, but hides its session-name badge. Project sessions selected with `t` keep their names. The current Termux number expands with its optional tmux name and windows, followed by later Termux numbers; colored blocks and spaces separate the groups. During automatic attachment, `exit`/`q` on the final pane also exits the outer shell without switching sessions. Other panes and unrelated sessions retain their normal lifetime. Detach to return to the outer shell, then run `~/dots/androidots/bin/termux-bar` to reattach. Startup does not loop after detaching or reloading shell configuration.

Requires Python 3, tmux, sibling `bin/termux-sessions`, readable procfs and inherited `TERMUX_APP__PID`. The launcher identifies the tab by its root process PID and start time, not its changing display number. It reuses only marked default sessions, preserves their windows and directory, refuses unmarked name collisions, and retains detached sessions without cleanup. Failure leaves a usable shell; no packages, service, shell links or tmux configuration are installed. The bar itself remains tmux's status display, so it disappears when detached.

Run `python3 -B tests/test_termux_bar.py` for isolated mocked identity/failure tests. The parent Dots `tools/test_termux_autostart.py` covers native Bash/Zsh/tmux with simulated Termux identity and private servers. Actual Android new-tab startup remains a manual check.

## Termux session reporting

`bin/termux-sessions` takes a fresh snapshot of running Termux terminal sessions.
It requires Python 3.9+ (`pkg install python` if needed), readable `/proc`, and the
`TERMUX_APP__PID` environment variable inherited from Termux. No Termux:API plugin,
background tracker, or shell startup hook is needed.

```sh
~/dots/androidots/bin/termux-sessions          # termux:3
~/dots/androidots/bin/termux-sessions --count  # 3
~/dots/androidots/bin/termux-sessions --list   # PID, TTY, COMMAND table
~/dots/androidots/bin/termux-sessions --json   # count and sessions array
```

Use the full path, or add this repository's `bin/` directory to your `PATH`.
The examples below assume the checkout is at `~/dots/androidots`; adjust that
path if necessary. Output has no colors and ends with a newline. JSON session
records contain `pid`, `tty`, and `command` (the root process name).

Only live terminal-owning session leaders directly beneath the inherited Termux
app process are counted. Nested shells, tmux panes, editor terminals, background
commands, and exited tabs retained in the drawer are excluded. Lists are sorted
by process start time, then PID; they do not reproduce drawer names, numbering,
or the selected tab. An `exec` replacement changes the reported process name.
Snapshots can change while processes start or exit. This reports the inherited
app instance; a missing or stale environment in a long-lived tmux server must be
refreshed from a current Termux shell.

A valid empty snapshot prints `termux:0` (or `0` with `--count`) and exits 0.
Discovery errors leave stdout empty, explain the failure on stderr, and exit 1;
invalid arguments exit 2. Prompt examples suppress error messages for display;
run the helper directly to diagnose missing output.

### Getters and templates

```sh
termux-sessions get current
termux-sessions --get total
termux-sessions -g tty
termux-sessions format '{number}/{total}'
termux-sessions --format '{previous} < {current} > {next}'
termux-sessions -f '{number}: {command} on {tty}' --pid "$$"
termux-sessions --get number --tty /dev/pts/1
termux-sessions --fields
```

`get`/`--get`/`-g` print one value; `format`/`--format`/`-f` combine values in a
template. These modes are mutually exclusive with `--count`, `--list`, and
`--json`. The existing JSON shape and list columns are unchanged.

| Field | Value |
| --- | --- |
| `current`, `number` | Calling session's one-based position in creation order |
| `previous`, `next` | Neighboring session numbers, wrapping at either end |
| `total` | Number of running Termux sessions |
| `pid` | Calling session's root process ID |
| `tty` | Calling session's terminal, such as `pts/1` |
| `command` | Calling session's root process name |
| `first`, `last` | First and last session numbers |

Numbers can change when sessions close and do not identify drawer positions.
With one session, current, previous, next, first, and last are all `1`.
Use `{{` and `}}` for literal braces. Only plain `{field}` placeholders are
supported; conversions, indexing, attributes, format specifications, unknown
fields, and malformed braces are usage errors (exit 2). Literal template text
is preserved; control characters in process names are replaced with `?`.

The helper follows calling-process ancestry. `--pid PID` selects a process or
descendant of the desired Termux session; `--tty pts/N` or `--tty /dev/pts/N`
selects its terminal directly. These selectors are mutually exclusive and work
with getters or templates. In tmux, automatic resolution validates the calling
pane and uses its session's single attached non-control client. Multiple clients,
a detached session, stale pane context, or failed tmux queries require an explicit
selector. Automatic tmux queries have a combined 250 ms time limit.

If a requested field cannot be resolved, stdout is empty and the command exits 1
with a diagnostic; a format never prints partial results. `total` remains usable
without current-session context, and `first`/`last` only require a nonempty snapshot.
The helper does not query tmux for formats or getters that need no current session.

### Shell completions

```sh
termux-sessions completion bash                  # print Bash source
termux-sessions --completion zsh                 # print Zsh source
termux-sessions completion fish --install        # install for Fish
termux-sessions completion zsh --install --dir "$HOME/my-completions"
termux-sessions completion --all --install       # install all three
termux-sessions completion --all --install --dir "$HOME/completion-export"
```

Generation prints only shell source, works without a Termux session environment,
and does not require the target shell to be installed. Completion is static: Tab
does not execute the helper or scan sessions. It suggests options, aliases, fields,
template placeholders, shell names, and destination directories.

| Shell | Default installation target |
| --- | --- |
| Bash | `${XDG_DATA_HOME:-$HOME/.local/share}/bash-completion/completions/termux-sessions.bash` |
| Zsh on Termux | `${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions/_termux-sessions` |
| Fish | `${XDG_CONFIG_HOME:-$HOME/.config}/fish/completions/termux-sessions.fish` |

Bash honors the first nonempty colon-separated `BASH_COMPLETION_USER_DIR` entry
as its base instead of the default `bash-completion` directory. Without a Termux
prefix, Zsh uses `${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions`.
For Zsh, ensure the destination is in `fpath` before `compinit`, then rebuild
completion discovery (in Dots, `rlcs`). Dots already includes Termux's
`site-functions`. Bash needs `bash-completion` enabled or the generated file
sourced explicitly; Fish loads its user completion files automatically.

`--dir` names the exact directory, including for `--all`; the three filenames are
distinct. `--all` requires `--install` and excludes an individual shell argument.
Installation creates directories and reports destinations on stderr. Identical
files are unchanged. Differing regular files are backed up beside the target as
`FILENAME.bak.UNIQUE` before atomic replacement; symlink and non-regular file
targets are rejected. All destinations are checked before writing. A later write
failure exits 1 and leaves earlier successful installs and reported backups intact.
Restore a backup by copying it over its corresponding completion file.
The installer does not modify shell startup files or reload running shells.

### tmux example

Add the command substitution to your existing status format. This standalone
example appends a segment to `status-right` and refreshes every five seconds:

```tmux
set -g status-interval 5
set -ag status-right ' #("$HOME/dots/androidots/bin/termux-sessions" --tty "#{client_tty}" --format "{number}/{total}" 2>/dev/null)'
set -ag update-environment ' TERMUX_APP__PID'
```

The explicit client TTY selects the viewing Termux session even with multiple
clients. For a total-only segment, use the helper without selectors or formatting.
The tmux server needs `TERMUX_APP__PID` in its global environment for status jobs.
New servers inherit it; refresh an existing server explicitly from a current
Termux shell with `tmux set-environment -g TERMUX_APP__PID "$TERMUX_APP__PID"`.
The update rule also copies it into the tmux session environment on attachment,
which is useful for newly created panes; it does not replace that global refresh.
Allow enough `status-right-length` for the added segment. See the
[tmux manual](https://man.openbsd.org/tmux#status-interval) for status formatting.

### Starship example

```toml
[custom.termux_sessions]
description = 'Running Termux terminal sessions'
command = '"$HOME/dots/androidots/bin/termux-sessions" --format "{number}/{total}" 2>/dev/null'
when = 'test -n "$TERMUX_APP__PID"'
shell = ['sh']
format = '[$output]($style) '
style = 'bold cyan'
```

Starship refreshes this when drawing a prompt. Inside tmux this requires a unique
attached client, or an explicit selector. Use `--get total` if you only need a
count regardless of client ambiguity. If your top-level `format` already
includes `$all` or `$custom`, the module is included automatically; otherwise add
`${custom.termux_sessions}` where you want it displayed. Keep output escaping
enabled. See [custom commands](https://starship.rs/config/#custom-commands).

Run the isolated helper checks from this repository root:

```sh
python -B -m unittest discover -s tests -p 'test_termux_sessions.py'
```

## EXTRA KEYS

termux.properties

```Java Properties
###############
# Extra keys
###############

extra-keys = [[ \
  {macro: 'CTRL c', display: "✖️", popup: {macro: "CTRL d", display: "exit"}}, \
  {key: '#', popup: '' }, \
  {key: '%', popup: '' }, \
  {key: '&', popup: '' }, \
  {key: '*', popup: {macro: "", display: ""}}, \
  {key: '$', popup: '^' }, \
  {key: ":", popup: ";" }, \
  {macro: 'ESC', display: "ESC", popup: {macro: "INS", display: "INS"}} \
], \
[ \
  {macro: "CTRL b", display: "™️", popup: {macro: "CTRL b d", display: "exit"}}, \
  {key: '|', popup: '' }, \
  {key: '/', popup: '\\\\' }, \
  {key: "(", popup: ")" }, \
  {key: "{", popup: "}" }, \
  {key: "[", popup: "]" }, \
  {key: ".", popup: "," }, \
  {key: 'TAB', popup: 'TAB' } \
], \
[ \
  {macro: "ESC :wa ENTER", display: "save", popup: {macro: "ESC :wqa ENTER", display:  "save&quit"}}, \
  {key: '!', popup: '?' }, \
  {key: '~', popup: '`' }, \
  {key: '-', popup: '_' }, \
  {key: 'QUOTE', popup: 'APOSTROPHE'}, \
  {key: '?', popup: {macro: 'CTRL l', display: 'CLS'}}, \
  {key: UP, popup: PGUP}, \
  {key: 'ALT', popup: '' } \
], \
[ \
  {key: 'KEYBOARD', popup: 'DRAWER'}, \
  {macro: "CTRL 2", display: ">_", popup: {macro: "CTRL n", display: "NEW"}}, \
  {key: 'CTRL', popup: '' }, \
  {key: '=', popup: '+' }, \
  {key: '@', popup: '' }, \
  {key: LEFT, popup: '<' }, \
  {key: DOWN, popup: PGDN}, \
  {key: RIGHT, popup: '>' } \
]]
```

X11 Keys

```Java Properties
[[{macro: 'CTRL c', display: '✖️'},{key: '%', popup: '#'},{key: '=', popup: '+'},{key: '!', popup: '?'},{key: '^', popup: '@'},{key: '$', popup: '*'},{key: ':', popup: ';'},{macro: 'ESC :w ENTER', display: '', popup: {macro: 'ESC :wqa ENTER', display: '󰆔'}}],
[{macro: 'HOME', display: '', popup: {macro: 'END', display: 'ᴇɴᴅ'}},{key: '|', popup: '&' },{key: '(', popup: ')'},{key: '{', popup: '}'},{key: '[', popup: ']'},{key: '/', popup: '\\'},{macro: 'MOUSE_HELPER', display: '󰍽', popup: 'STYLUS_HELPER'},{macro: 'ESC', display: '󱊷', popup: {macro: 'INS', display: '󰫶󰫻󰬀'}}], [{macro: 'ENTER', display: '󰘌'},{macro: 'FN', display: 'ꜰɴ', popup: {macro: 'F4', display: '󱊮'}},{key: '~', popup: '`'},{key: '-', popup: '_'},{key: 'QUOTE', popup: {macro: '', display: ''}},{key: 'APOSTROPHE', popup: {macro: 'CTRL l', display: 'CLS'}},'UP','TAB'],
[{key: 'KEYBOARD', popup: 'PREFERENCES'},{macro: 'CTRL', display: 'ᴄᴛʟ', popup: {macro: '', display: ''}},{macro: 'ALT', display: 'ᴀʟᴛ', popup: {macro: '', display: ''}},{macro: 'META', display: '󰚌'},{macro: 'CTRL b', display: '™️', popup: {macro: 'CTRL b d', display: 'exit'}},'LEFT','DOWN','RIGHT']]
```

```Java Properties
extra-keys = [[ \
  {macro: 'CTRL c', display: "✖️", popup: {macro: "CTRL d", display: "exit"}}, \
  {key: '%', popup: '#' }, \
  {key: '=', popup: '+' }, \
  {key: '!', popup: '?' }, \
  {key: '^', popup: '@' }, \
  {key: '$', popup: '*' }, \
  {key: ":", popup: ";" }, \
  {macro: "ESC :w ENTER", display: , popup: {macro: "ESC :wqa ENTER", display:  "󰆔"}} \
], \
[ \
  {macro: 'HOME', display: '', popup: {macro: 'END', display: 'ᴇɴᴅ'}}, \
  {key: '|', popup: '&' }, \
  {key: "(", popup: ")" }, \
  {key: "{", popup: "}" }, \
  {key: "[", popup: "]" }, \
  {key: '/', popup: '\\\\' }, \
  {key: '', popup: '' }, \
  {macro: 'ESC', display: "󱊷", popup: {macro: "INS", display: "INS"}} \
], \
[ \
  {macro: 'ENTER', display: '󰘌', popup: {macro: '', display: ''}}, \
  {macro: 'FN', display: "ꜰɴ", popup: {macro: "F4", display: "󱊮"}}, \
  {key: '~', popup: '`' }, \
  {key: '-', popup: '_' }, \
  {key: 'QUOTE', popup: {macro: '', display: ''}}, \
  {key: 'APOSTROPHE', popup: {macro: 'CTRL l', display: 'CLS'}}, \
  {key: UP, popup: PGUP}, \
  {key: 'TAB', popup: 'TAB' } \
], \
[ \
  {key: 'KEYBOARD', popup: 'DRAWER'}, \
  {macro: 'CTRL', display: 'ᴄᴛʟ', popup: {macro: '', display: ''}}, \
  {macro: 'ALT', display: 'ᴀʟᴛ', popup: {macro: '', display: ''}}, \
  {macro: 'META', display: '󰚌', popup: {macro: 'F1', display: '󱊫'}}, \
  {macro: "CTRL b", display: "™️", popup: {macro: "CTRL b d", display: "exit"}}, \
  {key: LEFT, popup: '<' }, \
  {key: DOWN, popup: PGDN}, \
  {key: RIGHT, popup: '>' } \
]]
```

## Dots files and themes

Configuration source now lives in `config/`; `configs -> config` is retained for
compatibility. This repository owns `.dots/files.json` for Termux resources. From
the parent Dots checkout, use `dots files list --repo termux --platform termux`
or `dots files locate QUERY` to inspect sources and observed destinations. Tracking
updates metadata only. `dots theme set ID` publishes shared colors and backs up the
Termux colors connector before replacement; `dots theme bg next` is a separate,
explicit Termux:API wallpaper action. Use the parent `dots files install` / `uninstall` commands for journaled setup and restore.
