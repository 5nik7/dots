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

export DOTS="$HOME/dots"
export SHELLS="$DOTS/shells"
export BASHDOT="$SHELLS/bash"
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

if is_installed zoxide; then
  eval "$(zoxide init bash)"
  alias cd='z'
fi

if is_installed starship; then
  eval "$(starship init bash)"
fi

if is_installed perl; then

  extend_path "${HOME}/perl5/bin"

  # PATH="/data/data/com.termux/files/home/perl5/bin${PATH:+:${PATH}}"; export PATH;
  PERL5LIB="/data/data/com.termux/files/home/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"
  export PERL5LIB
  PERL_LOCAL_LIB_ROOT="/data/data/com.termux/files/home/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"
  export PERL_LOCAL_LIB_ROOT
  PERL_MB_OPT="--install_base \"/data/data/com.termux/files/home/perl5\""
  export PERL_MB_OPT
  PERL_MM_OPT="INSTALL_BASE=/data/data/com.termux/files/home/perl5"
  export PERL_MM_OPT
fi
# eval "$(dircolors -b /etc/DIR_COLORS)"

# set bell-style none

# 33 is yellow, 32 is green, 31 is red, 36 is cyan, 34 is blue, 35 is magenta, 37 is white, 30 is black, 39 is default
# export TITLEPREFIX='BASH'
# export PS1='\[\033]0;$TITLEPREFIX: $PWD\007\]\n\[\033[32m\]\u@\h \[\033[34m\]\w\[\033[30m\]`__git_ps1`\[\033[0m\]\n\]\[\033[39m\] '
