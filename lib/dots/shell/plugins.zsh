# On-demand acquisition and safe-prompt activation for the Zsh adapter.
_dots_plugins_acquire() {
  local mode=$1 REPLY
  shift
  _dots_plugin_directory
  command python3 -B "$DOTS/lib/dots/zsh_plugins.py" "--completions" "${ZINIT[COMPLETIONS_DIR]:-${ZINIT[HOME_DIR]:-${XDG_DATA_HOME:-$HOME/.local/share}/zinit}/completions}" \
    "$mode" "$ZINIT_HOME" "$REPLY" \
    "${XDG_STATE_HOME:-$HOME/.local/state}/dots/zsh/plugins" "${DOTS_PLATFORM:-}" "$MACHTYPE" "$@"
}
_dots_plugins_queue() {
  (( $+commands[python3] && $+commands[timeout] )) || return 0
  local name
  local -a names=()
  for name in zdharma-continuum/zinit "$@"; do
    [[ -n ${_DOTS_PLUGINS_MISSING[$name]:-} && -z ${_DOTS_PLUGINS_REQUESTED[$name]:-} ]] || continue
    if [[ $name == dots-deja-binary ]]; then
      (( $+commands[curl] )) || continue
    else
      (( $+commands[git] )) || continue
    fi
    names+=("$name")
    _DOTS_PLUGINS_REQUESTED[$name]=1
  done
  (( $#names )) || return 0
  _dots_plugins_acquire auto "${names[@]}" </dev/null >/dev/null 2>&1 &!
  _DOTS_PLUGIN_WORKERS+=($!)
  add-zsh-hook precmd _dots_plugins_activate
}
_dots_plugins_refresh() {
  local had_completion=${_DOTS_PLUGIN_PATHS_READY:-}
  local had_fsh=${_DOTS_PLUGINS_LOADED[zdharma-continuum/fast-syntax-highlighting]:-}
  _dots_completion_plugins
  if [[ -z $had_completion && -n ${_DOTS_PLUGIN_PATHS_READY:-} ]]; then
    # Extend the live catalog without reinitializing unrelated widgets,
    # custom compdefs, higher-priority fpath entries or shell bindings.
    local REPLY file name
    local -a header
    _dots_plugin_directory
    local providers="$REPLY/zsh-users---zsh-completions/src"
    autoload -Uz compaudit
    if [[ -d $providers ]] && compaudit "$providers" >/dev/null 2>&1; then
      for file in "$providers"/_*(N-.); do
        name=${file:t}
        [[ $name != *.zwc && -z ${functions[$name]+x} ]] || continue
        IFS=$' \t' read -rA header < "$file"
        case $header[1] in
          ('#compdef') compdef -na "$name" "${(@)header[2,-1]}";;
          ('#autoload') autoload -Uz "$name";;
        esac
      done
    fi
  fi
  (( ! $+functions[_dots_termux_editor_plugins] )) || _dots_termux_editor_plugins
  _dots_widget_plugins
  if [[ -z $had_fsh && -n ${_DOTS_PLUGINS_LOADED[zdharma-continuum/fast-syntax-highlighting]:-} &&
        -r ${ZINIT[COMPLETIONS_DIR]:-}/_fast-theme ]] && (( $+functions[compdef] )); then
    compdef -na _fast-theme fast-theme
  fi
  (( ! $+functions[_dots_zsh_keys_apply] )) || _dots_zsh_keys_apply
}
_dots_plugins_activate() {
  local worker
  for worker in "${_DOTS_PLUGIN_WORKERS[@]}"; do
    kill -0 "$worker" 2>/dev/null && return 0
  done
  _DOTS_PLUGIN_WORKERS=()
  add-zsh-hook -d precmd _dots_plugins_activate
  local _dots_plugin_finished=${_DOTS_PLUGINS_REQUESTED[dots-deja-binary]:-}
  _dots_plugins_refresh
  # A failed Linux release selects the fallback only after the first batch.
  if [[ -n $_dots_plugin_finished && -n ${_DOTS_PLUGINS_MISSING[zsh-users/zsh-autosuggestions]:-} ]]; then
    _dots_plugins_queue zsh-users/zsh-autosuggestions
  fi
  return 0
}
_dots_plugins_setup_now() {
  local mode=${1:-setup}
  if (( $# > 1 )) || [[ $mode != setup && $mode != retry ]]; then
    print -ru2 -- 'usage: dots-zsh-plugins [setup|retry]'
    return 2
  fi
  (( $#_DOTS_PLUGINS_MISSING )) || { print -r -- 'Dots Zsh plugins are ready.'; return 0; }
  local -a names=("${(@k)_DOTS_PLUGINS_MISSING}")
  _dots_plugins_acquire "$mode" "${names[@]}"
  local result=$? _dots_plugin_finished=1
  _dots_plugins_refresh
  return "$result"
}
