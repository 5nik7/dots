# The old final FZF load owned the effective Ctrl-R/Tab bindings. Keep that
# precedence after Atuin/TV initialization, then let fzf-tab wrap completion.
if [[ -z ${_DOTS_FZF_READY:-} ]]; then
  if [[ -r "$HOME/.fzf.zsh" ]]; then
    source "$HOME/.fzf.zsh"
    _DOTS_FZF_READY=1
  elif (( $+commands[fzf] )); then
    source <(fzf --zsh)
    _DOTS_FZF_READY=1
  fi
fi
