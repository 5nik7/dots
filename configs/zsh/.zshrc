#     ____  ______ _____  _____
#    /_  / / __/ // / _ \/ ___/
#   _ / /__\ \/ _  / , _/ /__
#  (_)___/___/_//_/_/|_|\___/

export COLORTERM=truecolor

case $TERM in
  iterm            |\
  linux-truecolor  |\
  screen-truecolor |\
  tmux-truecolor   |\
  xterm-truecolor  )    export COLORTERM=truecolor ;;
  vte*)
esac

export LC_ALL='en_US.UTF-8'
export LANG='en_US.UTF-8'
export LANGUAGE='en_US.UTF-8'

export WIN='/mnt/c'
export REPOS="$WIN/repos"
export DOTS="$HOME/.dots"
export DOTFILES="$DOTS/configs"
export ZSH="$DOTFILES/zsh"

export SUDO_PROMPT="passwd: "

export TERMINAL='kitty'
export BROWSER='firefox'
export EDITOR="nvim"
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"
export EDITOR_TERM="$TERMINAL -e $EDITOR"
export MANPAGER="nvim +Man!"
export PAGER="nvim +Man!"
export BAT_CONFIG_PATH="$DOTFILES/bat/bat.conf"

export GOBIN="$HOME/go/bin"
export PYENV_ROOT="$HOME/.pyenv"
export BUN_INSTALL="$HOME/.bun"
export NVM_DIR="$HOME/.nvm"

function source_file() {
	if [ -e "$1" ]; then
		source "$1"
	fi
}

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

source_file "$ZSH/fzf.zsh"
source_file "$ZSH/functions.zsh"
source_file "$ZSH/util.zsh"
source_file "$ZSH/aliases.zsh"
source_file "$ZSH/plugins.zsh"
source_file "$ZSH/completions.zsh"

source_file "$HOME/.cargo/env"
source_file "$NVM_DIR/nvm.sh"
source_file "$NVM_DIR/bash_completion"
source_file "$HOME/.bun/_bun"
source_file "$HOME/.nix-profile/etc/profile.d/nix.sh"

# Options
# completions
unsetopt menu_complete   # do not autoselect the first completion entry
unsetopt flowcontrol
setopt auto_menu         # show completion menu on successive tab press
setopt complete_in_word
setopt always_to_end

# misc
setopt long_list_jobs
setopt interactivecomments
setopt multios
setopt prompt_subst
zle_highlight=('paste:none')

# History command configuration
setopt extended_history       # record timestamp of command in HISTFILE
setopt hist_expire_dups_first # delete duplicates first when HISTFILE size exceeds HISTSIZE
setopt hist_ignore_dups       # ignore duplicated commands history list
setopt hist_ignore_space      # ignore commands that start with space
setopt hist_verify            # show command with history expansion to user before running it
setopt inc_append_history     # add commands to HISTFILE in order of execution
setopt share_history          # share command history data

# Changing/making/removing directory
setopt auto_pushd
setopt pushd_ignore_dups
setopt pushdminus
setopt auto_cd

# Globbing
setopt ksh_glob

# setopt no_bg_nice
unsetopt beep
setopt no_list_beep


HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=$HISTSIZE

WORDCHARS='*?[]~=&;!#$%^(){}<>'

# export FZF_DEFAULT_OPTS="
# --layout=reverse --info=inline --height=80% --multi --cycle --margin=1 --border=sharp
# --preview '([[ -f {} ]] && (bat --style=numbers --color=always --line-range=:500 {} || cat {})) || ([[ -d {} ]] \
# && (exa -TFl --group-directories-first --icons -L 2 --no-user {} | less)) || echo {} 2> /dev/null | head -200'
# --prompt=' ' --pointer=' ' --marker=' '
# --color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0
# --color info:2,prompt:-1,spinner:2,pointer:6,marker:4
# --preview-window='border-sharp'
# --no-scrollbar
# --preview-window='right,65%,border-left,+{2}+3/3,~3'
# --bind '?:toggle-preview'
# --bind 'ctrl-a:select-all'
# --bind 'ctrl-y:execute-silent(echo {+} | $CLIPCOPY)'
# --bind 'ctrl-e:execute($TERMINAL $EDITOR {+})+reload(fzf)'"

# export FZF_DEFAULT_COMMAND='fd --hidden --follow --exclude=.git --exclude=node_modules'

extend_path "$WIN/Windows"
extend_path "$WIN/Windows/System32"
extend_path "$WIN/bin"
extend_path "$WIN/ProgramData/scoop/shims"
extend_path "$WIN/vscode/bin"
extend_path "$HOME/.local/bin"
prepend_path "$HOME/.local/share/bob/nvim-bin"
prepend_path "$GOBIN"
prepend_path "$BUN_INSTALL/bin"
prepend_path "$PYENV_ROOT/bin"
prepend_path "$DOTFILES/bin"

bindkey -v

# autoload -U up-line-or-beginning-search
# autoload -U down-line-or-beginning-search
# zle -N up-line-or-beginning-search
# zle -N down-line-or-beginning-search

# bindkey '^p' history-search-backward
# bindkey '^n' history-search-forward
# bindkey '^e' end-of-line
# bindkey '^w' forward-word
# bindkey "^[[3~" delete-char
# bindkey ";5C" forward-word
# bindkey ";5D" backward-word

BASE16_SHELL="$HOME/.config/base16-shell/"
[ -n "$PS1" ] && \
    [ -s "$BASE16_SHELL/profile_helper.sh" ] && \
        source "$BASE16_SHELL/profile_helper.sh"


# eval "$(pyenv init -)"

# eval "$(rbenv init -)"

# eval "$(direnv hook zsh)"

eval "$(fzf --zsh)"

eval "$(starship init zsh)"
