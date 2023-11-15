export REPOS="$HOME/repos"
export DOTFILES="$REPOS/dots"

unsetopt promptcr            # Prevent overwriting non-newline output at the prompt
setopt extended_history      # Record start time and elapsed time in history file
setopt append_history        # Add history (instead of creating .zhistory every time)
setopt hist_ignore_all_dups  # Delete older command lines if they overlap
setopt hist_ignore_dups      # Do not add the same command line to history as the previous one
setopt hist_ignore_space     # Remove command lines beginning with a space from history
unsetopt hist_verify         # Stop editability once between history invocation and execution
setopt hist_reduce_blanks    # Extra white space is stuffed and recorded <-teraterm makes history or crazy
setopt hist_save_no_dups     # Ignore old commands that are the same as old commands when writing to history file.
setopt hist_no_store         # history commands are not registered in history
setopt hist_expand           # automatically expand history on completion

setopt share_history

setopt auto_cd               # Move by directory only
setopt no_beep               # Don't beep on command input error

setopt equals                # Expand =COMMAND to COMMAND pathname
setopt nonomatch             # Enable glob expansion to avoid nomatch
setopt glob
setopt extended_glob         # Enable expanded globs
setopt hash_cmds             # Put path in hash when each command is executed         # Don't logout with C-d

setopt long_list_jobs        # Make internal command jobs output jobs -L by default
setopt magic_equal_subst     # command line arguments can be completed after =, e.g. --PREFIX=/USR
setopt multios               # TEE and CAT features are used as needed, such as multiple redirects and pipes

setopt notify                # Notify as soon as background job finishes (don't wait for prompt)

setopt interactive_comments  # Allow comments while typing commands


SAVEHIST=100000
HISTSIZE=100000
HISTFILE=~/.zsh_history

WORDCHARS=''

base00="#11111b"
base01="#181825"
base02="#313244"
base03="#45475a"
base04="#6c7086"
base05="#cdd6f4"
base06="#f5e0dc"
base07="#b4befe"
base08="#f38ba8"
base09="#fab387"
base0A="#f9e2af"
base0B="#a6e3a1"
base0C="#94e2d5"
base0D="#89b4fa"
base0E="#cba6f7"
base0F="#f2cdcd"

function extend_path() {
    [[ -d "$1" ]] || return

    if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
	    export PATH="$1:$PATH"
    fi
}

function source_path() {
	if [ -f "$1" ]; then
		source "$1"
	fi
}

extend_path "$DOTFILES"
extend_path "$HOME/.local/bin"
extend_path "$HOME/.nodenv/bin"
extend_path "$HOME/.local/share/bob/nvim-bin"
extend_path "/mnt/c/vscode/bin"

function cd() {
	builtin cd "$@" && eza -lA --icons --git-repos --git --group-directories-first --no-filesize --no-user --no-time
}

function cleanvim() {
	rm -rf ~/.config/nvim
	rm -rf ~/.local/share/nvim
	rm -rf ~/.local/state/nvim
	rm -rf ~/.cache/nvim
}

function ssh-key-set {
   ssh-add -D
   ssh-add "$HOME/.ssh/${1:-id_rsa}"
}

function ssh-key-info {
   ssh-keygen -l -f "$HOME/.ssh/${1:-id_rsa}"
}

function history-all() {
	history -E 1
}

### echo ###
function print_default() {
	echo -e "$*"
}

function print_info() {
	echo -e "\e[1;36m$*\e[m" # cyan
}

function print_notice() {
	echo -e "\e[1;35m$*\e[m" # magenta
}

function print_success() {
	echo -e "\e[1;32m$*\e[m" # green
}

function print_warning() {
	echo -e "\e[1;33m$*\e[m" # yellow
}

function print_error() {
	echo -e "\e[1;31m$*\e[m" # red
}

function print_debug() {
	echo -e "\e[1;34m$*\e[m" # blue
}

function 256color() {
	for code in {000..255}; do
		print -nP -- "%F{$code}$code %f";
		if [ $((${code} % 16)) -eq 15 ]; then
			echo ""
		fi
	done
}
bindkey -v

function prepend-sudo {
  if [[ $BUFFER != "sudo "* ]]; then
    BUFFER="sudo $BUFFER"; CURSOR+=5
  fi
}
zle -N prepend-sudo

bindkey -M vicmd s prepend-sudo

alias ll="eza -lA --icons --git-repos --git --group-directories-first"
alias l="eza -lA --icons --git-repos --git --group-directories-first --no-filesize --no-user --no-time"

alias c="clear"
alias q="exit"
alias ..="cd .."
alias path='echo $PATH | tr ":" "\n"'
alias d='ranger'
alias less='less -R -M -X'
alias npmup='npm install -g npm@latest'
alias v='nvim'
alias dot='cd $DOTFILES'
alias repos='cd $REPOS'
alias cat='bat'

export SUDO_PROMPT="passwd: "
export EDITOR='nvim'
export VISUAL=$EDITOR
export GIT_EDITOR=$EDITOR
export PAGER='bat'
export BAT_CONFIG_PATH="$HOME/.config/bat/bat.conf"
export BAT_THEME="Catppuccin-mocha"


# Configure and load plugins using Zinit's
ZINIT_HOME="${ZINIT_HOME:-${XDG_DATA_HOME:-${HOME}/.local/share}/zinit}"

# Added by Zinit's installer
if [[ ! -f ${ZINIT_HOME}/zinit.git/zinit.zsh ]]; then
    print -P "%F{14}Installing ZSH plugin manager %F{13}(zinit)%f"
    command mkdir -p "${ZINIT_HOME}" && command chmod g-rwX "${ZINIT_HOME}"
    command git clone https://github.com/zdharma-continuum/zinit.git "${ZINIT_HOME}/zinit.git" && \
        print -P "%F{10}Installation successful.%f%b" || \
        print -P "%F{9}The clone has failed.%f%b"
fi

source "${ZINIT_HOME}/zinit.git/zinit.zsh"

autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit

zinit ice wait="0" lucid from="gh-r" as="program" pick="zoxide-*/zoxide -> zoxide" cp="zoxide-*/completions/_zoxide -> _zoxide" atclone="./zoxide init zsh > init.zsh" atpull="%atclone" src="init.zsh"
zinit light ajeetdsouza/zoxide

zinit ice wait"0a" atinit"ZINIT[COMPINIT_OPTS]=-C; zpcompinit; zpcdreplay" atload"_zsh_highlight" lucid
zinit light zdharma-continuum/fast-syntax-highlighting
zinit ice wait"0a" compile'{src/*.zsh,src/strategies/*}' atinit"ZSH_AUTOSUGGEST_USE_ASYNC=1" atload"_zsh_autosuggest_start" lucid
zinit light zsh-users/zsh-autosuggestions
zinit ice wait"0b" lucid
zinit light hlissner/zsh-autopair
zinit ice wait"0b" blockf lucid
zinit light zsh-users/zsh-completions

zinit light chrissicool/zsh-256color
zinit light mafredri/zsh-async
zinit ice depth"1"

# FZF-TAB
zinit ice wait="1" lucid
zinit light Aloxaf/fzf-tab

zinit ice wait'3' lucid as"program" from"gh-r" \
  mv"gh*/bin/gh -> gh"
zinit light "cli/cli"

# DELTA
zinit ice lucid wait'3' as="program" from="gh-r" bpick="*amd64.deb" pick="usr/bin/delta"
zinit light dandavison/delta

# BOTTOM
zinit ice wait'3' lucid from="gh-r" as="program" bpick='*.deb' pick="usr/bin/btm"
zinit light ClementTsang/bottom

# LAZYGIT
zinit ice lucid wait'3' as="program" from="gh-r" bpick="*Linux_x86_64*" pick="lazygit" atload="alias lg='lazygit'"
zinit light jesseduffield/lazygit

zinit ice wait="2" lucid from="gh-r" as="program"
zinit light eza-community/eza
zinit ice wait blockf atpull'zinit creinstall -q .'


export FZF_DEFAULT_OPTS="
--ansi
--color preview-bg:$base00
--color border:$base00
--color gutter:$base01
--color bg:$base01
--color bg+:$base02
--color fg:$base04
--color hl:$base07
--color fg+:$base09
--color hl+:$base0A
--color info:$base0E
--color prompt:$base0E
--color spinner:$base0F
--color pointer:$base0C
--color marker:$base08
--color header:$base06
--height=50%
--prompt ' >  '
--pointer='|>'
--marker='✓'"

# fast-theme -q XDG:catppuccin-mocha

autoload colors && colors

source_path "$HOME/.cargo/env"

export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

eval "$(pyenv virtualenv-init -)"

eval "$(rbenv init -)"

eval "$(nodenv init - zsh)"

eval $(starship init zsh)
