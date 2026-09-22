# Termux's prefix is not a Unix /usr assumption.
[[ -d "${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions" ]] &&
  fpath=("${TERMUX__PREFIX:-$PREFIX}/share/zsh/site-functions" $fpath)
