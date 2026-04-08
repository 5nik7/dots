#  ╔═╗╔═╗╦ ╦╦═╗╔═╗
#  ╔═╝╚═╗╠═╣╠╦╝║
# o╚═╝╚═╝╩ ╩╩╚═╚═╝

if [ -n "${ZSH_DEBUGRC+1}" ]; then
    zmodload zsh/zprof
fi

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

[ -f "$COLORS" ] && source "$COLORS"
[ -f "$UTIL" ] && source "$UTIL"

fpath+=("$ZFUNC" "${fpath[@]}")

autoload -U +X bashcompinit && bashcompinit
autoload -Uz compinit; compinit
autoload -U colors; colors

# zieces 'zutil'
zieces 'functions'
zieces 'options'
zieces 'plugins'

addir "$HOME/.local/bin"
prepath "$GOBIN"
extpath "$HOME/.local/share/gem/ruby/3.4.0/bin"
prepath "$DOTSBIN"
prepath "$DOTSLOCALBIN"
prepath "$HOME/.cargo/bin"
prepath "$HOME/.local/bin"
prepath "$HOME/bin"
prepath "$DOTSCRIPTS"
prepath "$DOTSBIN"

so "$HOME/.cargo/env"
so "$DOTSHHHH/secrets.sh"
so "/usr/share/nvm/init-nvm.sh"

[ -f "$HOME/.pythonrc" ] &>/dev/null && export PYTHONSTARTUP="$HOME/.pythonrc"

has_theme() { command vivid generate "$1" &>/dev/null }

theme() {
  if has_theme "$1"; then
    echo "$1" >! "${DOTS}/.theme"
    set_theme
  else
    echo "'$1' not a theme."
  fi
}

set_theme() {
  export THEMESROOT="$DOTS/themes"
  export THEMEBIN="$THEMESROOT/bin"
  prepath "$THEMEBIN"
  export DOT_THEME="$(cat "$DOTS"/.theme)"
  export THEME="$(echo "$DOT_THEME" | cut -d '-' -f 1)"
  if [[ "$THEME" == "catppuccin" ]]; then
    export FLAVOR="$(echo "$DOT_THEME" | cut -d '-' -f 2)"
  fi
  export THEMEDIR="$THEMESROOT/$THEME"

  export LS_COLORS="$(vivid generate "$DOT_THEME")"

  so "$THEMEDIR/colors.zsh"
  so "${HOME}/.fzf.zsh"

  has fzf &&\
    zieces 'fzf'
}

set_theme

zieces 'completions'

has zoxide && {
  eval "$(zoxide init zsh)"
  alias cd='z'
}

zieces 'aliases'

has starship && eval "$(starship init zsh)"

has direnv && {
  eval "$(direnv hook zsh)"
  export DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m' }

has batpipe && eval "$(batpipe)"

has batman && eval "$(batman --export-env)"

has ipinfo && { complete -o default -C "$HOME/go/bin/ipinfo" ipinfo }

so "$HOME/.atuin/bin/env" && has atuin && eval "$(atuin init zsh)"

has uv && eval "$(uv generate-shell-completion zsh)"

has uvx && eval "$(uvx --generate-shell-completion zsh)"

has tv && eval "$(tv init zsh)"

if [[ "$distro" == "termux" ]]; then
  istermux=true
  zieces 'droid'
fi

istermux() {
  if [[ "$istermux" == true ]] &> /dev/null; then
    echo "true"
    return 0
  else
    echo "false"
    return 1
  fi
}

alias distro='echo $distro'

if [[ -r /etc/wsl-distribution.conf ]]; then
  iswsl=true
  zieces 'wsl'
fi

iswsl() {
  if [[ "$iswsl" == true ]] &> /dev/null; then
    echo "true"
    return 0
  else
    echo "false"
    return 1
  fi
}

if checkdir "$HOME/.bun"; then
  export BUN_INSTALL="$HOME/.bun"
  [ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"
  prepath "$BUN_INSTALL/bin"
fi

# bun completions
[ -s "/home/njen/.bun/_bun" ] && source "/home/njen/.bun/_bun"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

if [ -n "${ZSH_DEBUGRC+1}" ]; then
    zprof
fi

