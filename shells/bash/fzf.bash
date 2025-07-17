transparent="-1"
rosewater=$(rosewater)
flamingo=$(flamingo)
pink=$(pink)
mauve=$(mauve)
red=$(red)
maroon=$(maroon)
peach=$(peach)
yellow=$(yellow)
green=$(green)
teal=$(teal)
sky=$(sky)
sapphire=$(sapphire)
blue=$(blue)
lavender=$(lavender)
text=$(text)
subtext1=$(subtext1)
subtext0=$(subtext0)
overlay2=$(overlay2)
overlay1=$(overlay1)
overlay0=$(overlay0)
surface2=$(surface2)
surface1=$(surface1)
surface0=$(surface0)
base=$(base)
mantle=$(mantle)
crust=$(crust)

if is_droid; then
  # preview_pos='bottom:hidden:50%:border-top'
  preview_pos='bottom:hidden:50%:border-sharp'
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
bg+:${mantle},\
bg:${transparent},\
preview-bg:${transparent},\
selected-bg:${mantle},\
fg:$subtext0,\
fg+:${lavender}:bold:reverse,\
hl:${green}:underline,\
hl+:${green}:bold:underline:reverse,\
info:${surface1},\
query:${text},\
gutter:${transparent},\
pointer:${base},\
marker:${yellow},\
prompt:${surface1},\
spinner:${surface1},\
label:${surface2},\
preview-label:${surface0},\
separator:${base},\
border:${surface0},\
list-border:${surface0},\
preview-border:${surface0},\
input-border:${surface0}"
