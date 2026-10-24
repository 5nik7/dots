# Opt-in metadata events only. Never log commands, arguments or environment values.
_dots_debug_event() {
  local result=$? event=$1 label=$2 kind=${3:-module} event_status=${4:-} now debug_pid=${BASHPID:-$$}
  [[ ${DOTS_DEBUG_FD:-} =~ ^[0-9]+$ ]] || return "$result"
  if [[ -n ${ZSH_VERSION:-} ]]; then
    [[ -n ${EPOCHREALTIME:-} ]] || zmodload zsh/datetime 2>/dev/null
    zmodload -e zsh/system || zmodload zsh/system 2>/dev/null
    debug_pid=${sysparams[pid]:-$$}
  fi
  if [[ $kind == inlined || ( $kind == source && $label == */* && $label != /* ) ]]; then label="$DOTS/$label"; fi
  now=${EPOCHREALTIME:-${SECONDS:-0}}
  printf '%s\0%s\0%s\0%s\0%s\0%s\0' "$event" "$now" "$label" "$kind" "$event_status" "$debug_pid" 2>/dev/null 1>&"$DOTS_DEBUG_FD" || :
  return "$result"
}

# Ordinary startup pays only a native no-op call at each compiled boundary.
if [[ ! ${DOTS_DEBUG_FD:-} =~ ^[0-9]+$ ]]; then
  _dots_debug_event() { return $?; }
fi
