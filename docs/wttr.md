# wttr weather and the Termux clock

**Implemented:** `bin/wttr` and `bin/wttr.ps1` share the Python 3.11+ controller in `lib/dots/wttr`. Custom views request [wttr.in JSON](https://github.com/chubin/wttr.in#json-output) with `format=j1`. Stock requests use native curl. No Python packages are required. This standalone command does not add a `dots wttr` route. Older scripts under `scripts/` and Androidots are independent.

## Configuration and locations

The configuration is selected from `--config PATH`, the user configuration directory's `wttr/config.toml`, then the checkout's [`config/wttr/config.toml`](../config/wttr/config.toml). Unix uses `${XDG_CONFIG_HOME:-$HOME/.config}`; native Windows uses `%APPDATA%` unless `XDG_CONFIG_HOME` is explicit. The catalog's `wttr` resource can be linked with the normal managed-file workflow; adding the catalog entry does not install it.

Defaults are Fahrenheit/mph/inches (`units = "us"`), three days, and an **unset** `default_location`. To override automatic location, edit the chosen file, for example:

```toml
default_location = "London"
units = "us"
widget = "{icon} {temperature}{unit}{stale_marker}"
```

Resolution is explicit `--location` or positional input, then a nonempty configured `default_location`, then the city from Androidots `termux-geo --json` on Termux. A configured location skips automatic acquisition. The selected location supplies both the request and custom heading; wttr.in's `nearest_area` can identify a nearby neighborhood and no longer replaces that label. No IP geolocation request is made when these are unavailable. The helper can be on PATH or in the adjacent Androidots checkout. Its cache/permission/provider contracts remain authoritative; wttr neither reads Android providers directly nor changes permissions. Foreground acquisition keeps termux-geo’s normal device/address-cache policy and receives at most half of the total refresh deadline, leaving time for the weather request.

Normal foreground weather reads may acquire location when a refresh is needed. `--widget`, `--format` and `--daylight` use the configured override or `termux-geo --json --cached --max-age 86400`, including when explicitly refreshed. This is the safe surface for bars: a new HTTP refresh may run, but device acquisition cannot. Location cache age is configurable up to 24 hours. Automatic city lookup needs a usable address cache too. Missing city, failed/missing helpers, malformed output and timeouts yield unavailable data without exposing provider stderr. Foreground `wttr --refresh` can populate both caches through the existing helper. The helper remains responsible for reverse geocoding and its service cooldowns. See [termux-geo](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-geo.md).

The icon table maps all 48 [World Weather Online condition codes](https://www.worldweatheronline.com/weather-api/api/docs/weather-icons.aspx), plus `unknown`, to [Nerd Fonts Weather glyphs](https://github.com/ryanoasis/nerd-fonts/blob/master/bin/scripts/lib/i_weather.sh). Customize codes independently under `[icons]`; `[night_icons]` overrides clear, partly cloudy and snow-with-thunder conditions at night. Nerd Font appearance is a terminal/font setting, not something the command installs.

## Commands and output

```sh
wttr                            # current weather and up to three forecast days
wttr --location 'New York' --days 2
wttr '51.5,-0.1' --units metric --hourly
wttr --current --language fr
wttr --refresh                  # foreground recovery / automatic-location cache seed
wttr --json --cached             # original upstream j1 object, no decoration
wttr get sunrise --cached
wttr --get temperature --cached --units metric
wttr --widget                   # immediate cache view plus an on-demand refresh
wttr --format '{icon} {temperature}{unit} {wind}{wind_unit}{stale_marker}'
wttr --daylight                  # day, night or unknown
wttr --fields
wttr --help --color always
```

Main help (`wttr -h` / `--help`) and completion help (`wttr completion -h`) begin with the supplied two-line artwork and a title:

```text
█ █ █ ▀█▀ ▀█▀ █▀█
▀▄▀▄▀  █   █  █▀▄

 wttr — weather from wttr.in
```

The artwork uses a horizontal gradient from the published Dots theme's blue to cyan, with `#3B82F6` / `#06B6D4` fallbacks for unavailable endpoints. Plain help retains the artwork without ANSI. The title icon follows the icon controls independently; `--icons never` removes it. Help never reads weather configuration or queries providers, and reads at most one palette snapshot when colored. The banner appears only in help, never weather results, errors, stock responses, widgets, or data output.

Short flags are case-sensitive aliases with the same arguments and behavior as their long forms:

| Short | Long | Short | Long |
| --- | --- | --- | --- |
| `-h` | `--help` | `-V` | `--version` |
| `-v` | `--verbose` | `-f` | `--format` |
| `-j` | `--json` | `-F` | `--fields` |
| `-g` | `--get` | `-l` | `--location` |
| `-c` | `--current` | `-d` | `--days` |
| `-H` | `--hourly` | `-u` | `--units` |
| `-L` | `--language` | `-w` | `--widget` |
| `-r` | `--refresh` | `-C` | `--config` |
| `-t` | `--timeout` | | |

Boolean short flags may be grouped (`-vj`), and argument-taking flags accept attached values (`-d2`, `-lLondon`) or separate values. Quote templates, for example `wttr -f '{temp_color}{temperature}{unit}{reset}'`. Use `-l=-value` for a location starting with a dash. Bare stock letters remain distinct: `F` is an upstream option; `-F` lists local fields. Other options remain long-only. Completion provides the same separate-value contexts for aliases and long forms across Bash, Zsh, Fish, and PowerShell.

PowerShell uses the same options with `& "$env:DOTS/bin/wttr.ps1" ...` (or `wttr.ps1` on PATH). Use `--location` to pass a literal place called `get`, `completion`, `moon`, `m2`, or another reserved stock token; quote spaces and use `--location=-value` for a location starting with a dash.

`--days` accepts 1–3, matching j1's forecast horizon; hourly rows are the supplied three-hour forecast periods, not minute forecasts. `--current` omits forecast rows. `--units us|metric` affects rendered and scalar values; `--json` retains the original units/fields exactly as supplied upstream. `--language CODE` requests translated weather descriptions. `--timeout SECONDS` accepts integers 1–60 and limits a complete refresh, including location and HTTP. `--verbose` adds source and age to the human view.

`--color auto|always|never` and `--icons auto|always|never` honor the shared Dots presentation policy. Auto help is colored in a capable terminal; redirected output is plain. Progress is delayed, human-TTY-only and controlled by `DOTS_PROGRESS`. JSON, field, daylight, version and completion output never include progress or ANSI, even under forced color. Widgets never animate; their explicit color policy is described below. Widgets use configured icons in auto mode; `--icons never` or `DOTS_ICONS=never` removes them. Errors go to stderr; providers' stderr is never forwarded.

`--fields` lists the shared vocabulary: `location`, `attribution`, `condition`, `code`, `icon`, `temperature`, `unit`, `feels_like`, `humidity`, `wind`, `wind_unit`, `wind_direction`, `precipitation`, `precipitation_unit`, `sunrise`, `sunset`, `daylight`, `age`, `stale`, `stale_marker`, `wind_icon`, `sunrise_icon`, `sunset_icon`, `humidity_icon`, `precip_icon`, `location_icon`. Age is seconds since acquisition. Templates accept literal `{field}` placeholders, [style directives](#widget-style-directives), and doubled braces; attribute access, expressions, conversions and format specifiers are rejected. Widget values are single-line control-free text. Plain and ANSI widgets are **not tmux output**; use the explicit `tmux` widget format for escaped literal text and generated color styles. The shipped clock adapter accepts only three fixed tokens.

Missing widget data prints `?`. Missing daylight prints `unknown`. Ordinary weather/JSON/field requests without usable data return status 1 and a diagnostic; invalid arguments/configuration return status 2. Interruptions return 130. No-error views return 0.

## Temperature, icon and widget colors

The custom current, feels-like, daily low/high and hourly temperatures use any number of configurable bands (six in the shipped configuration). Forecast descriptions now include their own condition icons: midday uses that forecast's noon condition; hourly icons use that date's sunrise/sunset when available. Missing astronomy uses the normal day glyph. Current night overrides and icon-disable controls remain supported.

```toml
show_location_attribution = false
widget_color = "auto"        # auto, always, never
widget_color_format = "ansi" # ansi, plain, tmux

[temperature_scale]
unit = "F"                  # F or C, independent of --units
thresholds = [32, 45, 65, 80, 95]
colors = ["cyan", "blue", "green", "yellow", "orange", "red"]
```

The first boundary is inclusive: in this example, at or below 32°F is cyan. Above 32°F and below 45°F is blue; 45–<65°F green; 65–<80°F yellow; 80–<95°F orange; 95°F and above red. Use **N thresholds and N+1 color/style values**, ordered coldest to hottest. Thresholds must be finite, strictly increasing integers or decimals. An empty threshold list with one style applies that style to all numeric temperatures. The existing configuration-size limit applies; there is no separate band-count limit. A count mismatch is a configuration error. Omitting the scale retains the built-in five-cutoff defaults (32, 60, 75, 85, 95°F), while the shipped editable config supplies the example above. Values are converted from the displayed unit into the configured scale before comparison. Missing/non-numeric temperatures remain uncolored. These colors express temperature, not operation success/error states.

`[icon_colors]` maps each existing condition code, plus `unknown`, to a color. `[night_icon_colors]` supplies night overrides. The shipped table uses the current Dots theme: sun/partly cloudy yellow, cloud/fog/mist muted, rain blue, snow/ice/sleet cyan, thunder magenta and clear/partly cloudy nights blue. Glyphs remain separately editable in `[icons]` and `[night_icons]`.

All temperature and day/night icon color fields accept the same values, including mixed arrays:

| Configuration value | Meaning |
| --- | --- |
| `"blue"` | Read blue from the published Dots theme. |
| `"#89b4fa"` | Use this literal RGB value. |
| `33` or `"33"` | Use ANSI 256-color index 33, independent of Dots palette lookup. |
| `"default"` | Keep the surrounding foreground. |

Supported lowercase names are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, their `bright_` forms, and `orange`, `foreground`, `background`, `muted`, `accent`. Aliases are `gray`/`grey` → `muted`, `purple` → `magenta`, and `indigo` → `blue`. Black/white use published `color0`/`color7`; their bright variants use `color8`/`color15`. Hex must contain six digits; indices must be integers from 0 through 255. Invalid values produce a configuration error (status 2).

Style expressions can add `bold`, `italic`, `underline`, `dim`, and `reverse` to at most one foreground. Shorthands `b`, `i`, `u`, and `d` work in both config expressions and widget directives. Attribute order does not matter and repeated attributes are harmless. Attribute-only styles, such as `"bold"`, retain the surrounding foreground. Hex/index overrides also accept attributes, for example `"italic #89b4fa"` and `"underline 33"`. Unknown tokens and multiple foregrounds are errors.

`bright blue` means the theme's `bright_blue`; it does not imply bold. The separated `bright` modifier requires one of `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, or `white`. Bare `bright`, `bright orange`, and bright modifiers on hex/index values are invalid; the existing `bright_*` names remain valid.

```toml
[temperature_scale]
unit = "F"
thresholds = [32, 45, 65, 80, 95]
colors = ["bold cyan", "bold bright blue", "bright green", "bold yellow", "orange", "underline bold bright red"]

[icon_colors]
"113" = "bright yellow"
```

Human weather rows isolate each styled value so its attributes do not leak into the next field. The shipped styles remain color-only; the example above is an optional customization. Attribute appearance depends on the terminal and font.

Colored renders read at most one bounded snapshot from Dots' published `current/theme/palette.json` under its platform state directory (Unix `${XDG_STATE_HOME:-$HOME/.local/state}/dots`; native Windows `%LOCALAPPDATA%/dots`, with `XDG_STATE_HOME` overriding the base). The next invocation sees newly published theme colors; no theme command, publication, or weather-cache refresh is required. Explicit hex/index settings remain literal. Missing, malformed, or incomplete snapshots use terminal ANSI slots 0–15, orange index 208, muted index 8, accent blue, background index 0, and the surrounding foreground. No snapshot is needed for plain, JSON, scalar, daylight, or stock output.

Human weather output (default, `--current`, `--cached`, forecasts and hourly views) uses a minimum ten-character aligned label column followed by three spaces. Set top-level `label_gap = 3` to choose a gap from 1–8 spaces; booleans and non-integers are invalid. When an enabled label such as `Location data` is longer, the whole view uses that wider column. Wrapped continuation lines align with the values. Help and widget-template spacing are independent of this setting. `Now` contains the condition icon and temperature, with the condition description in a separate `Condition` row immediately below it. Midday and hourly rows retain their condition descriptions and one-space icon gap. Disabling icons, or configuring an empty condition glyph, removes the icon gap. Custom widget templates retain their own spacing.

```text
Weather —  London
    Now           53°F
    Condition    Clear
    Feels like   50°F
    Humidity     60% 
    Wind         5 mph NW ↘
    Precip       0.0 in 
    Sunrise      6:30 AM 
    Sunset       6:30 PM 󰖚
```

The fields `location_icon` (``), `sunrise_icon` (``), `sunset_icon` (`󰖚`), `humidity_icon` (``) and `precip_icon` (``) supply configurable glyphs without surrounding spaces. The location icon precedes the city in the heading; humidity, wind, precipitation, sunrise and sunset icons follow their row values with one space, including unavailable values. All icon fields follow the existing icon controls and become empty when icons are disabled. An empty glyph setting hides that icon and its human separator.

Add these named entries to the existing tables to customize the defaults; retain any condition-code entries already present. Older configurations receive these defaults automatically. Detail colors accept the same theme names, hex/index overrides, text attributes and `default` as condition colors. Wind arrows remain fixed, with a configurable style.

```toml
# Top-level, before any table:
label_gap = 3

[icons]
location = ""
sunrise = ""
sunset = "󰖚"
humidity = ""
precip = ""

[icon_colors]
location = "magenta"
sunrise = "yellow"
sunset = "orange"
humidity = "cyan"
precip = "blue"
wind = "cyan"
```

Human detail colors apply only to the glyph and separator, leaving values unchanged; the city retains the heading style. Widget templates without directives automatically style these icon fields. Manual templates use the named color directives below, for example `{humidity_color}{humidity_icon}{reset} {humidity}%`.

`wind_icon` uses eight Unicode arrows pointing **where the wind blows**: a north wind gives `↓`, and a northwest wind gives `↘`. Valid provider degrees (0–360, with 360 equivalent to north) take precedence over the 16-point compass value. Missing/invalid degrees fall back to the compass value; no usable direction yields an empty icon. Bearings round to the nearest 45° sector, with midpoint ties clockwise. The Wind row shows speed, units and the original compass text followed by the arrow, such as `2 mph NW ↘`. Icon positions in widgets remain controlled by the template.

Widget styling applies to `--widget` and local `--format`, including `{temperature}`, `{feels_like}`, adjacent `{unit}` placeholders and all icon fields. Color policy is explicit `--color`, then `DOTS_COLOR`, then `widget_color`. ANSI-auto colors a capable terminal and keeps pipes plain; `NO_COLOR` suppresses automatic colors. `always` forces them even in pipes, while `never` suppresses them. The `plain` format always emits plain text.

The explicit `tmux` format emits status styles through pipes in auto mode unless `NO_COLOR` is set. It escapes `#` in literal/template/provider text, saves the incoming style once, and restores it afterward. With colors disabled it still escapes literal text for tmux. Consume this as the output of a tmux status job; it is not a shell command or a format to evaluate recursively. It uses tmux's single saved-default slot, so do not nest it inside another `push-default`/`pop-default` block. ANSI and plain widgets remain suitable for their respective terminal/text consumers. No widget is enabled in the shipped bar.

Sunrise/sunset display fields omit a leading hour zero: `07:30 AM` becomes `7:30 AM`. This applies to human rows, widgets and scalar queries; minute padding and AM/PM are preserved, and noon/midnight remain `12:00 PM` / `12:00 AM`. Raw JSON and cached provider data remain unchanged, as do astronomy validation and daylight boundaries.

Other scalar fields, daylight tokens and stock curl responses retain their existing byte contracts. Color customization does not change provider polling, cache identity, freshness or the daylight clock.

## Widget style directives

Both the `widget` config and local `--format` support these zero-width directives. They do not become scalar fields and are not added to `get` or `--fields`.

| Directive | Effect |
| --- | --- |
| `{icon_color}` | Add the current condition's configured day/night icon style. |
| `{temp_color}` | Add the current temperature-band style. |
| `{feel_color}` | Add the same scale’s style for the feels-like temperature, including unit conversion and text attributes. |
| `{location_color}`, `{sunrise_color}`, `{sunset_color}`, `{humidity_color}`, `{precip_color}`, `{wind_color}` | Add the matching named `[icon_colors]` style. |
| `{bold white}` or `{bright green}` | Add any supported style expression. |
| `{b}`, `{i}`, `{u}`, `{d}` | Add bold, italic, underline, or dim. |
| `{reset}` | Clear widget-applied styling and return to the starting style. |

Missing or nonnumeric feels-like values select the default style, just as missing current temperatures do. `{feel_color}` is consumed without styling in plain output and is not a queryable field.

Attributes accumulate; a later foreground replaces the earlier foreground. Thus `{bold}{white}` means bold white, and `{icon_color}{temp_color}` retains attributes from both while the temperature foreground wins. Use `{reset}` between sections when those attributes should not carry forward. `{default}` restores the starting foreground while retaining added attributes.

```toml
# Top-level setting, before any [table]:
widget = "{icon_color}{icon}{reset} {temp_color}{temperature}{unit}{reset} feels {feel_color}{feels_like}{unit}{reset} {wind_icon} {wind}{wind_unit}{stale_marker}"
```

A template containing any actual directive uses **manual styling throughout**, including text before its first directive. Templates with no directives retain automatic styling of icon/temperature/feels-like fields and adjacent units. `{{bold}}` prints literal `{bold}` and does not enable manual styling. Inserted field values are never parsed again, so provider text cannot inject directives.

Disabled color and `plain` output consume directives without ANSI, tmux styling, or palette reads. Template validation still applies before any cache/provider work. Invalid braces, unknown placeholders, Python expressions, attribute access, conversions, and format specifiers are errors. Existing single-line and 1024-character limits remain.

ANSI spans reset to terminal defaults after each styled span and at the end of styled text. Tmux spans restore the incoming consumer style before applying each span's foreground/attributes, and restore the original foreground, background, and attributes on `{reset}` and at the widget boundary. Directives never create nested tmux saved-default blocks; literal text remains escaped. Background configuration is not part of this style syntax.

## Stock wttr.in requests

Plain `wttr` keeps the custom JSON-backed summary. Bare stock tokens select direct requests instead:

```sh
wttr m 2 T                     # same query as m2T
wttr --location London u0
wttr 'format=3'
wttr 'format=%l: %t'            # quote templates against shell expansion
wttr m 'format=%t' --location Paris
wttr moon
wttr moon@2016-10-25
wttr :help
wttr :bash.function
wttr :translation
```

The stock letters are `m u M 0 1 2 A d F n q Q T`, accepted separately or concatenated in input order. They form `https://wttr.in/LOCATION?OPTIONS`. One `format=VALUE` adds the encoded upstream format parameter, including `format=j1`, `format=3`, custom percent templates or literal `format=*`. Bare `format=...` and the local `--format '{field}'` are different interfaces. Locations and format values are literal argument values, encoded once; use spaces rather than URL-encoded text in templates. Shell quoting is required for spaces, wildcards and shell punctuation.

`moon` and valid `moon@YYYY-MM-DD` use their own URL paths and never acquire location. The three service pages use canonical single-slash paths, such as `https://wttr.in/:help`. The former double-slash path caused a redirect body to be displayed instead of the service page. `--help` remains local and provider-free. Special routes reject locations and format selectors; stock letters such as `T` can accompany them. Unknown colon routes, invalid dates, repeated formats and combinations with local rendering/cache options are usage errors. Use `--location` to disambiguate reserved words as literal locations.

Stock weather accepts `--location`, `--config`, `--timeout`, and explicit `--language` (sent as `lang`). Configured location and timeout apply; configured units/language do not silently add stock query options. `--color` and `--icons` affect only wrapper diagnostics, never forwarded bytes; use upstream `T` for plain stock output. Other local view/cache options are incompatible. Stock calls are fresh foreground requests: they neither read nor populate the JSON weather cache or clock data. Recurring bar commands should continue using the existing cached widget/daylight interfaces.

Native `curl` (`curl.exe` on Windows, not a PowerShell alias) is required only for this mode. Requests disable curlrc loading and URL globbing, use HTTPS with no automatic redirects/retries, and share the total location-plus-HTTP deadline. Successful response bytes are forwarded unchanged, including ANSI and newline conventions. No wrapper progress or curl meter is added. Failures leave stdout empty and report a bounded diagnostic on stderr; provider stderr is suppressed.

When `show_location_attribution = true`, the custom human view displays the geo helper's attribution and stock auto-city requests show it on stderr when both streams are terminals. The shipped configuration sets this to `false`; older configurations omitting the setting retain visible attribution. Machine output stays unchanged; consumers displaying the extracted city must retain suitable [OpenStreetMap attribution](https://www.openstreetmap.org/copyright), available through `wttr get attribution --cached` for JSON-backed cached views, or `termux-geo --json --cached` for direct stock lookups. Raw `--json` remains the original weather payload, including its original `nearest_area`.

## Cache and recovery

Weather lives in `${XDG_CACHE_HOME:-$HOME/.cache}/wttr` on Unix; Windows defaults to `%LOCALAPPDATA%/cache/wttr`, with the same XDG override. Private, atomically replaced JSON includes the upstream payload, location and acquisition timestamp. It retains the selected city/manual location and geo attribution; the upstream payload can also contain coordinates. Do not publish it. City-based cache identity/schema version 2 ignores older coordinate-only entries without deleting them; the clock uses the default foreground color until fresh astronomy is available.

Default freshness is 900 seconds, with a maximum retained weather age of 21600 seconds. `--cached` never creates directories, locks, workers or provider requests. Without `--cached`, ordinary foreground views refresh when due. Background views immediately return cached data and reserve one detached, bounded refresh; they have no persistent daemon. Locks coalesce competing refreshes; a bounded reservation expires after a crashed worker. Failed requests retain the last good payload and impose a 60-second cooldown; HTTP `Retry-After` is honored up to one day. `--refresh` explicitly overrides freshness and cooldown; a failed foreground explicit refresh reports failure even if an older fresh payload remains cached. It does not override termux-geo's own permission/provider behavior.

Widgets may display retained weather with `~`. Other outputs require `--allow-stale` to accept expired weather within the six-hour limit. Beyond that age, widgets show `?`. Daylight becomes `unknown` as soon as weather freshness expires, even when a stale forecast is still displayable. A future timestamp is unusable. Configuration location/language and manual locations partition the cache; a manual remote query never replaces the automatic bar entry.

The HTTP provider runs in a child with a total deadline covering DNS and slow streams; decoded response/cache reads are limited to 4 MiB. Geo JSON output is limited to 64 KiB; stock curl output to 4 MiB. There are no authentication tokens and no package/API polling installation.

Owner-run recovery, in the tmux server's HOME/XDG environment:

```sh
"$HOME/dots/bin/wttr" --refresh
"$HOME/dots/bin/wttr" --daylight --cached
```

The first command may acquire coordinates and reverse-geocode a city through termux-geo. To override automatic location, set `default_location` first; supplying a manual location refreshes only that manual entry. Keep the automatic/default location in the host's timezone for clock use.

## Termux upper row

The shipped tmux configuration no longer invokes Wi-Fi or cellular status helpers. Notification, volume and location status modules remain disabled too. Battery remains at the right; the existing clock stays at the left with unchanged time format and background. No weather widget is enabled.

[`weather-status.py`](../config/tmux/weather-status.py) reads `wttr --daylight` with a one-second/16-byte limit and suppressed stderr. It accepts only `day`, `night`, `unknown`; tmux maps those to theme yellow, blue and foreground. Missing Python/helper or failed reads also use foreground. The existing network adapter remains available for independent consumers and unreloaded configurations; its Androidots cache/gates are unchanged.

The clock compares **today's** j1 astronomy against host-local time: sunrise is inclusive, sunset exclusive, and before sunrise is night. Missing, invalid, expired, wrong-date or non-occurring solar events yield unknown. j1 does not supply a reliable timezone identifier; this is not a timezone conversion service. Manual remote forecasts do not drive the clock. The automatic/default location must share the host timezone.

After reviewing the source changes, the owner can publish the new theme option and reload the intended server:

```sh
"$HOME/dots/bin/dots" theme refresh
# Run inside the server you intend to update:
tmux source-file "${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"
```

The source config supplies terminal yellow/blue fallbacks before publication. Ordinary status jobs never contain `--refresh`; weather's bounded on-demand refresh supplies the necessary HTTP refresh source. Source edits do not reload the live server.

## Shell completion

Completion is static and never invokes weather or location. Stock flags, formats, moon queries and service pages share descriptions with local help. Zsh uses described entries for FZF-tab menus; selecting a description inserts only its argument. Fish descriptions and PowerShell tooltips use the same metadata. The currently supported stock tokens are described; PNG transport is not implemented. Generate one shell to stdout, or explicitly install with backup and a Dots file transaction:

```sh
wttr completion bash
wttr completion --all --install
wttr completion fish --install --dir "$HOME/.config/fish/completions"
```

Default destinations are checkout-local: `shells/bash/completions/wttr.bash`, `shells/zsh/completions/_wttr`, `shells/fish/completions/wttr.fish`, and `shells/powershell/completions/wttr.ps1`. `--dir` is for a single shell. Installation preflights all selected files, refuses symlinks/special targets, preserves originals through the existing transaction engine, and does nothing when contents match. The command prints the transaction ID and `dots files undo ID`; undo refuses drift. Recovery uses `dots files recover ID` for an interrupted transaction. No shell profile is edited automatically.

Load after installation, as appropriate:

```sh
# Bash
source "$HOME/dots/shells/bash/completions/wttr.bash"
# Zsh (add before your existing compinit, or initialize an otherwise bare shell)
fpath=("$HOME/dots/shells/zsh/completions" $fpath)
autoload -Uz compinit; compinit
# Fish
source "$HOME/dots/shells/fish/completions/wttr.fish"
```

If `_wttr` is already loaded in a running Zsh session, reload just this completion after updating its checkout file (with the usual completion system already initialized):

```zsh
fpath=("$HOME/dots/shells/zsh/completions" $fpath)
unfunction _wttr 2>/dev/null
autoload -Uz _wttr
compdef _wttr wttr
```

```powershell
& "$env:DOTS/bin/wttr.ps1" completion powershell --install
. "$env:DOTS/shells/powershell/completions/wttr.ps1"
```

## Verification limits

The focused suites use isolated homes/caches, mocked HTTP/location, native Termux shell completions and owned PTYs/private tmux sockets. They do not contact public weather services or change Android permissions. Actual location acquisition, service availability/rate limiting, font appearance and native Windows PowerShell 5.1/7 terminal/completion behavior are separate owner/platform acceptance checks. The shared native bridge and controller are tested without claiming Windows runtime evidence.
