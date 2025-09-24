#  ____  ______ _______  ___   __
# /_  / / __/ // / __/ |/ / | / /
#  / /__\ \/ _  / _//    /| |/ /
# /___/___/_//_/___/_/|_/ |___/

export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export ZSHDOTS="$SHELLS/zsh"
export ZFUNC="$ZSHDOTS/zfunc"
export DOTSBIN="$DOTS/bin"
export BASHDOT="$SHELLS/bash"
export DOTFILES="$DOTS/configs"

export DOT_THEME="$(cat "$DOTS"/.theme)"

export LS_COLORS="$(vivid generate "$DOT_THEME")"

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

fpath+=("$ZFUNC" "${fpath[@]}")

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

# [ -z ${WSLENV+x} ] || export PATH="${PATH:+"$PATH:"}$HOME/bin/win-bash-xclip-xsel"

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
