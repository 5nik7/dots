# Retired Dots Ruby exports and completion paths are not executable tool paths.
_dots_retire_environment() {
  local part normalized rest=${PATH:-} result='' separator='' base skip name record
  local -a retired_roots=("$DOTS" "${DOTS_PROFILE_CHECKOUT:-}" "${_DOTS_PREVIOUS_CHECKOUT:-}" "$HOME/dots")
  unset DOTRUBY RUBYCOMP
  if [[ $rest == */ruby/completion* ]]; then
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
  fi
  for name in DOTS_ENV_HOOKS DOTS_ENV_ORIGINS; do
    typeset -p "$name" >/dev/null 2>&1 || continue
    if [[ -n ${ZSH_VERSION:-} ]]; then rest=${(P)name}; else rest=${!name}; fi
    [[ $rest == *DOTRUBY* || $rest == *RUBYCOMP* ]] || continue
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
export THEME="${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme"
export THEMESBIN="${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes/commands/current/bin"
dot[config]=$_DOTS_CONFIG_PATH dot[state]=${XDG_STATE_HOME:-$HOME/.local/state}/dots
shells[root]=$SHELLS shells[zsh]=$ZSH shells[bash]=$SHELLS/bash shells[pwsh]=$PWSH
_dots_manual_path() {
  local manuals=$HOME/.local/share/man
  if [[ ${DOTS_PLATFORM:-} != windows && -d $manuals && :${MANPATH-}: != *":$manuals:"* ]]; then
    # An empty component asks man to keep its system search path.
    export MANPATH="$manuals:${MANPATH-}"
  fi
}
# If mise already activated a toolchain, its new bins precede the original
# PATH. Put a missing shim back immediately before the first inherited entry.
_dots_insert_active_mise_shims() {
  local rest=$PATH prefix='' entry
  while [[ -n $rest ]]; do
    entry=${rest%%:*}
    if [[ -n $entry && :${__MISE_ORIG_PATH}: == *":$entry:"* &&
          $entry != "$DOTBIN" && $entry != "$DOTSCRIPTS" && $entry != "$THEMESBIN" ]]; then break; fi
    prefix+=$entry:
    if [[ $rest == *:* ]]; then rest=${rest#*:}; else rest=''; fi
  done
  PATH=$prefix$_dots_mise_shims${rest:+:$rest}
}
# An early Zsh may inherit profile bins from its parent. Keep those ahead of
# the shim without activating profile directories that the parent never added.
_dots_early_mise_path_setup() {
  local part normalized rest=${PATH:-} inherited='' other='' separator='' active=0 kept_shim=0
  if [[ -n ${MISE_SHELL:-} && -n ${__MISE_ORIG_PATH:-} ]]; then active=1; fi
  while :; do
    part=${rest%%:*}; normalized=$part
    while [[ $normalized == */ && $normalized != / ]]; do normalized=${normalized%/}; done
    if [[ -n $normalized && $normalized == "${_dots_mise_shims:-}" ]]; then
      if (( active && ! kept_shim )) && [[ -d $normalized ]]; then
        other+=$separator$normalized; separator=:; kept_shim=1
      fi
    elif [[ -n $normalized && $normalized == "${_dots_early_mise_path:-}" ]]; then :
    elif [[ -n $normalized && :${DOTS_PROFILE_PATHS:-}: == *":$normalized:"* ]]; then
      inherited+=${inherited:+:}$part
    else
      other+=$separator$part; separator=:
    fi
    [[ $rest == *:* ]] || break
    rest=${rest#*:}
  done
  _dots_early_mise_path=''
  if [[ -d ${_dots_mise_shims:-} ]]; then
    _dots_early_mise_path=$_dots_mise_shims
    if (( ! active )); then inherited+=${inherited:+:}$_dots_early_mise_path; fi
  fi
  PATH=$other
  if (( active && ! kept_shim )) && [[ -n $_dots_early_mise_path ]]; then _dots_insert_active_mise_shims; fi
  [[ -z $inherited ]] || PATH=$inherited${PATH:+:$PATH}
}
_dots_shell_paths() {
  local directory part rest result='' separator=''
  if [[ ${1:-} == early && ( -d ${_dots_mise_shims:-} || -n ${_dots_early_mise_path:-} ) ]]; then
    _dots_early_mise_path_setup
  fi
  rest=${PATH:-}
  # Remove only retired paths and our optional generated-command path.
  while :; do
    part=${rest%%:*}
    if [[ -n ${_DOTS_PREVIOUS_CHECKOUT:-} && $_DOTS_PREVIOUS_CHECKOUT != "$DOTS" && ( $part == "$_DOTS_PREVIOUS_CHECKOUT/bin" || $part == "$_DOTS_PREVIOUS_CHECKOUT/scripts" ) ]]; then :
    elif [[ $part != "$DOTS/themes/bin" && $part != "$THEMESBIN" && $part != "$DOTBIN" && $part != "$DOTSCRIPTS" ]]; then
      result+=$separator$part; separator=:
    fi
    [[ $rest == *:* ]] || break
    rest=${rest#*:}
  done
  PATH=$result
  if [[ ${dots_options[DOTS_INIT_COMMANDS]} == 1 ]]; then PATH="$THEMESBIN${PATH:+:$PATH}"; fi
  for directory in "$DOTSCRIPTS" "$DOTBIN"; do
    [[ -d $directory ]] || continue
    case :$PATH: in *":$directory:"*) ;; *) PATH="$directory${PATH:+:$PATH}" ;; esac
  done
  export PATH
  _dots_manual_path
}
if [[ ${dots_options[DOTS_INIT_COMMANDS]} == 1 ]]; then
  alias .ln='"$DOTS/bin/dots" link'
elif [[ $(alias .ln 2>/dev/null) == *'"$DOTS/bin/dots" link'* ]]; then
  unalias .ln
fi
