# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
*i*) ;;
*) return ;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=10000
HISTFILESIZE=10000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
  debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
xterm-color | *-256color) color_prompt=yes ;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
  if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    # We have color support; assume it's compliant with Ecma-48
    # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
    # a case would tend to support setf rather than setaf.)
    color_prompt=yes
  else
    color_prompt=
  fi
fi

if [ "$color_prompt" = yes ]; then
  PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
  PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm* | rxvt*)
  PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
  ;;
*) ;;
esac

if [ -x /usr/bin/dircolors ]; then
  test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
  alias ls='ls --color=auto'
  alias dir='dir --color=auto'
  alias vdir='vdir --color=auto'

  alias grep='grep --color=auto'
  alias fgrep='fgrep --color=auto'
  alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

export WIN='/mnt/c'
export DOTS="$HOME/dots"
export DOTFILES="$DOTS/configs"
export ZSH="$HOME/.config/zsh"

export SUDO_PROMPT="passwd: "
export STARSHIP_CONFIG="$WIN/Users/njen/dev/dots/configs/starship/starship.toml"
export EDITOR="nvim"
export GOBIN="$HOME/go/bin"
export GOROOT="/usr/local/go"

export BAT_THEME="base16"
export BAT_STYLE="plain"
export BAT_PAGING="never"

function extend_path() {
  [[ -d "$1" ]] || return

  if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
    export PATH="$PATH:$1"
  fi
}

function prepend_path() {
  [[ -d "$1" ]] || return

  if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
    export PATH="$1:$PATH"
  fi
}

function source_file() {
  if [ -f "$1" ]; then
    source "$1"
  fi
}

extend_path "$WIN/Windows"
extend_path "$WIN/Windows/System32"
prepend_path "$WIN/Users/njen/scoop/apps/win32yank/0.1.1"
prepend_path "$HOME/source/wttrbar/target/release"
prepend_path "$HOME/source/eww/target/release"
prepend_path "$WIN/vscode/bin"
prepend_path "$HOME/.local/bin"
prepend_path "$GOBIN"
prepend_path "$GOROOT/bin"
prepend_path "$HOME/.local/share/bob/nvim-bin"
prepend_path "$DOTS/bin"

source_file "$HOME/.bash_aliases"
source_file "$HOME/.bash_functions"

alias rlp='source $HOME/.bashrc && echo "\n ZSH reloaded."'

if which nvim >/dev/null; then
  EDITOR='nvim'
elif which code >/dev/null; then
  EDITOR='code'
elif which vim >/dev/null; then
  EDITOR='vim'
elif which vi >/dev/null; then
  EDITOR='vi'
else
  EDITOR='nano'
fi
export EDITOR
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"
export EDITOR_TERM="$TERMINAL -e $EDITOR"

alias edit='$EDITOR'
alias v='$EDITOR'
alias sv="sudo $EDITOR"

. "$HOME/.cargo/env"

[ -f ~/.fzf.bash ] && source ~/.fzf.bash

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"                   # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion

export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

eval "$(pyenv virtualenv-init -)"

eval "$(starship init bash)"
