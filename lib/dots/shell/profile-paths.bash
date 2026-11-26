# Remove previous Dots profile entries before applying this checkout's layers.
_dots_apply_profile_paths() {
  local part normalized rest=${PATH:-} result='' old skip directory active_shim='' kept_shim=0
  if [[ -n ${MISE_SHELL:-} && -n ${__MISE_ORIG_PATH:-} && -d ${_dots_mise_shims:-} ]]; then
    active_shim=$_dots_mise_shims
  fi
  local -a inherited
  if [[ -n ${ZSH_VERSION:-} ]]; then inherited=("${(@s.:.)_DOTS_INHERITED_PROFILE_PATHS}")
  else IFS=: read -r -a inherited <<< "${_DOTS_INHERITED_PROFILE_PATHS:-}"; fi
  while :; do
    part=${rest%%:*}; normalized=$part; skip=0
    while [[ $normalized == */ && $normalized != / ]]; do normalized=${normalized%/}; done
    if [[ -n $active_shim && $normalized == "$active_shim" ]]; then
      # Full mise activation puts project tools ahead of its fallback shims.
      part=$active_shim; skip=$kept_shim; kept_shim=1
    else
      for old in "$DOTBIN" "$DOTSCRIPTS" "$THEMESBIN" "$DOTS/themes/bin" "${_dots_early_mise_path:-}" "${_DOTS_PROFILE_PATH_APPLIED[@]}" "${_dots_profile_path[@]}" "${inherited[@]}"; do [[ $normalized != "$old" ]] || skip=1; done
    fi
    if [[ -n ${_DOTS_PREVIOUS_CHECKOUT:-} && $_DOTS_PREVIOUS_CHECKOUT != "$DOTS" &&
        ( $part == "$_DOTS_PREVIOUS_CHECKOUT/bin" || $part == "$_DOTS_PREVIOUS_CHECKOUT/scripts" ) ]]; then skip=1; fi
    if (( ! skip )); then
      case :$result: in *":$part:"*) ;; *) result+=${result:+:}$part ;; esac
    fi
    [[ $rest == *:* ]] || break
    rest=${rest#*:}
  done
  PATH=$result
  if [[ -n $active_shim && $kept_shim == 0 ]]; then _dots_insert_active_mise_shims; fi
  result=''
  _DOTS_PROFILE_PATH_APPLIED=()
  for directory in "${_dots_profile_path[@]}"; do
    [[ -d $directory && $directory != "$active_shim" ]] || continue
    case :$result: in *":$directory:"*) continue ;; esac
    _DOTS_PROFILE_PATH_APPLIED+=("$directory")
    result+=${result:+:}$directory
  done
  export DOTS_PROFILE_PATHS=$result
  export PATH=${result:+$result:}$PATH
  if [[ ${dots_options[DOTS_INIT_COMMANDS]} == 1 ]]; then PATH="$THEMESBIN${PATH:+:$PATH}"; fi
  for directory in "$DOTSCRIPTS" "$DOTBIN"; do
    [[ ! -d $directory ]] || PATH="$directory${PATH:+:$PATH}"
  done
  _dots_manual_path
}
_dots_apply_profile_paths
unset _dots_early_mise_path
unset -f _dots_apply_profile_paths
