# Singular theme CLI. Legacy plural routes retain their positional interfaces.
source "$DT_LIB/core.bash"
source "$DT_LIB/../ui.bash"
dt_current_id() {
  dt_selected selection || return
  REPLY=$DT_THEME-$DT_FLAVOR
  [[ -d $DT_ROOT/$REPLY || -d $DT_USER_THEMES/$REPLY ]] || REPLY=$DT_THEME
}
dt_theme_ids() {
  local path name
  local -A seen=()
  for path in "$DT_ROOT/"*/colors.toml "$DT_USER_THEMES/"*/colors.toml; do
    [[ -f $path && ! -L $path ]] || continue
    name=${path%/colors.toml}; name=${name##*/}
    dt_theme_id "$name" || continue
    [[ ! ${seen[$name]:-} ]] || continue
    seen[$name]=1; printf '%s\n' "$name"
  done
  [[ ! -d $DT_ROOT/pywal16-current ]] || printf 'pywal16-current\n'
}
dt_command() {
  local action=${1:-help} name key value id dry=0 background=0
  (($# == 0)) || shift
  case $action in
    help) printf '%s\n' 'dots theme: list, show ID, current, dir [ID], color COLOR [FORMAT] [--theme ID]' '  set ID [--background] [--dry-run], refresh, init [--shell SHELL], switcher' '  install URL [--name ID], update ID|--all, remove ID, bg COMMAND';;
    list) (($# == 0)) || return 2; dt_theme_ids | LC_ALL=C sort ;;
    current) (($# == 0)) || return 2; dt_current_id && printf '%s\n' "$REPLY" ;;
    dir)
      (($# <= 1)) || return 2
      if (($#)); then id=$1; else dt_current_id || return; id=$REPLY; fi
      dt_find_theme "$id" || { dt_error 'theme not found'; return 1; }
      printf '%s\n' "$DT_THEME_DIR" ;;
    show)
      (($# == 1)) || return 2
      dt_load "$1" || return
      dots::heading "$DT_ID ($DT_MODE)"
      for key in "${!DT_SEMANTIC[@]}"; do printf '%s\t%s\n' "$key" "${DT_SEMANTIC[$key]}"; done | LC_ALL=C sort ;;
    color)
      local -a args=()
      id=''
      while (($#)); do
        case $1 in --theme) (($# >= 2)) || return 2; id=$2; shift 2 ;; *) args+=("$1"); shift ;; esac
      done
      ((${#args[@]} >= 1 && ${#args[@]} <= 2)) || return 2
      if [[ ! $id ]]; then dt_current_id || return; id=$REPLY; fi
      dt_load "$id" || return
      key=${args[0]}; value=${DT_SEMANTIC[$key]:-${DT_COLORS[$key]:-}}
      [[ $value ]] || { dt_error 'unknown color'; return 1; }
      if [[ $key == mode ]]; then printf '%s\n' "$value"
      else dt_value "$key" "${args[1]:-hex}" "$value" && printf '%s\n' "$REPLY"; fi ;;
    init) set -- init "$@"; source "$DT_LIB/cli.bash" ;;
    set|refresh)
      if [[ $action == refresh ]]; then (($# == 0)) || return 2; dt_current_id || return; id=$REPLY; export DOTS_THEME_REFRESH=1
      else (($# >= 1)) || return 2; id=$1; shift; fi
      while (($#)); do
        case $1 in --dry-run) dry=1 ;; --background) background=1 ;; *) return 2 ;; esac
        shift
      done
      dt_load "$id" || return
      source "$DT_LIB/state.bash"
      dt_state_preflight || return
      if ((dry)); then
        printf 'Select %s\nPublish %s\n' "$id" "$DT_ACTIVE"
        for name in "${DT_CONNECT_TARGETS[@]}"; do printf 'Connect %s\n' "$name"; done
        printf 'Reload available Termux, tmux and Kitty adapters\n'
        (( ! background )) || printf 'Apply the selected theme background\n'
        return 0
      fi
      dt_set "$id" || return
      if ((background)); then source "$DT_LIB/backgrounds.bash"; dt_bg select; fi ;;
    switcher)
      (($# == 0)) || return 2
      command -v fzf >/dev/null || { dt_error 'theme switcher requires fzf'; return 1; }
      id=$(dt_theme_ids | LC_ALL=C sort | fzf --prompt='Theme: ' --preview='dots theme show {}') || return
      [[ $id ]] && dt_command set "$id" ;;
    install|update|remove) source "$DT_LIB/install.bash"; dt_git_theme "$action" "$@" ;;
    bg) source "$DT_LIB/backgrounds.bash"; dt_bg "$@" ;;
    *) return 2 ;;
  esac
}
if dt_command "$@"; then return 0
else
  status=$?
  ((status != 2)) || dt_error 'invalid arguments; see dots theme --help'
  return "$status"
fi
