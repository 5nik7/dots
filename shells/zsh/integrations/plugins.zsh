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
# Zinit owns this optional executable, independently of its source plugin.
# An installed PATH executable always wins, including native Termux builds.
_dots_deja_binary() {
  (( $+commands[deja] )) && return 0
  case ${DOTS_PLATFORM:-} in
    linux|wsl) ;;
    termux)
      REPLY='deja is missing; Termux requires a native Go/CGO/Clang build'
      return 1 ;;
    *) REPLY='deja is missing; automatic installation supports Linux/WSL only'; return 1 ;;
  esac
  local arch
  case $MACHTYPE in
    x86_64|amd64) arch=amd64 ;;
    aarch64|arm64) arch=arm64 ;;
    *) REPLY="deja is missing; no Linux release for architecture $MACHTYPE"; return 1 ;;
  esac
  local -a previous_path=("${path[@]}")
  # Cached releases load locally. Only an absent Zinit installation downloads.
  # Do not use upstream install.sh: it imports history and edits .zshrc.
  zinit ice lucid from'gh-r' as'command' id-as'dots-deja-binary' \
    bpick"deja_*_linux_${arch}.tar.gz" pick'deja' nocompletions
  if zinit light Giammarco-Ferranti/deja >&2; then
    rehash
    if (( $+commands[deja] )) && command deja --version >/dev/null 2>&1; then
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
        print -ru2 -- "dots: $REPLY; using zsh-autosuggestions"
        engine=autosuggestions
      fi
      ;;
    none) _DOTS_SUGGESTION_ENGINE=none; return 0 ;;
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
    zinit ice lucid depth=1 pick'deja.plugin.zsh'
    _dots_load_plugin Giammarco-Ferranti/deja || return
  else
    _dots_load_plugin zsh-users/zsh-autosuggestions || return
  fi
  typeset -g _DOTS_SUGGESTION_ENGINE=$engine
}
_dots_widget_plugins() {
  _dots_plugin_setup || return
  _dots_load_plugin Aloxaf/fzf-tab
  _dots_load_plugin zdharma-continuum/fast-syntax-highlighting
  if (( ${+functions[_dots_fsh_theme]} )); then
    _dots_fsh_theme || print -ru2 -- 'dots theme: could not load FSH theme; keeping previous syntax colors'
  fi
  _dots_suggestion_plugin
  _dots_load_plugin zsh-users/zsh-history-substring-search
  autoload -Uz _zinit
  (( ${+_comps} )) && _comps[zinit]=_zinit
}
