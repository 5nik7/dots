# Opt-in PATH history. Only PATH and location metadata are written.
_dots_record_write() {
  printf '%s\0%s\0%s\0%s\0%s\0%s\0' "$1" "${EPOCHREALTIME:-0}" "$2" "$3" "$4" "${_dots_record_owner:-$$}" >&"$_dots_record_fd"
}
_dots_record_tick() {
  [[ ${_dots_record_active:-0} == 1 && ${_dots_record_busy:-0} == 0 ]] || return 0
  [[ ${BASHPID:-${sysparams[pid]:-$$}} == "$_dots_record_owner" ]] || return 0
  _dots_record_busy=1
  if [[ ${PATH-} != "$_dots_record_previous_path" ]]; then
    if (( _dots_record_count >= 10000 || _dots_record_bytes + ${#PATH} > 8000000 )); then
      _dots_record_write limit '' '' ''
      _dots_record_active=0
    else
      _dots_record_write path "$_dots_record_previous_file" "$_dots_record_previous_line" "${PATH-}"
      _dots_record_count=$((_dots_record_count+1))
      _dots_record_bytes=$((_dots_record_bytes+${#PATH}+${#_dots_record_previous_file}+100))
    fi
    _dots_record_previous_path=${PATH-}
  fi
  case $1 in */lib/dots/shell/record.bash) ;;
    *) _dots_record_previous_file=${1:-interactive}; _dots_record_previous_line=$2;;
  esac
  _dots_record_busy=0
  return 0
}
_dots_record_cleanup() {
  [[ ${BASHPID:-${sysparams[pid]:-$$}} == "${_dots_record_owner:-}" ]] || return 0
  [[ -n ${_dots_record_dir:-} && ${_dots_record_dir##*/} == dots-path.* ]] || return 0
  command rm -f -- "$_dots_record_dir/events"
  command rmdir -- "$_dots_record_dir" 2>/dev/null || :
}
_dots_record_start() {
  [[ ${_dots_record_active:-0} != 1 ]] || return 0
  if [[ -n ${ZSH_VERSION:-} ]]; then
    zmodload zsh/datetime; zmodload zsh/parameter; zmodload zsh/system
    if (( $+functions[TRAPDEBUG] )) || [[ ! -o debugbeforecmd ]]; then
      printf '%s\n' 'dots debug record: existing DEBUG instrumentation prevents recording' >&2; return 1
    fi
  elif [[ -n ${_dots_record_existing_debug:-} || -n $(trap -p DEBUG) || $- == *T* || ( -n $(trap -p EXIT) && -z ${_dots_record_owner:-} ) ]]; then
    printf '%s\n' 'dots debug record: existing DEBUG/EXIT instrumentation prevents recording' >&2; return 1
  fi
  _dots_record_owner=${BASHPID:-${sysparams[pid]:-$$}}
  if [[ -z ${_dots_record_dir:-} ]]; then
    _dots_record_dir=$(umask 077; command mktemp -d "${TMPDIR:-/tmp}/dots-path.XXXXXXXXXX") || return 1
  fi
  local _dots_record_mask
  _dots_record_mask=$(umask); umask 077
  exec {_dots_record_fd}>>"$_dots_record_dir/events"
  _dots_record_open=1
  umask "$_dots_record_mask"
  export DOTS_DEBUG_SESSION="$_dots_record_dir/events"
  _dots_record_count=${_dots_record_count:-0}; _dots_record_bytes=${_dots_record_bytes:-0}
  _dots_record_previous_path=${PATH-}; _dots_record_previous_file=interactive; _dots_record_previous_line=0
  _dots_record_write baseline inherited 0 "${PATH-}"
  _dots_record_active=1
  if [[ -n ${ZSH_VERSION:-} ]]; then
    TRAPDEBUG() { _dots_record_tick "${funcfiletrace[1]%:*}" "${funcfiletrace[1]##*:}"; return 0; }
    typeset -ga zshexit_functions
    if (( ! ${zshexit_functions[(Ie)_dots_record_cleanup]} )); then zshexit_functions+=(_dots_record_cleanup); fi
  else
    set -o functrace
    trap '_dots_record_tick "${BASH_SOURCE[0]:-interactive}" "$LINENO"' DEBUG
    trap '_dots_record_cleanup' EXIT
  fi
}
_dots_record_stop() {
  [[ ${_dots_record_open:-0} == 1 ]] || return 0
  _dots_record_tick interactive 0
  _dots_record_write stop '' '' ''
  _dots_record_active=0
  if [[ -n ${ZSH_VERSION:-} ]]; then
    if [[ ${functions[TRAPDEBUG]:-} == *_dots_record_tick* ]]; then unfunction TRAPDEBUG; fi
  elif [[ $(trap -p DEBUG) == *_dots_record_tick* ]]; then
    trap - DEBUG; set +o functrace
  fi
  exec {_dots_record_fd}>&-
  _dots_record_open=0
}
