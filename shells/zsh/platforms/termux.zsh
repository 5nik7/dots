# Termux's prefix is not a Unix /usr assumption.
[[ -d "${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions" ]] &&
  fpath=("${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions" $fpath)
# Registered before the single compinit; installation creates the directory.
if [[ -o interactive && -d $DOTS/profiles/termux ]]; then
  typeset -gU fpath
  fpath=("$DOTS/profiles/termux/shells/zsh/completions" $fpath)
fi
