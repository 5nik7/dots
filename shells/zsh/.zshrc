#  ╔═╗╔═╗╦ ╦╦═╗╔═╗
#  ╔═╝╚═╗╠═╣╠╦╝║
# o╚═╝╚═╝╩ ╩╩╚═╚═╝

zieces 'zutil'
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

function theme() {
  has_theme() { command vivid generate "$1" &>/dev/null }
  if has_theme "$1"; then
    echo "$1" >! "${DOTS}/.theme"
    set_theme
  else
    echo "'$1' not a theme."
  fi
}

function set_theme() {
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

  zource "$THEMEDIR/colors.zsh"

  zource "${HOME}/.fzf.zsh"
  cmd_exists fzf &&\
    zieces 'fzf'
}

set_theme

zieces 'completions'


if cmd_exists zoxide; then
  eval "$(zoxide init zsh)"
  alias cd='z'
fi

zieces 'aliases'

has starship && eval "$(starship init zsh)"

has direnv && eval "$(direnv hook zsh)" && \
  export DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m'

has batpipe && eval "$(batpipe)"

if cmd_exists batman; then
  eval "$(batman --export-env)"
fi

if cmd_exists ipinfo; then
  autoload -U +X bashcompinit && bashcompinit
  complete -o default -C "$HOME/go/bin/ipinfo" ipinfo
fi

zource "$HOME/.atuin/bin/env"

if cmd_exists atuin; then
  eval "$(atuin init zsh)"
fi

if cmd_exists uv; then
  eval "$(uv generate-shell-completion zsh)"
fi

if cmd_exists uvx; then
  eval "$(uvx --generate-shell-completion zsh)"
fi

if cmd_exists tv; then
  eval "$(tv init zsh)"
fi

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

function istermux() {
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

function iswsl() {
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
  prepend_path "$BUN_INSTALL/bin"
fi

fpath+=("$ZFUNC" "${fpath[@]}"); autoload -Uz compinit; compinit

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
