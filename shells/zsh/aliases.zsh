function rlp() {
  source ~/.zshrc
  ok " ZSH RELOADED"
}
alias rl='rlp'

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

if has git-up; then
  alias gup='git-up'
fi

alias d8="date '+%-I:%M %p'"

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

alias "zd"="fzd"

function mkcd() { mkdir -p "$@" && cd $_; }

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
alias "notes"="cd $NOTES"

alias ".c"="cd $HOME/.config"
alias ".l"="cd $HOME/.local"
alias ".lb"="cd $HOME/.local/bin"
alias ".lsh"="cd $HOME/.local/share"
alias ".lst"="cd $HOME/.local/state"
alias ".v"="cd $HOME/.config/nvim"

alias ".d"="cd $DOTS"
alias ".df"="cd $DOTFILES"
alias ".b"="cd $DOTSBIN"
alias ".s"="cd $SHELLS"
alias ".sc"="cd $DOTSCRIPTS"
alias ".sz"="cd $ZSHDOTS"
alias ".sb"="cd $SHELLS/bash"
alias ".sp"="cd $SHELLS/powershell"

alias ".a"="cd $DROIDOTS"
alias ".af"="cd $DROIDOTS/configs"
alias ".ab"="cd $DROIDOTS/bin"

alias ".w"="cd $WINDOTS"
alias ".wf"="cd $WINDOTS/configs"

if has eza; then
  export eza_opts=("--icons=always" "--color=always" "--group-directories-first")
  alias ls="eza ${eza_opts[*]}"
else
  alias ls="ls --color=always"
fi

alias lsa="ls -a"
alias l="ls -1"
alias ll"ls -la"
alias la="ls -1a"
alias lla="ls -la"

if has yazi; then

  function y() {
    local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
    command yazi "$@" --cwd-file="$tmp"
    IFS= read -r -d '' cwd <"$tmp"
    [ "$cwd" != "$PWD" ] && [ -d "$cwd" ] && builtin cd -- "$cwd"
    rm -f -- "$tmp"
  }
  alias d='y'

  function yap() {
    local yaziProject="$1"
    shift
    if [ -z "$yaziProject" ]; then
      >&2 echo "ERROR: The first argument must be a project"
      return 64
    fi

    # Generate random Yazi client ID (DDS / `ya emit` uses `YAZI_ID`)
    local yaziId=$RANDOM

    # Use Yazi's DDS to run a plugin command after Yazi has started
    # (the nested subshell is only to suppress "Done" output for the job)
    ( (
      sleep 0.1
      YAZI_ID=$yaziId ya emit plugin projects "load $yaziProject"
    ) &)

    # Run Yazi with the generated client ID
    y --client-id $yaziId "$@" || return $?
  }

fi

if has nvim; then
  EDITOR='nvim'
elif has vim; then
  EDITOR='vim'
elif has vi; then
  EDITOR='vi'
elif has code; then
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
  alias src="cd ${SRCDIR}"
fi

has lazygit && alias lg='lazygit'

if has glow; then
  if [[ -f "$DOTFILES/glow/styles/catppuccin-mocha.json" ]]; then
    alias glow="glow -s $DOTFILES/glow/styles/catppuccin-mocha.json"
  else
    alias glow="glow"
  fi
fi
