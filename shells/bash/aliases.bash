function rlp() {
  source "$HOME/.bashrc" && clear && print_in_yellow "\n BASH reloaded.\n"
}
alias rl='rlp'

if [[ -r /etc/os-release ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' /etc/os-release)
  distro="${distro%% *}"
fi

if [[ "$distro" == arch ]]; then
  alias pacman='sudo pacman'
  alias upd='sudo pacman -Syu --noconfirm'
  alias paci='sudo pacman -S'
  alias pacr='sudo pacman -R'
fi

if [[ "$distro" == ubuntu || "$distro" == debian ]]; then
  alias apt='sudo apt'
  alias upd='sudo apt update && sudo apt upgrade -y'
  alias apti='sudo apt install'
  alias aptr='sudo apt remove'
fi

alias c='clear'
alias q='exit'

alias g='git'

alias path='echo $PATH | tr ":" "\n"'

alias rmr='rm -fvr'

function mkcd() {
  mkdir -p "$1" && cd "$1"
}

alias h='history'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias ".d"="cd $DOTS"

if cmd_exists eza; then
  function l() {
    linebreak
    eza -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes
    linebreak
  }
  function ll() {
    # local timestyle='+󰨲 %m/%d/%y 󰅐 %H:%M'
    linebreak
    eza -l --group-directories-first --git-repos --git --icons --hyperlink --follow-symlinks --no-quotes --modified -h --no-user
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
  function la() {
    linebreak
    eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes
    linebreak
  }
  function lla() {
    # local timestyle='+󰨲 %m/%d/%y 󰅐 %H:%M'
    linebreak
    eza -a -l --group-directories-first --git-repos --git --icons --hyperlink --follow-symlinks --no-quotes --modified -h --no-user
    linebreak
  }
  function lta() {
    local level="$1"
    if [ "$1" = "" ]; then
      level=1
    fi
    linebreak
    eza -a --group-directories-first --git-repos --git --icons -n --tree -L "$level"
    linebreak
  }
  alias eza='eza --icons'
  alias ls='eza'
  alias lsa='ls -a'
fi

if cmd_exists yazi; then
  function y() {
    local tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
    yazi "$@" --cwd-file="$tmp"
    if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
      builtin cd -- "$cwd"
    fi
    rm -f -- "$tmp"
  }
  alias d='y'
fi

if cmd_exists nvim; then
  EDITOR='nvim'
elif cmd_exists vim; then
  EDITOR='vim'
elif cmd_exists vi; then
  EDITOR='vi'
elif cmd_exists code; then
  EDITOR='code'
else
  EDITOR='nano'
fi

export EDITOR
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"
export EDITOR_TERM="$TERMINAL -e $EDITOR"

alias edit='$EDITOR'
alias e='$EDITOR'
alias v='$EDITOR'
alias vi='$EDITOR'
alias vim='$EDITOR'
alias sv="sudo $EDITOR"

if [[ -d "$HOME/dev" ]]; then
  export DEV="$HOME/dev"
  alias dev="cd $DEV"
fi

if cmd_exists lazygit; then
  alias lg='lazygit'
fi
