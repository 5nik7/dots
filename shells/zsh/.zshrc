#  ╔═╗╔═╗╦ ╦╦═╗╔═╗
#  ╔═╝╚═╗╠═╣╠╦╝║
# o╚═╝╚═╝╩ ╩╩╚═╚═╝

if [ -n "${ZSH_DEBUGRC+1}" ]; then
  zmodload zsh/zprof
fi

[ -f "$COLORS" ] && source "$COLORS"
[ -f "$UTIL" ] && source "$UTIL"

fpath+=("$ZFUNC" "${fpath[@]}")

# Support colors in less
export LESS_TERMCAP_mb=$(
  tput bold
  tput setaf 1
)
export LESS_TERMCAP_md=$(
  tput bold
  tput setaf 1
)
export LESS_TERMCAP_me=$(tput sgr0)
export LESS_TERMCAP_se=$(tput sgr0)
export LESS_TERMCAP_so=$(
  tput bold
  tput setaf 3
  tput setab 4
)
export LESS_TERMCAP_ue=$(tput sgr0)
export LESS_TERMCAP_us=$(
  tput smul
  tput bold
  tput setaf 2
)
export LESS_TERMCAP_mr=$(tput rev)
export LESS_TERMCAP_mh=$(tput dim)
export LESS_TERMCAP_ZN=$(tput ssubm)
export LESS_TERMCAP_ZV=$(tput rsubm)
export LESS_TERMCAP_ZO=$(tput ssupm)
export LESS_TERMCAP_ZW=$(tput rsupm)

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

export THEMESROOT="$DOTS/themes"
export THEMEBIN="$THEMESROOT/bin"
prepath "$THEMEBIN"
export THEMEFILE="$THEMESROOT/.theme"
export DEFAULT_THEME="${DEFAULT_THEME:-catppuccin}"
export DEFAULT_FLAVOR="${DEFAULT_FLAVOR:-mocha}"

if [[ ! -f $THEMEFILE ]]; then
  THEME="${DEFAULT_THEME}"
  FLAVOR="${DEFAULT_FLAVOR}"
  echo "${DEFAULT_THEME}-${DEFAULT_FLAVOR}" >"$THEMEFILE"
fi

has_theme() { command vivid generate "$1" &>/dev/null; }

theme() {
  local new="$1"
  local old="$THEME"
  if has_theme "$new"; then
    if [[ $new == $old ]]; then
      warn "'$new' is current theme."
      return 1
    else
      echo "$new" >|"$THEMEFILE"
      set_theme "$new"
    fi
  else
    err "'$new' not a theme."
    return 1
  fi
}

set_theme() {
  local t out

  if [[ -n "$1" ]]; then
    t="$1"
  else
    t="$(cat "$THEMEFILE")"
  fi

  if [[ $t == *-* ]]; then
    export THEME="$(echo "$t" | cut -d '-' -f 1)"
    export FLAVOR="$(echo "$t" | cut -d '-' -f 2)"
    out="THEME:$THEME|FLAVOR:$FLAVOR"
  else
    export THEME="$t"
    out="THEME:$THEME"
  fi

  export THEMEDIR="$THEMESROOT/$THEME"
  export THEMESRC="$THEMEDIR/src"
  export THEMECONF="$THEMEDIR/conf"

  export LS_COLORS="$(vivid generate "$t")"

  so "$THEMEDIR/func.sh"
  so "$THEMEDIR/colors.sh"

  for file in $THEMESRC/*; do
    so "$file"
  done

  if has fzf; then
    zieces 'fzf'
  fi

  if [[ -n "$1" ]]; then
    ok "$out"
  fi
}

set_theme

zieces 'completions'

if has fzf; then
  so "$HOME/.fzf.zsh"
  zieces 'fzf'
fi

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

if [[ "$is_termux" == true ]] &>/dev/null; then
  zieces 'droid'
fi

if [[ "$is_wsl" == true ]] &>/dev/null; then
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

if [ -n "${ZSH_DEBUGRC+1}" ]; then
  zprof
fi
