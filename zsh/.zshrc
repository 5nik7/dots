export WINREPOS="/mnt/c/Users/nickf/Documents/GitHub/"
export REPOS="$HOME/repos"
export DOTFILES="$REPOS/dots"
export ZSH="$DOTFILES/zsh"
export SUDO_PROMPT="passwd: "
export EDITOR='nvim'
export VISUAL=$EDITOR
export GIT_EDITOR=$EDITOR
export PAGER='bat'
export BAT_CONFIG_PATH="$HOME/.config/bat/bat.conf"
export BAT_THEME="Catppuccin-mocha"

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
extend_path "$HOME/.local/bin"
extend_path "$HOME/.nodenv/bin"
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

source_path "$HOME/.cargo/env"

export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

eval "$(pyenv virtualenv-init -)"

eval "$(rbenv init -)"

eval "$(nodenv init - zsh)"

eval $(starship init zsh)
