#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=10000
HISTFILESIZE=20000
shopt -s checkwinsize

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

export DOTFILES="$HOME/.dotfiles"
export BASHRC="$HOME/.bashrc"
export ALIASES="$HOME/.aliases"
export WIN='/mnt/c'
export REPOS="$WIN/repos"

export EDITOR="nvim"
# export MANPAGER="nvim +Man!"
export MANPAGER="less -RF"
export BAT_PAGER="less -RF"
export PAGER="less -RF"
# export PAGER='bat'
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"

export GOBIN="$HOME/go/bin"

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

function fixpath() {
	PATH=$(echo $(sed 's/:/\n/g' <<<$PATH | sort | uniq) | sed -e 's/\s/':'/g')
}

function source_file() {
	if [ -f "$1" ]; then
		source "$1"
	fi
}

extend_path "$DOTFILES/bin"
extend_path "$HOME/.local/bin"
extend_path "$HOME/.local/share/bob/nvim-bin"
extend_path "$WIN/vscode/bin"
extend_path "$WIN/bin"
extend_path "$WIN/Windows"
extend_path "$GOBIN"
prepend_path "$HOME/.local/share/gem/ruby/3.0.0/bin"

source_file "$HOME/.aliases"

PS1='\[\033[01;32m\][\u@\h\[\033[01;37m\] \W\[\033[01;32m\]]$\[\033[00m\] '

source_file "$HOME/.cargo/env"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"                   # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion

eval "$(starship init bash)"
