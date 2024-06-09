#!/bin/bash

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=10000
HISTFILESIZE=$HISTSIZE
shopt -s checkwinsize

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

export WIN='/mnt/c'
export REPOS="$WIN/repos"
export DOTS="$REPOS/dots"
export DOTFILES="$DOTS/configs"
export ZSH="$DOTFILES/zsh"


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
SYSTEMD_EDITOR="$EDITOR"
export SYSTEMD_EDITOR
VISUAL="$EDITOR"
export VISUAL

export MANPAGER="bat"
export PAGER="bat"

export XDG_CONFIG_HOME="$HOME/.config"

export GOBIN="$HOME/go/bin"
export PYENV_ROOT="$HOME/.pyenv"
export NVM_DIR="$HOME/.nvm"

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
extend_path "$WIN/bin"
extend_path "$WIN/ProgramData/scoop/shims"
extend_path "$WIN/vscode/bin"
extend_path "$DOTFILES/bin"
extend_path "$HOME/.local/bin"
prepend_path "$HOME/go/bin"
prepend_path "$PYENV_ROOT/bin"

source_file "$HOME/.bash_aliases"

# LS_COLORS="$(vivid generate snazzy)"
# export LS_COLORS

# PS1='\[\033[01;32m\][\u@\h\[\033[01;37m\] \W\[\033[01;32m\]]$\[\033[00m\] '

source_file "$HOME/.cargo/env"

# eval "$(pyenv init -)"

eval "$(fzf --bash)"

eval "$(starship init bash)"
