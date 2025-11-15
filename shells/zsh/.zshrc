 #  ╔═╗╔═╗╦ ╦╦═╗╔═╗
 #  ╔═╝╚═╗╠═╣╠╦╝║  
 # o╚═╝╚═╝╩ ╩╩╚═╚═╝

zieces 'zutil'
zieces 'functions'
zieces 'options'
zieces 'plugins'

addir "$HOME/.local/bin"

extend_path "$HOME/.local/bin"
# extend_path "$HOME/src/nerd-fonts/bin/scripts"
extend_path "$HOME/.local/share/nvim/mason/bin"
prepend_path "$GOBIN"
extend_path "$DOTSBIN"
prepend_path "$HOME/.cargo/bin"
extend_path "$HOME/.local/share/gem/ruby/3.4.0/bin"

export SHHHH="$DOTS/secrets"
zource "$SHHHH/secrets.sh"
zource "/usr/share/nvm/init-nvm.sh"

is_droid || zieces 'droid'

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
  export DOT_THEME="$(cat "$DOTS"/.theme)"
  export THEME="$(echo "$DOT_THEME" | cut -d '-' -f 1)"
  if [[ "$THEME" == "catppuccin" ]]; then
    export FLAVOR="$(echo "$DOT_THEME" | cut -d '-' -f 2)"
  fi

  export LS_COLORS="$(vivid generate "$DOT_THEME")"

  zieces 'colors'

  zource "${HOME}/.fzf.zsh"
  cmd_exists fzf && zieces 'fzf'
}

set_theme

zieces 'completions'

[ -z ${WSLENV+x} ] || zieces 'wsl'

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
