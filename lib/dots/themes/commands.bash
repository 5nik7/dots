# Unified theme CLI. Existing full-ID routes and data-driven family queries.
source "$DT_LIB/core.bash" || return
source "$DT_LIB/views.bash"
source "$DT_LIB/../verbose.bash"
DOTS_OPERATION_VERBOSE=0
dt_error() { dots::error "dots theme: $*"; return 1; }
# backgrounds.bash also calls this helper with the bg route argument.
# shellcheck disable=SC2120
dt_help() { "${DT_LIB%/lib/dots/themes}/bin/dots" help theme "$@"; }
dt_list() {
  local id selected='' count=0
  if ! dots::human; then dt_theme_ids | LC_ALL=C sort; return; fi
  if dt_current_id 2>/dev/null; then selected=$REPLY; fi
  dots::heading 'Themes'
  while IFS= read -r id; do
    dots::style
    if [[ $id == "$selected" ]]; then
      printf '  %s%s%s  %s%s current%s\n' "$DOTS_UI_BLUE" "$id" "$DOTS_UI_RESET" "$DOTS_UI_GREEN" "$DOTS_UI_OK" "$DOTS_UI_RESET"
    else printf '  %s%s%s\n' "$DOTS_UI_BLUE" "$id" "$DOTS_UI_RESET"; fi
    ((count+=1))
  done < <(dt_theme_ids | LC_ALL=C sort)
  printf '\n  %s themes available\n' "$count"
}
dt_command() {
  local action=${1:-summary} name key value id dry=0 background=0 native=0
  local DOTS_OPERATION_VERBOSE=${DOTS_OPERATION_VERBOSE:-0}
  (($# == 0)) || shift
  case $action in
    help) dt_help ;;
    summary)
      dt_current_id || return
      dots::heading "Current theme: $REPLY"
      dt_load_native "$REPLY" && dt_native_preview || return
      printf '\nUse theme color NAME, theme set ID, or dots themes list.\n' ;;
    list)
      if (($# == 0)); then dt_list
      elif [[ $# == 1 && $1 == --families ]]; then dt_palette_list families
      elif [[ $# == 2 && $1 == --flavors ]]; then dt_palette_list flavors "$2"
      elif [[ $# == 1 && $1 == --flavors=* ]]; then dt_palette_list flavors "${1#*=}"
      else return 2; fi ;;
    current) (($# == 0)) || return 2; dt_current_id && printf '%s\n' "$REPLY" ;;
    dir)
      (($# <= 1)) || return 2
      if (($#)); then id=$1; else dt_current_id || return; id=$REPLY; fi
      dt_find_theme "$id" || { dt_error 'theme not found'; return 1; }
      printf '%s\n' "$DT_THEME_DIR" ;;
    show)
      id=''
      while (($#)); do
        case $1 in
          --native) native=1 ;;
          -*) return 2 ;;
          *) [[ ! $id ]] || return 2; id=$1 ;;
        esac
        shift
      done
      if [[ ! $id ]]; then dt_current_id || return; id=$REPLY; fi
      dt_find_theme "$id" || { dt_error 'unknown selectable theme ID'; return 1; }
      if ((native)); then dt_load_native "$id" && dt_native_preview; return; fi
      dt_load "$id" || return
      if dots::human; then
        dt_json | DOTS_COLOR="${DOTS_COLOR:-${dots_options[DOTS_COLOR]:-auto}}" python3 -B "$DT_LIB/file-colors.py" _show "$DT_THEME_DIR"
      else
        dots::heading "$DT_ID ($DT_MODE)"
        for key in "${!DT_SEMANTIC[@]}"; do printf '%s\t%s\n' "$key" "${DT_SEMANTIC[$key]}"; done | LC_ALL=C sort
      fi ;;
    color)
      local -a args=()
      id=''
      while (($#)); do
        case $1 in
          --theme) (($# >= 2)) && [[ -n $2 && $2 != -* ]] || return 2; id=$2; shift 2 ;;
          --theme=*) id=${1#*=}; [[ $id ]] || return 2; shift ;;
          --native) native=1; shift ;;
          -*) return 2 ;;
          *) args+=("$1"); shift ;;
        esac
      done
      ((${#args[@]} >= 1 && ${#args[@]} <= 2)) || return 2
      if [[ ! $id ]]; then dt_current_id || return; id=$REPLY; fi
      dt_find_theme "$id" || { dt_error 'unknown selectable theme ID'; return 1; }
      if ((native)); then dt_load_native "$id" || return; else dt_load "$id" || return; fi
      key=${args[0]}
      dt_key "$key" || { dt_error 'invalid color name'; return 1; }
      value=${DT_SEMANTIC[$key]:-${DT_COLORS[$key]:-}}
      (( ! native )) || value=${DT_COLORS[$key]:-}
      [[ $value ]] || { dt_error 'unknown color'; return 1; }
      if [[ $key == mode ]]; then printf '%s\n' "$value"
      else dt_value "$key" "${args[1]:-hex}" "$value" && printf '%s\n' "$REPLY"; fi ;;
    init) dt_init "$@" ;;
    set|refresh)
      local commands_only=0
      local -a operation_args=()
      for value in "$@"; do
        case $value in
          -v|--verbose) DOTS_OPERATION_VERBOSE=1 ;;
          --commands-only) [[ $action == refresh ]] || return 2; commands_only=1 ;;
          *) operation_args+=("$value") ;;
        esac
      done
      set -- "${operation_args[@]}"
      if ((commands_only)); then
        (($# == 0)) || return 2
        source "$DT_LIB/command-state.bash"
        dt_commands_refresh
        return
      fi
      if [[ $action == refresh ]]; then (($# == 0)) || return 2; dt_current_id || return; id=$REPLY; export DOTS_THEME_REFRESH=1
      else (($# >= 1)) || return 2; id=$1; shift; fi
      while (($#)); do
        case $1 in --dry-run) dry=1 ;; --background) background=1 ;; *) return 2 ;; esac
        shift
      done
      dt_find_theme "$id" || { dt_error 'unknown selectable theme ID'; return 1; }
      dt_load "$id" || return
      source "$DT_LIB/state.bash"
      dt_state_preflight || return
      if ((dry)); then
        dots::operation 'Would publish' '' '' "Select theme $id"
        for ((name=0;name<${#DT_CONNECT_TARGETS[@]};name++)); do
          dots::operation 'Would link' "${DT_CONNECT_SOURCES[name]}" "${DT_CONNECT_TARGETS[name]}" '' file symlink
        done
        if dots::human; then
          dots::heading 'Theme preview'
          dots::row 'Select' "$id"
          dots::resource_row 'Publish' "$DT_ACTIVE"
          for name in "${DT_CONNECT_TARGETS[@]}"; do dots::resource_row 'Connect' "$name"; done
          dots::row 'Reload' 'Available Termux, tmux and Kitty adapters'
          (( ! background )) || dots::row 'Background' 'Apply the selected theme background'
          printf '\n'; dots::info 'Preview only; no changes made'
          return 0
        fi
        printf 'Select %s\nPublish %s\n' "$id" "$DT_ACTIVE"
        for name in "${DT_CONNECT_TARGETS[@]}"; do printf 'Connect %s\n' "$name"; done
        printf 'Reload available Termux, tmux and Kitty adapters\n'
        (( ! background )) || printf 'Apply the selected theme background\n'
        return 0
      fi
      dt_set "$id" || return
      if ((background)); then source "$DT_LIB/backgrounds.bash"; dt_bg select; fi ;;
    switcher)
      for value in "$@"; do
        case $value in -v|--verbose) DOTS_OPERATION_VERBOSE=1 ;; *) return 2 ;; esac
      done
      source "$DT_LIB/switcher.bash"
      dt_switcher ;;
    install|update|remove) source "$DT_LIB/install.bash"; dt_git_theme "$action" "$@" ;;
    bg) source "$DT_LIB/backgrounds.bash"; dt_bg "$@" ;;
    *) source "$DT_LIB/palette-cli.bash"; dt_palette_command "$action" "$@" ;;
  esac
}
if dt_command "$@"; then return 0
else
  status=$?
  ((status != 2)) || dt_error 'invalid arguments; see dots theme --help'
  return "$status"
fi
