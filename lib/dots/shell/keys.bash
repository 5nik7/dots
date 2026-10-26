# Capture only when dots keys is invoked; ordinary dispatch stays native.
_dots_keys_snapshot() {
  local _dots_keys_map
  if [[ -n ${ZSH_VERSION:-} ]]; then
    local -a _dots_keys_maps
    # shellcheck disable=SC2296
    _dots_keys_maps=("${(@f)$(builtin bindkey -l)}")
    for _dots_keys_map in "${_dots_keys_maps[@]}"; do
      printf 'zsh\0%s\0' "$_dots_keys_map"
      builtin bindkey -L -M "$_dots_keys_map"
      printf '\0'
    done
  else
    for _dots_keys_map in emacs-standard emacs-meta emacs-ctlx vi-insert vi-command; do
      printf 'bash\0%s\0' "$_dots_keys_map"
      builtin bind -m "$_dots_keys_map" -p
      builtin bind -m "$_dots_keys_map" -s
      printf '\0bash\0%s:commands\0' "$_dots_keys_map"
      builtin bind -m "$_dots_keys_map" -X
      printf '\0'
    done
  fi
}
# Preserve an explicitly supplied user function. Re-sourcing our own adapter is
# harmless; no new wrapper layers or prompt hooks accumulate.
if ! typeset -f dots >/dev/null || [[ ${_DOTS_KEYS_WRAPPER:-0} == 1 ]]; then
  function dots {
    local _dots_keys_arg _dots_keys_route='' _dots_keys_capture=1
    for _dots_keys_arg in "$@"; do
      case $_dots_keys_arg in
        --color=*|--icons=*) continue ;;
        *) _dots_keys_route=$_dots_keys_arg; break ;;
      esac
    done
    local _dots_keys_value='' _dots_keys_seen=0
    for _dots_keys_arg in "$@"; do
      if [[ $_dots_keys_seen == 0 ]]; then
        [[ $_dots_keys_arg != keys ]] || _dots_keys_seen=1
        continue
      fi
      if [[ -n $_dots_keys_value ]]; then
        [[ $_dots_keys_value != --source || $_dots_keys_arg != configured ]] || _dots_keys_capture=0
        _dots_keys_value=''; continue
      fi
      case $_dots_keys_arg in
        --query|--mode|--source) _dots_keys_value=$_dots_keys_arg ;;
        --source=configured|--snapshot|--snapshot=*|-h|--help|tmux|nvim|yazi|codex|fzf|kitty|television|powershell) _dots_keys_capture=0 ;;
        zsh) [[ -n ${ZSH_VERSION:-} ]] || _dots_keys_capture=0 ;;
        bash) [[ -z ${ZSH_VERSION:-} ]] || _dots_keys_capture=0 ;;
      esac
    done
    if [[ $_dots_keys_route == keys && $_dots_keys_capture == 1 ]]; then
      _dots_keys_snapshot | DOTS_KEYS_CAPTURE=shell command dots "$@"
    else
      command dots "$@"
    fi
  }
  _DOTS_KEYS_WRAPPER=1
fi
if [[ -n ${ZSH_VERSION:-} ]]; then
  source "$DOTS/lib/dots/shell/keys-ipc.zsh"
fi
