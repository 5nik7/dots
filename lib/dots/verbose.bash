# Human operation details. The owning route opts in with a scoped variable.
source "${BASH_SOURCE[0]%/*}/progress.bash"

dots::operation() {
  [[ ${DOTS_OPERATION_VERBOSE:-0} == 1 ]] || return 0
  dots::progress_print dots::_operation_row "$@" || DOTS_OPERATION_VERBOSE=0
  return 0
}

# label, source, destination, reason, known source kind, known destination kind
dots::_operation_row() {
  local label=$1 source=${2:-} target=${3:-} reason=${4:-} kind=${5:-} target_kind=${6:-}
  local left='' right='' plain_left='' plain_right='' columns=${COLUMNS:-${DOTS_OPERATION_COLUMNS:-}} code
  if [[ ! $columns && -t 2 ]] && command -v stty >/dev/null 2>&1; then
    read -r _ DOTS_OPERATION_COLUMNS < <(stty size <&2 2>/dev/null) || DOTS_OPERATION_COLUMNS=80
    columns=$DOTS_OPERATION_COLUMNS
  fi
  [[ $columns =~ ^[0-9]{1,4}$ ]] || columns=80
  # The shared resource renderer uses this dynamically scoped terminal width.
  local COLUMNS=$columns
  dots::style
  code=$DOTS_UI_GREEN
  case $label in
    Unchanged|Skipped|Cleaned) code=$DOTS_UI_DIM ;;
    'Recovery copy'|'Recovery kept'|'Rolled back') code=$DOTS_UI_YELLOW ;;
    Failed|Conflict) code=$DOTS_UI_RED ;;
    'Would '*|Preparing) code=$DOTS_UI_BLUE ;;
  esac
  if [[ $source ]]; then
    dots::path "$source"; dots::resource "$source" "$REPLY" "$kind"
    left=$REPLY plain_left=$DOTS_RESOURCE_TEXT
  fi
  if [[ $target ]]; then
    dots::path "$target"; dots::resource "$target" "$REPLY" "$target_kind"
    right=$REPLY plain_right=$DOTS_RESOURCE_TEXT
  fi
  dots::text "$label"; label=$REPLY
  local plain="$label  $plain_left -> $plain_right" cells=2 i
  for ((i=0;i<${#plain};i++)); do
    ((cells+=1)); [[ ${plain:i:1} == [\ -~] ]] || ((cells+=1))
  done
  if (( cells < 10#$columns )); then
    printf '  %s%s%s  %s' "$code" "$label" "$DOTS_UI_RESET" "$left"
    [[ ! $target ]] || printf ' -> %s' "$right"
    printf '\n'
  else
    dots::line "$label" "$code" 2 "$columns"
    [[ ! $source ]] || { dots::path "$source"; dots::resource_row 'Source' "$source" "$REPLY" "$kind"; }
    [[ ! $target ]] || { dots::path "$target"; dots::resource_row '->' "$target" "$REPLY" "$target_kind"; }
  fi
  [[ ! $reason ]] || dots::line "$reason" "$DOTS_UI_DIM" 6 "$columns"
  return 0
}
