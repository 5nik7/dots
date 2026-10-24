export ZSH="$DOTS/shells/zsh" ZSHCOMP="$DOTS/shells/zsh/completions"
typeset -gA zsh
zsh[root]=$ZSH
zsh[completions]=$ZSHCOMP
source "$DOTS/shells/shared/session.sh"
zsh[local]="$HOME/.zshrc.local"
_dots_hook_source "$DOTS/secrets/secrets.env" private-env 1
for module in "${DOTS_ZSH_EXTRA_ENV[@]}"; do
  _dots_hook_source "$module" private-extra 1
done
# Native completion paths and public compatibility arrays remain Zsh-owned.
typeset -gU fpath
fpath=("$ZSHCOMP" $fpath)
[[ -r "$ZSH/platforms/${DOTS_PLATFORM:-linux}.zsh" ]] && source "$ZSH/platforms/${DOTS_PLATFORM:-linux}.zsh"
