if is_droid; then
  preview_pos='bottom:hidden:50%'
  else
  preview_pos='right:hidden:50%'
fi

if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

# --preview-label=' PREVIEW ' \
# --border-label=' FILES ' \
export FZF_DEFAULT_OPTS="--style full \
--height ~90% \
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
--preview-window='$preview_pos' \
--tabstop=2 \
--bind='Ctrl-X:toggle-preview' \
--preview 'fzf-preview.sh {}'"

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
