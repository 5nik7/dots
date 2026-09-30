export ZSH="$DOTS/shells/zsh" ZSHCOMP="$DOTS/shells/zsh/completions"
typeset -gA zsh
zsh[root]=$ZSH
zsh[completions]=$ZSHCOMP
source "$DOTS/shells/shared/environment.sh"
# Explicit compatibility order from the former recursive glob. Optional sources
# stay optional. Extra modules are absolute paths, in the owner's chosen order.
local module
for module in androidots/termux.env dot.env ruby/ruby.env \
    secrets/secrets.env shells/shells.env themes/themes.env windots/win.env; do
  if [[ -r "$DOTS/$module" ]]; then
    source "$DOTS/$module"
  fi
done
for module in "${DOTS_ZSH_EXTRA_ENV[@]}"; do
  [[ -r $module ]] && source "$module"
done

source "$DOTS/shells/shared/app-env.sh"
source "$DOTS/shells/shared/paths.sh"
# Native completion paths and public compatibility arrays remain Zsh-owned.
prepath "$ZSHCOMP"
typeset -gU fpath
fpath=("$ZSHCOMP" $fpath)
[[ -r "$ZSH/platforms/${DOTS_PLATFORM:-linux}.zsh" ]] && source "$ZSH/platforms/${DOTS_PLATFORM:-linux}.zsh"
