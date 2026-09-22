# Two stages: completion providers before compinit, widgets after tool bindings.
_dots_plugin_setup() {
  (( ${+functions[zinit]} )) && return 0
  typeset -g ZINIT_HOME="${ZINIT_HOME:-${XDG_DATA_HOME}/zinit/zinit.git}"
  if [[ ! -r "$ZINIT_HOME/zinit.zsh" ]]; then
    # Preserve the existing first-run bootstrap, but fail cleanly offline.
    (( $+commands[git] )) || return 1
    mkdir -p -- "${ZINIT_HOME:h}" || return 1
    command git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME" || return 1
  fi
  source "$ZINIT_HOME/zinit.zsh"
}
_dots_load_plugin() {
  local plugin=$1
  [[ -n ${_DOTS_PLUGINS_LOADED[$plugin]:-} ]] && return 0
  zinit light "$plugin" || return
  _DOTS_PLUGINS_LOADED[$plugin]=1
}
typeset -gA _DOTS_PLUGINS_LOADED
_dots_completion_plugins() {
  if [[ -n ${_DOTS_PLUGIN_PATHS_READY:-} ]]; then
    fpath=("${_DOTS_PLUGIN_FPATH[@]}" $fpath)
    return 0
  fi
  local -a before=("${fpath[@]}")
  local entry
  _dots_plugin_setup || return
  _dots_load_plugin zsh-users/zsh-completions
  typeset -ga _DOTS_PLUGIN_FPATH=()
  for entry in "${fpath[@]}"; do
    # Preserve only the prepended paths. Providers appended at the end must
    # remain there on reload, rather than gaining precedence.
    (( ${before[(Ie)$entry]} )) && break
    _DOTS_PLUGIN_FPATH+=("$entry")
  done
  _DOTS_PLUGIN_PATHS_READY=1
}
_dots_widget_plugins() {
  _dots_plugin_setup || return
  _dots_load_plugin Aloxaf/fzf-tab
  _dots_load_plugin zdharma-continuum/fast-syntax-highlighting
  _dots_load_plugin zsh-users/zsh-autosuggestions
  _dots_load_plugin zsh-users/zsh-history-substring-search
  autoload -Uz _zinit
  (( ${+_comps} )) && _comps[zinit]=_zinit
}
