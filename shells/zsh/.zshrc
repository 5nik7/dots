#    _____  _____ __  ______  ______
#   /__  / / ___// / / / __ \/ ____/
#     / /  \__ \/ /_/ / /_/ / /
#  _ / /_____/ / __  / _, _/ /___
# (_)____/____/_/ /_/_/ |_|\____/

export ZSHDOT="${HOME}/.config/zsh"
export ZFUNC="${ZSHDOT}/zfunc"
export DOTS="${HOME}/dots"
export DOTSBIN="${DOTS}/bin"

function zource() {
	if [ -f "$1" ]; then
		source "$1"
	fi
}

zource "${DOTSBIN}/utils"

function zieces() {
  local zfile="${ZSHDOT}/$1.zsh"
  if [ -f "$zfile" ]; then
    source "$zfile"
  fi
}

# zieces "zutil"
zieces "functions"
zieces "options"
zieces "plugins"
zieces "completions"
zieces "aliases"
# zieces "zbug"

if is_installed fzf; then
  zieces "fzf"
fi

fpath=( $ZFUNC "${fpath[@]}" )

addir "${HOME}/.local/bin"
extend_path "${HOME}/.local/bin"
extend_path "${HOME}/src/nerd-fonts/bin/scripts"

prepend_path "${DOTSBIN}"

if is_installed zoxide; then
  eval "$(zoxide init zsh)"
  alias cd='z'
fi

if is_installed starship; then
  eval "$(starship init zsh)"
fi
