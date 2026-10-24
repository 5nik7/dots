# Termux status indicators

Five commands in `bin/` provide Android status for tmux, Starship and other CLI
tools. They share `lib/termux_status/`; keep that directory beside `bin/` when
moving the scripts. Symlinks to the executables work. Existing `battery`,
`termux-sessions` and `termux-bar` commands are independent.

## Setup

Requires Python 3.9+, Android/Termux, and the `termux-api` command package for
Wi-Fi, cellular, notifications and volume. Install the compatible Termux:API companion
Android app as described in the [Termux:API documentation](https://wiki.termux.com/wiki/Termux:API).
Use a Nerd Font for the default icons; `--text` requires no special font.
Add `~/dots/androidots/bin` to `PATH`, or use absolute paths.

```sh
termux-wifi-status --refresh --both
termux-cell-status --refresh --both
termux-notification-status --refresh --both
termux-location-status --refresh --both
termux-volume-status --refresh --both
```

Run cellular and notification refreshes interactively first. They may request
Android permissions or open notification-access settings. Requests time out
after four seconds: grant access, return to Termux, then run `--refresh` again.
Only successful providers become eligible for automatic refresh. Any later
provider failure suspends its automatic requests until another successful
explicit refresh. Cell signal and telephony device information are independent.

Location reads the Android location **toggle**, using `settings --user USER get
secure location_mode`. Android may deny this even when location is enabled;
the result is then unknown. It never requests coordinates, activates GPS, or
claims to detect the Android location-in-use privacy indicator.

## Indicators and fields

| Command | Default indicator | Additional fields |
| --- | --- | --- |
| `termux-wifi-status` | Five signal levels, disconnected, or unknown | `connected`, `ssid`, `rssi`, `level`, `frequency_mhz`, `link_speed_mbps` |
| `termux-cell-status` | Strongest registered cell's Android level | `level`, `dbm`, `type`, `index`, `registered_count`, `carrier`, `roaming`, `data_enabled`, `data_state`, `network_type`, `device_age_seconds`, `device_stale` |
| `termux-notification-status` | Filled or empty bell | `count`, `package_count` |
| `termux-location-status` | Enabled, disabled, or unknown marker | `enabled`, `mode` |
| `termux-volume-status` | Zero, low, medium, high or unknown speaker | `stream`, `volume`, `max_volume`, `percent` |

Volume collection invokes `termux-volume` with no arguments and caches all returned streams.
`--stream music|ring|notification|alarm|system|call` selects the output; media (`music`) is the default.
It never sets volume. `percent` is rounded to the nearest integer; zero volume is `muted`,
positive volume at up to 33% is `low`, up to 66 `medium`, and higher values `high`.
Missing streams are unknown. Zero volume does not establish silent/vibrate/DND mode,
and volume level does not establish whether audio is playing. A normal read can start
volume polling without explicit initialization; failures suspend it until `--refresh` succeeds.

Wi-Fi levels 0–4 use RSSI thresholds of -85, -75, -67 and -55 dBm. Missing or
invalid strength is unknown, distinct from disconnected. Wi-Fi association
does not establish internet access or the current default network.

Cellular uses only registered cells; equal levels keep API order. Use `--cell 2`
to select the second registered cell. These indices are neither SIM numbers nor
stable identifiers. Device information comes from Android's telephony manager
and may refer to a different subscription; it does not identify the active
internet route. `--json` includes the normalized `data.registered` list.

Notification counts represent active notification entries, including any group
summaries returned by Android, not unread messages. The cache stores package
counts only, never titles, bodies or notification lines. By default Termux and
Termux:API entries are excluded. Filters apply to the cache:

```sh
termux-notification-status --both
termux-notification-status --include-self --get count
termux-notification-status --include-package org.example.chat --both
termux-notification-status --exclude-package org.example.player --json
```

Package options are repeatable. Inclusion limits the packages considered;
exclusion wins. Use `--include-self` alongside `--include-package com.termux`
to include Termux. JSON includes the filtered package counts.

## Output contract

All commands support `--icon` (default), `--text`, `--both`, `--json`, `--fields`,
`--no-newline`, `get`/`--get`/`-g`, and `format`/`--format`/`-f`.

```sh
termux-wifi-status get level
termux-cell-status --get data_state
termux-wifi-status format '{icon} {level}/4'
termux-wifi-status --format '{{wifi}} {state}' --no-newline
termux-notification-status --fields
```

Common fields are `module`, `state`, `icon`, `text`, `age_seconds`, `stale` and
`error`. Templates accept plain `{field}` placeholders and escaped `{{`/`}}`;
attribute access, indexing, conversions and format specifications are rejected.
Booleans print as `true`/`false`. Display modes are mutually exclusive. Output
has no ANSI colors and ends with a newline unless `--no-newline` is supplied.

JSON contains those common fields plus a normalized `data` object; unknown
values are `null`. `age_seconds` describes the primary provider, with separate
device age/staleness for cellular. API diagnostics are fixed messages, never raw
responses. An unavailable requested field produces no stdout, a diagnostic on
stderr, and exit 1. Invalid arguments exit 2. Ordinary icon/text/JSON reads exit
0 even when unknown. Failed explicit refreshes exit 1 and explain the failure
on stderr; display/JSON may still show a usable last sample.

## Cache and refresh

Cache files live in `${XDG_CACHE_HOME:-$HOME/.cache}/termux-status`, in a private
directory with mode 0700 and files with mode 0600. Atomic replacement and a
per-module lock allow multiple prompts to read safely. Only normalized fields
are saved; Wi-Fi SSID and carrier are retained when available.

Normal reads return cached output and start at most one detached, one-shot
refresh per module when needed. A cold read returns unknown. There is no
permanent polling service. Freshness lasts 10 seconds for Wi-Fi, 15 for cellular
and notifications, 30 for location, and 5 for volume. Up to five-minute-old samples remain
usable with a visible `~` suffix and `stale: true`; older data becomes unknown.
Provider failures also mark retained data stale. Boot identity and monotonic
time prevent a previous boot's sample from being treated as current.

`--cached` never starts work. `--refresh` collects synchronously, even when
polling was suspended. Each provider has a four-second deadline, a bounded
response size, and process-group cleanup. The two cell requests run concurrently.
An overlapping explicit refresh exits 1 rather than waiting on a lock.
Help, field listing and completion generation never access Android or the cache.

## tmux and Starship examples

### Dots tmux integration

Dots' canonical tmux configuration disables the Wi-Fi, cellular, notification,
volume and location status modules. The upper row shows battery at the right
and a weather-colored clock at the left; no weather widget is enabled. The
parent Dots `docs/wttr.md` owns weather configuration, cached-location policy,
timezone limits and activation commands. Androidots still owns all standalone
status commands and their permission/cache contracts.
The bold 12-hour clock occupies the upper left. Ordered Termux numbers occupy
the second row; the current number expands with its optional tmux session badge
and windows before later numbers. COPY/PREFIX/ZOOM indicators remain on its right.
Colored blocks and spaces separate groups, without literal brackets or dividers. Do not replace `status-right`
with these commands in this layout.

The retained `config/tmux/android-status.py` adapter is available to independent
consumers and unreloaded configurations. When used, it resolves these scripts from the physical Dots checkout and makes
normal `--json` reads, preserving the cache and permission-gating behavior above.
Connected Wi-Fi takes precedence. Cellular appears only when Wi-Fi is explicitly
disconnected and mobile data is both enabled and in the `connected` data state.
Unknown, missing, failed, invalid or expired Wi-Fi shows a neutral muted `?`, regardless of cellular state. Disconnected Wi-Fi with unknown, missing, incomplete or expired cellular activity also shows `?`. It claims neither a transport nor internet access. Only fresh disconnected Wi-Fi plus fresh confirmed inactive telephony-device data hides the segment. Registered-cell signal does not establish mobile-data activity or device-data freshness. Retained positive connection observations remain eligible with `~`; stale disconnected Wi-Fi also marks selected cellular data stale. Uncertain decisions involving either retained stale snapshot show `?~`; otherwise `?` is padded to the existing two-character slot.
Wi-Fi/data share an equal-width icon/marker slot and one separator before battery;
confirmed fresh inactivity leaves no slot or separator. Wi-Fi icons change with their
levels; cellular uses a fixed glyph. Signal levels 0–1 use theme red, 2 yellow,
and 3–4 green. Unknown/stale signal uses muted colors and `?`/`~` markers.
Battery has exactly one space between icon and percentage, padding after the
percentage to preserve its width. The upper row uses
`background`/`foreground`, the lower row uses `background` with `dark_background`
window labels, inactive Termux numbers use `lighter_background`/`hint`, and the current session retains `hint`/`darker_background`.

Source edits do not reload the live server. To activate the parent configuration with network indicators disabled and daylight clock colors, the owner runs `dots theme refresh`, then reloads the intended server: `tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"`, or tmux **prefix + q**.

For standalone/custom consumers only, initialize cellular polling or recover the affected provider interactively in that consumer's HOME/XDG cache environment. These commands are not needed by the shipped bar:

```sh
"$HOME/dots/androidots/bin/termux-wifi-status" --refresh --both
"$HOME/dots/androidots/bin/termux-cell-status" --refresh --both
```

Use the same HOME/XDG cache location as the tmux server. If permission requests
outlast the command timeout, grant access and retry. Provider failure requires
another successful explicit refresh. Do not put these initialization commands
in the recurring bar; normal reads already request bounded refreshes when due.

### Starship example

```toml
# Merge with your existing Starship configuration.
# If your format omits $custom/$all, add ${custom.termux_wifi} explicitly.
command_timeout = 1000

[custom.termux_wifi]
command = '~/dots/androidots/bin/termux-wifi-status'
when = true
shell = ['bash', '--noprofile', '--norc']
format = '[$output]($style) '
style = 'cyan'
```

Repeat the custom module with the other command names as desired. Keep
`--refresh` out of prompt/status commands: ordinary reads never wait for Android
requests. Python startup still takes time; adjust Starship's command timeout
for your device. Use `--cached` if a separate scheduled command owns refreshes.

## Shell completion

Each command generates Bash, Zsh and Fish completion without executing Android
requests. Replace `termux-wifi-status` below with any of the other four names.

```sh
termux-wifi-status completion bash
termux-wifi-status --completion zsh
termux-wifi-status completion fish --install
termux-wifi-status completion --all --install
termux-wifi-status completion --all --install --dir ./my-completions
```

`--all` means all three shells for this command. Without `--install`, stdout
contains only completion source. Install reports go to stderr. Identical files
are left alone; differing files receive a `.bak.*` backup before atomic
replacement. Symlinks and non-regular target files are refused. Targets are
preflighted together; if a later write fails, completed installs/backups remain
and are listed on stderr.

Default destinations:

- Bash: first nonempty `BASH_COMPLETION_USER_DIR` entry, or
  `${XDG_DATA_HOME:-~/.local/share}/bash-completion`, followed by
  `completions/COMMAND.bash`.
- Zsh: `${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions/_COMMAND`, or
  `${XDG_DATA_HOME:-~/.local/share}/zsh/site-functions/_COMMAND` without a prefix.
- Fish: `${XDG_CONFIG_HOME:-~/.config}/fish/completions/COMMAND.fish`.

`--dir` uses that exact directory. No startup files are changed. Bash needs
bash-completion loaded; Zsh needs the destination in `fpath` before `compinit`
(rebuild its completion dump after adding commands); Fish loads its default
completion directory automatically.

## Validation and sources

Run `python3 -B tests/test_termux_status.py` for isolated provider/cache/output
tests and native shell completion checks when Bash, Zsh and Fish are installed.
Tests use temporary directories and fake providers, never live permission APIs.
Existing regression suites are `tests/test_termux_sessions.py` and
`tests/test_termux_bar.py`. Device permissions, signal changes and font rendering
still need interactive Android validation.

Response normalization follows the official Termux:API
[Wi-Fi](https://github.com/termux/termux-api/blob/master/app/src/main/java/com/termux/api/apis/WifiAPI.java),
[telephony](https://github.com/termux/termux-api/blob/master/app/src/main/java/com/termux/api/apis/TelephonyAPI.java),
and [notification](https://github.com/termux/termux-api/blob/master/app/src/main/java/com/termux/api/apis/NotificationListAPI.java)
implementations. Icons use the
[Nerd Fonts Material Design glyphs](https://github.com/ryanoasis/nerd-fonts/blob/master/css/nerd-fonts-generated.css).
