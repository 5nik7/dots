# Invoked only by the guarded Dots FZF-tab adapter, never a public command.
# Native FZF-tab owns filtering, group state and the lifetime of its temp files.
emulate -L zsh -o extendedglob
local upstream=$1 heading=$2
shift 2
local -i header_lines=${2:-0} i
local output marker code line before after
local -a rows
output=$(command "$commands[zsh]" -f "$upstream" "$@") || exit $?
if [[ -z $heading || $heading != <->(\;<->)# ]] || (( header_lines == 0 )); then
  print -r -- "$output"
  exit 0
fi
rows=("${(@f)output}")
# Native reload returns only the selected group's candidates. Their first SGR
# is its identity, independent of the semantic colors inside each visible row.
marker=${(M)rows[$((header_lines+1))]#$'\e['[0-9\;]#m}
if [[ -n $marker ]]; then
  code=$'\e[0;'${heading}m
  for (( i=1; i<=header_lines; i++ )); do
    line=${rows[i]}
    # Match the group marker followed by our type style, not a label's text.
    # Other groups may intentionally use exactly the same semantic color.
    if [[ $line == *"$marker"$'\e[0;'[0-9\;]#m* ]]; then
      before=${line%%"$marker"$'\e[0;'[0-9\;]#m*}
      after=${line#*"$marker"$'\e[0;'[0-9\;]#m}
      rows[i]=$before$marker$code$after
    fi
  done
fi
print -rl -- "${rows[@]}"
