# Read only the documented literal colors from colors.sh; never source the export.
dt_pywal_load() {
  local line key value count=0 LC_ALL=C
  local assignment="^[[:space:]]*(background|foreground|cursor|color[0-9]+)=(['\"])(#[a-fA-F0-9]{6})(['\"])[[:space:]]*$"
  DT_PYWAL_FILE=${DOTS_PYWAL_FILE:-${PYWAL_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/wal}/colors.sh}
  [[ -f $DT_PYWAL_FILE && -r $DT_PYWAL_FILE ]] || { dt_error 'pywal16 colors.sh is unavailable; generate a palette with wal first or set DOTS_PYWAL_FILE'; return 1; }
  DT_DATA=() DT_KEYS=()
  # Bound the entire read before parsing, including ignored wallpaper/FZF lines.
  if IFS= read -r -d '' -n 65537 DT_PYWAL_INPUT < "$DT_PYWAL_FILE"; then
    dt_error 'pywal16 export contains NUL or exceeds 64 KiB'; return 1
  fi
  while [[ $DT_PYWAL_INPUT == *$'\n' ]]; do DT_PYWAL_INPUT=${DT_PYWAL_INPUT%$'\n'}; done
  while IFS= read -r line || [[ $line ]]; do
    (( ++count )); line=${line%$'\r'}
    if [[ $line =~ $assignment ]]; then
      [[ ${BASH_REMATCH[2]} == "${BASH_REMATCH[4]}" ]] || { dt_error "pywal16 export:$count: mismatched quotes"; return 1; }
      key=${BASH_REMATCH[1]} value=${BASH_REMATCH[3]}
      case $key in background|foreground|cursor|color[0-9]|color1[0-5]) ;; *) continue ;; esac
      [[ ! ${DT_DATA[$key]+yes} ]] || { dt_error "pywal16 export:$count: duplicate color $key"; return 1; }
      DT_DATA[$key]=$value
    elif [[ $line =~ ^[[:space:]]*(background|foreground|cursor|color[0-9]+)= ]]; then
      dt_error "pywal16 export:$count: expected a literal #RRGGBB color"; return 1
    fi
  done <<< "$DT_PYWAL_INPUT"
  DT_KEYS=(background foreground cursor)
  for ((count=0; count<16; count++)); do DT_KEYS+=("color$count"); done
  for key in "${DT_KEYS[@]}"; do
    [[ ${DT_DATA[$key]+yes} ]] || { dt_error "pywal16 export: missing $key"; return 1; }
  done
}
