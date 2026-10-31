# Sourceable Bash presentation helpers. Static views use builtins; an active
# progress worker is stopped before output. Never source shell configuration.
typeset -gA dots_options _DOTS_STYLE_ICONS _DOTS_STYLE_COLORS _DOTS_FORMATTING
# DOTS_COLOR / DOTS_ICONS: auto, always, never; dispatcher flags override them.
dots::settings() {
  if [[ -z ${_DOTS_CONFIG_PATH:-} && -n ${DOTS:-} && -r $DOTS/lib/dots/shell/config.bash ]]; then
    source "$DOTS/lib/dots/shell/config.bash"
    _dots_config_load || return
  fi
}
dots::icon() { REPLY=${_DOTS_STYLE_ICONS[$1]-${2-}}; }
dots::style() {
  dots::settings || return
  [[ -z ${DOTS_PROGRESS_FD:-} ]] || dots::progress_stop
  local fd=${1:-1} mode=${DOTS_COLOR:-${dots_options[DOTS_COLOR]:-auto}} icons=${DOTS_ICONS:-${dots_options[DOTS_ICONS]:-auto}}
  DOTS_UI_RESET='' DOTS_UI_BOLD='' DOTS_UI_BLUE='' DOTS_UI_GREEN=''
  DOTS_UI_YELLOW='' DOTS_UI_RED='' DOTS_UI_CYAN='' DOTS_UI_MAGENTA='' DOTS_UI_DIM=''
  DOTS_UI_INFO='[i]' DOTS_UI_OK='[+]' DOTS_UI_WARN='[!]' DOTS_UI_ERROR='[x]'
  if [[ $mode == always ]] || [[ $mode == auto && -t $fd && ${TERM:-dumb} != dumb && -z ${NO_COLOR:-} ]]; then
    DOTS_UI_RESET=$'\e[0m' DOTS_UI_BOLD=$'\e[1m'
    DOTS_UI_BLUE=$'\e[94m' DOTS_UI_CYAN=$'\e[96m' DOTS_UI_GREEN=$'\e[92m'
    DOTS_UI_YELLOW=$'\e[93m' DOTS_UI_RED=$'\e[91m'
    # Shared tokens consumed by command-specific library renderers.
    # shellcheck disable=SC2034
    DOTS_UI_MAGENTA=$'\e[95m' DOTS_UI_DIM=$'\e[2m'
    local token code
    for token in BLUE:94 CYAN:96 GREEN:92 YELLOW:93 RED:91 MAGENTA:95 DIM:90; do
      code=${token#*:}; token=${token%:*}
      printf -v "DOTS_UI_$token" '\e[%sm' "${_DOTS_STYLE_COLORS[$code]:-$code}"
    done
  fi
  if [[ $icons == always ]] || [[ $icons == auto && -t $fd && ${TERM:-dumb} != dumb ]]; then
    DOTS_UI_INFO=${_DOTS_STYLE_ICONS[status.info]-󰋽} DOTS_UI_OK=${_DOTS_STYLE_ICONS[status.success]-}
    DOTS_UI_WARN=${_DOTS_STYLE_ICONS[status.warning]-} DOTS_UI_ERROR=${_DOTS_STYLE_ICONS[status.error]-}
  fi
}
# Root usage branding. Keep the builtin classic/plain path available without Python.
dots::logo() {
  dots::style
  local line i steps
  local -a lines=()
  while IFS='' read -r line || [[ -n $line ]]; do lines+=("$line"); done
  if [[ $DOTS_UI_RESET && -r ${DOTS_LIB_DIR:-}/usage_logo.py ]] && ((${#lines[@]})) && command -v python3 >/dev/null 2>&1; then
    if printf '%s\n' "${lines[@]}" | command python3 -B "$DOTS_LIB_DIR/usage_logo.py" --color=always --stdin; then return 0; fi
  fi
  steps=$((${#lines[@]} - 1))
  (( steps > 0 )) || steps=1
  for ((i=0; i<${#lines[@]}; i++)); do
    if [[ $DOTS_UI_RESET ]]; then
      printf '\e[38;2;0;%d;255m%s%s\n' "$((96 + 159 * i / steps))" "${lines[i]}" "$DOTS_UI_RESET"
    else
      printf '%s\n' "${lines[i]}"
    fi
  done
}
dots::heading() { dots::style; printf '%s%s%s%s\n' "$DOTS_UI_BOLD" "$DOTS_UI_CYAN" "$*" "$DOTS_UI_RESET"; }
dots::row() {
  dots::style
  if dots::human && [[ ${_DOTS_FORMATTING[label_width]+set} ]]; then
    dots::aligned_row "$1" "${2:-}" "$DOTS_UI_BLUE" ''
    return
  fi
  local width=26 columns=${COLUMNS:-80} value=${2:-}
  [[ $columns =~ ^[0-9]+$ ]] && (( 10#$columns < 60 )) && width=0
  if dots::human; then
    [[ $columns =~ ^[0-9]+$ ]] || columns=80
    columns=$((10#$columns)); (( columns >= 20 )) || columns=20
    if (( width && ${#1} <= width && ${#value} <= columns-29 )) && [[ $1 != *[!\ -~]* && $value != *[!\ -~]* ]]; then
      printf '  %s%-26s%s %s\n' "$DOTS_UI_BLUE" "$1" "$DOTS_UI_RESET" "${2:-}"
      return
    fi
    if (( width == 0 || ${#1} > width )) || [[ $1 == *[!\ -~]* ]]; then
      dots::line "$1" "$DOTS_UI_BLUE" 2 "$columns"
      [[ ! ${2:-} ]] || dots::line "$2" '' 6 "$columns"
    else
      dots::text "$1"
      printf '  %s%-26s%s ' "$DOTS_UI_BLUE" "$REPLY" "$DOTS_UI_RESET"
      dots::line "${2:-}" '' 29 "$columns" first
    fi
    return
  fi
  if (( width == 0 || ${#1} > width )); then
    printf '  %s%s%s\n      %s\n' "$DOTS_UI_BLUE" "$1" "$DOTS_UI_RESET" "${2:-}"
  else
    printf '  %s%-26s%s %s\n' "$DOTS_UI_BLUE" "$1" "$DOTS_UI_RESET" "${2:-}"
  fi
}
# Shared human column preferences. Values come from the validated literal reader.
dots::aligned_row() {
  local label=$1 text=$2 label_color=$3 value_color=$4 columns=${COLUMNS:-80}
  local indent=${_DOTS_FORMATTING[indent]:-4} gap=${_DOTS_FORMATTING[label_gap]:-1}
  local width=${_DOTS_FORMATTING[label_width]:-10} align=${_DOTS_FORMATTING[alignment]:-left}
  local char i label_cells=0 number padding left=0 prefix prefix_width
  [[ $columns =~ ^[0-9]{1,6}$ ]] || columns=80
  columns=$((10#$columns)); (( columns >= 8 )) || columns=8
  indent=$((10#$indent)); gap=$((10#$gap))
  (( indent <= columns-8 )) || indent=$((columns-8))
  (( gap <= columns-indent-8 )) || gap=$((columns-indent-8))
  if [[ $width == *% ]]; then number=${width%\%}; width=$((columns*10#$number/100))
  else width=$((10#$width)); fi
  (( width <= columns-indent-gap-8 )) || width=$((columns-indent-gap-8))
  dots::text "$label"; label=$REPLY
  for ((i=0;i<${#label};i++)); do
    char=${label:i:1}; printf -v number '%d' "'$char"
    # Combining marks occupy no cells; common wide CJK/emoji occupy two.
    if (( number>=768 && number<=879 || number>=65024 && number<=65039 )); then :
    elif (( number>=4352 && number<=4447 || number>=11904 && number<=42191 || number>=44032 && number<=55203 || number>=63744 && number<=64255 || number>=65281 && number<=65376 || number>=127744 && number<=129791 )); then ((label_cells+=2))
    else ((label_cells+=1)); fi
  done
  padding=$((width-label_cells)); (( padding >= 0 )) || padding=0
  [[ $align != right ]] || left=$padding
  [[ $align != center ]] || left=$((padding/2))
  prefix_width=$((indent+label_cells+padding+gap))
  if (( width && label_cells>width || prefix_width>columns-8 )); then
    dots::line "$label" "$label_color" "$indent" "$columns"
    dots::line "$text" "$value_color" "$((indent+width+gap))" "$columns"
  else
    printf -v prefix '%*s' "$((indent+left))" ''
    printf '%s%s%s%*s%s' "$label_color" "$prefix" "$label" "$((padding-left+gap))" '' "$DOTS_UI_RESET"
    dots::line "$text" "$value_color" "$prefix_width" "$columns" first
  fi
}
# Inert text and conservative terminal widths, using only shell builtins.
dots::text() {
  local text=$1 char i number probe='ü'
  REPLY=''
  if [[ $text != *[!\ -~]* ]]; then REPLY=$text; return; fi
  if (( ${#probe} != 1 )) && [[ $text == *[!\ -~]* ]]; then
    printf -v REPLY '%q' "$text"
    return
  fi
  for ((i=0; i<${#text}; i++)); do
    char=${text:i:1}; printf -v number '%d' "'$char"
    if (( number < 32 || (number >= 127 && number < 160) )); then printf -v char '\\u%04x' "$number"; fi
    REPLY+=$char
  done
}
dots::line() {
  local text=$1 color=$2 indent=$3 columns=$4 first=${5:-} part='' char size used=0 i room
  dots::text "$text"; text=$REPLY
  room=$((columns-indent)); (( room >= 8 )) || room=8
  if (( ${#text} <= room )) && [[ $text != *[!\ -~]* ]]; then
    [[ $first ]] || printf '%*s' "$indent" ''
    printf '%s%s%s\n' "$color" "$text" "$DOTS_UI_RESET"
    return
  fi
  for ((i=0; i<${#text}; i++)); do
    char=${text:i:1}; size=1; [[ $char == [\ -~] ]] || size=2
    if (( used+size > room && used )); then
      [[ $first ]] || printf '%*s' "$indent" ''
      dots::breakline "$part" "$room"
      printf '%s%s%s\n' "$color" "$REPLY" "$DOTS_UI_RESET"
      first='' part=$DOTS_LINE_TAIL used=$DOTS_LINE_CELLS
    fi
    part+=$char; ((used+=size))
  done
  [[ $first ]] || printf '%*s' "$indent" ''
  printf '%s%s%s\n' "$color" "$part" "$DOTS_UI_RESET"
}
# Prefer a slash/space boundary while retaining the delimiter and every byte.
dots::breakline() {
  local part=$1 room=$2 i char count=0 boundary=0
  for ((i=0; i<${#part}; i++)); do
    char=${part:i:1}; ((count+=1)); [[ $char == [\ -~] ]] || ((count+=1))
    if [[ $char == / || $char == ' ' ]] && (( count >= room/2 )); then boundary=$((i+1)); fi
  done
  REPLY=$part DOTS_LINE_TAIL='' DOTS_LINE_CELLS=0
  if (( boundary )); then
    REPLY=${part:0:boundary}; DOTS_LINE_TAIL=${part:boundary}
    for ((i=0; i<${#DOTS_LINE_TAIL}; i++)); do
      ((DOTS_LINE_CELLS+=1)); [[ ${DOTS_LINE_TAIL:i:1} == [\ -~] ]] || ((DOTS_LINE_CELLS+=1))
    done
  fi
  return 0
}
dots::kv() { dots::row "$@"; }
dots::info() { dots::style; printf '%s%s%s %s\n' "$DOTS_UI_BLUE" "$DOTS_UI_INFO" "$DOTS_UI_RESET" "$*"; }
dots::success() { dots::style; printf '%s%s%s %s\n' "$DOTS_UI_GREEN" "$DOTS_UI_OK" "$DOTS_UI_RESET" "$*"; }
dots::warning() { dots::style 2; printf '%s%s%s %s\n' "$DOTS_UI_YELLOW" "$DOTS_UI_WARN" "$DOTS_UI_RESET" "$*" >&2; }
dots::error() { dots::style 2; printf '%s%s%s %s\n' "$DOTS_UI_RED" "$DOTS_UI_ERROR" "$DOTS_UI_RESET" "$*" >&2; }

# Rich listings in terminals, or when decoration is explicitly requested.
# Value/path/JSON commands must bypass this regardless of presentation settings.
dots::human() { dots::settings || return; [[ -t 1 || ${DOTS_COLOR:-${dots_options[DOTS_COLOR]:-auto}} == always || ${DOTS_ICONS:-${dots_options[DOTS_ICONS]:-auto}} == always ]]; }
dots::path() {
  REPLY=$1
  # A literal tilde is for display, not path resolution.
  # shellcheck disable=SC2088
  [[ ! ${HOME:-} || $1 != "$HOME"/* ]] || REPLY="~/${1#"$HOME"/}"
}
dots::swatch() {
  dots::style
  local hex=${1#\#}
  [[ $hex =~ ^[a-fA-F0-9]{6}$ && $DOTS_UI_RESET ]] || return 0
  printf '\e[48;2;%d;%d;%dm  %s ' "$((16#${hex:0:2}))" "$((16#${hex:2:2}))" "$((16#${hex:4:2}))" "$DOTS_UI_RESET"
}

# Resource tables are loaded only when a human view actually renders a path.
# Keep help, data interfaces and ordinary dispatch free of theme/catalog scans.
dots::resource() {
  source "${BASH_SOURCE[0]%/*}/resources.bash"
  dots::resource "$@"
}
dots::resource_row() {
  source "${BASH_SOURCE[0]%/*}/resources.bash"
  dots::resource_row "$@"
}

# Git role styles are published data, loaded only by a colored human Git view.
dots::git_style() {
  source "${BASH_SOURCE[0]%/*}/git-styles.bash"
  dots::git_style "$@"
}
