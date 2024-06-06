alias refresh='source ${HOME}/.zshrc'

alias ll='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes'
alias l='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time'

alias c='clear'
alias q='exit'

alias path='echo $PATH | tr ":" "\n"'
alias gc='nix-collect-garbage --delete-old'

alias clip="/mnt/c/Windows/System32/clip.exe"

alias yank='win32yank.exe -i --crlf'
alias paste='win32yank.exe -o --lf'

alias so='source'

alias v='$EDITOR'
alias sv="sudo $EDITOR"
alias vdot="$EDITOR $DOTFILES"
alias bashrc="$EDITOR $BASHRC"
alias aliases="$EDITOR $ALIASES"

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
