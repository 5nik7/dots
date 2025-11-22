if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

_FZF_OPTS_="\
--style default \
--layout reverse \
--height ~90% \
--border none \
--info hidden \
--prompt ' 󰅂 ' \
--pointer '▎' \
--marker '▎' \
--gutter '▎' \
--gutter-raw '▎' \
--no-separator \
--no-scrollbar \
--bind='\
Ctrl-X:toggle-preview,\
up:up-match,\
down:down-match,\
alt-r:toggle-raw'"
zource "$THEMEDIR/fzf.zsh"
_FZF_PREVIEW_POS_='bottom:hidden:50%:border-sharp'
export _PREVIEW_="preview.zsh"

export FZF_DEFAULT_OPTS="$_FZF_OPTS_ $_FZF_COLORS_ --preview-window='$_FZF_PREVIEW_POS_' --preview '$_PREVIEW_ {}'"

# export FZF_CACHE_DIR="$HOME/.cache/fzf"
# export FZF_CACHE_OPTS="$FZF_CACHE_DIR/opts"

# mkdir -pv "$FZF_CACHE_DIR"
# rm -fr "$FZF_CACHE_OPTS"
# echo "export FZF_DEFAULT_OPTS=\"${_FZF_DEFAULT_OPTS_}\"" >! "$FZF_CACHE_OPTS"

function fzpos() {
  export FZF_DEFAULT_OPTS=$(echo "$FZF_DEFAULT_OPTS" |
  sed "s/--preview-window='[^']*'/--preview-window='$@'/")
}

function fzopt() {
  local key value
  key=$1
  value=$2
    export FZF_DEFAULT_OPTS=$(echo "$FZF_DEFAULT_OPTS" |
      sed "s|--${key} [^ ]*|--${key} ${value}|")
}
