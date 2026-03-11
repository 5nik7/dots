 #  ╔═╗╔═╗╦ ╦╔═╗╔╗╔╦  ╦
 #  ╔═╝╚═╗╠═╣║╣ ║║║╚╗╔╝
 # o╚═╝╚═╝╩ ╩╚═╝╝╚╝ ╚╝

esc=$'\033'
c_reset="${esc}[0m"
c_red="${esc}[31m"
c_green="${esc}[32m"
c_yellow="${esc}[33m"
c_blue="${esc}[34m"
c_black="${esc}[30m"

export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export ZSHDOTS="$SHELLS/zsh"
export ZFUNC="$HOME/.zfunc"
export DOTSBIN="$DOTS/bin"
export DOTSLOCAL="$DOTS/local"
export DOTSLOCALBIN="$DOTSLOCAL/bin"
export DOTSLOCALSHARE="$DOTSLOCAL/share"
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

[ -f "$HOME/.pythonrc" ] &>/dev/null && export PYTHONSTARTUP="$HOME/.pythonrc"

fpath+=("$ZFUNC" "${fpath[@]}"); autoload -Uz compinit; compinit

function zource() {
  local files
  filea="$@"
  for file in "${files[@]}"; do
    if [[ -f "$file" ]] &>/dev/null;then
      source "$file"
    fi
  done
}

function zieces() {
  [ -f "$ZSHDOTS/$1.zsh" ] &>/dev/null
  source "$ZSHDOTS/$1.zsh"
}

# function zieces() {
#   local zfiles
#   ZIECES=()
#   [ -z "$ZSHDOTS" ] &>/dev/null && buggin "ZSHDOTS = $ZSHDOTS"
#   zfiles="$@"
#   for file in "${zfiles[@]}";do
#     ZIECE="$ZSHDOTS/$file.zsh"
#     [ -f "$ZIECE" ] &>/dev/null
#     source "$file"
#     ZIECES+="$ZIECE"
#   done
#   export ZIECES
# }

zource "$HOME/.cargo/env"

export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
