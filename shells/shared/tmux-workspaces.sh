# Bash/Zsh notify managed workspaces only after a pane's directory changes.
# shellcheck shell=bash
[[ $- == *i* && -n ${TMUX:-} && -n ${TMUX_PANE:-} ]] || return 0
_dots_workspace_prompt() {
  local previous_status=$? socket=${TMUX%,*,*}
  if [[ ${_DOTS_WORKSPACE_LAST_CWD-} != "$PWD" || ${_DOTS_WORKSPACE_LAST_PANE-} != "$TMUX_PANE" ]]; then
    _DOTS_WORKSPACE_LAST_CWD=$PWD _DOTS_WORKSPACE_LAST_PANE=$TMUX_PANE
    # Keep directory changes responsive. The bounded worker re-observes the
    # current pane under the server lock; rapid notifications converge on PWD.
    # A short-lived subshell keeps this worker out of the caller's job table.
    (command python3 -B "$DOTS/lib/dots/tmux_workspaces.py" reconcile \
      --socket "$socket" --pane "$TMUX_PANE" >/dev/null 2>&1 &)
  fi
  return "$previous_status"
}
if [[ -n ${ZSH_VERSION:-} ]]; then
  autoload -Uz add-zsh-hook
  add-zsh-hook -d precmd _dots_workspace_prompt 2>/dev/null
  add-zsh-hook precmd _dots_workspace_prompt
elif [[ -z ${_DOTS_WORKSPACE_PROMPT_READY:-} ]]; then
  if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == 'declare -a '* ]]; then
    PROMPT_COMMAND=(_dots_workspace_prompt "${PROMPT_COMMAND[@]}")
  else
    # This branch is scalar; Bash's array form is handled above.
    # shellcheck disable=SC2178,SC2128
    PROMPT_COMMAND="_dots_workspace_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
  fi
  _DOTS_WORKSPACE_PROMPT_READY=1
fi
true
