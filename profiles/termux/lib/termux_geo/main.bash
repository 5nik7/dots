# shellcheck shell=bash disable=SC2034,SC1090,SC1091,SC2154
# Loaded by bin/termux-geo; all external data remains data, never shell source.
GEO_FIELDS='latitude longitude coordinates accuracy_m city state state_code postcode county country country_code street house_number address source provider age_seconds cached address_cached stale attribution'
GEO_OPTIONS='--json --human --coords --get --format --lat --lon --stdin --provider --refresh --cached --max-age --allow-stale --timeout --language --fields --verbose --color --icons --help'

geo_error() {
  geo_stop
  local message=$*
  if [[ $GEO_HUMAN == 1 && $GEO_UI == 1 ]]; then
    dots::text "$message"; dots::error "termux-geo: $REPLY" 2>&4
  else printf 'termux-geo: %s\n' "${message//[[:cntrl:]]/?}" >&4; fi
}
geo_fail() { local status=$1; shift; geo_error "$@"; exit "$status"; }
geo_stop() { [[ $GEO_UI != 1 ]] || dots::progress_stop; return 0; }
geo_note() {
  [[ $GEO_HUMAN == 1 && $GEO_VERBOSE == 1 ]] || return 0
  if [[ $GEO_UI == 1 ]]; then dots::progress_print dots::info "$*"
  else printf '%s\n' "$*" >&2; fi
}
geo_phase() {
  [[ $GEO_UI != 1 ]] || dots::progress_start "$1"
  geo_note "$1"
}
geo_ui() {
  [[ $GEO_HUMAN == 1 ]] || return 0
  local root=${DOTS:-${GEO_ROOT%/profiles/termux}}
  [[ $root != "$GEO_ROOT" ]] || root=${GEO_ROOT%/*}
  if [[ -r $root/lib/dots/ui.bash && -r $root/lib/dots/progress.bash ]]; then
    DOTS=$root
    source "$root/lib/dots/ui.bash"
    source "$root/lib/dots/progress.bash"
    dots::settings || return 1
    DOTS_COLOR=${DOTS_COLOR:-${dots_options[DOTS_COLOR]:-auto}}
    DOTS_ICONS=${DOTS_ICONS:-${dots_options[DOTS_ICONS]:-auto}}
    DOTS_PROGRESS_HUMAN=1 GEO_UI=1
  fi
}
geo_help() {
  local line label body heading='' blue='' reset=''
  if [[ $GEO_UI == 1 ]]; then
    dots::heading 'termux-geo — Location'
    heading=$DOTS_UI_BOLD$DOTS_UI_CYAN blue=$DOTS_UI_BLUE reset=$DOTS_UI_RESET
  fi
  # Style the static help source without changing its text or spacing. Empty
  # shared tokens preserve plain output, including the standalone fallback.
  while IFS= read -r line; do
    case $line in
      Usage:*) printf '%sUsage:%s%s%s%s\n' "$heading" "$reset" "$blue" "${line#Usage:}" "$reset" ;;
      'Output:'|'Input and cache:'|'Presentation:'|'Completions:'|'Examples:')
        printf '%s%s%s\n' "$heading" "$line" "$reset" ;;
      '       termux-geo '*|'  termux-geo '*|'  termux-location '*)
        printf '%s%s%s\n' "$blue" "$line" "$reset" ;;
      '  '*)
        body=${line#'  '}; label=${body%%'  '*}
        printf '  %s%s%s%s\n' "$blue" "$label" "$reset" "${body#"$label"}" ;;
      Exit:*) printf '%sExit:%s%s\n' "$heading" "$reset" "${line#Exit:}" ;;
      *) printf '%s\n' "$line" ;;
    esac
  done <<'EOF'
Usage: termux-geo [show | get FIELD | format TEMPLATE] [OPTIONS]
       termux-geo completion SHELL [--install] [--dir DIRECTORY]
       termux-geo completion --all --install [--dir DIRECTORY]

Device location and Nominatim address. Terminal: human report; pipes: JSON.

Output:
  --json / --human              Explicit output mode
  --coords                     latitude,longitude; no address lookup
  -g, --get FIELD               One value; aliases: lat, lon, zip
  -f, --format TEMPLATE         Literal {field} placeholders; {{ and }} escape braces
  --fields                     List fields; no acquisition

Input and cache:
  --lat LAT --lon LON           Supplied coordinates, without Android acquisition
  --stdin                      One termux-location JSON object (not a stream)
  -p, --provider PROVIDER       network (default), gps, passive
  -r, --refresh                 New device fix; matching address cache still applies
  --cached                     Cache only; no Android or HTTP calls
  --max-age SECONDS             Device-fix age limit (default 60; 0 forces a new fix)
  --allow-stale                 Permit expired device cache; requires --cached
  --timeout SECONDS             Overall deadline, 1–3600 (default 20)
  --language CODE              Address language (default en)

Presentation:
  -v, --verbose                Human cache, timing and installation details
  --color=auto|always|never     Dots colors; NO_COLOR applies in auto mode
  --icons=auto|always|never     Dots icons; never selects ASCII markers
  -h, --help                   This help
  DOTS_PROGRESS=never          Disable human progress

Completions:
  completion bash|zsh|fish      Print static shell source
  --install                    Install to androidots/shells/SHELL/completions
  --all                        All shells; requires --install, excludes SHELL
  --dir DIRECTORY              Exact installation directory; requires --install

Examples:
  termux-geo get city
  termux-geo format '{city}, {state} {postcode}'
  termux-geo --refresh --provider gps --timeout 35
  termux-geo get city --cached --allow-stale
  termux-location -p network -r once | termux-geo --stdin
  termux-geo completion --all --install

Requires Bash 5.3+, jq, curl, coreutils and flock; device acquisition also requires
termux-api and the compatible Android Termux:API app with location permission.
No packages are installed automatically. Completion generation needs only Bash
and coreutils. Bash completion discovery requires bash-completion.

Address lookups send coordinates to the configured HTTPS service. Public
Nominatim is for occasional personal use, not bulk/systematic tracking. Responses
are cached; public requests are spaced at least 15 seconds apart. Preserve OSM
attribution when displaying derived addresses. Policy:
https://operations.osmfoundation.org/policies/nominatim/
TERMUX_GEO_ENDPOINT overrides the HTTPS reverse endpoint. Cached coordinates are
private local files. Address results are approximate and may lack postal codes.

Exit: 0 success; 1 unavailable/operational error; 2 usage; 124 timeout; 130 Ctrl-C.
EOF
}
geo_field() {
  case $1 in lat) REPLY=latitude ;; lon) REPLY=longitude ;; zip) REPLY=postcode ;; *) REPLY=$1 ;; esac
  [[ " $GEO_FIELDS " == *" $REPLY "* ]] || geo_fail 2 "unknown field: $1"
  case $REPLY in city|state|state_code|postcode|county|country|country_code|street|house_number|address|attribution|address_cached) GEO_ADDRESS=1 ;; esac
}
geo_template() {
  local remaining=$1 literal='' field
  GEO_PIECES=()
  while [[ $remaining ]]; do
    case $remaining in
      '{{'*) literal+='{' ; remaining=${remaining:2} ;;
      '}}'*) literal+='}' ; remaining=${remaining:2} ;;
      '{'*)
        [[ $remaining == *'}'* ]] || geo_fail 2 'unclosed template field'
        GEO_PIECES+=("L$literal"); literal=''
        field=${remaining#\{}; field=${field%%\}*}
        geo_field "$field"; GEO_PIECES+=("F$REPLY")
        remaining=${remaining#*\}} ;;
      '}'*) geo_fail 2 'unmatched template brace' ;;
      *) literal+=${remaining:0:1}; remaining=${remaining:1} ;;
    esac
  done
  GEO_PIECES+=("L$literal")
}
geo_mode() {
  [[ ! $GEO_MODE ]] || geo_fail 2 'choose only one output mode'
  GEO_MODE=$1
}
geo_parse() {
  local arg value
  while (($#)); do
    arg=$1; shift
    if [[ $arg == --*=* ]]; then value=${arg#*=}; arg=${arg%%=*}; set -- "$value" "$@"; fi
    case $arg in
      --get|-g|get|--format|-f|format|--lat|--lon|--provider|-p|--max-age|--timeout|--language|--color|--icons|--dir)
        (($#)) || geo_fail 2 "missing value for $arg"
        value=$1; shift
        case $arg in --lat|--lon|--provider|-p|--max-age|--timeout|--language) GEO_LOOKUP_OPTIONS=1 ;; esac
        case $arg in
          get|--get|-g) geo_mode get; GEO_FIELD=$value ;;
          format|--format|-f) geo_mode format; GEO_TEMPLATE=$value ;;
          --lat) GEO_LAT=$value; GEO_LAT_SET=1 ;;
          --lon) GEO_LON=$value; GEO_LON_SET=1 ;;
          --provider|-p) GEO_PROVIDER=$value; GEO_PROVIDER_SET=1 ;;
          --max-age) GEO_MAX_AGE=$value ;;
          --timeout) GEO_TIMEOUT=$value ;;
          --language) GEO_LANGUAGE=$value ;;
          --color) DOTS_COLOR=$value ;;
          --icons) DOTS_ICONS=$value ;;
          --dir) GEO_DIR=$value; GEO_DIR_SET=1 ;;
        esac ;;
      show) [[ ! $GEO_ROUTE ]] || geo_fail 2 'duplicate subcommand'; GEO_ROUTE=show ;;
      completion) [[ ! $GEO_ROUTE && ! $GEO_MODE ]] || geo_fail 2 'conflicting subcommand'; GEO_ROUTE=completion ;;
      bash|zsh|fish) [[ $GEO_ROUTE == completion && ! $GEO_SHELL ]] || geo_fail 2 'unexpected shell argument'; GEO_SHELL=$arg ;;
      --json) geo_mode json ;; --human) geo_mode human ;; --coords) geo_mode coords ;;
      --fields) geo_mode fields ;; --stdin) GEO_STDIN=1; GEO_LOOKUP_OPTIONS=1 ;;
      -r|--refresh) GEO_REFRESH=1; GEO_LOOKUP_OPTIONS=1 ;;
      --cached) GEO_CACHED=1; GEO_LOOKUP_OPTIONS=1 ;;
      --allow-stale) GEO_ALLOW_STALE=1; GEO_LOOKUP_OPTIONS=1 ;;
      --install) GEO_INSTALL=1 ;; --all) GEO_ALL=1 ;;
      -v|--verbose) GEO_VERBOSE=1 ;; -h|--help) GEO_HELP=1 ;;
      *) geo_fail 2 "unknown argument: $arg" ;;
    esac
  done
  for value in "${DOTS_COLOR:-auto}" "${DOTS_ICONS:-auto}"; do
    [[ $value == auto || $value == always || $value == never ]] || geo_fail 2 'invalid presentation mode'
  done
  [[ $GEO_TIMEOUT =~ ^[0-9]{1,4}$ && $GEO_MAX_AGE =~ ^[0-9]{1,5}$ ]] || geo_fail 2 'timeout and max-age must be integer seconds'
  GEO_TIMEOUT=$((10#$GEO_TIMEOUT)) GEO_MAX_AGE=$((10#$GEO_MAX_AGE))
  ((GEO_TIMEOUT >= 1 && GEO_TIMEOUT <= 3600 && GEO_MAX_AGE <= 86400)) || geo_fail 2 'timeout or max-age outside allowed range'
  [[ $GEO_PROVIDER == network || $GEO_PROVIDER == gps || $GEO_PROVIDER == passive ]] || geo_fail 2 'invalid location provider'
  [[ $GEO_LANGUAGE =~ ^[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*$ ]] || geo_fail 2 'invalid language code'
  ((GEO_LAT_SET == GEO_LON_SET)) || geo_fail 2 '--lat and --lon must be supplied together'
  ((GEO_STDIN + GEO_LAT_SET <= 1)) || geo_fail 2 'choose one input source'
  if ((GEO_STDIN || GEO_LAT_SET)); then
    (( ! GEO_PROVIDER_SET && ! GEO_REFRESH )) || geo_fail 2 'provider and refresh require device input'
  fi
  (( ! GEO_REFRESH || ! GEO_CACHED )) || geo_fail 2 '--refresh conflicts with --cached'
  (( ! GEO_ALLOW_STALE || GEO_CACHED )) || geo_fail 2 '--allow-stale requires --cached'
  if [[ $GEO_ROUTE == completion ]]; then
    if [[ $GEO_MODE ]] || ((GEO_LOOKUP_OPTIONS)); then geo_fail 2 'completion does not accept lookup modes'; fi
    (( ! GEO_ALL || (GEO_INSTALL && ${#GEO_SHELL} == 0) )) || geo_fail 2 '--all requires --install and no shell'
    [[ $GEO_SHELL || $GEO_ALL == 1 || $GEO_HELP == 1 ]] || geo_fail 2 'completion requires a shell or --all --install'
    (( ! GEO_DIR_SET || GEO_INSTALL )) || geo_fail 2 '--dir requires --install'
    (( ! GEO_DIR_SET )) || [[ $GEO_DIR ]] || geo_fail 2 '--dir must not be empty'
  else
    (( ! GEO_INSTALL && ! GEO_ALL && ! GEO_DIR_SET )) || geo_fail 2 'installation options require completion'
  fi
}
geo_cleanup() {
  geo_stop
  if [[ $GEO_CHILD ]]; then kill -TERM "$GEO_CHILD" 2>/dev/null || :; wait "$GEO_CHILD" 2>/dev/null || :; fi
  [[ ! $GEO_WORK ]] || rm -rf -- "$GEO_WORK"
  [[ ! $GEO_TEMP ]] || rm -f -- "$GEO_TEMP"
  return 0
}
geo_clock() {
  # Android blocks /proc/uptime. Bash 5.3 exposes CLOCK_MONOTONIC directly.
  # Freshness also uses wall elapsed time so suspend cannot retain a fresh fix.
  [[ ${BASH_MONOSECONDS:-} =~ ^[0-9]+$ ]] || geo_fail 1 'cached/device lookups require Bash 5.3 or newer'
  GEO_NOW=$BASH_MONOSECONDS
  if ! { IFS= read -r GEO_BOOT < /proc/sys/kernel/random/boot_id; } 2>/dev/null; then
    GEO_BOOT=''
  fi
}
geo_need() { command -v "$1" >/dev/null 2>&1 || geo_fail 1 "missing dependency: $1 (see --help)"; }
geo_run() {
  local phase=$1 remaining=$((GEO_DEADLINE - SECONDS)) rc=0
  shift
  ((remaining > 0)) || geo_fail 124 "$phase deadline exceeded"
  timeout -k 1 "$remaining" "$@" <&3 & GEO_CHILD=$!
  wait "$GEO_CHILD" || rc=$?
  GEO_CHILD=''
  ((rc != 124 && rc != 137)) || geo_fail 124 "$phase deadline exceeded"
  return "$rc"
}
geo_work() {
  [[ ! $GEO_WORK ]] || return 0
  local base=${TMPDIR:-${PREFIX:+$PREFIX/tmp}}
  GEO_WORK=$(mktemp -d "${base:-/tmp}/termux-geo.XXXXXXXX") || geo_fail 1 'cannot create private work directory'
}
geo_read_cache() {
  [[ ! -L $GEO_CACHE/state.json && ( ! -e $GEO_CACHE/state.json || -f $GEO_CACHE/state.json ) ]] || geo_fail 1 'unsafe cache file'
  [[ -f $GEO_CACHE/state.json ]] || return 1
  GEO_CONTENTS=''
  # A bounded builtin read avoids spawning head on every cached query.
  IFS= read -r -N 262145 GEO_CONTENTS < "$GEO_CACHE/state.json" || :
  ((${#GEO_CONTENTS} <= 262144))
}
geo_load() {
  GEO_STATE='{"version":1,"devices":{},"addresses":[],"rate":{}}'
  if geo_read_cache; then
    if jq -e -L "$GEO_ROOT/lib/termux_geo" 'include "cache"; valid_state' >/dev/null 2>&1 <<< "$GEO_CONTENTS"; then
      GEO_STATE=$GEO_CONTENTS
    else geo_note 'Ignoring malformed cache'; fi
  fi
}
geo_fast_cache() {
  [[ $GEO_MODE != human ]] && (( ! GEO_REFRESH && ! GEO_STDIN && ! GEO_LAT_SET )) || return 1
  geo_read_cache || return 1
  geo_clock
  # All validation/selection completes before the single final output value.
  # Failure emits nothing, then the normal path supplies the precise diagnostic.
  jq -er -L "$GEO_ROOT/lib/termux_geo" --arg p "$GEO_PROVIDER" --arg boot "$GEO_BOOT" \
    --argjson now "$GEO_NOW" --argjson wall "$EPOCHSECONDS" --argjson max "$GEO_MAX_AGE" \
    --argjson stale "$GEO_ALLOW_STALE" --argjson address "$GEO_ADDRESS" \
    --arg endpoint "$GEO_ENDPOINT" --arg language "$GEO_LANGUAGE" --arg mode "$GEO_MODE" \
    --args 'include "cache";
      select(valid_state) | . as $cache | cached_fix($p;$boot;$now;$wall;$max;$stale) |
      if $address == 1 then
        . as $fix | ($endpoint+"|"+$language+"|"+([.latitude,.longitude]|map(tostring)|join(","))) as $key |
        ($cache|cached_address($key;$wall)) as $a | $fix + $a | .address_cached=true
      else . end |
      if $mode == "json" then tojson
      elif $mode == "coords" then [.latitude,.longitude]|map(tostring)|join(",")
      else render_pieces($ARGS.positional) end' -- "${GEO_PIECES[@]}" <<< "$GEO_CONTENTS" 2>/dev/null
}
geo_prepare() {
  [[ ! -L $GEO_CACHE ]] || geo_fail 1 'refusing symlink cache directory'
  mkdir -p -- "$GEO_CACHE" || geo_fail 1 'cannot create cache directory'
  [[ -d $GEO_CACHE && -O $GEO_CACHE ]] || geo_fail 1 'cache directory is not owned by this user'
  chmod 700 -- "$GEO_CACHE" || geo_fail 1 'cannot protect cache directory'
  [[ ! -L $GEO_CACHE/lock && ( ! -e $GEO_CACHE/lock || -f $GEO_CACHE/lock ) ]] || geo_fail 1 'unsafe cache lock'
  exec 9>>"$GEO_CACHE/lock" || geo_fail 1 'cannot open cache lock'
  geo_run 'cache locking' flock -w 1 9 || geo_fail 1 'location lookup is busy; retry or use --cached'
  geo_load
}
geo_save() {
  [[ ! -L $GEO_CACHE/state.json && ( ! -e $GEO_CACHE/state.json || -f $GEO_CACHE/state.json ) ]] || geo_fail 1 'unsafe cache file'
  GEO_TEMP=$(mktemp "$GEO_CACHE/.state.XXXXXXXX") || geo_fail 1 'cannot stage cache'
  if ! { printf '%s\n' "$GEO_STATE" > "$GEO_TEMP" && mv -f -- "$GEO_TEMP" "$GEO_CACHE/state.json"; }; then geo_fail 1 'cannot save cache'; fi
  GEO_TEMP=''
}
geo_device_cache() {
  (( ! GEO_REFRESH )) || return 1
  geo_clock
  GEO_RECORD=$(jq -ce -L "$GEO_ROOT/lib/termux_geo" --arg p "$GEO_PROVIDER" --arg boot "$GEO_BOOT" --argjson now "$GEO_NOW" --argjson wall "$EPOCHSECONDS" \
    --argjson max "$GEO_MAX_AGE" --argjson stale "$GEO_ALLOW_STALE" '
    include "cache"; cached_fix($p;$boot;$now;$wall;$max;$stale)' <<< "$GEO_STATE" 2>/dev/null) || return 1
  geo_note 'Using cached device coordinates'
}
geo_normalize() {
  local source=$1 input=$2
  GEO_RECORD=$(jq -sc --arg action fix --arg source "$source" -f "$GEO_ROOT/lib/termux_geo/normalize.jq" <<< "$input" 2>/dev/null) || geo_fail 1 'location unavailable or invalid; check Termux:API location permissions and provider'
}
geo_acquire() {
  local raw rc=0
  if ((GEO_LAT_SET)); then
    raw=$(jq -cn --arg lat "$GEO_LAT" --arg lon "$GEO_LON" '{latitude:($lat|tonumber),longitude:($lon|tonumber)}' 2>/dev/null) || geo_fail 2 'invalid numeric coordinates'
    jq -e '.latitude >= -90 and .latitude <= 90 and .longitude >= -180 and .longitude <= 180' >/dev/null <<< "$raw" || geo_fail 2 'coordinates out of range'
    geo_normalize explicit "$raw"
  elif ((GEO_STDIN)); then
    geo_work
    geo_run 'stdin reading' head -c 65537 > "$GEO_WORK/input" || geo_fail 1 'cannot read location input'
    raw=$(<"$GEO_WORK/input")
    ((${#raw} <= 65536)) || geo_fail 1 'location input exceeds 64 KiB'
    [[ $(jq -s 'length' <<< "$raw" 2>/dev/null) == 1 ]] || geo_fail 1 'stdin requires exactly one JSON object'
    geo_normalize stdin "$raw"
  else
    geo_device_cache && return 0
    (( ! GEO_CACHED )) || geo_fail 1 'no acceptable cached device fix; run --refresh or explicitly --cached --allow-stale'
    geo_need termux-location
    geo_need wc
    geo_phase 'Getting location'
    geo_work
    # Bound captured stdout, not the API process's file-size resource limit:
    # a reduced RLIMIT_FSIZE makes the native Termux API bridge hang.
    # Keep both pipeline children inside the timed process group. The signal
    # trap lets Bash reap them before exiting during timeout/cancellation.
    # shellcheck disable=SC2016
    geo_run 'device location' bash -o pipefail -c '
      trap "exit 143" TERM HUP
      termux-location -p "$1" -r once | head -c 65537
    ' _ "$GEO_PROVIDER" > "$GEO_WORK/fix" 2> "$GEO_WORK/error" || rc=$?
    # Check bytes before loading into Bash, which strips trailing newlines/NULs.
    (($(wc -c < "$GEO_WORK/fix") <= 65536)) || geo_fail 1 'device location response exceeds 64 KiB'
    ((rc == 0)) || geo_fail 1 'device location failed; check Termux:API permissions, location settings, and provider'
    raw=$(<"$GEO_WORK/fix")
    geo_normalize device "$raw"
    jq -e --argjson max "$GEO_MAX_AGE" '.age_seconds != null and ($max == 0 or .age_seconds <= $max)' >/dev/null <<< "$GEO_RECORD" || geo_fail 1 'device returned an old or undated fix; try another provider'
    geo_clock
    GEO_STATE=$(jq -c --arg p "$GEO_PROVIDER" --arg boot "$GEO_BOOT" --argjson now "$GEO_NOW" --argjson wall "$EPOCHSECONDS" --argjson data "$GEO_RECORD" \
      '.devices[$p]={boot:$boot,at:$now,wall:$wall,data:$data}' <<< "$GEO_STATE") || geo_fail 1 'cannot encode device cache'
    geo_save
  fi
}
geo_address_cache() {
  local address
  address=$(jq -ce -L "$GEO_ROOT/lib/termux_geo" --arg key "$GEO_KEY" --argjson now "$EPOCHSECONDS" '
    include "cache"; cached_address($key;$now)' <<< "$GEO_STATE" 2>/dev/null) || return 1
  GEO_RECORD=$(jq -c --argjson a "$address" '. + $a | .address_cached=true' <<< "$GEO_RECORD") || return 1
  geo_note 'Using cached address'
}
geo_lookup() {
  local coords raw address rate headers code seconds
  coords=$(jq -r '[.latitude,.longitude]|map(tostring)|join(",")' <<< "$GEO_RECORD")
  GEO_KEY="$GEO_ENDPOINT|$GEO_LANGUAGE|$coords"
  geo_address_cache && return 0
  (( ! GEO_CACHED )) || { GEO_LOOKUP_ERROR='no cached address for these coordinates and language'; return 1; }
  geo_need curl
  geo_clock
  rate=$(jq -r --arg boot "$GEO_BOOT" --argjson now "$GEO_NOW" '
    .rate | if .boot == $boot and (.next|type) == "number" then ([.next-$now,0]|max|ceil) else 0 end' <<< "$GEO_STATE")
  if ((rate > 0)); then GEO_LOOKUP_ERROR="address service cooldown; retry after $rate seconds or use --cached"; return 1; fi
  # Apply the same conservative floor to endpoint overrides, including aliases
  # of the public server. Switching endpoints cannot bypass an active cooldown.
  seconds=15
  GEO_STATE=$(jq -c --arg boot "$GEO_BOOT" --arg endpoint "$GEO_ENDPOINT" --argjson next "$((GEO_NOW+seconds))" '.rate={boot:$boot,endpoint:$endpoint,next:$next}' <<< "$GEO_STATE")
  geo_save
  geo_work; geo_phase 'Looking up address'
  geo_run 'address lookup' curl -q --silent --show-error --proto '=https' --connect-timeout 5 --max-time "$GEO_TIMEOUT" --max-filesize 131072 \
    --user-agent 'androidots-termux-geo/1.0 (personal location lookup)' --get "$GEO_ENDPOINT" \
    --data-urlencode "lat=${coords%,*}" --data-urlencode "lon=${coords#*,}" \
    --data-urlencode 'format=jsonv2' --data-urlencode 'addressdetails=1' --data-urlencode "accept-language=$GEO_LANGUAGE" \
    --dump-header "$GEO_WORK/headers" --output "$GEO_WORK/address" --write-out '%{http_code}' > "$GEO_WORK/code" 2> "$GEO_WORK/error" || {
      [[ $? != 28 ]] || geo_fail 124 'address lookup timed out; check connectivity or try later'
      GEO_LOOKUP_ERROR='address request failed; check connectivity or try later'; return 1;
    }
  code=$(<"$GEO_WORK/code")
  # Honor Retry-After seconds or HTTP dates without displaying remote headers.
  headers=$(<"$GEO_WORK/headers")
  while IFS= read -r raw; do
    if [[ ${raw,,} == retry-after:* ]]; then
      raw=${raw#*:}; raw=${raw%$'\r'}; raw=${raw#"${raw%%[![:space:]]*}"}
      if [[ $raw =~ ^[0-9]{1,9}$ ]]; then seconds=$((10#$raw))
      elif rate=$(date -d "$raw" +%s 2>/dev/null); then seconds=$((rate-EPOCHSECONDS))
      else seconds=0; fi
      ((seconds > 0)) || continue
      geo_clock
      GEO_STATE=$(jq -c --argjson next "$((GEO_NOW+seconds))" '.rate.next=([.rate.next,$next]|max)' <<< "$GEO_STATE"); geo_save
    fi
  done <<< "$headers"
  if [[ $code != 200 ]]; then GEO_LOOKUP_ERROR="address service returned HTTP $code; retry later"; return 1; fi
  raw=$(<"$GEO_WORK/address")
  address=$(jq -sc --arg action address --arg source '' -f "$GEO_ROOT/lib/termux_geo/normalize.jq" <<< "$raw" 2>/dev/null) || {
    GEO_LOOKUP_ERROR='address unavailable or invalid response'; return 1;
  }
  GEO_RECORD=$(jq -c --argjson a "$address" '. + $a' <<< "$GEO_RECORD")
  GEO_STATE=$(jq -c --arg key "$GEO_KEY" --argjson at "$EPOCHSECONDS" --argjson data "$address" \
    '.addresses=([{key:$key,at:$at,data:$data}] + [.addresses[]|select(.key != $key and .at <= $at and $at-.at < 86400)])[:32]
      | until((tojson|utf8bytelength) <= 250000 or (.addresses|length) == 0; .addresses |= .[:-1])' <<< "$GEO_STATE")
  geo_save
}
geo_render() {
  geo_stop
  local field value label rendered
  case $GEO_MODE in
    json) printf '%s\n' "$GEO_RECORD" ;;
    coords) jq -r '[.latitude,.longitude]|map(tostring)|join(",")' <<< "$GEO_RECORD" ;;
    get|format)
      rendered=$(jq -ce -L "$GEO_ROOT/lib/termux_geo" --args '
        include "cache"; render_pieces($ARGS.positional)' -- "${GEO_PIECES[@]}" <<< "$GEO_RECORD" 2>/dev/null) || geo_fail 1 'a requested field is unavailable; inspect --json for available fields'
      jq -r . <<< "$rendered" ;;
    human)
      [[ $GEO_UI != 1 ]] || dots::heading 'Location'
      [[ $GEO_UI == 1 ]] || printf 'Location\n'
      while IFS= read -r field; do
        value=$(jq -r --arg f "$field" '.[$f] | if . == null then "Unavailable" else tostring end' <<< "$GEO_RECORD")
        case $field in accuracy_m) label='Accuracy (m)' ;; age_seconds) label='Fix age (seconds)' ;; *) label=${field^}; label=${label//_/ } ;; esac
        if [[ $GEO_UI == 1 ]]; then dots::text "$value"; dots::row "$label" "$REPLY"
        else printf '  %s: %s\n' "$label" "${value//[[:cntrl:]]/?}"; fi
      done <<< $'city\nstate\npostcode\ncountry\naddress\nlatitude\nlongitude\naccuracy_m\nsource\nprovider\nage_seconds\ncached\nstale\nattribution'
      ;;
  esac
}
geo_main() {
  # Preserve stdin for explicitly requested --stdin despite asynchronous waits,
  # and keep our diagnostics visible when child stderr is captured privately.
  exec 3<&0 4>&2
  GEO_PIECES=()
  GEO_MODE='' GEO_ROUTE='' GEO_FIELD='' GEO_TEMPLATE='' GEO_HUMAN=0 GEO_UI=0 GEO_VERBOSE=0 GEO_HELP=0
  GEO_LAT='' GEO_LON='' GEO_LAT_SET=0 GEO_LON_SET=0 GEO_STDIN=0 GEO_PROVIDER=network GEO_PROVIDER_SET=0
  GEO_REFRESH=0 GEO_CACHED=0 GEO_MAX_AGE=60 GEO_ALLOW_STALE=0 GEO_TIMEOUT=20 GEO_LANGUAGE=en GEO_ADDRESS=0
  GEO_INSTALL=0 GEO_ALL=0 GEO_DIR='' GEO_DIR_SET=0 GEO_SHELL='' GEO_WORK='' GEO_TEMP='' GEO_CHILD='' GEO_LOOKUP_OPTIONS=0
  GEO_ENDPOINT=${TERMUX_GEO_ENDPOINT:-https://nominatim.openstreetmap.org/reverse}
  geo_parse "$@"
  if [[ $GEO_ROUTE == completion ]]; then
    GEO_HUMAN=$GEO_INSTALL; (( ! GEO_HELP )) || GEO_HUMAN=1
    geo_ui || return 1
    if ((GEO_HELP)); then geo_help; return; fi
    source "$GEO_ROOT/lib/termux_geo/completion.bash"
    geo_completion; return
  fi
  if ((GEO_HELP)); then GEO_HUMAN=1; geo_ui || return 1; geo_help; return; fi
  if [[ $GEO_MODE == fields ]]; then
    local -a fields
    read -r -a fields <<< "$GEO_FIELDS"; printf '%s\n' "${fields[@]}"; return
  fi
  if [[ ! $GEO_MODE ]]; then if [[ -t 1 ]]; then GEO_MODE=human; else GEO_MODE=json; fi; fi
  case $GEO_MODE in
    human) GEO_HUMAN=1; GEO_ADDRESS=1 ;; json) GEO_ADDRESS=1 ;;
    get) geo_field "$GEO_FIELD"; GEO_PIECES=("F$REPLY") ;;
    format) geo_template "$GEO_TEMPLATE" ;;
  esac
  geo_ui || return 1
  geo_need jq; geo_need timeout; geo_need head
  [[ $GEO_ENDPOINT =~ ^https://[^/?#[:space:]@]+/[^?#[:space:]]*$ ]] || geo_fail 2 'TERMUX_GEO_ENDPOINT must be an HTTPS endpoint without credentials, query, or fragment'
  GEO_DEADLINE=$((SECONDS+GEO_TIMEOUT))
  trap geo_cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM HUP
  umask 077
  GEO_CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/termux-geo
  [[ ! -L $GEO_CACHE ]] || geo_fail 1 'refusing symlink cache directory'
  geo_fast_cache && return 0
  if ((GEO_STDIN || GEO_LAT_SET)); then
    geo_acquire
    if (( ! GEO_ADDRESS )); then geo_render; return; fi
    geo_load
    if (( ! GEO_CACHED )); then geo_need flock; geo_prepare; fi
    if ! geo_lookup; then
      [[ $GEO_MODE != human ]] || geo_render
      geo_fail 1 "$GEO_LOOKUP_ERROR"
    fi
    geo_render; return
  fi
  geo_load
  # A warm device hit returns without locks, temporary files, or Android/HTTP.
  if (( ! GEO_STDIN && ! GEO_LAT_SET )) && geo_device_cache; then
    if (( ! GEO_ADDRESS )); then geo_render; return; fi
    GEO_KEY="$GEO_ENDPOINT|$GEO_LANGUAGE|$(jq -r '[.latitude,.longitude]|map(tostring)|join(",")' <<< "$GEO_RECORD")"
    if geo_address_cache; then geo_render; return; fi
  fi
  if (( ! GEO_CACHED )); then geo_need flock; geo_prepare; fi
  geo_acquire
  if ((GEO_ADDRESS)) && ! geo_lookup; then
    [[ $GEO_MODE != human ]] || geo_render
    geo_fail 1 "$GEO_LOOKUP_ERROR"
  fi
  geo_note "Completed in $SECONDS seconds"
  geo_render
}
