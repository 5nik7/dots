[mgr]
cwd = { fg = "{{ accent }}" }
marker_copied = { fg = "{{ green }}", bg = "{{ green }}" }
marker_cut = { fg = "{{ red }}", bg = "{{ red }}" }
marker_selected = { fg = "{{ yellow }}", bg = "{{ yellow }}" }
border_style = { fg = "{{ lighter_background }}" }
[tabs]
active = { fg = "{{ darker_background }}", bg = "{{ accent }}" }
inactive = { fg = "{{ darker_background }}", bg = "{{ selection }}" }
[status]
progress_normal = { fg = "{{ accent }}", bg = "{{ selection }}" }
progress_error = { fg = "{{ red }}", bg = "{{ selection }}" }
[indicator]
padding = { open = "█", close = "█" }
[mode]
normal_main = { fg = "{{ darker_background }}", bg = "{{ accent }}", bold = true }
select_main = { fg = "{{ darker_background }}", bg = "{{ green }}", bold = true }
unset_main = { fg = "{{ darker_background }}", bg = "{{ yellow }}", bold = true }
