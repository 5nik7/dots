# Dots semantic Leaf theme, adapted from config/leaf/themes/catppuccin-mocha.toml.
base = "{{ leaf_base }}"
syntax = "dots.tmTheme"

[ui]
toc_bg = "{{ dark_background }}"
toc_border = "{{ muted }}"
content_bg = "{{ background }}"
scrollbar_hover = "{{ yellow }}"

status_bg = "{{ dark_background }}"
status_separator = "{{ dark_foreground }}"

status_brand_fg = "{{ leaf_badge_foreground }}"
status_brand_bg = "{{ yellow }}"

status_filename_fg = "{{ foreground }}"
status_filename_bg = "{{ lighter_background }}"

status_watch_fg = "{{ green }}"
status_watch_bg = "{{ lighter_background }}"

status_reloaded_fg = "{{ leaf_badge_foreground }}"
status_reloaded_bg = "{{ green }}"

status_search_fg = "{{ yellow }}"
status_search_bg = "{{ lighter_background }}"

status_success_fg = "{{ green }}"
status_success_bg = "{{ lighter_background }}"

status_warning_fg = "{{ yellow }}"

status_error_fg = "{{ red }}"
status_error_bg = "{{ lighter_background }}"

status_shortcut_fg = "{{ dark_foreground }}"
status_percent_fg = "{{ yellow }}"

toc_hover_fg = "{{ foreground }}"
toc_header_fg = "{{ dark_foreground }}"

toc_active_bg = "{{ lighter_background }}"
toc_inactive_bg = "{{ dark_background }}"

toc_accent = "{{ orange }}"

toc_index_inactive = "{{ dark_foreground }}"

toc_primary_active = "{{ foreground }}"
toc_primary_inactive = "{{ light_foreground }}"

toc_secondary_inactive = "{{ dark_foreground }}"

toc_secondary_text_active = "{{ foreground }}"
toc_secondary_text_inactive = "{{ dark_foreground }}"


[markdown]
search_highlight_bg = "{{ selection }}"
search_match_bg = "{{ yellow }}"

code_gutter = "{{ dark_foreground }}"

blockquote_marker = "{{ dark_foreground }}"

list_level_1 = "{{ green }}"
list_level_2 = "{{ blue }}"
list_level_3 = "{{ accent }}"

ordered_list = "{{ yellow }}"

table_border = "{{ muted }}"
table_separator = "{{ muted }}"
table_header = "{{ yellow }}"
table_cell = "{{ foreground }}"

heading_1 = "{{ yellow }}"
heading_2 = "{{ green }}"
heading_3 = "{{ blue }}"
heading_4 = "{{ accent }}"
heading_other = "{{ orange }}"

heading_underline = "{{ muted }}"

code_frame = "{{ muted }}"
code_label = "{{ dark_foreground }}"

inline_code_fg = "{{ orange }}"
inline_code_bg = "{{ lighter_background }}"

rule = "{{ muted }}"

link_icon = "{{ blue }}"
link_text = "{{ blue }}"
link_hover = "{{ bright_blue }}"

blockquote_text = "{{ light_foreground }}"

text = "{{ foreground }}"
strong_text = "{{ bright_foreground }}"

latex_inline_fg = "{{ accent }}"
latex_inline_bg = "{{ lighter_background }}"
latex_block_fg = "{{ accent }}"

mermaid_keyword = "{{ orange }}"
mermaid_arrow = "{{ blue }}"
mermaid_label = "{{ green }}"
mermaid_block_fg = "{{ foreground }}"

mark_fg = "{{ foreground }}"
mark_bg = "{{ selection }}"

task_checked = "{{ green }}"
task_unchecked = "{{ dark_foreground }}"

alert_note = "{{ blue }}"
alert_tip = "{{ green }}"
alert_important = "{{ accent }}"
alert_warning = "{{ yellow }}"
alert_caution = "{{ red }}"

footnote_ref = "{{ blue }}"
footnote_text = "{{ light_foreground }}"
