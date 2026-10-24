# Device location and addresses

**Implemented.** `bin/termux-geo` is a Bash command for occasional personal location lookups on Android/Termux. It calls `termux-location -p network -r once` when no acceptable device cache exists, then uses Nominatim to resolve the coordinates into an address. It is independent of `termux-location-status`, which only reports the Android location toggle.

```bash
termux-geo
termux-geo --refresh --provider gps --timeout 35
termux-geo get city
termux-geo format '{city}, {state} {postcode}'
termux-geo --coords
termux-geo --lat 40.7484 --lon -73.9857 --json
termux-location -p network -r once | termux-geo --stdin

city=$(termux-geo get city)
coordinates=$(termux-geo --coords)
termux-geo | jq '.postcode'
termux-geo get city --cached --allow-stale
```

Use the full `~/dots/androidots/bin/termux-geo` path if Androidots' `bin` directory is not on your PATH. Coordinate-only requests never contact an address service. Explicit coordinate and stdin inputs never replace the cached device reading. `--stdin` consumes exactly one JSON object, not continuous location updates; stdin is otherwise left alone.

## Requirements

Install dependencies yourself if missing: Bash 5.3+, `jq`, `curl`, coreutils (`timeout`, `head`, `readlink`, and ordinary file utilities), and `flock` (util-linux). Device acquisition additionally needs the `termux-api` CLI package, a compatible Android Termux:API app, enabled location services, and the Android permissions required by that app. Nothing installs packages or grants permissions automatically.

The monotonic clock comes from Bash 5.3's `BASH_MONOSECONDS`, because Android may block `/proc/uptime`. Device cache freshness combines monotonic elapsed time, wall elapsed time (including suspend), the API's `elapsedMs`, and boot identity. Backward wall-clock changes or unavailable/mismatched boot identity make cached freshness unknown. A new fix with unknown age is refused rather than presented as fresh.

## Options

| Interface | Meaning |
| --- | --- |
| No subcommand / `show` | Human report on terminal stdout, JSON when redirected |
| `--json`, `--human` | Explicit output mode |
| `get FIELD`, `--get FIELD`, `-g FIELD` | One field followed by a newline |
| `format TEMPLATE`, `--format TEMPLATE`, `-f TEMPLATE` | Literal `{field}` placeholders; `{{` and `}}` escape braces |
| `--coords` | `latitude,longitude`, without geocoding |
| `--fields` | Supported canonical fields, one per line |
| `--lat LAT --lon LON` | Explicit coordinates |
| `--stdin` | One Termux location JSON object |
| `-p`, `--provider network\|gps\|passive` | Device provider; default network, without silent fallback |
| `-r`, `--refresh` | Bypass device cache; matching address cache remains reusable |
| `--cached` | Cache-only read; no acquisition or refresh worker |
| `--max-age SECONDS` | Device age limit, 0–86400; default 60, zero requires a new fix |
| `--allow-stale` | Permit expired/unknown-age device cache with `--cached` |
| `--timeout SECONDS` | Overall acquisition/lookup deadline, 1–3600; default 20 |
| `--language CODE` | Address language, default `en` |
| `-v`, `--verbose` | Human cache/progress/timing detail |
| `--color=auto\|always\|never`, `--icons=auto\|always\|never` | Dots presentation controls |
| `-h`, `--help` | Usage and service restrictions |

Output selectors are mutually exclusive; default device, explicit coordinates, and stdin are mutually exclusive inputs. `--refresh` is device-only and conflicts with `--cached`. `--allow-stale` requires `--cached`; it does not extend the address cache lifetime. `--max-age` describes the age of a fix, not just when the script read it. Provider selection and refresh are invalid with supplied input. Language accepts a language tag such as `en` or `en-US`.

## Data and failure contract

JSON is a flat object with `version: 1` and these fields:

| Fields | Type and meaning |
| --- | --- |
| `latitude`, `longitude` | Numeric input/device coordinates, never replaced with geocoder object coordinates |
| `accuracy_m` | Numeric horizontal accuracy or null |
| `city`, `state`, `state_code`, `postcode`, `county`, `country`, `country_code`, `street`, `house_number`, `address` | Strings or null; country code uppercase, state code retains available ISO subdivision code |
| `source` | `device`, `explicit`, or `stdin` |
| `provider` | API provider, or null for supplied coordinates |
| `age_seconds` | Known fix age, or null |
| `cached`, `address_cached`, `stale` | Booleans distinguishing device and address reuse |
| `attribution` | Address-service attribution, or null when unavailable |

Getters/templates also expose `coordinates`, plus aliases `lat`, `lon`, and `zip`. City normalization checks city, town, village, municipality, then hamlet. Street normalization checks road, pedestrian, footway, then path. Missing components remain null; a successful reverse lookup need not contain every field. Postal codes remain strings, preserving leading zeros. Templates support no indexing, expressions, format specifications, or shell evaluation.

A getter or template requiring an unavailable value fails with empty stdout. Full JSON/address output also fails with empty stdout if geocoding fails. Human reports may show the acquired coordinates and unavailable address fields, with an actionable stderr diagnostic and nonzero status. Coordinate-only getters/templates do not need geocoding to succeed.

Exit statuses are 0 for success, 1 for unavailable data or operational failure, 2 for usage errors, 124 for a deadline or HTTP connection/request timeout, and 130 for Ctrl-C (143 for termination). Deadline diagnostics name the phase: device location, address lookup, stdin reading, or cache locking. Optional verbose output is suppressed in machine modes. JSON/scalar/template/coordinate/completion streams never gain decoration, including with forced color/icon flags. Errors remain on stderr.

Device stdout is captured through a bounded reader within the timed process group; responses exceeding 64 KiB are refused before parsing. The API process inherits the caller's file-size resource limit. Setting a small `ulimit -f` around the native API bridge can make otherwise working location requests hang. For diagnosis, compare `termux-location -p network -r once` with `termux-geo --coords --refresh`; both skip address lookup. The helper's deadline bounds its own request.

## Cache, service use, and presentation

The private cache lives in `${XDG_CACHE_HOME:-$HOME/.cache}/termux-geo`, with mode 0700 directories and 0600 files. Device records are separated by requested provider. At most 32 address responses are retained for 24 hours, keyed by exact normalized coordinates, language, and endpoint. Cache-only reads do not create directories, lock, or refresh anything. Normal misses use bounded locking and recheck cached data after acquiring the lock. Corrupt records are ignored; symlink or nonregular cache targets are refused. Cache writes are atomic. This is disposable command cache, not managed-file installation state.

Addresses are approximate nearest mapped-object results; postal codes are not guaranteed. An address lookup sends the coordinates to `https://nominatim.openstreetmap.org/reverse`. Set `TERMUX_GEO_ENDPOINT` to an HTTPS Nominatim-compatible reverse endpoint to use another service; credentials, query strings, and fragments are not accepted in this setting. The public service is intended for occasional personal queries, not systematic/bulk lookup or frequent tracking. Requests identify this client, reuse cached results, and are serialized with a conservative 15-second minimum interval, including endpoint overrides. Server `Retry-After` cooldowns are retained; automatic retries are disabled. A cooldown returns an error promptly, with a retry delay. One cache root coordinates this helper's processes; it cannot coordinate other devices or unrelated clients. See the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).

Human reports and JSON retain OpenStreetMap attribution. Programs displaying extracted address fields must also display suitable attribution, available via `get attribution` or JSON. Avoid passing confidential locations to public services. Location and address data are retained locally in the private cache, not in repository files or verbose logs.

Human output uses the parent's shared Dots semantic colors, wrapped rows and delayed stderr spinner when available, with a plain standalone fallback. `DOTS_COLOR`, `DOTS_ICONS`, `NO_COLOR`, and `DOTS_PROGRESS=auto|never` apply. Both output streams must be suitable terminals for progress; fast work and machine modes do not animate. No user rc file is sourced to obtain styling.

Help (`-h`, `--help`, and completion help) uses bold cyan headings and blue command syntax, option signatures and examples, with descriptions in the normal foreground color. `--color=auto|always|never`, `DOTS_COLOR`, `NO_COLOR` and stdout terminal detection control styling. Redirected help is plain by default; `--color=always` explicitly enables color. Without the shared Dots library, help stays plain. Help never starts progress or acquires location.

## Shell completions

```bash
termux-geo completion bash
termux-geo completion zsh --install
termux-geo completion fish --install
termux-geo completion --all --install
termux-geo completion --all --install --dir "$HOME/completion-export"
```

Default destinations are relative to this resolved Androidots checkout:

| Shell | File |
| --- | --- |
| Bash | `shells/bash/completions/termux-geo.bash` |
| Zsh | `shells/zsh/completions/_termux-geo` |
| Fish | `shells/fish/completions/termux-geo.fish` |

`--dir` overrides the exact directory, retaining distinct filenames for `--all`. Standard user-location environment variables do not override these repository-local installer defaults. `--all` requires `--install` and excludes an individual shell; `--dir` also requires installation. Generation needs no target shell, Android access, or network. Completion itself is static and does not execute the helper.

Installation preflights every target. Existing regular files are left unchanged when identical; differing files receive a byte-preserving sibling `NAME.bak.UNIQUE` backup before atomic replacement. Existing permissions are retained. Symlink/nonregular targets and observed target drift are refused. Earlier installed files and reported backups remain if a later write fails. The installer creates missing directories, reports results/backups to stderr, and keeps stdout empty. Restore a backup by explicitly copying it over the corresponding completion file. Completion files are source artifacts within Androidots; inspect resulting Git changes before publication.

The parent Dots personal shell configuration adds these fixed paths only for interactive Termux shells with Androidots present. Zsh gets the local completion directory in `fpath` before its single `compinit`; Bash gets the local `shells/bash` base in `BASH_COMPLETION_USER_DIR`, preserving existing bases and the normal XDG fallback; Fish gets the local completion directory in `fish_complete_path`. Reinitialization does not duplicate entries. These changes do not move other tools' completion files or alter generic `dots init` hooks.

Start a new configured shell after updating the startup files. In Zsh with the updated path already loaded, `rlcs` rebuilds completion discovery. Bash requires `bash-completion`; for immediate manual use, source `~/dots/androidots/shells/bash/completions/termux-geo.bash`. Fish discovers files through its configured path; start a fresh shell after path changes. `--dir` exports require adding their directory to the appropriate shell search path yourself. The installer cannot change a parent shell's active state and never reloads startup files.

## Verification and platform limits

Run `python3 -B tests/test_termux_geo.py` from Androidots and `python3 -B tools/test_termux_geo_shells.py` from the parent Dots checkout. The suites isolate HOME/config/state/cache/repository paths, mock both device and HTTP providers, and exercise native Bash/Zsh/Fish completion discovery and Termux PTYs. They do not query actual device coordinates or grant Android permissions.

Device acquisition is an Android/Termux-specific adapter; there is no native Windows PowerShell, Linux or WSL acquisition adapter. Native network acquisition and cache reuse were verified on the owner device after the file-size-limit repair, using disposable local roots and the inherited Android environment. A separate public-coordinate Nominatim lookup returned address fields. GPS availability, permission denial/recovery, and Android service cancellation remain acceptance checks. Terminating the CLI cleans up its owned processes, but does not prove immediate cancellation of the separate Android service. Timing measurements with mocked providers establish local overhead, not GPS or internet latency.
