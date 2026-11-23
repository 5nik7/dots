# Sourced inside fzf-tab's completion widget for the literal argument "nf".
# Keep the plugin's terminal frontend. It needs no per-row compadd metadata:
# the hidden hex field identifies a glyph, including aliases with different names.
local _ftb_curcontext=complete:nf:icons _ftb_query=''
local -a _ftb_headers=('Tab: mark  Enter: insert  Esc: cancel') _ftb_groups=() _ftb_compcap
local continuous_trigger='' print_query='' accept_line=''
local -a choices
local record point glyph joined=''
_ftb_finish=1
compstate[list]=''
compstate[insert]=''
local help=$(command fzf --help 2>/dev/null)
local -a flags
-ftb-zstyle -a fzf-flags flags || flags=()
flags+=(--ansi --multi --no-preview --delimiter=$'\t' --with-nth=2.. --nth=1.. --tabstop=2
  --bind='tab:toggle+down,btab:toggle+up,enter:accept,esc:abort,<:put,>:put')
local color=never
if _dots_completion_use_color; then color=always; flags+=(--color='fg+:-1:regular')
else flags+=(--color=bw)
fi
if [[ $help == *--freeze-left* ]]; then flags+=(--freeze-left=1)
else flags+=(--no-hscroll)
fi
# Read the cached release once, and avoid opening an empty menu on a missing index.
local -a rows
rows=("${(@f)$(DOTS_COLOR=$color command python3 -B "$DOTS/lib/dots/fonts/glyphs.py" completion)}") || return 0
[[ -n ${rows[1]:-} ]] || return 0
# The frontend sizes the menu from the candidate and header counts.
_ftb_compcap=("${(@)rows%%$'\t'*}")
choices=("${(@f)$(
  # These overrides live only in the picker subprocess. Keep the configured
  # frontend, theme and size, including when fzf-tab uses a tmux popup.
  zstyle ":fzf-tab:$_ftb_curcontext" fzf-flags "${flags[@]}"
  zstyle ":fzf-tab:$_ftb_curcontext" switch-group '<' '>'
  zstyle ":fzf-tab:$_ftb_curcontext" popup-smart-tab no
  print -rl -- $'\t'"$_ftb_headers[1]" "${rows[@]}" | -ftb-fzf
)}") || return 0
# fzf-tab prints its query and expect key before the accepted original records.
for record in "${choices[@]:2}"; do
  point=${record%%$'\t'*}
  [[ $record == *$'\t'* && $point == [0-9A-F](#c1,6) ]] || return 1
  printf -v glyph '%b' "\\U${(l:8::0:)point}"
  joined+=$glyph
done
[[ -n $joined ]] || return 0
builtin compadd -U -S '' -- "$joined"
compstate[insert]=1
