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
export FZF_DEFAULT_OPTS="--style default \
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

export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color \
bg+:${surface0},\
bg:${transparent},\
preview-bg:${transparent},\
fg:${subtext0},\
fg+:${text},\
hl:${blue}:bold:underline,\
hl+:${blue}:bold:underline,\
info:${surface2},\
query:${mauve},\
gutter:${surface0},\
pointer:${surface0},\
marker:${yellow},\
prompt:${surface1},\
spinner:${surface1},\
label:${surface2},\
preview-label:${surface0},\
separator:${base},\
border:${surface0},\
list-border:${surface0},\
preview-border:${surface0},\
input-border:${surface0},\
nomatch:strip:${surface1}:italic"
