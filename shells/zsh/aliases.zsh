command_exists() {
  command -v "$@" &> /dev/null
}

function y() {
	local tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
	yazi "$@" --cwd-file="$tmp"
	if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
		builtin cd -- "$cwd"
	fi
	rm -f -- "$tmp"
}
alias d='y'
alias pbcopy="/mnt/c/Windows/System32/clip.exe"
alias pbpaste="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -command 'Get-Clipboard'"

# alias python="python3"
# alias py="python3"

alias c='clear'
alias q='exit'

alias path='echo $PATH | tr ":" "\n"'

alias so='source'

alias grep='grep --color=auto'

command_exists fzf && command_exists bat && alias preview="fzf --preview 'bat --color \"always\" {}'"

alias cat='bat'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias lg='lazygit'

function dd {
    if [ -z "$1" ]; then
        explorer.exe .
    else
        explorer.exe "$1"
    fi
}

alias ll='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes && echo -e ""'
alias l='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time && echo -e ""'

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
