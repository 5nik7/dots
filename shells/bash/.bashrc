# shellcheck disable=SC2148
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

DOTS="$(dirname "$(dirname "$(dirname "$(readlink "$HOME/.bashrc")")")")"
export DOTS
SHELLS="$(dirname "$(dirname "$(readlink "$HOME/.bashrc")")")"
export SHELLS
BASHDOT="$(dirname "$(readlink "$HOME/.bashrc")")"
export BASHDOT
export DOTFILES="$DOTS/configs"
export DOTSBIN="$DOTS/bin"

function src() {
  if [ -f "$1" ]; then
    # shellcheck disable=SC1090
    source "$1"
  fi
}

src "$BASHDOT/utils.bash"
src "$BASHDOT/functions.bash"
src "$BASHDOT/aliases.bash"

if cmd_exists fzf; then
  src "$BASHDOT/fzf.bash"
fi

extend_path "$DOTSBIN"

export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# if cmd_exists nvim; then
# export MANPAGER='nvim +Man! +"set nocul" +"set noshowcmd" +"set noruler" +"set noshowmode" +"set laststatus=0" +"set showtabline=0" +"set nonumber"'
# fi

function is_droid() {
  [[ -d "$HOME/.termux" ]] &>/dev/null
  return $?
}

if is_droid; then
  src "$BASHDOT/droid.bash"
fi

# eval "$(dircolors -b /etc/DIR_COLORS)"

# set bell-style none

# 33 is yellow, 32 is green, 31 is red, 36 is cyan, 34 is blue, 35 is magenta, 37 is white, 30 is black, 39 is default
# export TITLEPREFIX='BASH'
# export PS1='\[\033]0;$TITLEPREFIX: $PWD\007\]\n\[\033[32m\]\u@\h \[\033[34m\]\w\[\033[30m\]`__git_ps1`\[\033[0m\]\n\]\[\033[39m\] '

if cmd_exists starship; then
  eval "$(starship init bash)"
fi

if cmd_exists zoxide; then
  eval "$(zoxide init bash)"
  alias cd='z'
fi
eval "$(gh copilot alias -- bash)"
