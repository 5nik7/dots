[[ $- != *i* ]] && return

HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=10000
HISTFILESIZE=$HISTSIZE
shopt -s checkwinsize

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

export REPOS="/c/repos"
export DOTS="$REPOS/dots"
export DOTFILES="$DOTS/configs"
export BASHRC="$HOME/.bashrc"
export ALIASES="$HOME/.bash_aliases"

WINHOME="/c/Users/$(whoami)"
export WINHOME

export EDITOR="nvim"
# export MANPAGER="nvim +Man!"
export MANPAGER="less -RF"
export BAT_PAGER="less -RF"
export PAGER="less -RF"
# export PAGER='bat'
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"

export GOBIN="$WINHOME/go/bin"

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

function open {
	if [ -z "$1" ]; then
		explorer.exe .
	else
		explorer.exe "$1"
	fi
}

extend_path "/usr/bin"
extend_path "/usr/local/bin"
extend_path "$DOTS/bin"
extend_path "$WINHOME/.local/bin"
extend_path "/c/vscode/bin"
extend_path "/c/bin"
extend_path "$GOBIN"
extend_path "/c/ProgramData/scoop/shims"
extend_path "$WINHOME/scoop/shims"
prepend_path "$HOME/.local/bin"
prepend_path "/usr/local/bin"
prepend_path "/c/Git/bin"

source_file "$WINHOME/.bash_aliases"

eval "$(starship init bash)"
