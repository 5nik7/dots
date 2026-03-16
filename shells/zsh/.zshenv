#  ╔═╗╔═╗╦ ╦╔═╗╔╗╔╦  ╦
#  ╔═╝╚═╗╠═╣║╣ ║║║╚╗╔╝
# o╚═╝╚═╝╩ ╩╚═╝╝╚╝ ╚╝

export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export ZSHDOTS="$SHELLS/zsh"
export ZFUNC="$ZSHDOTS/zfunc"
export DOTSBIN="$DOTS/bin"
export DOTSCRIPTS="$DOTS/scripts"
export DOTFILES="$DOTS/configs"
export DOTSHHHH="$DOTS/secrets"
export DOTSLOCAL="$DOTS/local"
export DOTSLOCALBIN="$DOTSLOCAL/bin"
export DOTSLOCALSHARE="$DOTSLOCAL/share"
export BASHDOT="$SHELLS/bash"
export WINDOTS="$DOTS/windots"
export DOCS="$HOME/Documents"

export STARSHIP_DIR="$DOTFILES/starship"
export STARSHIP_CONFIG="$STARSHIP_DIR/starship.toml"
export STARSHIP_THEMES="$STARSHIP_DIR/themes"
export BAT_CONFIG_DIR="$DOTFILES/bat"
export BAT_CONFIG_PATH="$BAT_CONFIG_DIR/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi"

export GOBIN="$HOME/go/bin"

export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

fpath+=("$ZFUNC" "${fpath[@]}")

function zource() {
  if [[ -f "$1" ]]; then
      source "$1"
  fi
}

function zieces() {
  if [[ -f "$ZSHDOTS/$1.zsh" ]]; then
    source "$ZSHDOTS/$1.zsh"
  fi
}

function extpath() {
	if [[ -d "$1" ]]; then
    if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
      export PATH="$PATH:$1"
    fi
  fi 2> /dev/null
}

function prepath() {
	if [[ -d "$1" ]]; then
    if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
		  export PATH="$1:$PATH"
	  fi
  fi 2> /dev/null
}

# fpath+=("$ZFUNC" "${fpath[@]}"); autoload -Uz compinit; compinit

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
