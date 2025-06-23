transparent="-1"
rosewater="#f5e0dc"
flamingo="#f2cdcd"
pink="#f5c2e7"
mauve="#cba6f7"
red="#f38ba8"
maroon="#eba0ac"
peach="#fab387"
yellow="#f9e2af"
green="#a6e3a1"
teal="#94e2d5"
sky="#89dceb"
sapphire="#74c7ec"
blue="#89b4fa"
lavender="#b4befe"
text="#cdd6f4"
subtext1="#bac2de"
subtext0="#a6adc8"
overlay2="#9399b2"
overlay1="#7f849c"
overlay0="#6c7086"
surface2="#585b70"
surface1="#45475a"
surface0="#313244"
base="#1e1e2e"
mantle="#181825"
crust="#11111b"

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
bg+:${mantle},\
bg:${transparent},\
preview-bg:${transparent},\
selected-bg:${mantle},\
fg:${subtext0},\
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
