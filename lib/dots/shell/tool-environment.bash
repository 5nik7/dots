# Shared Bash/Zsh environment needed by child processes from the first command.
if [[ -n ${CARGO_HOME:-} && -r $CARGO_HOME/env ]]; then source "$CARGO_HOME/env"
elif [[ -r $HOME/.cargo/env ]]; then source "$HOME/.cargo/env"; fi
if [[ -n ${ZSH_VERSION:-} && -r ${DOTSHHHH:-$DOTS/secrets}/secrets.sh ]]; then
  _dots_hook_source "${DOTSHHHH:-$DOTS/secrets}/secrets.sh" private-tools 1
fi
[[ ! -r $HOME/.pythonrc || -n ${PYTHONSTARTUP:-} ]] || export PYTHONSTARTUP="$HOME/.pythonrc"
if [[ -d ${BUN_INSTALL:-$HOME/.bun} ]]; then
  export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
  prepath "$BUN_INSTALL/bin"
fi
# NVM selects a Node version and updates PATH for shebangs and external
# scripts as well as the nvm shell function. Preserve that initial selection.
if [[ -r ${NVM_DIR:-$HOME/.nvm}/nvm.sh && -z ${_DOTS_TOOL_READY[nvm]:-} ]]; then
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  if source "$NVM_DIR/nvm.sh"; then
    [[ ! -r $NVM_DIR/bash_completion ]] || source "$NVM_DIR/bash_completion"
    _DOTS_TOOL_READY[nvm]=1
  fi
fi

# The bundled batpipe/batman only export these pager settings. Avoid their
# process-tree inspection on every fresh interactive shell. Paths are quoted
# for the shell which less/man invoke later.
_dots_pager_tool() {
  local name=$1 resolved
  if [[ -n ${ZSH_VERSION:-} ]]; then resolved=${commands[$name]:-}
  else resolved=$(type -P "$name"); fi
  [[ -n $resolved && $resolved -ef $DOTS/scripts/$name ]] || return 1
  printf -v resolved '%q' "$resolved"
  case $name in
    batpipe)
      export LESSOPEN="|$resolved %s" BATPIPE=color
      case " ${LESS:-} " in *' -R '*) ;; *) export LESS="${LESS:+$LESS }-R" ;; esac
      unset LESSCLOSE ;;
    batman)
      export MANPAGER="env BATMAN_IS_BEING_MANPAGER=yes bash $resolved" MANROFFOPT=-c ;;
  esac
}
