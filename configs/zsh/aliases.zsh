alias rlp='source ${HOME}/.zshrc'

alias ls='ls --color=auto --group-directories-first'

alias c='clear'
alias q='exit'

alias path='echo $PATH | tr ":" "\n"'
alias gc='nix-collect-garbage --delete-old'

alias clip="/mnt/c/Windows/System32/clip.exe"

alias yy='win32yank.exe -i --crlf'
alias pp='win32yank.exe -o --lf'

alias cat='bat'
alias so='source'

alias edit='$EDITOR'
alias v='$EDITOR'
alias sv="sudo $EDITOR"
alias vsh="$EDITOR ${ZSH}/.zshrc"

alias grep='grep --color=auto'
alias cat='bat'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias lg='lazygit'
