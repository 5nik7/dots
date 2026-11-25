# Two stages: completion providers before compinit, widgets after tool bindings.
# Startup can activate installed code. Only a real command or widget may start acquisition.
typeset -gA _DOTS_PLUGINS_LOADED _DOTS_PLUGINS_MISSING _DOTS_PLUGINS_REQUESTED
typeset -ga _DOTS_PLUGIN_WORKERS
typeset -g ZINIT_HOME="${ZINIT_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/zinit/zinit.git}"
_dots_plugin_directory() {
  REPLY=${ZINIT[PLUGINS_DIR]:-${ZINIT[HOME_DIR]:-${XDG_DATA_HOME:-$HOME/.local/share}/zinit}/plugins}
}
_dots_plugin_setup() {
  (( ${+functions[zinit]} )) && return 0
  if [[ ! -r "$ZINIT_HOME/zinit.zsh" ]]; then
    _DOTS_PLUGINS_MISSING[zdharma-continuum/zinit]=1
    return 1
  fi
  if ! source "$ZINIT_HOME/zinit.zsh"; then
    (( ! ${+functions[zinit]} )) || unfunction zinit
    return 1
  fi
  (( ${+functions[zinit]} )) || return 1
  unset '_DOTS_PLUGINS_MISSING[zdharma-continuum/zinit]'
}
_dots_plugin_available() {
  local plugin=$1
  local REPLY
  _dots_plugin_directory
  local id=$plugin ice
  for ice in "${@:2}"; do
    [[ $ice == id-as?* ]] && id=${ice#id-as}
  done
  local directory="$REPLY/${id//\//---}"
  if [[ ${_dots_expected_plugin:-} == "$plugin" && ! -r "$directory/${plugin:t}.plugin.zsh" ]]; then
    _DOTS_PLUGINS_MISSING[$plugin]=1
    return 1
  fi
  [[ -d $directory ]]
}
_dots_load_plugin() {
  local plugin=$1
  [[ -n ${_DOTS_PLUGINS_LOADED[$plugin]:-} ]] && return 0
  _dots_plugin_available "$@" || return 1
  _dots_plugin_setup || return 1
  shift
  if (( $# )); then zinit ice "$@" || return; fi
  zinit light "$plugin" || return
  _DOTS_PLUGINS_LOADED[$plugin]=1
  unset "_DOTS_PLUGINS_MISSING[$plugin]"
}
# Only these declared calls can enqueue a missing plugin. The worker independently
# restricts network requests to the fixed public upstreams.
_dots_default_plugin() {
  local _dots_expected_plugin=$1
  _dots_load_plugin "$@"
}
_dots_completion_plugins() {
  if [[ -n ${_DOTS_PLUGIN_PATHS_READY:-} ]]; then
    fpath=("${_DOTS_PLUGIN_FPATH[@]}" $fpath)
    return 0
  fi
  local -a before=("${fpath[@]}")
  local entry
  _dots_plugin_setup
  _dots_default_plugin zsh-users/zsh-completions || return
  typeset -ga _DOTS_PLUGIN_FPATH=()
  for entry in "${fpath[@]}"; do
    # Preserve only the prepended paths. Providers appended at the end must
    # remain there on reload, rather than gaining precedence.
    ((${before[(Ie)$entry]})) && break
    _DOTS_PLUGIN_FPATH+=("$entry")
  done
  _DOTS_PLUGIN_PATHS_READY=1
}
# Zinit owns this optional executable, independently of its source plugin.
# An installed PATH executable always wins, including native Termux builds.
_dots_deja_binary() {
  (($+commands[deja])) && return 0
  case ${DOTS_PLATFORM:-} in
  linux | wsl) ;;
  termux)
    REPLY='deja is missing; Termux requires a native Go/CGO/Clang build'
    return 1
    ;;
  *)
    REPLY='deja is missing; automatic installation supports Linux/WSL only'
    return 1
    ;;
  esac
  local arch
  case $MACHTYPE in
  x86_64 | amd64) arch=amd64 ;;
  aarch64 | arm64) arch=arm64 ;;
  *)
    REPLY="deja is missing; no Linux release for architecture $MACHTYPE"
    return 1
    ;;
  esac
  _dots_plugin_directory
  if [[ ! -d "$REPLY/dots-deja-binary" ]]; then
    _DOTS_PLUGINS_MISSING[dots-deja-binary]=1
    [[ -r "$REPLY/Giammarco-Ferranti---deja/deja.plugin.zsh" ]] || _DOTS_PLUGINS_MISSING[Giammarco-Ferranti/deja]=1
    REPLY='the Deja release is pending first-use setup'
    return 1
  fi
  _dots_plugin_setup || return 1
  unset '_DOTS_PLUGINS_MISSING[dots-deja-binary]'
  local -a previous_path=("${path[@]}")
  # The installed directory check keeps Zinit on its local activation path.
  # Do not use upstream install.sh: it imports history and edits .zshrc.
  zinit ice lucid from'gh-r' as'command' id-as'dots-deja-binary' \
    bpick"deja_*_linux_${arch}.tar.gz" pick'deja' nocompletions
  if zinit light Giammarco-Ferranti/deja >&2; then
    rehash
    if (($+commands[deja])) && command deja --version >/dev/null 2>&1; then
      return 0
    fi
    REPLY='the Zinit Deja executable is missing or cannot run; check zinit update dots-deja-binary'
  else
    REPLY='Zinit could not install Deja; check network access and Zinit download prerequisites'
  fi
  # A broken release must not remain on PATH after selecting the fallback.
  path=("${previous_path[@]}")
  rehash
  return 1
}
# Select once per shell: switching engines requires a fresh shell, not rl.
_dots_suggestion_plugin() {
  [[ -n ${_DOTS_SUGGESTION_ENGINE:-} ]] && return 0
  local engine=${DOTS_ZSH_SUGGESTIONS:-${dots_options[DOTS_ZSH_SUGGESTIONS]:-deja}}
  case $engine in
  deja)
    local REPLY
    if ! _dots_deja_binary; then
      # Native editing works while the selected release is being acquired.
      [[ -z ${_DOTS_PLUGINS_MISSING[dots-deja-binary]:-} || -n ${_dots_plugin_finished:-} ]] || return 1
      if [[ -z ${_DOTS_DEJA_NOTICE:-} ]]; then
        print -ru2 -- "dots: $REPLY; using zsh-autosuggestions"
        typeset -g _DOTS_DEJA_NOTICE=1
      fi
      engine=autosuggestions
    fi
    ;;
  none)
    _DOTS_SUGGESTION_ENGINE=none
    return 0
    ;;
  autosuggestions) ;;
  *)
    print -ru2 -- 'dots: invalid DOTS_ZSH_SUGGESTIONS; using zsh-autosuggestions'
    engine=autosuggestions
    ;;
  esac
  if [[ $engine == deja ]]; then
    # Leave Tab to fzf-tab; preserve explicit user key/style choices (even empty).
    export DEJA_CYCLE_KEY=${DEJA_CYCLE_KEY-}
    export DEJA_HIGHLIGHT_STYLE=${DEJA_HIGHLIGHT_STYLE-${ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE:-fg=8}}
    _dots_default_plugin Giammarco-Ferranti/deja lucid depth=1 pick'deja.plugin.zsh' || return
  else
    _dots_default_plugin zsh-users/zsh-autosuggestions || return
  fi
  typeset -g _DOTS_SUGGESTION_ENGINE=$engine
}
_dots_widget_plugins() {
  _dots_default_plugin Aloxaf/fzf-tab
  (( ! ${+functions[_dots_completion_install_fzf]} )) || _dots_completion_install_fzf
  _dots_default_plugin zdharma-continuum/fast-syntax-highlighting
  # Route highlighting is useful with theme initialization disabled too.
  if (( ${+FAST_HIGHLIGHT} )); then
    if (( ! ${+functions[_dots_fsh_install_chroma]} )); then
      source "$DOTS/lib/dots/themes/fsh-dots.zsh"
    fi
    _dots_fsh_install_chroma
  fi
  if ((${+functions[_dots_fsh_apply]})); then
    _dots_fsh_apply || :
  fi
  _dots_suggestion_plugin
  _dots_default_plugin zsh-users/zsh-history-substring-search
  if (( $+functions[zinit] )); then
    autoload -Uz _zinit
    ((${+_comps})) && _comps[zinit]=_zinit
  fi
}

_dots_plugins_backend() {
  (( $+functions[_dots_plugins_queue] )) || source "$DOTS/lib/dots/shell/plugins.zsh"
}
_dots_plugins_first_command() {
  add-zsh-hook -d preexec _dots_plugins_first_command
  [[ ${1%% *} == dots-zsh-plugins ]] && return 0
  _dots_plugins_backend && _dots_plugins_queue "${(@k)_DOTS_PLUGINS_MISSING}"
}
_dots_plugins_first_completion() {
  _dots_plugins_backend && _dots_plugins_queue zsh-users/zsh-completions Aloxaf/fzf-tab
  return 0
}
_dots_plugins_history_key() {
  local widget
  for widget in up-line-or-history down-line-or-history vi-up-line-or-history vi-down-line-or-history; do
    [[ ${widgets[$widget]:-} == user:_dots_plugins_history_key ]] && zle -A ".$widget" "$widget"
  done
  _dots_plugins_backend && _dots_plugins_queue zsh-users/zsh-history-substring-search
  zle ".$WIDGET" -- "$@"
}
_dots_plugins_history_bindings() {
  local widget
  for widget in up-line-or-history down-line-or-history vi-up-line-or-history vi-down-line-or-history; do
    [[ ${widgets[$widget]:-} == builtin ]] && zle -N "$widget" _dots_plugins_history_key
  done
}
_dots_plugins_arm() {
  (( $#_DOTS_PLUGINS_MISSING )) && [[ -o interactive && -o zle && -t 0 && -t 1 ]] || return 0
  autoload -Uz add-zsh-hook
  add-zsh-hook preexec _dots_plugins_first_command
  if [[ -n ${_DOTS_PLUGINS_MISSING[zsh-users/zsh-completions]:-}${_DOTS_PLUGINS_MISSING[Aloxaf/fzf-tab]:-} ]]; then
    (( ${compprefuncs[(Ie)_dots_plugins_first_completion]} )) || compprefuncs+=(_dots_plugins_first_completion)
  fi
  if [[ -n ${_DOTS_PLUGINS_MISSING[zsh-users/zsh-history-substring-search]:-} && -z ${_DOTS_PLUGINS_REQUESTED[zsh-users/zsh-history-substring-search]:-} ]]; then
    _dots_plugins_history_bindings
  fi
}
dots-zsh-plugins() {
  _dots_plugins_backend && _dots_plugins_setup_now "$@"
}
