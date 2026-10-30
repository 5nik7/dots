# Shared Bash/Zsh registration lifecycle; only reads generated names.
_dots_theme_completion_load() {
  local directory=$1 name specification
  local -a next=()
  local -A specifications=()
  typeset -ga _DOTS_THEME_COMPLETION_NAMES
  [[ -f $directory/names && ! -L $directory/names ]] || return 0
  while IFS= read -r name; do
    [[ $name =~ ^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$ ]] && next+=("$name")
  done < "$directory/names"
  if [[ -z ${ZSH_VERSION:-} && ( ${#next[@]} -gt 0 || -n ${_DOTS_THEME_COMPLETION_NAMES[*]-} ) ]]; then
    # One builtin snapshot avoids a subshell for every generated shortcut.
    while IFS= read -r specification; do
      name=${specification##* }
      [[ $name =~ ^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$ ]] || continue
      specifications[$name]=$specification
    done < <(complete -p "${_DOTS_THEME_COMPLETION_NAMES[@]}" "${next[@]}" 2>/dev/null)
  fi
  for name in "${_DOTS_THEME_COMPLETION_NAMES[@]}"; do
    [[ " ${next[*]} " != *" $name "* ]] || continue
    if [[ -n ${ZSH_VERSION:-} ]]; then
      [[ ${_comps[$name]:-} != _dots ]] || compdef -d "$name"
    else
      specification=${specifications[$name]:-}
      [[ $specification != *' -F _dots_complete_bash '* ]] || complete -r "$name"
    fi
  done
  for name in "${next[@]}"; do
    if [[ -n ${ZSH_VERSION:-} ]]; then
      [[ -z ${_comps[$name]:-} || ${_comps[$name]} == _dots ]] || continue
      compdef _dots "$name"
    else
      specification=${specifications[$name]:-}
      [[ ! $specification || $specification == *' -F _dots_complete_bash '* ]] || continue
      complete -F _dots_complete_bash -- "$name"
    fi
  done
  typeset -ga _DOTS_THEME_COMPLETION_NAMES=("${next[@]}")
}
