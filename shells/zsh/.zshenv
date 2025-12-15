 #  ╔═╗╔═╗╦ ╦╔═╗╔╗╔╦  ╦
 #  ╔═╝╚═╗╠═╣║╣ ║║║╚╗╔╝
 # o╚═╝╚═╝╩ ╩╚═╝╝╚╝ ╚╝

export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export ZSHDOTS="$SHELLS/zsh"
export ZFUNC="$ZSHDOTS/zfunc"
export DOTSBIN="$DOTS/bin"
export BASHDOT="$SHELLS/bash"
export DOTFILES="$DOTS/configs"
export WINDOTS="$DOTS/windots"
export DOCS="$HOME/Documents"

export STARSHIP_DIR="$DOTFILES/starship"
export STARSHIP_CONFIG="$STARSHIP_DIR/starship.toml"
export STARSHIP_THEMES="$STARSHIP_DIR/themes"
export BAT_CONFIG_DIR="$DOTFILES/bat"
export BAT_CONFIG_PATH="$BAT_CONFIG_DIR/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi"

export GOBIN="$HOME/go/bin"

if [[ -f "$HOME/.pythonrc" ]]; then
    export PYTHONSTARTUP="$HOME/.pythonrc"
fi

fpath+=("$ZFUNC" "${fpath[@]}"); autoload -Uz compinit; compinit

function zource() {
  if [[ -f "$1" ]]; then
    source "$1"
  fi
}

function zieces() {
  zfile="$ZSHDOTS/$1.zsh"
  if [[ -f "$zfile" ]]; then
    source "$zfile"
  fi
}

zource "$HOME/.cargo/env"

export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

export WTTR_PARAMS='u Q F'

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
