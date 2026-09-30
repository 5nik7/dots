# This hook precedes existing prompt commands and returns their incoming status.
_dots_bash_prompt() {
  local previous_status=$?
  _dots_theme_precmd
  # Append only this session's pending commands, then read other sessions' entries.
  history -a
  history -n
  return "$previous_status"
}
if [[ -z ${_DOTS_BASH_PROMPT_READY:-} ]]; then
  # Handle native scalar and array forms independently.
  # shellcheck disable=SC2178,SC2128
  if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == 'declare -a '* ]]; then
    PROMPT_COMMAND=(_dots_bash_prompt "${PROMPT_COMMAND[@]}")
  else
    PROMPT_COMMAND="_dots_bash_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
  fi
  _DOTS_BASH_PROMPT_READY=1
fi
# Starship owns PS1 after activation. The fallback uses only Bash expansions.
if [[ -z ${_DOTS_BASH_TOOL_READY[starship]:-} ]]; then
  PS1='\[\e[1;32m\]\u@\h\[\e[0m\] \[\e[1;34m\]\w\[\e[0m\] [$?]\n\$ '
fi
