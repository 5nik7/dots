#  ╔═╗╔═╗╦ ╦╦═╗╔═╗
 #  ╔═╝╚═╗╠═╣╠╦╝║
 # o╚═╝╚═╝╩ ╩╩╚═╚═╝

zieces 'zutil'
zieces 'functions'
zieces 'options'
zieces 'plugins'

addir "$HOME/.local/bin"
prepend_path "$DOTSBIN"
prepend_path "$GOBIN"
prepend_path "$DOTSBIN"
prepend_path "$DOTSLOCALBIN"
prepend_path "$HOME/.cargo/bin"
extend_path "$HOME/.local/share/gem/ruby/3.4.0/bin"
prepend_path "$HOME/.local/bin"
prepend_path "$HOME/bin"
export SHHHH="$DOTS/secrets"
zource "$SHHHH/secrets.sh"
zource "/usr/share/nvm/init-nvm.sh"



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
  prepend_path "$THEMEBIN"
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

if cmd_exists starship; then
  eval "$(starship init zsh)"
fi

if cmd_exists direnv; then
  eval "$(direnv hook zsh)"
  export DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m'
fi

if cmd_exists batpipe; then
    eval "$(batpipe)"
fi

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

# fpath+=("$ZFUNC" "${fpath[@]}"); autoload -Uz compinit; compinit

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


BUN_INSTALL="$HOME/.bun"
if [[ -d "$BUN_INSTALL" ]]; then
  export BUN_INSTALL="$HOME/.bun"
  [ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"
  prepend_path "$BUN_INSTALL/bin"
fi &>/dev/null


# fpath+=~/.zfunc; autoload -Uz compinit; compinit

# zstyle ':completion:*' menu select

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
