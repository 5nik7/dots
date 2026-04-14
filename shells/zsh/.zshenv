#  ╔═╗╔═╗╦ ╦╔═╗╔╗╔╦  ╦
#  ╔═╝╚═╗╠═╣║╣ ║║║╚╗╔╝
# o╚═╝╚═╝╩ ╩╚═╝╝╚╝ ╚╝

if [[ -r /etc/os-release ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' /etc/os-release)
  distro="${distro%% *}"
elif [[ -r "$PREFIX/etc/os-release" ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' "$TERMUX__PREFIX/etc/os-release")
  distro="${distro%% *}"
elif [[ -n "$TERMUX_VERSION" ]]; then
  distro='termux'
fi

if [[ -z "$distro" ]]; then
  distro='unknown'
fi

export distro

distro() {
  local distro="${distro:-unknown}"
  echo "$distro"
}

if [[ "$distro" == "termux" ]]; then
  istermux=true
fi

if [[ -r /etc/wsl-distribution.conf ]]; then
  iswsl=true
fi

export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export ZSHDOTS="$SHELLS/zsh"
export ZFUNC="$ZSHDOTS/zfunc"
export DOTSBIN="$DOTS/bin"
export UTIL="$DOTSBIN/util"
export COLORS="$DOTSBIN/colors"
export DOTSCRIPTS="$DOTS/scripts"
export DOTFILES="$DOTS/configs"
export DOTSHHHH="$DOTS/secrets"
export DOTSLOCAL="$DOTS/local"
export DOTSLOCALBIN="$DOTSLOCAL/bin"
export DOTSLOCALSHARE="$DOTSLOCAL/share"
export BASHDOT="$SHELLS/bash"
export WINDOTS="$DOTS/windots"
export DOCS="$HOME/Documents"
export NOTES="$DOCS/notes"

export STARSHIP_DIR="$DOTFILES/starship"
export STARSHIP_CONFIG="$STARSHIP_DIR/starship.toml"
export STARSHIP_THEMES="$STARSHIP_DIR/themes"
export BAT_CONFIG_DIR="$DOTFILES/bat"
export BAT_CONFIG_PATH="$BAT_CONFIG_DIR/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi"
export GOBIN="$HOME/go/bin"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
