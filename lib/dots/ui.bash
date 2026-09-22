# Sourceable Bash presentation helpers. No shell configuration or subprocesses.
# DOTS_COLOR / DOTS_ICONS: auto, always, never; dispatcher flags override them.
dots::style() {
  local fd=${1:-1} mode=${DOTS_COLOR:-auto} icons=${DOTS_ICONS:-auto}
  DOTS_UI_RESET='' DOTS_UI_BOLD='' DOTS_UI_BLUE='' DOTS_UI_GREEN=''
  DOTS_UI_YELLOW='' DOTS_UI_RED='' DOTS_UI_CYAN=''
  DOTS_UI_INFO='[i]' DOTS_UI_OK='[+]' DOTS_UI_WARN='[!]' DOTS_UI_ERROR='[x]'
  if [[ $mode == always ]] || [[ $mode == auto && -t $fd && ${TERM:-dumb} != dumb && -z ${NO_COLOR:-} ]]; then
    DOTS_UI_RESET=$'\e[0m' DOTS_UI_BOLD=$'\e[1m'
    DOTS_UI_BLUE=$'\e[94m' DOTS_UI_CYAN=$'\e[96m' DOTS_UI_GREEN=$'\e[92m'
    DOTS_UI_YELLOW=$'\e[93m' DOTS_UI_RED=$'\e[91m'
  fi
  if [[ $icons == always ]] || [[ $icons == auto && -t $fd && ${TERM:-dumb} != dumb ]]; then
    DOTS_UI_INFO='󰋽' DOTS_UI_OK='' DOTS_UI_WARN='' DOTS_UI_ERROR=''
  fi
}
dots::heading() { dots::style; printf '%s%s%s%s\n' "$DOTS_UI_BOLD" "$DOTS_UI_CYAN" "$*" "$DOTS_UI_RESET"; }
dots::row() {
  dots::style
  local width=26 columns=${COLUMNS:-80}
  [[ $columns =~ ^[0-9]+$ ]] && (( 10#$columns < 60 )) && width=0
  if (( width == 0 || ${#1} > width )); then
    printf '  %s%s%s\n      %s\n' "$DOTS_UI_BLUE" "$1" "$DOTS_UI_RESET" "${2:-}"
  else
    printf '  %s%-26s%s %s\n' "$DOTS_UI_BLUE" "$1" "$DOTS_UI_RESET" "${2:-}"
  fi
}
dots::kv() { dots::row "$@"; }
dots::info() { dots::style; printf '%s%s%s %s\n' "$DOTS_UI_BLUE" "$DOTS_UI_INFO" "$DOTS_UI_RESET" "$*"; }
dots::success() { dots::style; printf '%s%s%s %s\n' "$DOTS_UI_GREEN" "$DOTS_UI_OK" "$DOTS_UI_RESET" "$*"; }
dots::warning() { dots::style 2; printf '%s%s%s %s\n' "$DOTS_UI_YELLOW" "$DOTS_UI_WARN" "$DOTS_UI_RESET" "$*" >&2; }
dots::error() { dots::style 2; printf '%s%s%s %s\n' "$DOTS_UI_RED" "$DOTS_UI_ERROR" "$DOTS_UI_RESET" "$*" >&2; }
