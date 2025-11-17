if is_droid; then
  # preview_pos='bottom:hidden:50%:border-top'
  preview_pos='bottom:hidden:50%:border-sharp'
else
  preview_pos='bottom:hidden:50%:border-sharp'
  # preview_pos='right:50%:border-left'
fi

if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

export _PREVIEW_="$HOME/dots/shells/zsh/preview.zsh"
local extract="
local in=\${\${\"\$(<{f})\"%\$'\0'*}#*\$'\0'}
local -A ctxt
for entry in \${(@ps:\2:)CTXT}; do
      local key=\${entry%%=*}
      local value=\${entry#*=}
      ctxt[\$key]=\$value
done
local realpath=\${ctxt[IPREFIX]}\${ctxt[hpre]}\$in
realpath=\${(Qe)~realpath}
"
zstyle ':fzf-tab:complete:*:*' fzf-flags --preview=$extract';$_PREVIEW_ $realpath'

# --preview-label=' PREVIEW ' \
# --border-label=' FILES ' \
export FZF_DEFAULT_OPTS="\
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
--preview-window='$preview_pos' \
--bind='\
Ctrl-X:toggle-preview,\
up:up-match,\
down:down-match,\
alt-r:toggle-raw' \
--preview '$_PREVIEW_ {}'"


