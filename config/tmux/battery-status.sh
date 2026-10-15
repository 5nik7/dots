#!/usr/bin/env bash
# Tmux-format data, not terminal ANSI. The battery checkout owns icons/thresholds.
# An empty line (rather than no output) clears tmux's previous successful result.
empty() {
  if [[ ${slot:-0} == 1 ]]; then printf '#[fg=%s]󰂑 ?%%  #[default]\n' "$muted"; else printf '\n'; fi
  exit 0
}
slot=0 red=red yellow=yellow green=green muted=brightblack
if [[ ${1:-} == --slot && $# == 5 ]]; then
  for color in "${@:2}"; do
    [[ $color =~ ^(\#[a-fA-F0-9]{6}|default|(bright)?(black|red|green|yellow|blue|magenta|cyan|white))$ ]] || empty
  done
  slot=1 red=$2 yellow=$3 green=$4 muted=$5
elif (( $# )); then
  empty
fi

[[ -n ${HOME:-} && -r $HOME/repos/battery/battery ]] || empty
output=$(bash "$HOME/repos/battery/battery" \
  --format '{color}{icon} {percent}{reset}' \
  --color always --color-by percentage --no-newline 2>/dev/null) || empty

# Accept only the single colored icon/percentage record we requested. Reject
# control characters and tmux format introducers instead of forwarding them.
pattern=$'^\033\\[(31|32|33)m([^[:space:][:cntrl:]#]+) ([0-9]{1,3})%\033\\[0m$'
[[ $output =~ $pattern ]] || empty
color=${BASH_REMATCH[1]}
icon=${BASH_REMATCH[2]}
percentage=${BASH_REMATCH[3]}
# Nerd Font glyphs are four bytes when the caller uses the C locale.
if [[ ${#icon} -gt 4 ]] || (( 10#$percentage > 100 )); then
  empty
fi
case $color in
  31) color=$red ;;
  32) color=$green ;;
  33) color=$yellow ;;
esac
if (( slot )); then
  printf '#[fg=%s]%s %-4s#[default]\n' "$color" "$icon" "$((10#$percentage))%"
else
  printf '#[fg=%s]%s %s%%#[default]\n' "$color" "$icon" "$percentage"
fi
