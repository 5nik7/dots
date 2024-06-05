
alias refresh='source ${HOME}/.zshrc'

alias c='clear'
alias q='exit'

alias path='echo $PATH | tr ":" "\n"'
alias open='/mnt/c/Windows/explorer.exe'
alias gc='nix-collect-garbage --delete-old'

alias clip="/mnt/c/Windows/System32/clip.exe"

alias yank='win32yank.exe -i --crlf'
alias paste='win32yank.exe -o --lf'


alias so='source'

alias pkgi='sudo nala install'
alias pkgs='nala search'
alias pkgr='sudo nala remove'

alias v='$EDITOR'
alias sv="sudo $EDITOR"

alias grep='grep --color=auto'

alias npmup='npm install -g npm@latest'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias lg='lazygit'
