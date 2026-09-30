# shellcheck disable=SC1090,SC1091,SC2153
# Match Zsh's final FZF binding precedence, in both Readline editing keymaps.
if [[ -z ${_DOTS_BASH_FZF_READY:-} ]]; then
  if [[ -r $HOME/.fzf.bash ]]; then
    source "$HOME/.fzf.bash" && _DOTS_BASH_FZF_READY=1
  elif _dots_bash_generated fzf --bash; then
    eval "$REPLY" && _DOTS_BASH_FZF_READY=1
  fi
fi
