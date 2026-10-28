# Native environment assignment and provenance; values never enter cache files.
typeset -gA _DOTS_ENV_APPLIED _DOTS_ENV_ORIGINS _DOTS_HOOK_BEFORE _DOTS_HOOK_RECORDS
_dots_env_default() {
  local key=$1 value=$2 origin=${3:-default} current
  if [[ -n ${ZSH_VERSION:-} ]]; then current=${(P)key}; else current=${!key-}; fi
  # batpipe can supply -R before this shell starts. Keep those flags and add
  # mouse support once, before prompt options that may consume the remainder.
  local mouse_pattern='(^|[[:space:]])--(mouse|MOUSE)([=[:space:]]|$)'
  if [[ $key == LESS && $value == --mouse && -n $current && ! $current =~ $mouse_pattern ]]; then
    current="--mouse $current"
    export "LESS=$current"
  fi
  if [[ -n $current && ( -z ${_DOTS_ENV_APPLIED[$key]+yes} || $current != "${_DOTS_ENV_APPLIED[$key]}" ) ]]; then
    _DOTS_ENV_ORIGINS[$key]=environment
  else
    export "$key=$value"
    _DOTS_ENV_APPLIED[$key]=$value _DOTS_ENV_ORIGINS[$key]=$origin
  fi
}
_dots_hook_snapshot() {
  local key
  _DOTS_HOOK_BEFORE=()
  if [[ -n ${ZSH_VERSION:-} ]]; then
    for key in ${(k)parameters}; do
      [[ ${parameters[$key]} == *export* ]] && _DOTS_HOOK_BEFORE[$key]=${(P)key}
    done
  else
    while IFS= read -r key; do _DOTS_HOOK_BEFORE[$key]=${!key}; done < <(compgen -e)
  fi
}
_dots_hook_record() {
  local origin=$1 private=${2:-0} key value changed='' names=''
  local -a keys
  if [[ -n ${ZSH_VERSION:-} ]]; then
    for key in ${(k)parameters}; do [[ ${parameters[$key]} == *export* ]] && keys+=("$key"); done
  else
    while IFS= read -r key; do keys+=("$key"); done < <(compgen -e)
  fi
  for key in "${keys[@]}"; do
    [[ $key == _DOTS_* || $key == DOTS_ENV_* || $key == SHLVL || $key == _ ]] && continue
    if [[ -n ${ZSH_VERSION:-} ]]; then value=${(P)key}; else value=${!key-}; fi
    if [[ -z ${_DOTS_HOOK_BEFORE[$key]+yes} || $value != "${_DOTS_HOOK_BEFORE[$key]}" ]]; then
      changed+="${key}:${origin}:${private}:set;"
    fi
    unset "_DOTS_HOOK_BEFORE[$key]"
  done
  if [[ -n ${ZSH_VERSION:-} ]]; then keys=("${(@k)_DOTS_HOOK_BEFORE}"); else keys=("${!_DOTS_HOOK_BEFORE[@]}"); fi
  for key in "${keys[@]}"; do
    [[ $key == _DOTS_* || $key == DOTS_ENV_* || $key == _ ]] || changed+="${key}:${origin}:${private}:unset;"
  done
  # Only names, fixed provenance labels and sensitivity cross process boundaries.
  local entry rest=$changed
  while [[ -n $rest ]]; do
    entry=${rest%%;*}; rest=${rest#*;}
    key=${entry%%:*}
    if [[ ${_DOTS_HOOK_RECORDS[$key]:-} == *:1:* ]]; then
      entry=${entry/:0:/:1:}
    fi
    _DOTS_HOOK_RECORDS[$key]=$entry
  done
  if [[ -n ${ZSH_VERSION:-} ]]; then keys=("${(@k)_DOTS_HOOK_RECORDS}"); else keys=("${!_DOTS_HOOK_RECORDS[@]}"); fi
  DOTS_ENV_HOOKS=''
  for key in "${keys[@]}"; do DOTS_ENV_HOOKS+="${_DOTS_HOOK_RECORDS[$key]};"; done
  export DOTS_ENV_HOOKS
  _DOTS_HOOK_BEFORE=()
}
_dots_hook_source() {
  local file=$1 origin=$2 private=${3:-0} result
  local -A _DOTS_HOOK_BEFORE
  [[ -r $file ]] || return 0
  _dots_hook_snapshot
  if typeset -f _dots_debug_event >/dev/null; then _dots_debug_event begin "$file" source; fi
  source "$file"; result=$?
  if typeset -f _dots_debug_event >/dev/null; then _dots_debug_event end "$file" source "$result"; fi
  _dots_hook_record "$origin" "$private"
  return "$result"
}
_dots_env_publish_origins() {
  local key
  local -a keys
  if [[ -n ${ZSH_VERSION:-} ]]; then keys=("${(@k)_DOTS_ENV_ORIGINS}"); else keys=("${!_DOTS_ENV_ORIGINS[@]}"); fi
  DOTS_ENV_ORIGINS=''
  for key in "${keys[@]}"; do DOTS_ENV_ORIGINS+="${key}|${_DOTS_ENV_ORIGINS[$key]};"; done
  export DOTS_ENV_ORIGINS
}
