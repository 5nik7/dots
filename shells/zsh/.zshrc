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

export COLORTERM=truecolor

case $TERM in
iterm | \
    linux-truecolor | \
    screen-truecolor | \
    tmux-truecolor | \
    xterm-truecolor) export COLORTERM=truecolor ;;
vte*) ;;
esac

export SUDO_PROMPT="passwd: "
export STARSHIP_CONFIG="/mnt/c/projects/dots/configs/starship/starship.toml"
export EDITOR="nvim"
export GOBIN="$HOME/go/bin"
export GOROOT="/usr/local/go"

export WIN='/mnt/c'
export ZSH="$HOME/.zsh"
export DOTS="$HOME/dots"

export BAT_THEME="base16"
export BAT_STYLE="plain"
export BAT_PAGING="never"



setopt extended_history
setopt hist_expire_dups_first
setopt hist_ignore_dups
setopt hist_ignore_space
setopt hist_verify
setopt inc_append_history
setopt share_history
setopt auto_cd
unsetopt beep
setopt no_list_beep

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
alias vi='$EDITOR'
alias vim='$EDITOR'
alias sv="sudo $EDITOR"

# Keep 1000 lines of history within the shell and save it to ~/.zsh_history:
HISTSIZE=10000
SAVEHIST=10000
HISTFILE=~/.zsh_history

# Use modern completion system
autoload -Uz compinit
compinit

zle_highlight=('paste:none')

zstyle ':completion:*' auto-description 'specify: %d'
zstyle ':completion:*' completer _expand _complete _correct _approximate
zstyle ':completion:*' format 'Completing %d'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' menu select=2
eval "$(dircolors -b)"
zstyle ':completion:*:default' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' list-prompt %SAt %p: Hit TAB for more, or the character to insert%s
zstyle ':completion:*' matcher-list '' 'm:{a-z}={A-Z}' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=* l:|=*'
zstyle ':completion:*' menu select=long
zstyle ':completion:*' select-prompt %SScrolling active: current selection at %p%s
zstyle ':completion:*' use-compctl false
zstyle ':completion:*' verbose true

zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'
zstyle ':completion:*:kill:*' command 'ps -u $USER -o pid,%cpu,tty,cputime,cmd' Created by newuser for 5.8.1


# FZF colors
export FZF_DEFAULT_OPTS="--color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0 \
--color info:2,prompt:-1,spinner:2,pointer:6,marker:4 \
--border --margin=0,2"

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
prepend_path "$HOME/source/julia-1.10.5/bin"
prepend_path "$WIN/Users/njen/scoop/apps/win32yank/0.1.1"
prepend_path "$WIN/vscode/bin"
prepend_path "$HOME/.local/bin"
prepend_path "$GOBIN"
prepend_path "$GOROOT/bin"
prepend_path "$HOME/.local/share/bob/nvim-bin"
prepend_path "$DOTS/bin"

source_file "$ZSH/aliases.zsh"
source_file "$ZSH/functions.zsh"

alias rlp='source $HOME/.zshrc && echo "\n ZSH reloaded."'

eval "$(starship init zsh)"

. "$HOME/.cargo/env"

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
