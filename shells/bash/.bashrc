# shellcheck disable=SC2148

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

set bell-style none

# Shell Options
shopt -s nocaseglob
shopt -s checkwinsize
# History Options
shopt -s histappend
HISTCONTROL=ignoreboth
HISTSIZE=10000
HISTFILESIZE=10000
export HISTCONTROL=$HISTCONTROL${HISTCONTROL+,}ignoredups
export HISTIGNORE=$'[ \t]*:&:[fb]g:exit'

LANG=en_US.UTF-8
export LANG
export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export BASHDOT="$SHELLS/bash"
export DOTFILES="$DOTS/configs"
export DOTSBIN="$DOTS/bin"

export DOT_THEME="$(cat "$DOTS"/.theme)"

export LS_COLORS="$(vivid generate "$DOT_THEME")"

export STARSHIP_DIR="$DOTFILES/starship"
export STARSHIP_CONFIG="$STARSHIP_DIR/starship.toml"
export STARSHIP_THEMES="$STARSHIP_DIR/themes"

export GOBIN="$HOME/go/bin"

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

function so() {
  if [ -f "$1" ]; then
    # shellcheck disable=SC1090
    source "$1"
  fi
}

so "$BASHDOT/utils.bash"
so "$BASHDOT/functions.bash"

addir "$HOME/.local/bin"

extend_path "$HOME/.local/bin"
extend_path "$HOME/.local/share/nvim/mason/bin"
prepend_path "$GOBIN"
prepend_path "$DOTSBIN"
prepend_path "$HOME/.cargo/bin"

export SHHHH="$DOTS/secrets"
so "$SHHHH/secrets.sh"
so "/usr/share/nvm/init-nvm.sh"

if is_droid; then
  so "$BASHDOT/droid.bash"
fi

so "$BASHDOT/colors.bash"

if cmd_exists fzf; then
  so "$BASHDOT/fzf.bash" && eval "$(fzf --bash)"
fi

if [ -f /etc/wsl.conf ]; then
  so "$BASHDOT/wsl.bash"
fi

if cmd_exists zoxide; then
  eval "$(zoxide init bash)"
  alias cd='z'
fi

so "$BASHDOT/aliases.bash"

if cmd_exists starship; then
  eval "$(starship init bash)"
fi

if cmd_exists direnv; then
  eval "$(direnv hook bash)"
fi

if cmd_exists batpipe; then
  eval "$(batpipe)"
fi

if cmd_exists batman; then
  eval "$(batman --export-env)"
fi


complete -C /data/data/com.termux/files/home/go/bin/ipinfo -o default ipinfo
