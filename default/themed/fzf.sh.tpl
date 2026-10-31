export _FZF_COLORS_="\
bg+:{{ fzf_ui_selection_bg }},\
bg:-1,\
preview-bg:{{ background }},\
fg+:strip:{{ fzf_ui_accent_fg }}:bold,\
fg:regular,\
hl:-1:bold:underline,\
hl+:{{ fzf_ui_match_fg }}:bold:underline,\
info:{{ fzf_ui_muted_fg }},\
query:{{ fzf_status_warning_fg }},\
gutter:regular:{{ background }},\
pointer:regular:{{ fzf_ui_cursor_fg }}:bold,\
marker:{{ fzf_status_warning_fg }},\
prompt:{{ fzf_ui_accent_fg }},\
spinner:{{ dark_foreground }},\
header:{{ fzf_ui_heading_fg }},\
header-label:{{ dark_foreground }},\
footer:{{ fzf_status_info_fg }},\
footer-label:{{ dark_foreground }},\
input-label:{{ dark_foreground }},\
list-label:{{ dark_foreground }},\
preview-label:{{ dark_foreground }},\
label:{{ fzf_ui_muted_fg }},\
preview-label:{{ lighter_background }},\
separator:{{ fzf_ui_separator_fg }},\
border:{{ fzf_ui_border_fg }},\
list-border:{{ fzf_ui_border_fg }},\
preview-border:{{ fzf_ui_border_fg }},\
input-border:{{ fzf_ui_border_fg }},\
nomatch:strip:{{ dark_foreground }}:italic"

export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"
