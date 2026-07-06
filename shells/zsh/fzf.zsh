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
export _PREVIEW_="preview.zsh"

export FZF_DEFAULT_OPTS="$_FZF_OPTS_ --bind=$_FZF_BINDS_ --preview-window=$_FZF_PREVIEW_POS_ --preview='$_PREVIEW_ {}'"

# _fz_write_rc() {
#   local rc=~/.fzfrc
#   if [[ -f $rc ]]; then
#   print -r -- "$FZF_DEFAULT_OPTS" | sed 's/ --/\n--/g' >! "$rc"
# else
#   print -r -- "$FZF_DEFAULT_OPTS" | sed 's/ --/\n--/g' > "$rc"
#   fi
#   echo "fzopt: wrote $rc"
# }
