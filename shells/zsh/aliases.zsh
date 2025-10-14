function rlp() {
  source "$HOME/.zshrc" && clear && print_in_yellow "\n ZSH reloaded.\n"
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

alias get='httpGet'

alias h='history'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias ".c"="cd $HOME/.config"
alias ".l"="cd $HOME/.local"

alias ".d"="cd $DOTS"
alias ".f"="cd $DOTFILES"
alias ".s"="cd $SHELLS"
alias ".sz"="cd $ZSHDOTS"
alias ".sb"="cd $SHELLS/bash"
alias ".sp"="cd $SHELLS/powershell"

if cmd_exists pastel; then
  alias paint='pastel paint'
fi

if cmd_exists eza; then
    function l() {
     echo
      eza -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes "$@"
     echo
    }
    function ll() {
      # local timestyle='+󰨲 %m/%d/%y 󰅐 %H:%M'
     echo
      eza -l --group-directories-first --git-repos --git --icons --hyperlink --follow-symlinks --no-quotes --modified -h --no-user "$@"
     echo
    }
  function la() {
     echo
      eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes "$@"
     echo
    }
    function lla() {
      # local timestyle='+󰨲 %m/%d/%y 󰅐 %H:%M'
     echo
      eza -a -l --group-directories-first --git-repos --git --icons --hyperlink --follow-symlinks --no-quotes --modified -h --no-user "$@"
     echo
    }
    alias eza="eza --icons --group-directories-first"
    alias ls="eza"
    alias lsa="ls -a"
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

if [[ -d "$HOME/src" ]]; then
    export SRCDIR="$HOME/src"
    alias src="cd $SRCDIR"
fi


if cmd_exists lazygit; then
  alias lg='lazygit'
fi

if cmd_exists glow; then
  if [[ -f "$DOTFILES/glow/styles/catppuccin-mocha.json" ]]; then
    alias glow="glow -s $DOTFILES/glow/styles/catppuccin-mocha.json"
  else
    alias glow="glow"
  fi
fi
