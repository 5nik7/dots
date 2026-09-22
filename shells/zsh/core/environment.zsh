export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
export DOTS="${DOTS:-$HOME/dots}"
export ZSH="$DOTS/shells/zsh" ZSHCOMP="$DOTS/shells/zsh/completions"
typeset -gA zsh
zsh[root]=$ZSH
zsh[completions]=$ZSHCOMP

source "$DOTS/bin/util"
# Keep the historical editor selection point before optional runtime managers.
if has nvim; then EDITOR=nvim
elif has vim; then EDITOR=vim
elif has vi; then EDITOR=vi
elif has code; then EDITOR=code
else EDITOR=nano
fi
export EDITOR VISUAL="$EDITOR" SYSTEMD_EDITOR="$EDITOR"
export EDITOR_TERM="$TERMINAL -e $EDITOR"

# Explicit compatibility order from the former recursive glob. Optional sources
# stay optional. Extra modules are absolute paths, in the owner's chosen order.
local module
for module in androidots/termux.env bin/colors.env dot.env ruby/ruby.env \
    secrets/secrets.env shells/shells.env themes/themes.env windots/win.env; do
  [[ -r "$DOTS/$module" ]] && source "$DOTS/$module"
done
for module in "${DOTS_ZSH_EXTRA_ENV[@]}"; do
  [[ -r $module ]] && source "$module"
done

export DOCS="${DOCS:-$HOME/Documents}" NOTES="${NOTES:-$HOME/Notes}"
export STARSHIP_CONFIG="${dot[configs]}/starship/starship.toml"
export STARSHIP_DIR="${STARSHIP_CONFIG:h}" STARSHIP_THEMES="${STARSHIP_CONFIG:h}/themes"
export BAT_CONFIG_DIR="${dot[configs]}/bat" BAT_CONFIG_PATH="${dot[configs]}/bat/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi" GOBIN="${GOBIN:-$HOME/go/bin}"

[[ -d "$HOME/.fzf/bin" ]] && extpath "$HOME/.fzf/bin"
[[ -r "$XDG_DATA_HOME/bob/env/env.sh" ]] && source "$XDG_DATA_HOME/bob/env/env.sh"
prepath "$GOBIN"
extpath "$HOME/.local/share/gem/ruby/3.4.0/bin"
prepath "$HOME/.cargo/bin"
[[ -d "$HOME/.local/bin" ]] || mkdir -p -- "$HOME/.local/bin"
prepath "$HOME/.local/bin"
prepath "$HOME/bin"
# Completion directories belong to fpath; retain the legacy PATH entries too.
prepath "$ZSHCOMP"
typeset -gU fpath
fpath=("$ZSHCOMP" $fpath)
[[ -r "$ZSH/platforms/${DOTS_PLATFORM:-linux}.zsh" ]] && source "$ZSH/platforms/${DOTS_PLATFORM:-linux}.zsh"
