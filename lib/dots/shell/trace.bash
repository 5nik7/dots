# Explicit diagnostic instrumentation. Raw snapshots use only an anonymous pipe
# consumed in memory by the parent; never send these records to a file or stderr.
_dots_trace_field() {
  printf '%s\0%s\0%s\0%s\0%s\0%s\0' "$1" "${EPOCHREALTIME:-0}" "$2" "$3" "$4" "${BASHPID:-${sysparams[pid]:-$$}}"
}

_dots_trace_snapshot() {
  [[ ${_dots_trace_busy:-0} == 0 && ${DOTS_DEBUG_FD:-} =~ ^[0-9]+$ ]] || return 0
  _dots_trace_busy=1
  local _dots_trace_file=$1 _dots_trace_line=$2 _dots_trace_scope=$3 _dots_trace_name _dots_trace_attrs _dots_trace_frame
  {
    _dots_trace_field state-begin "$_dots_trace_file" "$_dots_trace_line" "$_dots_trace_scope"
    if [[ ${DOTS_DEBUG_DETAIL:-} == deep ]]; then
      if [[ -n ${ZSH_VERSION:-} ]]; then
        for _dots_trace_frame in "${funcfiletrace[@]}"; do _dots_trace_field state-frame "${_dots_trace_frame%:*}" '' ''; done
      else
        for _dots_trace_frame in "${BASH_SOURCE[@]}"; do _dots_trace_field state-frame "$_dots_trace_frame" '' ''; done
      fi
    fi
    if [[ ,${DOTS_DEBUG_CHANGES:-path,variables,functions,aliases,options}, == *,path,* ]]; then
      _dots_trace_field state-path PATH path "${PATH-}"
    fi
    if [[ ,${DOTS_DEBUG_CHANGES:-}, == *,variables,* ]]; then
      printf '%s\0%s\0%s\0%s\0' state-variable-block "${EPOCHREALTIME:-0}" "${private:-0}" "${ZSH_VERSION:+zsh}"
      if [[ -n ${ZSH_VERSION:-} ]]; then typeset -p
      else declare -p; fi
      printf '\0%s\0' "${BASHPID:-${sysparams[pid]:-$$}}"
    fi
    if [[ ,${DOTS_DEBUG_CHANGES:-}, == *,functions,* ]]; then
      printf '%s\0%s\0%s\0%s\0' state-function-block "${EPOCHREALTIME:-0}" '' ''
      if [[ -n ${ZSH_VERSION:-} ]]; then functions
      else declare -f; fi
      printf '\0%s\0' "${BASHPID:-${sysparams[pid]:-$$}}"
    fi
    if [[ ,${DOTS_DEBUG_CHANGES:-}, == *,aliases,* ]]; then
      if [[ -n ${ZSH_VERSION:-} ]]; then
        for _dots_trace_name in ${(k)aliases}; do _dots_trace_field state-aliases "$_dots_trace_name" alias "$aliases[$_dots_trace_name]"; done
        for _dots_trace_name in ${(k)galiases}; do _dots_trace_field state-aliases "$_dots_trace_name" global-alias "$galiases[$_dots_trace_name]"; done
        for _dots_trace_name in ${(k)saliases}; do _dots_trace_field state-aliases "$_dots_trace_name" suffix-alias "$saliases[$_dots_trace_name]"; done
      else
        for _dots_trace_name in "${!BASH_ALIASES[@]}"; do _dots_trace_field state-aliases "$_dots_trace_name" alias "${BASH_ALIASES[$_dots_trace_name]}"; done
      fi
    fi
    if [[ ,${DOTS_DEBUG_CHANGES:-}, == *,options,* ]]; then
      if [[ -n ${ZSH_VERSION:-} ]]; then
        printf '%s\0%s\0%s\0%s\0' state-option-block "${EPOCHREALTIME:-0}" '' ''
        setopt
        printf '\0%s\0' "${sysparams[pid]:-$$}"
      else
        _dots_trace_field state-options SHELLOPTS option "$SHELLOPTS"
        _dots_trace_field state-options BASHOPTS option "$BASHOPTS"
      fi
    fi
    _dots_trace_field state-end '' '' ''
  } 2>/dev/null >&"$DOTS_DEBUG_FD"
  _dots_trace_busy=0
  return 0
}

_dots_trace_debug() {
  [[ ${_dots_trace_busy:-0} == 0 ]] || return 0
  case $2 in */lib/dots/shell/trace.bash|*/lib/dots/shell/debug.bash|*/lib/dots/shell/record.bash) return 0;; esac
  _dots_trace_snapshot "${2:-interactive}" "$3" "$4"
  return 0
}

if [[ -n ${ZSH_VERSION:-} ]]; then
  zmodload zsh/datetime
  zmodload zsh/parameter
  zmodload zsh/system
fi
if [[ ${DOTS_DEBUG_DETAIL:-files} == deep ]]; then
  if [[ -n ${ZSH_VERSION:-} ]]; then
    if (( $+functions[TRAPDEBUG] )); then
      _dots_debug_event coverage 'Deep trace unavailable: existing DEBUG trap' phase
    elif [[ ! -o debugbeforecmd ]]; then
      _dots_debug_event coverage 'Deep trace unavailable: DEBUG_BEFORE_CMD is disabled' phase
    else
      TRAPDEBUG() { _dots_trace_debug "$?" "${funcfiletrace[1]%:*}" "${funcfiletrace[1]##*:}" "${funcstack[2]:-toplevel}"; return 0; }
    fi
  else
    if [[ -n $(trap -p DEBUG) || ( $- == *T* && ${DOTS_DEBUG_FUNCTRACE:-0} != 1 ) ]]; then
      _dots_debug_event coverage 'Deep trace unavailable: existing DEBUG trap or functrace' phase
    else
      set -o functrace
      trap '_dots_trace_debug "$?" "${BASH_SOURCE[0]:-interactive}" "$LINENO" "${FUNCNAME[0]:-toplevel}"' DEBUG
    fi
  fi
fi
