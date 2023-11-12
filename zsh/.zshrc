
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

setopt list_packed           # Compactly display completion list
setopt auto_remove_slash     # Automatically remove trailing / in completions
setopt auto_param_slash      # Automatically append trailing / in directory name completion to prepare for next completion
setopt mark_dirs             # Append trailing / to filename expansions when they match a directory
setopt list_types            # Display file type identifier in list of possible completions (ls -F)
unsetopt menu_complete       # When completing, instead of displaying a list of possible completions and beeping. Don't insert the first match suddenly.
setopt auto_list             # Display a list of possible completions with ^I (when there are multiple candidates for completion, display a list)
setopt auto_menu             # Automatic completion of completion candidates in order by hitting completion key repeatedly
setopt auto_param_keys       # Automatically completes bracket correspondence, etc.
setopt auto_resume           # Resume when executing the same command name as a suspended process


setopt auto_cd               # Move by directory only
setopt no_beep               # Don't beep on command input error

setopt complete_in_word
setopt equals                # Expand =COMMAND to COMMAND pathname
setopt nonomatch             # Enable glob expansion to avoid nomatch
setopt glob
setopt extended_glob         # Enable expanded globs
setopt hash_cmds             # Put path in hash when each command is executed
setopt no_hup                # Don't kill background jobs on logout
setopt ignore_eof            # Don't logout with C-d

setopt long_list_jobs        # Make internal command jobs output jobs -L by default
setopt magic_equal_subst     # command line arguments can be completed after =, e.g. --PREFIX=/USR
setopt multios               # TEE and CAT features are used as needed, such as multiple redirects and pipes
setopt numeric_glob_sort     # Sort by interpreting numbers as numerical values
setopt path_dirs             # Find subdirectories in PATH when / is included in command name

setopt auto_pushd            # Put the directory in the directory stack even when cd'ing normally.
setopt pushd_ignore_dups     # Delete old duplicates in the directory stack.
setopt pushd_to_home         # no pushd argument == pushd $HOME
setopt pushd_silent          # Don't show contents of directory stack on every pushd,popd

setopt notify                # Notify as soon as background job finishes (don't wait for prompt)

unsetopt no_clobber
setopt interactive_comments  # Allow comments while typing commands
setopt chase_links           # Symbolic links are converted to linked paths before execution
setopt noflowcontrol

setopt nolistambiguous # Show menu

SAVEHIST=100000
HISTSIZE=100000
HISTFILE=~/.zsh_history

WORDCHARS='*?_-[]~&;!#$%^(){}<>|'

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

extend_path "$HOME/.local/bin"
extend_path "$HOME/.local/share/bob/nvim-bin"
extend_path "/mnt/c/vscode/bin"

function cd() {
	builtin cd "$@" && eza -la --icons --hyperlink --git-repos --git --group-directories-first --no-filesize --no-user --no-time
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

alias ll="eza -la --icons --hyperlink --git-repos --git --group-directories-first"
alias l="eza -la --icons --hyperlink --git-repos --git --group-directories-first --no-filesize --no-user --no-time"

alias c="clear"
alias q="exit"
alias ..="cd .."
alias path='echo $PATH | tr ":" "\n"'
alias d='ranger'

export REPOS="$HOME/repos"
export DOTFILES="$REPOS/dots"
export SUDO_PROMPT="passwd: "
export EDITOR='nvim'
export VISUAL=$EDITOR
export GIT_EDITOR=$EDITOR
export PAGER='bat'
export BAT_CONFIG_PATH="$HOME/.config/bat/bat.conf"
export BAT_THEME="Catppuccin-mocha"

source_path "$HOME/.cargo/env"

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

zinit ice wait="0b" lucid blockf
zinit light zsh-users/zsh-completions

# FZF
zinit ice from="gh-r" as="command" bpick="*linux_amd64*"
zinit light junegunn/fzf
# BIND MULTIPLE WIDGETS USING FZF
zinit ice lucid wait'0c' multisrc"shell/{completion,key-bindings}.zsh" id-as="junegunn/fzf_completions" pick="/dev/null"
zinit light junegunn/fzf
# FZF-TAB
zinit ice wait="1" lucid
zinit light Aloxaf/fzf-tab

zinit wait'1' lucid \
	pick"fzf-extras.zsh" \
	light-mode for @atweiden/fzf-extras # fzf

zinit wait'1c' lucid \
	light-mode for @chitoku-k/fzf-zsh-completions


export FZF_DEFAULT_OPTS="
--ansi
--layout=default
--info=inline
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
--multi
--prompt ' >  '
--pointer='|>'
--marker='✓'
--bind 'ctrl-e:execute(nvim {} < /dev/tty > /dev/tty 2>&1)' > selected
--bind 'ctrl-v:execute(code {+})'"
export FZF_DEFAULT_COMMAND='rg --files --no-ignore --hidden --follow -g "!{.git,node_modules}/*" 2> /dev/null'
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"

zinit wait'0' lucid \
	light-mode for @mafredri/zsh-async

# EZA
zinit wait'1' lucid \
	from"gh-r" as"program" pick"eza" \
	light-mode for @eza-community/eza

# DELTA
zinit ice lucid wait="0" as="program" from="gh-r" bpick="*amd64.deb" pick="usr/bin/delta"
zinit light dandavison/delta

# BOTTOM
zinit ice wait="2" lucid from="gh-r" as="program" bpick='*.deb' pick="usr/bin/btm"
zinit light ClementTsang/bottom

# BAT

zinit wait'1' lucid \
	from"gh-r" as"program" cp"bat/autocomplete/bat.zsh -> _bat" pick"bat*/bat" \
	atload"export BAT_THEME='base16'; alias cat=bat" \
	light-mode for @sharkdp/bat

# BAT-EXTRAS
zinit ice lucid wait="1" as="program" pick="src/batgrep.sh"
zinit ice lucid wait="1" as="program" pick="src/batdiff.sh"
zinit light eth-p/bat-extras
alias rg=batgrep.sh
alias bd=batdiff.sh
alias man=batman.sh

# RIPGREP
zinit wait'1' lucid blockf nocompletions \
	from"gh-r" as'program' pick'ripgrep*/rg' \
	cp"ripgrep-*/complete/_rg -> _rg" \
	atclone'chown -R $(id -nu):$(id -ng) .; zinit creinstall -q BurntSushi/ripgrep' \
	atpull'%atclone' \
	light-mode for @BurntSushi/ripgrep

zinit wait'1' lucid blockf nocompletions \
	from"gh-r" as'program' cp"fd-*/autocomplete/_fd -> _fd" pick'fd*/fd' \
	atclone'chown -R $(id -nu):$(id -ng) .; zinit creinstall -q sharkdp/fd' \
	atpull'%atclone' \
	light-mode for @sharkdp/fd

# GH-CLI
zinit ice lucid as="command" from="gh-r" bpick="*linux_amd64.deb" atclone="./gh completion -s zsh > _gh" atpull="%atclone" mv="**/bin/gh* -> gh" pick="usr/bin/gh"
zinit light cli/cli

# LAZYGIT
zinit ice lucid wait="0" as="program" from="gh-r" bpick="*Linux_x86_64*" pick="lazygit" atload="alias lg='lazygit'"
zinit light jesseduffield/lazygit

# GLOW
zinit ice lucid wait"0" as"program" from"gh-r" bpick='*_amd64.deb' pick"usr/bin/glow"
zinit light charmbracelet/glow

# ERDTREE
zinit ice lucid wait"0" as"program" from"gh-r"
zinit light solidiquis/erdtree

# TREE-SITTER
zinit ice as="program" from="gh-r" mv="tree* -> tree-sitter" pick="tree-sitter"
zinit light tree-sitter/tree-sitter

# PRETTYPING
zinit ice lucid wait="" as="program" pick="prettyping" atload="alias ping=prettyping"
zinit load denilsonsa/prettyping


zinit wait'1' lucid \
	from"gh-r" as"program" \
	atload"alias rm='trash put'" \
	light-mode for @oberblastmeister/trashy

zinit wait'1' lucid \
	from"gh-r" as"program" mv'tealdeer* -> tldr' \
	light-mode for @dbrgn/tealdeer
zinit ice wait'1' lucid as"completion" mv'zsh_tealdeer -> _tldr'
zinit snippet https://github.com/dbrgn/tealdeer/blob/main/completion/zsh_tealdeer

zinit wait'2' lucid \
	light-mode for @caarlos0/zsh-git-sync


# translation #
zinit wait'1' lucid \
	ver"stable" pullopts"--rebase" \
	light-mode for @soimort/translate-shell

zinit light-mode for \
    zdharma-continuum/fast-syntax-highlighting \
    zsh-users/zsh-autosuggestions \
    ael-code/zsh-colored-man-pages \
    hlissner/zsh-autopair \
    tj/git-extras

fast-theme -q XDG:catppuccin-mocha

autoload colors && colors

function plugupdate() {
	print_info "Update zinit plugins"
	zinit update --all
	print_info "Finish zinit plugins"

	# print_info "Update $EDITOR plugins"
	# $EDITOR --headless -c 'Lazy! sync' -c 'qall'

	# print_info "Update $EDITOR mason"
	# $EDITOR --headless -c 'lua require("mason-registry").refresh(); require("mason-registry").update()' -c 'qall'

	# print_info "Finish Neovim plugins"
}


export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

eval "$(rbenv init -)"

eval $(starship init zsh)