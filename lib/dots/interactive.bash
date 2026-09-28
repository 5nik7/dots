# Optional interactive presentation, sourced only by interactive command paths.
# Callers validate labels/data and reserve fd 3 for the terminal before capturing
# selector stdout. No tool probes or subprocesses run merely by sourcing this file.
dots::interactive_backend() {
  REPLY=plain
  [[ ${TERM:-dumb} != dumb ]] || return 0
  if command -v gum >/dev/null 2>&1; then REPLY=gum
  elif command -v fzf >/dev/null 2>&1; then REPLY=fzf
  fi
}
dots::interactive_run() (
  dots::style 3
  if [[ $DOTS_UI_RESET ]]; then
    unset NO_COLOR
    export CLICOLOR=1 CLICOLOR_FORCE=1 FORCE_COLOR=1
  else
    export NO_COLOR=1 CLICOLOR=0 CLICOLOR_FORCE=0 FORCE_COLOR=0
  fi
  "$@" 2>&3
)
dots::gum_pick() {
  local kind=$1 header=$2 initial=$3 status
  shift 3
  local -a flags=(--limit=1 --no-limit=false --select-if-one=false --timeout=0s --output-delimiter=$'\n' --padding='0 0')
  dots::style 3
  if [[ $DOTS_UI_INFO == '[i]' ]]; then
    flags+=(--show-help=false --selected-prefix='> ' --unselected-prefix='  ')
    if [[ $kind == filter ]]; then flags+=(--indicator='> ')
    else flags+=(--cursor='> ' --cursor-prefix='> ')
    fi
  fi
  if [[ $kind == filter ]]; then
    flags+=(--strict --value='' --selected='' --prompt='Filter: ' --placeholder='Type to filter')
  else
    flags+=(--selected="$initial" --label-delimiter='' --ordered=false)
  fi
  if REPLY=$(dots::interactive_run gum "$kind" "${flags[@]}" --header="$header" -- "$@"); then
    [[ $REPLY ]] || return 130
  else
    status=$?
    # Gum 2.0 uses 1 for both Escape and errors. Preserve it, without retry.
    (( status == 130 )) && return 130
    dots::error 'Selector ended without a selection or failed.'
    return 1
  fi
}
dots::numbered_pick() {
  local header=$1 default=$2 i answer key
  shift 2
  local -a choices=("$@")
  printf '\n%s\n' "$header"
  for ((i=0;i<${#choices[@]};i++)); do printf '  %d) %s\n' "$((i+1))" "${choices[i]}"; done
  while :; do
    printf 'Number%s (Esc cancels): ' "${default:+ [$default]}"
    answer=''
    while :; do
      if ! IFS= read -r -s -n 1 key; then printf '\n'; return 130; fi
      case $key in
        $'\e'|$'\004') printf '\n'; return 130 ;;
        ''|$'\r') printf '\n'; break ;;
        $'\177'|$'\b') if [[ $answer ]]; then answer=${answer%?}; printf '\b \b'; fi ;;
        [0-9]) if ((${#answer}<9)); then answer+=$key; printf '%s' "$key"; fi ;;
      esac
    done
    answer=${answer:-$default}
    if [[ $answer =~ ^[0-9]+$ ]] && ((10#$answer >= 1 && 10#$answer <= ${#choices[@]})); then
      REPLY=${choices[10#$answer-1]}; return 0
    fi
    printf 'Choose a number from 1 to %d.\n' "${#choices[@]}"
  done
}

# Check before capturing stdout: the caller's three streams must be terminals.
dots::gum_confirm_available() {
  [[ -t 0 && -t 1 && -t 2 && ${TERM:-dumb} != dumb ]] && command -v gum >/dev/null 2>&1
}
# The result is a validated label; Cancel is successful interaction, not an error.
dots::gum_confirm() (
  local header=$1 action=$2
  exec 3>&2
  dots::gum_pick choose "$header" Cancel Cancel "$action" || exit
  case $REPLY in
    Cancel|"$action") printf '%s\n' "$REPLY" ;;
    *) dots::error 'Selector returned an unknown choice.'; exit 1 ;;
  esac
)
