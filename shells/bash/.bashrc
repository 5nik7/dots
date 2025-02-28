#!/bin/bash
# [[ "$-" != *i* ]] && return
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

src "${HOME}/.bash_functions"
src "${HOME}/.bash_aliases"

extend_path "$DOTSBIN"

export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

eval "$(dircolors -b /etc/DIR_COLORS)"

if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

if cmd_exists bat; then
   CAT_PREVIEWER='bat --style=numbers --color=always --pager=never'
else
   CAT_PREVIEWER='cat'
fi

FZF_COLORS="bg+:0,\
bg:-1,\
spinner:4,\
hl:12,\
fg:8,\
header:3,\
info:8,\
pointer:13,\
marker:14,\
fg+:13,\
prompt:2,\
hl+:10,\
gutter:-1,\
selected-bg:0,\
separator:0,\
preview-border:8,\
border:8,\
preview-bg:-1,\
preview-label:0,\
label:7,\
query:13,\
input-border:4"

export FZF_DEFAULT_OPTS="--height 60% \
--border sharp \
--layout reverse \
--info right \
--color '$FZF_COLORS' \
--prompt ' ' \
--pointer '┃' \
--marker '│' \
--separator '──' \
--scrollbar '│' \
--preview-window='border-sharp' \
--preview-window='right:65%' \
--preview '$CAT_PREVIEWER {}'"

# shellcheck disable=SC1090
source <(fzf --bash)

set bell-style none

# 33 is yellow, 32 is green, 31 is red, 36 is cyan, 34 is blue, 35 is magenta, 37 is white, 30 is black, 39 is default
# export TITLEPREFIX='BASH'
# export PS1='\[\033]0;$TITLEPREFIX: $PWD\007\]\n\[\033[32m\]\u@\h \[\033[34m\]\w\[\033[30m\]`__git_ps1`\[\033[0m\]\n\]\[\033[39m\] '
