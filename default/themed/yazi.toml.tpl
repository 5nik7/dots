[mgr]
cwd = { fg = "{{ yazi_ui_accent_fg }}" }
marker_copied = { fg = "{{ green }}", bg = "{{ green }}" }
marker_cut = { fg = "{{ red }}", bg = "{{ red }}" }
marker_selected = { fg = "{{ yellow }}", bg = "{{ yellow }}" }
border_style = { fg = "{{ lighter_background }}" }
[tabs]
active = { fg = "{{ darker_background }}", bg = "{{ yazi_ui_accent_fg }}" }
inactive = { fg = "{{ darker_background }}", bg = "{{ selection }}" }
[status]
progress_normal = { fg = "{{ yazi_ui_accent_fg }}", bg = "{{ selection }}" }
progress_error = { fg = "{{ red }}", bg = "{{ selection }}" }
[indicator]
padding = { open = "█", close = "█" }
[mode]
normal_main = { fg = "{{ darker_background }}", bg = "{{ yazi_ui_accent_fg }}", bold = true }
select_main = { fg = "{{ darker_background }}", bg = "{{ green }}", bold = true }
unset_main = { fg = "{{ darker_background }}", bg = "{{ yellow }}", bold = true }

{{ file_icons_yazi }}
