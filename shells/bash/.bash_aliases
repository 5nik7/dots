alias rlp='source $HOME/.bashrc'

alias ls='ls --color=auto --group-directories-first'

alias c='clear'
alias q='exit'

alias path='echo $PATH | tr ":" "\n"'

alias yy='win32yank.exe -i --crlf'
alias pp='win32yank.exe -o --lf'

alias so='source'

alias v='$EDITOR'
alias sv='sudo $EDITOR'
alias vsh='$EDITOR $DOTFILES/bash/.bashrc'

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

function yy() {
    local tmp
    tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
    yazi "$@" --cwd-file="$tmp"
    if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
        cd -- "$cwd" || exit
    fi
    rm -f -- "$tmp"
}
alias d='yy'

function dd {
    if [ -z "$1" ]; then
        explorer .
    else
        explorer "$1"
    fi
}

alias ll='echo -e "" && eza -la --git --git-repos --icons --group-directories-first --no-quotes && echo -e ""'
alias l='echo -e "" && eza -la --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time && echo -e ""'

# function cd() {
#     builtin cd "$@" && l
# }

function weather {
    if [[ "$1" == "help" ]]; then
        curl "wttr.in/:help"
    else
        curl "wttr.in/Yakima?uFQ$1"
    fi
}

bat() {
    local index
    local args=("$@")
    for index in $(seq 0 ${#args[@]}); do
        case "${args[index]}" in
        -*) continue ;;
        *) [ -e "${args[index]}" ] && args[index]="$(cygpath --windows "${args[index]}")" ;;
        esac
    done
    command bat "${args[@]}"
}
