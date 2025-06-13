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
--prompt '> ' \
--pointer '' \
--marker '│' \
--no-separator \
--no-scrollbar \
--preview-window='$preview_pos' \
--bind='Ctrl-X:toggle-preview' \
--preview 'fzf-preview.sh {}'"

export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color \
bg+:-1,\
bg:-1,\
preview-bg:-1,\
selected-bg:0,\
fg:15,\
fg+:6,\
hl:7:underline,\
hl+:10:underline,\
info:0,\
query:7,\
gutter:-1,\
pointer:14,\
marker:3,\
prompt:8,\
spinner:8,\
label:78,\
preview-label:0,\
separator:0,\
border:0,\
list-border:0,\
preview-border:0,\
input-border:8"
