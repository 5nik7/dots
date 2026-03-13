function rlp() {
  exec zsh;
  clear;
  print_in_yellow "\n ZSH reloaded.\n"
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

alias "p:"='echo -e ${PATH//:/\\n}'

alias path='echo $PATH | tr ":" "\n"'
# alias path='echo $PATH | tr ":" "\n" | sed "s|${HOME}|~|"'

alias rmr='rm -fvr'

# function mkcd() {
#   mkdir -p "$1" && cd "$1"
# }

mkcd() { mkdir -p "$@" && cd $_; }

alias get='httpGet'

alias h='history'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias "docs"="cd $DOCS"
alias "notes"="cd $DOCS/Notes"

alias ".c"="cd $HOME/.config"
alias ".l"="cd $HOME/.local"
alias ".lb"="cd $HOME/.local/bin"
alias ".lsh"="cd $HOME/.local/share"
alias ".lst"="cd $HOME/.local/state"
alias ".v"="cd $HOME/.config/nvim"

alias ".d"="cd $DOTS"
alias ".f"="cd $DOTFILES"
alias ".b"="cd $DOTSBIN"
alias ".s"="cd $SHELLS"
alias ".sz"="cd $ZSHDOTS"
alias ".sb"="cd $SHELLS/bash"
alias ".sp"="cd $SHELLS/powershell"

alias ".a"="cd $DROIDOTS"
alias ".af"="cd $DROIDOTS/configs"
alias ".ab"="cd $DROIDOTS/bin"

alias ".w"="cd $WINDOTS"
alias ".wf"="cd $WINDOTS/configs"

export eza_opts=("--color=always" "--icons" "--group-directories-first")

if cmd_exists eza; then
  function lscmd() {
    local opts=()
    if [ -n "$eza_opts" ]; then
    for opt in "${eza_opts[@]}";do
      opts+="$opt"
    done
    fi
  eza $opts $@
}
alias ls="lscmd"
else
  alias ls="ls --color=always"
fi

alias lsa="ls -a"
alias l="ls -1"
alias ll"ls -l"
alias la="ls -1a"
alias lla="ls -la"

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
  src() {
    cd "$SRCDIR/$(fd --type directory --base-directory=$SRCDIR/ --max-depth=2 --color=always | fzf --ansi)"
  }
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

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
