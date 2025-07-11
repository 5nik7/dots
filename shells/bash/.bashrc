# shellcheck disable=SC2148

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

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

DOTS="$HOME/dots"
export DOTS
SHELLS="$DOTS/shells"
export SHELLS
BASHDOT="$SHELLS/bash"
export BASHDOT
export DOTFILES="$DOTS/configs"
export DOTSBIN="$DOTS/bin"

DOT_THEME="$(cat "$DOTS"/.theme)"
export DOT_THEME

LS_COLORS="$(vivid generate "$DOT_THEME")"
export LS_COLORS

STARSHIP_DIR="$DOTFILES/starship"
export STARSHIP_DIR
STARSHIP_CONFIG="$STARSHIP_DIR/starship.toml"
export STARSHIP_CONFIG
STARSHIP_THEMES="$STARSHIP_DIR/themes"
export STARSHIP_THEMES

export GOBIN="$HOME/go/bin"

function src() {
  if [ -f "$1" ]; then
    # shellcheck disable=SC1090
    source "$1"
  fi
}

src "$BASHDOT/utils.bash"
src "$BASHDOT/functions.bash"

addir "$HOME/.local/bin"

extend_path "$HOME/.local/bin"
extend_path "$HOME/.local/share/nvim/mason/bin"
prepend_path "$GOBIN"
# prepend_path "$DOTSBIN"
prepend_path "$HOME/.cargo/bin"

export SHHHH="$DOTS/secrets"
src "$SHHHH/secrets.sh"
src "/usr/share/nvm/init-nvm.sh"

if cmd_exists fzf; then
  src "$BASHDOT/fzf.bash" && eval "$(fzf --bash)"
fi

if is_droid; then
  src "$BASHDOT/droid.bash"
fi

if [ -f /etc/wsl.conf ]; then
  src "$BASHDOT/wsl.bash"
fi

src "$BASHDOT/aliases.bash"
src "$BASHDOT/colors.bash"

if cmd_exists starship; then
  eval "$(starship init bash)"
fi

if cmd_exists direnv; then
  eval "$(direnv hook bash)"
fi

if cmd_exists zoxide; then
  eval "$(zoxide init bash)"
  alias cd='z'
fi

if cmd_exists batpipe; then
  eval "$(batpipe)"
fi

if cmd_exists batman; then
  eval "$(batman --export-env)"
fi

eval "$(gh copilot alias -- bash)"

set bell-style none
