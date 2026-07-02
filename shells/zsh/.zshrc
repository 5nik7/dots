#  ╔═╗╔═╗╦ ╦╦═╗╔═╗
#  ╔═╝╚═╗╠═╣╠╦╝║
# o╚═╝╚═╝╩ ╩╩╚═╚═╝

if [ -n "${ZSH_DEBUGRC+1}" ]; then
  zmodload zsh/zprof
fi

[ -f "$COLORS" ] && source "$COLORS"
[ -f "$UTIL" ] && source "$UTIL"

fpath+=("$ZFUNC" "${fpath[@]}")

autoload -U +X bashcompinit && bashcompinit
autoload -Uz compinit
compinit
autoload -U colors
colors

# zieces 'zutil'
zieces 'functions'
zieces 'options'
zieces 'plugins'

addir "$HOME/.local/bin"
prepath "$GOBIN"
extpath "$HOME/.local/share/gem/ruby/3.4.0/bin"
prepath "$DOTSBIN"
prepath "$DOTSLOCALBIN"
prepath "$HOME/.cargo/bin"
prepath "$HOME/.local/bin"
prepath "$HOME/bin"
prepath "$DOTSCRIPTS"
prepath "$DOTSBIN"

so "$HOME/.cargo/env"
so "$DOTSHHHH/secrets.sh"
so "/usr/share/nvm/init-nvm.sh"

PYTHONSTARTUP="$HOME/.pythonrc"
if check $PYTHONSTARTUP; then
  export PYTHONSTARTUP
fi

has_theme() { command vivid generate "$1" &>/dev/null; }

theme() {
  if has_theme "$1"; then
    echo "$1" >|"${DOTS}/.theme"
    set_theme
  else
    echo "'$1' not a theme."
  fi
}

set_theme() {
  export THEMESROOT="$DOTS/themes"
  export THEMEBIN="$THEMESROOT/bin"
  prepath "$THEMEBIN"
  export DOT_THEME="$(cat "$DOTS"/.theme)"
  if [[ $DOT_THEME == *-* ]]; then
    export THEME="$(echo "$DOT_THEME" | cut -d '-' -f 1)"
    export FLAVOR="$(echo "$DOT_THEME" | cut -d '-' -f 2)"
  fi

  export THEMEDIR="$THEMESROOT/$THEME"
  export THEMESRC="$THEMEDIR/src"
  export THEMECONF="$THEMEDIR/conf"

  export LS_COLORS="$(vivid generate "$DOT_THEME")"

  so "$THEMEDIR/func.sh"
  so "$THEMEDIR/colors.sh"

  for file in $THEMESRC/*; do
    so "$file"
  done

  if has fzf; then
    so "$HOME/.fzf.zsh"
    zieces 'fzf'
  fi
}

set_theme

zieces 'completions'

if has zoxide; then
  eval "$(zoxide init zsh)"
  alias cd='z'
fi

zieces 'aliases'

if has starship; then
  eval "$(starship init zsh)" && eval "$(starship completions zsh)"
fi

if has direnv; then
  eval "$(direnv hook zsh)"
  DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m'
  export DIRENV_LOG_FORMAT
fi

has batpipe && eval "$(batpipe)"

has batman && eval "$(batman --export-env)"

has ipinfo && { complete -o default -C "$HOME/go/bin/ipinfo" ipinfo; }

so "$HOME/.atuin/bin/env" && has atuin && eval "$(atuin init zsh)"

has uv && eval "$(uv generate-shell-completion zsh)"

has uvx && eval "$(uvx --generate-shell-completion zsh)"

has tv && eval "$(tv init zsh)"

has mise && eval "$(mise activate zsh)"

has usage && source <(usage g completion-init zsh)

if [[ "$istermux" == true ]] &>/dev/null; then
  zieces 'droid'
fi

if [[ "$iswsl" == true ]] &>/dev/null; then
  zieces 'wsl'
fi

if checkdir "$HOME/.bun"; then
  export BUN_INSTALL="$HOME/.bun"
  prepath "$BUN_INSTALL/bin"
  so "$HOME/.bun/_bun"
fi

if checkdir "$HOME/.nvm"; then
  export NVM_DIR="$HOME/.nvm"
  so "$NVM_DIR/nvm.sh"          # This loads nvm
  so "$NVM_DIR/bash_completion" # This loads nvm bash_completion
fi

zle_highlight=('paste:none')

if has fzf; then
  so "$HOME/.fzf.zsh"
  zieces "fzf"
fi

if [ -n "${ZSH_DEBUGRC+1}" ]; then
  zprof
fi
