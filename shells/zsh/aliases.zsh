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

alias grep='grep --color=auto'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias lg='lazygit'
alias clock='tty-clock -c -f %d-%m-%Y'
