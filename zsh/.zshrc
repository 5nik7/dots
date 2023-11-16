export WINREPOS="/mnt/c/GitHub/"
export REPOS="$(dirname "$(dirname "$(dirname "$(readlink "${(%):-%N}")")")")"
export DOTFILES="$(dirname "$(dirname "$(readlink "${(%):-%N}")")")"
export ZSH="$(dirname "$(readlink "${(%):-%N}")")"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export XDG_STATE_HOME="$HOME/.local/state"
export XDG_CONFIG_DIRS="/etc/xdg"

export SUDO_PROMPT=" passwd: "
export EDITOR='nvim'
export VISUAL=$EDITOR
export GIT_EDITOR=$EDITOR
export BROWSER="thorium-browser"
export PAGER='bat'
export BAT_CONFIG_PATH="$HOME/.config/bat/bat.conf"
export GOPATH=$HOME/go
export GOBIN=$HOME/go/bin
export zfunc="$XDG_DATA_HOME/zsh/functions"

fpath=(
    $ZSH/functions.zsh
    $zfunc
    $fpath
)

# PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/lib/wsl/lib"

function zmodule() {
	if [ -f "$ZSH/$1.zsh" ]; then
		source "$ZSH/$1.zsh"
	fi
}

zmodule "functions"
zmodule "options"
zmodule "theme"
zmodule "aliases"
zmodule "plugins"

extend_path "$DOTFILES"
extend_path "$XDG_DATA_HOME/zsh/functions"
extend_path "$HOME/.local/bin"
extend_path "$HOME/bin"
extend_path "$GOBIN"
extend_path "$HOME/.local/share/bob/nvim-bin"
extend_path "/mnt/c/vscode/bin"

export FZF_DEFAULT_OPTS="
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
--pointer='|>'"

# fast-theme -q XDG:catppuccin-mocha

autoload -U bashcompinit
bashcompinit

eval "$(luarocks path --bin)"

source_path "$HOME/.cargo/env"

source_path "$HOME/venv/bin/activate"

eval "$(rbenv init -)"

export NVM_DIR="$HOME/.config/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

eval $(starship init zsh)