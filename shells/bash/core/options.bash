# Native Readline/history equivalents. Do not share history formats with Zsh.
set -o vi
set -o noclobber
shopt -s histappend histverify checkwinsize hostcomplete extglob globstar cdspell dirspell autocd cmdhist
HISTFILE=${HISTFILE:-$HOME/.bash_history}
HISTSIZE=100000
HISTFILESIZE=100000
HISTCONTROL=ignoreboth:erasedups
HISTIGNORE='&:ls:pwd:[bf]g:ssh *:exit'
bind 'set bell-style none'
bind 'set completion-ignore-case on'
bind 'set show-all-if-ambiguous on'
# Readline 7+ supports mode strings, including nonprinting cursor sequences.
if (( BASH_VERSINFO[0] >= 5 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 4) )); then
  bind 'set show-mode-in-prompt on'
  bind 'set vi-ins-mode-string "\1\e[5 q\2"'
  bind 'set vi-cmd-mode-string "\1\e[1 q\2"'
fi
[[ ! -t 0 ]] || stty stop ''
