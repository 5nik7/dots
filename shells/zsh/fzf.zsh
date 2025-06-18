transparent='-1'

if is_droid; then
  preview_pos='bottom:hidden:50%:border-top'
  else
  preview_pos='right:hidden:50%:border-left'
fi

if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

# --preview-label=' PREVIEW ' \
# --border-label=' FILES ' \
export FZF_DEFAULT_OPTS="--style minimal \
--layout reverse \
--height ~90% \
--min-height 10+ \
--border none \
--info hidden \
--prompt ' > ' \
--pointer '' \
--marker '│' \
--no-separator \
--no-scrollbar \
--preview-window='$preview_pos' \
--bind='Ctrl-X:toggle-preview' \
--preview 'fzf-preview.sh {}'"

export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color \
bg+:$(flavor mantle),\
bg:$transparent,\
preview-bg:$transparent,\
selected-bg:$(flavor mantle),\
fg:$(flavor subtext0),\
fg+:$(flavor lavender):bold:reverse,\
hl:$(flavor green):underline,\
hl+:$(flavor green):bold:underline:reverse,\
info:$(flavor surface1),\
query:$(flavor text),\
gutter:$transparent,\
pointer:$(flavor base),\
marker:$(flavor yellow),\
prompt:$(flavor surface1),\
spinner:$(flavor surface1),\
label:$(flavor surface2),\
preview-label:$(flavor surface0),\
separator:$(flavor base),\
border:$(flavor surface0),\
list-border:$(flavor surface0),\
preview-border:$(flavor surface0),\
input-border:$(flavor surface0)"
