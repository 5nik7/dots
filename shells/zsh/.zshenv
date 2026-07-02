#  ╔═╗╔═╗╦ ╦╔═╗╔╗╔╦  ╦
#  ╔═╝╚═╗╠═╣║╣ ║║║╚╗╔╝
# o╚═╝╚═╝╩ ╩╚═╝╝╚╝ ╚╝

prefix="${TERMUX__PREFIX:-$PREFIX}"

if [[ -r /etc/os-release ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' /etc/os-release)
  distro="${distro%% *}"
elif [[ -r "$prefix/etc/os-release" ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' "$prefix/etc/os-release")
  distro="${distro%% *}"
elif [[ -n "${TERMUX_VERSION:-}" ]]; then
  distro='termux'
else
  distro='unknown'
fi

export distro

dotsro() {
  local distro="${distro:-unknown}"
  echo "$distro"
}

if [[ "$distro" == "termux" ]]; then
  istermux=true
fi

if [[ -r /etc/wsl-distribution.conf ]]; then
  iswsl=true
fi

istermux() {
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  if [[ "$istermux" == true ]] &>/dev/null; then
    ((verbose)) && echo "true"
    return 0
  else
    ((verbose)) && echo "false"
    return 1
  fi
}

iswsl() {
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  if [[ "$iswsl" == true ]] &>/dev/null; then
    ((verbose)) && echo "true"
    return 0
  else
    ((verbose)) && echo "false"
    return 1
  fi
}

# set global default env
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

docs="${DOCS:-$HOME/Documents}"
export DOCS="$docs"

notes="${NOTES:-$HOME/Notes}"
export NOTES="$notes"

# set dots env
export DOTS="${DOTS:-$HOME/dots}"
export DOTSBIN="$DOTS/bin"
export UTIL="$DOTSBIN/util"
export COLORS="$DOTSBIN/colors"
export DOTSCRIPTS="$DOTS/scripts"
export DOTSHHHH="$DOTS/secrets"
export DOTSLOCAL="$DOTS/local"
export DOTSLOCALBIN="$DOTSLOCAL/bin"
export DOTSLOCALSHARE="$DOTSLOCAL/share"
export SHELLS="$DOTS/shells"
export ZSHDOTS="$SHELLS/zsh"
export ZFUNC="$ZSHDOTS/zfunc"
export BASHDOT="$SHELLS/bash"
export WINDOTS="$DOTS/windots"
export DOTFILES="$DOTS/configs"

# set config env
export STARSHIP_CONFIG="$DOTFILES/starship/starship.toml"
export STARSHIP_DIR="${STARSHIP_CONFIG%/*}"
export STARSHIP_THEMES="$STARSHIP_DIR/themes"

export BAT_CONFIG_DIR="$DOTFILES/bat"
export BAT_CONFIG_PATH="$BAT_CONFIG_DIR/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi"

export GOBIN="${GOBIN:-$HOME/go/bin}"

if [[ -r "${XDG_DATA_HOME}/bob/env/env.sh" ]]; then
  . "${XDG_DATA_HOME}/bob/env/env.sh"
fi
