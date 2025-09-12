#  ____  ______ _____  _____
# /_  / / __/ // / _ \/ ___/
#  / /__\ \/ _  / , _/ /__
# /___/___/_//_/_/|_|\___/

zieces 'zutil'
zieces 'functions'
zieces 'options'
zieces 'completions'
zieces 'plugins'

addir "$HOME/.local/bin"

extend_path "$HOME/.local/bin"
# extend_path "$HOME/src/nerd-fonts/bin/scripts"
extend_path "$HOME/.local/share/nvim/mason/bin"
prepend_path "$GOBIN"
extend_path "$DOTSBIN"
prepend_path "$HOME/.cargo/bin"

export SHHHH="$DOTS/secrets"
zource "$SHHHH/secrets.sh"
zource "/usr/share/nvm/init-nvm.sh"

if is_droid; then
  zieces 'droid'
fi

zieces 'colors'

if cmd_exists fzf; then
    zieces 'fzf' && eval "$(fzf --zsh)"
fi

if [ -f /etc/wsl.conf ]; then
  zieces 'wsl'
fi

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

eval "$(gh copilot alias -- zsh)"

zource "$HOME/.zshrc.local"
autoload -U +X bashcompinit && bashcompinit
complete -o default -C /data/data/com.termux/files/home/go/bin/ipinfo ipinfo
