#    _____  _____ __  ______  ______
#   /__  / / ___// / / / __ \/ ____/
#     / /  \__ \/ /_/ / /_/ / /
#  _ / /_____/ / __  / _, _/ /___
# (_)____/____/_/ /_/_/ |_|\____/

export LANG=en_US.UTF-8
export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export ZSHDOTS="$SHELLS/zsh"
export ZFUNC=~/.zfunc
export DOTSBIN="$DOTS/bin"
export BASHDOT="$SHELLS/bash"
export DOTFILES="$DOTS/configs"

export DOT_THEME="$(cat "$DOTS"/.theme)"

export LS_COLORS="$(vivid generate "$DOT_THEME")"

export GOBIN="$HOME/go/bin"

fpath+=("$ZFUNC" "${fpath[@]}")

function zource() {
  if [ -f "$1" ]; then
    source "$1"
  fi
}

function zieces() {
  zfile="$ZSHDOTS/$1.zsh"
  if [ -f "$zfile" ]; then
    source "$zfile"
  fi
}

zieces 'zutil'
zieces 'functions'
zieces 'colors'
zieces 'options'
zieces 'completions'
zieces 'plugins'

addir "$HOME/.local/bin"

extend_path "$HOME/.local/bin"
# extend_path "$HOME/src/nerd-fonts/bin/scripts"
extend_path "$HOME/.local/share/nvim/mason/bin"
prepend_path "$GOBIN"
prepend_path "$DOTSBIN"
prepend_path "$HOME/.cargo/bin"

export SHHHH="$DOTS/secrets"
zource "$SHHHH/secrets.sh"
zource "/usr/share/nvm/init-nvm.sh"

if cmd_exists fzf; then
  zieces 'fzf' && eval "$(fzf --zsh)"
fi

if is_droid; then
  zieces 'droid'
fi

if [ -f /etc/wsl.conf ]; then
  zieces 'wsl'
fi

zieces 'aliases'

if cmd_exists starship; then
  eval "$(starship init zsh)"
fi

if cmd_exists direnv; then
  eval "$(direnv hook zsh)"
fi

if cmd_exists zoxide; then
  eval "$(zoxide init zsh)"
  alias cd='z'
fi

if cmd_exists batpipe; then
    eval "$(batpipe)"
fi

if cmd_exists batman; then
  eval "$(batman --export-env)"
fi

eval "$(gh copilot alias -- zsh)"
