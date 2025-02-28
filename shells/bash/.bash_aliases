#!/usr/bin/env bash

alias path='echo -e ${PATH//:/\\n}'

alias rm='rm -v'
alias cp='cp -v'
alias mv='mv -v'

alias less='less -r'                          # raw control characters
alias whence='type -a'                        # where, of a sort
alias grep='grep --color'                     # show differences in colour
alias egrep='egrep --color=auto'              # show differences in colour
alias fgrep='fgrep --color=auto'
           # show differences in colour
alias c='clear'
alias q='exit'
alias v='nvim'

alias g='git'

alias path='echo $PATH | tr ":" "\n"'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias ".d"='cd "$DOTS" || return'

if cmd_exists eza; then
      function ll() {
        local timestyle='+󰨲 %m/%d/%y 󰅐 %H:%M'
        linebreak
        eza -a -l --group-directories-first --git-repos --git --icons --hyperlink --follow-symlinks --no-quotes --modified -h --no-user --time-style "$timestyle"
        linebreak
    }
      function lt() {
        local level="$1"
        if [ "$1" = "" ]; then
            level=1
        fi
        linebreak
        eza --group-directories-first --git-repos --git --icons -n --tree -L "$level"
        linebreak
    }

    alias ls='eza --icons'
    alias l='eza -a -l --group-directories-first --git-repos --git --icons --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes'

    # alias ls='ls -hF --color=tty'                 # classify files in colour
    # alias dir='ls --color=auto --format=vertical'
    # alias vdir='ls --color=auto --format=long'
    # alias ll='ls -l'                              # long list
    # alias la='ls -A'                              # all but . and ..
    # alias l='ls -CF'                              #
fi

if cmd_exists yazi; then
    function y() {
      local tmp
      tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
      yazi "$@" --cwd-file="$tmp"
      if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
        builtin cd -- "$cwd" || return
      fi
      rm -f -- "$tmp"
    }
    alias d='y'
fi
