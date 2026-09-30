if command -v fd &>/dev/null; then
  export FZF_DEFAULT_COMMAND='fd --type f --color=always --ignore-case --strip-cwd-prefix --hidden --exclude .git'
fi

export _FZF_OPTS_="\
--style=default \
--layout=reverse \
--height=~90% \
--border=none \
--info=hidden \
--prompt=' 󰅂 ' \
--pointer='▎' \
--marker='▎' \
--gutter='▎' \
--gutter-raw='▎' \
--no-separator \
--no-scrollbar \
-x \
--smart-case \
--ansi"

export _FZF_BINDS_="\
Ctrl-X:toggle-preview,\
up:up-match,\
down:down-match,\
alt-r:toggle-raw"

# so "$THEMECONF/fzf.sh"
export _FZF_PREVIEW_POS_='right:hidden:50%:wrap-word:border-left'
if has zsh; then export _PREVIEW_="preview.zsh"
else export _PREVIEW_="bash \"$DOTS/shells/shared/preview.sh\""; fi

export FZF_DEFAULT_OPTS="$_FZF_OPTS_ --bind=$_FZF_BINDS_ --preview-window=$_FZF_PREVIEW_POS_ --preview='$_PREVIEW_ {}'"

