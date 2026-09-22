_dots_tool_completions() {
  (( $+commands[uv] )) && _dots_source_generated uv uv generate-shell-completion zsh
  (( $+commands[uvx] )) && _dots_source_generated uvx uvx --generate-shell-completion zsh
  (( $+commands[starship] )) && _dots_source_generated starship starship completions zsh
  return 0
}

# Reapply ordinary environment/local files on reload. Stateful activations run
# once when their tool is available; newly installed tools can activate on rl.
so "$HOME/.cargo/env"
so "$DOTSHHHH/secrets.sh"
PYTHONSTARTUP="$HOME/.pythonrc"
[[ -r $PYTHONSTARTUP ]] && export PYTHONSTARTUP
typeset -gA _DOTS_TOOL_READY
if has zoxide && [[ -z ${_DOTS_TOOL_READY[zoxide]:-} ]]; then
  eval "$(zoxide init zsh)"
  alias cd=z
  _DOTS_TOOL_READY[zoxide]=1
fi
if has direnv && [[ -z ${_DOTS_TOOL_READY[direnv]:-} ]]; then
  eval "$(direnv hook zsh)"
  export DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m'
  _DOTS_TOOL_READY[direnv]=1
fi
if has batpipe && [[ -z ${_DOTS_TOOL_READY[batpipe]:-} ]]; then
  eval "$(batpipe)"
  _DOTS_TOOL_READY[batpipe]=1
fi
if has usage && [[ -z ${_DOTS_TOOL_READY[usage]:-} ]]; then
  source <(usage g completion-init zsh)
  _DOTS_TOOL_READY[usage]=1
fi
if has batman && [[ -z ${_DOTS_TOOL_READY[batman]:-} ]]; then
  eval "$(batman --export-env)"
  _DOTS_TOOL_READY[batman]=1
fi
if so "$HOME/.atuin/bin/env" && has atuin && [[ -z ${_DOTS_TOOL_READY[atuin]:-} ]]; then
  eval "$(atuin init zsh)"
  _DOTS_TOOL_READY[atuin]=1
fi
if has tv && [[ -z ${_DOTS_TOOL_READY[tv]:-} ]]; then
  eval "$(tv init zsh)"
  _DOTS_TOOL_READY[tv]=1
fi
if has mise && [[ -z ${_DOTS_TOOL_READY[mise]:-} ]]; then
  eval "$(mise activate zsh)"
  _DOTS_TOOL_READY[mise]=1
fi
if [[ -d "$HOME/.bun" && -z ${_DOTS_TOOL_READY[bun]:-} ]]; then
  export BUN_INSTALL="$HOME/.bun"
  prepath "$BUN_INSTALL/bin"
  so "$BUN_INSTALL/_bun"
  _DOTS_TOOL_READY[bun]=1
fi
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -d $NVM_DIR && -z ${_DOTS_TOOL_READY[nvm]:-} ]]; then
  so "$NVM_DIR/nvm.sh"
  so "$NVM_DIR/bash_completion"
  _DOTS_TOOL_READY[nvm]=1
fi
RBENV="$HOME/.rbenv/bin/rbenv"
if [[ -x $RBENV && -z ${_DOTS_TOOL_READY[rbenv]:-} ]]; then
  eval "$("$RBENV" init - --no-rehash zsh)"
  _DOTS_TOOL_READY[rbenv]=1
fi
_dots_tool_completions
has ipinfo && complete -o default -C "${commands[ipinfo]}" ipinfo
if has starship && [[ -z ${_DOTS_TOOL_READY[starship]:-} ]]; then
  eval "$(starship init zsh)"
  _DOTS_TOOL_READY[starship]=1
fi
so "$HOME/.local/share/leaf/completions/_leaf"
