#     ____  ______ _____  _____
#    /_  / / __/ // / _ \/ ___/
#   _ / /__\ \/ _  / , _/ /__
#  (_)___/___/_//_/_/|_|\___/

ZINIT_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
 [ ! -d $ZINIT_HOME ] && mkdir -p "$(dirname $ZINIT_HOME)"
 [ ! -d $ZINIT_HOME/.git ] && git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
 source "${ZINIT_HOME}/zinit.zsh"

zinit load zdharma-continuum/fast-syntax-highlighting
zinit load zsh-users/zsh-autosuggestions
zinit load zsh-users/zsh-completions
zinit load zsh-users/zsh-history-substring-search

 autoload -Uz _zinit
 (( ${+_comps} )) && _comps[zinit]=_zinit

# Use emacs keybindings even if our EDITOR is set to vi
bindkey -v

# export LANG=en_US.UTF-8
# export LC_ALL=en_US.UTF-8

case $TERM in
iterm | \
    linux-truecolor | \
    screen-truecolor | \
    tmux-truecolor | \
    xterm-truecolor) export COLORTERM=truecolor ;;
vte*) ;;
esac
export COLORTERM=truecolor

export WIN='/mnt/c'
export DOTS="$HOME/dots"
export DOTFILES="$DOTS/configs"
export ZSH="$HOME/.config/zsh"
export TERMINAL='kitty'
export BROWSER='firefox'

export SUDO_PROMPT="passwd: "
# export STARSHIP_CONFIG="$WIN/Users/njen/dev/dots/configs/starship/starship.toml"
export STARSHIP_CONFIG="$DOTFILES/starship/starship.toml"
export EDITOR="nvim"
export GOBIN="$HOME/go/bin"
export GOROOT="/usr/local/go"

export BAT_THEME="base16"
export BAT_STYLE="plain"
export BAT_PAGING="never"

export MANPAGER="nvim +Man!"
export PAGER="nvim +Man!"

HISTSIZE=10000
SAVEHIST=10000
HISTFILE=~/.zsh_history

zle_highlight=('paste:none')

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


setopt_if_exists() {
  if [[ "${options[$1]+1}" ]]; then
    setopt "$1"
  fi
}

setopt_if_exists no_auto_cd
setopt_if_exists cd_silent
setopt_if_exists no_case_glob
setopt_if_exists extended_glob

setopt_if_exists hist_ignore_all_dups
setopt_if_exists hist_find_no_dups
setopt_if_exists hist_reduce_blanks
setopt_if_exists hist_ignore_space
setopt_if_exists hist_verify
setopt_if_exists no_inc_append_history
setopt_if_exists no_inc_append_history_time
setopt_if_exists share_history

setopt_if_exists no_clobber
setopt_if_exists correct # commands
setopt_if_exists correct_all # all arguments
setopt_if_exists interactive_comments
setopt_if_exists no_list_beep

unset setopt_if_exists

unsetopt beep

extend_path "$WIN/Windows"
extend_path "$WIN/Windows/System32"
prepend_path "$WIN/Users/njen/scoop/apps/win32yank/0.1.1"
prepend_path "$WIN/vscode/bin"
prepend_path "$HOME/source/wttrbar/target/release"
prepend_path "$HOME/source/eww/target/release"
prepend_path "$HOME/.local/bin"
prepend_path "$GOBIN"
prepend_path "$GOROOT/bin"
prepend_path "$HOME/.local/share/bob/nvim-bin"
prepend_path "$DOTS/bin"

source_file "$ZSH/aliases.zsh"
source_file "$ZSH/completions.zsh"
source_file "$ZSH/functions.zsh"

if [ $(command -v "fzf") ]; then
  source_file "$ZSH/fzf.zsh"
fi

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

alias rlp='source $HOME/.zshrc && echo "\n ZSH reloaded."'

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

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# eval "$(pyenv virtualenv-init -)"

eval "$(starship init zsh)"

. "$HOME/.cargo/env"
