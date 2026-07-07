#  ╔═╗╔═╗╦ ╦╦═╗╔═╗
#  ╔═╝╚═╗╠═╣╠╦╝║
# o╚═╝╚═╝╩ ╩╩╚═╚═╝

if [ -n "${ZSH_DEBUGRC+1}" ]; then
  zmodload zsh/zprof
fi

# set global default env
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

export DOTS="${SOTS:-$HOME/dots}"

[ -r "$DOTS/bin/util" ] && source "$DOTS/bin/util"

if has nvim; then
  EDITOR='nvim'
elif has vim; then
  EDITOR='vim'
elif has vi; then
  EDITOR='vi'
elif has code; then
  EDITOR='code'
else
  EDITOR='nano'
fi

export EDITOR
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"
export EDITOR_TERM="$TERMINAL -e $EDITOR"

fpath=($PREFIX/share/zsh/site-functions $fpath)

export ZSH="$DOTS/shells/zsh"
export ZSHCOMP="$ZSH/completions"

declare -xgA zsh
declare -x zsh[root]="$ZSH"
declare -x zsh[completions]="$ZSHCOMP"

prepath "$zsh[completions]"

fpath=($zsh[completions] $fpath)

environments=($DOTS/**/*.env)

for file in ${(M)environments#*/*.env}; do
  source $file
done

docs="${DOCS:-$HOME/Documents}"
export DOCS="$docs"

notes="${NOTES:-$HOME/Notes}"
export NOTES="$notes"

# set config env
export STARSHIP_CONFIG="${dot[configs]}/starship/starship.toml"
export STARSHIP_DIR="${STARSHIP_CONFIG%/*}"
export STARSHIP_THEMES="$STARSHIP_DIR/themes"

export BAT_CONFIG_DIR="${dot[configs]}/bat"
export BAT_CONFIG_PATH="$BAT_CONFIG_DIR/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi"

[ -r "$HOME/.fzf.zsh" ] && source "$HOME/.fzf.zsh"

[ -r "${XDG_DATA_HOME}/bob/env/env.sh" ] && source "${XDG_DATA_HOME}/bob/env/env.sh
"
export GOBIN="${GOBIN:-$HOME/go/bin}"
autoload -U colors
colors

export CLICOLOR=1

autoload -U +X bashcompinit && bashcompinit
autoload -Uz compinit

# if [[ -n $HOME/.zcompdump(#qN.mh+24) ]]; then
#   compinit -d $HOME/.zcompdump
# else
#   compinit -C
# fi

zmodload zsh/complist
compinit
_comp_options+=(globdots)

alias zieces="shellmod"

zieces 'functions'
zieces 'aliases'
zieces 'options'
zieces 'fzf'
zieces 'completions'
zieces 'plugins'

prepath "$GOBIN"
extpath "$HOME/.local/share/gem/ruby/3.4.0/bin"
prepath "$HOME/.cargo/bin"
prepath "$HOME/.local/bin" || addir "$HOME/.local/bin"
prepath "$HOME/bin
"

#add each topic folder to fpath so that they can add functions and completion scripts

so "$HOME/.cargo/env"
so "$DOTSHHHH/secrets.sh"
so "/usr/share/nvm/init-nvm.sh"

PYTHONSTARTUP="$HOME/.pythonrc"
if check $PYTHONSTARTUP; then
  export PYTHONSTARTUP
fi

if has zoxide; then
  eval "$(zoxide init zsh)"
  alias cd='z'
fi

if has direnv; then
  eval "$(direnv hook zsh)"
  DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m'
  export DIRENV_LOG_FORMAT
fi

has batpipe && eval "$(batpipe)"

has batman && eval "$(batman --export-env)"

so "$HOME/.atuin/bin/env" && has atuin && eval "$(atuin init zsh)"

has tv && eval "$(tv init zsh)"

has mise && eval "$(mise activate zsh)"

if checkdir "$HOME/.bun"; then
  export BUN_INSTALL="$HOME/.bun"
  prepath "$BUN_INSTALL/bin"
  so "$HOME/.bun/_bun"
fi

NVM_DIR="${NVM_DIR}:-$HOME/.nvm}"
if checkdir "$NVM_DIR"; then
  so "$NVM_DIR/nvm.sh"          # This loads nvm
  so "$NVM_DIR/bash_completion" # This loads nvm bash_completion
fi

# autoload -U +X bashcompinit && bashcompinit
#
# autoload -Uz compinit
# compinit

has usage && source <(usage g completion-init zsh)

has uv && eval "$(uv generate-shell-completion zsh)"

has uvx && eval "$(uvx --generate-shell-completion zsh)"

has ipinfo && { complete -o default -C "$HOME/go/bin/ipinfo" ipinfo; }

if [[ "$is_termux" == true ]] &>/dev/null; then
  zieces 'droid'
fi

if [[ "$is_wsl" == true ]] &>/dev/null; then
  zieces 'wsl'
fi

if has starship; then
  eval "$(starship init zsh)" && eval "$(starship completions zsh)"
fi

[ -r "${zsh[local]}" ] && source "${zsh[local]}"

if [ -n "${ZSH_DEBUGRC+1}" ]; then
  zprof
fi
