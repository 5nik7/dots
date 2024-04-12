#     ____  ______ _____  _____
#    /_  / / __/ // / _ \/ ___/
#   _ / /__\ \/ _  / , _/ /__
#  (_)___/___/_//_/_/|_|\___/

export LC_ALL='en_US.UTF-8'
export LANG='en_US.UTF-8'
export LANGUAGE='en_US.UTF-8'

export WIN='/mnt/c'
export REPOS="$WIN/repos"

export SUDO_PROMPT="passwd: "
export DOTFILES="$REPOS/dots"
export ZSH="$DOTFILES/configs/zsh"
export SHELL='/usr/bin/zsh'

export TERMINAL='kitty'
export BROWSER='firefox'
export EDITOR="nvim"
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"
export EDITOR_TERM="$TERMINAL -e $EDITOR"
export MANPAGER="nvim +Man!"
export PAGER="nvim +Man!"
export BAT_CONFIG_PATH="$HOME/.config/bat/bat.conf"

export GOBIN="$HOME/go/bin"
export PYENV_ROOT="$HOME/.pyenv"
export BUN_INSTALL="$HOME/.bun"
export NVM_DIR="$HOME/.nvm"

export WAL_BACKEND="$(< "$HOME/.backend")"

fpath=(
	$ZSH/functions
	/usr/local/share/zsh/site-functions
	$fpath
)

autoload -U $ZSH/functions/*(:t)

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
setopt no_bg_nice
setopt no_hup
setopt hist_ignore_dups
setopt hist_expire_dups_first
unsetopt beep
setopt no_list_beep
setopt auto_cd
setopt glob_dots
setopt nomatch
setopt menu_complete
setopt extended_glob
setopt interactive_comments
setopt append_history
setopt local_options
setopt prompt_subst

setopt complete_aliases

HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000

WORDCHARS='*?[]~=&;!#$%^(){}<>'

export FZF_DEFAULT_OPTS="
--layout=reverse --info=inline --height=80% --multi --cycle --margin=1 --border=sharp
--preview '([[ -f {} ]] && (bat --style=numbers --color=always --line-range=:500 {} || cat {})) || ([[ -d {} ]] \
&& (exa -TFl --group-directories-first --icons -L 2 --no-user {} | less)) || echo {} 2> /dev/null | head -200'
--prompt=' ' --pointer=' ' --marker=' '
--color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0
--color info:2,prompt:-1,spinner:2,pointer:6,marker:4
--preview-window='border-sharp'
--no-scrollbar
--preview-window='right,65%,border-left,+{2}+3/3,~3'
--bind '?:toggle-preview'
--bind 'ctrl-a:select-all'
--bind 'ctrl-y:execute-silent(echo {+} | $CLIPCOPY)'
--bind 'ctrl-e:execute($TERMINAL $EDITOR {+})+reload(fzf)'"

export FZF_DEFAULT_COMMAND='fd --hidden --follow --exclude=.git --exclude=node_modules'

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

autoload -U up-line-or-beginning-search
autoload -U down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search

bindkey '^p' history-search-backward
bindkey '^n' history-search-forward
bindkey '^e' end-of-line
bindkey '^w' forward-word
bindkey "^[[3~" delete-char
bindkey ";5C" forward-word
bindkey ";5D" backward-word

zle_highlight=('paste:none')

eval "$(pyenv init -)"

eval "$(rbenv init -)"

eval "$(direnv hook zsh)"

eval "$(starship init zsh)"
