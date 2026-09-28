#!/usr/bin/env bash
# Private argv/result bridge for Python consumers of the shared UI adapter.
# stdin is the keyboard, stderr the visible terminal, stdout the exact selection.
ui_lib=${BASH_SOURCE[0]%/*}
source "$ui_lib/ui.bash"
source "$ui_lib/interactive.bash"
exec 3>&2
backend=${1:-}; shift || exit 2
if [[ $backend == detect ]]; then
  (($# == 0)) || exit 2
  dots::interactive_backend
  printf '%s\n' "$REPLY"
  exit
fi
(($# >= 4)) || exit 2
kind=$1 header=$2 initial=$3; shift 3
[[ $kind == filter || $kind == choose ]] || exit 2
case $backend in
  gum) dots::gum_pick "$kind" "$header" "$initial" "$@" || exit ;;
  fzf)
    if [[ $kind == filter ]]; then
      dots::style 3
      flags=(--no-multi --prompt='Filter: ' --header="$header" --bind='esc:abort,ctrl-c:abort')
      [[ $DOTS_UI_RESET ]] || flags+=(--color=bw)
      [[ $DOTS_UI_INFO != '[i]' ]] || flags+=(--no-unicode)
      if REPLY=$(printf '%s\n' "$@" | FZF_DEFAULT_OPTS='' FZF_DEFAULT_OPTS_FILE='' dots::interactive_run fzf "${flags[@]}"); then
        [[ $REPLY ]] || exit 130
      else
        status=$?
        ((status == 130)) && exit 130
        dots::error 'Selector failed.'; exit 1
      fi
    else
      dots::numbered_pick "$header" 1 "$@" >&3 || exit
    fi ;;
  plain)
    default=''; [[ $kind != choose ]] || default=1
    dots::numbered_pick "$header" "$default" "$@" >&3 || exit ;;
  *) exit 2 ;;
esac
# Validate even plain/tool selections before returning to the caller.
for choice in "$@"; do
  if [[ $choice == "$REPLY" ]]; then printf '%s\n' "$REPLY"; exit 0; fi
done
dots::error 'Selector returned an unknown choice.'
exit 1
