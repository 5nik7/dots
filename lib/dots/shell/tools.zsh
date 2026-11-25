# Keep each profile's Perl root first, including on reload from older shells.
_dots_zsh_perl_environment() {
  local root=$1 name directory value entry
  local -a entries
  for name in PERL5LIB PERL_LOCAL_LIB_ROOT; do
    directory=$root
    [[ $name != PERL5LIB ]] || directory+=/lib/perl5
    entries=("$directory")
    value=${(P)name}
    if [[ -n $value ]]; then
      for entry in "${(@s.:.)value}"; do
        [[ $entry == "$directory" ]] || entries+=("$entry")
      done
    fi
    export "$name=${(j.:.)entries}"
  done
  export PERL_MB_OPT="--install_base \"$root\"" PERL_MM_OPT="INSTALL_BASE=$root"
}

# compinit and the editor are ready at the first prompt. Only the generator
# belonging to the selected first completion runs, inside its native context.
_dots_zsh_generated_completion() {
  local name=${service:-${words[1]:t}} handler REPLY
  case $name in
    uv) _dots_source_generated uv uv generate-shell-completion zsh || return 1 ;;
    uvx) _dots_zsh_generated uvx --generate-shell-completion zsh && eval "$REPLY" || return 1 ;;
    starship) _dots_source_generated starship starship completions zsh || return 1 ;;
    *) return 1 ;;
  esac
  handler=${_comps[$name]:-}
  [[ -n $handler && $handler != _dots_zsh_generated_completion ]] || return 1
  "$handler" "$@"
}
_dots_zsh_pip_completion() {
  local REPLY
  _dots_zsh_generated pip completion --zsh && eval "$REPLY" || return 1
  (( ${+functions[__pip]} )) && __pip "$@"
}
_dots_tool_completions() {
  (( ${+functions[compdef]} )) || return 0
  local name
  for name in uv uvx starship; do
    (( ${+commands[$name]} )) && compdef _dots_zsh_generated_completion "$name"
  done
  (( ${+commands[pip]} )) && compdef _dots_zsh_pip_completion -P 'pip[0-9.]#'
  return 0
}

# Reapply ordinary environment/local files on reload. Stateful activations run
# once when their tool is available; newly installed tools can activate on rl.
# Evaluate at source scope only after the generator succeeds.
_dots_zsh_generated() { REPLY=$("$@") && [[ -n $REPLY ]]; }
typeset -gA _DOTS_TOOL_READY
source "$DOTS/lib/dots/shell/tool-environment.bash"
if has zoxide && [[ -z ${_DOTS_TOOL_READY[zoxide]:-} ]] &&
    _dots_zsh_generated zoxide init zsh && eval "$REPLY"; then
  _DOTS_TOOL_READY[zoxide]=1
fi
if has direnv && [[ -z ${_DOTS_TOOL_READY[direnv]:-} ]] &&
    _dots_zsh_generated direnv hook zsh && eval "$REPLY"; then
  export DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m'
  _DOTS_TOOL_READY[direnv]=1
fi
if has batpipe && [[ -z ${_DOTS_TOOL_READY[batpipe]:-} ]]; then
  if _dots_pager_tool batpipe || { _dots_zsh_generated batpipe && eval "$REPLY"; }; then
    _DOTS_TOOL_READY[batpipe]=1
  fi
fi
# usage can register providers for several commands. Let the completion
# system initialize them just before it looks up the first requested provider.
_dots_zsh_usage_completion() {
  local REPLY
  if _dots_zsh_generated usage g completion-init zsh && eval "$REPLY"; then
    _DOTS_TOOL_READY[usage]=1
    compprefuncs=(${compprefuncs:#_dots_zsh_usage_completion})
  fi
}
if has usage && [[ -z ${_DOTS_TOOL_READY[usage]:-} ]]; then
  (( ${compprefuncs[(Ie)_dots_zsh_usage_completion]} )) || compprefuncs+=(_dots_zsh_usage_completion)
fi
if has batman && [[ -z ${_DOTS_TOOL_READY[batman]:-} ]]; then
  if _dots_pager_tool batman || { _dots_zsh_generated batman --export-env && eval "$REPLY"; }; then
    _DOTS_TOOL_READY[batman]=1
  fi
fi
if so "$HOME/.atuin/bin/env" && has atuin && [[ -z ${_DOTS_TOOL_READY[atuin]:-} ]] &&
    _dots_zsh_generated atuin init zsh && eval "$REPLY"; then
  _DOTS_TOOL_READY[atuin]=1
fi
if has tv && [[ -z ${_DOTS_TOOL_READY[tv]:-} ]] &&
    _dots_zsh_generated tv init zsh && eval "$REPLY"; then
  _DOTS_TOOL_READY[tv]=1
fi
if [[ -n ${BUN_INSTALL:-} && -z ${_DOTS_TOOL_READY[bun]:-} && -r $BUN_INSTALL/_bun ]]; then
  source "$BUN_INSTALL/_bun" && _DOTS_TOOL_READY[bun]=1
fi
if has mise && [[ -z ${_DOTS_TOOL_READY[mise]:-} ]] &&
    _dots_zsh_generated mise activate zsh && eval "$REPLY"; then
  _DOTS_TOOL_READY[mise]=1
fi
_dots_tool_completions
has ipinfo && complete -o default -C "${commands[ipinfo]}" ipinfo
if has starship && [[ -z ${_DOTS_TOOL_READY[starship]:-} ]] &&
    _dots_zsh_generated starship init zsh && eval "$REPLY"; then
  _DOTS_TOOL_READY[starship]=1
fi
so "$HOME/.local/share/leaf/completions/_leaf"
