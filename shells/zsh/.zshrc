#  ╔═╗╔═╗╦ ╦╦═╗╔═╗
#  ╔═╝╚═╗╠═╣╠╦╝║
# o╚═╝╚═╝╩ ╩╩╚═╚═╝

if [ -n "${ZSH_DEBUGRC+1}" ]; then
    zmodload zsh/zprof
fi

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

if [[ -r /etc/os-release ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' /etc/os-release)
  distro="${distro%% *}"
elif [[ -r "$TERMUX__PREFIX/etc/os-release" ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' "$TERMUX__PREFIX/etc/os-release")
  distro="${distro%% *}"
elif [[ -n "$TERMUX_VERSION" ]]; then
  distro='termux'
fi

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

if [ -n "${ZSH_DEBUGRC+1}" ]; then
    zprof
fi

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
