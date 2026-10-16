# Public colors and options are shared with the sourced adapters.
# shellcheck disable=SC2034,SC2154
# Dots integration only. No personal aliases, plugins, prompt or tool activation.
source "$DOTS/lib/dots/shell/config.bash"
_dots_config_load || return
source "$DOTS/lib/dots/shell/environment.bash"
source "$DOTS/lib/dots/shell/platform.bash"
[[ $- == *i* ]] || return 0
[[ ${rst-} == $'\e[0m' ]] || typeset -g rst=$'\e[0m'
[[ ${RST-} == $'\e[0m' ]] || typeset -g RST=$'\e[0m'
if [[ ${dots_options[DOTS_INIT_COLORS]} == 0 ]]; then
  for _dots_name in "${_DOTS_THEME_COLOR_NAMES[@]-}"; do [[ ! $_dots_name ]] || unset "$_dots_name"; done
  _DOTS_THEME_COLOR_NAMES=()
  unset _dots_name
fi
if [[ ${dots_options[DOTS_INIT_THEME]} == 1 ]]; then
  source "$DOTS/lib/dots/themes/shell.bash"
  set_theme 2>/dev/null || printf 'dots: could not initialize theme; previous colors retained\n' >&2
fi
_dots_shell_completion_off() {
  local name specification
  local -a names=(dots theme)
  if [[ -r ${THEMESBIN%/bin}/names ]]; then
    while IFS= read -r name; do names+=("$name"); done < "${THEMESBIN%/bin}/names"
  fi
  for name in "${names[@]}"; do
    if [[ -n ${ZSH_VERSION:-} ]]; then
      if (( ${+functions[compdef]} )) && [[ ${_comps[$name]:-} == _dots ]]; then compdef -d "$name"; fi
    else
      specification=$(complete -p "$name" 2>/dev/null) || continue
      [[ $specification != *' -F _dots_complete_bash '* ]] || complete -r "$name"
    fi
  done
  _DOTS_COMPLETION_READY='' _DOTS_THEME_COMMANDS_TOKEN=''
}
[[ ${dots_options[DOTS_INIT_COMPLETION]} == 1 ]] || _dots_shell_completion_off
_dots_shell_prompt() {
  local previous_status=$?
  if [[ ${dots_options[DOTS_INIT_COMPLETION]} == 1 ]]; then
    if [[ -n ${ZSH_VERSION:-} ]]; then
      if (( ${+functions[compdef]} )) && [[ -z ${_DOTS_COMPLETION_READY:-} ]]; then
        source "$DOTS/lib/dots/completion/zsh" && _DOTS_COMPLETION_READY=1
      fi
    fi
    if typeset -f _dots_theme_commands >/dev/null; then _dots_theme_commands; fi
  fi
  if [[ ${dots_options[DOTS_INIT_THEME]} == 1 && ${dots_options[DOTS_THEME_AUTO_UPDATE]} == 1 ]]; then
    _dots_theme_precmd
  fi
  return "$previous_status"
}
if [[ -n ${ZSH_VERSION:-} ]]; then
  autoload -Uz add-zsh-hook
  add-zsh-hook -d precmd _dots_theme_precmd 2>/dev/null
  add-zsh-hook precmd _dots_shell_prompt
else
  if [[ ${dots_options[DOTS_INIT_COMPLETION]} == 1 ]]; then source "$DOTS/lib/dots/completion/bash"; fi
  if [[ -z ${_DOTS_SHELL_PROMPT_READY:-} ]]; then
    # Native scalar and array prompt forms are intentionally separate.
    # shellcheck disable=SC2178,SC2128
    if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == 'declare -a '* ]]; then
      PROMPT_COMMAND=(_dots_shell_prompt "${PROMPT_COMMAND[@]}")
    else PROMPT_COMMAND="_dots_shell_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"; fi
    _DOTS_SHELL_PROMPT_READY=1
  fi
fi
true
