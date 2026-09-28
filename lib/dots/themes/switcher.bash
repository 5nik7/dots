# Explicit interactive selection. All preview/review paths remain read-only.
dt_switcher() (
  [[ -t 0 && -t 1 ]] || {
    dt_error 'theme switcher needs terminal input and output; use dots theme list and dots theme set ID'
    return 1
  }
  # Captured selector results must not capture the visible interface.
  exec 3>&1
  trap 'exit 130' INT
  source "$DT_LIB/../interactive.bash"
  local catalog id candidate backend action preview status
  local -a ids=() flags=()
  catalog=$(dt_theme_ids | LC_ALL=C sort) || return 1
  [[ $catalog ]] || { dt_error 'no themes available; use dots theme list'; return 1; }
  while IFS= read -r id; do ids+=("$id"); done <<< "$catalog"
  dots::interactive_backend; backend=$REPLY
  while :; do
    case $backend in
      gum) dots::gum_pick filter 'Select a theme to preview' '' "${ids[@]}" || return; id=$REPLY ;;
      fzf)
        dots::style 3
        flags=(--no-multi --prompt='Theme: ' --bind='esc:abort,ctrl-c:abort')
        [[ $DOTS_UI_RESET ]] || flags+=(--color=bw)
        [[ $DOTS_UI_INFO != '[i]' ]] || flags+=(--no-unicode)
        printf -v preview '%q theme show {}' "${DT_LIB%/lib/dots/themes}/bin/dots"
        if id=$(printf '%s\n' "${ids[@]}" | SHELL=$BASH FZF_DEFAULT_OPTS='' FZF_DEFAULT_OPTS_FILE='' dots::interactive_run fzf "${flags[@]}" --preview="$preview"); then
          [[ $id ]] || return 130
        else
          status=$?
          ((status == 130)) && return 130
          dt_error 'theme selector failed; no theme was applied'; return 1
        fi ;;
      plain) dots::numbered_pick 'Select a theme to preview' '' "${ids[@]}" || return; id=$REPLY ;;
    esac
    candidate=''
    for action in "${ids[@]}"; do [[ $id != "$action" ]] || candidate=$id; done
    [[ $candidate ]] || { dt_error 'selector returned an unknown theme; no theme was applied'; return 1; }
    dt_command show "$candidate" || return 1
    dots::info 'Preview only; choose Apply to publish this theme.'
    if [[ $backend == gum ]]; then
      dots::gum_pick choose 'Theme action' Back Back Apply Cancel || return
    else
      dots::numbered_pick 'Theme action' 1 Back Apply Cancel || return
    fi
    case $REPLY in
      Back) continue ;;
      Cancel) dots::info 'Cancelled; no theme was applied.'; return 0 ;;
      Apply) dt_command set "$candidate"; return $? ;;
      *) dt_error 'selector returned an unknown action; no theme was applied'; return 1 ;;
    esac
  done
)
