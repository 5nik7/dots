
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

zinit ice blockf atpull'zinit creinstall -q .'
zinit light zsh-users/zsh-completions

# EZA
zinit ice wait="2" lucid from="gh-r" as="program"
zinit light eza-community/eza
zinit ice wait blockf atpull'zinit creinstall -q .'

# DELTA
zinit ice lucid wait="0" as="program" from="gh-r" bpick="*amd64.deb" pick="usr/bin/delta"
zinit light dandavison/delta

# BOTTOM
zinit ice wait="2" lucid from="gh-r" as="program" bpick='*.deb' pick="usr/bin/btm"
zinit light ClementTsang/bottom

# BAT
zinit ice from="gh-r" as="program" pick="usr/bin/bat" bpick="*amd64.deb" atload="alias cat=bat"
zinit light sharkdp/bat

# BAT-EXTRAS
zinit ice lucid wait="1" as="program" pick="src/batgrep.sh"
zinit ice lucid wait="1" as="program" pick="src/batdiff.sh"
zinit light eth-p/bat-extras

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

zinit light-mode for \
    zdharma-continuum/fast-syntax-highlighting \
    zsh-users/zsh-autosuggestions \
    Aloxaf/fzf-tab \
    ael-code/zsh-colored-man-pages \
    hlissner/zsh-autopair \
    tj/git-extras

fast-theme -q XDG:catppuccin-mocha

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Add RVM to PATH for scripting. Make sure this is the last PATH variable change.
export PATH="$PATH:$HOME/.rvm/bin"

eval $(starship init zsh)