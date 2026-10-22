# Termux's prefix is not a Unix /usr assumption.
[[ -d "${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions" ]] &&
  fpath=("${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions" $fpath)
# Registered before the single compinit; installation creates the directory.
if [[ -o interactive && -d $DOTS/androidots ]]; then
  typeset -gU fpath
  fpath=("$DOTS/androidots/shells/zsh/completions" $fpath)
fi
