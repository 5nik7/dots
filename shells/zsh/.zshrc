#    _____  _____ __  ______  ______
#   /__  / / ___// / / / __ \/ ____/
#     / /  \__ \/ /_/ / /_/ / /
#  _ / /_____/ / __  / _, _/ /___
# (_)____/____/_/ /_/_/ |_|\____/

export DOTS="${HOME}/dots"
export SHELLS="${DOTS}/shells"
export ZSHDOTS="${SHELLS}/zsh"
export ZFUNC="${HOME}/.zfunc"
export DOTSBIN="${DOTS}/bin"
export backups="${HOME}/.backups"

export DOT_THEME="$(cat $DOTS/.theme)"

export LS_COLORS="$(vivid generate $DOT_THEME)"

function zource() {
	if [ -f "${1}" ]; then
		source "${1}"
	fi
}

function zieces() {
  zfile="${ZSHDOTS}/${1}.zsh"
  if [ -f "${zfile}" ]; then
    source "${zfile}"
  fi
}

zieces "zutil"
zieces "functions"
zieces "options"
zieces "plugins"
zieces "completions"
zieces "aliases"

fpath=( "${ZFUNC}" "${fpath[@]}" )

addir "${HOME}/.local/bin"
addir "${backups}"

extend_path "${HOME}/.local/bin"
extend_path "${HOME}/src/nerd-fonts/bin/scripts"

extend_path "${HOME}/.local/share/nvim/mason/bin"

prepend_path "${DOTSBIN}"

export SHHHH="${DOTS}/secrets"
zource "${SHHHH}/secrets.sh"

if is_installed nvim; then
    export MANPAGER='nvim +Man! +"set nocul" +"set noshowcmd" +"set noruler" +"set noshowmode" +"set laststatus=0" +"set showtabline=0" +"set nonumber"'
fi

if is_installed zoxide; then
  eval "$(zoxide init zsh)"
  alias cd='z'
fi

if is_installed starship; then
  eval "$(starship init zsh)"
fi

if is_installed direnv; then
  eval "$(direnv hook zsh)"
fi

if is_installed fzf; then

if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

if cmd_exists bat; then
  PREVIEWER='bat --style=numbers --color=always --pager=never'
else
  PREVIEWER='cat'
fi

export FZF_DEFAULT_OPTS="--style full \
--height 90% \
--border sharp \
--input-border sharp \
--list-border sharp \
--layout reverse \
--info right \
--prompt '> ' \
--pointer '┃' \
--marker '│' \
--separator '──' \
--scrollbar '│' \
--preview-window='border-sharp' \
--preview-window='bottom:50%' \
--preview-label=' PREVIEW ' \
--border-label=' FILES ' \
--tabstop=2 \
--color=16 \
--preview '${PREVIEWER} {}'"

export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color \
bg+:0,\
bg:-1,\
preview-bg:-1,\
selected-bg:0,\
fg:7,\
fg+:6,\
hl:7:underline,\
hl+:10:underline,\
header:3,\
info:8,\
query:13,\
gutter:-1,\
pointer:6,\
marker:14,\
prompt:2,\
spinner:4,\
label:7,\
preview-label:0,\
separator:0,\
border:0,\
list-border:0,\
preview-border:0,\
input-border:8"

function finst() {
  fzpkgs="$(pkg list-all | tr '/' ' '  | grep -v installed | grep -v Listing | awk '{print $1}' | fzf --preview 'apt-cache show {}')"
  if [ -z "$fzpkgs" ]; then
    echo "No package selected."
  else
    pkg install -y "$fzpkgs"
  fi
}

source <(fzf --zsh)
fi

if is_droid; then
    zieces "droid"
fi

