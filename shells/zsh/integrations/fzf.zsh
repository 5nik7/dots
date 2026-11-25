# The old final FZF load owned the effective Ctrl-R/Tab bindings. Keep that
# precedence after Atuin/TV initialization, then let fzf-tab wrap completion.
if [[ -z ${_DOTS_FZF_READY:-} ]]; then
  if [[ -r "$HOME/.fzf.zsh" ]]; then
    source "$HOME/.fzf.zsh" && _DOTS_FZF_READY=1
  elif (( $+commands[fzf] )); then
    if _dots_fzf_init=$(fzf --zsh) && [[ -n $_dots_fzf_init ]] &&
        source /dev/stdin <<< "$_dots_fzf_init"; then
      _DOTS_FZF_READY=1
    fi
    unset _dots_fzf_init
  fi
fi
