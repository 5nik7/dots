rlp() {
  . ~/.zshrc
  ok "ZSH RELOADED"
}
alias rl='rlp'

gup() {
  local msg
  if [ "$#" -eq 0 ]; then
    msg='Sync repository tree'
  else
    msg="$@"
  fi
  command git-it publish --all --yes -m "$msg"
}

alias c='clear'
alias q='exit'
alias t='tmux attach || tmux new -s Work'
alias g='git'
alias gcm='git commit -m'
alias gcam='git commit -a -m'
alias gcad='git commit -a --amend'

alias "p:"='echo -e ${PATH//:/\\n}'
alias path='echo $PATH | tr ":" "\n"'
# alias path='echo $PATH | tr ":" "\n" | sed "s|${HOME}|~|"'
alias rmr='rm -fvr'
alias d8="date '+%-I:%M %p'"
alias get='httpGet'
alias h='history'
mkcd() {
  source "${dot[scripts]}/mkcd" "$@"
}

if command -v zoxide &>/dev/null; then
  alias cd="zd"
  zd() {
    if (($# == 0)); then
      builtin cd ~ || return
    elif [[ -d $1 ]]; then
      builtin cd "$1" || return
    else
      if ! z "$@"; then
        echo "Error: Directory not found"
        return 1
      fi

      printf "\U000F17A9 "
      pwd
    fi
  }
fi

alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias ......='cd ../../../../..'
alias .......='cd ../../../../../..'
alias ........='cd ../../../../../../..'

alias "docs"="cd $DOCS"
alias "notes"="cd $NOTES"

alias ".c"="cd $HOME/.config"
alias ".l"="cd $HOME/.local"
alias ".lb"="cd $HOME/.local/bin"
alias ".lsh"="cd $HOME/.local/share"
alias ".lst"="cd $HOME/.local/state"

alias ".d"="cd $dot[root]"
alias ".df"="cd $dot[files]"
alias ".b"="cd $dot[bin]"
alias ".s"="cd $dot[shells]"
alias ".sc"="cd $dot[scripts]"
alias ".sz"="cd $shells[zsh]"
alias ".sb"="cd $shella[bash]"
alias ".sp"="cd $shells[pwsh]"

if command -v eza &>/dev/null; then
  alias l='eza --no-user --no-filesize --no-time --no-permissions --group-directories-first --git --git-repos --icons=auto'
  alias ls='eza -lh --no-user --no-filesize --no-time --no-permissions --group-directories-first --git --git-repos --icons=auto'
  alias lsa='ls -a'
  alias la='lsa'
  alias ll='eza -lh --group-directories-first --git --git-repos --icons=auto'
  alias lla='ll -a'
  alias lt='eza --tree --level=2 --long --icons --git --git-repos --no-filesize --no-time --no-permissions --no-user'
  alias lta='lt -a'
fi

if command -v yazi &>/dev/null; then
  y() {
    local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
    command yazi "$@" --cwd-file="$tmp"
    IFS= read -r -d '' cwd <"$tmp"
    [ "$cwd" != "$PWD" ] && [ -d "$cwd" ] && builtin cd -- "$cwd"
    command rm -f -- "$tmp"
  }
  alias d='y'

  yap() {
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

alias edit='$EDITOR'
alias v='$EDITOR'
alias vi='$EDITOR'
alias vim='$EDITOR'
alias sv="sudo $EDITOR"

if [[ "$TERM" == "xterm-kitty" ]]; then
  alias ff="fzf --preview 'case \$(file --mime-type -b {}) in image/*) kitty icat --clear --transfer-mode=memory --stdin=no --place=\${FZF_PREVIEW_COLUMNS}x\${FZF_PREVIEW_LINES}@0x0 {} ;; *) bat --style=numbers --color=always {} ;; esac'"
else
  alias ff="fzf --preview 'bat --style=numbers --color=always {}'"
fi
alias eff='$EDITOR "$(ff)"'
sff() {
  if [ $# -eq 0 ]; then
    echo "Usage: sff <destination> (e.g. sff host:/tmp/)"
    return 1
  fi
  local file
  file=$(find . -type f -printf '%T@\t%p\n' | sort -rn | cut -f2- | ff) && [ -n "$file" ] && scp "$file" "$1"
}

if [ -d "$HOME/repos" ]; then
  REPOS="$HOME/repos"
  alias repos="cd ${REPOS}"
fi

if [ -d "$HOME/dev" ]; then
  DEV="$HOME/dev"
  alias dev="cd ${DEV}"
fi

if [ -d "$HOME/src" ]; then
  SRCDIR="$HOME/src"
  alias src="cd ${SRCDIR}"
fi

if command -v lazygit &>/dev/null; then
  alias lg='lazygit'
fi

n() { if [ "$#" -eq 0 ]; then command nvim .; else command nvim "$@"; fi; }

# if has glow; then
#   if [[ -f "$DOTFILES/glow/styles/catppuccin-mocha.json" ]]; then
#     alias glow="glow -s $DOTFILES/glow/styles/catppuccin-mocha.json"
#   else
#     alias glow="glow"
#   fi
# fi

# if [[ "$distro" == arch ]]; then
#   alias pacman='sudo pacman'
#   alias upd='sudo pacman -Syu --noconfirm'
#   alias paci='sudo pacman -S'
#   alias pacr='sudo pacman -R'
# fi
#
# if [[ "$distro" == ubuntu || "$distro" == debian ]]; then
#   alias apt='sudo apt'
#   alias upd='sudo apt update && sudo apt upgrade -y'
#   alias apti='sudo apt install'
#   alias aptr='sudo apt remove'
# fi
