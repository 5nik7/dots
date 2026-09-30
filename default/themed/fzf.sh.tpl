export _FZF_COLORS_="\
bg+:-1,\
bg:-1,\
preview-bg:{{ dark_background }},\
fg+:strip:{{ accent }}:bold,\
fg:regular,\
hl:{{ selection_foreground }}:underline,\
hl+:{{ bright_green }}:bold:underline,\
info:{{ muted }},\
query:{{ warning }},\
gutter:regular:{{ background }},\
pointer:regular:{{ accent }}:bold,\
marker:{{ warning }},\
prompt:{{ accent }},\
spinner:{{ dark_foreground }},\
header:{{ hint }},\
header-label:{{ dark_foreground }},\
footer:{{ info }},\
footer-label:{{ dark_foreground }},\
input-label:{{ dark_foreground }},\
list-label:{{ dark_foreground }},\
preview-label:{{ dark_foreground }},\
label:{{ muted }},\
preview-label:{{ lighter_background }},\
separator:{{ background }},\
border:{{ lighter_background }},\
list-border:{{ lighter_background }},\
preview-border:{{ dark_background }},\
input-border:{{ lighter_background }},\
nomatch:strip:{{ dark_foreground }}:italic"

export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"
