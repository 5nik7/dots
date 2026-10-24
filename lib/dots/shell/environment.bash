# Retired Dots Ruby exports and completion paths are not executable tool paths.
_dots_retire_environment() {
  local part normalized rest=${PATH:-} result='' separator='' base skip name record
  local -a retired_roots=("$DOTS" "${DOTS_PROFILE_CHECKOUT:-}" "${_DOTS_PREVIOUS_CHECKOUT:-}" "$HOME/dots")
  unset DOTRUBY RUBYCOMP
  while :; do
    part=${rest%%:*}; normalized=$part; skip=0
    while [[ $normalized == */ && $normalized != / ]]; do normalized=${normalized%/}; done
    for base in "${retired_roots[@]}"; do
      [[ -z $base || $normalized != "${base%/}/ruby/completion" ]] || skip=1
    done
    if (( ! skip )); then result+=$separator$part; separator=:; fi
    [[ $rest == *:* ]] || break
    rest=${rest#*:}
  done
  export PATH=$result
  for name in DOTS_ENV_HOOKS DOTS_ENV_ORIGINS; do
    typeset -p "$name" >/dev/null 2>&1 || continue
    if [[ -n ${ZSH_VERSION:-} ]]; then rest=${(P)name}; else rest=${!name}; fi
    result=''
    while [[ -n $rest ]]; do
      record=${rest%%;*}
      case $record in DOTRUBY:*|RUBYCOMP:*|DOTRUBY\|*|RUBYCOMP\|*|'') ;; *) result+="$record;" ;; esac
      [[ $rest == *';'* ]] || break
      rest=${rest#*;}
    done
    export "$name=$result"
  done
  for name in _DOTS_ENV_APPLIED _DOTS_ENV_ORIGINS _DOTS_HOOK_RECORDS; do
    if typeset -p "$name" >/dev/null 2>&1; then unset "${name}[DOTRUBY]" "${name}[RUBYCOMP]"; fi
  done
}
_dots_retire_environment

# Derived paths and public maps are consumed by the caller.
# shellcheck disable=SC2034,SC2154
typeset -gA dot shells
dot=()
_dots_derive_paths() {
  local variable key relative value
  while IFS=$'\t' read -r variable key relative; do
    value=$DOTS
    [[ $relative == . ]] || value=$DOTS/$relative
    [[ $variable == - ]] || export "$variable=$value"
    [[ $key == - ]] || dot[$key]=$value
  done < "$DOTS/lib/dots/shell/paths.tsv"
}
_dots_derive_paths
unset -f _dots_derive_paths
export THEMESCMD="$DOTS/bin/theme"
export THEMESBIN="${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes/commands/current/bin"
dot[config]=$_DOTS_CONFIG_PATH dot[state]=${XDG_STATE_HOME:-$HOME/.local/state}/dots
shells[root]=$SHELLS shells[zsh]=$ZSH shells[bash]=$SHELLS/bash shells[pwsh]=$PWSH
_dots_shell_paths() {
  local directory part rest=${PATH:-} result='' separator=''
  # Remove only retired paths and our optional generated-command path.
  while :; do
    part=${rest%%:*}
    if [[ -n ${_DOTS_PREVIOUS_CHECKOUT:-} && $_DOTS_PREVIOUS_CHECKOUT != "$DOTS" && ( $part == "$_DOTS_PREVIOUS_CHECKOUT/bin" || $part == "$_DOTS_PREVIOUS_CHECKOUT/scripts" ) ]]; then :
    elif [[ $part != "$DOTS/themes/bin" && $part != "$THEMESBIN" ]]; then
      result+=$separator$part; separator=:
    fi
    [[ $rest == *:* ]] || break
    rest=${rest#*:}
  done
  PATH=$result
  for directory in "$DOTBIN" "$DOTSCRIPTS"; do
    [[ -d $directory ]] || continue
    case :$PATH: in *":$directory:"*) ;; *) PATH="$directory${PATH:+:$PATH}" ;; esac
  done
  if [[ ${dots_options[DOTS_INIT_COMMANDS]} == 1 ]]; then PATH="${PATH:+$PATH:}$THEMESBIN"; fi
  export PATH
}
_dots_shell_paths
unset -f _dots_shell_paths
