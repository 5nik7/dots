alias c='clear'
alias q='exit'

alias cat='bat'

alias path='echo $PATH | tr ":" "\n"'

alias d='yazi'

alias so='source'

alias v='$EDITOR'
alias sv="sudo $EDITOR"

alias ls='ls --color=auto'
alias ll='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes'
alias l='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time'
alias grep='grep --color=auto'

alias lg='lazygit'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."