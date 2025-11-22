if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

export _FZF_OPTS_="\
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

export FZF_DEFAULT_OPTS="$_FZF_OPTS_"

zource "$THEMEDIR/fzf.zsh"

export _FZF_PREVIEW_POS_='bottom:hidden:50%:border-sharp'

export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS \
--preview-window='$_FZF_PREVIEW_POS_'"

export _PREVIEW_="preview.zsh"
export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS \
--preview '$_PREVIEW_ {}'"



