# Remove previous Dots profile entries before applying this checkout's layers.
_dots_apply_profile_paths() {
  local part rest=${PATH:-} result='' old skip directory
  local -a inherited
  if [[ -n ${ZSH_VERSION:-} ]]; then inherited=("${(@s.:.)_DOTS_INHERITED_PROFILE_PATHS}")
  else IFS=: read -r -a inherited <<< "${_DOTS_INHERITED_PROFILE_PATHS:-}"; fi
  while :; do
    part=${rest%%:*}; skip=0
    for old in "${_DOTS_PROFILE_PATH_APPLIED[@]}" "${_dots_profile_path[@]}" "${inherited[@]}"; do [[ $part != "$old" ]] || skip=1; done
    if (( ! skip )); then
      case :$result: in *":$part:"*) ;; *) result+=${result:+:}$part ;; esac
    fi
    [[ $rest == *:* ]] || break
    rest=${rest#*:}
  done
  PATH=$result
  _DOTS_PROFILE_PATH_APPLIED=()
  for directory in "${_dots_profile_path[@]}"; do
    [[ -d $directory ]] || continue
    _DOTS_PROFILE_PATH_APPLIED+=("$directory")
  done
  result=''
  for directory in "${_DOTS_PROFILE_PATH_APPLIED[@]}"; do result+=${result:+:}$directory; done
  export DOTS_PROFILE_PATHS=$result
  export PATH=${result:+$result:}$PATH
}
_dots_apply_profile_paths
unset -f _dots_apply_profile_paths
