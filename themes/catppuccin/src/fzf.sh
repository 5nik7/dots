rosewater=$(catppuccin rosewater hex)
flamingo=$(catppuccin flamingo hex)
pink=$(catppuccin pink hex)
mauve=$(catppuccin mauve hex)
red=$(catppuccin red hex)
maroon=$(catppuccin maroon hex)
peach=$(catppuccin peach hex)
yellow=$(catppuccin yellow hex)
green=$(catppuccin green hex)
teal=$(catppuccin teal hex)
sky=$(catppuccin sky hex)
sapphire=$(catppuccin sapphire hex)
blue=$(catppuccin blue hex)
lavender=$(catppuccin lavender hex)
text=$(catppuccin text hex)
subtext1=$(catppuccin subtext1 hex)
subtext0=$(catppuccin subtext0 hex)
overlay2=$(catppuccin overlay2 hex)
overlay1=$(catppuccin overlay1 hex)
overlay0=$(catppuccin overlay0 hex)
surface2=$(catppuccin surface2 hex)
surface1=$(catppuccin surface1 hex)
surface0=$(catppuccin surface0 hex)
base=$(catppuccin base hex)
mantle=$(catppuccin mantle hex)
crust=$(catppuccin crust hex)

transparent="-1"

_FZF_COLORS_="\
bg+:${transparent},\
bg:${transparent},\
preview-bg:$mantle,\
fg+:strip:${mauve}:bold,\
fg:regular,\
hl:${sky}:underline,\
hl+:${green}:bold:underline,\
info:${surface2},\
query:${yellow},\
gutter:regular:${surface0},\
pointer:regular:${surface2}:bold,\
marker:${yellow},\
prompt:${mauve},\
spinner:${surface1},\
label:${surface2},\
preview-label:${surface0},\
separator:${base},\
border:${surface0},\
list-border:${surface0},\
preview-border:${mantle},\
input-border:${surface0},\
nomatch:strip:${surface1}:italic"
