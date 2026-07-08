transparent="-1"

export _FZF_COLORS_="\
bg+:${transparent},\
bg:${transparent},\
preview-bg:${mantle[hex]},\
fg+:strip:${mauve[hex]}:bold,\
fg:regular,\
hl:${sky[hex]}:underline,\
hl+:${green[hex]}:bold:underline,\
info:${surface2[hex]},\
query:${yellow[hex]},\
gutter:regular:${surface0[hex]},\
pointer:regular:${surface2[hex]}:bold,\
marker:${yellow[hex]},\
prompt:${mauve[hex]},\
spinner:${surface1[hex]},\
label:${surface2[hex]},\
preview-label:${surface0[hex]},\
separator:${base[hex]},\
border:${surface0[hex]},\
list-border:${surface0[hex]},\
preview-border:${mantle[hex]},\
input-border:${surface0[hex]},\
nomatch:strip:${surface1[hex]}:italic"

export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"
